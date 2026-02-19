"""
단일 파일 탭 (단일 MP3에 특정 곡 메타데이터 적용)
"""

import re
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional, Dict
from io import BytesIO

from src.models import AlbumInfo, TrackInfo
from src.api import MelonCrawler
from src.services import MP3Handler
from src.ui.theme import Theme, _get_default_dir, PIL_AVAILABLE, DND_AVAILABLE, DND_FILES
from src.ui.widgets.file_dialog import CustomFileDialog
from src.ui.widgets.status_bar import StatusBar

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

class SingleFileTab(ttk.Frame):
    """
    단일 MP3 파일에 특정 곡의 메타데이터를 적용하는 탭.

    레이아웃:
    ┌─────────────────────────────────────────────────┐
    │  멜론 앨범 URL: [_____________] 찾을 노래: [__] │
    │  [크롤링 시작]  [초기화]                        │
    ├─────────────────────────────────────────────────┤
    │  좌: MP3 파일 선택 영역          우: 미리보기   │
    │  (드래그앤드롭 + 파일 선택 버튼)  (앨범아트+메타)│
    ├─────────────────────────────────────────────────┤
    │  [원본 백업] [앨범아트 포함]  [메타데이터 적용] │
    └─────────────────────────────────────────────────┘
    """

    ART_SIZE = 160

    def __init__(self, parent, status_bar: "StatusBar", **kwargs):
        super().__init__(parent, style="TFrame", **kwargs)
        self._status_bar = status_bar
        self._mp3_path: Optional[str] = None
        self._album: Optional[AlbumInfo] = None
        self._matched_track: Optional[TrackInfo] = None
        self._lyrics: str = ""
        self._synced_lyrics: list = []
        self._photo_ref = None
        self._build()
        self._setup_drag_drop()

    def _build(self):
        T = Theme

        # ── 입력 패널 ──────────────────────────
        input_panel = ttk.Frame(self, style="Panel.TFrame")
        input_panel.pack(side="top", fill="x")

        # URL 행
        url_row = ttk.Frame(input_panel, style="Panel.TFrame")
        url_row.pack(fill="x", padx=12, pady=(10, 4))

        ttk.Label(
            url_row, text="멜론 앨범 URL",
            background=T.PANEL, width=12, anchor="e",
        ).pack(side="left", padx=(0, 8))

        self._url_var = tk.StringVar()
        self._url_entry = ttk.Entry(
            url_row, textvariable=self._url_var, font=Theme.FONT_MONO,
        )
        self._url_entry.pack(side="left", fill="x", expand=True, padx=(0, 0))
        self._url_entry.bind("<Return>", lambda e: self._do_crawl())

        # 찾을 노래 행
        search_row = ttk.Frame(input_panel, style="Panel.TFrame")
        search_row.pack(fill="x", padx=12, pady=(0, 10))

        ttk.Label(
            search_row, text="찾을 노래",
            background=T.PANEL, width=12, anchor="e",
        ).pack(side="left", padx=(0, 8))

        self._search_var = tk.StringVar()
        self._search_entry = ttk.Entry(
            search_row, textvariable=self._search_var,
        )
        self._search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._search_entry.bind("<Return>", lambda e: self._do_crawl())

        self._crawl_btn = ttk.Button(
            search_row, text="크롤링 시작",
            style="Accent.TButton", command=self._do_crawl,
        )
        self._crawl_btn.pack(side="left", padx=(0, 6))

        ttk.Button(
            search_row, text="초기화",
            style="TButton", command=self._do_clear,
        ).pack(side="left")

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # ── 메인 영역 ──────────────────────────
        main_frame = ttk.Frame(self, style="TFrame")
        main_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # 좌측: 파일 선택 영역
        file_card = ttk.Frame(main_frame, style="Card.TFrame")
        file_card.pack(side="left", fill="y", padx=(0, 6))
        file_card.configure(width=260)
        file_card.pack_propagate(False)

        ttk.Label(
            file_card, text="MP3 파일 선택",
            style="Header.TLabel", background=T.SURFACE,
        ).pack(anchor="w", padx=12, pady=(10, 8))

        # 드롭 영역 (테두리 효과용 outer frame)
        drop_outer = tk.Frame(file_card, bg=T.BORDER, padx=1, pady=1)
        drop_outer.pack(padx=16, pady=(0, 10))

        self._drop_frame = tk.Frame(
            drop_outer, bg=T.PANEL, width=210, height=110,
        )
        self._drop_frame.pack()
        self._drop_frame.pack_propagate(False)

        self._drop_label = tk.Label(
            self._drop_frame,
            text="MP3 파일을\n여기에 드래그",
            bg=T.PANEL, fg=T.TEXT_DIM,
            font=T.FONT_KR,
        )
        self._drop_label.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Button(
            file_card, text="파일 선택",
            style="TButton", command=self._pick_file,
        ).pack(padx=16, fill="x")

        ttk.Separator(file_card, orient="horizontal").pack(fill="x", padx=16, pady=10)

        ttk.Label(
            file_card, text="선택된 파일",
            style="Accent.TLabel", background=T.SURFACE,
        ).pack(anchor="w", padx=16)

        self._file_name_var = tk.StringVar(value="없음")
        ttk.Label(
            file_card, textvariable=self._file_name_var,
            style="Sub.TLabel", wraplength=220, justify="left",
        ).pack(anchor="w", padx=16, pady=(4, 0))

        # 우측: 미리보기 영역
        preview_card = ttk.Frame(main_frame, style="Card.TFrame")
        preview_card.pack(side="left", fill="both", expand=True)

        ttk.Label(
            preview_card, text="매칭 결과 미리보기",
            style="Header.TLabel", background=T.SURFACE,
        ).pack(anchor="w", padx=12, pady=(10, 8))

        preview_body = ttk.Frame(preview_card, style="Card.TFrame")
        preview_body.pack(fill="x", padx=12, pady=(0, 8))

        # 앨범아트
        art_wrapper = tk.Frame(
            preview_body, bg=T.PANEL,
            width=self.ART_SIZE, height=self.ART_SIZE,
        )
        art_wrapper.pack(side="left", padx=(0, 20), pady=4)
        art_wrapper.pack_propagate(False)

        self._art_label = tk.Label(
            art_wrapper, bg=T.PANEL,
            text="앨범아트\n없음",
            fg=T.TEXT_DIM, font=T.FONT_KR_SM,
        )
        self._art_label.place(relx=0.5, rely=0.5, anchor="center")

        # 메타데이터 필드
        meta_frame = ttk.Frame(preview_body, style="Card.TFrame")
        meta_frame.pack(side="left", fill="both", expand=True, pady=4)

        fields = [
            ("제목",        "title"),
            ("아티스트",    "artist"),
            ("앨범",        "album"),
            ("앨범아티스트", "album_artist"),
            ("장르",        "genre"),
            ("발매일",      "release_date"),
            ("트랙번호",    "track_number"),
            ("디스크번호",  "disc_number"),
        ]
        self._meta_vars: Dict[str, tk.StringVar] = {}

        for label_text, key in fields:
            row = ttk.Frame(meta_frame, style="Card.TFrame")
            row.pack(fill="x", pady=3)

            ttk.Label(
                row, text=label_text,
                style="Accent.TLabel", width=10, anchor="w",
            ).pack(side="left")

            var = tk.StringVar(value="—")
            self._meta_vars[key] = var

            ttk.Label(
                row, textvariable=var,
                style="Sub.TLabel",
                wraplength=340, justify="left", anchor="w",
            ).pack(side="left", fill="x", expand=True)

        # ── 가사 영역 ──────────────────────────
        ttk.Separator(preview_card, orient="horizontal").pack(fill="x", padx=12, pady=(4, 0))

        lyrics_header = ttk.Frame(preview_card, style="Card.TFrame")
        lyrics_header.pack(fill="x", padx=12, pady=(6, 4))

        ttk.Label(
            lyrics_header, text="가사",
            style="Accent.TLabel",
        ).pack(side="left")

        self._lyrics_status_var = tk.StringVar(value="")
        ttk.Label(
            lyrics_header, textvariable=self._lyrics_status_var,
            style="Sub.TLabel",
        ).pack(side="left", padx=(8, 0))

        self._sync_status_var = tk.StringVar(value="")
        ttk.Label(
            lyrics_header, textvariable=self._sync_status_var,
            style="Accent.TLabel",
        ).pack(side="left", padx=(12, 0))

        lyrics_frame = ttk.Frame(preview_card, style="Card.TFrame")
        lyrics_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._lyrics_text = tk.Text(
            lyrics_frame,
            bg=T.ENTRY_BG,
            fg=T.TEXT,
            insertbackground=T.TEXT,
            selectbackground=T.SELECT_BG,
            selectforeground=T.SELECT_FG,
            font=T.FONT_KR_SM,
            relief="flat",
            wrap="word",
            state="disabled",
            height=6,
        )
        lyrics_vsb = ttk.Scrollbar(
            lyrics_frame, orient="vertical", command=self._lyrics_text.yview,
        )
        self._lyrics_text.configure(yscrollcommand=lyrics_vsb.set)
        self._lyrics_text.pack(side="left", fill="both", expand=True)
        lyrics_vsb.pack(side="right", fill="y")

        # ── 하단: 적용 버튼 바 ─────────────────
        apply_bar = ttk.Frame(self, style="Card.TFrame", padding=(10, 6))
        apply_bar.pack(side="bottom", fill="x", padx=8, pady=(0, 4))

        ttk.Separator(apply_bar, orient="horizontal").pack(fill="x", pady=(0, 8))

        btn_row = ttk.Frame(apply_bar, style="Card.TFrame")
        btn_row.pack(fill="x")

        self._apply_btn = ttk.Button(
            btn_row, text="메타데이터 적용",
            style="Accent.TButton", command=self._do_apply,
            state="disabled",
        )
        self._apply_btn.pack(side="left", padx=(0, 8))

        opts_frame = ttk.Frame(btn_row, style="Card.TFrame")
        opts_frame.pack(side="right")

        self._backup_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts_frame, text="원본 백업",
            variable=self._backup_var,
        ).pack(side="left", padx=6)

        self._cover_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            opts_frame, text="앨범아트 포함",
            variable=self._cover_var,
        ).pack(side="left", padx=6)

    def _setup_drag_drop(self):
        if not DND_AVAILABLE:
            return
        for widget in (self._drop_frame, self._drop_label):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        raw = event.data or ""
        paths = re.findall(r'\{([^}]+)\}|([^\s{}]+)', raw)
        paths = [p[0] or p[1] for p in paths if p[0] or p[1]]
        if paths:
            self._set_mp3_file(paths[0])

    def _pick_file(self):
        dlg = CustomFileDialog(self, initial_dir=_get_default_dir())
        self.wait_window(dlg)
        files = dlg.get_files()
        if files:
            self._set_mp3_file(files[0])

    def _set_mp3_file(self, path: str):
        # Windows 경로 자동 변환
        if len(path) > 2 and path[1] == ":":
            try:
                r = subprocess.run(["wslpath", path], capture_output=True, timeout=3)
                if r.returncode == 0:
                    path = r.stdout.decode("utf-8", errors="replace").strip()
            except Exception:
                pass

        p = Path(path)
        if p.suffix.lower() != ".mp3":
            messagebox.showwarning("파일 오류", "MP3 파일만 선택할 수 있습니다.")
            return

        self._mp3_path = str(p)
        name = p.name
        display = name[:28] + "…" if len(name) > 28 else name
        self._file_name_var.set(display)
        self._drop_label.config(text=display, fg=Theme.TEXT)

        # 미리보기가 이미 로드된 상태면 적용 버튼 활성화
        if self._matched_track:
            self._apply_btn.configure(state="normal")

    # ── 크롤링 ────────────────────────────────
    def _do_crawl(self):
        url = self._url_var.get().strip()
        search = self._search_var.get().strip()

        if not url:
            messagebox.showwarning("URL 필요", "멜론 앨범 URL을 입력해 주세요.")
            return
        if not search:
            messagebox.showwarning("노래 제목 필요", "찾을 노래 제목을 입력해 주세요.")
            return

        self._crawl_btn.configure(state="disabled")
        self._apply_btn.configure(state="disabled")
        self._status_bar.set_status("크롤링 중...", "info")
        self._status_bar.set_progress(0)
        self._clear_preview()

        threading.Thread(
            target=self._crawl_worker, args=(url, search), daemon=True,
        ).start()

    def _crawl_worker(self, url: str, search: str):
        try:
            crawler = MelonCrawler()
            album = crawler.crawl_album(url)
            self.after(0, self._on_crawl_done, album, search)
        except Exception as exc:
            self.after(0, self._on_crawl_error, str(exc))

    def _on_crawl_done(self, album: AlbumInfo, search: str):
        self._album = album
        self._crawl_btn.configure(state="normal")

        track = self._find_track(album, search)
        if track is None:
            self._status_bar.set_status(
                f"'{search}'와 일치하는 곡을 찾지 못했습니다.", "warning"
            )
            messagebox.showwarning(
                "곡 미발견",
                f"'{search}'와 일치하는 곡을 앨범에서 찾지 못했습니다.\n"
                "제목을 다시 확인해 주세요.\n\n"
                f"앨범 트랙 수: {len(album.tracks)}곡",
            )
            return

        self._matched_track = track
        self._show_preview(album, track)

        if self._mp3_path:
            self._apply_btn.configure(state="normal")

        self._status_bar.set_status(f"'{track.title}' 매칭 완료", "success")
        self._status_bar.set_progress(100)

        # 가사 비동기 로딩 시작 (일반 + 싱크)
        if track.song_id:
            self._lyrics_status_var.set("가사 로딩 중...")
            self._sync_status_var.set("")
            threading.Thread(
                target=self._fetch_lyrics_worker,
                args=(track.song_id, track.title, track.artist, track.album),
                daemon=True,
            ).start()
        else:
            self._lyrics_status_var.set("가사 정보 없음")
            self._sync_status_var.set("")

    def _on_crawl_error(self, msg: str):
        self._crawl_btn.configure(state="normal")
        self._status_bar.set_status(f"크롤링 실패: {msg}", "error")
        self._status_bar.reset_progress()
        messagebox.showerror(
            "크롤링 오류",
            f"앨범 정보를 가져오는 중 오류가 발생했습니다.\n\n{msg}",
        )

    # ── 가사 로딩 ────────────────────────────
    def _fetch_lyrics_worker(self, song_id: str, title: str, artist: str, album: str):
        crawler = MelonCrawler()
        detail = crawler.crawl_song_detail(song_id)
        synced = crawler.fetch_synced_lyrics(title, artist, album)
        self.after(0, self._on_lyrics_done, detail["lyrics"], synced, detail["genre"])

    def _on_lyrics_done(self, lyrics: str, synced: list, genre: str):
        # 멜론 가사가 없고 LRCLIB 싱크 가사가 있으면 LRC에서 plain 텍스트 추출
        if not lyrics and synced:
            lyrics = "\n".join(text for text, _ in synced if text.strip())

        self._lyrics = lyrics
        self._synced_lyrics = synced

        # 곡 상세 페이지에서 가져온 장르로 미리보기 갱신
        if genre:
            self._meta_vars["genre"].set(genre)

        self._lyrics_text.configure(state="normal")
        self._lyrics_text.delete("1.0", "end")
        if lyrics:
            self._lyrics_text.insert("1.0", lyrics)
            self._lyrics_status_var.set("가사 로드됨")
        else:
            self._lyrics_text.insert("1.0", "(가사 없음)")
            self._lyrics_status_var.set("가사 없음")
        self._lyrics_text.configure(state="disabled")

        if synced:
            self._sync_status_var.set(f"싱크 가사 있음 ({len(synced)}줄)")
        else:
            self._sync_status_var.set("싱크 가사 없음")

    def _find_track(self, album: AlbumInfo, search: str) -> Optional[TrackInfo]:
        """검색어와 가장 잘 일치하는 트랙 반환 (정확→정규화→부분 포함 순)"""
        search_lower = search.lower()
        search_norm = re.sub(r"[\s\-_\(\)\[\]]", "", search_lower)

        # 1순위: 정확 일치 (대소문자 무관)
        for track in album.tracks:
            if track.title.lower() == search_lower:
                return track

        # 2순위: 정규화 일치
        for track in album.tracks:
            title_norm = re.sub(r"[\s\-_\(\)\[\]]", "", track.title.lower())
            if title_norm == search_norm:
                return track

        # 3순위: 부분 포함
        for track in album.tracks:
            title_norm = re.sub(r"[\s\-_\(\)\[\]]", "", track.title.lower())
            if search_norm and (search_norm in title_norm or title_norm in search_norm):
                return track

        return None

    def _show_preview(self, album: AlbumInfo, track: TrackInfo):
        self._meta_vars["title"].set(track.title or "—")
        self._meta_vars["artist"].set(track.artist or "—")
        self._meta_vars["album"].set(track.album or "—")
        self._meta_vars["album_artist"].set(track.album_artist or "—")
        self._meta_vars["genre"].set(track.genre or "—")
        self._meta_vars["release_date"].set(album.release_date or "—")
        self._meta_vars["track_number"].set(str(track.track_number))
        self._meta_vars["disc_number"].set(str(track.disc_number))

        if album.cover_data and PIL_AVAILABLE:
            img = Image.open(BytesIO(album.cover_data))
            img = img.resize((self.ART_SIZE, self.ART_SIZE), Image.LANCZOS)
            self._photo_ref = ImageTk.PhotoImage(img)
            self._art_label.config(image=self._photo_ref, text="")
        else:
            self._art_label.config(text="앨범아트\n없음", image="")

    def _clear_preview(self):
        for var in self._meta_vars.values():
            var.set("—")
        self._art_label.config(text="앨범아트\n없음", image="")
        self._photo_ref = None
        self._matched_track = None
        self._lyrics = ""
        self._synced_lyrics = []
        self._lyrics_status_var.set("")
        self._sync_status_var.set("")
        self._lyrics_text.configure(state="normal")
        self._lyrics_text.delete("1.0", "end")
        self._lyrics_text.configure(state="disabled")

    # ── 적용 ──────────────────────────────────
    @staticmethod
    def _safe_filename(text: str) -> str:
        """파일명에 사용할 수 없는 문자를 제거한다."""
        return re.sub(r'[\\/:*?"<>|]', "", text).strip()

    def _do_apply(self):
        if not self._mp3_path:
            messagebox.showwarning("파일 없음", "MP3 파일을 먼저 선택해 주세요.")
            return
        if not self._matched_track or not self._album:
            messagebox.showwarning("매칭 없음", "먼저 크롤링을 실행해 주세요.")
            return

        track = self._matched_track
        handler = MP3Handler()

        try:
            if self._backup_var.get():
                backup_path = Path(self._mp3_path).with_suffix(".mp3.bak")
                if not backup_path.exists():
                    shutil.copy2(self._mp3_path, backup_path)

            handler.write_metadata(
                filepath=self._mp3_path,
                title=track.title,
                artist=track.artist,
                album=track.album,
                album_artist=track.album_artist,
                genre=track.genre,
                track_number=track.track_number,
                disc_number=track.disc_number,
                cover_data=self._album.cover_data if self._cover_var.get() else None,
                lyrics=self._lyrics,
            )

            # ── 파일명 변경: 가수명-트랙번호-노래제목.mp3 ──
            old_path = Path(self._mp3_path)
            artist_part = self._safe_filename(track.artist)
            title_part  = self._safe_filename(track.title)
            new_name    = f"{artist_part}-{track.track_number:02d}-{title_part}.mp3"
            new_path    = old_path.parent / new_name

            # 동일 이름 파일이 이미 있으면 덮어쓰지 않고 번호 붙임
            if new_path.exists() and new_path != old_path:
                stem = f"{artist_part}-{track.track_number:02d}-{title_part}"
                for i in range(2, 100):
                    candidate = old_path.parent / f"{stem}({i}).mp3"
                    if not candidate.exists():
                        new_path = candidate
                        break

            old_path.rename(new_path)
            self._mp3_path = str(new_path)

            # ── .lrc 사이드카 파일 생성 (삼성뮤직 싱크 가사) ──
            # 파일명 변경 이후에 생성해야 MP3와 이름이 일치함
            lrc_created = False
            if self._synced_lyrics:
                handler.write_lrc_file(str(new_path), self._synced_lyrics)
                lrc_created = True

            # UI 표시 갱신
            display = new_name[:28] + "…" if len(new_name) > 28 else new_name
            self._file_name_var.set(display)
            self._drop_label.config(text=display, fg=Theme.ACCENT)

            lrc_info = "\n싱크 가사(.lrc) 파일도 생성되었습니다." if lrc_created else ""
            self._status_bar.set_status(
                f"적용 완료 — {new_name}", "success"
            )
            messagebox.showinfo(
                "적용 완료",
                f"메타데이터와 파일명이 변경되었습니다.{lrc_info}\n\n"
                f"변경 전: {old_path.name}\n"
                f"변경 후: {new_name}\n\n"
                f"제목: {track.title}\n"
                f"아티스트: {track.artist}",
            )
        except Exception as exc:
            self._status_bar.set_status(f"적용 실패: {exc}", "error")
            messagebox.showerror(
                "적용 오류",
                f"메타데이터 적용 중 오류가 발생했습니다.\n\n{exc}",
            )

    def _do_clear(self):
        self._url_var.set("")
        self._search_var.set("")
        self._clear_preview()
        self._apply_btn.configure(state="disabled")
        self._status_bar.set_status("초기화됨", "info")
        self._status_bar.reset_progress()



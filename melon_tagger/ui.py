"""
melon_tagger/ui.py
Melon MP3 Tagger - tkinter + ttk UI
다크 테마 기반 메인 애플리케이션 윈도우
"""

import os
import re
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, List, Dict
from io import BytesIO

# PIL은 앨범아트 표시에 사용 (없으면 텍스트 대체)
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# tkinterdnd2 : 드래그 앤 드롭 지원
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

from melon_tagger.crawler import MelonCrawler, AlbumInfo, TrackInfo
from melon_tagger.mp3_handler import MP3Handler


def _get_default_dir() -> Path:
    """WSL 환경이면 Windows 바탕화면, 아니면 홈 디렉토리를 반환한다."""
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", "echo %USERPROFILE%"],
            capture_output=True, timeout=3
        )
        # Windows cmd 출력은 CP949(한국어 Windows)로 인코딩됨
        win_profile = result.stdout.decode("cp949", errors="replace").strip()
        if win_profile and win_profile != "%USERPROFILE%":
            wsl = subprocess.run(
                ["wslpath", win_profile],
                capture_output=True, timeout=3
            )
            wsl_path = wsl.stdout.decode("utf-8", errors="replace").strip()
            desktop = Path(wsl_path) / "Desktop"
            if desktop.is_dir():
                return desktop
    except Exception:
        pass
    return Path.home()


# ─────────────────────────────────────────────
# 디자인 토큰 (색상, 폰트)
# ─────────────────────────────────────────────
class Theme:
    BG         = "#1e1e2e"   # 최외곽 배경
    SURFACE    = "#181825"   # 패널 내부 배경
    PANEL      = "#313244"   # 카드 / 헤더 배경
    BORDER     = "#45475a"   # 구분선, 테두리
    ACCENT     = "#00C73C"   # 멜론 그린
    ACCENT_DIM = "#009e30"   # 호버/프레스 그린
    TEXT       = "#cdd6f4"   # 기본 텍스트
    TEXT_SUB   = "#a6adc8"   # 보조 텍스트
    TEXT_DIM   = "#6c7086"   # 비활성 텍스트
    ERROR      = "#f38ba8"   # 에러 (레드)
    SUCCESS    = "#a6e3a1"   # 성공 (그린)
    WARNING    = "#f9e2af"   # 경고 (옐로)
    SELECT_BG  = "#1e3a2f"   # Treeview 선택 배경
    SELECT_FG  = "#00C73C"   # Treeview 선택 텍스트
    ENTRY_BG   = "#2a2a3e"   # Entry 배경

    FONT_KR    = ("맑은 고딕", 10)
    FONT_KR_SM = ("맑은 고딕", 9)
    FONT_KR_LG = ("맑은 고딕", 12, "bold")
    FONT_KR_H  = ("맑은 고딕", 14, "bold")
    FONT_MONO  = ("Consolas", 9)


# ─────────────────────────────────────────────
# ttk.Style 전체 설정
# ─────────────────────────────────────────────
def apply_dark_theme(root: tk.Tk) -> ttk.Style:
    """전체 ttk 위젯에 다크 테마를 적용한다."""
    style = ttk.Style(root)
    style.theme_use("clam")   # clam 베이스가 색상 커스터마이징에 가장 유연함

    T = Theme

    # ── 공통 ──────────────────────────────────
    style.configure(".",
        background=T.BG,
        foreground=T.TEXT,
        font=T.FONT_KR,
        borderwidth=0,
        focuscolor=T.ACCENT,
        relief="flat",
    )
    style.map(".",
        background=[("disabled", T.BG)],
        foreground=[("disabled", T.TEXT_DIM)],
    )

    # ── Frame ──────────────────────────────────
    style.configure("TFrame",    background=T.BG)
    style.configure("Card.TFrame",
        background=T.SURFACE,
        relief="flat",
    )
    style.configure("Panel.TFrame",
        background=T.PANEL,
    )

    # ── LabelFrame ────────────────────────────
    style.configure("TLabelframe",
        background=T.BG,
        foreground=T.TEXT_SUB,
        bordercolor=T.BORDER,
        relief="flat",
        padding=(8, 4),
    )
    style.configure("TLabelframe.Label",
        background=T.BG,
        foreground=T.TEXT_SUB,
        font=T.FONT_KR_SM,
    )

    # ── Label ─────────────────────────────────
    style.configure("TLabel",
        background=T.BG,
        foreground=T.TEXT,
        font=T.FONT_KR,
    )
    style.configure("Title.TLabel",
        background=T.SURFACE,
        foreground=T.TEXT,
        font=T.FONT_KR_LG,
    )
    style.configure("Sub.TLabel",
        background=T.SURFACE,
        foreground=T.TEXT_SUB,
        font=T.FONT_KR_SM,
    )
    style.configure("Accent.TLabel",
        background=T.SURFACE,
        foreground=T.ACCENT,
        font=T.FONT_KR_SM,
    )
    style.configure("Header.TLabel",
        background=T.BG,
        foreground=T.TEXT,
        font=T.FONT_KR_H,
    )
    style.configure("Status.TLabel",
        background=T.PANEL,
        foreground=T.TEXT_SUB,
        font=T.FONT_KR_SM,
        padding=(6, 3),
    )

    # ── Entry ─────────────────────────────────
    style.configure("TEntry",
        fieldbackground=T.ENTRY_BG,
        foreground=T.TEXT,
        insertcolor=T.TEXT,
        bordercolor=T.BORDER,
        lightcolor=T.BORDER,
        darkcolor=T.BORDER,
        relief="flat",
        padding=(6, 5),
    )
    style.map("TEntry",
        bordercolor=[("focus", T.ACCENT)],
        lightcolor=[("focus", T.ACCENT)],
    )

    # ── Button ────────────────────────────────
    style.configure("TButton",
        background=T.PANEL,
        foreground=T.TEXT,
        bordercolor=T.BORDER,
        lightcolor=T.BORDER,
        darkcolor=T.BORDER,
        relief="flat",
        padding=(10, 6),
        font=T.FONT_KR,
    )
    style.map("TButton",
        background=[
            ("pressed",  T.BORDER),
            ("active",   T.BORDER),
        ],
        foreground=[
            ("pressed",  T.TEXT),
            ("active",   T.TEXT),
        ],
    )

    # 강조 버튼 (크롤링, 적용 등)
    style.configure("Accent.TButton",
        background=T.ACCENT,
        foreground="#0f0f0f",
        bordercolor=T.ACCENT,
        lightcolor=T.ACCENT,
        darkcolor=T.ACCENT,
        relief="flat",
        padding=(12, 6),
        font=(*T.FONT_KR[:2], "bold"),
    )
    style.map("Accent.TButton",
        background=[
            ("pressed",  T.ACCENT_DIM),
            ("active",   T.ACCENT_DIM),
            ("disabled", T.BORDER),
        ],
        foreground=[
            ("disabled", T.TEXT_DIM),
        ],
    )

    # 위험 버튼 (삭제)
    style.configure("Danger.TButton",
        background="#3d2030",
        foreground=T.ERROR,
        bordercolor="#5a2a3a",
        padding=(10, 6),
        font=T.FONT_KR,
    )
    style.map("Danger.TButton",
        background=[("active", "#5a2030"), ("pressed", "#5a2030")],
    )

    # ── Treeview ──────────────────────────────
    style.configure("Treeview",
        background=T.SURFACE,
        foreground=T.TEXT,
        fieldbackground=T.SURFACE,
        bordercolor=T.BORDER,
        font=T.FONT_KR,
        rowheight=26,
    )
    style.configure("Treeview.Heading",
        background=T.PANEL,
        foreground=T.TEXT_SUB,
        relief="flat",
        font=T.FONT_KR_SM,
        padding=(4, 6),
    )
    style.map("Treeview",
        background=[("selected", T.SELECT_BG)],
        foreground=[("selected", T.SELECT_FG)],
    )
    style.map("Treeview.Heading",
        background=[("active", T.BORDER)],
    )

    # ── Progressbar ───────────────────────────
    style.configure("TProgressbar",
        background=T.ACCENT,
        troughcolor=T.PANEL,
        bordercolor=T.PANEL,
        lightcolor=T.ACCENT,
        darkcolor=T.ACCENT_DIM,
        thickness=6,
    )

    # ── Scrollbar ─────────────────────────────
    style.configure("TScrollbar",
        background=T.PANEL,
        troughcolor=T.SURFACE,
        bordercolor=T.SURFACE,
        arrowcolor=T.TEXT_DIM,
        relief="flat",
        width=10,
    )
    style.map("TScrollbar",
        background=[("active", T.BORDER)],
    )

    # ── Separator ─────────────────────────────
    style.configure("TSeparator", background=T.BORDER)

    # ── Combobox ──────────────────────────────
    style.configure("TCombobox",
        fieldbackground=T.ENTRY_BG,
        background=T.PANEL,
        foreground=T.TEXT,
        arrowcolor=T.TEXT_SUB,
        bordercolor=T.BORDER,
        insertcolor=T.TEXT,
        padding=(6, 5),
    )
    style.map("TCombobox",
        fieldbackground=[("readonly", T.ENTRY_BG)],
        foreground=[("readonly", T.TEXT)],
    )

    # ── Checkbutton ───────────────────────────
    style.configure("TCheckbutton",
        background=T.BG,
        foreground=T.TEXT,
        indicatorcolor=T.ENTRY_BG,
        indicatorbackground=T.ENTRY_BG,
    )
    style.map("TCheckbutton",
        indicatorcolor=[("selected", T.ACCENT)],
    )

    # ── Notebook ──────────────────────────────
    #
    # 높이 차이 구현 원리:
    #   - style.map의 padding이 configure의 기본 padding을 상태별로 덮어씀
    #   - selected: 상단 패딩 11px → 탭이 더 높게 렌더링됨
    #   - 미선택(기본): 상단 패딩 7px → 상대적으로 낮게 보임
    #   - tabmargins=[0, 3, 0, 0]: 상단 마진 3px로 선택 탭이 위로 살짝 돌출되는
    #     효과를 허용하면서, 탭 바와 탭 바디 사이 경계선을 최소화함
    #
    style.configure("TNotebook",
        background=T.BG,
        bordercolor=T.BORDER,
        # tabmargins: [좌, 상, 우, 하]
        # 상단 마진을 3으로 주어 선택된 탭이 위로 돌출되는 느낌을 살림
        tabmargins=[0, 3, 0, 0],
    )
    style.configure("TNotebook.Tab",
        background=T.PANEL,
        foreground=T.TEXT_SUB,
        # 기본(미선택) 패딩: [좌우 18px, 상하 7px]
        # selected 상태는 style.map에서 덮어씌워 상단을 더 크게 만듦
        padding=[18, 7],
        font=T.FONT_KR,
    )
    style.map("TNotebook.Tab",
        # 선택된 탭: 짙은 배경(SURFACE) + 상단 패딩 확장으로 높이 증가
        # 미선택 호버(active): BORDER 배경으로 미묘한 피드백
        background=[
            ("selected", T.SURFACE),
            ("active",   T.BORDER),
        ],
        foreground=[
            ("selected", T.ACCENT),
            ("active",   T.TEXT),
        ],
        # padding[1](상단)을 선택 시 11, 기본 7로 차이를 줌 → 4px 높이 차이
        # active도 8px로 호버 시 미묘하게 커지는 느낌 추가
        padding=[
            ("selected", [18, 11]),
            ("active",   [18, 8]),
        ],
        # 선택 탭에만 볼드 폰트 적용 — T.FONT_KR[:2]로 크기/패밀리 유지
        font=[
            ("selected", (*T.FONT_KR[:2], "bold")),
        ],
    )

    return style


# ─────────────────────────────────────────────
# AlbumInfoPanel - 좌측 앨범 정보 패널
# ─────────────────────────────────────────────
class AlbumInfoPanel(ttk.Frame):
    """
    앨범아트(180x180) + 앨범명/아티스트/장르/발매일 텍스트 표시
    레이아웃: pack() 사용 (수직 스택)
    """

    ART_SIZE = 180

    def __init__(self, parent, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self._photo_ref = None   # GC 방지 (PhotoImage 레퍼런스)
        self._build()

    def _build(self):
        T = Theme

        # ── 앨범아트 영역 ──────────────────────
        art_wrapper = tk.Frame(
            self, bg=T.PANEL,
            width=self.ART_SIZE, height=self.ART_SIZE,
        )
        art_wrapper.pack(pady=(16, 10))
        art_wrapper.pack_propagate(False)   # 고정 크기 유지

        self._art_label = tk.Label(
            art_wrapper,
            bg=T.PANEL,
            text="앨범아트\n없음",
            fg=T.TEXT_DIM,
            font=Theme.FONT_KR_SM,
        )
        self._art_label.place(relx=0.5, rely=0.5, anchor="center")

        # ── 텍스트 정보 영역 ───────────────────
        info_frame = ttk.Frame(self, style="Card.TFrame")
        info_frame.pack(fill="x", padx=14, pady=(0, 14))

        fields = [
            ("앨범명",    "album_name"),
            ("아티스트",  "album_artist"),
            ("장르",      "genre"),
            ("발매일",    "release_date"),
        ]
        self._info_vars: Dict[str, tk.StringVar] = {}

        for label_text, key in fields:
            row = ttk.Frame(info_frame, style="Card.TFrame")
            row.pack(fill="x", pady=2)

            ttk.Label(
                row,
                text=f"{label_text}",
                style="Accent.TLabel",
                width=7,
                anchor="w",
            ).pack(side="left")

            var = tk.StringVar(value="—")
            self._info_vars[key] = var

            ttk.Label(
                row,
                textvariable=var,
                style="Sub.TLabel",
                wraplength=140,
                justify="left",
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

        # ── 트랙 수 배지 ───────────────────────
        badge_frame = ttk.Frame(self, style="Card.TFrame")
        badge_frame.pack(fill="x", padx=14, pady=(0, 14))

        ttk.Label(
            badge_frame,
            text="트랙 수",
            style="Accent.TLabel",
            width=7,
            anchor="w",
        ).pack(side="left")

        self._track_count_var = tk.StringVar(value="—")
        ttk.Label(
            badge_frame,
            textvariable=self._track_count_var,
            style="Sub.TLabel",
        ).pack(side="left")

    # ── 공개 API ──────────────────────────────
    def load_album(self, album: AlbumInfo):
        """AlbumInfo 객체로 패널을 갱신한다."""
        self._info_vars["album_name"].set(album.album_name or "—")
        self._info_vars["album_artist"].set(album.album_artist or "—")
        self._info_vars["genre"].set(album.genre or "—")
        self._info_vars["release_date"].set(album.release_date or "—")
        self._track_count_var.set(f"{len(album.tracks)}곡")

        if album.cover_data and PIL_AVAILABLE:
            self._load_cover(album.cover_data)
        else:
            self._art_label.config(text="앨범아트\n없음", image="")

    def clear(self):
        for var in self._info_vars.values():
            var.set("—")
        self._track_count_var.set("—")
        self._art_label.config(text="앨범아트\n없음", image="")
        self._photo_ref = None

    def _load_cover(self, data: bytes):
        img = Image.open(BytesIO(data))
        img = img.resize((self.ART_SIZE, self.ART_SIZE), Image.LANCZOS)
        self._photo_ref = ImageTk.PhotoImage(img)
        self._art_label.config(image=self._photo_ref, text="")


# ─────────────────────────────────────────────
# TrackTreeview - 우측 트랙 목록
# ─────────────────────────────────────────────
class TrackTreeview(ttk.Frame):
    """
    멜론 크롤링 트랙 목록 Treeview
    컬럼: #(트랙번호) | 제목 | 아티스트 | 매칭상태
    """

    COLS = {
        "#":      {"width": 40,  "anchor": "center", "label": "#"},
        "title":  {"width": 240, "anchor": "w",      "label": "제목"},
        "artist": {"width": 160, "anchor": "w",      "label": "아티스트"},
        "status": {"width": 80,  "anchor": "center", "label": "상태"},
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self._build()

    def _build(self):
        T = Theme

        # 헤더 레이블
        hdr = ttk.Label(
            self, text="트랙 목록", style="Header.TLabel",
            background=T.SURFACE,
        )
        hdr.pack(anchor="w", padx=12, pady=(10, 6))

        # Treeview + 스크롤바
        tree_frame = ttk.Frame(self, style="Card.TFrame")
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        col_ids = list(self.COLS.keys())
        self.tree = ttk.Treeview(
            tree_frame,
            columns=col_ids,
            show="headings",
            selectmode="browse",
        )

        for col_id, cfg in self.COLS.items():
            self.tree.heading(
                col_id,
                text=cfg["label"],
                anchor=cfg["anchor"],
            )
            self.tree.column(
                col_id,
                width=cfg["width"],
                minwidth=cfg["width"] // 2,
                anchor=cfg["anchor"],
                stretch=(col_id == "title"),  # 제목 컬럼만 stretch
            )

        # 홀짝 행 색상 태그
        self.tree.tag_configure("even", background=T.SURFACE)
        self.tree.tag_configure("odd",  background=T.BG)
        self.tree.tag_configure("matched",   foreground=T.SUCCESS)
        self.tree.tag_configure("unmatched", foreground=T.TEXT_DIM)
        self.tree.tag_configure("partial",   foreground=T.WARNING)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # grid 배치 (스크롤바 포함)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

    # ── 공개 API ──────────────────────────────
    def load_tracks(self, tracks: List[TrackInfo]):
        """트랙 목록을 Treeview에 채운다."""
        self.tree.delete(*self.tree.get_children())
        for i, track in enumerate(tracks):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert(
                "", "end",
                iid=str(track.track_number),
                values=(
                    track.track_number,
                    track.title,
                    track.artist,
                    "대기",
                ),
                tags=(tag,),
            )

    def set_track_status(self, track_number: int, status: str, status_type: str = ""):
        """
        특정 트랙의 상태 셀을 업데이트한다.
        status_type: 'matched' | 'unmatched' | 'partial' | ''
        """
        iid = str(track_number)
        if not self.tree.exists(iid):
            return
        vals = list(self.tree.item(iid, "values"))
        vals[3] = status
        current_tags = list(self.tree.item(iid, "tags"))
        # 기존 상태 태그 제거
        for t in ("matched", "unmatched", "partial"):
            if t in current_tags:
                current_tags.remove(t)
        if status_type:
            current_tags.append(status_type)
        self.tree.item(iid, values=vals, tags=current_tags)

    def clear(self):
        self.tree.delete(*self.tree.get_children())

    def get_selected_track_number(self) -> Optional[int]:
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None


# ─────────────────────────────────────────────
# MP3FilePanel - 하단 MP3 파일 관리 패널
# ─────────────────────────────────────────────
class MP3FilePanel(ttk.Frame):
    """
    MP3 파일 목록 Treeview + 파일/폴더 추가/제거 버튼
    매칭 결과(트랙번호, 매칭상태) 컬럼 포함
    """

    COLS = {
        "filename":   {"width": 240, "anchor": "w",      "label": "파일명"},
        "track":      {"width": 50,  "anchor": "center", "label": "트랙#"},
        "title":      {"width": 180, "anchor": "w",      "label": "현재 제목"},
        "artist":     {"width": 140, "anchor": "w",      "label": "현재 아티스트"},
        "match":      {"width": 90,  "anchor": "center", "label": "매칭"},
    }

    def __init__(self, parent, on_files_changed=None, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self._on_files_changed = on_files_changed
        self._file_paths: Dict[str, str] = {}   # iid -> 절대경로
        self._last_dir: Path = _get_default_dir()   # 마지막 탐색 디렉토리
        self._build()
        self._setup_drag_drop()

    def _build(self):
        T = Theme

        # ── 헤더 + 버튼 바 ────────────────────
        top_bar = ttk.Frame(self, style="Card.TFrame")
        top_bar.pack(fill="x", padx=10, pady=(8, 4))

        ttk.Label(
            top_bar, text="MP3 파일", style="Header.TLabel",
            background=T.SURFACE,
        ).pack(side="left")

        btn_frame = ttk.Frame(top_bar, style="Card.TFrame")
        btn_frame.pack(side="right")

        buttons = [
            ("파일 추가",   self._add_files,   "TButton"),
            ("폴더 추가",   self._add_folder,  "TButton"),
            ("자동 매칭",   self._auto_match,  "Accent.TButton"),
            ("선택 제거",   self._remove_selected, "Danger.TButton"),
            ("전체 제거",   self._clear_all,   "Danger.TButton"),
        ]
        for text, cmd, style_name in buttons:
            ttk.Button(
                btn_frame, text=text, command=cmd, style=style_name,
            ).pack(side="left", padx=3)

        # ── Treeview ──────────────────────────
        tree_frame = ttk.Frame(self, style="Card.TFrame")
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        col_ids = list(self.COLS.keys())
        self.tree = ttk.Treeview(
            tree_frame,
            columns=col_ids,
            show="headings",
            selectmode="extended",
        )

        for col_id, cfg in self.COLS.items():
            self.tree.heading(col_id, text=cfg["label"], anchor=cfg["anchor"])
            self.tree.column(
                col_id,
                width=cfg["width"],
                minwidth=col_id == "filename" and 120 or 40,
                anchor=cfg["anchor"],
                stretch=(col_id == "filename"),
            )

        self.tree.tag_configure("matched",   foreground=T.SUCCESS)
        self.tree.tag_configure("unmatched", foreground=T.ERROR)
        self.tree.tag_configure("applied",   foreground=T.ACCENT)
        self.tree.tag_configure("even",      background=T.SURFACE)
        self.tree.tag_configure("odd",       background=T.BG)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

    def _setup_drag_drop(self):
        """tkinterdnd2가 있으면 드래그 앤 드롭 등록, 없으면 건너뜀"""
        if DND_AVAILABLE:
            self.tree.drop_target_register(DND_FILES)
            self.tree.dnd_bind("<<Drop>>", self._on_drop)
            # 드롭 힌트 표시
            self.tree.heading("filename",
                              text="파일명  (파일을 여기에 드래그하세요 🎵)")

    def _on_drop(self, event):
        """tkinterdnd2 드롭 이벤트 처리 - 경로에 공백 포함 가능"""
        raw = event.data or ""
        # tkinterdnd2 는 공백 포함 경로를 {}로 감쌈
        paths = re.findall(r'\{([^}]+)\}|([^\s{}]+)', raw)
        paths = [p[0] or p[1] for p in paths if p[0] or p[1]]
        # Windows 경로 자동 변환
        converted = []
        for p in paths:
            if len(p) > 2 and p[1] == ":":
                try:
                    r = subprocess.run(["wslpath", p],
                                       capture_output=True, timeout=3)
                    if r.returncode == 0:
                        p = r.stdout.decode("utf-8", errors="replace").strip()
                except Exception:
                    pass
            converted.append(p)
        self._add_path_list(converted)

    # ── 버튼 핸들러 ───────────────────────────
    def _add_files(self):
        """주소창이 있는 커스텀 파일 선택 대화상자 열기"""
        dlg = CustomFileDialog(self, initial_dir=self._last_dir)
        self.wait_window(dlg)
        paths = dlg.get_files()
        if paths:
            self._last_dir = Path(paths[0]).parent
            self._add_path_list(paths)

    def _add_folder(self):
        """주소창이 있는 커스텀 대화상자로 폴더 내 MP3 전체 추가"""
        dlg = CustomFileDialog(self, initial_dir=self._last_dir)
        # 폴더 확인 버튼 대신, 열리면 MP3 전체 선택 후 확인
        dlg.title("폴더 내 MP3 파일 추가 — 폴더를 이동 후 [MP3 전체 선택] → [확인]")
        self.wait_window(dlg)
        paths = dlg.get_files()
        if paths:
            self._last_dir = Path(paths[0]).parent
            self._add_path_list(paths)

    def _remove_selected(self):
        for iid in self.tree.selection():
            self.tree.delete(iid)
            self._file_paths.pop(iid, None)
        self._notify_changed()

    def _clear_all(self):
        self.tree.delete(*self.tree.get_children())
        self._file_paths.clear()
        self._notify_changed()

    def _auto_match(self):
        """자동 매칭 요청 - 외부 콜백으로 위임"""
        if self._on_files_changed:
            self._on_files_changed("auto_match")

    def _add_path_list(self, paths: List[str]):
        handler = MP3Handler()
        existing = set(self._file_paths.values())
        count = len(self.tree.get_children())

        for path in paths:
            if path in existing:
                continue
            p = Path(path)
            if not p.suffix.lower() == ".mp3":
                continue

            meta = handler.read_metadata(str(p))
            iid = f"mp3_{count}"
            tag = "even" if count % 2 == 0 else "odd"
            self.tree.insert(
                "", "end", iid=iid,
                values=(
                    p.name,
                    meta.get("track_number", ""),
                    meta.get("title", ""),
                    meta.get("artist", ""),
                    "없음",
                ),
                tags=(tag,),
            )
            self._file_paths[iid] = str(p)
            existing.add(str(p))
            count += 1

        self._notify_changed()

    def _notify_changed(self):
        if self._on_files_changed:
            self._on_files_changed("files_changed")

    # ── 공개 API ──────────────────────────────
    def get_file_paths(self) -> List[str]:
        """현재 목록의 모든 파일 경로를 순서대로 반환"""
        return [
            self._file_paths[iid]
            for iid in self.tree.get_children()
            if iid in self._file_paths
        ]

    def set_match_result(self, iid: str, track_number: int, status: str, status_type: str):
        """
        파일 행의 매칭 결과를 갱신한다.
        status_type: 'matched' | 'unmatched'
        """
        if not self.tree.exists(iid):
            return
        vals = list(self.tree.item(iid, "values"))
        vals[1] = track_number
        vals[4] = status
        tags = [t for t in self.tree.item(iid, "tags")
                if t not in ("matched", "unmatched", "applied")]
        tags.append(status_type)
        self.tree.item(iid, values=vals, tags=tags)

    def mark_applied(self, iid: str):
        tags = [t for t in self.tree.item(iid, "tags")
                if t not in ("matched", "unmatched", "applied")]
        tags.append("applied")
        self.tree.item(iid, tags=tags)

    def get_iids(self) -> List[str]:
        return list(self.tree.get_children())

    def get_path_by_iid(self, iid: str) -> Optional[str]:
        return self._file_paths.get(iid)


# ─────────────────────────────────────────────
# StatusBar - 최하단 상태바
# ─────────────────────────────────────────────
class StatusBar(ttk.Frame):
    """
    진행률 표시바 + 상태 메시지 + 통계 카운터
    레이아웃: grid (3열)
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, style="Panel.TFrame", **kwargs)
        self._build()

    def _build(self):
        T = Theme
        self.grid_columnconfigure(1, weight=1)

        # 상태 아이콘 + 메시지
        self._status_var = tk.StringVar(value="준비")
        self._status_label = ttk.Label(
            self,
            textvariable=self._status_var,
            style="Status.TLabel",
            anchor="w",
        )
        self._status_label.grid(row=0, column=0, sticky="w", padx=(8, 4), pady=4)

        # 진행바
        self._progress_var = tk.DoubleVar(value=0)
        self._progress = ttk.Progressbar(
            self,
            variable=self._progress_var,
            maximum=100,
            length=200,
        )
        self._progress.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        # 우측 통계 카운터
        self._stats_var = tk.StringVar(value="")
        ttk.Label(
            self,
            textvariable=self._stats_var,
            style="Status.TLabel",
            anchor="e",
        ).grid(row=0, column=2, sticky="e", padx=(4, 12), pady=4)

    # ── 공개 API ──────────────────────────────
    def set_status(self, message: str, kind: str = "info"):
        """
        kind: 'info' | 'success' | 'error' | 'warning'
        """
        prefix = {"info": "●", "success": "✔", "error": "✖", "warning": "⚠"}.get(kind, "●")
        color  = {
            "info":    Theme.TEXT_SUB,
            "success": Theme.SUCCESS,
            "error":   Theme.ERROR,
            "warning": Theme.WARNING,
        }.get(kind, Theme.TEXT_SUB)
        self._status_var.set(f"  {prefix}  {message}")
        self._status_label.configure(foreground=color)

    def set_progress(self, value: float, maximum: float = 100):
        if maximum > 0:
            self._progress_var.set(value / maximum * 100)

    def reset_progress(self):
        self._progress_var.set(0)

    def set_stats(self, matched: int, total: int, applied: int):
        self._stats_var.set(f"매칭 {matched}/{total}  |  적용 {applied}")


# ─────────────────────────────────────────────
# UrlBar - 상단 URL 입력 + 크롤링 버튼
# ─────────────────────────────────────────────
class UrlBar(ttk.Frame):
    """
    URL Entry + 크롤링 시작 버튼 + 초기화 버튼
    레이아웃: pack (horizontal)
    """

    def __init__(self, parent, on_crawl=None, **kwargs):
        super().__init__(parent, style="Panel.TFrame", **kwargs)
        self._on_crawl = on_crawl
        self._build()

    def _build(self):
        T = Theme

        ttk.Label(
            self,
            text="멜론 앨범 URL",
            style="TLabel",
            background=T.PANEL,
        ).pack(side="left", padx=(12, 6), pady=8)

        self._url_var = tk.StringVar()
        self._entry = ttk.Entry(
            self,
            textvariable=self._url_var,
            width=60,
            font=Theme.FONT_MONO,
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 6), pady=8)
        self._entry.bind("<Return>", lambda e: self._do_crawl())

        # 붙여넣기 단축키 힌트
        self._entry.insert(0, "https://www.melon.com/album/detail.htm?albumId=...")

        self._crawl_btn = ttk.Button(
            self,
            text="크롤링 시작",
            style="Accent.TButton",
            command=self._do_crawl,
        )
        self._crawl_btn.pack(side="left", padx=(0, 6), pady=8)

        ttk.Button(
            self,
            text="초기화",
            style="TButton",
            command=self._do_clear,
        ).pack(side="left", padx=(0, 12), pady=8)

    def _do_crawl(self):
        url = self._url_var.get().strip()
        if not url or url.startswith("https://www.melon.com/album"):
            # 플레이스홀더 텍스트인 경우
            if "albumId=..." in url:
                messagebox.showwarning("URL 필요", "멜론 앨범 URL을 입력해 주세요.")
                return
        if self._on_crawl:
            self._on_crawl(url)

    def _do_clear(self):
        self._url_var.set("")

    # ── 공개 API ──────────────────────────────
    def get_url(self) -> str:
        return self._url_var.get().strip()

    def set_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self._entry.configure(state=state)
        self._crawl_btn.configure(state=state)


# ─────────────────────────────────────────────
# ActionBar - 하단 메타데이터 적용 버튼 바
# ─────────────────────────────────────────────
class ActionBar(ttk.Frame):
    """
    '선택 항목 적용' / '매칭된 항목 모두 적용' / '건너뛰기' 버튼
    """

    def __init__(self, parent,
                 on_apply_selected=None,
                 on_apply_all=None,
                 on_skip=None,
                 **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self._on_apply_selected = on_apply_selected
        self._on_apply_all = on_apply_all
        self._on_skip = on_skip
        self._build()

    def _build(self):
        T = Theme
        self.configure(padding=(10, 6))

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=(0, 8))

        btn_row = ttk.Frame(self, style="Card.TFrame")
        btn_row.pack(fill="x")

        ttk.Button(
            btn_row,
            text="선택 항목 적용",
            style="Accent.TButton",
            command=lambda: self._on_apply_selected and self._on_apply_selected(),
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            btn_row,
            text="매칭된 항목 모두 적용",
            style="Accent.TButton",
            command=lambda: self._on_apply_all and self._on_apply_all(),
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            btn_row,
            text="건너뛰기",
            style="TButton",
            command=lambda: self._on_skip and self._on_skip(),
        ).pack(side="left")

        # 우측: 적용 옵션 체크박스
        opts_frame = ttk.Frame(btn_row, style="Card.TFrame")
        opts_frame.pack(side="right")

        self._backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            opts_frame,
            text="원본 백업",
            variable=self._backup_var,
        ).pack(side="left", padx=6)

        self._cover_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            opts_frame,
            text="앨범아트 포함",
            variable=self._cover_var,
        ).pack(side="left", padx=6)

    # ── 공개 API ──────────────────────────────
    def get_options(self) -> dict:
        return {
            "backup":       self._backup_var.get(),
            "include_cover": self._cover_var.get(),
        }


# ─────────────────────────────────────────────
# CustomFileDialog - 주소창이 있는 MP3 파일 선택 대화상자
# ─────────────────────────────────────────────
class CustomFileDialog(tk.Toplevel):
    """
    상단에 주소창(경로 직접 입력)이 있는 MP3 파일 선택 대화상자.
    - 주소창에 경로를 직접 입력하고 Enter / [이동] 버튼으로 이동
    - 폴더 더블클릭으로 탐색, MP3 파일 클릭으로 선택
    - [MP3 전체 선택] 버튼으로 현재 폴더의 모든 MP3 선택
    """

    def __init__(self, parent, initial_dir: Optional[Path] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.title("MP3 파일 선택")
        self.geometry("760x520")
        self.minsize(500, 360)
        self.configure(bg=Theme.BG)
        self.resizable(True, True)
        self.grab_set()

        self._selected: List[str] = []
        self._current_dir: Path = Path(initial_dir) if initial_dir else _get_default_dir()
        self._entries: List[tuple] = []   # (kind, Path)

        self._build()
        self._load_dir(self._current_dir)

    # ── 레이아웃 ──────────────────────────────
    def _build(self):
        T = Theme

        # 주소창 바
        addr_bar = tk.Frame(self, bg=T.PANEL, padx=8, pady=6)
        addr_bar.pack(fill="x")

        tk.Label(
            addr_bar, text="주소", bg=T.PANEL, fg=T.TEXT_SUB,
            font=T.FONT_KR_SM,
        ).pack(side="left", padx=(0, 6))

        self._path_var = tk.StringVar()
        self._path_entry = ttk.Entry(
            addr_bar, textvariable=self._path_var,
            font=Theme.FONT_MONO,
        )
        self._path_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._path_entry.bind("<Return>", self._on_path_enter)

        ttk.Button(addr_bar, text="이동", width=6,
                   command=self._on_path_enter).pack(side="left", padx=(0, 4))
        ttk.Button(addr_bar, text="↑ 상위", width=7,
                   command=self._go_up).pack(side="left")

        # 파일 목록
        list_frame = tk.Frame(self, bg=T.SURFACE)
        list_frame.pack(fill="both", expand=True, padx=8, pady=(6, 4))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self._listbox = tk.Listbox(
            list_frame,
            selectmode="extended",
            bg=T.SURFACE,
            fg=T.TEXT,
            selectbackground=T.SELECT_BG,
            selectforeground=T.SELECT_FG,
            font=T.FONT_KR,
            activestyle="none",
            relief="flat",
            borderwidth=0,
        )
        vsb = ttk.Scrollbar(list_frame, orient="vertical",
                            command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=vsb.set)

        self._listbox.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self._listbox.bind("<Double-1>", self._on_double_click)
        self._listbox.bind("<<ListboxSelect>>", self._update_count)

        # 하단 바
        bottom = tk.Frame(self, bg=Theme.PANEL, padx=8, pady=6)
        bottom.pack(fill="x")

        self._count_var = tk.StringVar(value="MP3 파일을 선택하세요")
        tk.Label(
            bottom, textvariable=self._count_var,
            bg=Theme.PANEL, fg=Theme.TEXT_SUB, font=Theme.FONT_KR_SM,
        ).pack(side="left")

        ttk.Button(bottom, text="취소",
                   command=self.destroy).pack(side="right", padx=(4, 0))
        ttk.Button(bottom, text="확인", style="Accent.TButton",
                   command=self._confirm).pack(side="right", padx=4)
        ttk.Button(bottom, text="MP3 전체 선택",
                   command=self._select_all_mp3).pack(side="right", padx=4)

    # ── 내부 동작 ─────────────────────────────
    def _load_dir(self, path: Path):
        self._current_dir = path
        self._path_var.set(str(path))
        self._listbox.delete(0, "end")
        self._entries = []

        # 상위 폴더 항목
        if path.parent != path:
            self._listbox.insert("end", "  📁  ..")
            self._entries.append(("dir", path.parent))

        try:
            items = sorted(
                path.iterdir(),
                key=lambda p: (p.is_file(), p.name.lower()),
            )
            for item in items:
                if item.is_dir() and not item.name.startswith("."):
                    self._listbox.insert("end", f"  📁  {item.name}/")
                    self._entries.append(("dir", item))
                elif item.suffix.lower() == ".mp3":
                    self._listbox.insert("end", f"  🎵  {item.name}")
                    self._entries.append(("mp3", item))
        except PermissionError:
            pass

        self._update_count()

    def _on_path_enter(self, _event=None):
        raw = self._path_var.get().strip()
        # Windows 경로(C:\...) 를 WSL 경로로 자동 변환
        if raw and raw[1:3] == ":\\":
            try:
                result = subprocess.run(
                    ["wslpath", raw], capture_output=True, timeout=3
                )
                if result.returncode == 0:
                    raw = result.stdout.decode("utf-8", errors="replace").strip()
            except Exception:
                pass
        path = Path(raw)
        if path.is_dir():
            self._load_dir(path)
        elif path.is_file() and path.suffix.lower() == ".mp3":
            self._load_dir(path.parent)
        else:
            messagebox.showwarning("경로 오류",
                                   f"유효한 경로가 아닙니다:\n{raw}", parent=self)

    def _go_up(self):
        parent = self._current_dir.parent
        if parent != self._current_dir:
            self._load_dir(parent)

    def _on_double_click(self, _event=None):
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self._entries) and self._entries[idx][0] == "dir":
            self._load_dir(self._entries[idx][1])

    def _select_all_mp3(self):
        self._listbox.selection_clear(0, "end")
        for i, (kind, _) in enumerate(self._entries):
            if kind == "mp3":
                self._listbox.selection_set(i)
        self._update_count()

    def _update_count(self, _event=None):
        sel = self._listbox.curselection()
        n = sum(
            1 for i in sel
            if i < len(self._entries) and self._entries[i][0] == "mp3"
        )
        self._count_var.set(f"MP3 파일 {n}개 선택됨" if n else "MP3 파일을 선택하세요")

    def _confirm(self):
        sel = self._listbox.curselection()
        self._selected = [
            str(self._entries[i][1])
            for i in sel
            if i < len(self._entries) and self._entries[i][0] == "mp3"
        ]
        self.destroy()

    # ── 공개 API ──────────────────────────────
    def get_files(self) -> List[str]:
        return self._selected


# ─────────────────────────────────────────────
# SingleFileTab - 단일 파일 탭
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# MultiFileTab - 다중 파일 탭 (기존 UI 그대로)
# ─────────────────────────────────────────────
class MultiFileTab(ttk.Frame):
    """
    다수 MP3 파일의 메타데이터를 일괄 변경하는 탭.
    기존 MainWindow의 레이아웃과 동일.
    """

    def __init__(self, parent, status_bar: "StatusBar", **kwargs):
        super().__init__(parent, style="TFrame", **kwargs)
        self._status_bar = status_bar
        self._album: Optional[AlbumInfo] = None
        self._match_map: Dict[str, int] = {}
        self._stats = {"matched": 0, "total": 0, "applied": 0}
        self._build()

    def _build(self):
        # ── URL 입력바 ─────────────────────────
        self.url_bar = UrlBar(self, on_crawl=self._start_crawl)
        self.url_bar.pack(side="top", fill="x")

        ttk.Separator(self, orient="horizontal").pack(side="top", fill="x")

        # ── 액션바 (bottom) ────────────────────
        self.action_bar = ActionBar(
            self,
            on_apply_selected=self._apply_selected,
            on_apply_all=self._apply_all,
            on_skip=self._skip,
        )
        self.action_bar.pack(side="bottom", fill="x", padx=8, pady=(0, 4))

        # ── 메인 PanedWindow ───────────────────
        outer_pane = ttk.PanedWindow(self, orient="vertical")
        outer_pane.pack(side="top", fill="both", expand=True, padx=8, pady=8)

        # 상단 수평 PanedWindow
        top_pane = ttk.PanedWindow(outer_pane, orient="horizontal")

        self.album_panel = AlbumInfoPanel(top_pane)
        top_pane.add(self.album_panel, weight=0)
        self.album_panel.configure(width=220)

        self.track_tree = TrackTreeview(top_pane)
        top_pane.add(self.track_tree, weight=3)

        outer_pane.add(top_pane, weight=2)

        # 하단: MP3 파일 패널
        self.mp3_panel = MP3FilePanel(
            outer_pane,
            on_files_changed=self._on_files_changed,
        )
        outer_pane.add(self.mp3_panel, weight=1)

        # sash 초기 위치
        self.after(100, lambda: outer_pane.sashpos(0, 380))

    # ─────────────────────────────────────────
    # 크롤링 로직
    # ─────────────────────────────────────────
    def _start_crawl(self, url: str):
        if not url:
            messagebox.showwarning("URL 필요", "멜론 앨범 URL을 입력해 주세요.")
            return

        self.url_bar.set_enabled(False)
        self._status_bar.set_status("크롤링 중...", "info")
        self._status_bar.set_progress(0)
        self.album_panel.clear()
        self.track_tree.clear()

        threading.Thread(
            target=self._crawl_worker, args=(url,), daemon=True,
        ).start()

    def _crawl_worker(self, url: str):
        try:
            crawler = MelonCrawler()
            album = crawler.crawl_album(url)
            self.after(0, self._on_crawl_success, album)
        except Exception as exc:
            self.after(0, self._on_crawl_error, str(exc))

    def _on_crawl_success(self, album: AlbumInfo):
        self._album = album
        self.album_panel.load_album(album)
        self.track_tree.load_tracks(album.tracks)
        self._status_bar.set_status(
            f"크롤링 완료 — {album.album_name} ({len(album.tracks)}곡)", "success"
        )
        self._status_bar.set_progress(100)
        self.url_bar.set_enabled(True)
        self._update_stats()

    def _on_crawl_error(self, msg: str):
        self._status_bar.set_status(f"크롤링 실패: {msg}", "error")
        self._status_bar.reset_progress()
        self.url_bar.set_enabled(True)
        messagebox.showerror(
            "크롤링 오류",
            f"앨범 정보를 가져오는 중 오류가 발생했습니다.\n\n{msg}",
        )

    # ─────────────────────────────────────────
    # 매칭 로직
    # ─────────────────────────────────────────
    def _on_files_changed(self, event: str):
        if event == "auto_match":
            self._auto_match()
        self._update_stats()

    def _auto_match(self):
        """파일명 기반 자동 매칭 (트랙번호 추출)"""
        if not self._album:
            messagebox.showinfo("앨범 없음", "먼저 멜론 앨범을 크롤링해 주세요.")
            return

        self._match_map.clear()
        matched_count = 0
        iids = self.mp3_panel.get_iids()
        total = len(iids)

        track_by_num = {t.track_number: t for t in self._album.tracks}
        track_by_title = {t.title.lower(): t for t in self._album.tracks}

        for iid in iids:
            path = self.mp3_panel.get_path_by_iid(iid)
            if not path:
                continue
            stem = Path(path).stem

            # 파일명에서 트랙번호 추출 시도
            m = re.match(r"^(\d+)[.\s_-]", stem)
            if m:
                num = int(m.group(1))
                if num in track_by_num:
                    self._match_map[iid] = num
                    self.mp3_panel.set_match_result(iid, num, "매칭됨", "matched")
                    self.track_tree.set_track_status(num, "매칭됨", "matched")
                    matched_count += 1
                    continue

            # 제목 유사도 매칭
            normalized = re.sub(r"[\s\-_\(\)\[\]]", "", stem).lower()
            best_match = None
            for title_lower, track in track_by_title.items():
                norm_title = re.sub(r"[\s\-_\(\)\[\]]", "", title_lower)
                if norm_title and norm_title in normalized:
                    best_match = track
                    break

            if best_match:
                self._match_map[iid] = best_match.track_number
                self.mp3_panel.set_match_result(
                    iid, best_match.track_number, "매칭됨", "matched"
                )
                self.track_tree.set_track_status(
                    best_match.track_number, "매칭됨", "matched"
                )
                matched_count += 1
            else:
                self.mp3_panel.set_match_result(iid, 0, "미매칭", "unmatched")

        self._status_bar.set_status(
            f"자동 매칭 완료 — {matched_count}/{total}개 매칭", "success"
        )
        self._update_stats(matched=matched_count, total=total)

    # ─────────────────────────────────────────
    # 적용 로직
    # ─────────────────────────────────────────
    def _apply_selected(self):
        selected = self.mp3_panel.tree.selection()
        if not selected:
            messagebox.showinfo("선택 없음", "적용할 파일을 선택해 주세요.")
            return
        self._apply_iids(list(selected))

    def _apply_all(self):
        iids = [i for i in self.mp3_panel.get_iids() if i in self._match_map]
        if not iids:
            messagebox.showinfo(
                "매칭 없음",
                "매칭된 파일이 없습니다. 먼저 자동 매칭을 실행해 주세요.",
            )
            return
        self._apply_iids(iids)

    def _skip(self):
        self._status_bar.set_status("건너뜀", "warning")

    def _apply_iids(self, iids: List[str]):
        if not self._album:
            messagebox.showwarning("앨범 없음", "먼저 멜론 앨범을 크롤링해 주세요.")
            return

        opts = self.action_bar.get_options()
        handler = MP3Handler()
        track_by_num = {t.track_number: t for t in self._album.tracks}
        applied = 0
        errors = []

        for iid in iids:
            track_num = self._match_map.get(iid)
            if track_num is None:
                continue
            track = track_by_num.get(track_num)
            if not track:
                continue
            path = self.mp3_panel.get_path_by_iid(iid)
            if not path:
                continue

            try:
                if opts["backup"]:
                    backup_path = Path(path).with_suffix(".mp3.bak")
                    if not backup_path.exists():
                        shutil.copy2(path, backup_path)

                handler.write_metadata(
                    filepath=path,
                    title=track.title,
                    artist=track.artist,
                    album=track.album,
                    album_artist=track.album_artist,
                    genre=track.genre,
                    track_number=track.track_number,
                    cover_data=self._album.cover_data if opts["include_cover"] else None,
                )
                self.mp3_panel.mark_applied(iid)
                self.track_tree.set_track_status(track_num, "적용됨", "matched")
                applied += 1
            except Exception as exc:
                errors.append(f"{Path(path).name}: {exc}")

        self._stats["applied"] += applied
        self._update_stats()
        self._status_bar.set_status(f"적용 완료 — {applied}개 파일 처리됨", "success")

        if errors:
            messagebox.showerror(
                "일부 오류",
                "다음 파일에서 오류가 발생했습니다:\n\n" + "\n".join(errors[:10]),
            )

    # ─────────────────────────────────────────
    # 통계 업데이트
    # ─────────────────────────────────────────
    def _update_stats(self, matched: int = None, total: int = None):
        if matched is not None:
            self._stats["matched"] = matched
        if total is not None:
            self._stats["total"] = total
        else:
            self._stats["total"] = len(self.mp3_panel.get_iids())

        self._status_bar.set_stats(
            self._stats["matched"],
            self._stats["total"],
            self._stats["applied"],
        )


# ─────────────────────────────────────────────
# MainWindow - 메인 애플리케이션 윈도우
# ─────────────────────────────────────────────
_BaseWindow = TkinterDnD.Tk if DND_AVAILABLE else tk.Tk


class MainWindow(_BaseWindow):
    """
    Melon MP3 Tagger 메인 윈도우

    레이아웃 구조 (pack 기반):
    ┌──────────────────────────────────────────┐
    │  Notebook                                │
    │  ├── 단일 파일 탭 (SingleFileTab)        │
    │  └── 다중 파일 탭 (MultiFileTab)         │
    ├──────────────────────────────────────────┤
    │  StatusBar (bottom, fixed)               │
    └──────────────────────────────────────────┘
    """

    WIN_W, WIN_H  = 1200, 800
    WIN_MIN_W     = 900
    WIN_MIN_H     = 650

    def __init__(self):
        super().__init__()
        self._setup_window()
        apply_dark_theme(self)
        self._build_layout()
        self._apply_root_bg()

    def _setup_window(self):
        self.title("Melon MP3 Tagger")
        self.geometry(f"{self.WIN_W}x{self.WIN_H}")
        self.minsize(self.WIN_MIN_W, self.WIN_MIN_H)
        try:
            self.iconbitmap("assets/icon.ico")
        except Exception:
            pass

    def _apply_root_bg(self):
        self.configure(bg=Theme.BG)

    def _build_layout(self):
        # ── 상태바 (최하단, 고정) ───────────────
        self.status_bar = StatusBar(self)
        self.status_bar.pack(side="bottom", fill="x")

        # ── Notebook (메인 영역) ────────────────
        notebook = ttk.Notebook(self)
        notebook.pack(side="top", fill="both", expand=True, padx=6, pady=(6, 0))

        # 단일 파일 탭
        self.single_tab = SingleFileTab(notebook, status_bar=self.status_bar)
        notebook.add(self.single_tab, text="  단일 파일  ")

        # 다중 파일 탭
        self.multi_tab = MultiFileTab(notebook, status_bar=self.status_bar)
        notebook.add(self.multi_tab, text="  다중 파일  ")


# ─────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────
def main():
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()

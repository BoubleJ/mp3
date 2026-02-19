"""
다중 파일 탭 (다수 MP3 일괄 메타데이터 변경)
"""

import re
import shutil
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional, Dict, List

from src.models import AlbumInfo, TrackInfo
from src.api import MelonCrawler
from src.services import MP3Handler
from src.ui.theme import Theme
from src.ui.widgets.album_panel import AlbumInfoPanel
from src.ui.widgets.track_tree import TrackTreeview
from src.ui.widgets.mp3_panel import MP3FilePanel
from src.ui.widgets.url_bar import UrlBar
from src.ui.widgets.action_bar import ActionBar
from src.ui.widgets.status_bar import StatusBar

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

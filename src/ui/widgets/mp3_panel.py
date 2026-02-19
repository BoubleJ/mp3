"""
MP3 파일 목록 패널 (Treeview + 파일/폴더 추가, 자동 매칭)
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from tkinter import ttk

from src.services import MP3Handler
from src.ui.theme import Theme, _get_default_dir, DND_AVAILABLE, DND_FILES
from src.ui.widgets.file_dialog import CustomFileDialog

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

"""
하단 메타데이터 적용 버튼 바
"""

import tkinter as tk
from tkinter import ttk

from src.ui.theme import Theme


class ActionBar(ttk.Frame):
    """'선택 항목 적용' / '매칭된 항목 모두 적용' / '건너뛰기' 버튼"""

    def __init__(self, parent, on_apply_selected=None, on_apply_all=None, on_skip=None, **kwargs):
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
        ttk.Button(btn_row, text="선택 항목 적용", style="Accent.TButton", command=lambda: self._on_apply_selected and self._on_apply_selected()).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="매칭된 항목 모두 적용", style="Accent.TButton", command=lambda: self._on_apply_all and self._on_apply_all()).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="건너뛰기", style="TButton", command=lambda: self._on_skip and self._on_skip()).pack(side="left")
        opts_frame = ttk.Frame(btn_row, style="Card.TFrame")
        opts_frame.pack(side="right")
        self._backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_frame, text="원본 백업", variable=self._backup_var).pack(side="left", padx=6)
        self._cover_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_frame, text="앨범아트 포함", variable=self._cover_var).pack(side="left", padx=6)

    def get_options(self) -> dict:
        return {"backup": self._backup_var.get(), "include_cover": self._cover_var.get()}

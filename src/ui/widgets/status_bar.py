"""
최하단 상태바 (진행률 + 메시지 + 통계)
"""

import tkinter as tk
from tkinter import ttk

from src.ui.theme import Theme


class StatusBar(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, style="Panel.TFrame", **kwargs)
        self._build()

    def _build(self):
        T = Theme
        self.grid_columnconfigure(1, weight=1)
        self._status_var = tk.StringVar(value="준비")
        self._status_label = ttk.Label(self, textvariable=self._status_var, style="Status.TLabel", anchor="w")
        self._status_label.grid(row=0, column=0, sticky="w", padx=(8, 4), pady=4)
        self._progress_var = tk.DoubleVar(value=0)
        self._progress = ttk.Progressbar(self, variable=self._progress_var, maximum=100, length=200)
        self._progress.grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        self._stats_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self._stats_var, style="Status.TLabel", anchor="e").grid(row=0, column=2, sticky="e", padx=(4, 12), pady=4)

    def set_status(self, message: str, kind: str = "info"):
        prefix = {"info": "●", "success": "✔", "error": "✖", "warning": "⚠"}.get(kind, "●")
        color = {"info": Theme.TEXT_SUB, "success": Theme.SUCCESS, "error": Theme.ERROR, "warning": Theme.WARNING}.get(kind, Theme.TEXT_SUB)
        self._status_var.set(f"  {prefix}  {message}")
        self._status_label.configure(foreground=color)

    def set_progress(self, value: float, maximum: float = 100):
        if maximum > 0:
            self._progress_var.set(value / maximum * 100)

    def reset_progress(self):
        self._progress_var.set(0)

    def set_stats(self, matched: int, total: int, applied: int):
        self._stats_var.set(f"매칭 {matched}/{total}  |  적용 {applied}")

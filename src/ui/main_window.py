"""
메인 애플리케이션 윈도우
"""

import tkinter as tk
from tkinter import ttk

from src.ui.theme import Theme, apply_dark_theme, DND_AVAILABLE
from src.ui.widgets import StatusBar, SingleFileTab, MultiFileTab

try:
    from tkinterdnd2 import TkinterDnD
    _BaseWindow = TkinterDnD.Tk
except ImportError:
    _BaseWindow = tk.Tk

# ─────────────────────────────────────────────
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

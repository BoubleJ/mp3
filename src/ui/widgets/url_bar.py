"""
URL 입력 + 크롤링 버튼 바
"""

import tkinter as tk
from tkinter import ttk, messagebox

from src.ui.theme import Theme


class UrlBar(ttk.Frame):
    """URL Entry + 크롤링 시작 버튼 + 초기화 버튼. 레이아웃: pack (horizontal)"""

    def __init__(self, parent, on_crawl=None, **kwargs):
        super().__init__(parent, style="Panel.TFrame", **kwargs)
        self._on_crawl = on_crawl
        self._build()

    def _build(self):
        T = Theme
        ttk.Label(self, text="멜론 앨범 URL", style="TLabel", background=T.PANEL).pack(side="left", padx=(12, 6), pady=8)
        self._url_var = tk.StringVar()
        self._entry = ttk.Entry(self, textvariable=self._url_var, width=60, font=Theme.FONT_MONO)
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 6), pady=8)
        self._entry.bind("<Return>", lambda e: self._do_crawl())
        self._entry.insert(0, "https://www.melon.com/album/detail.htm?albumId=...")
        self._crawl_btn = ttk.Button(self, text="크롤링 시작", style="Accent.TButton", command=self._do_crawl)
        self._crawl_btn.pack(side="left", padx=(0, 6), pady=8)
        ttk.Button(self, text="초기화", style="TButton", command=self._do_clear).pack(side="left", padx=(0, 12), pady=8)

    def _do_crawl(self):
        url = self._url_var.get().strip()
        if not url or url.startswith("https://www.melon.com/album"):
            if "albumId=..." in url:
                messagebox.showwarning("URL 필요", "멜론 앨범 URL을 입력해 주세요.")
                return
        if self._on_crawl:
            self._on_crawl(url)

    def _do_clear(self):
        self._url_var.set("")

    def get_url(self) -> str:
        return self._url_var.get().strip()

    def set_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self._entry.configure(state=state)
        self._crawl_btn.configure(state=state)

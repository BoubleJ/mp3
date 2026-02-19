"""
앨범 정보 패널 (앨범아트 + 앨범명/아티스트/장르/발매일)
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict
from io import BytesIO

from src.models import AlbumInfo
from src.ui.theme import Theme, PIL_AVAILABLE

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None


class AlbumInfoPanel(ttk.Frame):
    """
    앨범아트(180x180) + 앨범명/아티스트/장르/발매일 텍스트 표시
    레이아웃: pack() 사용 (수직 스택)
    """

    ART_SIZE = 180

    def __init__(self, parent, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self._photo_ref = None
        self._build()

    def _build(self):
        T = Theme

        art_wrapper = tk.Frame(
            self, bg=T.PANEL,
            width=self.ART_SIZE, height=self.ART_SIZE,
        )
        art_wrapper.pack(pady=(16, 10))
        art_wrapper.pack_propagate(False)

        self._art_label = tk.Label(
            art_wrapper,
            bg=T.PANEL,
            text="앨범아트\n없음",
            fg=T.TEXT_DIM,
            font=Theme.FONT_KR_SM,
        )
        self._art_label.place(relx=0.5, rely=0.5, anchor="center")

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
            ttk.Label(row, text=f"{label_text}", style="Accent.TLabel", width=7, anchor="w").pack(side="left")
            var = tk.StringVar(value="—")
            self._info_vars[key] = var
            ttk.Label(row, textvariable=var, style="Sub.TLabel", wraplength=140, justify="left", anchor="w").pack(side="left", fill="x", expand=True)

        badge_frame = ttk.Frame(self, style="Card.TFrame")
        badge_frame.pack(fill="x", padx=14, pady=(0, 14))
        ttk.Label(badge_frame, text="트랙 수", style="Accent.TLabel", width=7, anchor="w").pack(side="left")
        self._track_count_var = tk.StringVar(value="—")
        ttk.Label(badge_frame, textvariable=self._track_count_var, style="Sub.TLabel").pack(side="left")

    def load_album(self, album: AlbumInfo):
        self._info_vars["album_name"].set(album.album_name or "—")
        self._info_vars["album_artist"].set(album.album_artist or "—")
        self._info_vars["genre"].set(album.genre or "—")
        self._info_vars["release_date"].set(album.release_date or "—")
        self._track_count_var.set(f"{len(album.tracks)}곡")
        if album.cover_data and PIL_AVAILABLE and Image is not None and ImageTk is not None:
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

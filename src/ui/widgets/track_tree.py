"""
트랙 목록 Treeview (멜론 크롤링 결과)
"""

from tkinter import ttk
from typing import List, Optional

from src.models import TrackInfo
from src.ui.theme import Theme


class TrackTreeview(ttk.Frame):
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
        ttk.Label(self, text="트랙 목록", style="Header.TLabel", background=T.SURFACE).pack(anchor="w", padx=12, pady=(10, 6))
        tree_frame = ttk.Frame(self, style="Card.TFrame")
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        col_ids = list(self.COLS.keys())
        self.tree = ttk.Treeview(tree_frame, columns=col_ids, show="headings", selectmode="browse")
        for col_id, cfg in self.COLS.items():
            self.tree.heading(col_id, text=cfg["label"], anchor=cfg["anchor"])
            stretch = col_id == "title"
            self.tree.column(col_id, width=cfg["width"], minwidth=cfg["width"] // 2, anchor=cfg["anchor"], stretch=stretch)
        self.tree.tag_configure("even", background=T.SURFACE)
        self.tree.tag_configure("odd", background=T.BG)
        self.tree.tag_configure("matched", foreground=T.SUCCESS)
        self.tree.tag_configure("unmatched", foreground=T.TEXT_DIM)
        self.tree.tag_configure("partial", foreground=T.WARNING)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

    def load_tracks(self, tracks: List[TrackInfo]):
        self.tree.delete(*self.tree.get_children())
        for i, track in enumerate(tracks):
            tag = "even" if i % 2 == 0 else "odd"
            vals = (track.track_number, track.title, track.artist, "대기")
            self.tree.insert("", "end", iid=str(track.track_number), values=vals, tags=(tag,))

    def set_track_status(self, track_number: int, status: str, status_type: str = ""):
        iid = str(track_number)
        if not self.tree.exists(iid):
            return
        vals = list(self.tree.item(iid, "values"))
        vals[3] = status
        current_tags = list(self.tree.item(iid, "tags"))
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

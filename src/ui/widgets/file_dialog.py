"""
주소창이 있는 MP3 파일 선택 대화상자
"""

import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import List, Optional

from src.ui.theme import Theme, _get_default_dir


class CustomFileDialog(tk.Toplevel):
    """상단에 주소창이 있는 MP3 파일 선택 대화상자."""

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
        self._entries: List[tuple] = []
        self._build()
        self._load_dir(self._current_dir)

    def _build(self):
        T = Theme
        addr_bar = tk.Frame(self, bg=T.PANEL, padx=8, pady=6)
        addr_bar.pack(fill="x")
        tk.Label(addr_bar, text="주소", bg=T.PANEL, fg=T.TEXT_SUB, font=T.FONT_KR_SM).pack(side="left", padx=(0, 6))
        self._path_var = tk.StringVar()
        self._path_entry = ttk.Entry(addr_bar, textvariable=self._path_var, font=Theme.FONT_MONO)
        self._path_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._path_entry.bind("<Return>", self._on_path_enter)
        ttk.Button(addr_bar, text="이동", width=6, command=self._on_path_enter).pack(side="left", padx=(0, 4))
        ttk.Button(addr_bar, text="↑ 상위", width=7, command=self._go_up).pack(side="left")
        list_frame = tk.Frame(self, bg=T.SURFACE)
        list_frame.pack(fill="both", expand=True, padx=8, pady=(6, 4))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self._listbox = tk.Listbox(list_frame, selectmode="extended", bg=T.SURFACE, fg=T.TEXT, selectbackground=T.SELECT_BG, selectforeground=T.SELECT_FG, font=T.FONT_KR, activestyle="none", relief="flat", borderwidth=0)
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=vsb.set)
        self._listbox.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self._listbox.bind("<Double-1>", self._on_double_click)
        self._listbox.bind("<<ListboxSelect>>", self._update_count)
        bottom = tk.Frame(self, bg=Theme.PANEL, padx=8, pady=6)
        bottom.pack(fill="x")
        self._count_var = tk.StringVar(value="MP3 파일을 선택하세요")
        tk.Label(bottom, textvariable=self._count_var, bg=Theme.PANEL, fg=Theme.TEXT_SUB, font=Theme.FONT_KR_SM).pack(side="left")
        ttk.Button(bottom, text="취소", command=self.destroy).pack(side="right", padx=(4, 0))
        ttk.Button(bottom, text="확인", style="Accent.TButton", command=self._confirm).pack(side="right", padx=4)
        ttk.Button(bottom, text="MP3 전체 선택", command=self._select_all_mp3).pack(side="right", padx=4)

    def _load_dir(self, path: Path):
        self._current_dir = path
        self._path_var.set(str(path))
        self._listbox.delete(0, "end")
        self._entries = []
        if path.parent != path:
            self._listbox.insert("end", "  ..")
            self._entries.append(("dir", path.parent))
        try:
            items = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            for item in items:
                if item.is_dir() and not item.name.startswith("."):
                    self._listbox.insert("end", f"  {item.name}/")
                    self._entries.append(("dir", item))
                elif item.suffix.lower() == ".mp3":
                    self._listbox.insert("end", f"  {item.name}")
                    self._entries.append(("mp3", item))
        except PermissionError:
            pass
        self._update_count()

    def _on_path_enter(self, _event=None):
        raw = self._path_var.get().strip()
        if raw and len(raw) >= 3 and raw[1:3] == ":\\":
            try:
                result = subprocess.run(["wslpath", raw], capture_output=True, timeout=3)
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
            messagebox.showwarning("경로 오류", f"유효한 경로가 아닙니다:\n{raw}", parent=self)

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
        n = sum(1 for i in sel if i < len(self._entries) and self._entries[i][0] == "mp3")
        self._count_var.set(f"MP3 파일 {n}개 선택됨" if n else "MP3 파일을 선택하세요")

    def _confirm(self):
        sel = self._listbox.curselection()
        self._selected = [str(self._entries[i][1]) for i in sel if i < len(self._entries) and self._entries[i][0] == "mp3"]
        self.destroy()

    def get_files(self) -> List[str]:
        return self._selected

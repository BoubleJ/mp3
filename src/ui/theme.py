"""
다크 테마·디자인 토큰 (색상, 폰트, ttk.Style)
옵션: PIL, tkinterdnd2 가용 여부
"""

import subprocess
import tkinter as tk
from tkinter import ttk
from pathlib import Path

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    DND_FILES = None


def _get_default_dir() -> Path:
    """WSL 환경이면 Windows 바탕화면, 아니면 홈 디렉토리를 반환한다."""
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", "echo %USERPROFILE%"],
            capture_output=True, timeout=3
        )
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


class Theme:
    BG         = "#1e1e2e"
    SURFACE    = "#181825"
    PANEL      = "#313244"
    BORDER     = "#45475a"
    ACCENT     = "#00C73C"
    ACCENT_DIM = "#009e30"
    TEXT       = "#cdd6f4"
    TEXT_SUB   = "#a6adc8"
    TEXT_DIM   = "#6c7086"
    ERROR      = "#f38ba8"
    SUCCESS    = "#a6e3a1"
    WARNING    = "#f9e2af"
    SELECT_BG  = "#1e3a2f"
    SELECT_FG  = "#00C73C"
    ENTRY_BG   = "#2a2a3e"

    FONT_KR    = ("맑은 고딕", 10)
    FONT_KR_SM = ("맑은 고딕", 9)
    FONT_KR_LG = ("맑은 고딕", 12, "bold")
    FONT_KR_H  = ("맑은 고딕", 14, "bold")
    FONT_MONO  = ("Consolas", 9)


def apply_dark_theme(root: tk.Tk) -> ttk.Style:
    """전체 ttk 위젯에 다크 테마를 적용한다."""
    style = ttk.Style(root)
    style.theme_use("clam")
    T = Theme

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

    style.configure("TFrame",    background=T.BG)
    style.configure("Card.TFrame", background=T.SURFACE, relief="flat")
    style.configure("Panel.TFrame", background=T.PANEL)

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

    style.configure("TLabel", background=T.BG, foreground=T.TEXT, font=T.FONT_KR)
    style.configure("Title.TLabel", background=T.SURFACE, foreground=T.TEXT, font=T.FONT_KR_LG)
    style.configure("Sub.TLabel", background=T.SURFACE, foreground=T.TEXT_SUB, font=T.FONT_KR_SM)
    style.configure("Accent.TLabel", background=T.SURFACE, foreground=T.ACCENT, font=T.FONT_KR_SM)
    style.configure("Header.TLabel", background=T.BG, foreground=T.TEXT, font=T.FONT_KR_H)
    style.configure("Status.TLabel", background=T.PANEL, foreground=T.TEXT_SUB, font=T.FONT_KR_SM, padding=(6, 3))

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
    style.map("TEntry", bordercolor=[("focus", T.ACCENT)], lightcolor=[("focus", T.ACCENT)])

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
        background=[("pressed", T.BORDER), ("active", T.BORDER)],
        foreground=[("pressed", T.TEXT), ("active", T.TEXT)],
    )
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
        background=[("pressed", T.ACCENT_DIM), ("active", T.ACCENT_DIM), ("disabled", T.BORDER)],
        foreground=[("disabled", T.TEXT_DIM)],
    )
    style.configure("Danger.TButton",
        background="#3d2030",
        foreground=T.ERROR,
        bordercolor="#5a2a3a",
        padding=(10, 6),
        font=T.FONT_KR,
    )
    style.map("Danger.TButton", background=[("active", "#5a2030"), ("pressed", "#5a2030")])

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
    style.map("Treeview.Heading", background=[("active", T.BORDER)])

    style.configure("TProgressbar",
        background=T.ACCENT,
        troughcolor=T.PANEL,
        bordercolor=T.PANEL,
        lightcolor=T.ACCENT,
        darkcolor=T.ACCENT_DIM,
        thickness=6,
    )
    style.configure("TScrollbar",
        background=T.PANEL,
        troughcolor=T.SURFACE,
        bordercolor=T.SURFACE,
        arrowcolor=T.TEXT_DIM,
        relief="flat",
        width=10,
    )
    style.map("TScrollbar", background=[("active", T.BORDER)])
    style.configure("TSeparator", background=T.BORDER)
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
    style.configure("TCheckbutton",
        background=T.BG,
        foreground=T.TEXT,
        indicatorcolor=T.ENTRY_BG,
        indicatorbackground=T.ENTRY_BG,
    )
    style.map("TCheckbutton", indicatorcolor=[("selected", T.ACCENT)])

    style.configure("TNotebook", background=T.BG, bordercolor=T.BORDER, tabmargins=[0, 3, 0, 0])
    style.configure("TNotebook.Tab",
        background=T.PANEL,
        foreground=T.TEXT_SUB,
        padding=[18, 7],
        font=T.FONT_KR,
    )
    style.map("TNotebook.Tab",
        background=[("selected", T.SURFACE), ("active", T.BORDER)],
        foreground=[("selected", T.ACCENT), ("active", T.TEXT)],
        padding=[("selected", [18, 11]), ("active", [18, 8])],
        font=[("selected", (*T.FONT_KR[:2], "bold"))],
    )
    return style

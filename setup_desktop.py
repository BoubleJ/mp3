#!/usr/bin/env python3
"""
setup_desktop.py
Windows 바탕화면에 'Melon MP3 Tagger' 단축 아이콘을 생성합니다.
WSL2 + WSLg 환경에서 콘솔 창 없이 GUI 앱을 실행합니다.
"""

import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow 설치 필요: pip3 install Pillow --break-system-packages")
    sys.exit(1)


# ─── 경로 유틸 ───────────────────────────────────────────────────────────────

def _cmd(args: list, timeout=5) -> str:
    """cmd.exe 명령 실행 → CP949 디코딩 후 strip 반환"""
    r = subprocess.run(args, capture_output=True, timeout=timeout)
    return r.stdout.decode("cp949", errors="replace").strip()


def _wslpath(win_path: str) -> Path:
    """Windows 경로 → WSL 경로 변환"""
    r = subprocess.run(["wslpath", win_path], capture_output=True, timeout=5)
    return Path(r.stdout.decode("utf-8", errors="replace").strip())


def _win_path(wsl_path: Path) -> str:
    """WSL 경로 → Windows 경로 변환"""
    r = subprocess.run(["wslpath", "-w", str(wsl_path)],
                       capture_output=True, timeout=5)
    return r.stdout.decode("utf-8", errors="replace").strip()


def get_windows_info() -> dict:
    username = _cmd(["cmd.exe", "/c", "echo %USERNAME%"])
    appdata_win = _cmd(["cmd.exe", "/c", "echo %APPDATA%"])
    appdata_wsl = _wslpath(appdata_win)
    desktop_wsl = appdata_wsl.parent / "Desktop"
    return {
        "username": username,
        "appdata_wsl": appdata_wsl,
        "desktop_wsl": desktop_wsl,
    }


# ─── 아이콘 생성 ─────────────────────────────────────────────────────────────

def create_icon(dest: Path):
    """멜론 그린 배경 + 음표 ICO 파일 생성 (다중 해상도)"""
    MELON_GREEN = (0, 199, 60, 255)
    WHITE = (255, 255, 255, 255)

    S = 256
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 배경 원
    pad = S // 12
    d.ellipse([pad, pad, S - pad - 1, S - pad - 1], fill=MELON_GREEN)

    # 음표 머리
    cx, cy = S // 2, S // 2
    r = S // 7
    hx, hy = cx - r // 2, cy + r // 2
    d.ellipse([hx - r, hy - r // 2, hx + r, hy + r // 2], fill=WHITE)

    # 음표 기둥
    sx = hx + r
    d.rectangle([sx - 4, hy - r // 2 - S // 5, sx, hy - r // 2 + 4], fill=WHITE)

    # 음표 꼬리
    ty = hy - r // 2 - S // 5
    d.rectangle([sx - 4, ty, sx + S // 6, ty + 4], fill=WHITE)

    # 256px 이미지 하나로 ICO 다중 해상도 생성
    img.save(
        dest, format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"  ✔ 아이콘 생성: {dest}  ({dest.stat().st_size:,} bytes)")


# ─── VBS 런처 ────────────────────────────────────────────────────────────────

def create_vbs_launcher(vbs_path: Path, project_wsl: str):
    """
    wscript.exe 로 실행하면 콘솔 창이 뜨지 않음.
    DISPLAY 환경변수 설정은 WSLg가 자동 처리하므로 불필요.
    """
    content = (
        'Set oShell = CreateObject("WScript.Shell")\r\n'
        f'oShell.Run "wsl.exe bash -c ""cd {project_wsl} && python3 main.py""", 0, False\r\n'
    )
    vbs_path.write_text(content, encoding="utf-8")
    print(f"  ✔ 런처 생성: {vbs_path}")


# ─── Windows 단축 아이콘(.lnk) ───────────────────────────────────────────────

def create_shortcut(lnk_win: str, vbs_win: str, icon_win: str):
    """PowerShell COM 오브젝트로 .lnk 파일 생성"""
    ps = f"""
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut('{lnk_win}')
$lnk.TargetPath      = 'wscript.exe'
$lnk.Arguments       = '"{vbs_win}"'
$lnk.Description     = 'Melon MP3 Tagger'
$lnk.IconLocation    = '{icon_win}, 0'
$lnk.WorkingDirectory = ''
$lnk.WindowStyle     = 1
$lnk.Save()
Write-Output 'OK'
"""
    r = subprocess.run(
        ["powershell.exe", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True, timeout=15,
    )
    out = r.stdout.decode("cp949", errors="replace").strip()
    if "OK" in out:
        print(f"  ✔ 단축 아이콘 생성: {lnk_win}")
    else:
        err = r.stderr.decode("cp949", errors="replace").strip()
        print(f"  ✖ 단축 아이콘 생성 실패:\n{err}")


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  Melon MP3 Tagger — Windows 바탕화면 아이콘 설치")
    print("=" * 55)

    info = get_windows_info()
    username    = info["username"]
    appdata_wsl = info["appdata_wsl"]
    desktop_wsl = info["desktop_wsl"]

    print(f"\n사용자: {username}")
    print(f"AppData: {appdata_wsl}")
    print(f"바탕화면: {desktop_wsl}\n")

    # 앱 데이터 폴더
    app_dir = appdata_wsl / "MelonTagger"
    app_dir.mkdir(parents=True, exist_ok=True)

    project_wsl = "/home/dogmnil2007/develop/mp3"

    # 1. 아이콘
    icon_wsl = app_dir / "melon_tagger.ico"
    create_icon(icon_wsl)

    # 2. VBS 런처
    vbs_wsl = app_dir / "launch.vbs"
    create_vbs_launcher(vbs_wsl, project_wsl)

    # 3. Windows 경로 변환
    icon_win = _win_path(icon_wsl)
    vbs_win  = _win_path(vbs_wsl)
    lnk_win  = f"C:\\Users\\{username}\\Desktop\\Melon MP3 Tagger.lnk"

    # 4. 바탕화면 단축 아이콘
    create_shortcut(lnk_win, vbs_win, icon_win)

    print()
    print("─" * 55)
    print("설치 완료!")
    print("바탕화면의 'Melon MP3 Tagger' 아이콘을 더블클릭하세요.")
    print("─" * 55)


if __name__ == "__main__":
    main()

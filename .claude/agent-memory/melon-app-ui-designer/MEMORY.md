# Melon MP3 Tagger - UI Designer Memory

## Project Structure
- `/home/dogmnil2007/develop/mp3/melon_tagger/`
  - `crawler.py` — MelonCrawler, AlbumInfo, TrackInfo dataclasses
  - `mp3_handler.py` — MP3Handler (mutagen 기반 read/write_metadata)
  - `ui.py` — 메인 tkinter UI (구현 완료)

## Framework Decision
- **tkinter + ttk** 사용 (PyQt6 아님). ttk.Style + clam 테마 베이스
- PIL(Pillow) 앨범아트 표시에 사용; 없으면 텍스트 대체

## Design Tokens (Theme class in ui.py)
- BG=#1e1e2e, SURFACE=#181825, PANEL=#313244, BORDER=#45475a
- ACCENT=#00C73C (멜론 그린), ACCENT_DIM=#009e30
- TEXT=#cdd6f4, TEXT_SUB=#a6adc8, TEXT_DIM=#6c7086
- ERROR=#f38ba8, SUCCESS=#a6e3a1, WARNING=#f9e2af
- Font: ("맑은 고딕", 10) KR, ("Consolas", 9) mono

## Key Components (ui.py)
- `Theme` — 색상/폰트 토큰 클래스
- `apply_dark_theme(root)` — ttk.Style 전체 설정, clam 베이스
- `AlbumInfoPanel(parent)` — 좌측 앨범아트+텍스트 패널, pack 레이아웃
- `TrackTreeview(parent)` — 우측 트랙 목록, grid+scrollbar
- `MP3FilePanel(parent, on_files_changed)` — 하단 MP3 파일 관리
- `StatusBar(parent)` — 최하단 상태바+진행바, grid 3열
- `UrlBar(parent, on_crawl)` — 상단 URL 입력바, pack horizontal
- `ActionBar(parent, ...)` — 적용/건너뛰기 버튼 + 옵션 체크박스
- `MainWindow(tk.Tk)` — 메인 윈도우, 1200x800 (min 900x650)

## Layout Pattern
- 최외곽: pack (top/bottom 고정, center expand)
- 메인 영역: ttk.PanedWindow(vertical) > ttk.PanedWindow(horizontal)
- Treeview: 항상 grid + vsb/hsb scrollbar 조합 사용
- 앨범 패널: pack_propagate(False)로 아트 크기 고정

## ttk.Style 주의사항
- clam 테마에서 Entry 테두리는 lightcolor/darkcolor로 제어
- Treeview 선택색은 style.map()의 background/foreground로만 적용
- Button hover는 "active" 상태로 처리 (Qt의 hover와 동일)
- fieldbackground는 Entry/Treeview 내부 배경 (background와 별개)

## TNotebook.Tab 높이 차이 구현 패턴 (확정)
- `style.map("TNotebook.Tab", padding=[...])` 으로 상태별 패딩을 덮어씌움
- selected: padding=[18, 11] (상단 11px), 기본: padding=[18, 7] (상단 7px) → 4px 높이 차이
- active(호버): padding=[18, 8] → 미묘하게 커지는 피드백
- font도 style.map에서 selected 시 bold 처리 가능: `font=[("selected", (*FONT_KR[:2], "bold"))]`
- TNotebook tabmargins=[0, 3, 0, 0]: 상단 마진 3px로 선택 탭 돌출 효과 허용
- tabmargins 상단값이 0이면 패딩 차이가 시각적으로 드러나지 않으므로 반드시 양수로 설정

## Treeview 컬럼 패턴
- columns 파라미터에 id 리스트 전달, show="headings"
- stretch=True는 제목/파일명 컬럼에만 적용
- tag_configure로 홀짝 행 색상 + 상태별 색상 분리

## 진입점
- `python3 -m melon_tagger.ui` 또는 ui.py 직접 실행
- `main()` 함수 → `MainWindow().mainloop()`

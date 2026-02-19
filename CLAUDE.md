# Melon MP3 Tagger — Claude 작업 규칙

## 필수 규칙

### 커밋
- **모든 작업 완료 후 반드시 git commit을 수행한다.**
- 커밋 대상: 작업에서 수정한 소스 파일만 (`melon_tagger/`, `main.py`, `setup_desktop.py` 등)
- 커밋 제외: `.claude/`, `__pycache__/`, `.pyc` 파일
- 커밋 메시지 형식:
  ```
  <type>: <한국어 요약>

  - 변경 내용 bullet

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  ```
- type 예시: `feat`(기능 추가), `fix`(버그 수정), `refactor`(리팩터링), `style`(UI 변경), `chore`(설정/기타)

## 프로젝트 개요

멜론 앨범 페이지를 크롤링하여 MP3 파일에 메타데이터를 적용하는 WSL2 기반 tkinter GUI 앱.

### 핵심 파일
| 파일 | 역할 |
|------|------|
| `melon_tagger/crawler.py` | 멜론 크롤러 (앨범, 곡 상세, 가사, 싱크가사) |
| `melon_tagger/mp3_handler.py` | mutagen 기반 ID3 태그 읽기/쓰기 |
| `melon_tagger/ui.py` | tkinter + ttk 다크 테마 GUI |
| `main.py` | 진입점 |
| `setup_desktop.py` | Windows 바탕화면 단축아이콘 설치 |

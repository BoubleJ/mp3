"""
mutagen 기반 MP3 메타데이터 읽기/쓰기 (서비스 레이어)
"""

from pathlib import Path
from typing import List, Optional, Tuple

from mutagen.mp3 import MP3
from mutagen.id3 import (
    ID3,
    ID3NoHeaderError,
    TIT2,
    TPE1,
    TALB,
    TPE2,
    TCON,
    TRCK,
    APIC,
    USLT,
    TPOS,
)

class MP3Handler:
    def read_metadata(self, filepath: str) -> dict:
        """현재 MP3 파일의 메타데이터를 딕셔너리로 반환"""
        result = {
            "title": "",
            "artist": "",
            "album": "",
            "album_artist": "",
            "genre": "",
            "track_number": "",
        }
        try:
            tags = ID3(filepath)
            result["title"] = str(tags.get("TIT2", ""))
            result["artist"] = str(tags.get("TPE1", ""))
            result["album"] = str(tags.get("TALB", ""))
            result["album_artist"] = str(tags.get("TPE2", ""))
            result["genre"] = str(tags.get("TCON", ""))
            result["track_number"] = str(tags.get("TRCK", ""))
        except ID3NoHeaderError:
            pass
        except Exception:
            pass
        return result

    def write_metadata(
        self,
        filepath: str,
        title: str = "",
        artist: str = "",
        album: str = "",
        album_artist: str = "",
        genre: str = "",
        track_number: int = 0,
        cover_data: Optional[bytes] = None,
        lyrics: str = "",
        disc_number: int = 0,
    ) -> None:
        """MP3 파일에 메타데이터를 기록"""
        try:
            tags = ID3(filepath)
        except ID3NoHeaderError:
            audio = MP3(filepath)
            audio.add_tags()
            tags = audio.tags

        if title:
            tags["TIT2"] = TIT2(encoding=3, text=title)
        if artist:
            tags["TPE1"] = TPE1(encoding=3, text=artist)
        if album:
            tags["TALB"] = TALB(encoding=3, text=album)
        if album_artist:
            tags["TPE2"] = TPE2(encoding=3, text=album_artist)
        if genre:
            tags["TCON"] = TCON(encoding=3, text=genre)
        if track_number:
            tags["TRCK"] = TRCK(encoding=3, text=str(track_number))
        if disc_number:
            tags["TPOS"] = TPOS(encoding=3, text=str(disc_number))

        if cover_data:
            tags["APIC"] = APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=cover_data,
            )

        if lyrics:
            tags["USLT::kor"] = USLT(encoding=3, lang="kor", desc="", text=lyrics)

        tags.save(filepath, v2_version=3)

    def write_lrc_file(
        self,
        mp3_filepath: str,
        synced_lyrics: List[Tuple[str, int]],
    ) -> str:
        """싱크 가사를 MP3와 동일한 이름의 .lrc 파일로 저장. 반환: 생성된 .lrc 경로"""
        lrc_path = Path(mp3_filepath).with_suffix(".lrc")
        lines = []
        for text, ms in synced_lyrics:
            mm = ms // 60000
            ss = (ms % 60000) // 1000
            cs = (ms % 1000) // 10
            lines.append(f"[{mm:02d}:{ss:02d}.{cs:02d}]{text}")
        lrc_path.write_text("\n".join(lines), encoding="utf-8")
        return str(lrc_path)

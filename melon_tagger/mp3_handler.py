"""
melon_tagger/mp3_handler.py
mutagen 기반 MP3 메타데이터 읽기/쓰기
"""

from pathlib import Path
from typing import Optional

from mutagen.mp3 import MP3
from mutagen.id3 import (
    ID3,
    ID3NoHeaderError,
    TIT2,  # 제목
    TPE1,  # 아티스트
    TALB,  # 앨범
    TPE2,  # 앨범아티스트
    TCON,  # 장르
    TRCK,  # 트랙번호
    APIC,  # 앨범아트
    TYER,  # 연도
    ID3TimeStamp,
    TDRC,
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
    ) -> None:
        """MP3 파일에 메타데이터를 기록"""
        try:
            tags = ID3(filepath)
        except ID3NoHeaderError:
            # ID3 헤더가 없는 경우 새로 생성
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

        # 앨범아트
        if cover_data:
            tags["APIC"] = APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,  # Front cover
                desc="Cover",
                data=cover_data,
            )

        tags.save(filepath, v2_version=3)

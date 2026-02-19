"""
도메인·데이터 구조: 앨범/트랙 정보 (UI·API·서비스 공통)
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TrackInfo:
    track_number: int
    title: str
    artist: str
    album: str
    album_artist: str
    genre: str
    song_id: str = ""
    lyrics: str = ""
    disc_number: int = 1


@dataclass
class AlbumInfo:
    album_name: str
    album_artist: str
    genre: str
    release_date: str
    cover_url: str
    tracks: List[TrackInfo] = field(default_factory=list)
    cover_data: Optional[bytes] = None

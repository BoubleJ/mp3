"""
melon_tagger/crawler.py
멜론 앨범 페이지 크롤러
"""

import requests
from bs4 import BeautifulSoup
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


@dataclass
class AlbumInfo:
    album_name: str
    album_artist: str
    genre: str
    release_date: str
    cover_url: str
    tracks: List[TrackInfo] = field(default_factory=list)
    cover_data: Optional[bytes] = None


class MelonCrawler:
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Referer": "https://www.melon.com/",
    }

    def crawl_album(self, url: str) -> AlbumInfo:
        resp = requests.get(url, headers=self.HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 앨범명
        album_name = self._get_album_name(soup)

        # 앨범아티스트
        album_artist = self._get_album_artist(soup)

        # 장르 / 발매일
        genre, release_date = self._get_meta_info(soup)

        # 앨범아트 URL
        cover_url = self._get_cover_url(soup)

        # 트랙 목록
        tracks = self._get_tracks(soup, album_name, album_artist, genre)

        album = AlbumInfo(
            album_name=album_name,
            album_artist=album_artist,
            genre=genre,
            release_date=release_date,
            cover_url=cover_url,
            tracks=tracks,
        )

        # 앨범아트 다운로드
        if cover_url:
            try:
                cover_resp = requests.get(cover_url, headers=self.HEADERS, timeout=10)
                album.cover_data = cover_resp.content
            except Exception:
                pass

        return album

    def _get_album_name(self, soup: BeautifulSoup) -> str:
        el = soup.select_one(".song_name")
        if not el:
            return ""
        for tag in el.find_all("strong"):
            tag.decompose()
        return el.get_text(strip=True)

    def _get_album_artist(self, soup: BeautifulSoup) -> str:
        # 아티스트 이름 (첫 번째 span)
        el = soup.select_one(".artist .artist_name span")
        if el:
            return el.get_text(strip=True)
        # fallback: og:title
        og = soup.find("meta", property="og:title")
        if og:
            return og.get("content", "")
        return ""

    def _get_meta_info(self, soup: BeautifulSoup):
        genre = ""
        release_date = ""
        dl = soup.select_one("dl.list")
        if dl:
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")
            for dt, dd in zip(dts, dds):
                text = dt.get_text(strip=True)
                if "장르" in text:
                    genre = dd.get_text(strip=True)
                elif "발매일" in text:
                    release_date = dd.get_text(strip=True)
        return genre, release_date

    def _get_cover_url(self, soup: BeautifulSoup) -> str:
        og = soup.find("meta", property="og:image")
        return og.get("content", "") if og else ""

    def _get_tracks(
        self,
        soup: BeautifulSoup,
        album_name: str,
        album_artist: str,
        genre: str,
    ) -> List[TrackInfo]:
        tracks = []
        rows = soup.select("tbody tr")

        for row in rows:
            rank_el = row.select_one(".rank")
            if not rank_el:
                continue
            try:
                track_num = int(rank_el.get_text(strip=True))
            except ValueError:
                continue

            # Song ID
            checkbox = row.select_one('input[type="checkbox"]')
            song_id = checkbox["value"] if checkbox else ""

            # 제목: 재생 링크 텍스트
            play_links = row.select('a[title*="재생"]')
            if play_links:
                title = play_links[0].get_text(strip=True)
            else:
                # fallback: song_info 링크 title 속성에서 추출
                info_link = row.select_one("a.song_info")
                if info_link:
                    raw = info_link.get("title", "")
                    title = raw.replace("곡정보", "").strip()
                else:
                    title = ""

            # 아티스트: rank02 내 링크들
            artist_links = row.select(".rank02 a")
            artists = [a.get_text(strip=True) for a in artist_links if a.get_text(strip=True)]
            # 중복 제거 (멜론이 같은 이름을 두 번 출력하는 경우)
            seen = []
            for a in artists:
                if a not in seen:
                    seen.append(a)
            artist = ", ".join(seen) if seen else album_artist

            tracks.append(
                TrackInfo(
                    track_number=track_num,
                    title=title,
                    artist=artist,
                    album=album_name,
                    album_artist=album_artist,
                    genre=genre,
                    song_id=song_id,
                )
            )

        return tracks

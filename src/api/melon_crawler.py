"""
멜론 앨범 페이지 크롤러 (외부 연동)
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import List, Tuple

from src.models import AlbumInfo, TrackInfo


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

        album_name = self._get_album_name(soup)
        album_artist = self._get_album_artist(soup)
        genre, release_date = self._get_meta_info(soup)
        cover_url = self._get_cover_url(soup)
        tracks = self._get_tracks(soup, album_name, album_artist, genre)

        album = AlbumInfo(
            album_name=album_name,
            album_artist=album_artist,
            genre=genre,
            release_date=release_date,
            cover_url=cover_url,
            tracks=tracks,
        )

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
        el = soup.select_one(".artist .artist_name span")
        if el:
            return el.get_text(strip=True)
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

            disc_attr = row.get("data-group-items", "")
            disc_match = re.search(r"cd(\d+)", disc_attr, re.IGNORECASE)
            disc_num = int(disc_match.group(1)) if disc_match else 1

            checkbox = row.select_one('input[type="checkbox"]')
            song_id = checkbox["value"] if checkbox else ""
            if not song_id:
                info_link = row.select_one("a.song_info")
                if info_link:
                    m = re.search(r"goSongDetail\('(\d+)'\)", info_link.get("href", ""))
                    if m:
                        song_id = m.group(1)

            play_links = row.select('a[title*="재생"]')
            if play_links:
                title = play_links[0].get_text(strip=True)
            else:
                info_link = row.select_one("a.song_info")
                if info_link:
                    raw = info_link.get("title", "")
                    title = raw.replace("곡정보", "").strip()
                else:
                    title = ""

            artist_links = row.select(".rank02 a")
            artists = [a.get_text(strip=True) for a in artist_links if a.get_text(strip=True)]
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
                    disc_number=disc_num,
                )
            )

        return tracks

    def crawl_song_detail(self, song_id: str) -> dict:
        result = {"lyrics": "", "genre": ""}
        if not song_id:
            return result
        url = f"https://www.melon.com/song/detail.htm?songId={song_id}"
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            result["lyrics"] = self._extract_lyrics(soup)
            result["genre"] = self._extract_song_genre(soup)
        except Exception:
            pass
        return result

    def crawl_lyrics(self, song_id: str) -> str:
        return self.crawl_song_detail(song_id)["lyrics"]

    def _extract_song_genre(self, soup: BeautifulSoup) -> str:
        dl = soup.select_one("dl.list")
        if dl:
            for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd")):
                if "장르" in dt.get_text(strip=True):
                    return dd.get_text(strip=True)
        return ""

    def fetch_synced_lyrics(
        self, title: str, artist: str, album: str
    ) -> List[Tuple[str, int]]:
        url = "https://lrclib.net/api/get"
        params = {
            "artist_name": artist,
            "track_name": title,
            "album_name": album,
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                lrc_text = data.get("syncedLyrics") or ""
                if lrc_text:
                    return self._parse_lrc(lrc_text)
        except Exception:
            pass
        return []

    def _parse_lrc(self, lrc_text: str) -> List[Tuple[str, int]]:
        pattern = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)")
        result = []
        for line in lrc_text.splitlines():
            m = pattern.match(line.strip())
            if m:
                mm, ss, cs, text = m.groups()
                ms = int(mm) * 60000 + int(ss) * 1000 + int(cs.ljust(3, "0")[:3])
                result.append((text.strip(), ms))
        return result

    def _extract_lyrics(self, soup: BeautifulSoup) -> str:
        candidates = [
            ".lyric_wrap .lyric",
            "#lyricArea",
            ".lyric_wrap",
            ".lyric",
        ]
        for sel in candidates:
            el = soup.select_one(sel)
            if el:
                for btn in el.select("button"):
                    btn.decompose()
                for hidden in el.select(".none"):
                    hidden.decompose()
                for br in el.find_all("br"):
                    br.replace_with("\n")
                text = el.get_text().strip()
                if "가사 준비중" in text:
                    return ""
                if len(text) > 10:
                    return text
        return ""

from __future__ import annotations

from typing import Any

import aiohttp


_BASE_URL = "https://www.screenscraper.fr/api2/jeuInfos.php"

# ScreenScraper numeric system IDs for platforms pr-meta handles.
_PLATFORM_IDS: dict[str, int] = {
    "n64": 14,
    "ps1": 57,
    "ps2": 58,
    "snes": 4,
    "gba": 12,
    "md": 1,
    "nes": 3,
    "gb": 9,
    "gbc": 10,
    "saturn": 22,
    "dreamcast": 23,
    "gamecube": 13,
    "wii": 16,
    "xbox": 32,
    "ps3": 60,
}


def _find_text(
    items: list[dict], lang_key: str, lang_val: str, fallback_index: int = 0
) -> str | None:
    for item in items:
        if item.get(lang_key) == lang_val:
            return item.get("text")
    if items:
        return items[fallback_index].get("text")
    return None


def _parse_rating(note_text: str | None) -> float | None:
    """Convert 'N/20' or '0.N' strings to a 0.0-1.0 float."""
    if not note_text:
        return None
    try:
        if "/" in note_text:
            num, denom = note_text.split("/")
            return round(float(num) / float(denom), 4)
        return round(float(note_text), 4)
    except (ValueError, ZeroDivisionError):
        return None


def _find_media_url(medias: list[dict], media_type: str) -> str | None:
    for m in medias:
        if m.get("type") == media_type:
            return m.get("url")
    return None


class ScreenScraperClient:
    def __init__(self, devid: str, devpassword: str, softname: str) -> None:
        self._devid = devid
        self._devpassword = devpassword
        self._softname = softname

    async def scrape(self, platform: str, title: str) -> dict[str, Any] | None:
        """Query ScreenScraper.fr for *title* on *platform*.
        Returns a normalized metadata dict or None if not found."""
        system_id = _PLATFORM_IDS.get(platform)
        if system_id is None:
            return None

        params = {
            "devid": self._devid,
            "devpassword": self._devpassword,
            "softname": self._softname,
            "output": "json",
            "romnom": title,
            "systemeid": system_id,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(_BASE_URL, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json(content_type=None)

        jeu = data.get("response", {}).get("jeu")
        if not jeu:
            return None

        noms = jeu.get("noms", [])
        dates = jeu.get("dates", [])
        genres = jeu.get("genres", [])
        synopsis = jeu.get("synopsis", [])
        medias = jeu.get("medias", [])

        title_str = _find_text(noms, "region", "us") or ""
        date_str = _find_text(dates, "region", "us") or ""
        year = int(date_str[:4]) if len(date_str) >= 4 and date_str[:4].isdigit() else None

        genre_str: str | None = None
        if genres:
            genre_noms = genres[0].get("noms", [])
            genre_str = _find_text(genre_noms, "langue", "en")

        description = _find_text(synopsis, "langue", "en")
        rating = _parse_rating((jeu.get("note") or {}).get("text"))
        players_text = (jeu.get("joueurs") or {}).get("text")
        try:
            players = int(players_text) if players_text else None
        except ValueError:
            players = None

        return {
            "title": title_str,
            "year": year,
            "genre": genre_str,
            "publisher": (jeu.get("editeur") or {}).get("text"),
            "developer": (jeu.get("developpeur") or {}).get("text"),
            "description": description,
            "rating": rating,
            "players": players,
            "image_url": _find_media_url(medias, "box-2D"),
            "video_url": _find_media_url(medias, "video"),
        }

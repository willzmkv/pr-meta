from __future__ import annotations

from typing import Any

import aiohttp

_BASE_URL = "https://api.thegamesdb.net/v1"


class TheGamesDBClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def scrape(self, platform: str, title: str) -> dict[str, Any] | None:
        params = {
            "apikey": self._api_key,
            "name": title,
            "fields": "genres,publishers,developers,overview,rating,players",
            "include": "genres,boxart",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{_BASE_URL}/Games/ByGameName", params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json(content_type=None)

        games = (data.get("data") or {}).get("games", [])
        if not games:
            return None

        g = games[0]
        game_id = g.get("id")
        include = data.get("include", {})

        # Year
        year: int | None = None
        release = g.get("release_date", "")
        if release and len(release) >= 4 and release[:4].isdigit():
            year = int(release[:4])

        # Genre via include
        genre: str | None = None
        genres_map = (include.get("genres") or {}).get("data", {})
        game_genre_ids = g.get("genres", [])
        if game_genre_ids:
            gid = str(game_genre_ids[0])
            genre = (genres_map.get(gid) or {}).get("genre")

        # Publisher / developer
        publishers = g.get("publishers", [])
        developers = g.get("developers", [])
        publisher = publishers[0].get("name") if publishers else None
        developer = developers[0].get("name") if developers else None

        # Cover art via include
        image_url: str | None = None
        boxart_include = include.get("boxart", {})
        base_url = (boxart_include.get("base_url") or {}).get("original", "")
        boxart_data = (boxart_include.get("data") or {}).get(str(game_id), [])
        for art in boxart_data:
            if art.get("side") == "front" or art.get("type") == "boxart":
                image_url = base_url + art.get("filename", "")
                break

        # Rating
        rating_raw = g.get("rating")
        rating: float | None = None
        if rating_raw:
            try:
                if "/" in str(rating_raw):
                    num, denom = str(rating_raw).split("/")
                    rating = round(float(num) / float(denom), 4)
                else:
                    rating = round(float(rating_raw) / 10.0, 4)
            except (ValueError, ZeroDivisionError):
                pass

        players_text = g.get("players")
        try:
            players = int(players_text) if players_text else None
        except ValueError:
            players = None

        return {
            "title": g.get("game_title"),
            "year": year,
            "genre": genre,
            "publisher": publisher,
            "developer": developer,
            "description": g.get("overview"),
            "rating": rating,
            "players": players,
            "image_url": image_url,
            "video_url": None,
        }

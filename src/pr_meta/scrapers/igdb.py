from __future__ import annotations

import datetime
import time
from typing import Any

import aiohttp

_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
_GAMES_URL = "https://api.igdb.com/v4/games"


class IGDBClient:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._token_expiry: float = 0.0

    async def _get_token(self, session: aiohttp.ClientSession) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        async with session.post(
            _TOKEN_URL,
            params={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "client_credentials",
            },
        ) as resp:
            data = await resp.json(content_type=None)
        self._token = data["access_token"]
        self._token_expiry = time.time() + data.get("expires_in", 3600)
        return self._token

    async def scrape(self, platform: str, title: str) -> dict[str, Any] | None:
        async with aiohttp.ClientSession() as session:
            token = await self._get_token(session)
            headers = {
                "Client-ID": self._client_id,
                "Authorization": f"Bearer {token}",
            }
            body = (
                f'search "{title}"; '
                f"fields name,first_release_date,genres.name,"
                f"involved_companies.company.name,involved_companies.publisher,"
                f"involved_companies.developer,summary,rating,cover.url; "
                f"limit 1;"
            )
            async with session.post(_GAMES_URL, headers=headers, data=body) as resp:
                if resp.status != 200:
                    return None
                games = await resp.json(content_type=None)

        if not games:
            return None

        g = games[0]
        year: int | None = None
        ts = g.get("first_release_date")
        if ts:
            # utcfromtimestamp() is deprecated since Python 3.12.
            year = datetime.datetime.fromtimestamp(ts, tz=datetime.UTC).year

        genre: str | None = None
        genres = g.get("genres", [])
        if genres:
            genre = genres[0].get("name")

        publisher: str | None = None
        developer: str | None = None
        for ic in g.get("involved_companies", []):
            company_name = (ic.get("company") or {}).get("name")
            if ic.get("publisher"):
                publisher = company_name
            if ic.get("developer"):
                developer = company_name

        rating_raw = g.get("rating")
        rating = round(rating_raw / 100.0, 4) if rating_raw is not None else None

        cover_url = (g.get("cover") or {}).get("url")
        if cover_url and cover_url.startswith("//"):
            cover_url = "https:" + cover_url

        return {
            "title": g.get("name"),
            "year": year,
            "genre": genre,
            "publisher": publisher,
            "developer": developer,
            "description": g.get("summary"),
            "rating": rating,
            "players": None,  # IGDB does not expose player count in basic fields
            "image_url": cover_url,
            "video_url": None,
        }

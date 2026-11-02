from __future__ import annotations

import logging
import os
from typing import Any

from .screenscraper import ScreenScraperClient
from .igdb import IGDBClient
from .thegamesdb import TheGamesDBClient

logger = logging.getLogger(__name__)


def _clients() -> tuple[ScreenScraperClient, IGDBClient, TheGamesDBClient]:
    ss = ScreenScraperClient(
        devid=os.environ.get("SS_DEVID", ""),
        devpassword=os.environ.get("SS_DEVPASSWORD", ""),
        softname="pr-meta",
    )
    igdb = IGDBClient(
        client_id=os.environ.get("IGDB_CLIENT_ID", ""),
        client_secret=os.environ.get("IGDB_CLIENT_SECRET", ""),
    )
    tgdb = TheGamesDBClient(api_key=os.environ.get("TGDB_APIKEY", ""))
    return ss, igdb, tgdb


async def scrape(platform: str, title: str) -> dict[str, Any] | None:
    """Try ScreenScraper → IGDB → TheGamesDB. Return first non-None result.

    A source that raises (offline, bad/missing credentials, unexpected
    response shape) is logged and treated like a miss, so the chain falls
    through and the install pipeline still writes pr-meta.json/gamelist.xml.
    """
    ss, igdb, tgdb = _clients()
    for client in (ss, igdb, tgdb):
        try:
            result = await client.scrape(platform=platform, title=title)
        except Exception as exc:  # noqa: BLE001 — any source failure is a miss
            logger.warning(
                "%s failed for %s / %s: %r", type(client).__name__, platform, title, exc
            )
            continue
        if result is not None:
            return result
    return None


__all__ = ["scrape", "ScreenScraperClient", "IGDBClient", "TheGamesDBClient"]

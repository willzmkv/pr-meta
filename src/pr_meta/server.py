from __future__ import annotations

import asyncio
import json
import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .downloader import download_media
from .gamelist import read_gamelist, upsert_game, write_gamelist
from .meta_writer import read_meta, write_meta
from .scrapers import scrape

logger = logging.getLogger(__name__)

_DEFAULT_SOCKET = "/run/project-r/pr-meta.sock"
_DEFAULT_GAMES_ROOT = Path.home() / "games"


async def handle_event(
    event: dict[str, Any],
    games_root: Path = _DEFAULT_GAMES_ROOT,
) -> None:
    """Process a single event dict received from pr-builder."""
    event_type = event.get("event")
    platform = event["platform"]
    title = event["title"]
    game_dir = Path(event.get("game_dir") or games_root / platform / title)

    gamelist_path = games_root / platform / "gamelist.xml"

    if event_type == "badge_update":
        await _handle_badge_update(event, game_dir, gamelist_path)
        return

    if event_type == "game_installed":
        await _handle_game_installed(event, game_dir, gamelist_path)
        return

    logger.warning("Unknown event type: %s", event_type)


async def _handle_game_installed(
    event: dict[str, Any],
    game_dir: Path,
    gamelist_path: Path,
) -> None:
    platform = event["platform"]
    title = event["title"]
    badge = event.get("badge", "EMU")
    core = event.get("core")
    binary = event.get("binary", "")

    scraped = await scrape(platform=platform, title=title)

    meta: dict[str, Any] = {
        "title": title,
        "platform": platform,
        "badge": badge,
        "core": core,
        "binary": binary,
    }

    if scraped:
        meta.update(
            {
                "year": scraped.get("year"),
                "genre": scraped.get("genre"),
                "publisher": scraped.get("publisher"),
                "developer": scraped.get("developer"),
                "description": scraped.get("description"),
                "rating": scraped.get("rating"),
                "players": scraped.get("players"),
            }
        )
        image_url = scraped.get("image_url")
        video_url = scraped.get("video_url")
    else:
        image_url = None
        video_url = None

    media = await download_media(game_dir, image_url=image_url, video_url=video_url)
    meta["image"] = media.get("image")
    meta["video"] = media.get("video")

    write_meta(game_dir, meta)

    gamelist_path.parent.mkdir(parents=True, exist_ok=True)
    tree = read_gamelist(gamelist_path)
    fields = _meta_to_gamelist_fields(meta, game_dir)
    _claim_folder_entry(tree, game_dir.name, fields["path"])
    upsert_game(tree, fields)
    write_gamelist(gamelist_path, tree)
    logger.info("Installed: %s / %s [%s]", platform, title, badge)


async def _handle_badge_update(
    event: dict[str, Any],
    game_dir: Path,
    gamelist_path: Path,
) -> None:
    badge = event.get("badge", "EMU")
    core = event.get("core") or ""

    # Update pr-meta.json if it exists
    meta = read_meta(game_dir)
    if meta:
        meta["badge"] = badge
        meta["core"] = core if core else None
        write_meta(game_dir, meta)

    gamelist_path.parent.mkdir(parents=True, exist_ok=True)
    tree = read_gamelist(gamelist_path)

    # Determine the path field (relative to platform dir). Prefer the entry
    # already present for this game folder so a badge flip never duplicates it.
    title = event["title"]
    folder = game_dir.name
    game_path = _game_path(folder, (meta or {}).get("binary", ""))
    existing = [g.findtext("path") for g in _folder_entries(tree, folder)]
    if existing and game_path not in existing:
        game_path = existing[0]

    upsert_game(
        tree,
        {
            "path": game_path,
            "pr_badge": badge,
            "pr_core": core,
        },
    )
    write_gamelist(gamelist_path, tree)
    logger.info("Badge update: %s / %s → %s", event["platform"], title, badge)


def _game_path(folder: str, binary: str | None) -> str:
    """gamelist.xml <path> for a game: relative to the platform dir.

    ``binary`` is relative to the game dir (``./sm64.x86_64``); its leading
    ``./`` is dropped so the result is ``./Super Mario 64/sm64.x86_64``.
    An empty binary maps to the game folder itself (``./Banjo-Kazooie/``).
    """
    binary = (binary or "").removeprefix("./")
    return f"./{folder}/{binary}" if binary else f"./{folder}/"


def _media_path(folder: str, rel: str | None) -> str:
    """Re-base a pr-meta.json media path (``./media/cover.png``, relative to the
    game dir) onto the platform dir, which is what ES-DE resolves against."""
    if not rel:
        return ""
    return f"./{folder}/{rel.removeprefix('./')}"


def _folder_entries(root: ET.Element, folder: str) -> list[ET.Element]:
    prefix = f"./{folder}/"
    return [g for g in root.findall("game") if (g.findtext("path") or "").startswith(prefix)]


def _claim_folder_entry(root: ET.Element, folder: str, game_path: str) -> None:
    """Ensure at most one <game> exists for *folder*, carrying *game_path*.

    An earlier entry for the same folder (EMU install without binary, or a
    BUILDING badge sent before install) is re-pathed rather than duplicated,
    which also preserves fields ES-DE itself wrote (favorite, playcount...).
    """
    entries = _folder_entries(root, folder)
    keep = next((g for g in entries if g.findtext("path") == game_path), None)
    if keep is None and entries:
        keep = entries[0]
        keep.find("path").text = game_path
    for g in entries:
        if g is not keep:
            root.remove(g)


def _meta_to_gamelist_fields(meta: dict[str, Any], game_dir: Path) -> dict[str, str]:
    title = meta.get("title", "")
    folder = game_dir.name
    game_path = _game_path(folder, meta.get("binary"))

    year = meta.get("year")
    releasedate = f"{year}0101T000000" if year else ""

    return {
        "path": game_path,
        "name": title,
        "desc": meta.get("description") or "",
        "image": _media_path(folder, meta.get("image")),
        "video": _media_path(folder, meta.get("video")),
        "releasedate": releasedate,
        "developer": meta.get("developer") or "",
        "publisher": meta.get("publisher") or "",
        "genre": meta.get("genre") or "",
        "players": str(meta.get("players") or ""),
        "rating": str(meta.get("rating") or ""),
        "pr_badge": meta.get("badge") or "EMU",
        "pr_core": meta.get("core") or "",
    }


_MAX_EVENT_BYTES = 65536


async def _read_event(reader: asyncio.StreamReader) -> dict[str, Any] | None:
    """Read one JSON object from *reader*.

    Stops at EOF (client closed / half-closed) or as soon as the bytes received
    so far parse as JSON (client keeps its write side open), so a message split
    across several reads is reassembled. Returns None for an empty connection.
    """
    buf = b""
    while len(buf) < _MAX_EVENT_BYTES:
        chunk = await reader.read(_MAX_EVENT_BYTES - len(buf))
        if not chunk:
            break
        buf += chunk
        try:
            return json.loads(buf)
        except ValueError:  # incomplete (or invalid) so far — keep reading
            continue
    return json.loads(buf) if buf else None


async def _serve(socket_path: str, games_root: Path) -> None:
    async def _client_handler(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            event = await _read_event(reader)
            if event is not None:
                await handle_event(event, games_root=games_root)
        except Exception:
            logger.exception("Error handling event")
        finally:
            writer.close()
            await writer.wait_closed()

    if os.path.exists(socket_path):
        os.unlink(socket_path)

    server = await asyncio.start_unix_server(_client_handler, path=socket_path)
    os.chmod(socket_path, 0o660)
    logger.info("pr-meta listening on %s", socket_path)
    async with server:
        await server.serve_forever()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    socket_path = os.environ.get("PR_META_SOCKET", _DEFAULT_SOCKET)
    games_root = Path(os.environ.get("PR_GAMES_ROOT", str(_DEFAULT_GAMES_ROOT)))
    asyncio.run(_serve(socket_path, games_root))

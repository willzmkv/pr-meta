import asyncio
import json
import xml.etree.ElementTree as ET
from unittest.mock import AsyncMock, patch

import pytest

from pr_meta.server import _serve, handle_event

INSTALL_EVENT = {
    "event": "game_installed",
    "platform": "n64",
    "title": "Super Mario 64",
    "rom_hash": "20b854b239203baf6354e9f5e5ea9bc7",
    "game_dir": None,  # set in tests using tmp_path
    "badge": "NATIVE",
    "core": None,
    "binary": "./sm64.x86_64",
}

BADGE_EVENT = {
    "event": "badge_update",
    "platform": "n64",
    "title": "Super Mario 64",
    "badge": "BUILD ERROR",
    "core": None,
    "progress": None,
}

SCRAPED_META = {
    "title": "Super Mario 64",
    "year": 1996,
    "genre": "Platform",
    "publisher": "Nintendo",
    "developer": "Nintendo",
    "description": "Guide Mario.",
    "rating": 0.95,
    "players": 1,
    "image_url": "https://example.com/cover.png",
    "video_url": "https://example.com/video.mp4",
}

DOWNLOAD_RESULT = {"image": "./media/cover.png", "video": "./media/video.mp4"}


@pytest.mark.asyncio
async def test_handle_game_installed_writes_meta_and_gamelist(tmp_path):
    game_dir = tmp_path / "n64" / "Super Mario 64"
    game_dir.mkdir(parents=True)
    gamelist_dir = tmp_path / "n64"

    event = dict(INSTALL_EVENT)
    event["game_dir"] = str(game_dir)

    with (
        patch("pr_meta.server.scrape", new_callable=AsyncMock, return_value=SCRAPED_META),
        patch(
            "pr_meta.server.download_media", new_callable=AsyncMock, return_value=DOWNLOAD_RESULT
        ),
    ):
        await handle_event(event, games_root=tmp_path)

    meta_path = game_dir / "pr-meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert meta["title"] == "Super Mario 64"
    assert meta["badge"] == "NATIVE"
    assert meta["image"] == "./media/cover.png"

    gamelist_path = gamelist_dir / "gamelist.xml"
    assert gamelist_path.exists()
    content = gamelist_path.read_text()
    assert "<pr_badge>NATIVE</pr_badge>" in content
    assert "<name>Super Mario 64</name>" in content


@pytest.mark.asyncio
async def test_handle_badge_update_updates_gamelist(tmp_path):
    game_dir = tmp_path / "n64" / "Super Mario 64"
    game_dir.mkdir(parents=True)
    gamelist_dir = tmp_path / "n64"

    # First install a game so gamelist.xml exists
    install_event = dict(INSTALL_EVENT)
    install_event["game_dir"] = str(game_dir)

    with (
        patch("pr_meta.server.scrape", new_callable=AsyncMock, return_value=SCRAPED_META),
        patch(
            "pr_meta.server.download_media", new_callable=AsyncMock, return_value=DOWNLOAD_RESULT
        ),
    ):
        await handle_event(install_event, games_root=tmp_path)

    # Now send badge_update
    badge_event = dict(BADGE_EVENT)
    badge_event["game_dir"] = str(game_dir)

    with patch("pr_meta.server.scrape", new_callable=AsyncMock) as scrape_mock:
        await handle_event(badge_event, games_root=tmp_path)
        scrape_mock.assert_not_called()  # badge updates must NOT re-scrape

    gamelist_path = gamelist_dir / "gamelist.xml"
    content = gamelist_path.read_text()
    assert "<pr_badge>BUILD ERROR</pr_badge>" in content


@pytest.mark.asyncio
async def test_handle_event_skips_scrape_when_scraper_returns_none(tmp_path):
    game_dir = tmp_path / "n64" / "Super Mario 64"
    game_dir.mkdir(parents=True)

    event = dict(INSTALL_EVENT)
    event["game_dir"] = str(game_dir)

    with (
        patch("pr_meta.server.scrape", new_callable=AsyncMock, return_value=None),
        patch(
            "pr_meta.server.download_media",
            new_callable=AsyncMock,
            return_value={"image": None, "video": None},
        ),
    ):
        await handle_event(event, games_root=tmp_path)

    # meta.json should still be written with badge/binary from event
    meta_path = game_dir / "pr-meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert meta["badge"] == "NATIVE"
    assert meta["title"] == "Super Mario 64"


# --- Additions beyond the plan -------------------------------------------------


def _games(gamelist_path):
    return ET.parse(gamelist_path).getroot().findall("game")


async def _install(tmp_path, event, scraped=SCRAPED_META, media=DOWNLOAD_RESULT):
    with (
        patch("pr_meta.server.scrape", new_callable=AsyncMock, return_value=scraped),
        patch("pr_meta.server.download_media", new_callable=AsyncMock, return_value=media),
    ):
        await handle_event(event, games_root=tmp_path)


@pytest.mark.asyncio
async def test_gamelist_paths_are_relative_to_platform_dir(tmp_path):
    """ES-DE resolves gamelist.xml paths against the platform dir, while
    pr-meta.json media paths are relative to the game dir."""
    game_dir = tmp_path / "n64" / "Super Mario 64"
    game_dir.mkdir(parents=True)
    event = dict(INSTALL_EVENT, game_dir=str(game_dir))

    await _install(tmp_path, event)

    (game,) = _games(tmp_path / "n64" / "gamelist.xml")
    assert game.findtext("path") == "./Super Mario 64/sm64.x86_64"
    assert game.findtext("image") == "./Super Mario 64/media/cover.png"
    assert game.findtext("video") == "./Super Mario 64/media/video.mp4"
    meta = json.loads((game_dir / "pr-meta.json").read_text())
    assert meta["image"] == "./media/cover.png"


@pytest.mark.asyncio
async def test_reinstall_with_native_binary_reuses_entry(tmp_path):
    """EMU install (no binary) followed by a native re-install must not
    leave two <game> entries for the same folder."""
    game_dir = tmp_path / "n64" / "Banjo-Kazooie"
    game_dir.mkdir(parents=True)
    emu = {
        "event": "game_installed",
        "platform": "n64",
        "title": "Banjo-Kazooie",
        "rom_hash": "abc123",
        "game_dir": str(game_dir),
        "badge": "EMU",
        "core": "mupen64plus_next",
        "binary": "",
    }
    await _install(tmp_path, emu, media={"image": None, "video": None})
    native = dict(emu, badge="NATIVE", core=None, binary="./bk.x86_64")
    await _install(tmp_path, native, media={"image": None, "video": None})

    games = _games(tmp_path / "n64" / "gamelist.xml")
    assert len(games) == 1
    assert games[0].findtext("path") == "./Banjo-Kazooie/bk.x86_64"
    assert games[0].findtext("pr_badge") == "NATIVE"
    assert games[0].findtext("pr_core") == ""


@pytest.mark.asyncio
async def test_building_badge_before_install_yields_single_entry(tmp_path):
    """pr-builder may report BUILDING before the game is installed."""
    building = dict(BADGE_EVENT, badge="BUILDING", progress=42)
    await handle_event(building, games_root=tmp_path)

    game_dir = tmp_path / "n64" / "Super Mario 64"
    game_dir.mkdir(parents=True, exist_ok=True)
    await _install(tmp_path, dict(INSTALL_EVENT, game_dir=str(game_dir)))

    games = _games(tmp_path / "n64" / "gamelist.xml")
    assert len(games) == 1
    assert games[0].findtext("path") == "./Super Mario 64/sm64.x86_64"
    assert games[0].findtext("pr_badge") == "NATIVE"


async def _send(sock_path, payload: bytes, *, half_close: bool) -> None:
    reader, writer = await asyncio.open_unix_connection(sock_path)
    writer.write(payload)
    await writer.drain()
    if half_close:
        writer.write_eof()
    # The server closes the connection once the event has been processed.
    await asyncio.wait_for(reader.read(), timeout=5)
    writer.close()
    await writer.wait_closed()


@pytest.mark.asyncio
async def test_socket_server_end_to_end(tmp_path):
    """Real Unix-socket round trip: garbage is ignored, install + badge events
    are processed, and the server keeps serving between connections."""
    sock_path = str(tmp_path / "pr-meta.sock")
    game_dir = tmp_path / "n64" / "Super Mario 64"
    game_dir.mkdir(parents=True)

    with (
        patch("pr_meta.server.scrape", new_callable=AsyncMock, return_value=SCRAPED_META),
        patch(
            "pr_meta.server.download_media", new_callable=AsyncMock, return_value=DOWNLOAD_RESULT
        ),
    ):
        server = asyncio.create_task(_serve(sock_path, tmp_path))
        try:
            for _ in range(200):
                if (tmp_path / "pr-meta.sock").exists():
                    break
                await asyncio.sleep(0.01)
            await _send(sock_path, b"not json", half_close=True)
            install = dict(INSTALL_EVENT, game_dir=str(game_dir))
            await _send(sock_path, json.dumps(install).encode(), half_close=True)
            # Client that keeps its write side open must still be served.
            badge = dict(BADGE_EVENT, badge="BUILDING", progress=10)
            await _send(sock_path, json.dumps(badge).encode(), half_close=False)
        finally:
            server.cancel()
            with pytest.raises(asyncio.CancelledError):
                await server

    (game,) = _games(tmp_path / "n64" / "gamelist.xml")
    assert game.findtext("name") == "Super Mario 64"
    assert game.findtext("pr_badge") == "BUILDING"
    assert json.loads((game_dir / "pr-meta.json").read_text())["badge"] == "BUILDING"


@pytest.mark.asyncio
async def test_full_pipeline_badge_flips_emu_to_native(tmp_path):
    """Simulate: game installed as EMU, then build completes and badge flips to NATIVE."""
    game_dir = tmp_path / "n64" / "Banjo-Kazooie"
    game_dir.mkdir(parents=True)

    # Step 1: install as EMU (no build project found)
    install_emu = {
        "event": "game_installed",
        "platform": "n64",
        "title": "Banjo-Kazooie",
        "rom_hash": "abc123",
        "game_dir": str(game_dir),
        "badge": "EMU",
        "core": "mupen64plus_next",
        "binary": "",
    }

    emu_meta = {
        "title": "Banjo-Kazooie",
        "year": 1998,
        "genre": "Platform",
        "publisher": "Nintendo",
        "developer": "Rare",
        "description": "Collect jiggies.",
        "rating": 0.92,
        "players": 1,
        "image_url": None,
        "video_url": None,
    }

    with (
        patch("pr_meta.server.scrape", new_callable=AsyncMock, return_value=emu_meta),
        patch(
            "pr_meta.server.download_media",
            new_callable=AsyncMock,
            return_value={"image": None, "video": None},
        ),
    ):
        await handle_event(install_emu, games_root=tmp_path)

    gamelist_path = tmp_path / "n64" / "gamelist.xml"
    assert "<pr_badge>EMU</pr_badge>" in gamelist_path.read_text()

    # Step 2: build completes — flip badge to NATIVE
    flip_event = {
        "event": "badge_update",
        "platform": "n64",
        "title": "Banjo-Kazooie",
        "game_dir": str(game_dir),
        "badge": "NATIVE",
        "core": None,
        "progress": None,
    }
    await handle_event(flip_event, games_root=tmp_path)

    content = gamelist_path.read_text()
    assert "<pr_badge>NATIVE</pr_badge>" in content
    assert "<pr_badge>EMU</pr_badge>" not in content

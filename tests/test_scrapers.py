from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from pr_meta.scrapers import scrape
from pr_meta.scrapers.igdb import IGDBClient
from pr_meta.scrapers.screenscraper import ScreenScraperClient
from pr_meta.scrapers.thegamesdb import TheGamesDBClient

SCREENSCRAPER_RESPONSE = {
    "response": {
        "jeu": {
            "noms": [{"region": "us", "text": "Super Mario 64"}],
            "dates": [{"region": "us", "text": "1996-06-23"}],
            "genres": [{"noms": [{"langue": "en", "text": "Platform"}]}],
            "editeur": {"text": "Nintendo"},
            "developpeur": {"text": "Nintendo"},
            "synopsis": [{"langue": "en", "text": "Guide Mario through 15 courses."}],
            "note": {"text": "19/20"},
            "joueurs": {"text": "1"},
            "medias": [
                {"type": "box-2D", "url": "https://ss.fr/cover.png", "region": "us"},
                {"type": "video", "url": "https://ss.fr/video.mp4", "region": "us"},
            ],
        }
    }
}


def _make_mock_session(json_response):
    resp = AsyncMock()
    resp.status = 200
    resp.json = AsyncMock(return_value=json_response)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)

    session = AsyncMock()
    session.get = MagicMock(return_value=resp)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.mark.asyncio
async def test_screenscraper_returns_normalized_meta():
    client = ScreenScraperClient(devid="testdev", devpassword="testpass", softname="pr-meta")
    with patch(
        "pr_meta.scrapers.screenscraper.aiohttp.ClientSession",
        return_value=_make_mock_session(SCREENSCRAPER_RESPONSE),
    ):
        result = await client.scrape(platform="n64", title="Super Mario 64")

    assert result is not None
    assert result["title"] == "Super Mario 64"
    assert result["year"] == 1996
    assert result["genre"] == "Platform"
    assert result["publisher"] == "Nintendo"
    assert result["developer"] == "Nintendo"
    assert result["description"] == "Guide Mario through 15 courses."
    assert abs(result["rating"] - 0.95) < 0.01
    assert result["players"] == 1
    assert result["image_url"] == "https://ss.fr/cover.png"
    assert result["video_url"] == "https://ss.fr/video.mp4"


@pytest.mark.asyncio
async def test_screenscraper_returns_none_on_404():
    resp = AsyncMock()
    resp.status = 404
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    session = AsyncMock()
    session.get = MagicMock(return_value=resp)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    client = ScreenScraperClient(devid="testdev", devpassword="testpass", softname="pr-meta")
    with patch("pr_meta.scrapers.screenscraper.aiohttp.ClientSession", return_value=session):
        result = await client.scrape(platform="n64", title="Unknown Game")

    assert result is None


@pytest.mark.asyncio
async def test_screenscraper_returns_none_on_missing_jeu():
    client = ScreenScraperClient(devid="testdev", devpassword="testpass", softname="pr-meta")
    with patch(
        "pr_meta.scrapers.screenscraper.aiohttp.ClientSession",
        return_value=_make_mock_session({"response": {}}),
    ):
        result = await client.scrape(platform="n64", title="Missing Game")
    assert result is None


IGDB_TOKEN_RESPONSE = {"access_token": "mock_token_123", "expires_in": 3600}

IGDB_GAME_RESPONSE = [
    {
        "name": "Super Mario 64",
        "first_release_date": 835473600,  # 1996-06-23 UTC epoch
        "genres": [{"name": "Platform"}],
        "involved_companies": [
            {"company": {"name": "Nintendo"}, "publisher": True, "developer": True}
        ],
        "summary": "Guide Mario through 15 courses.",
        "rating": 95.0,
        "cover": {"url": "//images.igdb.com/cover.jpg"},
    }
]


def _make_igdb_session(token_resp, game_resp):
    token_response = AsyncMock()
    token_response.status = 200
    token_response.json = AsyncMock(return_value=token_resp)
    token_response.__aenter__ = AsyncMock(return_value=token_response)
    token_response.__aexit__ = AsyncMock(return_value=False)

    game_response = AsyncMock()
    game_response.status = 200
    game_response.json = AsyncMock(return_value=game_resp)
    game_response.__aenter__ = AsyncMock(return_value=game_response)
    game_response.__aexit__ = AsyncMock(return_value=False)

    session = AsyncMock()
    call_count = {"n": 0}

    def side_effect(*args, **kwargs):
        if call_count["n"] == 0:
            call_count["n"] += 1
            return token_response
        return game_response

    session.post = MagicMock(side_effect=side_effect)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.mark.asyncio
async def test_igdb_returns_normalized_meta():
    client = IGDBClient(client_id="test_id", client_secret="test_secret")
    with patch(
        "pr_meta.scrapers.igdb.aiohttp.ClientSession",
        return_value=_make_igdb_session(IGDB_TOKEN_RESPONSE, IGDB_GAME_RESPONSE),
    ):
        result = await client.scrape(platform="n64", title="Super Mario 64")

    assert result is not None
    assert result["title"] == "Super Mario 64"
    assert result["year"] == 1996
    assert result["genre"] == "Platform"
    assert result["publisher"] == "Nintendo"
    assert abs(result["rating"] - 0.95) < 0.01
    assert "igdb.com" in result["image_url"]


@pytest.mark.asyncio
async def test_igdb_returns_none_on_empty_response():
    client = IGDBClient(client_id="test_id", client_secret="test_secret")
    with patch(
        "pr_meta.scrapers.igdb.aiohttp.ClientSession",
        return_value=_make_igdb_session(IGDB_TOKEN_RESPONSE, []),
    ):
        result = await client.scrape(platform="n64", title="Unknown")
    assert result is None


TGDB_RESPONSE = {
    "data": {
        "games": [
            {
                "id": 1,
                "game_title": "Super Mario 64",
                "release_date": "1996-06-23",
                "genres": [9],
                "publishers": [{"name": "Nintendo"}],
                "developers": [{"name": "Nintendo"}],
                "overview": "Guide Mario through 15 courses.",
                "rating": "9/10",
                "players": "1",
            }
        ]
    },
    "include": {
        "genres": {"data": {"9": {"genre": "Platform"}}},
        "boxart": {
            "data": {
                "1": [{"filename": "boxart/front/1-1.jpg", "side": "front", "type": "boxart"}]
            },
            "base_url": {"original": "https://cdn.thegamesdb.net/images/original/"},
        },
    },
}


@pytest.mark.asyncio
async def test_thegamesdb_returns_normalized_meta():
    client = TheGamesDBClient(api_key="test_key")
    with patch(
        "pr_meta.scrapers.thegamesdb.aiohttp.ClientSession",
        return_value=_make_mock_session(TGDB_RESPONSE),
    ):
        result = await client.scrape(platform="n64", title="Super Mario 64")

    assert result is not None
    assert result["title"] == "Super Mario 64"
    assert result["year"] == 1996
    assert result["genre"] == "Platform"
    assert result["publisher"] == "Nintendo"
    assert result["image_url"].endswith(".jpg")


@pytest.mark.asyncio
async def test_thegamesdb_returns_none_on_empty():
    empty = {"data": {"games": []}, "include": {}}
    client = TheGamesDBClient(api_key="test_key")
    with patch(
        "pr_meta.scrapers.thegamesdb.aiohttp.ClientSession",
        return_value=_make_mock_session(empty),
    ):
        result = await client.scrape(platform="n64", title="Unknown")
    assert result is None


MINIMAL_META = {
    "title": "Super Mario 64",
    "year": 1996,
    "genre": "Platform",
    "publisher": "Nintendo",
    "developer": "Nintendo",
    "description": "Guide Mario.",
    "rating": 0.95,
    "players": 1,
    "image_url": "https://example.com/cover.png",
    "video_url": None,
}


@pytest.mark.asyncio
async def test_scrape_returns_screenscraper_result_when_available():
    with (
        patch(
            "pr_meta.scrapers.ScreenScraperClient.scrape",
            new_callable=AsyncMock,
            return_value=MINIMAL_META,
        ) as ss_mock,
        patch(
            "pr_meta.scrapers.IGDBClient.scrape", new_callable=AsyncMock, return_value=None
        ) as igdb_mock,
        patch(
            "pr_meta.scrapers.TheGamesDBClient.scrape", new_callable=AsyncMock, return_value=None
        ),
    ):
        result = await scrape(platform="n64", title="Super Mario 64")
    assert result["title"] == "Super Mario 64"
    ss_mock.assert_called_once()
    igdb_mock.assert_not_called()


@pytest.mark.asyncio
async def test_scrape_falls_back_to_igdb_when_screenscraper_none():
    with (
        patch(
            "pr_meta.scrapers.ScreenScraperClient.scrape", new_callable=AsyncMock, return_value=None
        ),
        patch(
            "pr_meta.scrapers.IGDBClient.scrape", new_callable=AsyncMock, return_value=MINIMAL_META
        ) as igdb_mock,
        patch(
            "pr_meta.scrapers.TheGamesDBClient.scrape", new_callable=AsyncMock, return_value=None
        ),
    ):
        result = await scrape(platform="n64", title="Super Mario 64")
    assert result["title"] == "Super Mario 64"
    igdb_mock.assert_called_once()


@pytest.mark.asyncio
async def test_scrape_falls_back_to_thegamesdb_as_last_resort():
    with (
        patch(
            "pr_meta.scrapers.ScreenScraperClient.scrape", new_callable=AsyncMock, return_value=None
        ),
        patch("pr_meta.scrapers.IGDBClient.scrape", new_callable=AsyncMock, return_value=None),
        patch(
            "pr_meta.scrapers.TheGamesDBClient.scrape",
            new_callable=AsyncMock,
            return_value=MINIMAL_META,
        ) as tgdb_mock,
    ):
        result = await scrape(platform="n64", title="Super Mario 64")
    assert result["title"] == "Super Mario 64"
    tgdb_mock.assert_called_once()


@pytest.mark.asyncio
async def test_scrape_returns_none_when_all_fail():
    with (
        patch(
            "pr_meta.scrapers.ScreenScraperClient.scrape", new_callable=AsyncMock, return_value=None
        ),
        patch("pr_meta.scrapers.IGDBClient.scrape", new_callable=AsyncMock, return_value=None),
        patch(
            "pr_meta.scrapers.TheGamesDBClient.scrape", new_callable=AsyncMock, return_value=None
        ),
    ):
        result = await scrape(platform="n64", title="Super Mario 64")
    assert result is None


@pytest.mark.asyncio
async def test_scrape_falls_through_when_a_scraper_raises():
    """Network errors / bad credentials in one source must not abort the chain."""
    with (
        patch(
            "pr_meta.scrapers.ScreenScraperClient.scrape",
            new_callable=AsyncMock,
            side_effect=aiohttp.ClientConnectionError("offline"),
        ),
        patch(
            "pr_meta.scrapers.IGDBClient.scrape",
            new_callable=AsyncMock,
            side_effect=KeyError("access_token"),
        ),
        patch(
            "pr_meta.scrapers.TheGamesDBClient.scrape",
            new_callable=AsyncMock,
            return_value=MINIMAL_META,
        ) as tgdb_mock,
    ):
        result = await scrape(platform="n64", title="Super Mario 64")
    assert result["title"] == "Super Mario 64"
    tgdb_mock.assert_called_once()


@pytest.mark.asyncio
async def test_screenscraper_unknown_platform_skips_http():
    client = ScreenScraperClient(devid="testdev", devpassword="testpass", softname="pr-meta")
    with patch("pr_meta.scrapers.screenscraper.aiohttp.ClientSession") as session_cls:
        result = await client.scrape(platform="atari2600", title="Pitfall!")
    assert result is None
    session_cls.assert_not_called()


@pytest.mark.parametrize(
    "note, expected",
    [("19/20", 0.95), ("0.8", 0.8), ("n/a", None), ("1/0", None), ("", None), (None, None)],
)
def test_screenscraper_parse_rating(note, expected):
    from pr_meta.scrapers.screenscraper import _parse_rating

    assert _parse_rating(note) == expected


@pytest.mark.asyncio
async def test_screenscraper_falls_back_to_first_region_and_language():
    response = {
        "response": {
            "jeu": {
                "noms": [{"region": "jp", "text": "Super Mario 64 (JP)"}],
                "dates": [{"region": "jp", "text": "1996"}],
                "genres": [{"noms": [{"langue": "fr", "text": "Plateforme"}]}],
                "synopsis": [{"langue": "fr", "text": "Guidez Mario."}],
                "joueurs": {"text": "1-2"},
                "medias": [],
            }
        }
    }
    client = ScreenScraperClient(devid="testdev", devpassword="testpass", softname="pr-meta")
    with patch(
        "pr_meta.scrapers.screenscraper.aiohttp.ClientSession",
        return_value=_make_mock_session(response),
    ):
        result = await client.scrape(platform="n64", title="Super Mario 64")

    assert result["title"] == "Super Mario 64 (JP)"
    assert result["year"] == 1996
    assert result["genre"] == "Plateforme"
    assert result["description"] == "Guidez Mario."
    assert result["players"] is None  # non-integer player count is dropped
    assert result["rating"] is None
    assert result["image_url"] is None
    assert result["video_url"] is None

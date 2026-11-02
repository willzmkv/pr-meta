import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from pr_meta.scrapers.igdb import IGDBClient
from pr_meta.scrapers.screenscraper import ScreenScraperClient


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

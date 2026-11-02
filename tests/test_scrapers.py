import pytest
from unittest.mock import AsyncMock, patch, MagicMock

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

from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from pr_meta.downloader import download_media


@pytest.fixture
def fake_image_bytes():
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # fake PNG header


@pytest.fixture
def fake_video_bytes():
    return b"\x00\x00\x00\x18ftyp" + b"\x00" * 100  # fake MP4 header


@pytest.mark.asyncio
async def test_download_media_creates_files(tmp_path, fake_image_bytes, fake_video_bytes):
    game_dir = tmp_path / "Super Mario 64"
    game_dir.mkdir()
    media_dir = game_dir / "media"

    image_url = "https://example.com/cover.png"
    video_url = "https://example.com/video.mp4"

    call_count = {"n": 0}
    responses = [fake_image_bytes, fake_video_bytes]

    def mock_get(url, **kwargs):
        resp = AsyncMock()
        resp.status = 200
        resp.read = AsyncMock(return_value=responses[call_count["n"]])
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=False)
        call_count["n"] += 1
        return resp

    with patch("pr_meta.downloader.aiohttp.ClientSession") as mock_session_cls:
        session_instance = AsyncMock()
        session_instance.get = mock_get
        session_instance.__aenter__ = AsyncMock(return_value=session_instance)
        session_instance.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = session_instance

        result = await download_media(game_dir, image_url=image_url, video_url=video_url)

    assert result["image"] == "./media/cover.png"
    assert result["video"] == "./media/video.mp4"
    assert (media_dir / "cover.png").exists()
    assert (media_dir / "video.mp4").exists()


@pytest.mark.asyncio
async def test_download_media_skips_none_urls(tmp_path):
    game_dir = tmp_path / "Game"
    game_dir.mkdir()

    with patch("pr_meta.downloader.aiohttp.ClientSession") as mock_session_cls:
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await download_media(game_dir, image_url=None, video_url=None)

    assert result["image"] is None
    assert result["video"] is None
    assert not (game_dir / "media").exists()


@pytest.mark.asyncio
async def test_download_media_handles_http_error(tmp_path):
    game_dir = tmp_path / "Game"
    game_dir.mkdir()

    def mock_get_error(url, **kwargs):
        resp = AsyncMock()
        resp.status = 404
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=False)
        return resp

    with patch("pr_meta.downloader.aiohttp.ClientSession") as mock_session_cls:
        session_instance = AsyncMock()
        session_instance.get = mock_get_error
        session_instance.__aenter__ = AsyncMock(return_value=session_instance)
        session_instance.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = session_instance

        result = await download_media(
            game_dir, image_url="https://example.com/cover.png", video_url=None
        )

    assert result["image"] is None


@pytest.mark.asyncio
async def test_download_media_network_error_is_non_fatal(tmp_path, fake_video_bytes):
    """A connection error on one asset must not abort the others (offline box)."""
    game_dir = tmp_path / "Game"
    game_dir.mkdir()

    def mock_get(url, **kwargs):
        if url.endswith(".png"):
            raise aiohttp.ClientConnectionError("network down")
        resp = AsyncMock()
        resp.status = 200
        resp.read = AsyncMock(return_value=fake_video_bytes)
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=False)
        return resp

    with patch("pr_meta.downloader.aiohttp.ClientSession") as mock_session_cls:
        session_instance = AsyncMock()
        session_instance.get = mock_get
        session_instance.__aenter__ = AsyncMock(return_value=session_instance)
        session_instance.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = session_instance

        result = await download_media(
            game_dir,
            image_url="https://example.com/cover.png",
            video_url="https://example.com/video.mp4",
        )

    assert result["image"] is None
    assert result["video"] == "./media/video.mp4"
    assert (game_dir / "media" / "video.mp4").exists()

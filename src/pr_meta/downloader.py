from __future__ import annotations

import logging
from pathlib import Path

import aiofiles
import aiohttp

logger = logging.getLogger(__name__)


async def download_media(
    game_dir: Path | str,
    *,
    image_url: str | None,
    video_url: str | None,
) -> dict[str, str | None]:
    """Download cover art and video preview into game_dir/media/.

    Returns a dict with keys 'image' and 'video', each either a relative
    path string (e.g. './media/cover.png') or None if not downloaded.
    """
    game_dir = Path(game_dir)
    result: dict[str, str | None] = {"image": None, "video": None}

    downloads: list[tuple[str, str, str]] = []
    if image_url:
        downloads.append(("image", image_url, "cover.png"))
    if video_url:
        downloads.append(("video", video_url, "video.mp4"))

    if not downloads:
        return result

    media_dir = game_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        for key, url, filename in downloads:
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        continue
                    content = await resp.read()
            except (aiohttp.ClientError, TimeoutError) as exc:
                # Network failures are non-fatal: the game still gets its
                # pr-meta.json / gamelist entry, just without this asset.
                logger.warning("Download failed for %s: %s", url, exc)
                continue
            dest = media_dir / filename
            async with aiofiles.open(dest, "wb") as f:
                await f.write(content)
            result[key] = f"./media/{filename}"

    return result

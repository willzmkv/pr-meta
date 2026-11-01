# pr-meta

> Project-R metadata scraper — fetches game info from ScreenScraper/IGDB/TheGamesDB and writes ES-DE gamelist.xml.

**Language:** Python 3.11+ · **Status:** Pre-alpha · [Implementation Plan](https://github.com/willzmkv/project-r-os/blob/main/ROADMAP.md#pr-meta--metadata-scraper--es-de)

## What it does

Listens for `game_installed` events from pr-builder. Scrapes metadata (name, description, cover art, video) from ScreenScraper → IGDB → TheGamesDB (priority chain). Writes ES-DE-compatible `gamelist.xml` entries with IHC badge tags.

## IHC Badges

| Badge | Color | Meaning |
|---|---|---|
| NATIVE | `#4ecdc4` | Native recompiled binary |
| EMU | `#f5a623` | RetroArch / standalone emulator |
| IN PROGRESS | `#4a9eff` | Build running |
| BUILD ERROR | `#e94560` | Build failed |

## Architecture

- `meta_writer.py` — read/write `pr-meta.json` per game
- `gamelist.py` — ES-DE gamelist.xml upsert
- `downloader.py` — async cover art + video downloader
- `scrapers/` — ScreenScraper, IGDB, TheGamesDB clients + priority chain
- `badges.py` — Badge enum with IHC hex colors
- `server.py` — asyncio Unix socket server at `/run/project-r/pr-meta.sock`

## License

GPL-3.0

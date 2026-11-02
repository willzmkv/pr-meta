# pr-meta

> Project-R metadata scraper — fetches game info from ScreenScraper/IGDB/TheGamesDB and writes ES-DE gamelist.xml.

**Language:** Python 3.11+ · **Status:** Pre-alpha · [Implementation Plan](https://github.com/willzmkv/project-r-os/blob/main/ROADMAP.md#pr-meta--metadata-scraper--es-de)

## What it does

Listens on a Unix socket for events from `pr-builder`:

- **`game_installed`** — scrapes metadata (name, description, cover art, video) from
  ScreenScraper → IGDB → TheGamesDB (first hit wins), downloads media into the game's
  `media/` folder, writes the canonical `pr-meta.json`, and upserts the game's `<game>`
  entry (with IHC badge tags) in the platform's ES-DE `gamelist.xml`.
- **`badge_update`** — flips `pr_badge` / `pr_core` in `gamelist.xml` and `pr-meta.json`
  (e.g. `EMU → BUILDING → NATIVE`) without re-scraping.

pr-meta only rewrites `gamelist.xml` in place; it never restarts the frontend. Picking up
the change live is left to ES-DE's own file watch.

Scraping is best-effort: if every source misses or fails (offline, missing credentials),
the game still gets its `pr-meta.json` and `gamelist.xml` entry, just without the scraped
fields and media.

## IHC Badges

Canonical values live in `pr_meta.badges` (`Badge` enum + `BADGE_COLORS`); import them
rather than hard-coding hex strings.

| Badge | Color | Meaning |
|---|---|---|
| `NATIVE` | `#4ecdc4` | Native recompiled binary |
| `EMU` | `#f5a623` | RetroArch / standalone emulator (informative, not an error) |
| `BUILDING` | `#4a9eff` | Build running |
| `BUILD ERROR` | `#e94560` | Build failed — action required |

## IPC contract

pr-meta owns this contract; `pr-builder` is the client.

### Transport

| | |
|---|---|
| Socket | Unix stream socket at **`/run/project-r/pr-meta.sock`** (override with `PR_META_SOCKET`) |
| Permissions | `0660` — clients must share the service's group |
| Framing | **One UTF-8 JSON object per connection**, max 64 KiB. Send it, then close (or `shutdown(SHUT_WR)`). A message split across several writes is reassembled. |
| Reply | None. The server closes the connection once the event has been fully processed, so a client *may* read until EOF to wait for completion (optional). |
| Errors | Malformed JSON, missing required fields and unknown `event` values are logged and dropped; the server keeps serving. |

Minimal client:

```python
import json, socket

with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    s.connect("/run/project-r/pr-meta.sock")
    s.sendall(json.dumps(event).encode("utf-8"))
    s.shutdown(socket.SHUT_WR)
    s.recv(1)  # optional: returns b"" once pr-meta has finished processing
```

### `game_installed`

```json
{
  "event": "game_installed",
  "platform": "n64",
  "title": "Super Mario 64",
  "rom_hash": "20b854b239203baf6354e9f5e5ea9bc7",
  "game_dir": "/home/arcade/games/n64/Super Mario 64",
  "badge": "NATIVE",
  "core": null,
  "binary": "./sm64.x86_64"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `event` | `"game_installed"` | yes | |
| `platform` | string | yes | Platform slug = folder under the games root (`n64`, `ps1`, `ps2`, `snes`, `gba`, `md`, `nes`, `gb`, `gbc`, `saturn`, `dreamcast`, `gamecube`, `wii`, `xbox`, `ps3`). |
| `title` | string | yes | Display name; also the scrape query. |
| `rom_hash` | string | no | ROM MD5. Accepted, currently unused by the scrapers. |
| `game_dir` | string | no | Absolute game folder. Default: `$PR_GAMES_ROOT/{platform}/{title}`. Must sit directly under `$PR_GAMES_ROOT/{platform}/` for ES-DE paths to resolve. |
| `badge` | `"NATIVE"` \| `"EMU"` \| `"BUILDING"` \| `"BUILD ERROR"` | no | Default `"EMU"`. |
| `core` | string \| null | no | RetroArch core for EMU games (e.g. `"mupen64plus_next"`). |
| `binary` | string | no | Launch file **relative to `game_dir`** (`"./sm64.x86_64"`, or the ROM/cue for EMU). `""` = the game folder itself. |

Re-sending `game_installed` for the same game folder (e.g. with the native `binary` after
a build finishes) re-scrapes and **updates the existing entry in place**, re-pathing it
if `binary` changed; it never creates a duplicate.

### `badge_update`

```json
{
  "event": "badge_update",
  "platform": "n64",
  "title": "Super Mario 64",
  "game_dir": "/home/arcade/games/n64/Super Mario 64",
  "badge": "BUILDING",
  "core": null,
  "progress": 42
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `event` | `"badge_update"` | yes | |
| `platform` | string | yes | |
| `title` | string | yes | |
| `game_dir` | string | no | Same default as above. |
| `badge` | `"NATIVE"` \| `"EMU"` \| `"BUILDING"` \| `"BUILD ERROR"` | no | Default `"EMU"`. |
| `core` | string \| null | no | `null`/`""` clears `pr_core`. |
| `progress` | int (0–100) \| null | no | Accepted; not yet persisted. |

Never triggers scraping or downloads. Updates `badge`/`core` in `pr-meta.json` if it exists
and `pr_badge`/`pr_core` on the game's `gamelist.xml` entry (creating a minimal entry if the
game is not installed yet — a later `game_installed` takes that entry over).

## Outputs

**`{game_dir}/pr-meta.json`** — canonical per-game record (media paths relative to `game_dir`):

```json
{
  "title": "Super Mario 64",
  "platform": "n64",
  "badge": "NATIVE",
  "core": null,
  "binary": "./sm64.x86_64",
  "year": 1996,
  "genre": "Platform",
  "publisher": "Nintendo",
  "developer": "Nintendo",
  "description": "Guide Mario through 15 courses.",
  "rating": 0.95,
  "players": 1,
  "image": "./media/cover.png",
  "video": "./media/video.mp4"
}
```

`year`…`players` are only present when a scraper hit; `image`/`video` are `null` when
nothing was downloaded.

**`$PR_GAMES_ROOT/{platform}/gamelist.xml`** — ES-DE format, paths relative to the platform dir:

```xml
<game>
  <path>./Super Mario 64/sm64.x86_64</path>
  <name>Super Mario 64</name>
  <desc>Guide Mario through 15 courses.</desc>
  <image>./Super Mario 64/media/cover.png</image>
  <video>./Super Mario 64/media/video.mp4</video>
  <releasedate>19960101T000000</releasedate>
  <developer>Nintendo</developer>
  <publisher>Nintendo</publisher>
  <genre>Platform</genre>
  <players>1</players>
  <rating>0.95</rating>
  <pr_badge>NATIVE</pr_badge>
  <pr_core></pr_core>
</game>
```

## Configuration

All settings come from the environment — no credentials live in this repo.

| Variable | Default | Purpose |
|---|---|---|
| `PR_META_SOCKET` | `/run/project-r/pr-meta.sock` | Socket path |
| `PR_GAMES_ROOT` | `~/games` | Library root (`{root}/{platform}/{title}/`) |
| `SS_DEVID`, `SS_DEVPASSWORD` | empty | ScreenScraper.fr developer credentials |
| `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET` | empty | Twitch app credentials for IGDB |
| `TGDB_APIKEY` | empty | TheGamesDB API key |

A source without credentials simply misses and the chain falls through.

Run: `pr-meta` (console script → `pr_meta.server:main`).

## Architecture

- `server.py` — asyncio Unix socket server; routes events, runs the pipeline
- `scrapers/` — ScreenScraper, IGDB, TheGamesDB clients + priority chain (`scrape()`)
- `downloader.py` — async cover art + video downloader
- `meta_writer.py` — read/write `pr-meta.json` per game
- `gamelist.py` — ES-DE `gamelist.xml` read/upsert/write
- `badges.py` — `Badge` enum with IHC hex colors

## Development

Tests mock every HTTP call (no real ScreenScraper/IGDB/TheGamesDB traffic) and need Linux
for the Unix-socket tests. On the Project-R dev box:

```bash
docker run --rm -v "$PWD:/src" -w /src project-r-dev \
  bash -c "pip install -q -e '.[dev]' && pytest -v && ruff check . && black --check ."
```

## License

GPL-3.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_META_FILENAME = "pr-meta.json"


def write_meta(game_dir: Path | str, meta: dict[str, Any]) -> None:
    """Write pr-meta.json into game_dir, overwriting any existing file."""
    path = Path(game_dir) / _META_FILENAME
    path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def read_meta(game_dir: Path | str) -> dict[str, Any] | None:
    """Read pr-meta.json from game_dir. Returns None if file is missing."""
    path = Path(game_dir) / _META_FILENAME
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

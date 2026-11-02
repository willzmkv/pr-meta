from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


EMPTY_GAMELIST_XML = '<?xml version="1.0" encoding="utf-8"?>\n<gameList>\n</gameList>\n'

# Fields written in order for readability.
_ORDERED_FIELDS = [
    "path",
    "name",
    "desc",
    "image",
    "video",
    "releasedate",
    "developer",
    "publisher",
    "genre",
    "players",
    "rating",
    "pr_badge",
    "pr_core",
]


def read_gamelist(path: Path) -> ET.Element:
    """Read gamelist.xml and return the root <gameList> element.
    If the file does not exist, return an empty <gameList> root."""
    if not path.exists():
        return ET.fromstring(EMPTY_GAMELIST_XML)
    return ET.parse(path).getroot()


def upsert_game(root: ET.Element, fields: dict[str, str]) -> None:
    """Insert or update a <game> entry in *root* identified by <path>.

    If a <game> with the same <path> already exists, only the keys present
    in *fields* are updated; other sub-elements are left intact.
    """
    game_path = fields.get("path")
    if not game_path:
        raise ValueError("fields must include 'path'")

    # Find existing entry by path value.
    existing: ET.Element | None = None
    for game in root.findall("game"):
        p = game.find("path")
        if p is not None and p.text == game_path:
            existing = game
            break

    if existing is None:
        existing = ET.SubElement(root, "game")

    for key in _ORDERED_FIELDS:
        if key not in fields:
            continue
        el = existing.find(key)
        if el is None:
            el = ET.SubElement(existing, key)
        el.text = str(fields[key]) if fields[key] is not None else ""


def write_gamelist(path: Path, root: ET.Element) -> None:
    """Write *root* to *path* as a well-formed XML file with declaration.

    Empty fields are written as explicit open/close tags (``<pr_core></pr_core>``)
    rather than self-closing ones, matching the layout ES-DE itself produces.
    """
    ET.indent(root, space="  ")
    tree = ET.ElementTree(root)
    tree.write(path, encoding="utf-8", xml_declaration=True, short_empty_elements=False)

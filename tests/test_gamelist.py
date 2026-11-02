import xml.etree.ElementTree as ET

from pr_meta.gamelist import upsert_game, read_gamelist, write_gamelist, EMPTY_GAMELIST_XML


GAME_ENTRY = {
    "path": "./Super Mario 64/sm64.x86_64",
    "name": "Super Mario 64",
    "desc": "Guide Mario through 15 courses.",
    "image": "./Super Mario 64/media/cover.png",
    "video": "./Super Mario 64/media/video.mp4",
    "releasedate": "19960623T000000",
    "developer": "Nintendo",
    "publisher": "Nintendo",
    "genre": "Platform",
    "players": "1",
    "rating": "0.95",
    "pr_badge": "NATIVE",
    "pr_core": "",
}


def test_empty_gamelist_is_valid_xml():
    tree = ET.fromstring(EMPTY_GAMELIST_XML)
    assert tree.tag == "gameList"


def test_upsert_adds_new_game(tmp_path):
    gamelist_path = tmp_path / "gamelist.xml"
    gamelist_path.write_text(EMPTY_GAMELIST_XML, encoding="utf-8")
    tree = read_gamelist(gamelist_path)
    upsert_game(tree, GAME_ENTRY)
    games = tree.findall("game")
    assert len(games) == 1
    assert games[0].find("name").text == "Super Mario 64"


def test_upsert_updates_existing_game(tmp_path):
    gamelist_path = tmp_path / "gamelist.xml"
    gamelist_path.write_text(EMPTY_GAMELIST_XML, encoding="utf-8")
    tree = read_gamelist(gamelist_path)
    upsert_game(tree, GAME_ENTRY)
    updated = dict(GAME_ENTRY)
    updated["pr_badge"] = "EMU"
    updated["pr_core"] = "mupen64plus_next"
    upsert_game(tree, updated)
    games = tree.findall("game")
    assert len(games) == 1  # not duplicated
    assert games[0].find("pr_badge").text == "EMU"
    assert games[0].find("pr_core").text == "mupen64plus_next"


def test_write_gamelist_creates_file(tmp_path):
    gamelist_path = tmp_path / "gamelist.xml"
    gamelist_path.write_text(EMPTY_GAMELIST_XML, encoding="utf-8")
    tree = read_gamelist(gamelist_path)
    upsert_game(tree, GAME_ENTRY)
    write_gamelist(gamelist_path, tree)
    content = gamelist_path.read_text(encoding="utf-8")
    assert "<name>Super Mario 64</name>" in content
    assert "<pr_badge>NATIVE</pr_badge>" in content
    assert "<pr_core>" in content


def test_write_gamelist_includes_xml_declaration(tmp_path):
    gamelist_path = tmp_path / "gamelist.xml"
    gamelist_path.write_text(EMPTY_GAMELIST_XML, encoding="utf-8")
    tree = read_gamelist(gamelist_path)
    write_gamelist(gamelist_path, tree)
    content = gamelist_path.read_text(encoding="utf-8")
    assert content.startswith("<?xml")


def test_read_gamelist_creates_empty_if_missing(tmp_path):
    gamelist_path = tmp_path / "gamelist.xml"
    # file does not exist
    tree = read_gamelist(gamelist_path)
    assert tree.tag == "gameList"


def test_upsert_badge_only_update(tmp_path):
    """Badge update event: only pr_badge and pr_core change."""
    gamelist_path = tmp_path / "gamelist.xml"
    gamelist_path.write_text(EMPTY_GAMELIST_XML, encoding="utf-8")
    tree = read_gamelist(gamelist_path)
    upsert_game(tree, GAME_ENTRY)
    badge_patch = {
        "path": "./Super Mario 64/sm64.x86_64",
        "pr_badge": "BUILD ERROR",
        "pr_core": "",
    }
    upsert_game(tree, badge_patch)
    game = tree.find("game")
    assert game.find("pr_badge").text == "BUILD ERROR"
    # name preserved from original insert
    assert game.find("name").text == "Super Mario 64"

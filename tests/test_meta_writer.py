import json

from pr_meta.meta_writer import write_meta, read_meta


def test_write_meta_creates_file(tmp_path, sample_meta):
    game_dir = tmp_path / "Super Mario 64"
    game_dir.mkdir()
    write_meta(game_dir, sample_meta)
    assert (game_dir / "pr-meta.json").exists()


def test_write_meta_content(tmp_path, sample_meta):
    game_dir = tmp_path / "Super Mario 64"
    game_dir.mkdir()
    write_meta(game_dir, sample_meta)
    data = json.loads((game_dir / "pr-meta.json").read_text())
    assert data["title"] == "Super Mario 64"
    assert data["year"] == 1996
    assert data["badge"] == "NATIVE"
    assert data["core"] is None


def test_write_meta_overwrites_existing(tmp_path, sample_meta):
    game_dir = tmp_path / "Super Mario 64"
    game_dir.mkdir()
    write_meta(game_dir, sample_meta)
    updated = dict(sample_meta)
    updated["badge"] = "EMU"
    updated["core"] = "mupen64plus_next"
    write_meta(game_dir, updated)
    data = json.loads((game_dir / "pr-meta.json").read_text())
    assert data["badge"] == "EMU"
    assert data["core"] == "mupen64plus_next"


def test_read_meta_returns_dict(tmp_path, sample_meta):
    game_dir = tmp_path / "Super Mario 64"
    game_dir.mkdir()
    write_meta(game_dir, sample_meta)
    result = read_meta(game_dir)
    assert result["title"] == "Super Mario 64"


def test_read_meta_missing_returns_none(tmp_path):
    game_dir = tmp_path / "Nonexistent Game"
    game_dir.mkdir()
    assert read_meta(game_dir) is None

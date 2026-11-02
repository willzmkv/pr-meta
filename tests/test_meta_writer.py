import json

from pr_meta.badges import Badge, BADGE_COLORS
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


def test_badge_colors_all_defined():
    for badge in Badge:
        assert badge in BADGE_COLORS, f"Missing color for badge {badge}"


def test_badge_color_hex_format():
    for color in BADGE_COLORS.values():
        assert color.startswith("#")
        assert len(color) == 7


def test_badge_build_error_value():
    assert Badge.BUILD_ERROR.value == "BUILD ERROR"


def test_badge_colors_match_design_spec():
    """Spec section 4 (Sistema de Badges ES-DE) is the source of truth."""
    assert BADGE_COLORS == {
        Badge.NATIVE: "#4ecdc4",
        Badge.EMU: "#f5a623",
        Badge.BUILDING: "#4a9eff",
        Badge.BUILD_ERROR: "#e94560",
    }

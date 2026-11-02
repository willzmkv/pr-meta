import pytest


SAMPLE_INSTALL_EVENT = {
    "event": "game_installed",
    "platform": "n64",
    "title": "Super Mario 64",
    "rom_hash": "20b854b239203baf6354e9f5e5ea9bc7",
    "game_dir": "/home/arcade/games/n64/Super Mario 64",
    "badge": "NATIVE",
    "core": None,
    "binary": "./sm64.x86_64",
}

SAMPLE_BADGE_EVENT = {
    "event": "badge_update",
    "platform": "n64",
    "title": "Super Mario 64",
    "badge": "NATIVE",
    "core": None,
    "progress": None,
}

SAMPLE_META = {
    "title": "Super Mario 64",
    "platform": "n64",
    "year": 1996,
    "genre": "Platform",
    "publisher": "Nintendo",
    "developer": "Nintendo",
    "description": "Guide Mario through 15 courses.",
    "rating": 0.95,
    "players": 1,
    "badge": "NATIVE",
    "core": None,
    "binary": "./sm64.x86_64",
    "image": "./media/cover.png",
    "video": "./media/video.mp4",
}


@pytest.fixture
def sample_install_event():
    return dict(SAMPLE_INSTALL_EVENT)


@pytest.fixture
def sample_badge_event():
    return dict(SAMPLE_BADGE_EVENT)


@pytest.fixture
def sample_meta():
    return dict(SAMPLE_META)

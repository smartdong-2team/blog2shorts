"""배경음악 카탈로그와 목록 API 테스트."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import music
from app.services.music import (
    available_tracks,
    find_track,
    music_gain,
)

client = TestClient(app)


@pytest.fixture
def music_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(music, "MUSIC_DIR", tmp_path)
    return tmp_path


def test_available_tracks_lists_only_existing_files(music_dir):
    (music_dir / "soft_piano.mp3").write_bytes(b"fake")

    assert available_tracks() == [
        {"id": "soft_piano", "label": "잔잔한 피아노"},
    ]


def test_find_track_rejects_unknown_id_and_path_tricks(music_dir):
    (music_dir / "soft_piano.mp3").write_bytes(b"fake")

    assert find_track("soft_piano") == music_dir / "soft_piano.mp3"
    assert find_track("dreamy_synth") is None
    assert find_track("../soft_piano") is None


@pytest.mark.parametrize(
    "percent,gain",
    [(0, 0.0), (30, 0.12), (100, 0.4)],
)
def test_music_gain(percent, gain):
    assert music_gain(percent) == pytest.approx(gain)


def test_music_list_api(music_dir):
    (music_dir / "light_acoustic.wav").write_bytes(b"fake")

    response = client.get("/api/v1/audio/music")

    assert response.status_code == 200
    assert response.json() == {
        "tracks": [
            {"id": "light_acoustic", "label": "경쾌한 어쿠스틱"},
        ]
    }

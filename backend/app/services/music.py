"""배경음악 카탈로그.

음원은 라이선스를 확인한 파일만 assets/music/ 에 `<id>.<확장자>` 로 넣는다.
파일이 있는 곡만 화면에 표시되므로, 없는 음악을 고를 수는 없다.
"""

from pathlib import Path

MUSIC_DIR = Path(__file__).resolve().parents[2] / "assets" / "music"

NO_MUSIC = "none"

MUSIC_LABELS = {
    "salsa_new_york": "살사 (Salsa Estilo New York 03)",
    "soft_piano": "잔잔한 피아노",
    "light_acoustic": "경쾌한 어쿠스틱",
    "dreamy_synth": "몽환적인 신스",
}

MUSIC_EXTENSIONS = (".mp3", ".m4a", ".wav")

# 화면의 음악 크기 100%일 때의 실제 음량. 내레이션을 가리지 않도록 제한한다
MAX_MUSIC_GAIN = 0.4


def find_track(track_id: str) -> Path | None:
    """곡 ID에 해당하는 음원 파일을 찾는다."""

    if track_id not in MUSIC_LABELS:
        return None

    for extension in MUSIC_EXTENSIONS:
        path = MUSIC_DIR / f"{track_id}{extension}"

        if path.is_file():
            return path

    return None


def available_tracks() -> list[dict[str, str]]:
    """실제 음원 파일이 있는 곡 목록."""

    return [
        {"id": track_id, "label": label}
        for track_id, label in MUSIC_LABELS.items()
        if find_track(track_id) is not None
    ]


def music_gain(volume_percent: int) -> float:
    """화면의 음악 크기(0~100)를 FFmpeg 음량으로 변환한다."""

    return round(volume_percent / 100 * MAX_MUSIC_GAIN, 3)

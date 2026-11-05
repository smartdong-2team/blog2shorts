
import math

from app.schemas.audio import SubtitleCue


# --------------------------------------------------
# 1. 장면 시작 시간과 음성 길이로 자막 구간 생성
# --------------------------------------------------
def create_subtitle(
    caption: str,
    start_sec: float,
    duration_sec: float,
) -> SubtitleCue:
    """장면 시작 시간과 음성 길이로 자막 구간을 생성한다."""

    if not caption.strip():
        raise ValueError("자막 텍스트가 비어 있습니다.")

    if not math.isfinite(start_sec) or start_sec < 0:
        raise ValueError("시작 시간은 0 이상의 유한한 값이어야 합니다.")

    if not math.isfinite(duration_sec) or duration_sec <= 0:
        raise ValueError("음성 길이는 0보다 큰 유한한 값이어야 합니다.")

    return SubtitleCue(
        text=caption.strip(),
        start_sec=start_sec,
        end_sec=start_sec + duration_sec,
    )


# --------------------------------------------------
# 2. 여러 장면의 자막을 전체 영상 시간에 맞춰 배치
# --------------------------------------------------
def create_subtitle_timeline(
    captions: list[str],
    durations: list[float],
) -> list[SubtitleCue]:
    """여러 장면의 자막을 전체 영상 시간에 맞춰 배치한다."""

    if not captions:
        raise ValueError("자막 목록이 비어 있습니다.")

    if len(captions) != len(durations):
        raise ValueError("자막과 음성 길이의 개수가 일치해야 합니다.")

    subtitles: list[SubtitleCue] = []
    current_time = 0.0

    for caption, duration in zip(captions, durations):
        subtitle = create_subtitle(
            caption=caption,
            start_sec=current_time,
            duration_sec=duration,
        )

        subtitles.append(subtitle)
        current_time = subtitle.end_sec

    return subtitles

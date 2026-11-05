
import pytest
from pydantic import ValidationError

from app.schemas.audio import SubtitleCue
from app.services.subtitles import (
    create_subtitle,
    create_subtitle_timeline,
)


# 1. 단일 자막 생성
def test_create_subtitle_success():
    subtitle = create_subtitle(
        caption="안녕하세요.",
        start_sec=2.0,
        duration_sec=3.5,
    )

    assert isinstance(subtitle, SubtitleCue)
    assert subtitle.text == "안녕하세요."
    assert subtitle.start_sec == pytest.approx(2.0)
    assert subtitle.end_sec == pytest.approx(5.5)


# 2. 자막 앞뒤 공백 제거
def test_create_subtitle_strips_whitespace():
    subtitle = create_subtitle(
        caption="  안녕하세요.  ",
        start_sec=0.0,
        duration_sec=2.0,
    )

    assert subtitle.text == "안녕하세요."


# 3. 빈 자막 거부
@pytest.mark.parametrize(
    "caption",
    ["", "   ", "\n\t"],
)
def test_create_subtitle_rejects_empty_caption(caption):
    with pytest.raises(ValueError, match="자막 텍스트가 비어 있습니다"):
        create_subtitle(
            caption=caption,
            start_sec=0.0,
            duration_sec=2.0,
        )


# 4. 잘못된 시작 시간 거부
@pytest.mark.parametrize(
    "start_sec",
    [-1.0, float("nan"), float("inf"), float("-inf")],
)
def test_create_subtitle_rejects_invalid_start(start_sec):
    with pytest.raises(ValueError, match="시작 시간"):
        create_subtitle(
            caption="테스트 자막",
            start_sec=start_sec,
            duration_sec=2.0,
        )


# 5. 잘못된 음성 길이 거부
@pytest.mark.parametrize(
    "duration_sec",
    [0.0, -1.0, float("nan"), float("inf"), float("-inf")],
)
def test_create_subtitle_rejects_invalid_duration(duration_sec):
    with pytest.raises(ValueError, match="음성 길이"):
        create_subtitle(
            caption="테스트 자막",
            start_sec=0.0,
            duration_sec=duration_sec,
        )


# 6. 여러 장면의 타임라인 생성
def test_create_subtitle_timeline_success():
    subtitles = create_subtitle_timeline(
        captions=[
            "첫 번째 장면",
            "두 번째 장면",
            "세 번째 장면",
        ],
        durations=[4.8, 6.2, 5.0],
    )

    assert len(subtitles) == 3

    assert subtitles[0].start_sec == pytest.approx(0.0)
    assert subtitles[0].end_sec == pytest.approx(4.8)

    assert subtitles[1].start_sec == pytest.approx(4.8)
    assert subtitles[1].end_sec == pytest.approx(11.0)

    assert subtitles[2].start_sec == pytest.approx(11.0)
    assert subtitles[2].end_sec == pytest.approx(16.0)


# 7. 단일 장면 타임라인
def test_create_subtitle_timeline_single_scene():
    subtitles = create_subtitle_timeline(
        captions=["하나의 장면"],
        durations=[3.0],
    )

    assert len(subtitles) == 1
    assert subtitles[0].start_sec == pytest.approx(0.0)
    assert subtitles[0].end_sec == pytest.approx(3.0)


# 8. 빈 타임라인 거부
def test_create_subtitle_timeline_rejects_empty():
    with pytest.raises(ValueError, match="자막 목록이 비어 있습니다"):
        create_subtitle_timeline(
            captions=[],
            durations=[],
        )


# 9. 자막과 음성 길이 개수 불일치
@pytest.mark.parametrize(
    "captions,durations",
    [
        (["첫 번째", "두 번째"], [3.0]),
        (["첫 번째"], [3.0, 4.0]),
    ],
)
def test_create_subtitle_timeline_rejects_length_mismatch(
    captions,
    durations,
):
    with pytest.raises(ValueError, match="개수가 일치해야 합니다"):
        create_subtitle_timeline(
            captions=captions,
            durations=durations,
        )


# 10. 타임라인 내 잘못된 장면 데이터 거부
def test_create_subtitle_timeline_rejects_invalid_scene():
    with pytest.raises(ValueError, match="자막 텍스트가 비어 있습니다"):
        create_subtitle_timeline(
            captions=["정상 자막", "   "],
            durations=[3.0, 4.0],
        )


# 11. 앞 장면 종료와 다음 장면 시작이 일치하는지 확인
def test_create_subtitle_timeline_is_continuous():
    subtitles = create_subtitle_timeline(
        captions=["장면 1", "장면 2", "장면 3"],
        durations=[1.25, 2.75, 3.5],
    )

    for previous, current in zip(subtitles, subtitles[1:]):
        assert current.start_sec == pytest.approx(previous.end_sec)

    assert subtitles[-1].end_sec == pytest.approx(7.5)

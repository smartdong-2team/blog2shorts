
import pytest
from pydantic import ValidationError

from app.schemas.audio import SubtitleCue
from app.services.subtitles import (
    SUBTITLE_MAX_WIDTH,
    create_narration_cues,
    split_into_pages,
    text_width,
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


# --------------------------------------------------
# 내레이션을 화면 폭에 맞는 자막 페이지로 분할
# --------------------------------------------------
LONG_NARRATION = (
    "엔진, 섀시, 전기 세 과목을 먼저 나눠서 보고 기출문제를 세 번 "
    "반복하면 합격선에 빠르게 가까워져요. 오답 노트도 꼭 만들어 보세요."
)


def test_split_into_pages_fits_screen_width_and_two_lines():
    pages = split_into_pages(LONG_NARRATION)

    assert len(pages) > 1

    for lines in pages:
        assert len(lines) <= 2
        assert all(
            text_width(line) <= SUBTITLE_MAX_WIDTH
            for line in lines
        )


def test_split_into_pages_keeps_every_word_in_order():
    pages = split_into_pages(LONG_NARRATION)

    assert " ".join(" ".join(lines) for lines in pages) == LONG_NARRATION


def test_split_into_pages_breaks_at_sentence_boundary():
    pages = split_into_pages("짧은 첫 문장이에요. 짧은 둘째 문장이에요.")

    assert pages == [["짧은 첫 문장이에요."], ["짧은 둘째 문장이에요."]]


def test_split_into_pages_follows_meaning_units():
    """목적어까지 묶고, 술어는 이어지는 말과 함께 다음 페이지로 넘긴다."""

    pages = split_into_pages(
        "먼저 자동차 기본 구조와 각 장치의 작동 원리를 이해하는 게 기본이에요."
    )

    assert pages == [
        ["먼저 자동차 기본 구조와", "각 장치의 작동 원리를"],
        ["이해하는 게 기본이에요."],
    ]


@pytest.mark.parametrize(
    "before,after",
    [
        ("이해하는", "게"),
        ("각", "장치의"),
        ("어떤", "방법으로"),
        ("장치의", "작동"),
    ],
)
def test_split_into_pages_keeps_dependent_words_together(before, after):
    narration = (
        f"오늘은 공부할 때 꼭 필요한 내용을 정리해 볼게요 {before} {after} "
        "부분을 먼저 살펴보고 천천히 따라오세요."
    )

    joined_lines = [
        line
        for lines in split_into_pages(narration)
        for line in lines
    ]

    assert any(f"{before} {after}" in line for line in joined_lines)


def test_split_into_pages_avoids_single_word_page():
    pages = split_into_pages(LONG_NARRATION.split(".")[0] + " 끝")

    assert all(len(" ".join(lines).split()) > 1 for lines in pages)


def test_split_into_pages_hard_breaks_very_long_word():
    pages = split_into_pages("가" * 60)

    assert "".join("".join(lines) for lines in pages) == "가" * 60

    for lines in pages:
        assert all(
            text_width(line) <= SUBTITLE_MAX_WIDTH
            for line in lines
        )


def test_create_narration_cues_cover_duration_without_gaps():
    cues = create_narration_cues(LONG_NARRATION, 12.0)

    assert cues[0].start_sec == pytest.approx(0.0)
    assert cues[-1].end_sec == pytest.approx(12.0)

    for previous, current in zip(cues, cues[1:]):
        assert previous.end_sec == pytest.approx(current.start_sec)


def test_create_narration_cues_gives_longer_page_more_time():
    cues = create_narration_cues(
        "네. 이 문장은 앞 문장보다 훨씬 길어요.",
        6.0,
    )
    durations = [cue.end_sec - cue.start_sec for cue in cues]

    assert durations[0] < durations[1]


def test_create_narration_cues_rejects_empty_text():
    with pytest.raises(ValueError):
        create_narration_cues("   ", 3.0)


import pytest
from pydantic import ValidationError

from app.schemas.audio import SubtitleCue
from app.services.subtitle_styles import SUBTITLE_STYLES
from app.services.subtitles import (
    HOOK_MAX_FONT_SIZE,
    HOOK_MAX_WIDTH,
    SUBTITLE_MAX_WIDTH,
    layout_hook,
    clean_subtitle_pages,
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


# --------------------------------------------------
# AI가 나눈 자막 페이지 검증
# --------------------------------------------------
NARRATION = "먼저 자동차 기본 구조와 각 장치의 작동 원리를 이해하는 게 기본이에요."
AI_PAGES = [
    ["먼저 자동차 기본 구조와", "각 장치의 작동 원리를"],
    ["이해하는 게 기본이에요."],
]


def test_clean_subtitle_pages_accepts_exact_split():
    assert clean_subtitle_pages(AI_PAGES, NARRATION) == AI_PAGES


def test_clean_subtitle_pages_ignores_punctuation_and_spaces():
    pages = [
        ["먼저 자동차 기본구조와", "각 장치의 작동 원리를"],
        ["이해하는 게 기본이에요"],
    ]

    assert clean_subtitle_pages(pages, NARRATION) == pages


@pytest.mark.parametrize(
    "pages",
    [
        None,
        [],
        # 글자가 빠지거나 바뀜
        [["먼저 자동차 기본 구조와"], ["이해하는 게 기본이에요."]],
        [["먼저 자동차 구조와 각 장치의", "작동 원리를 아는 게"], ["기본이에요."]],
        # 3줄
        [["먼저 자동차", "기본 구조와", "각 장치의 작동 원리를"], ["이해하는 게 기본이에요."]],
        # 빈 줄·빈 페이지
        [["먼저 자동차 기본 구조와", ""], ["각 장치의 작동 원리를 이해하는 게 기본이에요."]],
        [[], *AI_PAGES],
        # 화면 폭 초과
        [[NARRATION]],
    ],
)
def test_clean_subtitle_pages_rejects_invalid_pages(pages):
    assert clean_subtitle_pages(pages, NARRATION) is None


def test_create_narration_cues_uses_valid_ai_pages():
    cues = create_narration_cues(NARRATION, 6.0, AI_PAGES)

    assert [cue.text for cue in cues] == [
        "먼저 자동차 기본 구조와\n각 장치의 작동 원리를",
        "이해하는 게 기본이에요.",
    ]
    assert cues[-1].end_sec == pytest.approx(6.0)


def test_create_narration_cues_falls_back_after_narration_edit():
    """사용자가 문구를 고치면 예전 AI 자막 대신 규칙으로 다시 나눈다."""

    edited = "구조부터 차근차근 살펴보면 금방 익숙해져요."

    cues = create_narration_cues(edited, 4.0, AI_PAGES)

    joined = " ".join(cue.text.replace("\n", " ") for cue in cues)
    assert joined == edited



@pytest.mark.parametrize(
    "pages,narration",
    [
        # 앞말과 붙어야 할 말이 줄에서 끊김
        (
            [["먼저 구조와 원리를 잘 이해하는", "게 중요해요."]],
            "먼저 구조와 원리를 잘 이해하는 게 중요해요.",
        ),
        # 페이지 경계에서 끊김
        (
            [["먼저 구조와 원리를 잘 이해하는"], ["게 중요해요."]],
            "먼저 구조와 원리를 잘 이해하는 게 중요해요.",
        ),
        # 한 자막에 두 문장이 섞임
        (
            [["먼저 구조를 이해해요.", "그림도 참고해 보세요."]],
            "먼저 구조를 이해해요. 그림도 참고해 보세요.",
        ),
        # 짧은 술어만 혼자 남음
        (
            [["공부 방법이 고민될 때가", "많아요."]],
            "공부 방법이 고민될 때가 많아요.",
        ),
    ],
)
def test_clean_subtitle_pages_rejects_awkward_breaks(pages, narration):
    assert clean_subtitle_pages(pages, narration) is None


def test_clean_subtitle_pages_rejects_single_word_page():
    """문장이 이어지는데 한 단어만 다음 페이지로 넘어가면 쓰지 않는다."""

    narration = "강의는 기초부터 핵심 이론과 문제 풀이까지 체계적으로 알려줘요."

    assert clean_subtitle_pages(
        [
            ["강의는 기초부터 핵심 이론과", "문제 풀이까지 체계적으로"],
            ["알려줘요."],
        ],
        narration,
    ) is None


def test_clean_subtitle_pages_allows_short_full_sentence_page():
    """한 단어라도 그 자체로 문장이면 따로 둘 수 있다."""

    pages = [["탄탄히 준비해서 꼭 합격하세요!"], ["응원할게요."]]

    assert clean_subtitle_pages(
        pages,
        "탄탄히 준비해서 꼭 합격하세요! 응원할게요.",
    ) == pages


def test_create_narration_cues_respects_user_edited_pages():
    """사용자가 나눈 자막은 품질 검사 없이 그대로 쓴다."""

    narration = "먼저 구조를 이해하는 게 좋아요."
    pages = [["먼저 구조를 이해하는"], ["게 좋아요."]]

    cues = create_narration_cues(narration, 4.0, pages)

    assert [cue.text for cue in cues] == [
        "먼저 구조를 이해하는",
        "게 좋아요.",
    ]


# --------------------------------------------------
# 상단 제목 배치
# --------------------------------------------------
@pytest.mark.parametrize(
    "text",
    [
        "2026년 전산세무 2급 시험,\n놓치면 안 될 일정 알려줘요!",
        "2026년 전산세무 2급 시험, 놓치면 안 될 일정 알려줘요!",
        "첫째 줄\n둘째 줄\n셋째 줄",
        "짧은 제목",
    ],
)
def test_layout_hook_fits_two_lines(text):
    lines, fontsize = layout_hook(text)

    assert 1 <= len(lines) <= 2
    assert all(
        text_width(line) / SUBTITLE_STYLES["default"]["font_size"] * fontsize
        <= HOOK_MAX_WIDTH
        for line in lines
    )


def test_layout_hook_keeps_manual_line_break():
    lines, _ = layout_hook("앞줄이 아주 짧고\n뒷줄")

    assert lines == ["앞줄이 아주 짧고", "뒷줄"]


def test_layout_hook_merges_extra_lines_without_losing_words():
    lines, _ = layout_hook("첫째 줄\n둘째 줄\n셋째 줄")

    assert lines == ["첫째 줄", "둘째 줄 셋째 줄"]


def test_layout_hook_shrinks_long_line():
    long_line = "아주 긴 제목이 한 단어처럼붙어서길게이어지는경우에도들어가야해요"

    lines, fontsize = layout_hook(f"짧은 줄\n{long_line}")

    assert lines[1] == long_line
    assert fontsize < HOOK_MAX_FONT_SIZE


def test_layout_hook_empty():
    assert layout_hook("  \n ")[0] == []


# --------------------------------------------------
# 나열과 줄 길이 균형
# --------------------------------------------------
def test_split_into_pages_keeps_list_together():
    """나열은 중간에서 끊지 않고, 나열이 끝난 뒤에서 줄을 나눈다."""

    pages = split_into_pages(
        "인디자인은 책, 잡지, 브로슈어 등 다양한 편집디자인에 쓰이는 "
        "아주 중요한 프로그램이에요."
    )

    assert pages[0] == [
        "인디자인은 책, 잡지, 브로슈어 등",
        "다양한 편집디자인에 쓰이는",
    ]


def test_split_into_pages_prefers_comma_between_clauses():
    """나열이 아닌 쉼표는 여전히 좋은 줄바꿈 위치다."""

    pages = split_into_pages(
        "자동차정비기능사 필기시험, 혼자 준비할 수 있을지 고민되시죠?"
    )

    assert pages == [
        ["자동차정비기능사 필기시험,", "혼자 준비할 수 있을지 고민되시죠?"],
    ]


def test_clean_subtitle_pages_rejects_break_inside_list():
    narration = "책, 잡지, 브로슈어 등 다양한 편집디자인에 쓰여요."

    assert clean_subtitle_pages(
        [["책, 잡지,", "브로슈어 등 다양한 편집디자인에 쓰여요."]],
        narration,
    ) is None


def test_clean_subtitle_pages_rejects_unbalanced_lines():
    narration = "먼저 자동차 기본 구조부터 차근차근 이해하세요 천천히요."

    assert clean_subtitle_pages(
        [["먼저 자동차 기본 구조부터 차근차근 이해하세요", "천천히요."]],
        narration,
    ) is None


def test_split_into_pages_keeps_subject_with_predicate():
    """'6회가 있으며'처럼 주어와 서술어는 떼지 않고 쉼표 뒤에서 나눈다."""

    pages = split_into_pages(
        "2026년 전산세무 2급 시험은 총 6회가 있으며, "
        "마지막 시험은 12월 5일에 치러져요."
    )

    assert pages == [
        ["2026년 전산세무 2급 시험은", "총 6회가 있으며,"],
        ["마지막 시험은 12월 5일에 치러져요."],
    ]


@pytest.mark.parametrize(
    "pages",
    [
        [["2026년 전산세무 2급 시험은 총 6회가"], ["있으며, 마지막 시험은", "12월 5일에 치러져요."]],
        [["2026년 전산세무 2급 시험은 총 6회가", "있으며, 마지막 시험은"], ["12월 5일에 치러져요."]],
    ],
)
def test_clean_subtitle_pages_rejects_split_predicate(pages):
    assert clean_subtitle_pages(
        pages,
        "2026년 전산세무 2급 시험은 총 6회가 있으며, 마지막 시험은 12월 5일에 치러져요.",
    ) is None


# --------------------------------------------------
# 줄 글자 수 권장 규칙
# --------------------------------------------------
@pytest.mark.parametrize(
    "narration,expected",
    [
        # 둘째 줄이 짧으면 앞줄의 의미 단위를 아래로 내린다
        (
            "이해 어려우면 온라인 강의를 활용해보세요.",
            [["이해 어려우면", "온라인 강의를 활용해보세요."]],
        ),
        # 첫 줄 권장 때문에 멀쩡한 자막을 둘로 쪼개지 않는다
        (
            "시험은 어렵지 않으며, 합격선은 60점이에요.",
            [["시험은 어렵지 않으며,", "합격선은 60점이에요."]],
        ),
        # 보조 용언과 의존 표현은 앞말과 같은 줄에 둔다
        (
            "기초부터 실전까지 체계적으로 가르쳐 주니 초보자도 쉽게 따라갈 수 있어요.",
            [
                ["기초부터 실전까지 체계적으로"],
                ["가르쳐 주니 초보자도", "쉽게 따라갈 수 있어요."],
            ],
        ),
    ],
)
def test_split_into_pages_line_length_recommendation(narration, expected):
    assert split_into_pages(narration) == expected


@pytest.mark.parametrize(
    "narration",
    [
        "기출문제로 시험 유형 익히고, 틀린 문제는 이론 복습하세요. 이해 어려우면 온라인 강의를 활용해보세요.",
        "기초부터 실전까지 체계적으로 가르쳐 주니 초보자도 쉽게 따라갈 수 있어요.",
        "온라인 강의와 교재를 함께 활용하면 정말 좋아요.",
    ],
)
def test_split_into_pages_avoids_short_second_line(narration):
    for lines in split_into_pages(narration):
        if len(lines) == 2:
            assert len(lines[1].replace(" ", "").rstrip(".!?")) > 6


def test_clean_subtitle_pages_rejects_short_second_line():
    assert clean_subtitle_pages(
        [["이해 어려우면 온라인 강의를", "활용해보세요."]],
        "이해 어려우면 온라인 강의를 활용해보세요.",
    ) is None



# --------------------------------------------------
# 제목 강조 (*로 감싼 부분)
# --------------------------------------------------
from app.services.subtitles import emphasis_segments, layout_hook, normalize_emphasis, strip_emphasis  # noqa: E402


def test_emphasis_segments_split_marked_words():
    assert emphasis_segments(["행정사 1차", "*3과목* 공부 순서"]) == [
        [("행정사 1차", False)],
        [("3과목", True), (" 공부 순서", False)],
    ]


def test_emphasis_keeps_spaces_outside_box_and_continues_across_lines():
    assert emphasis_segments(["시험 * 3과목", "순서* 끝"]) == [
        [("시험 ", False), (" ", False), ("3과목", True)],
        [("순서", True), (" 끝", False)],
    ]


def test_unpaired_mark_is_dropped():
    assert normalize_emphasis("*3과목 공부") == "3과목 공부"
    assert normalize_emphasis("*3과목* 공부*") == "*3과목* 공부"


def test_layout_hook_measures_without_marks():
    marked, size = layout_hook("행정사 1차\n*3과목* 공부 순서")
    plain, plain_size = layout_hook("행정사 1차\n3과목 공부 순서")

    assert [strip_emphasis(line) for line in marked] == plain
    assert size == plain_size

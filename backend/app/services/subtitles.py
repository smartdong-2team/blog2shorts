
import math
import re
from functools import lru_cache

from PIL import ImageFont

from app.schemas.audio import SubtitleCue
from app.services.subtitle_styles import SUBTITLE_STYLES

# 자막 한 줄의 최대 폭(px). 1080 화면에서 배경 여백을 뺀 값
SUBTITLE_MAX_WIDTH = 960
SUBTITLE_MAX_LINES = 2
LINE_BREAK_WEIGHT = 110

SENTENCE_END = re.compile(r"[.!?。！？…][\"'”’)]*$")

# 뒤 단어가 앞말에 의존해서 떼어 놓으면 어색한 경우
DEPENDENT_AFTER = re.compile(
    r"^(수|뒤|때|것|것이|것을|게|걸|건|거|줄|있어요|있죠|없어요|보세요|해요|돼요|드려요)[.!?,]?$"
)
# 뒤 명사를 꾸며서 이어져야 하는 말
MODIFIER_BEFORE = re.compile(
    r"(하는|되는|있는|없는|위한|대한|통한|같은|익힌|확인한|작성한|배운)$"
)
DETERMINER = re.compile(
    r"^(각|이|그|저|몇|여러|새|어떤|주요|핵심|최신|다양한|필요한|중요한|이런|그런|모든)$"
)
LINKED_ENDINGS = re.compile(r"[,，:：]$|(하면|하지만|다면|으며|면서|하고|고|니|서)$")


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


# --------------------------------------------------
# 3. 내레이션을 의미 단위 자막 페이지로 분할
#    문법 분석기가 아니라 조사·어미를 보는 가벼운 규칙이다.
# --------------------------------------------------
@lru_cache
def _subtitle_font() -> ImageFont.FreeTypeFont:
    style = SUBTITLE_STYLES["default"]

    return ImageFont.truetype(
        str(style["font_file"]),
        style["font_size"],
    )


def text_width(text: str) -> float:
    """영상에 그려질 글꼴 기준의 실제 폭(px)."""

    return _subtitle_font().getlength(text)


def _split_long_word(word: str) -> list[str]:
    """한 줄에 들어가지 않는 단어는 글자 단위로 나눈다."""

    pieces = []
    current = ""

    for char in word:
        if current and text_width(current + char) > SUBTITLE_MAX_WIDTH:
            pieces.append(current)
            current = char
        else:
            current += char

    pieces.append(current)
    return pieces


def _page_break_cost(before: str, after: str) -> int:
    """두 단어 사이에서 자막 페이지를 넘길 때의 비용. 낮을수록 좋다."""

    if SENTENCE_END.search(before):
        return 0

    if DEPENDENT_AFTER.match(after):
        return 65

    if MODIFIER_BEFORE.search(before):
        return 55

    if DETERMINER.match(before) or before.endswith("의"):
        return 45

    if re.search(r"(은|는|이|가|을|를)$", before):
        return -14

    if LINKED_ENDINGS.search(before):
        return -6

    return 12


def _line_break_cost(before: str, after: str) -> int:
    """페이지 안에서 줄을 나눌 때의 등급. 낮을수록 좋다."""

    if (
        DEPENDENT_AFTER.match(after)
        or MODIFIER_BEFORE.search(before)
        or DETERMINER.match(before)
        or before.endswith("의")
    ):
        return 3

    if LINKED_ENDINGS.search(before) or re.search(
        r"(은|는|이|가|을|를|와|과|도|에|로)$",
        before,
    ):
        return 0

    return 1


def _layout_page(words: list[str]) -> list[str] | None:
    """단어들을 1~2줄로 배치한다. 들어가지 않으면 None."""

    single_line = " ".join(words)

    if text_width(single_line) <= SUBTITLE_MAX_WIDTH:
        return [single_line]

    best = None
    best_score = None

    for index in range(1, len(words)):
        first = " ".join(words[:index])
        second = " ".join(words[index:])
        first_width = text_width(first)
        second_width = text_width(second)

        if max(first_width, second_width) > SUBTITLE_MAX_WIDTH:
            continue

        # 의미가 우선이고, 같은 등급이면 두 줄의 길이가 비슷한 쪽을 고른다
        score = (
            _line_break_cost(words[index - 1], words[index]),
            abs(first_width - second_width),
        )

        if best_score is None or score < best_score:
            best = [first, second]
            best_score = score

    return best


def _split_sentence(words: list[str]) -> list[list[str]]:
    """문장 전체 비용이 가장 낮아지도록 페이지 경계를 고른다."""

    memo: dict[int, tuple[float, list[list[str]]]] = {}

    def solve(start: int) -> tuple[float, list[list[str]]]:
        if start == len(words):
            return 0.0, []

        if start in memo:
            return memo[start]

        best = None

        for end in range(start + 1, len(words) + 1):
            part = words[start:end]
            lines = _layout_page(part)

            if lines is None:
                # 단어를 더해도 다시 들어갈 수는 없다
                break

            rest_cost, rest_pages = solve(end)

            fill = text_width(" ".join(part)) / (
                SUBTITLE_MAX_WIDTH * SUBTITLE_MAX_LINES
            )
            # 한두 단어만 남는 페이지는 어색하다
            orphan = 65 if len(part) == 1 else 22 if len(part) == 2 else 0
            boundary = (
                _page_break_cost(words[end - 1], words[end])
                if end < len(words)
                else 0
            )
            # 어중간한 줄바꿈보다는 페이지를 하나 더 쓰는 편이 읽기 좋다
            line_break = (
                _line_break_cost(lines[0].split()[-1], lines[1].split()[0])
                * LINE_BREAK_WEIGHT
                if len(lines) == 2
                else 0
            )
            cost = (
                100
                + max(0.0, 1 - fill) ** 2 * 20
                + orphan
                + boundary
                + line_break
                + rest_cost
            )

            if best is None or cost < best[0]:
                best = (cost, [lines, *rest_pages])

        memo[start] = best
        return best

    return solve(0)[1]


def split_into_pages(text: str) -> list[list[str]]:
    """내레이션을 의미 단위로 나눈 페이지 목록을 만든다. 페이지는 1~2줄이다."""

    sentence: list[str] = []
    pages: list[list[str]] = []

    words = [
        piece
        for word in text.split()
        for piece in _split_long_word(word)
    ]

    for word in words:
        sentence.append(word)

        if SENTENCE_END.search(word):
            pages.extend(_split_sentence(sentence))
            sentence = []

    if sentence:
        pages.extend(_split_sentence(sentence))

    return pages


def create_narration_cues(
    narration: str,
    duration_sec: float,
) -> list[SubtitleCue]:
    """장면 내레이션을 페이지로 나누고 글자 수 비율로 시간을 배분한다.

    단어별 음성 정렬이 아니라 글자 수 기반 추정값이다.
    반환되는 시간은 장면 시작을 0으로 하는 장면 기준 시간이다.
    """

    pages = split_into_pages(narration)

    if not pages:
        raise ValueError("자막 텍스트가 비어 있습니다.")

    if not math.isfinite(duration_sec) or duration_sec <= 0:
        raise ValueError("음성 길이는 0보다 큰 유한한 값이어야 합니다.")

    weights = [
        sum(len(re.sub(r"\s", "", line)) for line in page)
        for page in pages
    ]
    total_weight = sum(weights)

    cues: list[SubtitleCue] = []
    elapsed_weight = 0

    for page, weight in zip(pages, weights):
        start = duration_sec * elapsed_weight / total_weight
        elapsed_weight += weight
        end = duration_sec * elapsed_weight / total_weight

        cues.append(
            SubtitleCue(
                text="\n".join(page),
                start_sec=start,
                end_sec=end,
            )
        )

    return cues

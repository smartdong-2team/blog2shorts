
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
# 의미 등급 하나와 맞바꿀 수 있는 두 줄의 폭 차이(px)
LINE_GRADE_PX = 200
# 이 정도까지의 폭 차이는 뜻을 살리기 위해 허용한다(px)
LINE_BALANCE_ALLOWANCE_PX = 400
# AI가 나눈 두 줄의 폭 차이가 이보다 크면 다시 나눈다(px)
MAX_LINE_WIDTH_GAP_PX = 560
# 두 줄 자막의 권장 글자 수 (공백·문장 부호 제외)
MIN_FIRST_LINE_CHARS = 10
SHORT_SECOND_LINE_CHARS = 6
# 권장 글자 수를 벗어날 때의 비용. 뜻이 더 나쁘게 끊기면 권장을 어길 수 있다
# 둘째 줄이 짧은 것이 더 어색하므로, 그때는 첫 줄이 좀 짧아져도 앞말을 내린다
SHORT_FIRST_LINE_PX = 150
SHORT_SECOND_LINE_PX = 500
SHORT_SECOND_LINE_PAGE_COST = 120

# 상단 제목 (항상 두 줄 이내)
HOOK_MAX_WIDTH = 1000
HOOK_MAX_FONT_SIZE = 80
HOOK_MIN_FONT_SIZE = 44

SENTENCE_END = re.compile(r"[.!?。！？…][\"'”’)]*$")

# 뒤 단어가 앞말에 의존해서 떼어 놓으면 어색한 경우
DEPENDENT_AFTER = re.compile(
    r"^(수|뒤|때|것|것이|것을|게|걸|건|거|줄|보세요|해요|돼요|드려요"
    # '가르쳐 주니', '준비해야 할지'처럼 앞말에 이어지는 말
    r"|주니|주면|주고|줘요|주세요|드릴게요|할지|할까요"
    # '6회가 있으며'처럼 주어와 떨어지면 안 되는 서술어
    r"|(있|없)(어요|죠|으며|고|는데|으면|지만|어서|으니|습니다))[.!?,]?$"
)
# 뒤 명사를 꾸며서 이어져야 하는 말
MODIFIER_BEFORE = re.compile(
    r"(하는|되는|있는|없는|위한|대한|통한|같은|익힌|확인한|작성한|배운)$"
)
DETERMINER = re.compile(
    r"^(각|이|그|저|몇|여러|새|어떤|및|주요|핵심|최신|다양한|필요한|중요한|이런|그런|모든)$"
)
LINKED_ENDINGS = re.compile(r"[,，:：]$|(면|하지만|으며|면서|하고|고|니|서)$")
# 나열이 끝나는 말. 이 뒤는 끊기 좋다
LIST_END = {"등", "등을", "등이", "등의", "등도", "등은"}
COMMA_END = re.compile(r"[,，]$")


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


def _is_list_comma(words: list[str], index: int) -> bool:
    """"책, 잡지, 브로슈어 등"처럼 나열 안에 있는 쉼표인지 확인한다."""

    if not COMMA_END.search(words[index]):
        return False

    previous_has_comma = index > 0 and COMMA_END.search(words[index - 1])
    next_has_comma = index + 1 < len(words) and COMMA_END.search(words[index + 1])
    # 'A, B C 등'처럼 쉼표 뒤 몇 단어 안에 나열이 끝나는 경우
    list_ends_soon = any(word in LIST_END for word in words[index + 2:index + 4])

    return bool(previous_has_comma or next_has_comma or list_ends_soon)


def _page_break_cost(words: list[str], index: int) -> int:
    """words[index] 뒤에서 자막 페이지를 넘길 때의 비용. 낮을수록 좋다."""

    before = words[index]
    after = words[index + 1]

    if SENTENCE_END.search(before):
        return 0

    if DEPENDENT_AFTER.match(after):
        return 65

    if MODIFIER_BEFORE.search(before):
        return 55

    if (
        DETERMINER.match(before)
        or before.endswith("의")
        or _is_list_comma(words, index)
    ):
        return 45

    if LINKED_ENDINGS.search(before):
        return -20

    if re.search(r"(은|는|이|가|을|를)$", before):
        return -14

    if before in LIST_END:
        return -6

    return 12


def _line_break_cost(words: list[str], index: int) -> int:
    """words[index] 뒤에서 줄을 나눌 때의 등급. 낮을수록 좋다."""

    before = words[index]
    after = words[index + 1]

    if (
        DEPENDENT_AFTER.match(after)
        or MODIFIER_BEFORE.search(before)
        or DETERMINER.match(before)
        or before.endswith("의")
    ):
        return 3

    # 나열은 중간에서 끊지 않는다
    if _is_list_comma(words, index):
        return 2

    if (
        before in LIST_END
        or LINKED_ENDINGS.search(before)
        or re.search(r"(은|는|이|가|을|를|와|과|도|에|로)$", before)
    ):
        return 0

    return 1


def _short_line_penalty(first: str, second: str) -> int:
    """두 줄이 권장 글자 수보다 짧을 때의 비용(px)."""

    penalty = 0

    if len(_compare_key(first)) < MIN_FIRST_LINE_CHARS:
        penalty += SHORT_FIRST_LINE_PX

    if _is_short_second_line(second):
        penalty += SHORT_SECOND_LINE_PX

    return penalty


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

        # 의미가 우선이지만, 두 줄 길이 차이가 너무 크면 다음 후보를 고른다
        gap = abs(first_width - second_width)
        score = (
            _line_break_cost(words, index - 1) * LINE_GRADE_PX
            + _short_line_penalty(first, second)
            + max(0.0, gap - LINE_BALANCE_ALLOWANCE_PX),
            gap,
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
                _page_break_cost(words, end - 1)
                if end < len(words)
                else 0
            )
            # 어중간한 줄바꿈보다는 페이지를 하나 더 쓰는 편이 읽기 좋다
            line_break = (
                _line_break_cost(part, len(lines[0].split()) - 1)
                * LINE_BREAK_WEIGHT
                + (
                    SHORT_SECOND_LINE_PAGE_COST
                    if _is_short_second_line(lines[1])
                    else 0
                )
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


# 제목에서 강조할 부분을 감싸는 표시. 예: 둘째 줄이 '*3과목* 공부 순서'면 3과목을 강조한다
EMPHASIS_MARK = "*"


def normalize_emphasis(text: str) -> str:
    """짝이 맞지 않는 마지막 강조 표시는 지운다."""

    if text.count(EMPHASIS_MARK) % 2 == 0:
        return text

    index = text.rindex(EMPHASIS_MARK)
    return text[:index] + text[index + 1:]


def strip_emphasis(text: str) -> str:
    """강조 표시를 뺀, 화면에 실제로 보이는 글자."""

    return text.replace(EMPHASIS_MARK, "")


def ensure_hook_emphasis(text: str, max_length: int = 40) -> str:
    """AI가 제목에 강조를 넣지 않았으면 아랫줄 전체를 강조한다.

    한 줄 제목은 영상과 같은 규칙으로 두 줄로 나눈 뒤 아랫줄을 강조한다.
    한 줄로 들어가는 짧은 제목이나, 표시를 넣으면 max_length를 넘는 제목은 그대로 둔다.
    """

    text = normalize_emphasis(text)

    if EMPHASIS_MARK in text:
        return text

    lines, _ = layout_hook(text)

    if len(lines) < 2:
        return text

    emphasized = "\n".join([*lines[:-1], f"{EMPHASIS_MARK}{lines[-1]}{EMPHASIS_MARK}"])
    return emphasized if len(emphasized) <= max_length else text


def emphasis_segments(lines: list[str]) -> list[list[tuple[str, bool]]]:
    """줄마다 (글자, 강조 여부) 조각으로 나눈다. 강조가 줄을 넘어가도 이어진다.

    강조 조각 앞뒤 공백은 강조 밖으로 뺀다 (배경 상자가 공백까지 덮지 않게).
    """

    result = []
    emphasized = False

    for line in lines:
        segments: list[tuple[str, bool]] = []

        for index, part in enumerate(line.split(EMPHASIS_MARK)):
            if index > 0:
                emphasized = not emphasized
            if not part:
                continue
            if emphasized:
                core = part.strip()
                lead = part[: len(part) - len(part.lstrip())]
                trail = part[len(part.rstrip()):]
                for text, flag in ((lead, False), (core, True), (trail, False)):
                    if text:
                        segments.append((text, flag))
            else:
                segments.append((part, False))

        result.append(segments)

    return result


def layout_hook(text: str) -> tuple[list[str], int]:
    """제목을 최대 두 줄로 나누고, 폭에 맞는 글자 크기를 정한다.

    직접 넣은 줄바꿈은 지키고(세 줄 이상이면 둘째 줄로 합침), 없으면 균형 있게 나눈다.
    """

    rows = [row.strip() for row in normalize_emphasis(text).splitlines() if strip_emphasis(row).strip()]

    if not rows:
        return [], HOOK_MAX_FONT_SIZE

    if len(rows) > 1:
        lines = [rows[0], " ".join(rows[1:])]
    else:
        lines = _balance_hook_line(rows[0])

    # 자막 글꼴 크기로 잰 폭을 제목 크기로 환산한다
    base_size = SUBTITLE_STYLES["default"]["font_size"]
    widest_at_one = max(text_width(strip_emphasis(line)) for line in lines) / base_size
    fontsize = int(HOOK_MAX_WIDTH / widest_at_one)

    return lines, max(HOOK_MIN_FONT_SIZE, min(HOOK_MAX_FONT_SIZE, fontsize))


def _balance_hook_line(text: str) -> list[str]:
    """한 줄 제목을 두 줄 폭이 가장 비슷해지도록 나눈다."""

    words = text.split()
    single_width = text_width(strip_emphasis(text))
    base_size = SUBTITLE_STYLES["default"]["font_size"]

    # 가장 큰 글자로도 한 줄에 들어가면 나누지 않는다
    if len(words) == 1 or single_width / base_size * HOOK_MAX_FONT_SIZE <= HOOK_MAX_WIDTH:
        return [text]

    candidates = (
        (" ".join(words[:i]), " ".join(words[i:]))
        for i in range(1, len(words))
    )

    return list(
        min(
            candidates,
            key=lambda pair: abs(text_width(strip_emphasis(pair[0])) - text_width(strip_emphasis(pair[1]))),
        )
    )


def _compare_key(text: str) -> str:
    """문장 부호와 공백을 뺀 비교용 문자열."""

    return re.sub(r"[\s.,!?…\"'’”]", "", text)


def validate_subtitle_pages(
    pages: list[list[str]] | None,
    narration: str,
) -> list[list[str]] | None:
    """자막 페이지의 구조와 글자를 확인한다. 쓸 수 없으면 None을 돌려준다.

    - 내레이션의 글자를 빠짐없이 같은 순서로 담아야 한다 (문장 부호·공백 제외)
    - 페이지는 1~2줄이어야 한다
    """

    if not pages:
        return None

    cleaned: list[list[str]] = []

    for page in pages:
        lines = [line.strip() for line in page]

        if not 1 <= len(lines) <= SUBTITLE_MAX_LINES or not all(lines):
            return None

        cleaned.append(lines)

    joined = "".join(line for lines in cleaned for line in lines)

    if _compare_key(joined) != _compare_key(narration):
        return None

    return cleaned


def clean_subtitle_pages(
    pages: list[list[str]] | None,
    narration: str,
) -> list[list[str]] | None:
    """AI가 나눈 자막의 품질까지 검사한다. 쓸 수 없으면 None을 돌려준다.

    사용자가 직접 고친 자막에는 쓰지 않는다. 편집 결과는 그대로 존중한다.
    """

    cleaned = validate_subtitle_pages(pages, narration)

    if cleaned is None:
        return None

    if any(
        text_width(line) > SUBTITLE_MAX_WIDTH
        for lines in cleaned
        for line in lines
    ):
        return None

    if _has_awkward_break(cleaned):
        return None

    return cleaned


def _is_short_second_line(line: str) -> bool:
    """"좋아요."처럼 둘째 줄에 짧은 말만 남았는지 확인한다."""

    return len(_compare_key(line)) <= SHORT_SECOND_LINE_CHARS


def _has_awkward_break(pages: list[list[str]]) -> bool:
    """글자는 맞아도 읽기 어색하게 나눈 자막인지 확인한다."""

    all_words = [
        word
        for lines in pages
        for line in lines
        for word in line.split()
    ]
    position = 0

    for page_index, lines in enumerate(pages):
        page_words = " ".join(lines).split()

        # 한 자막에 두 문장을 섞지 않는다 (같은 줄 안의 짧은 문장도 포함)
        if any(SENTENCE_END.search(word) for word in page_words[:-1]):
            return True

        # 줄을 나눈 곳이 어색한 경우
        if len(lines) == 2:
            first_end = position + len(lines[0].split()) - 1

            if _line_break_cost(all_words, first_end) >= 2:
                return True

            if _is_short_second_line(lines[1]):
                return True

            gap = abs(text_width(lines[0]) - text_width(lines[1]))

            if gap > MAX_LINE_WIDTH_GAP_PX:
                return True

        # 페이지를 넘긴 곳이 어색한 경우
        # 문장이 이어지는데 한 단어만 다음 페이지로 넘어간 경우도 어색하다
        if page_index > 0 and not SENTENCE_END.search(all_words[position - 1]) and (
            _page_break_cost(all_words, position - 1) >= 45
            or len(page_words) == 1
        ):
            return True

        position += len(page_words)

    return False


def create_narration_cues(
    narration: str,
    duration_sec: float,
    subtitle_pages: list[list[str]] | None = None,
) -> list[SubtitleCue]:
    """내레이션 자막 페이지를 만들고 글자 수 비율로 시간을 배분한다.

    전달받은 페이지(AI 결과 또는 사용자 편집본)가 내레이션과 일치하면 그대로 쓰고,
    아니면 규칙으로 다시 나눈다.

    단어별 음성 정렬이 아니라 글자 수 기반 추정값이다.
    반환되는 시간은 장면 시작을 0으로 하는 장면 기준 시간이다.
    """

    pages = (
        validate_subtitle_pages(subtitle_pages, narration)
        or split_into_pages(narration)
    )

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

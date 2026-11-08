
import math
import re
from functools import lru_cache

from PIL import ImageFont

from app.schemas.audio import SubtitleCue
from app.services.subtitle_styles import SUBTITLE_STYLES

# 자막 한 줄의 최대 폭(px). 1080 화면에서 배경 여백을 뺀 값
SUBTITLE_MAX_WIDTH = 960
SUBTITLE_MAX_LINES = 2

# 쉼표 뒤에서 줄을 나누면 읽기 편하므로 그만큼의 폭 차이를 허용한다
COMMA_BREAK_BONUS_PX = 150


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
# 3. 내레이션을 화면 폭에 맞는 자막 페이지로 분할
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


def _take_page_word_count(words: list[str]) -> int:
    """다음 자막 페이지(최대 2줄)에 넣을 단어 수를 구한다."""

    count = 0
    lines_left = SUBTITLE_MAX_LINES
    line = ""

    for word in words:
        candidate = f"{line} {word}" if line else word

        if text_width(candidate) <= SUBTITLE_MAX_WIDTH:
            line = candidate
        elif lines_left > 1:
            lines_left -= 1
            line = word
        else:
            break

        count += 1

    # 다음 페이지에 단어 하나만 남으면 어색하므로 한 단어를 넘겨준다
    if len(words) - count == 1 and count > 1:
        count -= 1

    return count


def _layout_page(words: list[str]) -> str:
    """단어들을 가장 균형 잡힌 1~2줄로 배치한다."""

    single_line = " ".join(words)

    if text_width(single_line) <= SUBTITLE_MAX_WIDTH:
        return single_line

    best_text = single_line
    best_score = math.inf

    for index in range(1, len(words)):
        first = " ".join(words[:index])
        second = " ".join(words[index:])
        first_width = text_width(first)
        second_width = text_width(second)

        if max(first_width, second_width) > SUBTITLE_MAX_WIDTH:
            continue

        score = abs(first_width - second_width)

        if first.endswith(","):
            score -= COMMA_BREAK_BONUS_PX

        if score < best_score:
            best_score = score
            best_text = f"{first}\n{second}"

    return best_text


def split_into_pages(text: str) -> list[str]:
    """내레이션을 문장 경계를 살려 최대 2줄짜리 자막 페이지로 나눈다."""

    pages: list[str] = []
    sentences = re.split(r"(?<=[.!?…])\s+", text.strip())

    for sentence in sentences:
        words = [
            piece
            for word in sentence.split()
            for piece in _split_long_word(word)
        ]

        while words:
            count = _take_page_word_count(words)
            pages.append(_layout_page(words[:count]))
            words = words[count:]

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

    weights = [len(re.sub(r"\s", "", page)) for page in pages]
    total_weight = sum(weights)

    cues: list[SubtitleCue] = []
    elapsed_weight = 0

    for page, weight in zip(pages, weights):
        start = duration_sec * elapsed_weight / total_weight
        elapsed_weight += weight
        end = duration_sec * elapsed_weight / total_weight

        cues.append(
            SubtitleCue(text=page, start_sec=start, end_sec=end)
        )

    return cues

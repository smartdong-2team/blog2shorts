"""목소리(TTS)로 보낼 문장을 읽기 좋게 바꾼다. 화면 자막은 바꾸지 않는다.

숫자를 한글 발음으로 바꾼다. TTS가 '288,000원'을 제대로 읽지 못해서다.
- 기본은 한자어 수: 288,000원 → 이십팔만팔천원, 2026년 → 이천이십육년, 1급 → 일급
- 개수를 세는 말 앞의 1~99는 고유어 수: 3과목 → 세과목, 5개 → 다섯개
- 소수와 퍼센트: 3.5 → 삼점오, 60% → 육십퍼센트
"""

import re

DIGITS = "영일이삼사오육칠팔구"
SMALL_UNITS = ["", "십", "백", "천"]
LARGE_UNITS = ["", "만", "억", "조"]

# 이 말 앞에서는 1~99를 고유어로 읽는다 (세 과목, 다섯 개)
NATIVE_COUNTERS = (
    "개", "가지", "과목", "시간", "번", "명", "장", "권", "달", "살",
    "마리", "문제", "군데", "곳", "사람", "벌", "켤레",
)
NATIVE_ONES = ["", "한", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉"]
NATIVE_TENS = ["", "열", "스물", "서른", "마흔", "쉰", "예순", "일흔", "여든", "아흔"]

NUMBER = re.compile(r"(\d[\d,]*(?:\.\d+)?)(\s*)(%|[가-힣]*)")


def sino_korean(number: int) -> str:
    """정수를 한자어 수로 읽는다. 예: 288000 → 이십팔만팔천"""

    if number == 0:
        return "영"

    parts = []
    group_index = 0

    while number > 0:
        group = number % 10000
        number //= 10000

        if group:
            words = ""
            for position in range(3, -1, -1):
                digit = group // (10 ** position) % 10
                if digit == 0:
                    continue
                # 십·백·천 앞의 '일'은 읽지 않는다 (십, 백, 천)
                words += ("" if digit == 1 and position > 0 else DIGITS[digit]) + SMALL_UNITS[position]
            # 만 앞의 '일'도 읽지 않는다 (10000 → 만)
            if group == 1 and group_index == 1:
                words = ""
            parts.append(words + LARGE_UNITS[group_index])

        group_index += 1

    return "".join(reversed(parts))


def native_korean(number: int) -> str:
    """1~99를 세는 말 앞의 고유어 수로 읽는다. 예: 3 → 세, 20 → 스무"""

    tens, ones = divmod(number, 10)
    if tens == 2 and ones == 0:
        return "스무"
    return NATIVE_TENS[tens] + NATIVE_ONES[ones]


def _read_number(text: str, following: str) -> str:
    text = text.replace(",", "")

    if "." in text:
        whole, fraction = text.split(".", 1)
        return sino_korean(int(whole)) + "점" + "".join(DIGITS[int(d)] for d in fraction)

    number = int(text)

    # 6월, 10월은 유월, 시월로 읽는다
    if following.startswith("월") and number in (6, 10):
        return "유" if number == 6 else "시"

    if 1 <= number <= 99 and following.startswith(NATIVE_COUNTERS):
        return native_korean(number)

    return sino_korean(number)


def to_spoken_korean(text: str) -> str:
    """숫자를 한글 발음으로 바꾼 문장. 숫자가 없으면 그대로 돌려준다."""

    # 20~24일 → 20에서 24일
    text = re.sub(r"(?<=\d)\s*~\s*(?=\d)", "에서 ", text)

    def replace(match: re.Match) -> str:
        number, space, following = match.groups()
        spoken = _read_number(number, following)
        if following == "%":
            return spoken + space + "퍼센트"
        return spoken + space + following

    return NUMBER.sub(replace, text)

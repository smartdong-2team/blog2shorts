"""목소리용 문장 변환(숫자 → 한글 발음) 테스트."""

import pytest

from app.services.speech_text import native_korean, sino_korean, to_spoken_korean


@pytest.mark.parametrize(
    ("number", "spoken"),
    [
        (0, "영"),
        (10, "십"),
        (11, "십일"),
        (180, "백팔십"),
        (1000, "천"),
        (2026, "이천이십육"),
        (10000, "만"),
        (48000, "사만팔천"),
        (288000, "이십팔만팔천"),
        (100000000, "일억"),
        (110000, "십일만"),
    ],
)
def test_sino_korean(number, spoken):
    assert sino_korean(number) == spoken


@pytest.mark.parametrize(
    ("number", "spoken"),
    [(1, "한"), (3, "세"), (20, "스무"), (21, "스물한"), (99, "아흔아홉")],
)
def test_native_korean(number, spoken):
    assert native_korean(number) == spoken


@pytest.mark.parametrize(
    ("text", "spoken"),
    [
        ("종합반은 288,000원이에요.", "종합반은 이십팔만팔천원이에요."),
        ("민법, 행정법 3과목이에요.", "민법, 행정법 세과목이에요."),
        ("5개 중 1개", "다섯개 중 한개"),
        ("100개", "백개"),
        ("50문항, 80분", "오십문항, 팔십분"),
        ("2026년 7월 20~24일", "이천이십육년 칠월 이십에서 이십사일"),
        ("6월, 10월 시험", "유월, 시월 시험"),
        ("합격률 52.3%", "합격률 오십이점삼퍼센트"),
        ("1차 1급", "일차 일급"),
        ("숫자 없는 문장이에요.", "숫자 없는 문장이에요."),
    ],
)
def test_to_spoken_korean(text, spoken):
    assert to_spoken_korean(text) == spoken

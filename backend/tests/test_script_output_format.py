
"""OpenAI 출력 스키마와 서버 검증 스키마 테스트."""

import pytest
from pydantic import ValidationError

from app.schemas.script import (
    ScriptAIOutput,
    ScriptOutputFormat,
)


@pytest.fixture
def valid_output():
    """정상적인 대본 생성 결과."""

    narration = (
        "인디자인을 효과적으로 공부하려면 "
        "기본 기능을 이해하고 실제 편집 작업을 "
        "반복하면서 실무 감각을 익히는 것이 중요합니다."
    )

    return {
        "summary": {
            "topic": "인디자인 독학",
            "key_points": ["기초 학습", "실습", "복습"],
        },
        "scenes": [
            {
                "order": i + 1,
                "role": (
                    "hook" if i == 0
                    else "cta" if i == 3
                    else "body"
                ),
                "narration": narration,
                "caption": "인디자인 학습",
                "asset_id": None,
            }
            for i in range(4)
        ],
    }


def test_valid_output_passes_both_models(valid_output):
    """정상 데이터는 두 모델 모두 통과한다."""

    ai_output = ScriptOutputFormat.model_validate(valid_output)

    validated = ScriptAIOutput.model_validate(
        ai_output.model_dump()
    )

    assert len(validated.scenes) == 4


def test_too_few_scenes_passes_format_but_fails_rules(valid_output):
    """장면 수가 부족하면 서버 검증에서 실패한다."""

    valid_output["scenes"] = valid_output["scenes"][:3]

    # 출력 형식 검증은 통과
    ai_output = ScriptOutputFormat.model_validate(valid_output)

    assert len(ai_output.scenes) == 3

    # 서비스 규칙 검증은 실패
    with pytest.raises(ValidationError):
        ScriptAIOutput.model_validate(
            ai_output.model_dump()
        )


def test_invalid_order_fails_server_validation(valid_output):
    """장면 순서가 잘못되면 서버 검증에서 실패한다."""

    valid_output["scenes"][1]["order"] = 5

    ai_output = ScriptOutputFormat.model_validate(valid_output)

    with pytest.raises(
        ValidationError,
        match="Scene order must be",
    ):
        ScriptAIOutput.model_validate(
            ai_output.model_dump()
        )


def test_short_narration_fails_server_validation(valid_output):
    """전체 나레이션이 너무 짧으면 실패한다."""

    for scene in valid_output["scenes"]:
        scene["narration"] = "짧은 대본"

    ai_output = ScriptOutputFormat.model_validate(valid_output)

    with pytest.raises(
        ValidationError,
        match="Total narration length",
    ):
        ScriptAIOutput.model_validate(
            ai_output.model_dump()
        )

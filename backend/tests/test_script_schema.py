
import pytest
from pydantic import ValidationError

from app.schemas.script import ScriptAIOutput


@pytest.fixture
def valid_ai_output():
    """모든 스키마 검증 조건을 만족하는 정상 AI 응답."""

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
        "hook_text": "인디자인 독학, 어디서부터?",
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



def test_valid_ai_output(valid_ai_output):
    """정상적인 AI 결과는 검증을 통과한다."""
    result = ScriptAIOutput.model_validate(valid_ai_output)
    assert len(result.scenes) == 4


def test_invalid_scene_order(valid_ai_output):
    """장면 순서가 연속되지 않으면 실패한다."""
    valid_ai_output["scenes"][1]["order"] = 5

    with pytest.raises(ValidationError):
        ScriptAIOutput.model_validate(valid_ai_output)


def test_invalid_scene_role(valid_ai_output):
    """마지막 장면이 CTA가 아니면 실패한다."""
    valid_ai_output["scenes"][-1]["role"] = "body"

    with pytest.raises(ValidationError):
        ScriptAIOutput.model_validate(valid_ai_output)

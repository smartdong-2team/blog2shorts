"""
대본 생성 API 테스트

"""


from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.script import ScriptGenerateResponse
from app.services.script_generate import ScriptGenerationError


client = TestClient(app)

API_URL = "/api/v1/scripts/generate"

VALID_REQUEST = {
    "title": "인디자인 독학",
    "text": "인디자인을 공부할 때는 기본 기능을 익히고 직접 편집물을 제작하면서 연습하는 것이 중요합니다. " * 5,
    "images": [],
    "target_duration_sec": 45,
}


# --------------------------------------------------
# 1. 정상적인 대본 생성 요청
# --------------------------------------------------
def make_response() -> ScriptGenerateResponse:
    """테스트에 사용할 정상적인 대본 생성 결과."""

    narration = (
        "인디자인을 효과적으로 공부하려면 기본 기능을 익히고 "
        "실제 편집물을 제작하면서 반복적으로 연습하는 것이 중요합니다."
    )

    return ScriptGenerateResponse(
        summary={
            "topic": "인디자인 독학",
            "key_points": ["기본 기능", "실습"],
        },
        scenes=[
            {
                "order": i + 1,
                "role": "hook" if i == 0 else "cta" if i == 3 else "body",
                "narration": narration,
                "caption": "인디자인 학습",
                "asset_id": None,
            }
            for i in range(4)
        ],
        estimated_duration_sec=40,
    )


# --------------------------------------------------
# 2. 대본 생성 API 테스트
# --------------------------------------------------
def test_generate_script_success():
    """정상 요청은 HTTP 200을 반환한다."""

    fake_response = make_response()

    with patch(
        "app.api.v1.scripts.generate_script",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = fake_response

        response = client.post(API_URL, json=VALID_REQUEST)

    assert response.status_code == 200
    assert response.json()["summary"]["topic"] == "인디자인 독학"
    assert len(response.json()["scenes"]) == 4
    assert response.json()["estimated_duration_sec"] == 40
    mock_generate.assert_awaited_once()


# --------------------------------------------------
# 3. 대본 생성 요청 실패 테스트
# --------------------------------------------------
def test_generate_script_invalid_request():
    """본문이 200자 미만이면 HTTP 422를 반환한다."""

    invalid_request = {
        **VALID_REQUEST,
        "text": "너무 짧은 본문",
    }

    with patch(
        "app.api.v1.scripts.generate_script",
        new_callable=AsyncMock,
    ) as mock_generate:
        response = client.post(API_URL, json=invalid_request)

    assert response.status_code == 422
    mock_generate.assert_not_awaited()


# --------------------------------------------------
# 4. 대본 생성 AI 실패 테스트
# --------------------------------------------------
def test_generate_script_ai_failure():
    """대본 생성이 최종 실패하면 HTTP 502를 반환한다."""

    with patch(
        "app.api.v1.scripts.generate_script",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.side_effect = ScriptGenerationError(
            "대본 생성 실패"
        )

        response = client.post(API_URL, json=VALID_REQUEST)

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "대본 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."
    )
    mock_generate.assert_awaited_once()

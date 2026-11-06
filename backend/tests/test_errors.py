"""공통 오류 응답과 실패 원인 분류 테스트."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import openai
import pytest
from fastapi.testclient import TestClient

from app.api.v1.videos import video_jobs
from app.core.config import get_settings
from app.core.errors import classify_error
from app.core.openai import OpenAIKeyMissingError
from app.main import app
from app.services.script_generate import ScriptGenerationError
from app.services.tts import TTSGenerationError
from app.services.video_render import VideoRenderingError

client = TestClient(app)

SCRIPT_URL = "/api/v1/scripts/generate"
VIDEO_URL = "/api/v1/videos"
SCRIPT_REQUEST = {
    "title": "제목",
    "text": "인디자인을 공부할 때는 직접 편집물을 만들어 보는 것이 중요합니다. " * 10,
    "images": [],
    "target_duration_sec": 45,
}
EXPIRED_MESSAGE = "Your API key has expired. Create a new API key to continue."


def status_error(cls, status: int, message: str = "error", code: str | None = None):
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    return cls(
        message,
        response=httpx.Response(status, request=request),
        body={"code": code} if code else None,
    )


def wrapped(cause: Exception, wrapper: Exception) -> Exception:
    """`raise wrapper from cause`로 만들어진 예외를 돌려준다."""

    wrapper.__cause__ = cause
    return wrapper


REQUEST = httpx.Request("POST", "https://api.openai.com/v1/responses")


# --------------------------------------------------
# 1. 실패 원인 분류
# --------------------------------------------------
@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (status_error(openai.AuthenticationError, 401, EXPIRED_MESSAGE), "OPENAI_API_KEY_EXPIRED"),
        (status_error(openai.AuthenticationError, 401, "Incorrect API key"), "OPENAI_API_KEY_INVALID"),
        (OpenAIKeyMissingError("없음"), "OPENAI_API_KEY_MISSING"),
        (status_error(openai.PermissionDeniedError, 403), "OPENAI_PERMISSION_DENIED"),
        (status_error(openai.RateLimitError, 429, code="insufficient_quota"), "OPENAI_QUOTA_EXCEEDED"),
        (status_error(openai.RateLimitError, 429), "OPENAI_RATE_LIMITED"),
        (status_error(openai.NotFoundError, 404), "OPENAI_MODEL_NOT_FOUND"),
        (openai.APITimeoutError(REQUEST), "OPENAI_TIMEOUT"),
        (openai.APIConnectionError(request=REQUEST), "OPENAI_CONNECTION_FAILED"),
        (status_error(openai.InternalServerError, 500), "OPENAI_SERVER_ERROR"),
        (status_error(openai.BadRequestError, 400), "OPENAI_ERROR"),
        (ScriptGenerationError("검증 실패"), "AI_GENERATION_FAILED"),
        (TTSGenerationError("TTS 실패"), "TTS_FAILED"),
        (VideoRenderingError("FFmpeg 실패"), "RENDER_FAILED"),
        (KeyError("x"), "INTERNAL_ERROR"),
    ],
)
def test_classify_error(exc, code):
    assert classify_error(exc).code == code


def test_classify_error_finds_cause_inside_wrapper():
    """TTS 오류로 감싸져도 실제 원인(키 만료)을 찾는다."""

    exc = wrapped(
        status_error(openai.AuthenticationError, 401, EXPIRED_MESSAGE),
        TTSGenerationError("TTS 음성 생성에 실패했습니다."),
    )

    assert classify_error(exc).code == "OPENAI_API_KEY_EXPIRED"


def test_classified_message_hides_openai_original():
    """OpenAI 원문(키 일부 포함 가능)을 그대로 내보내지 않는다."""

    exc = status_error(openai.AuthenticationError, 401, "Incorrect API key provided: sk-abc")

    assert "sk-abc" not in classify_error(exc).message


# --------------------------------------------------
# 2. API 오류 응답
# --------------------------------------------------
def test_expired_key_response_has_message_and_cors_header():
    """키 만료는 공통 형식으로 내려가고 브라우저가 읽을 수 있어야 한다."""

    origin = get_settings().cors_origins[0]

    with patch(
        "app.api.v1.scripts.generate_script",
        new_callable=AsyncMock,
        side_effect=status_error(openai.AuthenticationError, 401, EXPIRED_MESSAGE),
    ):
        response = client.post(SCRIPT_URL, json=SCRIPT_REQUEST, headers={"Origin": origin})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "OPENAI_API_KEY_EXPIRED"
    assert "만료" in response.json()["error"]["message"]
    assert response.headers["access-control-allow-origin"] == origin


def test_unhandled_error_keeps_cors_header():
    """예상 못 한 예외도 네트워크 오류로 보이지 않도록 CORS 헤더를 붙인다."""

    origin = get_settings().cors_origins[0]
    no_raise_client = TestClient(app, raise_server_exceptions=False)

    with patch(
        "app.api.v1.scripts.generate_script",
        new_callable=AsyncMock,
        side_effect=KeyError("secret-detail"),
    ):
        response = no_raise_client.post(SCRIPT_URL, json=SCRIPT_REQUEST, headers={"Origin": origin})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "secret-detail" not in response.json()["error"]["message"]
    assert response.headers["access-control-allow-origin"] == origin


def test_validation_error_uses_common_format():
    response = client.post(SCRIPT_URL, json={**SCRIPT_REQUEST, "text": "짧음"})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "text" in error["message"]
    assert error["details"][0]["loc"] == ["body", "text"]


# --------------------------------------------------
# 3. 영상 작업 상태 조회
# --------------------------------------------------
def video_request() -> dict:
    return {
        "scenes": [
            {
                "order": 1,
                "role": "hook",
                "narration": "내레이션",
                "caption": "자막",
                "asset_id": str(uuid4()),
            }
        ],
        "voice": None,
    }


def create_failing_job(side_effect: Exception) -> str:
    with (
        patch("app.api.v1.videos.get_asset", return_value=object()),
        patch(
            "app.api.v1.videos.generate_video",
            new_callable=AsyncMock,
            side_effect=side_effect,
        ),
    ):
        response = client.post(VIDEO_URL, json=video_request())

    assert response.status_code == 202
    return response.json()["job_id"]


def test_video_status_reports_expired_key():
    job_id = create_failing_job(
        wrapped(
            status_error(openai.AuthenticationError, 401, EXPIRED_MESSAGE),
            TTSGenerationError("TTS 음성 생성에 실패했습니다."),
        )
    )

    response = client.get(f"{VIDEO_URL}/{job_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error"]["code"] == "OPENAI_API_KEY_EXPIRED"
    video_jobs.pop(job_id)


def test_video_status_reports_pipeline_error_message():
    job_id = create_failing_job(ValueError("이미지를 찾을 수 없습니다"))

    error = client.get(f"{VIDEO_URL}/{job_id}").json()["error"]

    assert error["code"] == "RENDER_FAILED"
    assert "이미지를 찾을 수 없습니다" in error["message"]
    video_jobs.pop(job_id)


def test_video_status_not_found():
    response = client.get(f"{VIDEO_URL}/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"

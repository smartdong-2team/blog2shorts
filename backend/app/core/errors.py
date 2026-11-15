"""공통 오류 응답과 실패 원인 분류.

모든 API 오류를 `{ "error": { code, message, details } }` 형식으로 내려준다.
OpenAI 원문 메시지는 키 일부가 들어갈 수 있어 클라이언트에 그대로 보내지 않는다.
"""

import logging
from collections.abc import Iterator
from typing import Any

import openai
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.nvidia import NvidiaKeyMissingError
from app.core.openai import OpenAIKeyMissingError
from app.services.script_generate import ScriptGenerationError
from app.services.tts import TTSGenerationError
from app.services.video_render import VideoRenderingError

logger = logging.getLogger(__name__)

KEY_FIX_GUIDE = "backend/.env의 OPENAI_API_KEY를 바꾼 뒤 서버를 다시 시작해 주세요."

HTTP_STATUS_CODES = {
    400: "BAD_REQUEST",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "JOB_NOT_READY",
    422: "VALIDATION_ERROR",
    502: "UPSTREAM_ERROR",
}


class AppError(Exception):
    """클라이언트에 그대로 보여줄 수 있는 오류."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _cause_chain(exc: BaseException) -> Iterator[BaseException]:
    """예외와 그 `__cause__`를 바깥쪽부터 차례로 돌려준다."""

    current: BaseException | None = exc
    seen: set[int] = set()

    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__


def _classify_openai_error(exc: openai.OpenAIError) -> AppError:
    def upstream(code: str, message: str) -> AppError:
        return AppError(502, code, message)

    if isinstance(exc, openai.AuthenticationError):
        if "expired" in exc.message.lower():
            return upstream(
                "OPENAI_API_KEY_EXPIRED",
                f"OpenAI API 키가 만료되었습니다. 새 키를 발급받아 {KEY_FIX_GUIDE}",
            )
        return upstream(
            "OPENAI_API_KEY_INVALID",
            f"OpenAI API 키가 올바르지 않습니다. {KEY_FIX_GUIDE}",
        )
    if isinstance(exc, openai.PermissionDeniedError):
        return upstream(
            "OPENAI_PERMISSION_DENIED",
            "이 OpenAI API 키로는 해당 기능을 사용할 권한이 없습니다.",
        )
    if isinstance(exc, openai.RateLimitError):
        if exc.code == "insufficient_quota":
            return upstream(
                "OPENAI_QUOTA_EXCEEDED",
                "OpenAI 크레딧 또는 사용 한도가 소진되었습니다. 결제·한도 설정을 확인해 주세요.",
            )
        return upstream(
            "OPENAI_RATE_LIMITED",
            "OpenAI 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
        )
    if isinstance(exc, openai.NotFoundError):
        return upstream(
            "OPENAI_MODEL_NOT_FOUND",
            "OpenAI 모델을 사용할 수 없습니다. 모델 이름과 계정 권한을 확인해 주세요.",
        )
    # APITimeoutError는 APIConnectionError의 하위 클래스라 먼저 확인한다.
    if isinstance(exc, openai.APITimeoutError):
        return upstream(
            "OPENAI_TIMEOUT",
            "OpenAI 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.",
        )
    if isinstance(exc, openai.APIConnectionError):
        return upstream(
            "OPENAI_CONNECTION_FAILED",
            "OpenAI 서버에 연결하지 못했습니다. 네트워크 상태를 확인해 주세요.",
        )
    if isinstance(exc, openai.InternalServerError):
        return upstream(
            "OPENAI_SERVER_ERROR",
            "OpenAI 서버에 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        )
    if isinstance(
        exc,
        openai.LengthFinishReasonError | openai.ContentFilterFinishReasonError,
    ):
        return upstream(
            "AI_GENERATION_FAILED",
            "AI가 응답을 끝까지 만들지 못했습니다. 본문을 줄이거나 다시 시도해 주세요.",
        )
    return upstream(
        "OPENAI_ERROR",
        f"OpenAI 요청이 실패했습니다. ({type(exc).__name__})",
    )


def classify_error(exc: BaseException) -> AppError:
    """예외를 원인 체인까지 살펴 사용자에게 보여줄 오류로 바꾼다."""

    # 감싼 예외(TTS·대본 생성)보다 안쪽의 실제 원인을 우선한다.
    for item in _cause_chain(exc):
        if isinstance(item, AppError):
            return item
        if isinstance(item, OpenAIKeyMissingError):
            return AppError(
                500,
                "OPENAI_API_KEY_MISSING",
                f"OpenAI API 키가 설정되지 않았습니다. {KEY_FIX_GUIDE}",
            )
        if isinstance(item, NvidiaKeyMissingError):
            return AppError(
                500,
                "NVIDIA_API_KEY_MISSING",
                "NVIDIA API 키가 설정되지 않았습니다. backend/.env에 NVIDIA_API_KEY를 넣거나 SCRIPT_PROVIDER=openai로 바꿔 주세요.",
            )
        if isinstance(item, openai.OpenAIError):
            return _classify_openai_error(item)

    if isinstance(exc, ScriptGenerationError):
        return AppError(
            502,
            "AI_GENERATION_FAILED",
            "AI가 만든 대본이 검증을 통과하지 못했습니다. 다시 시도해 주세요.",
        )
    if isinstance(exc, TTSGenerationError):
        return AppError(502, "TTS_FAILED", str(exc))
    if isinstance(exc, VideoRenderingError):
        return AppError(500, "RENDER_FAILED", str(exc))

    return AppError(
        500,
        "INTERNAL_ERROR",
        f"서버 내부 오류가 발생했습니다. ({type(exc).__name__})",
    )


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": jsonable_encoder(details),
            }
        },
        headers=headers,
    )


async def _handle_app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return _error_response(exc.status_code, exc.code, exc.message)


async def _handle_openai_error(_: Request, exc: Exception) -> JSONResponse:
    error = classify_error(exc)
    logger.warning("OpenAI 요청 실패: %s (%s)", error.code, type(exc).__name__)
    return _error_response(error.status_code, error.code, error.message)


async def _handle_http_exception(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = HTTP_STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
    message = str(exc.detail)
    details = None

    if isinstance(exc.detail, dict):
        extra = dict(exc.detail)
        code = extra.pop("code", code)
        message = extra.pop("message", message)
        details = extra or None

    return _error_response(
        exc.status_code,
        code,
        message,
        details,
        headers=dict(exc.headers) if exc.headers else None,
    )


async def _handle_validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [
        {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
        for item in exc.errors()
    ]
    first = details[0] if details else None
    field = ".".join(str(part) for part in first["loc"] if part != "body") if first else ""
    reason = f" {field}: {first['msg']}" if first else ""

    return _error_response(
        422,
        "VALIDATION_ERROR",
        f"입력값이 올바르지 않습니다.{reason}",
        details,
    )


def register_error_handlers(app: FastAPI) -> None:
    """오류 핸들러와 처리되지 않은 예외용 미들웨어를 등록한다.

    CORS 미들웨어보다 먼저 호출해야 한다. 나중에 등록한 미들웨어가 바깥쪽에서
    실행되므로, 먼저 등록해야 이 응답에도 CORS 헤더가 붙는다.
    `exception_handler(Exception)`은 CORS 바깥에서 실행되어 브라우저가 응답을
    읽지 못하고 네트워크 오류로 보게 되므로 쓰지 않는다.
    """

    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(openai.OpenAIError, _handle_openai_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)

    @app.middleware("http")
    async def catch_unhandled_errors(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logger.exception("처리되지 않은 오류: %s %s", request.method, request.url.path)
            error = classify_error(exc)
            return _error_response(error.status_code, error.code, error.message)

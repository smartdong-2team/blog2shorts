
from openai import AsyncOpenAI

from app.core.config import get_settings


def get_openai_client() -> AsyncOpenAI:
    """설정된 API 키로 OpenAI 비동기 클라이언트를 생성한다."""

    settings = get_settings()

    if (
        settings.openai_api_key is None
        or not settings.openai_api_key.get_secret_value()
    ):
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    return AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        max_retries=0,
    )

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """환경변수(또는 backend/.env)에서 읽는 애플리케이션 설정.

    실제 환경변수가 .env 값보다 우선한다. 리스트 값은 JSON 문자열로 지정한다.
    """

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Blog to Shorts API"
    app_env: Literal["development", "production"] = "development"

    # 프론트엔드 개발 서버 Origin. 예: CORS_ORIGINS=["http://localhost:5173"]
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # 아래 값은 이후 단계(콘텐츠 추출·AI·영상)에서 사용한다.
    openai_api_key: SecretStr | None = None
    openai_script_model: str = "gpt-4.1-mini"
    openai_tts_model: str = "tts-1"

    # Supertonic 로컬 음성 모델 (supertonic-2: 빠름, supertonic-3: 31개 언어)
    supertonic_model: str = "supertonic-2"

    # 목소리 빠르기. 1.0이 각 음성의 기본 속도, 1.15면 15% 빠르게 (모든 목소리 공통)
    tts_speed: float = Field(default=1.15, ge=0.5, le=2.0)

    naver_blog_ids: list[str] = ["copper567"]
    storage_dir: Path = BACKEND_DIR / "storage"


@lru_cache
def get_settings() -> Settings:
    return Settings()

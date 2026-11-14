from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
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

    # 대본 생성 AI. nvidia면 NVIDIA 무료 API(build.nvidia.com)를 쓴다. 음성(TTS)은 항상 OpenAI
    script_provider: Literal["openai", "nvidia"] = "openai"
    nvidia_api_key: SecretStr | None = None
    # 이미지 입력과 JSON 스키마 출력을 지원하는 모델이어야 한다
    nvidia_script_model: str = "nvidia/nemotron-3.5-super-vl-120b-a12b"
    naver_blog_ids: list[str] = ["copper567"]
    storage_dir: Path = BACKEND_DIR / "storage"


@lru_cache
def get_settings() -> Settings:
    return Settings()

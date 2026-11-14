
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.audio import AudioAsset, SubtitleCue


# 외부 API 계층
# VideoSceneInput → VideoCreateRequest → VideoCreateResponse
# 프론트엔드 요청 검증 및 작업 접수

# 내부 영상 합성 계층
# VideoSettings → RenderScene → VideoRenderRequest → VideoRenderResult
# 이미지·음성·자막을 이용한 MP4 생성

# ==========================================================
# 1. 내부 영상 렌더링 스키마 (FFmpeg)
# ==========================================================
# 백엔드 내부에서 FFmpeg로 영상을 합성할 때 사용하는 모델.
# 외부 API 요청/응답과는 구분한다.

Motion = Literal[
    "zoom_in",
    "zoom_out",
    "pan_left",
    "pan_right",
]

Voice = Literal[
    "edge_injoon",
    "edge_sunhi",
    "edge_hyunsu",
    "supertonic_male",
    "supertonic_female",
    "calm_female",
    "bright_female",
    "clear_male",
    "low_male",
]


class VideoSettings(BaseModel):
    """영상 출력 설정: 해상도, FPS, 이미지 배치 방식."""

    width: int = Field(default=1080, gt=0)
    height: int = Field(default=1920, gt=0)
    fps: int = Field(default=30, gt=0)
    image_fit: str = Field(default="cover", pattern="^(cover|contain)$")


class RenderScene(BaseModel):
    """렌더링할 개별 장면의 이미지, 음성, 자막 데이터."""

    order: int = Field(ge=1)
    narration: str = Field(min_length=1)
    image_path: Path
    audio: AudioAsset
    subtitles: list[SubtitleCue] = Field(default_factory=list)
    # 장면 이미지 모션
    motion: Motion = "zoom_in"


class VideoRenderRequest(BaseModel):
    """FFmpeg 렌더링 서비스에 전달하는 입력 데이터."""

    scenes: list[RenderScene] = Field(min_length=1)
    output_path: Path
    settings: VideoSettings = Field(default_factory=VideoSettings)

    # 배경음악. music_path가 없으면 내레이션만 사용한다
    music_path: Path | None = None
    music_gain: float = Field(default=0.0, ge=0, le=1)

    # 영상 상단 고정 훅 문구
    hook_text: str = Field(
        default="",
        max_length=40,
        description="영상 전체에 고정 표시할 훅 문구",
    )

    @model_validator(mode="after")
    def validate_scene_order(self):
        orders = [scene.order for scene in self.scenes]

        if orders != list(range(1, len(orders) + 1)):
            raise ValueError(
                "장면 순서는 1부터 연속적으로 증가해야 합니다."
            )

        return self


class VideoRenderResult(BaseModel):
    """렌더링 완료 후 반환하는 MP4 파일 정보."""

    path: Path
    duration_sec: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int = Field(gt=0)


# ==========================================================
# 2. 영상 생성 API 스키마 (POST /api/v1/videos)
# ==========================================================
# 프론트엔드와 백엔드 사이에서 주고받는 데이터 모델.
# 영상 생성 작업을 접수하고 작업 ID를 반환하는 데 사용한다.


class VideoSceneInput(BaseModel):
    """프론트엔드에서 전달하는 편집 완료된 장면 데이터."""

    model_config = ConfigDict(extra="forbid")

    order: int = Field(ge=1)
    role: Literal["hook", "body", "cta"]
    narration: str = Field(min_length=1)
    caption: str = Field(min_length=1)
    asset_id: UUID
    # 프론트엔드에서 선택한 모션
    motion: Motion = "zoom_in"
    # AI가 나눈 자막(페이지별 줄 목록). 문구를 고쳤거나 비어 있으면 서버가 다시 나눈다
    subtitle_pages: list[list[str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_text(self):
        if not self.narration.strip():
            raise ValueError("내레이션이 비어 있습니다.")

        if not self.caption.strip():
            raise ValueError("자막이 비어 있습니다.")

        return self


class VideoCreateRequest(BaseModel):
    """영상 생성 API 요청: 편집된 장면 목록과 음성 설정."""

    model_config = ConfigDict(extra="forbid")

    scenes: list[VideoSceneInput] = Field(min_length=1)
    hook_text: str = Field(
        default="",
        max_length=40,
        description="영상 상단에 고정 표시할 훅 문구",
    )
    # null이면 기본 목소리를 사용한다
    voice: Voice | None = None
    # 배경음악 곡 ID. "none"이면 배경음악 없음
    music: str = "none"
    music_volume: int = Field(default=20, ge=0, le=100)

    @model_validator(mode="after")
    def validate_scenes(self):
        orders = [scene.order for scene in self.scenes]

        if orders != list(range(1, len(orders) + 1)):
            raise ValueError(
                "장면 순서는 1부터 연속적으로 증가해야 합니다."
            )

        return self


class VideoCreateResponse(BaseModel):
    """영상 생성 작업 접수 응답: HTTP 202 Accepted."""

    job_id: str = Field(min_length=1)
    status: Literal["queued"] = "queued"
    status_url: str = Field(min_length=1)

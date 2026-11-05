from pydantic import BaseModel, Field, model_validator

# --------------------------------------------------
# 1. 생성된 음성 파일 경로와 실제 길이
# --------------------------------------------------
class AudioAsset(BaseModel):
    """TTS로 생성한 장면별 음성 파일 정보."""

    path: str = Field(min_length=1)
    duration_sec: float = Field(gt=0)


# --------------------------------------------------
# 2. 자막 텍스트와 표시 시간
# --------------------------------------------------
class SubtitleCue(BaseModel):
    """영상 타임라인에서 자막이 표시되는 구간."""

    text: str = Field(min_length=1)
    start_sec: float = Field(ge=0)
    end_sec: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_timing(self):
        if self.end_sec <= self.start_sec:
            raise ValueError(
                "자막 종료 시간은 시작 시간보다 커야 합니다."
            )
        return self


# --------------------------------------------------
# 3. 한 장면에 속하는 음성·자막·이미지 연결
# --------------------------------------------------
class SceneMedia(BaseModel):
    """영상 합성에 필요한 장면별 음성 및 자막."""

    order: int = Field(ge=1)
    asset_id: str | None = None
    audio: AudioAsset
    subtitles: list[SubtitleCue] = Field(min_length=1)


# --------------------------------------------------
# 4. 전체 영상 합성 결과 - FR-04의 전체 결과를 FR-05에 전달
# --------------------------------------------------
class AudioGenerationResult(BaseModel):
    """FR-04 전체 처리 결과."""

    scenes: list[SceneMedia] = Field(min_length=1)
    total_duration_sec: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_scene_order(self):
        orders = [scene.order for scene in self.scenes]

        if orders != list(range(1, len(orders) + 1)):
            raise ValueError(
                "장면 순서는 1부터 연속적으로 증가해야 합니다."
            )

        return self
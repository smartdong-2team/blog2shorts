
"""
AI 숏폼 대본 생성 API 스키마.

Endpoint: POST /api/v1/scripts/generate

역할:
- 클라이언트 요청 데이터 검증
- OpenAI 생성 결과의 구조 및 비즈니스 규칙 검증
- 프론트엔드에 반환할 최종 응답 구조 정의

참고:
- 요청과 응답의 형식은 API 명세를 기준으로 한다.
- 예상 영상 길이는 AI가 아닌 서버에서 계산한다.
"""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


# 대본 스타일. info: 정보 전달, shorts: 숏츠(질문형 첫 장면). 스타일별 프롬프트는 services/script_prompts.py
ScriptStyle = Literal["info", "shorts"]
DEFAULT_STYLE: ScriptStyle = "shorts"


# --------------------------------------------------
# 1. 요청(Request) 스키마
# --------------------------------------------------

class ScriptImage(BaseModel):
    """대본 생성에 사용할 이미지의 메타데이터."""

    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(
        min_length=1,
        description="업로드된 이미지의 고유 식별자",
    )
    alt: str | None = Field(
        default=None,
        description="이미지 설명. 없으면 null",
    )


class ScriptGenerateRequest(BaseModel):
    """프론트엔드에서 전달하는 대본 생성 요청."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(
        default=None,
        max_length=200,
        description="콘텐츠 제목 (선택)",
    )
    text: str = Field(
        min_length=200,
        max_length=20_000,
        description="대본 생성에 사용할 본문 텍스트",
    )
    images: list[ScriptImage] = Field(
        default_factory=list,
        max_length=20,
        description="사용 가능한 이미지 목록. 직접 입력 시 빈 배열",
    )
    target_duration_sec: int = Field(
        default=45,
        ge=30,
        le=60,
        description="목표 영상 길이(초). 기본값 45초",
    )
    style: ScriptStyle = Field(
        default=DEFAULT_STYLE,
        description="대본 스타일. info: 정보 전달, shorts: 숏츠(질문형 첫 장면)",
    )


# --------------------------------------------------
# 2. 공통 데이터 스키마
# --------------------------------------------------

class ScriptSummary(BaseModel):
    """원본 콘텐츠를 분석한 핵심 정보."""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(
        description="콘텐츠의 핵심 주제",
    )
    key_points: list[str] = Field(
        description="대본 구성에 사용할 핵심 내용 목록",
    )


class ScriptScene(BaseModel):
    """숏폼 영상의 개별 장면 정보."""

    model_config = ConfigDict(extra="forbid")

    order: int = Field(
        ge=1,
        description="장면 순서. 1부터 시작",
    )
    role: Literal["hook", "body", "cta"] = Field(
        description="장면 역할: 도입, 본문, 행동 유도",
    )
    narration: str = Field(
        min_length=1,
        max_length=120,
        description="TTS 음성으로 변환할 장면별 대본",
    )
    caption: str = Field(
        min_length=1,
        max_length=30,
        description="화면에 표시할 짧은 요약 자막",
    )
    subtitle_pages: list[list[str]] = Field(
        default_factory=list,
        description="내레이션을 나눈 자막. 페이지별 줄 목록. 비어 있으면 서버가 규칙으로 나눈다",
    )
    asset_id: str | None = Field(
        default=None,
        description="사용할 이미지 ID. null이면 대체 배경 사용",
    )


# --------------------------------------------------
# 3. AI 생성 결과 스키마
# --------------------------------------------------

class ScriptAIOutput(BaseModel):
    """
    OpenAI가 생성한 대본 결과를 검증한다.

    검증 규칙:
    - 장면 수: 4~6개
    - 장면 순서: 1부터 연속
    - 장면 역할: hook → body → cta
    - 전체 나레이션 길이: 150~350자

    estimated_duration_sec는 AI 출력에 포함하지 않는다.
    """

    model_config = ConfigDict(extra="forbid")

    summary: ScriptSummary

    # 쇼츠에는 상단에 항상 표시되는 훅 문구가 필요합니다. 
    # 기존에는 나레이션 자체를 hook , body, cta로 구분했지만 
    # hook_text를 별도로 두어 영상 상단에 고정 표시되는 훅 문구를 제공합니다.
    hook_text: str = Field(
        min_length=1,
        max_length=40,
        description="영상 상단에 고정 표시할 훅 문구",
    )
    scenes: list[ScriptScene] = Field(
        min_length=4,
        max_length=6,
    )

    @model_validator(mode="after")
    def validate_scenes(self):
        """장면 순서, 역할, 전체 나레이션 길이를 검증한다."""

        for index, scene in enumerate(self.scenes):
            expected_order = index + 1

            if scene.order != expected_order:
                raise ValueError(
                    f"Scene order must be {expected_order}"
                )

            # 첫 장면은 hook, 마지막은 cta,
            # 그 사이 장면은 모두 body여야 한다.
            expected_role = (
                "hook" if index == 0
                else "cta" if index == len(self.scenes) - 1
                else "body"
            )

            if scene.role != expected_role:
                raise ValueError(
                    f"Scene {expected_order} "
                    f"must have role '{expected_role}'"
                )

        # 전체 나레이션 길이는 장면별 글자 수의 합이다.
        total_length = sum(
            len(scene.narration)
            for scene in self.scenes
        )

        if not 150 <= total_length <= 350:
            raise ValueError(
                "Total narration length "
                f"must be between 150 and 350, got {total_length}"
            )

        return self


# --------------------------------------------------
# 4. OpenAI Structured Outputs용 스키마
# OpenAI가 써주는 JSON 구조를 검증하기 위해 별도 스키마를 정의한다.
# --------------------------------------------------
class ScriptOutputScene(BaseModel):
    """OpenAI가 생성할 장면의 기본 구조."""

    model_config = ConfigDict(extra="forbid")

    order: int
    role: Literal["hook", "body", "cta"]
    narration: str
    caption: str
    subtitle_pages: list[list[str]]
    asset_id: str | None


class ScriptOutputFormat(BaseModel):
    """OpenAI Structured Outputs용 응답 스키마."""

    model_config = ConfigDict(extra="forbid")

    summary: ScriptSummary
    hook_text: str = Field(
        description="영상 전체에 고정 표시할 짧은 훅 문구",
    )
    scenes: list[ScriptOutputScene]


# --------------------------------------------------
# 5. 최종 API 응답 스키마
# --------------------------------------------------

class ScriptGenerateResponse(ScriptAIOutput):
    """
    프론트엔드에 반환하는 최종 대본 생성 결과.

    ScriptAIOutput의 검증 규칙을 상속한다.
    서버에서 계산한 예상 영상 길이만 추가한다.
    """

    estimated_duration_sec: int = Field(
        ge=0,
        description="서버에서 글자 수를 기반으로 계산한 예상 영상 길이(초)",
    )

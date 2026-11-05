# request

# {
#   "title": "인디자인독학 실무자들은 이렇게 공부해요",
#   "text": "본문 텍스트 (200~20,000자)",
#   "images": [ { "asset_id": "5b8e…", "alt": null } ],
#   "target_duration_sec": 45
# }


# response
# {
#   "summary": { "topic": "인디자인 독학 방법", "key_points": ["…", "…", "…"] },
#   "scenes": [
#     { "order": 1, "role": "hook", "narration": "디자이너들은 인디자인을 어떻게 공부할까요?", "caption": "실무자는 이렇게 공부한다", "asset_id": "5b8e…" },
#     { "order": 2, "role": "body", "narration": "…", "caption": "…", "asset_id": "…" },
#     { "order": 3, "role": "body", "narration": "…", "caption": "…", "asset_id": null },
#     { "order": 4, "role": "cta",  "narration": "…", "caption": "…", "asset_id": "…" }
#   ],
#   "estimated_duration_sec": 42
# }




from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class ScriptImage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1)
    alt: str | None = None


# 프론트엔드 입력 검증
class ScriptGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(
        default=None,
        max_length=200,
    )
    text: str = Field(
        min_length=200,
        max_length=20_000,
    )
    images: list[ScriptImage] = Field(
        default_factory=list,
        max_length=20,
    )
    target_duration_sec: int = Field(
        default=45,
        ge=30,
        le=60,
    )


#OpenAI 생성 결과 검증
class ScriptAIOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: ScriptSummary
    scenes: list[ScriptScene] = Field(
        min_length=4,
        max_length=6,
    )

    @model_validator(mode="after")
    def validate_scenes(self):
        for index, scene in enumerate(self.scenes):
            if scene.order != index + 1:
                raise ValueError("Invalid scene order")

            expected_role = (
                "hook" if index == 0
                else "cta" if index == len(self.scenes) - 1
                else "body"
            )

            if scene.role != expected_role:
                raise ValueError("Invalid scene role")

        total_length = sum(
            len(scene.narration) for scene in self.scenes
        )

        if not 150 <= total_length <= 350:
            raise ValueError("Invalid narration length")

        return self


class ScriptGenerateResponse(ScriptAIOutput):
    estimated_duration_sec: int = Field(ge=0)

class ScriptSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    key_points: list[str]


class ScriptScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int = Field(ge=1)
    role: Literal["hook", "body", "cta"]
    narration: str = Field(
        min_length=1,
        max_length=120,
    )
    caption: str = Field(
        min_length=1,
        max_length=30,
    )
    asset_id: str | None = None

#예상 영상 길이를 추가한 최종 응답
class ScriptGenerateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: ScriptSummary
    scenes: list[ScriptScene] = Field(
        min_length=4,
        max_length=6,
    )
    estimated_duration_sec: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_scene_structure(self):
        scenes = self.scenes

        for index, scene in enumerate(scenes, start=1):
            if scene.order != index:
                raise ValueError(
                    "Scene order must start at 1 "
                    "and increase sequentially."
                )

            expected_role = (
                "hook"
                if index == 1
                else "cta"
                if index == len(scenes)
                else "body"
            )

            if scene.role != expected_role:
                raise ValueError(
                    f"Scene {index} must have "
                    f"role '{expected_role}'."
                )

        total_length = sum(
            len(scene.narration)
            for scene in scenes
        )

        if not 150 <= total_length <= 350:
            raise ValueError(
                "Total narration length "
                "must be between 150 and 350."
            )

        return self

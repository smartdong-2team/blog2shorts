
"""OpenAI를 이용한 숏폼 대본 생성 서비스."""

import logging
from pydantic import ValidationError
from openai import AsyncOpenAI, APIConnectionError, APITimeoutError, InternalServerError
from app.core.config import get_settings
from app.core.openai import get_openai_client
from app.schemas.script import (
    ScriptAIOutput,
    ScriptOutputFormat,
    ScriptGenerateRequest,
    ScriptGenerateResponse,
)

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2
CHARS_PER_SECOND = 5

class ScriptGenerationError(Exception):
    """대본 생성에 최종적으로 실패한 경우."""




# --------------------------------------------------
# 1. OpenAI 클라이언트 생성 
# --------------------------------------------------
# core -> openai.py로 이동

# --------------------------------------------------
# 2. 이미지 ID 검증
# --------------------------------------------------
def validate_image_ids(
    result: ScriptAIOutput,
    request: ScriptGenerateRequest,
) -> None:
    """생성된 이미지 ID가 요청에 포함된 이미지인지 검증한다."""

    allowed_ids = {image.asset_id for image in request.images}

    for scene in result.scenes:
        if scene.asset_id is not None and scene.asset_id not in allowed_ids:
            raise ValueError(
                f"허용되지 않은 이미지 ID: {scene.asset_id}"
            )

# --------------------------------------------------
# 3. 예상 영상 길이 계산
# --------------------------------------------------
def estimate_duration(result: ScriptAIOutput) -> int:
    """나레이션 글자 수를 기반으로 예상 영상 길이를 계산한다."""

    total_chars = sum(
        len(scene.narration)
        for scene in result.scenes
    )

    return round(total_chars / CHARS_PER_SECOND)

# --------------------------------------------------
# 4. 대본 생성 함수
# --------------------------------------------------
async def generate_script(
    request: ScriptGenerateRequest,
) -> ScriptGenerateResponse:
    """숏폼 대본을 생성하고 검증한 뒤 최종 응답을 반환한다."""

    client = get_openai_client()

    instructions = (
        "너는 교육 콘텐츠를 숏폼 영상 대본으로 변환하는 작가야. "
        "원본의 핵심 정보를 유지하면서 4~6개의 장면을 생성해. "
        "첫 장면은 hook, 마지막 장면은 cta, "
        "중간 장면은 모두 body로 구성해. "
        "장면 순서는 1부터 시작해. "
        "각 장면의 narration은 1~120자, "
        "caption은 1~30자로 작성해. "
        "전체 narration은 150~350자로 작성해. "
        "원본에 없는 사실을 만들어내지 마. "
        "이미지는 제공된 asset_id만 사용하고, "
        "적절한 이미지가 없으면 null을 사용해."
    )

    user_input = (
        f"제목: {request.title or '없음'}\n"
        f"본문:\n{request.text}\n"
        f"목표 영상 길이: {request.target_duration_sec}초\n"
        f"사용 가능한 이미지 ID와 설명:\n"
        f"{[(image.asset_id, image.alt) for image in request.images]}"
    )

    try:
        for attempt in range(MAX_ATTEMPTS):
            try:
                # 1. OpenAI 대본 생성
                response = await client.responses.parse(
                    model="gpt-4.1-mini",
                    instructions=instructions,
                    input=user_input,
                    text_format=ScriptOutputFormat,
                )

                ai_output = response.output_parsed

                if ai_output is None:
                    raise ValueError("AI 대본 생성 결과가 없습니다.")

                # 2. 비즈니스 규칙 검증
                validated = ScriptAIOutput.model_validate(
                    ai_output.model_dump()
                )

                # 3. 이미지 ID 검증
                validate_image_ids(validated, request)

                # 4. 예상 영상 길이 계산
                estimated_duration_sec = estimate_duration(validated)

                # 5. 최종 응답 생성
                return ScriptGenerateResponse(
                    **validated.model_dump(),
                    estimated_duration_sec=estimated_duration_sec,
                )

            except (
                ValidationError,
                ValueError,
                APIConnectionError,
                APITimeoutError,
                InternalServerError,
            ) as error:
                logger.warning(
                    "대본 생성 실패 (%d/%d): %s",
                    attempt + 1,
                    MAX_ATTEMPTS,
                    type(error).__name__,
                )

                if attempt == MAX_ATTEMPTS - 1:
                    raise ScriptGenerationError(
                        "대본 생성 및 검증에 실패했습니다."
                    ) from error
    finally:
        await client.close()

    raise ScriptGenerationError("대본 생성에 실패했습니다.")

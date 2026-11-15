
"""OpenAI를 이용한 숏폼 대본 생성 서비스."""

import asyncio
import base64
import logging
import re
from io import BytesIO
from uuid import UUID

from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError
from openai import APIConnectionError, APITimeoutError, InternalServerError
from app.core.config import get_settings
from app.core.openai import get_openai_client
from app.schemas.script import (
    ScriptAIOutput,
    ScriptOutputFormat,
    ScriptGenerateRequest,
    ScriptGenerateResponse,
)
from app.services.script_prompts import SCRIPT_INSTRUCTIONS
from app.services.storage import get_asset
from app.services.subtitles import clean_subtitle_pages, split_into_pages

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2
CHARS_PER_SECOND = 5

# AI에 보여줄 이미지 제한. 비용과 요청 크기를 줄이기 위해 축소해서 보낸다
MAX_VISION_IMAGES = 8
VISION_IMAGE_MAX_SIDE = 768
VISION_IMAGE_QUALITY = 80

# 격식체 어미 → 해요체 (AI가 원문 말투를 따라 쓰는 경우를 교정한다)
FORMAL_ENDINGS = {
    "바랍니다": "바라요",
    "드립니다": "드려요",
    "합니다": "해요",
    "됩니다": "돼요",
    "있습니다": "있어요",
    "없습니다": "없어요",
    "좋습니다": "좋아요",
    "갑니다": "가요",
    "옵니다": "와요",
    "줍니다": "줘요",
}
SENTENCE_END = r"(?=[.!?…,\"'\s]|$)"


class ScriptGenerationError(Exception):
    """대본 생성에 최종적으로 실패한 경우."""


def _has_final_consonant(char: str) -> bool:
    code = ord(char) - 0xAC00
    return 0 <= code <= 11171 and code % 28 != 0


def normalize_narration_style(text: str) -> str:
    """내레이션의 흔한 격식체 어미를 해요체로 바꾼다."""

    pattern = "|".join(FORMAL_ENDINGS)
    text = re.sub(
        f"({pattern}){SENTENCE_END}",
        lambda match: FORMAL_ENDINGS[match[1]],
        text,
    )

    # "입니다"는 앞 글자 받침에 따라 달라진다: 요령이에요 / 강의예요
    return re.sub(
        rf"(.)입니다{SENTENCE_END}",
        lambda match: (
            f"{match[1]}이에요"
            if _has_final_consonant(match[1])
            else f"{match[1]}예요"
        ),
        text,
    )


def normalize_subtitle_pages(
    pages: list[list[str]],
    narration: str,
) -> list[list[str]]:
    """AI가 나눈 자막을 검사한다. 쓸 수 없으면 규칙으로 다시 나눈다.

    화면에서 바로 편집할 수 있도록 항상 자막 단위를 돌려준다.
    """

    normalized = [
        [normalize_narration_style(line) for line in lines]
        for lines in pages
    ]
    cleaned = clean_subtitle_pages(normalized, narration)

    if cleaned is None:
        logger.info("AI 자막 분할을 쓸 수 없어 규칙으로 나눕니다.")
        return split_into_pages(narration)

    return cleaned


def normalize_ai_output(ai_output: ScriptOutputFormat) -> dict:
    """AI 출력의 말투와 자막 나누기를 교정한 dict를 돌려준다. 검증 전에 쓴다."""

    output = ai_output.model_dump()

    for scene in output["scenes"]:
        scene["narration"] = normalize_narration_style(scene["narration"])
        scene["subtitle_pages"] = normalize_subtitle_pages(
            scene["subtitle_pages"],
            scene["narration"],
        )

    return output


# --------------------------------------------------
# 1. AI에 보여줄 이미지 준비
# --------------------------------------------------
def load_image_data_url(asset_id: str) -> str | None:
    """저장된 이미지를 축소한 JPEG data URL로 만든다. 읽을 수 없으면 None."""

    try:
        asset = get_asset(UUID(asset_id))
    except ValueError:
        return None

    if asset is None:
        return None

    try:
        with Image.open(asset.path) as image:
            image = image.convert("RGB")
            image.thumbnail(
                (VISION_IMAGE_MAX_SIDE, VISION_IMAGE_MAX_SIDE)
            )

            buffer = BytesIO()
            image.save(
                buffer,
                format="JPEG",
                quality=VISION_IMAGE_QUALITY,
            )
    except (UnidentifiedImageError, OSError):
        logger.warning("이미지를 읽을 수 없습니다: %s", asset_id)
        return None

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


async def build_user_content(
    request: ScriptGenerateRequest,
) -> list[dict]:
    """본문과 이미지를 함께 담은 사용자 메시지를 만든다."""

    content: list[dict] = [
        {
            "type": "input_text",
            "text": (
                f"제목: {request.title or '없음'}\n"
                f"본문:\n{request.text}\n"
                f"목표 영상 길이: {request.target_duration_sec}초"
            ),
        }
    ]

    for image in request.images[:MAX_VISION_IMAGES]:
        data_url = await asyncio.to_thread(
            load_image_data_url,
            image.asset_id,
        )

        if data_url is None:
            continue

        content.append(
            {
                "type": "input_text",
                "text": (
                    f"다음 이미지의 asset_id: {image.asset_id}"
                    f" / 설명: {image.alt or '없음'}"
                ),
            }
        )
        content.append(
            {
                "type": "input_image",
                "image_url": data_url,
                "detail": "low",
            }
        )

    return content


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


def fill_missing_images(
    result: ScriptAIOutput,
    request: ScriptGenerateRequest,
) -> None:
    """이미지를 고르지 않은 장면에 아직 쓰지 않은 이미지를 우선 배정한다."""

    image_ids = [image.asset_id for image in request.images]

    if not image_ids:
        return

    used = {scene.asset_id for scene in result.scenes}
    candidates = [
        asset_id for asset_id in image_ids if asset_id not in used
    ] + image_ids

    for scene in result.scenes:
        if scene.asset_id is None:
            scene.asset_id = candidates.pop(0)


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

    user_content = await build_user_content(request)

    try:
        for attempt in range(MAX_ATTEMPTS):
            try:
                # 1. OpenAI 대본 생성
                response = await client.responses.parse(
                    model=get_settings().openai_script_model,
                    instructions=SCRIPT_INSTRUCTIONS,
                    input=[{"role": "user", "content": user_content}],
                    text_format=ScriptOutputFormat,
                )

                ai_output = response.output_parsed

                if ai_output is None:
                    raise ValueError("AI 대본 생성 결과가 없습니다.")

                # 2. 말투 교정 (글자 수가 바뀌므로 검증 전에 수행)
                output = normalize_ai_output(ai_output)

                # 3. 비즈니스 규칙 검증
                validated = ScriptAIOutput.model_validate(output)

                # 4. 이미지 ID 검증과 빈 장면 보완
                validate_image_ids(validated, request)
                fill_missing_images(validated, request)

                # 5. 예상 영상 길이 계산
                estimated_duration_sec = estimate_duration(validated)

                # 6. 최종 응답 생성
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

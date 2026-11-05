
"""OpenAI를 이용한 숏폼 대본 생성 서비스."""

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.schemas.script import (
    ScriptAIOutput,
    ScriptOutputFormat,
    ScriptGenerateRequest,
)


# --------------------------------------------------
# 1. OpenAI 클라이언트 생성 
# --------------------------------------------------
def get_openai_client() -> AsyncOpenAI:
    """설정된 API 키로 OpenAI 비동기 클라이언트를 생성한다."""

    settings = get_settings()

    if settings.openai_api_key is None:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    return AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
    )


# --------------------------------------------------
# 2. 대본 생성 함수
# --------------------------------------------------
async def generate_script(
    request: ScriptGenerateRequest,
) -> ScriptAIOutput:
    """원본 콘텐츠를 숏폼 영상 대본으로 변환한다."""

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
        f"사용 가능한 이미지 ID: "
        f"{[image.asset_id for image in request.images]}"
    )

    # 1. OpenAI 호출
    #ScriptOutputFormat: OpenAI가 어떤 형태의 데이터를 생성해야 하는지 지정
    response = await client.responses.parse(
        model="gpt-4.1-mini",
        instructions=instructions,
        input=user_input,
        text_format=ScriptOutputFormat, 
    )

    # 2. 결과 존재 여부 확인
    ai_output = response.output_parsed

    if ai_output is None:
        raise ValueError("AI 대본 생성 결과가 없습니다.")

    # 3. 서버의 비즈니스 규칙 검증
    #ScriptAIOutput: 생성된 결과가 장면 수, 순서, 글자 수 등 우리 서비스 규칙을 만족하는지 검증
    validated = ScriptAIOutput.model_validate( 
        ai_output.model_dump()
    )

    # 4. 검증된 결과 반환
    return validated

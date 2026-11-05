"""대본 생성 API 라우터.
- 블로그 본문을 숏폼 영상 대본으로 변환하는 API를 제공한다.
- OpenAI API를 호출하여 대본을 생성하고, 생성된 대본을
  서버에서 검증한 후 프론트엔드에 반환한다.
역할:
- OpenAI API 호출 및 재시도 로직 관리
- 생성된 대본의 구조 및 비즈니스 규칙 검증
- 예상 영상 길이 계산 및 반환
참고:
- 요청과 응답의 형식은 API 명세를 기준으로 한다.
- 예상 영상 길이는 AI가 아닌 서버에서 계산한다.
"""



from fastapi import APIRouter, HTTPException

from app.schemas.script import (
    ScriptGenerateRequest,
    ScriptGenerateResponse,
)
from app.services.script_generate import (
    ScriptGenerationError,
    generate_script,
)

router = APIRouter(prefix="/scripts", tags=["scripts"])


# --------------------------------------------------
# 1. 블로그 본문을 숏폼 영상 대본으로 변환하는 API
# --------------------------------------------------
@router.post(
    "/generate",
    response_model=ScriptGenerateResponse,
)
async def create_script(
    request: ScriptGenerateRequest,
) -> ScriptGenerateResponse:
    """블로그 본문을 숏폼 영상 대본으로 변환한다."""

    try:
        return await generate_script(request)

    except ScriptGenerationError as error:
        raise HTTPException(
            status_code=502,
            detail="대본 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.",
        ) from error

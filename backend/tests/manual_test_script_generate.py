
"""실제 OpenAI API를 이용한 대본 생성 테스트."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.script_generate import (
    generate_script,
    ScriptGenerationError,
    validate_image_ids,
)
from app.schemas.script import ScriptOutputFormat,ScriptGenerateRequest,ScriptAIOutput


# --------------------------------------------------
# 1. OpenAI API를 이용한 대본 생성 테스트
# --------------------------------------------------
async def main():
    request = ScriptGenerateRequest(
        title="인디자인 독학을 시작하는 방법",
        text=(
            "인디자인은 책이나 잡지, 브로슈어와 같은 편집물을 "
            "제작할 때 사용하는 디자인 프로그램입니다. "
            "처음 공부할 때는 문서 설정과 페이지 구성부터 익히는 것이 좋습니다. "
            "그다음 텍스트 프레임과 이미지 프레임을 활용하여 "
            "실제 편집물을 만들어보는 연습이 필요합니다. "
            "특히 단락 스타일과 문자 스타일을 익히면 "
            "반복적인 편집 작업을 효율적으로 처리할 수 있습니다. "
            "마지막으로 직접 작은 브로슈어를 제작하면서 "
            "배운 기능을 복습하는 것이 중요합니다. "
            "처음부터 모든 기능을 외우려고 하기보다는 "
            "하나의 결과물을 완성하는 과정에서 필요한 기능을 "
            "익히는 방식이 효과적입니다."
        ),
        images=[],
        target_duration_sec=45,
    )

    print("OpenAI 대본 생성 요청 중...")

    result = await generate_script(request)

    print("\n=== 생성 결과 ===")
    print(result.model_dump_json(indent=2))


# --------------------------------------------------
# 2. 이미지 ID 검증 테스트
# --------------------------------------------------
def test_invalid_image_id():
    """요청에 없는 이미지 ID를 거부하는지 확인한다."""

    request = ScriptGenerateRequest(
        text="테스트 본문입니다. " * 20,
        images=[],
    )

    result = ScriptAIOutput.model_validate({
        "summary": {
            "topic": "테스트",
            "key_points": ["핵심 내용"],
        },
        "scenes": [
            {
                "order": i + 1,
                "role": "hook" if i == 0 else "cta" if i == 3 else "body",
                "narration": "인디자인을 효과적으로 공부하려면 기본 기능을 익히고 실제 작업을 반복하며 연습하는 것이 중요합니다.",
                "caption": "인디자인 학습",
                "asset_id": "unknown-image",
            }
            for i in range(4)
        ],
    })

    try:
        validate_image_ids(result, request)
    except ValueError as error:
        print("이미지 검증 정상 작동:", error)
    else:
        raise AssertionError("잘못된 이미지 ID가 허용되었습니다.")


# --------------------------------------------------
# 3. 재시도 로직 테스트
# --------------------------------------------------
async def test_retry_success():
    """첫 번째 실패 후 두 번째 호출에서 성공하는지 확인한다."""

    request = ScriptGenerateRequest(
        text="인디자인을 독학하는 방법에 대한 설명입니다. " * 10,
    )

    # 정상적인 AI 응답을 가짜로 만든다.
    fake_output = ScriptOutputFormat(
        summary={
            "topic": "인디자인 독학",
            "key_points": ["기본 기능", "실습"],
        },
        scenes=[
            {
                "order": i + 1,
                "role": "hook" if i == 0 else "cta" if i == 3 else "body",
                "narration": "인디자인을 효과적으로 공부하려면 기본 기능을 익히고 실제 작업을 반복하며 연습하는 것이 중요합니다.",
                "caption": "인디자인 학습",
                "asset_id": None,
            }
            for i in range(4)
        ],
    )

    # 첫 호출은 실패, 두 번째 호출은 성공
    fake_response = MagicMock()
    fake_response.output_parsed = fake_output

    mock_client = MagicMock()
    mock_client.responses.parse = AsyncMock(
        side_effect=[
            ValueError("첫 번째 호출 실패"),
            fake_response,
        ]
    )
    mock_client.close = AsyncMock()

    with patch(
        "app.services.script_generate.get_openai_client",
        return_value=mock_client,
    ):
        result = await generate_script(request)

    assert result.summary.topic == "인디자인 독학"
    assert result.estimated_duration_sec > 0
    assert mock_client.responses.parse.await_count == 2
    mock_client.close.assert_awaited_once()

    print("재시도 후 성공 테스트 통과!")


# --------------------------------------------------
# 4. 재시도 실패 테스트
# --------------------------------------------------
async def test_retry_failure():
    """두 번 모두 실패하면 최종 오류가 발생하는지 확인한다."""

    request = ScriptGenerateRequest(
        text="인디자인을 독학하는 방법에 대한 설명입니다. " * 10,
    )

    mock_client = MagicMock()
    mock_client.responses.parse = AsyncMock(
        side_effect=ValueError("AI 결과 검증 실패")
    )
    mock_client.close = AsyncMock()

    with patch(
        "app.services.script_generate.get_openai_client",
        return_value=mock_client,
    ):
        try:
            await generate_script(request)
        except ScriptGenerationError:
            pass
        else:
            raise AssertionError(
                "두 번 실패했는데 ScriptGenerationError가 발생하지 않았습니다."
            )

    assert mock_client.responses.parse.await_count == 2
    mock_client.close.assert_awaited_once()

    print("재시도 최종 실패 테스트 통과!")


if __name__ == "__main__":
    test_invalid_image_id()
    asyncio.run(test_retry_success())
    asyncio.run(test_retry_failure())
    asyncio.run(main())


"""실제 OpenAI API를 이용한 대본 생성 테스트."""

import asyncio

from app.schemas.script import ScriptGenerateRequest
from app.services.script_generate import generate_script


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


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from pathlib import Path
from uuid import UUID
from scripts.check_video_render import find_korean_font

from app.schemas.video import VideoCreateRequest
from app.services.video_pipeline import generate_video


BACKEND_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BACKEND_DIR / "output" / "pipeline-check"

ASSET_IDS = [
    "0cf840a2-4d67-4612-ac1c-9ed01c68a207",
    "149559ae-5c08-427a-8bcf-584f4b9caa1a",
    "185df8b9-c562-441c-906f-d59b2887f23e",
]


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    request = VideoCreateRequest(
        scenes=[
            {
                "order": 1,
                "role": "hook",
                "narration": "오늘은 새로운 공부 방법을 알아볼게요.",
                "caption": "새로운 공부 방법",
                "asset_id": UUID(ASSET_IDS[0]),
            },
            {
                "order": 2,
                "role": "body",
                "narration": "첫 번째는 작은 목표부터 시작하는 것입니다.",
                "caption": "작은 목표부터 시작하기",
                "asset_id": UUID(ASSET_IDS[1]),
            },
            {
                "order": 3,
                "role": "cta",
                "narration": "여러분도 오늘부터 하나씩 실천해 보세요.",
                "caption": "오늘부터 실천해 보세요!",
                "asset_id": UUID(ASSET_IDS[2]),
            },
        ]
    )

    print("영상 생성 시작...")

    result = await generate_video(
        request=request,
        output_path=OUTPUT_DIR / "output.mp4",
        work_dir=OUTPUT_DIR / "work",
        font_file=find_korean_font(),
    )

    print("영상 생성 완료!")
    print(f"파일 경로: {result.path}")
    print(f"영상 길이: {result.duration_sec:.2f}초")
    print(f"해상도: {result.width}x{result.height}")
    print(f"FPS: {result.fps}")

    assert result.path.is_file(), "영상 파일이 생성되지 않았습니다."
    assert result.path.stat().st_size > 0, "영상 파일이 비어 있습니다."


if __name__ == "__main__":
    asyncio.run(main())
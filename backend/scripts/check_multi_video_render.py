
import asyncio
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from app.schemas.audio import AudioAsset, SubtitleCue
from app.schemas.video import (
    RenderScene,
    VideoRenderRequest,
    VideoSettings,
)
from app.services.video_render import render_video
from scripts.check_video_render import (
    create_test_audio,
    find_korean_font,
)


OUTPUT_PATH = Path("output/video-check/multi-scene.mp4")


def create_colored_image(
    path: Path,
    color: tuple[int, int, int],
) -> None:
    """장면 구분을 위한 단색 이미지를 생성한다."""

    image = Image.new("RGB", (800, 600), color)
    draw = ImageDraw.Draw(image)

    draw.rectangle(
        (100, 100, 700, 500),
        outline="white",
        width=10,
    )

    image.save(path)


async def main() -> None:
    font_path = find_korean_font()

    scene_configs = [
        ("첫 번째 장면입니다.", (40, 80, 140)),
        ("두 번째 장면입니다.", (70, 130, 90)),
        ("세 번째 장면입니다.", (150, 70, 90)),
    ]

    scenes = []
    scene_start_sec = 0.0
    duration_sec = 3.0

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for order, (caption, color) in enumerate(
            scene_configs,
            start=1,
        ):
            image_path = temp_path / f"image-{order}.jpg"
            audio_path = temp_path / f"audio-{order}.wav"

            create_colored_image(image_path, color)
            create_test_audio(audio_path, duration=duration_sec)

            scenes.append(
                RenderScene(
                    order=order,
                    image_path=image_path,
                    audio=AudioAsset(
                        path=str(audio_path),
                        duration_sec=duration_sec,
                    ),
                    subtitles=[
                        SubtitleCue(
                            text=caption,
                            start_sec=scene_start_sec + 0.5,
                            end_sec=scene_start_sec + 2.5,
                        )
                    ],
                )
            )

            scene_start_sec += duration_sec

        request = VideoRenderRequest(
            scenes=scenes,
            output_path=OUTPUT_PATH,
            settings=VideoSettings(
                width=1080,
                height=1920,
                fps=30,
                image_fit="cover",
            ),
        )

        result = await render_video(
            request=request,
            font_file=font_path,
        )

        print("\n=== 다중 장면 렌더링 완료 ===")
        print(f"영상 경로: {result.path}")
        print(f"영상 길이(요청 기준): {result.duration_sec}초")
        print(f"해상도: {result.width} x {result.height}")
        print(f"FPS: {result.fps}")
        print(f"파일 크기: {result.path.stat().st_size:,} bytes")


if __name__ == "__main__":
    asyncio.run(main())


import asyncio
import math
import struct
import tempfile
import wave
from pathlib import Path

from PIL import Image, ImageDraw

from app.schemas.audio import AudioAsset
from app.schemas.video import RenderScene, VideoSettings
from app.services.video_render import render_scene


def create_test_image(path: Path):
    """테스트용 이미지 생성."""
    image = Image.new("RGB", (800, 600), (40, 80, 140))
    draw = ImageDraw.Draw(image)
    draw.rectangle((100, 100, 700, 500), outline="white", width=10)
    image.save(path)


def create_test_audio(path: Path, duration: float = 3.0):
    """테스트용 WAV 음성 생성 (440Hz 사인파)."""
    sample_rate = 24000
    amplitude = 0.2

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        for i in range(int(sample_rate * duration)):
            sample = int(
                amplitude
                * 32767
                * math.sin(2 * math.pi * 440 * i / sample_rate)
            )
            wav.writeframes(struct.pack("<h", sample))


async def main():
    output_dir = Path("output/video-check")
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)

        image_path = temp / "test.jpg"
        audio_path = temp / "test.wav"

        create_test_image(image_path)
        create_test_audio(audio_path)

        scene = RenderScene(
            order=1,
            image_path=image_path,
            audio=AudioAsset(
                path=str(audio_path),
                duration_sec=3.0,
            ),
            subtitles=[],
        )

        output_path = output_dir / "scene-1.mp4"

        result = await render_scene(
            scene=scene,
            output_path=output_path,
            settings=VideoSettings(
                width=1080,
                height=1920,
                fps=30,
                image_fit="cover",
            ),
        )

        print(f"영상 생성 성공: {result.resolve()}")
        print(f"파일 크기: {result.stat().st_size:,} bytes")


if __name__ == "__main__":
    asyncio.run(main())

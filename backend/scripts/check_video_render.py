
import asyncio
import math
import struct
import tempfile
import wave
from pathlib import Path

from PIL import Image, ImageDraw

from app.schemas.audio import AudioAsset, SubtitleCue
from app.schemas.video import RenderScene, VideoSettings
from app.services.video_render import render_scene


# ==========================================================
# 1. 테스트 환경 설정
# ==========================================================

OUTPUT_DIR = Path("output/video-check")
OUTPUT_PATH = OUTPUT_DIR / "scene-1-subtitled.mp4"

FONT_CANDIDATES = [
    Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    Path("/Library/Fonts/NanumGothic.ttf"),
]

DURATION_SEC = 3.0


def find_korean_font() -> Path:
    """시스템에 설치된 한국어 폰트를 찾는다."""

    for font_path in FONT_CANDIDATES:
        if font_path.is_file():
            return font_path

    raise FileNotFoundError(
        "한국어 폰트를 찾을 수 없습니다. "
        "FONT_CANDIDATES에 설치된 폰트 경로를 추가해 주세요."
    )


# ==========================================================
# 2. 테스트 이미지 생성
# ==========================================================

def create_test_image(path: Path) -> None:
    """세로 영상 합성에 사용할 테스트 이미지를 생성한다."""

    image = Image.new(
        "RGB",
        (800, 600),
        (40, 80, 140),
    )

    draw = ImageDraw.Draw(image)

    draw.rectangle(
        (100, 100, 700, 500),
        outline="white",
        width=10,
    )

    image.save(path)


# ==========================================================
# 3. 테스트 WAV 음성 생성
# ==========================================================

def create_test_audio(
    path: Path,
    duration: float = DURATION_SEC,
) -> None:
    """440Hz 사인파로 테스트용 WAV 음성을 생성한다."""

    sample_rate = 24000
    amplitude = 0.2

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        frames = bytearray()

        for i in range(int(sample_rate * duration)):
            sample = int(
                amplitude
                * 32767
                * math.sin(
                    2 * math.pi * 440 * i / sample_rate
                )
            )

            frames.extend(struct.pack("<h", sample))

        wav.writeframes(frames)


# ==========================================================
# 4. 실제 FFmpeg 자막 렌더링 검증
# ==========================================================

async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    font_path = find_korean_font()

    print("=== FFmpeg 자막 렌더링 검증 ===")
    print(f"사용 폰트: {font_path}")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)

        image_path = temp / "test.jpg"
        audio_path = temp / "test.wav"

        # 테스트용 이미지와 음성 생성
        create_test_image(image_path)
        create_test_audio(audio_path)

        # 전체 영상 기준 자막 타임라인
        scene = RenderScene(
            order=1,
            image_path=image_path,
            audio=AudioAsset(
                path=str(audio_path),
                duration_sec=DURATION_SEC,
            ),
            subtitles=[
                SubtitleCue(
                    text="안녕하세요! 영상 자막 테스트입니다.",
                    start_sec=0.5,
                    end_sec=2.5,
                )
            ],
        )

        settings = VideoSettings(
            width=1080,
            height=1920,
            fps=30,
            image_fit="cover",
        )

        # 실제 FFmpeg 렌더링
        result = await render_scene(
            scene=scene,
            output_path=OUTPUT_PATH,
            settings=settings,
            scene_start_sec=0.0,
            font_file=font_path,
        )

        print("\n=== 렌더링 완료 ===")
        print(f"영상 경로: {result.resolve()}")
        print(f"파일 크기: {result.stat().st_size:,} bytes")
        print(f"해상도: {settings.width} x {settings.height}")
        print(f"FPS: {settings.fps}")
        print(f"영상 길이: {DURATION_SEC}초")
        print("자막 표시 구간: 0.5초 ~ 2.5초")
        print("\n영상 파일을 열어 자막 표시 여부를 확인해 주세요.")


if __name__ == "__main__":
    asyncio.run(main())

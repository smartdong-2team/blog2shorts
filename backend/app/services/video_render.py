
import asyncio
from pathlib import Path

from app.schemas.video import RenderScene, VideoSettings


class VideoRenderingError(Exception):
    """FFmpeg 영상 렌더링 실패 시 발생하는 오류."""


async def render_scene(
    scene: RenderScene,
    output_path: Path,
    settings: VideoSettings | None = None,
) -> Path:
    """이미지와 음성을 합성하여 단일 장면 MP4를 생성한다.

    현재 버전은 자막을 합성하지 않는다.
    """

    settings = settings or VideoSettings()

    image_path = scene.image_path
    audio_path = Path(scene.audio.path)

    if not image_path.is_file():
        raise FileNotFoundError(
            f"이미지 파일을 찾을 수 없습니다: {image_path}"
        )

    if not audio_path.is_file():
        raise FileNotFoundError(
            f"음성 파일을 찾을 수 없습니다: {audio_path}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if settings.image_fit == "cover":
        image_filter = (
            f"scale={settings.width}:{settings.height}:"
            "force_original_aspect_ratio=increase,"
            f"crop={settings.width}:{settings.height},"
            "setsar=1"
        )
    else:
        image_filter = (
            f"scale={settings.width}:{settings.height}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={settings.width}:{settings.height}:"
            "(ow-iw)/2:(oh-ih)/2,"
            "setsar=1"
        )

    command = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-framerate", str(settings.fps),
        "-i", str(image_path),
        "-i", str(audio_path),
        "-vf", image_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-r", str(settings.fps),
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", str(scene.audio.duration_sec),
        "-movflags", "+faststart",
        str(output_path),
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        _, stderr = await process.communicate()

        if process.returncode != 0:
            raise VideoRenderingError(
                f"FFmpeg 렌더링 실패: {stderr.decode(errors='replace')}"
            )

        if not output_path.is_file():
            raise VideoRenderingError(
                "FFmpeg 실행 후 출력 파일이 생성되지 않았습니다."
            )

        return output_path

    except Exception:
        output_path.unlink(missing_ok=True)
        raise

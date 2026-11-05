
import asyncio
from pathlib import Path

from app.schemas.video import RenderScene, VideoSettings
from app.schemas.audio import SubtitleCue


class VideoRenderingError(Exception):
    """FFmpeg 영상 렌더링 실패 시 발생하는 오류."""



# 시간 관련 유틸리티
def normalize_subtitles(
    subtitles: list[SubtitleCue],
    scene_start_sec: float,
    scene_duration_sec: float,
) -> list[SubtitleCue]:
    """전체 영상 기준 자막 시간을 장면 기준 시간으로 변환한다."""

    scene_end_sec = scene_start_sec + scene_duration_sec
    normalized = []

    for subtitle in subtitles:
        # 현재 장면과 겹치지 않는 자막은 제외
        if (
            subtitle.end_sec <= scene_start_sec
            or subtitle.start_sec >= scene_end_sec
        ):
            continue

        # 장면 범위를 벗어나는 자막은 잘라낸다.
        local_start = max(
            0.0,
            subtitle.start_sec - scene_start_sec,
        )
        local_end = min(
            scene_duration_sec,
            subtitle.end_sec - scene_start_sec,
        )

        normalized.append(
            SubtitleCue(
                text=subtitle.text,
                start_sec=local_start,
                end_sec=local_end,
            )
        )

    return normalized


# FFmpeg drawtext 필터 생성
def build_subtitle_filter(
    subtitles: list[SubtitleCue],
    font_file: Path,
) -> str:
    """장면 기준 자막 목록을 FFmpeg drawtext 필터로 변환한다."""

    if not subtitles:
        return ""

    # FFmpeg 필터 옵션에 사용되는 특수문자 이스케이프
    def escape_filter_value(value: str) -> str:
        return (
            value
            .replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace("'", r"\'")
            .replace(",", r"\,")
            .replace("[", r"\[")
            .replace("]", r"\]")
            .replace("%", r"\%")
        )

    filters = []

    for subtitle in subtitles:
        text = escape_filter_value(subtitle.text)
        font = escape_filter_value(str(font_file))

        filters.append(
            "drawtext="
            f"fontfile='{font}':"
            f"text='{text}':"
            "fontcolor=white:"
            "fontsize=64:"
            "borderw=4:"
            "bordercolor=black:"
            "x=(w-text_w)/2:"
            "y=h*0.78:"
            f"enable='between(t,{subtitle.start_sec:.3f},"
            f"{subtitle.end_sec:.3f})'"
        )

    return ",".join(filters)


async def render_scene(
    scene: RenderScene,
    output_path: Path,
    settings: VideoSettings | None = None,
    scene_start_sec: float = 0.0,
    font_file: Path | None = None,
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

    
    # 전체 영상 기준 자막을 현재 장면 기준으로 변환
    local_subtitles = normalize_subtitles(
        subtitles=scene.subtitles,
        scene_start_sec=scene_start_sec,
        scene_duration_sec=scene.audio.duration_sec,
    )

    # 자막이 있는 경우에만 drawtext 필터 추가
    if local_subtitles:
        if font_file is None or not font_file.is_file():
            raise FileNotFoundError(
                "자막 렌더링에 사용할 폰트 파일이 필요합니다."
            )

        subtitle_filter = build_subtitle_filter(
            subtitles=local_subtitles,
            font_file=font_file,
        )

        image_filter = f"{image_filter},{subtitle_filter}"


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

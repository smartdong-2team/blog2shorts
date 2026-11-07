
import asyncio
import tempfile
from pathlib import Path
import time
import os


from app.services.subtitle_styles import SUBTITLE_STYLES
from app.schemas.video import RenderScene, VideoSettings
from app.schemas.audio import SubtitleCue
from app.schemas.video import (
    VideoRenderRequest,
    VideoRenderResult,
)

# 로고 이미지 경로
LOGO_PATH = (
    Path(__file__).resolve().parents[2]
    / "assets"
    / "branding"
    / "company_logo.png"
)

FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "ffmpeg")

# 쇼츠 이미지 레이아웃
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 780
IMAGE_Y = 580




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


# 자막 필터
def build_subtitle_filter(
    subtitles: list[SubtitleCue],
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

    style = SUBTITLE_STYLES["default"]  # 현재는 단일 스타일만 사용
    style_font = Path(style["font_file"])

    for subtitle in subtitles:
        text = escape_filter_value(subtitle.text)

        if not style_font.is_file():
            raise FileNotFoundError(
                f"자막 폰트 파일을 찾을 수 없습니다: {style_font}"
            )

        font = escape_filter_value(str(style_font))

        # 자막 스타일 설정
        font_color = style["color"]
        font_size = style["font_size"]
        outline_color = style["outline_color"]
        outline_width = style["outline_width"]

        # 배경 색상 및 투명도
        background_color = style["background_color"]
        background_opacity = style["background_opacity"]
        background_padding = style["background_padding"]

        # FFmpeg 색상 형식: #000000@0.65
        box_color = f"{background_color}@{background_opacity}"

        filters.append(
            "drawtext="
            f"fontfile='{font}':"
            f"text='{text}':"
            f"fontcolor={font_color}:"
            f"fontsize={font_size}:"
            f"borderw={outline_width}:"
            f"bordercolor={outline_color}:"
            "box=1:"
            f"boxcolor={box_color}:"
            f"boxborderw={background_padding}:"
            "x=(w-text_w)/2:"
            "y=1280-text_h/2:"
            f"enable='between(t,{subtitle.start_sec:.3f},"
            f"{subtitle.end_sec:.3f})'"
        )

    return ",".join(filters)


# 훅 필터
def build_hook_filter(hook_text: str) -> str:
    """사용자가 입력한 줄바꿈을 유지하며 영상 상단에 훅을 표시한다."""

    if not hook_text or not hook_text.strip():
        return ""

    style = SUBTITLE_STYLES["default"]
    font_file = Path(style["font_file"])

    if not font_file.is_file():
        raise FileNotFoundError(
            f"훅 폰트 파일을 찾을 수 없습니다: {font_file}"
        )

    # 사용자가 입력한 줄바꿈 유지
    lines = [
        line.strip()
        for line in hook_text.splitlines()
        if line.strip()
    ]

    # 줄바꿈이 없는 긴 문장만 자동 분할
    if len(lines) == 1 and len(lines[0]) > 16:
        import textwrap

        lines = textwrap.wrap(
            lines[0],
            width=16,
            break_long_words=False,
            break_on_hyphens=False,
        )


    # 가장 긴 줄을 기준으로 글자 크기 조절
    max_length = max(len(line) for line in lines)

    if max_length > 20:
        fontsize = 58
    elif max_length > 16:
        fontsize = 68
    else:
        fontsize = 80

    line_height = int(fontsize * 1.3)

    # 상단 영역 중앙 부근에 배치
    # 상단 훅 영역의 중앙을 기준으로 배치
    hook_center_y = 290

    total_height = (len(lines) - 1) * line_height + fontsize
    start_y = int(hook_center_y - total_height / 2)

    font = (
        str(font_file)
        .replace("\\", r"\\")
        .replace(":", r"\:")
    )

    filters = []

    for index, line in enumerate(lines):
        text = (
            line
            .replace("\\", r"\\")
            .replace(":", r"\:")
            .replace("'", r"\'")
            .replace(",", r"\,")
            .replace("%", r"\%")
        )

        y = start_y + index * line_height

        filters.append(
            "drawtext="
            f"fontfile='{font}':"
            f"text='{text}':"
            "fontcolor=white:"
            f"fontsize={fontsize}:"
            "borderw=4:"
            "bordercolor=black:"
            "x=(w-text_w)/2:"
            f"y={y}"
        )

    return ",".join(filters)
# 단일 씬 생성 함수
async def render_scene(
    scene: RenderScene,
    output_path: Path,
    settings: VideoSettings | None = None,
    scene_start_sec: float = 0.0,
    font_file: Path | None = None,
    hook_text: str = "",
) -> Path:

    """이미지와 음성을 합성하여 단일 장면 MP4를 생성한다.

    현재 버전은 자막을 합성하지 않는다.
    """
    print("[DEBUG] render_scene 진입 성공", flush=True)

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

    if not LOGO_PATH.is_file():
        raise FileNotFoundError(
            f"로고 파일을 찾을 수 없습니다: {LOGO_PATH}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    image_filter = (
        f"scale={IMAGE_WIDTH}:{IMAGE_HEIGHT}:"
        "force_original_aspect_ratio=increase,"
        f"crop={IMAGE_WIDTH}:{IMAGE_HEIGHT},"
        f"pad={settings.width}:{settings.height}:0:{IMAGE_Y}:black,"
        "setsar=1"
    )

    # 상단 고정 훅 추가
    if hook_text:
        hook_filter = build_hook_filter(hook_text)

        if hook_filter:
            image_filter = f"{image_filter},{hook_filter}"

    
    print("[DEBUG] 자막 시간 계산 시작", flush=True)
    # 전체 영상 기준 자막을 현재 장면 기준으로 변환
    local_subtitles = normalize_subtitles(
        subtitles=scene.subtitles,
        scene_start_sec=scene_start_sec,
        scene_duration_sec=scene.audio.duration_sec,
    )

    # 자막이 있는 경우에만 drawtext 필터 추가
    if local_subtitles:
        subtitle_filter = build_subtitle_filter(
            subtitles=local_subtitles,
        )

        image_filter = f"{image_filter},{subtitle_filter}"

    # 로고추가하는 부분
    filter_complex = (
        f"[0:v]{image_filter}[base];"
        "[2:v]format=rgba,scale=500:-1[logo];"
        "[base][logo]overlay="
        "x=(W-w)/2:"
        "y=H-h-320:"
        "format=auto,"
        "format=yuv420p[outv]"
    )
    command = [
        FFMPEG_BIN,
        "-y",
        "-loop", "1",
        "-framerate", str(settings.fps),
        "-i", str(image_path),
        "-i", str(audio_path),

        # 로고 이미지 입력
        "-loop", "1",
        "-framerate", str(settings.fps),
        "-i", str(LOGO_PATH),

        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "1:a:0",

        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", str(settings.fps),
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", str(scene.audio.duration_sec),
        "-movflags", "+faststart",
        str(output_path),
    ]

    try:
        print("[FFmpeg] 실행 직전", flush=True)
        print(f"[FFmpeg] 명령어: {command}", flush=True)

        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=None,
        )

        print(
            f"[FFmpeg] 프로세스 시작 (PID: {process.pid})",
            flush=True,
        )

        await asyncio.wait_for(
            process.wait(),
            timeout=60,
        )

        print(
            f"[FFmpeg] 프로세스 종료: {process.returncode}",
            flush=True,
        )

        if process.returncode != 0:
            raise VideoRenderingError(
                f"FFmpeg 렌더링 실패 (종료 코드: {process.returncode})"
            )

        if not output_path.is_file():
            raise VideoRenderingError(
                "FFmpeg 실행 후 출력 파일이 생성되지 않았습니다."
            )

        return output_path

    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        output_path.unlink(missing_ok=True)
        raise VideoRenderingError(
            "FFmpeg 렌더링 시간 초과 (60초)"
        )

    except Exception:
        output_path.unlink(missing_ok=True)
        raise



# 씬을 연결해 하나의 MP4로 합성
async def render_video(
    request: VideoRenderRequest,
    font_file: Path | None = None,
) -> VideoRenderResult:
    """여러 장면을 렌더링하고 하나의 MP4로 연결한다."""

    output_path = request.output_path.resolve()

    # 최종 출력 경로 준비
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 장면별 렌더링은 임시 디렉터리에서 수행한다.
    with tempfile.TemporaryDirectory(
        prefix="blog2shorts-render-"
    ) as temp_dir:
        temp_path = Path(temp_dir)

        scene_paths: list[Path] = []
        scene_start_sec = 0.0

        # 1. 각 장면을 개별 MP4로 렌더링
        # 1. 각 장면을 개별 MP4로 렌더링
        for scene in request.scenes:
            scene_output = (
                temp_path / f"scene-{scene.order:03d}.mp4"
            )

            start = time.perf_counter()

            print(
                f"[Render] 장면 {scene.order} 렌더링 시작",
                flush=True,
            )

            await render_scene(
                scene=scene,
                output_path=scene_output,
                settings=request.settings,
                scene_start_sec=scene_start_sec,
                font_file=font_file,
                hook_text=request.hook_text,
            )

            print(
                f"[Render] 장면 {scene.order} 완료: "
                f"{time.perf_counter() - start:.2f}초",
                flush=True,
            )

            scene_paths.append(scene_output)
            scene_start_sec += scene.audio.duration_sec

        # 2. FFmpeg concat 목록 생성
        concat_file = temp_path / "concat.txt"

        concat_file.write_text(
            "".join(
                f"file '{path.name}'\n"
                for path in scene_paths
            ),
            encoding="utf-8",
        )

        # 3. 장면 영상 연결
        command = [
            FFMPEG_BIN,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            "-movflags", "+faststart",
            str(output_path),
        ]

        try:
            print("[FFmpeg] 프로세스 실행 요청", flush=True)
            print(f"[FFmpeg] 명령어: {command}", flush=True)

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=None,
            )

            print(
                f"[FFmpeg] 프로세스 시작됨 (PID: {process.pid})",
                flush=True,
            )

            await process.wait()

            print(
                f"[FFmpeg] 프로세스 종료 (code: {process.returncode})",
                flush=True,
            )

            if process.returncode != 0:
                raise VideoRenderingError(
                    f"FFmpeg 장면 연결 실패 (종료 코드: {process.returncode})"
                )

            if not output_path.is_file():
                raise VideoRenderingError(
                    "FFmpeg 실행 후 최종 영상이 생성되지 않았습니다."
                )

        except Exception:
            output_path.unlink(missing_ok=True)
            raise

    return VideoRenderResult(
        path=output_path,
        duration_sec=scene_start_sec,
        width=request.settings.width,
        height=request.settings.height,
        fps=request.settings.fps,
    )

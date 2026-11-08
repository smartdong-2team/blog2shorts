
import asyncio
import logging
import tempfile
import textwrap
from pathlib import Path
import os


from app.services.subtitle_styles import SUBTITLE_STYLES
from app.schemas.video import RenderScene, VideoSettings
from app.schemas.audio import SubtitleCue
from app.schemas.video import (
    VideoRenderRequest,
    VideoRenderResult,
)

logger = logging.getLogger(__name__)

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

# 자막 블록의 세로 중심
SUBTITLE_CENTER_Y = 1270

SCENE_TIMEOUT_SEC = 60
CONCAT_TIMEOUT_SEC = 120
MUSIC_TIMEOUT_SEC = 120

# FFmpeg 오류 로그에 남길 마지막 글자 수
STDERR_TAIL_CHARS = 2000


class VideoRenderingError(Exception):
    """FFmpeg 영상 렌더링 실패 시 발생하는 오류."""


# FFmpeg 실행
async def run_ffmpeg(
    command: list[str],
    timeout_sec: float,
    failure_message: str,
) -> None:
    """FFmpeg를 실행하고, 시간 초과·취소 시 프로세스를 함께 종료한다."""

    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        _, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout_sec,
        )

    except asyncio.TimeoutError:
        await _kill_process(process)
        raise VideoRenderingError(
            f"{failure_message}: 시간 초과 ({timeout_sec:g}초)"
        ) from None

    except asyncio.CancelledError:
        await _kill_process(process)
        raise

    if process.returncode != 0:
        logger.error(
            "%s (종료 코드 %s): %s",
            failure_message,
            process.returncode,
            (stderr or b"").decode("utf-8", "replace")[-STDERR_TAIL_CHARS:],
        )
        raise VideoRenderingError(
            f"{failure_message} (종료 코드: {process.returncode})"
        )


async def _kill_process(process) -> None:
    if process.returncode is None:
        process.kill()
        await process.wait()


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
    )


def escape_drawtext_value(text: str) -> str:
    """text='...' 안에 넣을 문자열을 이스케이프한다.

    작은따옴표는 FFmpeg 필터 문법상 그대로 둘 수 없어 같은 모양의 ’로 바꾼다.
    %는 expansion=none으로 그대로 그리므로 이스케이프하지 않는다.
    """

    return (
        text
        .replace("\\", "\\\\")
        .replace("'", "’")
        .replace(":", "\\:")
        .replace(",", "\\,")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace(";", "\\;")
    )


# 자막 필터
def build_subtitle_filter(
    subtitles: list[SubtitleCue],
) -> str:
    """장면 기준 자막 목록을 FFmpeg drawtext 필터로 변환한다.

    자막의 줄바꿈마다 drawtext를 하나씩 만들어 줄별로 가운데 정렬한다.
    """

    if not subtitles:
        return ""

    style = SUBTITLE_STYLES["default"]  # 현재는 단일 스타일만 사용
    style_font = Path(style["font_file"])

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

    # 줄 배경이 겹치지 않고 맞닿는 줄 간격
    line_height = font_size + background_padding * 2

    filters = []

    for subtitle in subtitles:
        lines = subtitle.text.splitlines()

        for index, line in enumerate(lines):
            center_y = (
                SUBTITLE_CENTER_Y
                + (index - (len(lines) - 1) / 2) * line_height
            )
            y = round(center_y - font_size / 2)

            filters.append(
                "drawtext="
                f"fontfile='{font}':"
                f"text='{escape_drawtext_value(line)}':"
                "expansion=none:"
                f"fontcolor={font_color}:"
                f"fontsize={font_size}:"
                f"borderw={outline_width}:"
                f"bordercolor={outline_color}:"
                "box=1:"
                f"boxcolor={box_color}:"
                f"boxborderw={background_padding}:"
                "x=(w-text_w)/2:"
                f"y={y}:"
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

    # 상단 훅 영역의 중앙을 기준으로 배치
    hook_center_y = 290

    total_height = (len(lines) - 1) * line_height + fontsize
    start_y = int(hook_center_y - total_height / 2)

    font = escape_filter_value(str(font_file))

    filters = []

    for index, line in enumerate(lines):
        y = start_y + index * line_height

        filters.append(
            "drawtext="
            f"fontfile='{font}':"
            f"text='{escape_drawtext_value(line)}':"
            "expansion=none:"
            "fontcolor=white:"
            f"fontsize={fontsize}:"
            "borderw=4:"
            "bordercolor=black:"
            "x=(w-text_w)/2:"
            f"y={y}"
        )

    return ",".join(filters)


# 모션 필터
def build_motion_filter(
    motion: str,
    duration_sec: float,
    fps: int,
    motion_duration_sec: float = 1.2,
) -> str:
    """장면 시작 시 짧게 움직이고 마지막 위치에서 정지한다."""

    total_frames = max(1, round(duration_sec * fps))

    motion_frames = max(
        1,
        min(round(motion_duration_sec * fps), total_frames - 1)
    )

    work_width = IMAGE_WIDTH * 2
    work_height = IMAGE_HEIGHT * 2

    base = (
        f"scale={work_width}:{work_height}:"
        "force_original_aspect_ratio=increase,"
        f"crop={work_width}:{work_height},"
        "setsar=1"
    )

    # 0~1.2초 동안 0→1, 이후에는 1로 고정
    progress = f"min(on/{motion_frames},1)"

    # 부드럽게 시작하고 멈추는 ease-in-out
    eased = f"({progress}*{progress}*(3-2*{progress}))"

    # 모션 강도 설정
    ZOOM_AMOUNT = 0.06   # 확대·축소 6%
    PAN_ZOOM = 1.08      # 좌우 이동 시 여백 확보용 확대
    PAN_AMOUNT = 0.30    # 이동 가능한 범위의 30%만 이동

    if motion == "zoom_in":
        zoom = f"1+{ZOOM_AMOUNT}*{eased}"
        x = "iw/2-iw/zoom/2"
        y = "ih/2-ih/zoom/2"

    elif motion == "zoom_out":
        zoom = f"1+{ZOOM_AMOUNT}*(1-{eased})"
        x = "iw/2-iw/zoom/2"
        y = "ih/2-ih/zoom/2"

    elif motion == "pan_left":
        zoom = str(PAN_ZOOM)
        x = f"(iw-iw/zoom)*(0.5+{PAN_AMOUNT}/2-{PAN_AMOUNT}*{eased})"
        y = "ih/2-ih/zoom/2"

    elif motion == "pan_right":
        zoom = str(PAN_ZOOM)
        x = f"(iw-iw/zoom)*(0.5-{PAN_AMOUNT}/2+{PAN_AMOUNT}*{eased})"
        y = "ih/2-ih/zoom/2"

    else:
        raise ValueError(f"지원하지 않는 모션: {motion}")

    return (
        f"{base},"
        f"zoompan="
        f"z='{zoom}':"
        f"x='{x}':"
        f"y='{y}':"
        f"d=1:"
        f"s={work_width}x{work_height}:"
        f"fps={fps},"
        f"scale={IMAGE_WIDTH}:{IMAGE_HEIGHT}:flags=lanczos,"
        "setsar=1"
    )


# 단일 씬 생성 함수
async def render_scene(
    scene: RenderScene,
    output_path: Path,
    settings: VideoSettings | None = None,
    hook_text: str = "",
) -> Path:
    """이미지·음성·훅·자막·로고를 합성하여 단일 장면 MP4를 생성한다.

    scene.subtitles의 시간은 장면 시작을 0으로 하는 장면 기준 시간이다.
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

    if not LOGO_PATH.is_file():
        raise FileNotFoundError(
            f"로고 파일을 찾을 수 없습니다: {LOGO_PATH}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    motion_filter = build_motion_filter(
        motion=scene.motion,
        duration_sec=scene.audio.duration_sec,
        fps=settings.fps,
    )

    image_filter = (
        f"{motion_filter},"
        f"pad={settings.width}:{settings.height}:"
        f"0:{IMAGE_Y}:black,"
        "setsar=1"
    )

    # 상단 고정 훅 추가
    if hook_text:
        hook_filter = build_hook_filter(hook_text)

        if hook_filter:
            image_filter = f"{image_filter},{hook_filter}"

    # 음성 길이를 벗어나는 자막 정리
    local_subtitles = normalize_subtitles(
        subtitles=scene.subtitles,
        scene_start_sec=0.0,
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
        await run_ffmpeg(
            command,
            timeout_sec=SCENE_TIMEOUT_SEC,
            failure_message="FFmpeg 렌더링 실패",
        )

        if not output_path.is_file():
            raise VideoRenderingError(
                "FFmpeg 실행 후 출력 파일이 생성되지 않았습니다."
            )

        return output_path

    except BaseException:
        output_path.unlink(missing_ok=True)
        raise


# 배경음악 믹싱
async def mix_background_music(
    video_path: Path,
    music_path: Path,
    gain: float,
    duration_sec: float,
    output_path: Path,
) -> None:
    """내레이션 아래에 배경음악을 반복해 깔고 끝에서 줄인다."""

    fade_start = max(0.0, duration_sec - 1.0)

    filter_complex = (
        f"[1:a]volume={gain},"
        f"afade=t=out:st={fade_start:.3f}:d=1[music];"
        "[0:a][music]amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.95:level=false[audio]"
    )

    await run_ffmpeg(
        [
            FFMPEG_BIN,
            "-y",
            "-i", str(video_path),
            "-stream_loop", "-1",
            "-i", str(music_path),
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[audio]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", f"{duration_sec:.3f}",
            "-movflags", "+faststart",
            str(output_path),
        ],
        timeout_sec=MUSIC_TIMEOUT_SEC,
        failure_message="FFmpeg 배경음악 합성 실패",
    )


# 씬을 연결해 하나의 MP4로 합성
async def render_video(
    request: VideoRenderRequest,
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
        duration_sec = 0.0

        # 1. 각 장면을 개별 MP4로 렌더링
        for scene in request.scenes:
            scene_output = (
                temp_path / f"scene-{scene.order:03d}.mp4"
            )

            await render_scene(
                scene=scene,
                output_path=scene_output,
                settings=request.settings,
                hook_text=request.hook_text,
            )

            scene_paths.append(scene_output)
            duration_sec += scene.audio.duration_sec

        # 2. FFmpeg concat 목록 생성
        concat_file = temp_path / "concat.txt"

        concat_file.write_text(
            "".join(
                f"file '{path.name}'\n"
                for path in scene_paths
            ),
            encoding="utf-8",
        )

        # 배경음악이 있으면 연결한 영상을 한 번 더 가공한다
        concat_output = (
            temp_path / "concat.mp4"
            if request.music_path
            else output_path
        )

        try:
            # 3. 장면 영상 연결
            await run_ffmpeg(
                [
                    FFMPEG_BIN,
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_file),
                    "-c", "copy",
                    "-movflags", "+faststart",
                    str(concat_output),
                ],
                timeout_sec=CONCAT_TIMEOUT_SEC,
                failure_message="FFmpeg 장면 연결 실패",
            )

            # 4. 배경음악 믹싱
            if request.music_path:
                await mix_background_music(
                    video_path=concat_output,
                    music_path=request.music_path,
                    gain=request.music_gain,
                    duration_sec=duration_sec,
                    output_path=output_path,
                )

            if not output_path.is_file():
                raise VideoRenderingError(
                    "FFmpeg 실행 후 최종 영상이 생성되지 않았습니다."
                )

        except BaseException:
            output_path.unlink(missing_ok=True)
            raise

    return VideoRenderResult(
        path=output_path,
        duration_sec=duration_sec,
        width=request.settings.width,
        height=request.settings.height,
        fps=request.settings.fps,
    )


import asyncio
import re
import shutil
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.schemas.audio import AudioAsset,SubtitleCue
from app.schemas.video import RenderScene, VideoSettings,VideoRenderRequest
from app.services.subtitle_styles import SUBTITLE_STYLES
from app.services.video_render import (
    VideoRenderingError,
    render_scene,
    normalize_subtitles,
    build_subtitle_filter,
    render_video,
    run_ffmpeg,
    FFMPEG_BIN,
)


# ==========================================================
# 테스트 데이터 생성 헬퍼
# ==========================================================

def make_scene(tmp_path: Path) -> RenderScene:
    """임시 이미지와 음성 파일을 사용하는 장면 생성."""

    image_path = tmp_path / "image.jpg"
    audio_path = tmp_path / "audio.wav"

    image_path.write_bytes(b"fake image")
    audio_path.write_bytes(b"fake audio")

    return RenderScene(
        order=1,
        narration="테스트 내레이션",
        image_path=image_path,
        audio=AudioAsset(
            path=str(audio_path),
            duration_sec=2.5,
        ),
        subtitles=[],
    )


def make_mock_process(returncode: int = 0, stderr: bytes = b""):
    """FFmpeg 프로세스 Mock 생성."""

    process = AsyncMock()
    process.returncode = returncode
    process.communicate.return_value = (b"", stderr)

    return process


# ==========================================================
# 1. 정상 렌더링 테스트
# ==========================================================

@pytest.mark.asyncio
async def test_render_scene_success(tmp_path):
    """FFmpeg 실행 성공 시 출력 파일 경로 반환."""

    scene = make_scene(tmp_path)
    output_path = tmp_path / "output" / "scene.mp4"

    process = make_mock_process()

    async def mock_exec(*command, **kwargs):
        output_path.write_bytes(b"fake mp4")
        return process

    with patch(
        "app.services.video_render.asyncio.create_subprocess_exec",
        side_effect=mock_exec,
    ) as mock_subprocess:
        result = await render_scene(scene, output_path)

    assert result == output_path
    assert output_path.exists()
    assert mock_subprocess.call_count == 1


@pytest.mark.asyncio
async def test_render_scene_uses_default_settings(tmp_path):
    """기본 해상도와 FPS가 FFmpeg 명령어에 반영되는지 확인."""

    scene = make_scene(tmp_path)
    output_path = tmp_path / "scene.mp4"
    process = make_mock_process()

    async def mock_exec(*command, **kwargs):
        output_path.write_bytes(b"fake mp4")
        return process

    with patch(
        "app.services.video_render.asyncio.create_subprocess_exec",
        side_effect=mock_exec,
    ) as mock_subprocess:
        await render_scene(scene, output_path)

    command = mock_subprocess.call_args.args

    assert command[0] == "ffmpeg"
    assert "-framerate" in command
    assert command[command.index("-framerate") + 1] == "30"
    assert "pad=1080:1920" in " ".join(command)


@pytest.mark.asyncio
async def test_render_scene_custom_settings(tmp_path):
    """사용자 지정 해상도와 FPS 적용 확인."""

    scene = make_scene(tmp_path)
    output_path = tmp_path / "scene.mp4"

    settings = VideoSettings(
        width=720,
        height=1280,
        fps=24,
        image_fit="contain",
    )

    process = make_mock_process()

    async def mock_exec(*command, **kwargs):
        output_path.write_bytes(b"fake mp4")
        return process

    with patch(
        "app.services.video_render.asyncio.create_subprocess_exec",
        side_effect=mock_exec,
    ) as mock_subprocess:
        await render_scene(scene, output_path, settings)

    command = mock_subprocess.call_args.args
    command_text = " ".join(command)

    assert "pad=720:1280" in command_text
    assert command[command.index("-r") + 1] == "24"


# ==========================================================
# 2. 이미지 배치 방식 테스트
# ==========================================================

@pytest.mark.asyncio
async def test_render_scene_layout(tmp_path):
    """사진 영역을 채운 뒤 9:16 검은 화면에 배치한다."""

    scene = make_scene(tmp_path)
    output_path = tmp_path / "scene.mp4"

    process = make_mock_process()

    async def mock_exec(*command, **kwargs):
        output_path.write_bytes(b"fake mp4")
        return process

    with patch(
        "app.services.video_render.asyncio.create_subprocess_exec",
        side_effect=mock_exec,
    ) as mock_subprocess:
        await render_scene(scene, output_path)

    command_text = " ".join(mock_subprocess.call_args.args)

    assert "crop=2160:1560" in command_text
    assert "pad=1080:1920:0:580:black" in command_text


# ==========================================================
# 3. 입력 파일 검증 테스트
# ==========================================================

@pytest.mark.asyncio
async def test_render_scene_missing_image(tmp_path):
    """이미지 파일이 없으면 오류 발생."""

    scene = make_scene(tmp_path)
    scene.image_path.unlink()

    output_path = tmp_path / "scene.mp4"

    with pytest.raises(FileNotFoundError, match="이미지"):
        await render_scene(scene, output_path)


@pytest.mark.asyncio
async def test_render_scene_missing_audio(tmp_path):
    """음성 파일이 없으면 오류 발생."""

    scene = make_scene(tmp_path)
    Path(scene.audio.path).unlink()

    output_path = tmp_path / "scene.mp4"

    with pytest.raises(FileNotFoundError, match="음성"):
        await render_scene(scene, output_path)


# ==========================================================
# 4. FFmpeg 오류 처리 테스트
# ==========================================================

@pytest.mark.asyncio
async def test_render_scene_ffmpeg_failure(tmp_path):
    """FFmpeg 실패 시 예외 발생 및 부분 출력 파일 삭제."""

    scene = make_scene(tmp_path)
    output_path = tmp_path / "scene.mp4"

    process = make_mock_process(
        returncode=1,
        stderr=b"FFmpeg encoding failed",
    )

    async def mock_exec(*command, **kwargs):
        output_path.write_bytes(b"partial mp4")
        return process

    with patch(
        "app.services.video_render.asyncio.create_subprocess_exec",
        side_effect=mock_exec,
    ):
        with pytest.raises(
            VideoRenderingError,
            match="FFmpeg 렌더링 실패",
        ):
            await render_scene(scene, output_path)

    assert not output_path.exists()


@pytest.mark.asyncio
async def test_render_scene_no_output_file(tmp_path):
    """FFmpeg 성공 코드가 반환되어도 파일이 없으면 오류 발생."""

    scene = make_scene(tmp_path)
    output_path = tmp_path / "scene.mp4"

    process = make_mock_process(returncode=0)

    with patch(
        "app.services.video_render.asyncio.create_subprocess_exec",
        return_value=process,
    ):
        with pytest.raises(
            VideoRenderingError,
            match="출력 파일이 생성되지 않았습니다",
        ):
            await render_scene(scene, output_path)

    assert not output_path.exists()


@pytest.mark.asyncio
async def test_render_scene_subprocess_exception(tmp_path):
    """FFmpeg 프로세스 실행 자체가 실패하는 경우."""

    scene = make_scene(tmp_path)
    output_path = tmp_path / "scene.mp4"

    with patch(
        "app.services.video_render.asyncio.create_subprocess_exec",
        side_effect=OSError("FFmpeg 실행 불가"),
    ):
        with pytest.raises(OSError, match="FFmpeg 실행 불가"):
            await render_scene(scene, output_path)

    assert not output_path.exists()


# ==========================================================
# 5. 기존 입력 파일 보존 테스트
# ==========================================================

@pytest.mark.asyncio
async def test_render_scene_preserves_input_files(tmp_path):
    """렌더링 실패 시에도 원본 이미지와 음성 파일 유지."""

    scene = make_scene(tmp_path)
    output_path = tmp_path / "scene.mp4"

    process = make_mock_process(returncode=1)

    with patch(
        "app.services.video_render.asyncio.create_subprocess_exec",
        return_value=process,
    ):
        with pytest.raises(VideoRenderingError):
            await render_scene(scene, output_path)

    assert scene.image_path.exists()
    assert Path(scene.audio.path).exists()



# ==========================================================
# 6. 자막 시간 변환 테스트
# ==========================================================

def test_normalize_subtitles():
    """전체 영상 시간을 장면 기준 시간으로 변환한다."""

    subtitles = [
        SubtitleCue(
            text="두 번째 장면",
            start_sec=3.0,
            end_sec=6.5,
        )
    ]

    result = normalize_subtitles(
        subtitles=subtitles,
        scene_start_sec=3.0,
        scene_duration_sec=3.5,
    )

    assert len(result) == 1
    assert result[0].start_sec == pytest.approx(0.0)
    assert result[0].end_sec == pytest.approx(3.5)
    assert result[0].text == "두 번째 장면"


def test_normalize_subtitles_clips_overlapping_cues():
    """장면 경계를 넘어가는 자막은 현재 장면 범위로 제한한다."""

    subtitles = [
        SubtitleCue(
            text="앞에서 시작된 자막",
            start_sec=2.0,
            end_sec=4.0,
        ),
        SubtitleCue(
            text="뒤까지 이어지는 자막",
            start_sec=5.0,
            end_sec=8.0,
        ),
    ]

    result = normalize_subtitles(
        subtitles=subtitles,
        scene_start_sec=3.0,
        scene_duration_sec=3.5,
    )

    assert len(result) == 2

    assert result[0].start_sec == pytest.approx(0.0)
    assert result[0].end_sec == pytest.approx(1.0)

    assert result[1].start_sec == pytest.approx(2.0)
    assert result[1].end_sec == pytest.approx(3.5)


def test_normalize_subtitles_excludes_unrelated_cues():
    """현재 장면과 겹치지 않는 자막은 제외한다."""

    subtitles = [
        SubtitleCue(
            text="첫 번째 장면",
            start_sec=0.0,
            end_sec=2.0,
        ),
        SubtitleCue(
            text="세 번째 장면",
            start_sec=7.0,
            end_sec=9.0,
        ),
    ]

    result = normalize_subtitles(
        subtitles=subtitles,
        scene_start_sec=3.0,
        scene_duration_sec=3.5,
    )

    assert result == []


def test_normalize_subtitles_empty():
    """자막이 없는 경우 빈 목록을 반환한다."""

    result = normalize_subtitles(
        subtitles=[],
        scene_start_sec=0.0,
        scene_duration_sec=3.0,
    )

    assert result == []


# ==========================================================
# 7. FFmpeg 자막 필터 생성 테스트
# ==========================================================

def test_build_subtitle_filter():
    """자막 텍스트와 노출 시간이 drawtext 필터에 반영된다."""

    subtitles = [
        SubtitleCue(
            text="안녕하세요",
            start_sec=0.0,
            end_sec=2.5,
        )
    ]

    result = build_subtitle_filter(subtitles=subtitles)

    assert "drawtext=" in result
    assert "안녕하세요" in result
    assert "fontcolor=#FFFFFF" in result
    assert "between(t,0.000,2.500)" in result


def test_build_subtitle_filter_empty():
    """자막이 없으면 필터를 생성하지 않는다."""

    result = build_subtitle_filter(subtitles=[])

    assert result == ""


def test_build_subtitle_filter_multiple_cues():
    """자막이 여러 개일 때 각각의 drawtext 필터를 생성한다."""

    subtitles = [
        SubtitleCue(
            text="첫 번째 자막",
            start_sec=0.0,
            end_sec=1.5,
        ),
        SubtitleCue(
            text="두 번째 자막",
            start_sec=1.5,
            end_sec=3.0,
        ),
    ]

    result = build_subtitle_filter(subtitles=subtitles)

    assert result.count("drawtext=") == 2
    assert "첫 번째 자막" in result
    assert "두 번째 자막" in result


# ==========================================================
# 8. 자막 포함 렌더링 테스트
# ==========================================================

@pytest.mark.asyncio
async def test_render_scene_with_subtitles(tmp_path):
    """자막이 있는 장면은 FFmpeg 명령어에 drawtext를 포함한다."""

    scene = make_scene(tmp_path)
    scene.subtitles = [
        SubtitleCue(
            text="테스트 자막",
            start_sec=0.0,
            end_sec=2.5,
        )
    ]

    output_path = tmp_path / "scene.mp4"

    process = make_mock_process()

    async def mock_exec(*command, **kwargs):
        output_path.write_bytes(b"fake mp4")
        return process

    with patch(
        "app.services.video_render.asyncio.create_subprocess_exec",
        side_effect=mock_exec,
    ) as mock_subprocess:
        result = await render_scene(
            scene=scene,
            output_path=output_path,
        )

    command_text = " ".join(mock_subprocess.call_args.args)

    assert result == output_path
    assert "drawtext=" in command_text
    assert "테스트 자막" in command_text
    assert "between(t,0.000,2.500)" in command_text


@pytest.mark.asyncio
async def test_render_scene_missing_font(tmp_path, monkeypatch):
    """자막이 있는데 폰트 파일이 없으면 오류가 발생한다."""

    scene = make_scene(tmp_path)
    scene.subtitles = [
        SubtitleCue(
            text="테스트 자막",
            start_sec=0.0,
            end_sec=2.5,
        )
    ]

    monkeypatch.setitem(
        SUBTITLE_STYLES["default"],
        "font_file",
        tmp_path / "missing-font.ttf",
    )

    output_path = tmp_path / "scene.mp4"

    with pytest.raises(FileNotFoundError, match="폰트"):
        await render_scene(
            scene=scene,
            output_path=output_path,
        )


@pytest.mark.asyncio
async def test_render_scene_without_subtitles_has_no_drawtext(tmp_path):
    """자막과 훅이 없는 장면에는 drawtext를 넣지 않는다."""

    scene = make_scene(tmp_path)
    output_path = tmp_path / "scene.mp4"
    process = make_mock_process()

    async def mock_exec(*command, **kwargs):
        output_path.write_bytes(b"fake mp4")
        return process

    with patch(
        "app.services.video_render.asyncio.create_subprocess_exec",
        side_effect=mock_exec,
    ) as mock_subprocess:
        result = await render_scene(
            scene=scene,
            output_path=output_path,
        )

    command_text = " ".join(mock_subprocess.call_args.args)

    assert result == output_path
    assert "drawtext=" not in command_text



# ==========================================================
# 9. 다중 장면 렌더링 테스트
# ==========================================================

@pytest.mark.asyncio
async def test_render_video_multiple_scenes(tmp_path):
    """여러 장면이 순서대로 렌더링되고 연결된다."""
    from unittest.mock import AsyncMock

    scenes = []

    for order in range(1, 4):
        image_path = tmp_path / f"image-{order}.jpg"
        audio_path = tmp_path / f"audio-{order}.wav"

        image_path.write_bytes(b"fake image")
        audio_path.write_bytes(b"fake audio")

        scenes.append(
            RenderScene(
                order=order,
                narration="테스트 내레이션",
                image_path=image_path,
                audio=AudioAsset(
                    path=str(audio_path),
                    duration_sec=float(order),
                ),
            )
        )

    request = VideoRenderRequest(
        scenes=scenes,
        output_path=tmp_path / "final.mp4",
    )

    async def fake_render_scene(
        scene,
        output_path,
        settings=None,
        hook_text="",
    ):
        output_path.write_bytes(b"fake scene mp4")
        return output_path

    process = make_mock_process()
    render_calls = []

    async def track_render_scene(**kwargs):
        render_calls.append(kwargs)
        return await fake_render_scene(**kwargs)

    async def mock_exec(*command, **kwargs):
        request.output_path.write_bytes(b"fake final mp4")
        return process

    with (
        patch(
            "app.services.video_render.render_scene",
            side_effect=track_render_scene,
        ),
        patch(
            "app.services.video_render.asyncio.create_subprocess_exec",
            side_effect=mock_exec,
        ) as mock_subprocess,
    ):
        result = await render_video(request)

    assert result.path == request.output_path.resolve()
    assert result.duration_sec == pytest.approx(6.0)
    assert result.width == 1080
    assert result.height == 1920
    assert result.fps == 30

    assert len(render_calls) == 3

    assert [
        call["scene"].order for call in render_calls
    ] == [1, 2, 3]

    command = mock_subprocess.call_args.args

    assert "-f" in command
    assert "concat" in command
    assert "-c" in command
    assert "copy" in command
    assert str(request.output_path.resolve()) in command


@pytest.mark.asyncio
async def test_render_video_concat_failure(tmp_path):
    """FFmpeg 연결 실패 시 오류를 발생시키고 출력 파일을 정리한다."""

    scene = make_scene(tmp_path)

    request = VideoRenderRequest(
        scenes=[scene],
        output_path=tmp_path / "final.mp4",
    )

    async def fake_render_scene(**kwargs):
        kwargs["output_path"].write_bytes(b"fake scene mp4")
        return kwargs["output_path"]

    process = make_mock_process()
    process.returncode = 1
    process.communicate = AsyncMock(
        return_value=(b"", b"concat failed")
    )

    async def mock_exec(*command, **kwargs):
        request.output_path.write_bytes(b"partial mp4")
        return process

    with (
        patch(
            "app.services.video_render.render_scene",
            side_effect=fake_render_scene,
        ),
        patch(
            "app.services.video_render.asyncio.create_subprocess_exec",
            side_effect=mock_exec,
        ),
    ):
        with pytest.raises(
            VideoRenderingError,
            match="장면 연결 실패",
        ):
            await render_video(request)

    assert not request.output_path.exists()


@pytest.mark.asyncio
async def test_render_video_scene_failure(tmp_path):
    """장면 렌더링 실패 시 concat을 실행하지 않는다."""

    scene = make_scene(tmp_path)

    request = VideoRenderRequest(
        scenes=[scene],
        output_path=tmp_path / "final.mp4",
    )

    with (
        patch(
            "app.services.video_render.render_scene",
            side_effect=VideoRenderingError("scene failed"),
        ),
        patch(
            "app.services.video_render.asyncio.create_subprocess_exec",
        ) as mock_subprocess,
    ):
        with pytest.raises(
            VideoRenderingError,
            match="scene failed",
        ):
            await render_video(request)

    mock_subprocess.assert_not_called()
    assert not request.output_path.exists()


@pytest.mark.asyncio
async def test_render_video_missing_final_output(tmp_path):
    """FFmpeg가 성공했지만 최종 파일이 없으면 오류를 발생시킨다."""

    scene = make_scene(tmp_path)

    request = VideoRenderRequest(
        scenes=[scene],
        output_path=tmp_path / "final.mp4",
    )

    async def fake_render_scene(**kwargs):
        kwargs["output_path"].write_bytes(b"fake scene mp4")
        return kwargs["output_path"]

    process = make_mock_process()

    with (
        patch(
            "app.services.video_render.render_scene",
            side_effect=fake_render_scene,
        ),
        patch(
            "app.services.video_render.asyncio.create_subprocess_exec",
            return_value=process,
        ),
    ):
        with pytest.raises(
            VideoRenderingError,
            match="최종 영상이 생성되지 않았습니다",
        ):
            await render_video(request)

    assert not request.output_path.exists()


# ==========================================================
# 10. 두 줄 자막과 특수문자
# ==========================================================

def test_build_subtitle_filter_draws_each_line_separately():
    """줄바꿈마다 drawtext를 만들고 위아래로 나눠 배치한다."""

    result = build_subtitle_filter(
        subtitles=[
            SubtitleCue(
                text="첫째 줄\n둘째 줄",
                start_sec=0.0,
                end_sec=2.0,
            )
        ],
    )

    assert result.count("drawtext=") == 2
    assert "첫째 줄" in result
    assert "둘째 줄" in result

    y_positions = [int(y) for y in re.findall(r":y=(\d+):", result)]
    assert y_positions[0] < y_positions[1]


@pytest.mark.skipif(
    shutil.which(FFMPEG_BIN) is None,
    reason="FFmpeg가 필요합니다.",
)
@pytest.mark.parametrize(
    "text",
    [
        "합격률 50%",
        "it's 특가",
        "쉼표, 콜론: 포함",
        "[한정] 세미콜론; 포함",
        "역슬래시 C:\\경로",
    ],
)
def test_subtitle_filter_accepts_special_characters(text):
    """특수문자가 있어도 실제 FFmpeg가 필터를 처리할 수 있다."""

    subtitle_filter = build_subtitle_filter(
        subtitles=[
            SubtitleCue(text=text, start_sec=0.0, end_sec=1.0)
        ],
    )

    result = subprocess.run(
        [
            FFMPEG_BIN,
            "-loglevel", "error",
            "-f", "lavfi",
            "-i", "color=c=gray:s=1080x1920:d=0.1",
            "-filter_complex", f"[0:v]{subtitle_filter}[out]",
            "-map", "[out]",
            "-frames:v", "1",
            "-f", "null",
            "-",
        ],
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")


# ==========================================================
# 11. 배경음악
# ==========================================================

@pytest.mark.asyncio
async def test_render_video_mixes_music_after_concat(tmp_path):
    """배경음악이 있으면 연결한 영상에 음악을 입혀 최종 파일을 만든다."""

    music_path = tmp_path / "music.mp3"
    music_path.write_bytes(b"fake music")

    request = VideoRenderRequest(
        scenes=[make_scene(tmp_path)],
        output_path=tmp_path / "final.mp4",
        music_path=music_path,
        music_gain=0.12,
    )

    async def fake_render_scene(**kwargs):
        kwargs["output_path"].write_bytes(b"fake scene mp4")
        return kwargs["output_path"]

    commands = []

    async def mock_exec(*command, **kwargs):
        commands.append(command)
        Path(command[-1]).write_bytes(b"fake mp4")
        return make_mock_process()

    with (
        patch(
            "app.services.video_render.render_scene",
            side_effect=fake_render_scene,
        ),
        patch(
            "app.services.video_render.asyncio.create_subprocess_exec",
            side_effect=mock_exec,
        ),
    ):
        await render_video(request)

    concat_command, mix_command = commands

    assert "concat" in concat_command
    assert concat_command[-1] != str(request.output_path.resolve())

    assert str(music_path) in mix_command
    assert "volume=0.12" in " ".join(mix_command)
    assert mix_command[-1] == str(request.output_path.resolve())


# ==========================================================
# 12. 중지 시 FFmpeg 종료
# ==========================================================

@pytest.mark.asyncio
async def test_run_ffmpeg_kills_process_when_cancelled():
    """작업이 취소되면 실행 중인 FFmpeg도 함께 종료한다."""

    started = asyncio.Event()

    async def never_finishes():
        started.set()
        await asyncio.Event().wait()

    process = make_mock_process()
    process.returncode = None
    process.kill = Mock()
    process.communicate = never_finishes

    with patch(
        "app.services.video_render.asyncio.create_subprocess_exec",
        return_value=process,
    ):
        task = asyncio.create_task(
            run_ffmpeg(["ffmpeg"], 60, "실패")
        )
        await started.wait()
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    process.kill.assert_called_once()
    process.wait.assert_awaited_once()


# ==========================================================
# 13. 직접 편집한 긴 자막
# ==========================================================

def test_build_subtitle_filter_shrinks_long_edited_line():
    """화면 폭을 넘는 줄은 글자를 줄여서 넣는다."""

    long_text = "직접 입력한 아주 긴 자막이라서 한 줄에 모두 들어가지 않는 문장"

    result = build_subtitle_filter(
        subtitles=[
            SubtitleCue(text=long_text, start_sec=0.0, end_sec=2.0)
        ],
    )

    font_size = int(re.search(r"fontsize=(\d+)", result)[1])

    assert font_size < SUBTITLE_STYLES["default"]["font_size"]

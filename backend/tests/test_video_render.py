
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.audio import AudioAsset
from app.schemas.video import RenderScene, VideoSettings
from app.services.video_render import (
    VideoRenderingError,
    render_scene,
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
    assert "scale=1080:1920" in " ".join(command)


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

    assert "scale=720:1280" in command_text
    assert "pad=720:1280" in command_text
    assert command[command.index("-r") + 1] == "24"


# ==========================================================
# 2. 이미지 배치 방식 테스트
# ==========================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "image_fit,expected_filter",
    [
        ("cover", "crop=1080:1920"),
        ("contain", "pad=1080:1920"),
    ],
)
async def test_render_scene_image_fit(
    tmp_path,
    image_fit,
    expected_filter,
):
    """cover/contain에 따른 이미지 필터 적용 확인."""

    scene = make_scene(tmp_path)
    output_path = tmp_path / "scene.mp4"
    settings = VideoSettings(image_fit=image_fit)

    process = make_mock_process()

    async def mock_exec(*command, **kwargs):
        output_path.write_bytes(b"fake mp4")
        return process

    with patch(
        "app.services.video_render.asyncio.create_subprocess_exec",
        side_effect=mock_exec,
    ) as mock_subprocess:
        await render_scene(scene, output_path, settings)

    command_text = " ".join(mock_subprocess.call_args.args)

    assert expected_filter in command_text


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

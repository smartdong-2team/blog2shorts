
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.audio import AudioAsset, SubtitleCue
from app.schemas.video import (
    RenderScene,
    VideoCreateRequest,
    VideoCreateResponse,
    VideoRenderRequest,
    VideoRenderResult,
    VideoSceneInput,
    VideoSettings,
)


# ==========================================================
# 테스트 데이터 생성 헬퍼
# ==========================================================

def make_render_scene(order: int = 1) -> RenderScene:
    return RenderScene(
        order=order,
        narration="테스트 내레이션",
        image_path=Path(f"images/scene-{order}.jpg"),
        audio=AudioAsset(
            path=f"audio/scene-{order}.wav",
            duration_sec=2.5,
        ),
        subtitles=[
            SubtitleCue(
                text="테스트 자막",
                start_sec=0.0,
                end_sec=2.5,
            )
        ],
    )


def make_video_scene_input(order: int = 1) -> dict:
    return {
        "order": order,
        "role": "hook" if order == 1 else "body",
        "narration": "테스트 내레이션",
        "caption": "테스트 자막",
        "asset_id": str(uuid4()),
    }


# ==========================================================
# 1. 내부 영상 렌더링 스키마 테스트 (FFmpeg)
# ==========================================================

def test_video_settings_defaults():
    settings = VideoSettings()

    assert settings.width == 1080
    assert settings.height == 1920
    assert settings.fps == 30
    assert settings.image_fit == "cover"


@pytest.mark.parametrize(
    "field,value",
    [
        ("width", 0),
        ("height", -1),
        ("fps", 0),
        ("image_fit", "stretch"),
    ],
)
def test_video_settings_reject_invalid_values(field, value):
    with pytest.raises(ValidationError):
        VideoSettings(**{field: value})


def test_render_scene_valid():
    scene = make_render_scene()

    assert scene.order == 1
    assert scene.image_path == Path("images/scene-1.jpg")
    assert scene.audio.duration_sec == 2.5
    assert len(scene.subtitles) == 1


def test_render_scene_reject_invalid_order():
    with pytest.raises(ValidationError):
        RenderScene(
            order=0,
            image_path="images/test.jpg",
            audio=AudioAsset(
                path="audio/test.wav",
                duration_sec=2.0,
            ),
        )


def test_video_render_request_valid():
    request = VideoRenderRequest(
        scenes=[
            make_render_scene(1),
            make_render_scene(2),
        ],
        output_path="output/video.mp4",
    )

    assert len(request.scenes) == 2
    assert request.settings.width == 1080
    assert request.output_path == Path("output/video.mp4")


@pytest.mark.parametrize(
    "orders",
    [
        [],
        [2],
        [1, 3],
        [1, 1],
        [2, 1],
    ],
)
def test_video_render_request_reject_invalid_scene_orders(orders):
    with pytest.raises(ValidationError):
        VideoRenderRequest(
            scenes=[make_render_scene(order) for order in orders],
            output_path="output/video.mp4",
        )


def test_video_render_result_valid():
    result = VideoRenderResult(
        path="output/video.mp4",
        duration_sec=12.5,
        width=1080,
        height=1920,
        fps=30,
    )

    assert result.path == Path("output/video.mp4")
    assert result.duration_sec == 12.5


@pytest.mark.parametrize(
    "field,value",
    [
        ("duration_sec", 0),
        ("width", 0),
        ("height", -1),
        ("fps", 0),
    ],
)
def test_video_render_result_reject_invalid_values(field, value):
    data = {
        "path": "output/video.mp4",
        "duration_sec": 12.5,
        "width": 1080,
        "height": 1920,
        "fps": 30,
    }
    data[field] = value

    with pytest.raises(ValidationError):
        VideoRenderResult(**data)


# ==========================================================
# 2. 영상 생성 API 스키마 테스트 (POST /api/v1/videos)
# ==========================================================

def test_video_scene_input_valid():
    data = make_video_scene_input()

    scene = VideoSceneInput(**data)

    assert scene.order == 1
    assert scene.role == "hook"
    assert scene.narration == "테스트 내레이션"
    assert scene.asset_id is not None


@pytest.mark.parametrize("role", ["hook", "body", "cta"])
def test_video_scene_input_accept_valid_roles(role):
    data = make_video_scene_input()
    data["role"] = role

    scene = VideoSceneInput(**data)

    assert scene.role == role


@pytest.mark.parametrize(
    "field,value",
    [
        ("order", 0),
        ("role", "intro"),
        ("narration", ""),
        ("narration", "   "),
        ("caption", ""),
        ("caption", "   "),
        ("asset_id", "invalid-uuid"),
    ],
)
def test_video_scene_input_reject_invalid_values(field, value):
    data = make_video_scene_input()
    data[field] = value

    with pytest.raises(ValidationError):
        VideoSceneInput(**data)


def test_video_scene_input_reject_extra_fields():
    data = make_video_scene_input()
    data["unexpected"] = "value"

    with pytest.raises(ValidationError):
        VideoSceneInput(**data)


def test_video_create_request_valid():
    request = VideoCreateRequest(
        scenes=[
            make_video_scene_input(1),
            make_video_scene_input(2),
        ],
        voice=None,
    )

    assert len(request.scenes) == 2
    assert request.voice is None


def test_video_create_request_voice_defaults_to_none():
    request = VideoCreateRequest(
        scenes=[make_video_scene_input()]
    )

    assert request.voice is None


def test_video_create_request_accepts_voice_and_music():
    request = VideoCreateRequest(
        scenes=[make_video_scene_input()],
        voice="low_male",
        music="soft_piano",
        music_volume=50,
    )

    assert request.voice == "low_male"
    assert request.music == "soft_piano"
    assert request.music_volume == 50


@pytest.mark.parametrize("volume", [-1, 101])
def test_video_create_request_rejects_invalid_music_volume(volume):
    with pytest.raises(ValidationError):
        VideoCreateRequest(
            scenes=[make_video_scene_input()],
            music_volume=volume,
        )


def test_video_create_request_rejects_unknown_voice():
    with pytest.raises(ValidationError):
        VideoCreateRequest(
            scenes=[make_video_scene_input()],
            voice="alloy",
        )


@pytest.mark.parametrize(
    "orders",
    [
        [],
        [2],
        [1, 3],
        [1, 1],
        [2, 1],
    ],
)
def test_video_create_request_reject_invalid_scene_orders(orders):
    with pytest.raises(ValidationError):
        VideoCreateRequest(
            scenes=[
                make_video_scene_input(order)
                for order in orders
            ]
        )


def test_video_create_request_reject_extra_fields():
    with pytest.raises(ValidationError):
        VideoCreateRequest(
            scenes=[make_video_scene_input()],
            unexpected="value",
        )


def test_video_create_response_valid():
    response = VideoCreateResponse(
        job_id="c1f2-example",
        status="queued",
        status_url="/api/v1/videos/c1f2-example",
    )

    assert response.job_id == "c1f2-example"
    assert response.status == "queued"
    assert response.status_url == "/api/v1/videos/c1f2-example"


def test_video_create_response_defaults_to_queued():
    response = VideoCreateResponse(
        job_id="job-123",
        status_url="/api/v1/videos/job-123",
    )

    assert response.status == "queued"


def test_video_create_response_reject_invalid_status():
    with pytest.raises(ValidationError):
        VideoCreateResponse(
            job_id="job-123",
            status="completed",
            status_url="/api/v1/videos/job-123",
        )

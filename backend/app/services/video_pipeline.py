
from pathlib import Path
from uuid import UUID

from app.schemas.video import (
    VideoCreateRequest,
    VideoRenderRequest,
    VideoRenderResult,
    RenderScene,
)
from app.services.audio_pipeline import generate_scene_audio
from app.services.music import NO_MUSIC, find_track, music_gain
from app.services.storage import get_asset
from app.services.subtitles import create_narration_cues
from app.services.tts import DEFAULT_VOICE, OPENAI_VOICES
from app.services.video_render import render_video


async def generate_video(
    request: VideoCreateRequest,
    output_path: Path,
    work_dir: Path,
) -> VideoRenderResult:
    """이미지 조회 → TTS 생성 → 자막 분할 → 영상 렌더링."""

    # 1. 입력 이미지 확인
    image_paths = {}

    for scene in request.scenes:
        asset = get_asset(scene.asset_id)

        if asset is None:
            raise ValueError(
                f"이미지를 찾을 수 없습니다: {scene.asset_id}"
            )

        image_paths[scene.asset_id] = asset.path

    # 2. 배경음악 확인 (유료 TTS를 호출하기 전에 실패시킨다)
    music_path = None

    if request.music != NO_MUSIC:
        music_path = find_track(request.music)

        if music_path is None:
            raise ValueError(
                f"배경음악 파일을 찾을 수 없습니다: {request.music}"
            )

    # 3. 장면별 TTS 생성
    audio_result = await generate_scene_audio(
        scenes=request.scenes,
        output_dir=work_dir / "audio",
        voice=OPENAI_VOICES[request.voice or DEFAULT_VOICE],
    )

    # 4. 렌더링에 필요한 장면 데이터 구성
    scene_input_by_order = {
        scene.order: scene
        for scene in request.scenes
    }

    render_scenes = []

    for scene in audio_result.scenes:
        original = scene_input_by_order[scene.order]

        render_scenes.append(
            RenderScene(
                order=scene.order,
                narration=original.narration,
                image_path=image_paths[UUID(scene.asset_id)],
                audio=scene.audio,
                # 음성 전체를 자막으로 보여주되, 의미 단위로 나눈다
                subtitles=create_narration_cues(
                    narration=original.narration,
                    duration_sec=scene.audio.duration_sec,
                    subtitle_pages=original.subtitle_pages,
                ),
                motion=original.motion,
            )
        )

    # 5. 최종 영상 렌더링
    return await render_video(
        VideoRenderRequest(
            scenes=render_scenes,
            output_path=output_path,
            hook_text=request.hook_text,
            music_path=music_path,
            music_gain=music_gain(request.music_volume),
        )
    )


import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal
from uuid import UUID

from app.core.config import get_settings
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
from app.services.tts import DEFAULT_VOICE
from app.services.video_render import render_video


# 전체 진행률에서 단계별 비중(대략값). 장면 렌더링이 음성 생성보다 오래 걸린다
TTS_WEIGHT = 0.3
RENDER_WEIGHT = 0.65
# 나머지 0.05는 장면 연결·배경음악 합성

# 영상은 30초 이상이어야 한다 (FR-05-3). 목소리 길이가 영상 길이다
MIN_VIDEO_SEC = 30.0
# 30초를 맞추려고 목소리를 늦출 때 원래 속도(1.0)보다 더 느리게는 하지 않는다
MIN_STRETCH_SPEED = 1.0

VideoStage = Literal["tts", "rendering", "finishing"]

logger = logging.getLogger(__name__)


@dataclass
class VideoProgress:
    """영상 작업 진행 상황. 화면의 진행률·남은 시간 표시에 쓴다."""

    stage: VideoStage
    # 지금 단계에서 끝난 장면 수 / 전체 장면 수
    done: int
    total: int
    # 전체 작업 기준 0~1
    progress: float


async def generate_video(
    request: VideoCreateRequest,
    output_path: Path,
    work_dir: Path,
    on_progress: Callable[[VideoProgress], None] | None = None,
) -> VideoRenderResult:
    """이미지 조회 → TTS 생성 → 자막 분할 → 영상 렌더링."""

    total_scenes = len(request.scenes)

    def report(stage: VideoStage, done: int, progress: float) -> None:
        if on_progress is not None:
            on_progress(VideoProgress(stage, done, total_scenes, round(min(progress, 1.0), 3)))

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
    report("tts", 0, 0.0)
    audio_result = await generate_scene_audio(
        scenes=request.scenes,
        output_dir=work_dir / "audio",
        voice=request.voice or DEFAULT_VOICE,
        on_scene_done=lambda done, total: report("tts", done, TTS_WEIGHT * done / total),
    )

    # 30초보다 짧으면 모자란 만큼 목소리를 늦춰 한 번 더 만든다
    total_sec = audio_result.total_duration_sec
    speed = get_settings().tts_speed

    if total_sec < MIN_VIDEO_SEC and speed > MIN_STRETCH_SPEED:
        slower = max(MIN_STRETCH_SPEED, speed * total_sec / (MIN_VIDEO_SEC + 0.5))
        logger.info(
            "영상이 %.1f초라 목소리를 %.2f배 → %.2f배로 다시 만듭니다",
            total_sec, speed, slower,
        )

        for scene in audio_result.scenes:
            Path(scene.audio.path).unlink(missing_ok=True)

        audio_result = await generate_scene_audio(
            scenes=request.scenes,
            output_dir=work_dir / "audio",
            voice=request.voice or DEFAULT_VOICE,
            on_scene_done=lambda done, total: report("tts", done, TTS_WEIGHT * done / total),
            speed=slower,
        )

    if audio_result.total_duration_sec < MIN_VIDEO_SEC:
        logger.warning("영상이 %.1f초로 30초보다 짧습니다", audio_result.total_duration_sec)

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

    # 5. 최종 영상 렌더링 (장면별 렌더링이 끝나면 연결·배경음악 합성)
    def scene_rendered(done: int, total: int) -> None:
        if done < total:
            report("rendering", done, TTS_WEIGHT + RENDER_WEIGHT * done / total)
        else:
            report("finishing", done, TTS_WEIGHT + RENDER_WEIGHT)

    report("rendering", 0, TTS_WEIGHT)
    return await render_video(
        VideoRenderRequest(
            scenes=render_scenes,
            output_path=output_path,
            hook_text=request.hook_text,
            music_path=music_path,
            music_gain=music_gain(request.music_volume),
        ),
        on_scene_done=scene_rendered,
    )

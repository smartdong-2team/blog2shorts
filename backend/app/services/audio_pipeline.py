
from pathlib import Path
from typing import Any

#스키마 가져오기
from app.schemas.audio import (
    AudioGenerationResult,
    SceneMedia,
)
from app.services.subtitles import create_subtitle_timeline
from app.services.tts import generate_speech


# --------------------------------------------------
# 1. 여러 장면의 TTS 음성과 자막 타임라인 생성
# --------------------------------------------------
async def generate_scene_audio(
    scenes: list[Any],
    output_dir: Path,
    voice: str = "alloy",
) -> AudioGenerationResult:
    """여러 장면의 TTS 음성과 자막 타임라인을 생성한다."""

    if not scenes:
        raise ValueError("장면 목록이 비어 있습니다.")

    # 장면 순서 정렬
    ordered_scenes = sorted(
        scenes,
        key=lambda scene: scene.order,
    )

    orders = [scene.order for scene in ordered_scenes]

    if orders != list(range(1, len(ordered_scenes) + 1)):
        raise ValueError(
            "장면 순서는 1부터 연속적으로 증가해야 합니다."
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 장면별 TTS 생성
    audio_assets = []

    try:
        for scene in ordered_scenes:
            audio = await generate_speech(
                narration=scene.narration,
                output_dir=output_dir,
                voice=voice,
            )

            audio_assets.append(audio)

        # 2. 실제 음성 길이를 기준으로 자막 타임라인 계산
        captions = [
            scene.caption for scene in ordered_scenes
        ]

        durations = [
            audio.duration_sec for audio in audio_assets
        ]

        subtitles = create_subtitle_timeline(
            captions=captions,
            durations=durations,
        )

        # 3. 영상 합성에 필요한 장면별 데이터 구성
        scene_media = []

        for scene, audio, subtitle in zip(
            ordered_scenes,
            audio_assets,
            subtitles,
        ):
            scene_media.append(
                SceneMedia(
                    order=scene.order,
                    asset_id=str(scene.asset_id),
                    audio=audio,
                    subtitles=[subtitle],
                )
            )

        return AudioGenerationResult(
            scenes=scene_media,
            total_duration_sec=sum(durations),
        )
    except Exception:
        for audio in audio_assets:
            Path(audio.path).unlink(missing_ok=True)

        raise

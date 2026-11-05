
import time
from pathlib import Path
from uuid import UUID

from app.schemas.video import (
    VideoCreateRequest,
    VideoRenderRequest,
    VideoRenderResult,
    RenderScene,
)
from app.services.audio_pipeline import generate_scene_audio
from app.services.storage import get_asset
from app.services.video_render import render_video


async def generate_video(
    request: VideoCreateRequest,
    output_path: Path,
    work_dir: Path,
    font_file: Path | None = None,
) -> VideoRenderResult:
    """이미지 조회 → TTS/자막 생성 → 영상 렌더링."""

    total_start = time.perf_counter()

    # 1. 입력 이미지 확인
    start = time.perf_counter()
    print("[Pipeline] 이미지 조회 시작", flush=True)

    image_paths = {}

    for scene in request.scenes:
        asset = get_asset(scene.asset_id)

        if asset is None:
            raise ValueError(
                f"이미지를 찾을 수 없습니다: {scene.asset_id}"
            )

        image_paths[scene.asset_id] = asset.path

    print(
        f"[Pipeline] 이미지 조회 완료: "
        f"{time.perf_counter() - start:.2f}초",
        flush=True,
    )

    # 2. TTS 및 자막 생성
    start = time.perf_counter()
    print("[Pipeline] TTS + 자막 생성 시작", flush=True)

    audio_result = await generate_scene_audio(
        scenes=request.scenes,
        output_dir=work_dir / "audio",
        voice=request.voice or "alloy",
    )

    print(
        f"[Pipeline] TTS + 자막 생성 완료: "
        f"{time.perf_counter() - start:.2f}초",
        flush=True,
    )

    # 3. 렌더링에 필요한 장면 데이터 구성
    start = time.perf_counter()
    print("[Pipeline] 렌더링 데이터 구성 시작", flush=True)

    render_scenes = []

    for scene in audio_result.scenes:
        render_scenes.append(
            RenderScene(
                order=scene.order,
                image_path=image_paths[UUID(scene.asset_id)],
                audio=scene.audio,
                subtitles=scene.subtitles,
            )
        )

    render_request = VideoRenderRequest(
        scenes=render_scenes,
        output_path=output_path,
    )

    print(
        f"[Pipeline] 렌더링 데이터 구성 완료: "
        f"{time.perf_counter() - start:.2f}초",
        flush=True,
    )

    # 4. 최종 영상 렌더링
    start = time.perf_counter()
    print("[Pipeline] 영상 렌더링 시작", flush=True)

    result = await render_video(
        render_request,
        font_file=font_file,
    )

    print(
        f"[Pipeline] 영상 렌더링 완료: "
        f"{time.perf_counter() - start:.2f}초",
        flush=True,
    )

    # 5. 전체 소요 시간
    total_elapsed = time.perf_counter() - total_start

    print("-" * 40, flush=True)
    print(
        f"[Pipeline] 전체 소요 시간: {total_elapsed:.2f}초",
        flush=True,
    )
    print("-" * 40, flush=True)

    return result

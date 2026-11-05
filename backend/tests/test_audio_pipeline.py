
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.audio import AudioAsset, AudioGenerationResult
from app.services.audio_pipeline import generate_scene_audio
from app.services.tts import TTSGenerationError


def make_scene(
    order: int,
    narration: str = "테스트 내레이션",
    caption: str = "테스트 자막",
    asset_id: str | None = None,
):
    """파이프라인 입력용 장면 객체를 생성한다."""

    return SimpleNamespace(
        order=order,
        narration=narration,
        caption=caption,
        asset_id=asset_id,
    )


def make_audio(
    order: int,
    duration_sec: float,
    output_dir: Path,
) -> AudioAsset:
    """TTS 결과를 대신할 AudioAsset을 생성한다."""

    return AudioAsset(
        path=str(output_dir / f"scene_{order:02d}.wav"),
        duration_sec=duration_sec,
    )


# 1. 여러 장면의 음성 및 자막 생성

@pytest.mark.asyncio
async def test_generate_scene_audio_success(tmp_path):
    scenes = [
        make_scene(
            order=1,
            narration="첫 번째 내레이션",
            caption="첫 번째 자막",
            asset_id="image-001",
        ),
        make_scene(
            order=2,
            narration="두 번째 내레이션",
            caption="두 번째 자막",
            asset_id="image-002",
        ),
        make_scene(
            order=3,
            narration="세 번째 내레이션",
            caption="세 번째 자막",
            asset_id="image-003",
        ),
    ]

    mock_tts = AsyncMock(
        side_effect=[
            make_audio(1, 3.2, tmp_path),
            make_audio(2, 4.5, tmp_path),
            make_audio(3, 2.3, tmp_path),
        ]
    )

    with patch(
        "app.services.audio_pipeline.generate_speech",
        mock_tts,
    ):
        result = await generate_scene_audio(
            scenes=scenes,
            output_dir=tmp_path,
        )

    assert isinstance(result, AudioGenerationResult)
    assert len(result.scenes) == 3
    assert result.total_duration_sec == pytest.approx(10.0)

    assert result.scenes[0].audio.duration_sec == pytest.approx(3.2)
    assert result.scenes[1].audio.duration_sec == pytest.approx(4.5)
    assert result.scenes[2].audio.duration_sec == pytest.approx(2.3)

    assert result.scenes[0].subtitles[0].start_sec == pytest.approx(0.0)
    assert result.scenes[0].subtitles[0].end_sec == pytest.approx(3.2)

    assert result.scenes[1].subtitles[0].start_sec == pytest.approx(3.2)
    assert result.scenes[1].subtitles[0].end_sec == pytest.approx(7.7)

    assert result.scenes[2].subtitles[0].start_sec == pytest.approx(7.7)
    assert result.scenes[2].subtitles[0].end_sec == pytest.approx(10.0)

    assert result.scenes[0].asset_id == "image-001"
    assert result.scenes[1].asset_id == "image-002"
    assert result.scenes[2].asset_id == "image-003"

    assert mock_tts.await_count == 3


# 2. 입력 순서와 관계없이 order 기준으로 처리

@pytest.mark.asyncio
async def test_generate_scene_audio_sorts_scenes(tmp_path):
    scenes = [
        make_scene(3, narration="세 번째"),
        make_scene(1, narration="첫 번째"),
        make_scene(2, narration="두 번째"),
    ]

    mock_tts = AsyncMock(
        side_effect=[
            make_audio(1, 1.0, tmp_path),
            make_audio(2, 2.0, tmp_path),
            make_audio(3, 3.0, tmp_path),
        ]
    )

    with patch(
        "app.services.audio_pipeline.generate_speech",
        mock_tts,
    ):
        result = await generate_scene_audio(
            scenes=scenes,
            output_dir=tmp_path,
        )

    assert [scene.order for scene in result.scenes] == [1, 2, 3]

    narrations = [
        call.kwargs["narration"]
        for call in mock_tts.await_args_list
    ]

    assert narrations == [
        "첫 번째",
        "두 번째",
        "세 번째",
    ]

    assert result.total_duration_sec == pytest.approx(6.0)


# 3. 단일 장면 처리

@pytest.mark.asyncio
async def test_generate_scene_audio_single_scene(tmp_path):
    scenes = [
        make_scene(
            order=1,
            caption="하나의 장면",
        )
    ]

    mock_tts = AsyncMock(
        return_value=make_audio(1, 5.0, tmp_path)
    )

    with patch(
        "app.services.audio_pipeline.generate_speech",
        mock_tts,
    ):
        result = await generate_scene_audio(
            scenes=scenes,
            output_dir=tmp_path,
        )

    assert len(result.scenes) == 1
    assert result.total_duration_sec == pytest.approx(5.0)
    assert result.scenes[0].subtitles[0].text == "하나의 장면"
    assert result.scenes[0].subtitles[0].start_sec == pytest.approx(0.0)
    assert result.scenes[0].subtitles[0].end_sec == pytest.approx(5.0)


# 4. 사용자 지정 음성 전달

@pytest.mark.asyncio
async def test_generate_scene_audio_custom_voice(tmp_path):
    mock_tts = AsyncMock(
        return_value=make_audio(1, 2.0, tmp_path)
    )

    with patch(
        "app.services.audio_pipeline.generate_speech",
        mock_tts,
    ):
        await generate_scene_audio(
            scenes=[make_scene(1)],
            output_dir=tmp_path,
            voice="nova",
        )

    assert mock_tts.await_args.kwargs["voice"] == "nova"


# 5. 빈 장면 목록 거부

@pytest.mark.asyncio
async def test_generate_scene_audio_rejects_empty(tmp_path):
    with patch(
        "app.services.audio_pipeline.generate_speech",
        new_callable=AsyncMock,
    ) as mock_tts:
        with pytest.raises(
            ValueError,
            match="장면 목록이 비어 있습니다",
        ):
            await generate_scene_audio(
                scenes=[],
                output_dir=tmp_path,
            )

    mock_tts.assert_not_awaited()


# 6. 잘못된 장면 순서 거부

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "orders",
    [
        [2, 3],
        [1, 3],
        [1, 1],
        [0, 1],
    ],
)
async def test_generate_scene_audio_rejects_invalid_order(
    tmp_path,
    orders,
):
    scenes = [
        make_scene(order)
        for order in orders
    ]

    with patch(
        "app.services.audio_pipeline.generate_speech",
        new_callable=AsyncMock,
    ) as mock_tts:
        with pytest.raises(
            ValueError,
            match="장면 순서는 1부터 연속적으로 증가해야 합니다",
        ):
            await generate_scene_audio(
                scenes=scenes,
                output_dir=tmp_path,
            )

    mock_tts.assert_not_awaited()


# 7. TTS 실패 시 예외 전달

@pytest.mark.asyncio
async def test_generate_scene_audio_tts_failure(tmp_path):
    mock_tts = AsyncMock(
        side_effect=TTSGenerationError("TTS 생성 실패")
    )

    with patch(
        "app.services.audio_pipeline.generate_speech",
        mock_tts,
    ):
        with pytest.raises(
            TTSGenerationError,
            match="TTS 생성 실패",
        ):
            await generate_scene_audio(
                scenes=[make_scene(1)],
                output_dir=tmp_path,
            )

    assert mock_tts.await_count == 1


# 8. 잘못된 자막 입력 거부

@pytest.mark.asyncio
async def test_generate_scene_audio_invalid_caption(tmp_path):
    mock_tts = AsyncMock(
        return_value=make_audio(1, 3.0, tmp_path)
    )

    with patch(
        "app.services.audio_pipeline.generate_speech",
        mock_tts,
    ):
        with pytest.raises(
            ValueError,
            match="자막 텍스트가 비어 있습니다",
        ):
            await generate_scene_audio(
                scenes=[
                    make_scene(
                        order=1,
                        caption="   ",
                    )
                ],
                output_dir=tmp_path,
            )

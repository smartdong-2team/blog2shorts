import asyncio
import wave
import pytest
from pathlib import Path
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.tts import (
    generate_speech,
    get_wav_duration,
    TTSGenerationError,
)

from app.core.openai import get_openai_client
from app.schemas.audio import AudioAsset


def create_test_wav(
    path: Path,
    duration_sec: float = 2.0,
    sample_rate: int = 16000,
) -> None:
    """실제 재생 가능한 무음 WAV 파일을 생성한다."""

    frames = int(duration_sec * sample_rate)

    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(b"\x00\x00" * frames)



def mock_openai_client(duration_sec: float = 2.0):
    """OpenAI TTS 스트리밍 응답을 모킹한다."""

    client = MagicMock()
    client.close = AsyncMock()

    response = MagicMock()

    async def stream_to_file(path):
        create_test_wav(
            Path(path),
            duration_sec=duration_sec,
        )

    response.stream_to_file = AsyncMock(
        side_effect=stream_to_file
    )

    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(
        return_value=response
    )
    context_manager.__aexit__ = AsyncMock(
        return_value=None
    )

    client.audio.speech.with_streaming_response.create.return_value = (
        context_manager
    )

    return client



# 1. WAV 길이 측정 테스트
def test_get_wav_duration(tmp_path):
    wav_path = tmp_path / "test.wav"
    create_test_wav(wav_path, duration_sec=3.5)

    duration = get_wav_duration(wav_path)

    assert duration == pytest.approx(3.5)


# 2. 정상 음성 생성 테스트
@pytest.mark.asyncio
async def test_generate_speech_success(tmp_path):
    client = mock_openai_client(duration_sec=2.5)

    with patch(
        "app.services.tts.get_openai_client",
        return_value=client,
    ):
        result = await generate_speech(
            narration="안녕하세요. 테스트입니다.",
            output_dir=tmp_path,
        )

    assert isinstance(result, AudioAsset)
    assert result.duration_sec == pytest.approx(2.5)
    assert Path(result.path).exists()
    assert Path(result.path).suffix == ".wav"

    client.audio.speech.with_streaming_response.create.assert_called_once_with(
        model="tts-1",
        voice="alloy",
        input="안녕하세요. 테스트입니다.",
        response_format="wav",
    )

    client.close.assert_awaited_once()


# 3. 사용자 지정 음성 테스트
@pytest.mark.asyncio
async def test_generate_speech_custom_voice(tmp_path):
    client = mock_openai_client()

    with patch(
        "app.services.tts.get_openai_client",
        return_value=client,
    ):
        await generate_speech(
            narration="음성 선택 테스트입니다.",
            output_dir=tmp_path,
            voice="nova",
        )

    call_kwargs = (
        client.audio.speech.with_streaming_response.create.call_args.kwargs
    )

    assert call_kwargs["voice"] == "nova"


# 4. 빈 내레이션 테스트
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "narration",
    ["", "   ", "\n\t"],
)
async def test_generate_speech_rejects_empty_narration(
    tmp_path,
    narration,
):
    with pytest.raises(ValueError, match="내레이션이 비어 있습니다"):
        await generate_speech(
            narration=narration,
            output_dir=tmp_path,
        )

    assert list(tmp_path.iterdir()) == []


# 5. OpenAI API 실패 테스트
@pytest.mark.asyncio
async def test_generate_speech_api_failure(tmp_path):
    client = MagicMock()
    client.close = AsyncMock()

    client.audio.speech.with_streaming_response.create.side_effect = (
        RuntimeError("API unavailable")
    )

    with patch(
        "app.services.tts.get_openai_client",
        return_value=client,
    ):
        with pytest.raises(TTSGenerationError):
            await generate_speech(
                narration="API 실패 테스트",
                output_dir=tmp_path,
            )

    assert list(tmp_path.glob("*.wav")) == []
    client.close.assert_awaited_once()


# 6. 파일 생성 중 실패 및 정리 테스트
@pytest.mark.asyncio
async def test_generate_speech_cleans_up_partial_file(tmp_path):
    client = MagicMock()
    client.close = AsyncMock()

    response = MagicMock()

    async def failing_stream(path):
        Path(path).write_bytes(b"incomplete audio")
        raise RuntimeError("Download interrupted")

    response.stream_to_file.side_effect = failing_stream

    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=response)
    context_manager.__aexit__ = AsyncMock(return_value=None)

    client.audio.speech.with_streaming_response.create.return_value = (
        context_manager
    )

    with patch(
        "app.services.tts.get_openai_client",
        return_value=client,
    ):
        with pytest.raises(TTSGenerationError):
            await generate_speech(
                narration="파일 정리 테스트",
                output_dir=tmp_path,
            )

    assert list(tmp_path.glob("*.wav")) == []
    client.close.assert_awaited_once()

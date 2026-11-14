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
        speed=1.15,
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


# --------------------------------------------------
# Edge 음성
# --------------------------------------------------
@pytest.mark.asyncio
async def test_generate_speech_uses_edge_for_edge_voice(tmp_path):
    from app.services import tts

    saved = {}

    class FakeCommunicate:
        def __init__(self, text, voice, rate):
            saved.update(text=text, voice=voice, rate=rate)

        async def save(self, path):
            Path(path).write_bytes(b"mp3")

    async def fake_ffmpeg(command, timeout_sec, failure_message):
        create_test_wav(Path(command[-1]), duration_sec=1.5)

    fake_module = MagicMock(Communicate=FakeCommunicate)

    with (
        patch.dict("sys.modules", {"edge_tts": fake_module}),
        patch.object(tts, "run_ffmpeg", side_effect=fake_ffmpeg),
        patch.object(tts, "get_openai_client") as openai_client,
    ):
        result = await generate_speech("안녕하세요", tmp_path, voice="edge_injoon")

    assert saved == {"text": "안녕하세요", "voice": "ko-KR-InJoonNeural", "rate": "+15%"}
    assert result.duration_sec == pytest.approx(1.5)
    openai_client.assert_not_called()
    # 중간 MP3는 지운다
    assert list(tmp_path.glob("*.mp3")) == []


@pytest.mark.asyncio
async def test_generate_speech_maps_app_voice_to_openai(tmp_path):
    client = mock_openai_client()

    with patch("app.services.tts.get_openai_client", return_value=client):
        await generate_speech("안녕하세요", tmp_path, voice="calm_female")

    call_kwargs = client.audio.speech.with_streaming_response.create.call_args.kwargs
    assert call_kwargs["voice"] == "shimmer"


@pytest.mark.asyncio
async def test_edge_failure_raises_tts_error(tmp_path):
    from app.services import tts

    class BrokenCommunicate:
        def __init__(self, text, voice, rate):
            pass

        async def save(self, path):
            raise ConnectionError("막힘")

    with patch.dict("sys.modules", {"edge_tts": MagicMock(Communicate=BrokenCommunicate)}):
        with pytest.raises(TTSGenerationError):
            await tts.generate_speech("안녕하세요", tmp_path, voice="edge_sunhi")

    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------
# Supertonic 로컬 음성
# --------------------------------------------------
class FakeSupertonicTTS:
    loads = 0

    def __init__(self, model, auto_download):
        FakeSupertonicTTS.loads += 1
        self.model = model

    def get_voice_style(self, voice_name):
        return voice_name

    def synthesize(self, text, voice_style, lang, speed):
        self.last = (text, voice_style, lang, round(speed, 4))
        return "wav", [1.0]

    def save_audio(self, wav, output_path):
        create_test_wav(Path(output_path), duration_sec=1.0)


@pytest.mark.asyncio
async def test_generate_speech_uses_supertonic_and_loads_model_once(tmp_path):
    from app.services import tts

    FakeSupertonicTTS.loads = 0

    with (
        patch.dict("sys.modules", {"supertonic": MagicMock(TTS=FakeSupertonicTTS)}),
        patch.object(tts, "_supertonic_model", None),
        patch.object(tts, "get_openai_client") as openai_client,
    ):
        first = await generate_speech("안녕하세요", tmp_path, voice="supertonic_female")
        await generate_speech("다음 장면", tmp_path, voice="supertonic_male")
        model = tts._supertonic_model

    assert first.duration_sec == pytest.approx(1.0)
    assert FakeSupertonicTTS.loads == 1
    assert model.model == "supertonic-2"
    assert model.last == ("다음 장면", "M1", "ko", round(1.05 * 1.15, 4))
    openai_client.assert_not_called()


@pytest.mark.asyncio
async def test_supertonic_failure_raises_tts_error(tmp_path):
    from app.services import tts

    class BrokenTTS(FakeSupertonicTTS):
        def synthesize(self, text, voice_style, lang, speed):
            raise RuntimeError("모델 오류")

    with (
        patch.dict("sys.modules", {"supertonic": MagicMock(TTS=BrokenTTS)}),
        patch.object(tts, "_supertonic_model", None),
    ):
        with pytest.raises(TTSGenerationError):
            await generate_speech("안녕하세요", tmp_path, voice="supertonic_male")

    assert list(tmp_path.iterdir()) == []

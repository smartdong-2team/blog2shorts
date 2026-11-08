
import asyncio
import wave
from pathlib import Path
from uuid import uuid4
from app.core.config import get_settings
from app.core.openai import get_openai_client
from app.schemas.audio import AudioAsset

class TTSGenerationError(Exception):
    """음성 생성에 실패했을 때 발생하는 오류."""

# --------------------------------------------------
# 1. 내레이션을 WAV 파일로 생성
# --------------------------------------------------
async def generate_speech(
    narration: str,
    output_dir: Path,
    voice: str = "alloy",
) -> AudioAsset:
    """내레이션을 WAV 파일로 생성하고 실제 길이를 반환한다."""

    if not narration.strip():
        raise ValueError("내레이션이 비어 있습니다.")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{uuid4().hex}.wav"

    client = get_openai_client()

    try:
        async with client.audio.speech.with_streaming_response.create(
            model=get_settings().openai_tts_model,
            voice=voice,
            input=narration,
            response_format="wav",
        ) as response:
            await response.stream_to_file(output_path)

        duration_sec = await asyncio.to_thread(
            get_wav_duration,
            output_path,
        )

        return AudioAsset(
            path=str(output_path),
            duration_sec=duration_sec,
        )

    except Exception as exc:
        output_path.unlink(missing_ok=True)
        raise TTSGenerationError(
            "TTS 음성 생성에 실패했습니다."
        ) from exc

    finally:
        await client.close()


# --------------------------------------------------
# 2. WAV 파일의 재생 시간 계산
# --------------------------------------------------
def get_wav_duration(path: Path) -> float:
    """WAV 파일의 실제 PCM 데이터 크기로 재생 시간을 계산한다."""

    with wave.open(str(path), "rb") as audio:
        sample_rate = audio.getframerate()
        channels = audio.getnchannels()
        sample_width = audio.getsampwidth()

        if sample_rate <= 0:
            raise ValueError("유효하지 않은 샘플레이트입니다.")

        if channels <= 0 or sample_width <= 0:
            raise ValueError("유효하지 않은 WAV 형식입니다.")

        # 스트리밍 WAV의 헤더에 기록된 프레임 수를 신뢰하지 않고
        # 실제로 읽을 수 있는 PCM 데이터를 기준으로 계산한다.
        pcm_data = audio.readframes(audio.getnframes())

        bytes_per_frame = channels * sample_width
        actual_frames = len(pcm_data) // bytes_per_frame

        duration_sec = actual_frames / sample_rate

        if not 0 < duration_sec <= 300:
            raise ValueError(
                f"비정상적인 음성 길이: {duration_sec:.2f}초"
            )

        return duration_sec
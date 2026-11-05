
import asyncio
import wave
from pathlib import Path
from uuid import uuid4

from openai import AsyncOpenAI

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

    client = AsyncOpenAI()

    try:
        async with client.audio.speech.with_streaming_response.create(
            model="tts-1",
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
    """WAV 파일의 실제 재생 시간을 초 단위로 계산한다."""

    with wave.open(str(path), "rb") as audio:
        frames = audio.getnframes()
        sample_rate = audio.getframerate()

        if sample_rate <= 0:
            raise ValueError("유효하지 않은 샘플레이트입니다.")

        return frames / sample_rate

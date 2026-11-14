
import asyncio
import threading
import wave
from pathlib import Path
from uuid import uuid4
from app.core.config import get_settings
from app.core.openai import get_openai_client
from app.schemas.audio import AudioAsset
from app.services.video_render import FFMPEG_BIN, run_ffmpeg

# 화면의 목소리 선택값 → OpenAI TTS 음성
OPENAI_VOICES = {
    "calm_female": "shimmer",
    "bright_female": "nova",
    "clear_male": "echo",
    "low_male": "onyx",
}

# 화면의 목소리 선택값 → Microsoft Edge 음성 (edge-tts, 키 없이 무료)
# 공식 API가 아니라 Edge '소리 내어 읽기' 서비스를 쓰므로 막히면 OpenAI 음성으로 바꿔야 한다
EDGE_VOICES = {
    "edge_injoon": "ko-KR-InJoonNeural",
    "edge_sunhi": "ko-KR-SunHiNeural",
    "edge_hyunsu": "ko-KR-HyunsuMultilingualNeural",
}

# 화면의 목소리 선택값 → Supertonic 로컬 음성 (키·비용 없음, 처음 쓸 때 모델을 내려받음)
# 모델: OpenRAIL-M. 공식 저장소는 보관(개발 종료) 상태다
SUPERTONIC_VOICES = {
    "supertonic_male": "M1",
    "supertonic_female": "F1",
}

DEFAULT_VOICE = "edge_injoon"

# Supertonic의 기본 speed 값. 설정 속도(tts_speed)를 여기에 곱한다
SUPERTONIC_BASE_SPEED = 1.05

_supertonic_model = None
_supertonic_lock = threading.Lock()


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
    """내레이션을 WAV 파일로 생성하고 실제 길이를 반환한다.

    voice는 화면의 선택값(edge_injoon, calm_female 등)이나 OpenAI 음성 이름(alloy 등)이다.
    """

    if not narration.strip():
        raise ValueError("내레이션이 비어 있습니다.")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{uuid4().hex}.wav"

    if voice in EDGE_VOICES:
        return await generate_edge_speech(narration, output_path, EDGE_VOICES[voice])

    if voice in SUPERTONIC_VOICES:
        return await generate_supertonic_speech(narration, output_path, SUPERTONIC_VOICES[voice])

    voice = OPENAI_VOICES.get(voice, voice)
    client = get_openai_client()

    try:
        async with client.audio.speech.with_streaming_response.create(
            model=get_settings().openai_tts_model,
            voice=voice,
            input=narration,
            response_format="wav",
            speed=get_settings().tts_speed,
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


async def generate_edge_speech(
    narration: str,
    output_path: Path,
    edge_voice: str,
) -> AudioAsset:
    """Edge 음성으로 MP3를 받아 다른 음성과 같은 WAV(24kHz 모노)로 바꾼다."""

    import edge_tts

    mp3_path = output_path.with_suffix(".mp3")

    try:
        rate = f"{round((get_settings().tts_speed - 1) * 100):+d}%"
        await edge_tts.Communicate(narration, edge_voice, rate=rate).save(str(mp3_path))
        await run_ffmpeg(
            [
                FFMPEG_BIN, "-y", "-i", str(mp3_path),
                "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le",
                str(output_path),
            ],
            timeout_sec=60,
            failure_message="Edge 음성 변환 실패",
        )
        duration_sec = await asyncio.to_thread(get_wav_duration, output_path)
        return AudioAsset(path=str(output_path), duration_sec=duration_sec)

    except Exception as exc:
        output_path.unlink(missing_ok=True)
        raise TTSGenerationError("Edge 음성 생성에 실패했습니다.") from exc

    finally:
        mp3_path.unlink(missing_ok=True)


def _synthesize_supertonic(narration: str, output_path: Path, style_name: str) -> None:
    """Supertonic으로 WAV를 만든다. 모델은 한 번만 불러 쓰고, 동시에 한 장면씩만 합성한다."""

    global _supertonic_model

    with _supertonic_lock:
        if _supertonic_model is None:
            from supertonic import TTS

            _supertonic_model = TTS(model=get_settings().supertonic_model, auto_download=True)

        style = _supertonic_model.get_voice_style(voice_name=style_name)
        wav, _ = _supertonic_model.synthesize(
            narration,
            voice_style=style,
            lang="ko",
            speed=SUPERTONIC_BASE_SPEED * get_settings().tts_speed,
        )
        _supertonic_model.save_audio(wav, str(output_path))


async def generate_supertonic_speech(
    narration: str,
    output_path: Path,
    style_name: str,
) -> AudioAsset:
    """Supertonic 로컬 모델로 WAV(44.1kHz 모노)를 만든다."""

    try:
        await asyncio.to_thread(_synthesize_supertonic, narration, output_path, style_name)
        duration_sec = await asyncio.to_thread(get_wav_duration, output_path)
        return AudioAsset(path=str(output_path), duration_sec=duration_sec)

    except Exception as exc:
        output_path.unlink(missing_ok=True)
        raise TTSGenerationError("Supertonic 음성 생성에 실패했습니다.") from exc


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
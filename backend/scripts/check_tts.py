
import asyncio
import wave
from pathlib import Path

from app.services.tts import generate_speech


async def main():
    output_dir = Path("output/tts-check")

    print("OpenAI TTS 생성 시작...")

    audio = await generate_speech(
        narration=(
            "안녕하세요. 블로그 글을 짧은 영상으로 "
            "변환하는 음성 생성 테스트입니다."
        ),
        output_dir=output_dir,
        voice="alloy",
    )

    audio_path = Path(audio.path)

    with wave.open(str(audio_path), "rb") as wav:
        sample_rate = wav.getframerate()
        channels = wav.getnchannels()
        frames = wav.getnframes()

    print("\nTTS 생성 성공!")
    print(f"파일: {audio_path.resolve()}")
    print(f"크기: {audio_path.stat().st_size:,} bytes")
    print(f"길이: {audio.duration_sec:.2f}초")
    print(f"샘플레이트: {sample_rate} Hz")
    print(f"채널: {channels}")
    print(f"프레임: {frames}")


if __name__ == "__main__":
    asyncio.run(main())

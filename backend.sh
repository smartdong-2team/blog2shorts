#!/usr/bin/env bash
# 백엔드 개발 서버 실행: ./backend.sh
# 포트 변경: PORT=8001 ./backend.sh
set -euo pipefail

cd "$(dirname "$0")/backend"

# 1. uv 설치 확인
if ! command -v uv >/dev/null 2>&1; then
  echo "uv가 필요합니다: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

# 2. 환경변수 파일 생성
if [ ! -f .env ]; then
  cp .env.example .env
  echo "backend/.env 를 .env.example 에서 생성했습니다."
fi

# 3. FFmpeg drawtext 지원 여부 확인
supports_drawtext() {
  "$1" -hide_banner -filters 2>/dev/null |
    grep 'drawtext' >/dev/null
}

FFMPEG_BIN=""

# 환경변수로 FFmpeg 경로를 직접 지정한 경우
if [ -n "${FFMPEG_BIN_OVERRIDE:-}" ]; then
  if supports_drawtext "$FFMPEG_BIN_OVERRIDE"; then
    FFMPEG_BIN="$FFMPEG_BIN_OVERRIDE"
  else
    echo "지정한 FFmpeg에서 drawtext를 사용할 수 없습니다: $FFMPEG_BIN_OVERRIDE" >&2
    exit 1
  fi
fi

# PATH에 등록된 FFmpeg 확인
if [ -z "$FFMPEG_BIN" ] && command -v ffmpeg >/dev/null 2>&1; then
  CANDIDATE="$(command -v ffmpeg)"

  if supports_drawtext "$CANDIDATE"; then
    FFMPEG_BIN="$CANDIDATE"
  fi
fi

# macOS Homebrew ffmpeg-full 확인
if [ -z "$FFMPEG_BIN" ] && command -v brew >/dev/null 2>&1; then
  BREW_FULL_PREFIX="$(brew --prefix ffmpeg-full 2>/dev/null || true)"

  if [ -n "$BREW_FULL_PREFIX" ]; then
    CANDIDATE="$BREW_FULL_PREFIX/bin/ffmpeg"

    if [ -x "$CANDIDATE" ] && supports_drawtext "$CANDIDATE"; then
      FFMPEG_BIN="$CANDIDATE"
    fi
  fi
fi

# 사용 가능한 FFmpeg가 없으면 실행 중단
if [ -z "$FFMPEG_BIN" ]; then
  echo "오류: drawtext 필터를 지원하는 FFmpeg를 찾지 못했습니다." >&2
  echo "macOS에서는 brew install ffmpeg-full 을 확인해 주세요." >&2
  exit 1
fi

export FFMPEG_BIN
echo "FFmpeg 확인 완료: $FFMPEG_BIN"

# 4. Python 의존성 설치
uv sync

# 5. 백엔드 서버 실행
exec uv run uvicorn app.main:app --reload --port "${PORT:-8000}"
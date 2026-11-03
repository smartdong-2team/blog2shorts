#!/usr/bin/env bash
# 백엔드 개발 서버 실행: ./backend.sh  (포트 변경: PORT=8001 ./backend.sh)
set -euo pipefail

cd "$(dirname "$0")/backend"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv가 필요합니다: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "backend/.env 를 .env.example 에서 생성했습니다."
fi

uv sync
exec uv run uvicorn app.main:app --reload --port "${PORT:-8000}"

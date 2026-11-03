#!/usr/bin/env bash
# 프론트엔드 개발 서버 실행: ./frontend.sh  (http://localhost:5173)
set -euo pipefail

cd "$(dirname "$0")/frontend"

if ! command -v npm >/dev/null 2>&1; then
  echo "Node.js(npm)가 필요합니다: https://nodejs.org/" >&2
  exit 1
fi

if [ ! -f .env.local ]; then
  cp .env.example .env.local
  echo "frontend/.env.local 을 .env.example 에서 생성했습니다."
fi

# package-lock.json 기준으로 의존성이 바뀌었을 때만 설치
if [ ! -d node_modules ] || [ package-lock.json -nt node_modules/.package-lock.json ]; then
  npm install
fi

exec npm run dev -- --port "${PORT:-5173}"

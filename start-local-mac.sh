#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [ ! -f "$ROOT_DIR/.env" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "Created .env from .env.example. Add API keys there for video processing."
fi

cd "$ROOT_DIR"
docker compose up -d postgres redis

export DATABASE_URL="postgresql+asyncpg://supoclip:supoclip_password@127.0.0.1:55432/supoclip"
export REDIS_HOST="127.0.0.1"
export REDIS_PORT="6379"
export PYTHONPATH="."
if [ -x "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg" ]; then
  export FFMPEG_BINARY="/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
  export FFPROBE_BINARY="/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
fi

set -a
# shellcheck disable=SC1091
source "$ROOT_DIR/.env"
set +a

cleanup() {
  jobs -p | xargs -r kill
}
trap cleanup EXIT INT TERM

(
  cd "$BACKEND_DIR"
  DATABASE_URL="$DATABASE_URL" REDIS_HOST="$REDIS_HOST" REDIS_PORT="$REDIS_PORT" PYTHONPATH="$PYTHONPATH" FFMPEG_BINARY="${FFMPEG_BINARY:-ffmpeg}" FFPROBE_BINARY="${FFPROBE_BINARY:-ffprobe}" \
    uv run uvicorn src.main_refactored:app --host 127.0.0.1 --port 8000
) &

(
  cd "$BACKEND_DIR"
  DATABASE_URL="$DATABASE_URL" REDIS_HOST="$REDIS_HOST" REDIS_PORT="$REDIS_PORT" PYTHONPATH="$PYTHONPATH" FFMPEG_BINARY="${FFMPEG_BINARY:-ffmpeg}" FFPROBE_BINARY="${FFPROBE_BINARY:-ffprobe}" \
    uv run arq src.workers.tasks.WorkerSettings
) &

(
  cd "$FRONTEND_DIR"
  DATABASE_URL="postgresql://supoclip:supoclip_password@127.0.0.1:55432/supoclip" \
  BACKEND_INTERNAL_URL="http://127.0.0.1:8000" \
  NEXT_PUBLIC_API_URL="http://127.0.0.1:8000" \
  NEXT_PUBLIC_APP_URL="http://localhost:3107" \
  NEXT_PUBLIC_SELF_HOST="true" \
  BETTER_AUTH_URL="http://localhost:3107" \
    corepack pnpm dev
) &

echo "SupoClip is starting:"
echo "  Frontend: http://localhost:3107"
echo "  Backend:  http://127.0.0.1:8000"
echo "Press Ctrl+C to stop local app processes."

wait

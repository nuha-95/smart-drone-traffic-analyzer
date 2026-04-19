#!/bin/bash

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_NAME="drone-env"

echo "Starting Drone Traffic Analyzer..."

cleanup() {
  if [ -n "${BACKEND_PID:-}" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

cd "$ROOT_DIR"
if [ "${CONDA_DEFAULT_ENV:-}" = "$ENV_NAME" ]; then
  python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
else
  conda run -n "$ENV_NAME" --no-capture-output python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
fi
BACKEND_PID=$!

cd "$ROOT_DIR/frontend"
npm start

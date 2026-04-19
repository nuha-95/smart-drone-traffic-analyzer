#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_NAME="drone-env"

echo "============================================"
echo " Smart Drone Traffic Analyzer - Setup"
echo "============================================"
echo

if ! command -v conda >/dev/null 2>&1; then
  echo "Error: conda is required but was not found."
  echo "Install Miniconda or Anaconda and run this script again."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "Error: npm is required but was not found."
  echo "Install Node.js 18+ and run this script again."
  exit 1
fi

echo "Using conda: $(command -v conda)"
echo "Using npm: $(command -v npm)"
echo

if conda env list | awk '{print $1}' | grep -Fxq "$ENV_NAME"; then
  echo "Conda environment '$ENV_NAME' already exists"
else
  echo "Creating conda environment '$ENV_NAME' ..."
  conda create -n "$ENV_NAME" python=3.11 -y
fi

echo "Installing backend dependencies ..."
conda run -n "$ENV_NAME" python -m pip install --upgrade pip
conda run -n "$ENV_NAME" python -m pip install -r "$ROOT_DIR/requirements.txt"

echo "Installing frontend dependencies ..."
cd "$ROOT_DIR/frontend"
npm install

cd "$ROOT_DIR"
mkdir -p storage/uploads storage/outputs storage/reports

echo
echo "Setup complete."
echo
echo "Next steps:"
echo "1. Start the app with: ./start.sh"
echo "2. Or run with Docker: docker compose up --build"

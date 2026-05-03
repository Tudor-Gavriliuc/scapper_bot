#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-$HOME/promo-scraper-bot}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[INFO] Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-venv python3-pip unzip

mkdir -p "$APP_DIR"
cd "$APP_DIR"

if [ ! -d ".venv" ]; then
  echo "[INFO] Creating virtual environment..."
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate

echo "[INFO] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[INFO] Installing Playwright Chromium..."
python -m playwright install chromium

echo "[INFO] Ensuring data directory..."
mkdir -p data

echo "[INFO] Setup complete."
echo "[NEXT] Edit .env and run:"
echo "       source .venv/bin/activate && python run_daily_posting.py"

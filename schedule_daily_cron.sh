#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-$HOME/promo-scraper-bot}"
PYTHON_PATH="$APP_DIR/.venv/bin/python"
RUN_FILE="$APP_DIR/run_daily_posting.py"
LOG_FILE="$APP_DIR/daily.log"
CRON_EXPR="${2:-0 9 * * *}"

if [ ! -f "$RUN_FILE" ]; then
  echo "[ERROR] Missing run file: $RUN_FILE"
  exit 1
fi

if [ ! -x "$PYTHON_PATH" ]; then
  echo "[ERROR] Missing python in venv: $PYTHON_PATH"
  exit 1
fi

CRON_LINE="$CRON_EXPR cd $APP_DIR && $PYTHON_PATH $RUN_FILE >> $LOG_FILE 2>&1"

( crontab -l 2>/dev/null | grep -v "run_daily_posting.py"; echo "$CRON_LINE" ) | crontab -

echo "[INFO] Cron installed:"
crontab -l | grep "run_daily_posting.py"

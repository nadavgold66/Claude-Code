#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Single launcher for the Israeli News Aggregator + Telegram Bot
# Usage:  ./start.sh
# Stop:   Ctrl+C  (both processes shut down automatically)
# ──────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Pre-flight checks ───────────────────────────────────────
if ! command -v node &>/dev/null; then
    echo "Error: Node.js is not installed. See https://nodejs.org"
    exit 1
fi

PYTHON=""
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "Error: Python is not installed. See https://python.org"
    exit 1
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "Error: TELEGRAM_BOT_TOKEN is not set."
    echo "Run:  export TELEGRAM_BOT_TOKEN=\"your-token-here\""
    exit 1
fi

if [ ! -d "$SCRIPT_DIR/node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm --prefix "$SCRIPT_DIR" install
fi

# ── Cleanup on exit ──────────────────────────────────────────
cleanup() {
    echo ""
    echo "Shutting down..."
    # Kill the aggregator background process and all children
    if [ -n "$AGG_PID" ] && kill -0 "$AGG_PID" 2>/dev/null; then
        kill "$AGG_PID" 2>/dev/null
        wait "$AGG_PID" 2>/dev/null
    fi
    exit 0
}
trap cleanup INT TERM

# ── Start the news aggregator in the background ─────────────
echo "Starting news aggregator..."
npm --prefix "$SCRIPT_DIR" run dev &
AGG_PID=$!

# Wait for the aggregator to be ready
echo "Waiting for aggregator to start on http://localhost:3000 ..."
for i in $(seq 1 30); do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo "Aggregator is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "Error: Aggregator did not start in time."
        cleanup
    fi
    sleep 1
done

# ── Start the Telegram bot in the foreground ─────────────────
echo "Starting Telegram bot..."
$PYTHON "$SCRIPT_DIR/telegram-bot/bot.py"

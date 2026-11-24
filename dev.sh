#!/usr/bin/env bash
# Starts all AgroPilot services for local development.
# Usage: ./dev.sh [stop]
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
PIDS_FILE="$REPO/.dev-pids"

stop_all() {
  if [[ ! -f "$PIDS_FILE" ]]; then
    echo "No running dev session found."
    return
  fi
  echo "Stopping AgroPilot services..."
  while IFS= read -r pid; do
    kill "$pid" 2>/dev/null && echo "  killed $pid" || true
  done < "$PIDS_FILE"
  rm -f "$PIDS_FILE"
  echo "Done."
}

wait_healthy() {
  local name=$1 url=$2
  local attempts=0
  printf "  Waiting for %-20s" "$name..."
  until curl -sf "$url" > /dev/null 2>&1; do
    sleep 0.5
    attempts=$((attempts + 1))
    if [[ $attempts -ge 30 ]]; then
      echo " TIMEOUT"
      echo "  Check logs: $REPO/tmp/logs/${name}.log"
      return 1
    fi
  done
  echo " up"
}

if [[ "${1:-}" == "stop" ]]; then
  stop_all
  exit 0
fi

if [[ -f "$PIDS_FILE" ]]; then
  echo "Dev session already running. Run './dev.sh stop' first."
  exit 1
fi

mkdir -p "$REPO/tmp/logs"
> "$PIDS_FILE"

echo "Starting AgroPilot services..."

# --- Registry (18000) ---
cd "$REPO/services/registry-service"
uv run --locked uvicorn main:app --host 127.0.0.1 --port 18000 --no-access-log \
  > "$REPO/tmp/logs/registry.log" 2>&1 &
echo $! >> "$PIDS_FILE"

# --- Weather (18001) ---
cd "$REPO/services/weather-service"
uv run uvicorn main:app --host 127.0.0.1 --port 18001 --no-access-log \
  > "$REPO/tmp/logs/weather.log" 2>&1 &
echo $! >> "$PIDS_FILE"

# --- Planner (18002) ---
cd "$REPO/services/planner-service"
uv run uvicorn main:app --factory --host 127.0.0.1 --port 18002 --no-access-log \
  > "$REPO/tmp/logs/planner.log" 2>&1 &
echo $! >> "$PIDS_FILE"

# --- Frontend (3000) ---
cd "$REPO/services/frontend"
npm run dev > "$REPO/tmp/logs/frontend.log" 2>&1 &
echo $! >> "$PIDS_FILE"

# --- Health checks ---
wait_healthy "registry"  "http://127.0.0.1:18000/health"
wait_healthy "weather"   "http://127.0.0.1:18001/health"
wait_healthy "planner"   "http://127.0.0.1:18002/health"
wait_healthy "frontend"  "http://localhost:3000/"

echo ""
echo "AgroPilot is running:"
echo "  Frontend  → http://localhost:3000"
echo "  Registry  → http://127.0.0.1:18000"
echo "  Weather   → http://127.0.0.1:18001"
echo "  Planner   → http://127.0.0.1:18002"
echo ""
echo "Logs: $REPO/tmp/logs/"
echo "Stop: ./dev.sh stop"

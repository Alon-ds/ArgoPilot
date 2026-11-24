#!/usr/bin/env bash
# Starts, stops and inspects the whole AgroPilot stack for local development.
# Usage: ./dev.sh [start|stop|status]
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
LOGS="$REPO/tmp/logs"

REGISTRY_PORT="${REGISTRY_PORT:-8000}"
WEATHER_PORT="${WEATHER_PORT:-8001}"
PLANNER_PORT="${PLANNER_PORT:-8002}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
ALL_PORTS=("$REGISTRY_PORT" "$WEATHER_PORT" "$PLANNER_PORT" "$FRONTEND_PORT")

listeners() { lsof -ti "tcp:$1" -sTCP:LISTEN 2>/dev/null || true; }

status() {
  printf '%-10s %-6s %s\n' SERVICE PORT STATE
  for entry in "registry:$REGISTRY_PORT" "weather:$WEATHER_PORT" "planner:$PLANNER_PORT" "frontend:$FRONTEND_PORT"; do
    local name=${entry%%:*} port=${entry##*:} pids state
    pids=$(listeners "$port" | tr '\n' ' ')
    if [[ -n "${pids// /}" ]]; then state="up (pid ${pids% })"; else state="down"; fi
    printf '%-10s %-6s %s\n' "$name" "$port" "$state"
  done
}

stop_all() {
  local stopped=0
  for port in "${ALL_PORTS[@]}"; do
    for pid in $(listeners "$port"); do
      kill "$pid" 2>/dev/null && echo "  stopped pid $pid on port $port" && stopped=1
    done
  done
  [[ $stopped -eq 1 ]] || echo "  nothing was listening on ${ALL_PORTS[*]}"
}

# Fails rather than starting a second copy beside a service that is already up:
# two stacks on different ports silently disagree about which database they wrote to.
require_free_ports() {
  local busy=()
  for port in "${ALL_PORTS[@]}"; do
    [[ -n "$(listeners "$port")" ]] && busy+=("$port")
  done
  if [[ ${#busy[@]} -gt 0 ]]; then
    echo "Ports already in use: ${busy[*]}"
    echo "Run './dev.sh stop' first, or './dev.sh status' to see what is running."
    exit 1
  fi
}

wait_healthy() {
  local name=$1 url=$2 attempts=0
  printf '  %-9s' "$name"
  until curl -sf "$url" >/dev/null 2>&1; do
    sleep 0.5
    attempts=$((attempts + 1))
    if [[ $attempts -ge 60 ]]; then
      echo "TIMEOUT - see $LOGS/$name.log"
      return 1
    fi
  done
  echo "up"
}

start_all() {
  require_free_ports
  mkdir -p "$LOGS"
  echo "Starting AgroPilot..."

  (cd "$REPO/services/registry-service" && exec uv run uvicorn main:app \
    --host 127.0.0.1 --port "$REGISTRY_PORT" --no-access-log) >"$LOGS/registry.log" 2>&1 &

  (cd "$REPO/services/weather-service" && exec uv run uvicorn main:app \
    --host 127.0.0.1 --port "$WEATHER_PORT" --no-access-log) >"$LOGS/weather.log" 2>&1 &

  # The planner calls the other two. Exporting their URLs (pydantic-settings reads the
  # environment before .env) keeps it pointed at the ports this script actually started,
  # instead of whatever its .env was last set to.
  (cd "$REPO/services/planner-service" \
    && REGISTRY_URL="http://127.0.0.1:$REGISTRY_PORT" \
       WEATHER_URL="http://127.0.0.1:$WEATHER_PORT" \
       exec uv run uvicorn main:app --factory \
    --host 127.0.0.1 --port "$PLANNER_PORT" --no-access-log) >"$LOGS/planner.log" 2>&1 &

  # Exported URLs beat .env.local (Next.js reads process.env first), so the ports chosen
  # here are the ports the frontend calls, with no second place to keep them in sync.
  (cd "$REPO/services/frontend" \
    && REGISTRY_URL="http://127.0.0.1:$REGISTRY_PORT" \
       WEATHER_URL="http://127.0.0.1:$WEATHER_PORT" \
       PLANNER_URL="http://127.0.0.1:$PLANNER_PORT" \
       exec npm run dev -- --port "$FRONTEND_PORT") >"$LOGS/frontend.log" 2>&1 &

  wait_healthy registry "http://127.0.0.1:$REGISTRY_PORT/health"
  wait_healthy weather  "http://127.0.0.1:$WEATHER_PORT/health"
  wait_healthy planner  "http://127.0.0.1:$PLANNER_PORT/health"
  wait_healthy frontend "http://127.0.0.1:$FRONTEND_PORT/"

  cat <<EOF

AgroPilot is running:
  Frontend  http://localhost:$FRONTEND_PORT
  Registry  http://127.0.0.1:$REGISTRY_PORT/docs
  Weather   http://127.0.0.1:$WEATHER_PORT/docs
  Planner   http://127.0.0.1:$PLANNER_PORT/docs

Logs: $LOGS/
Stop: ./dev.sh stop
EOF
}

case "${1:-start}" in
  start) start_all ;;
  stop) stop_all ;;
  status) status ;;
  *) echo "Usage: ./dev.sh [start|stop|status]" >&2; exit 2 ;;
esac

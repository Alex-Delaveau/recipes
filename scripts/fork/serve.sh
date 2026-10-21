#!/usr/bin/env bash
# Run the app for manual or headless checks: production build of vue3 + Django dev server.
# Usage: scripts/fork/serve.sh start|stop|restart|status [--no-build] [--port 8000]
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p .fork
PID_FILE=.fork/server.pid
LOG_FILE=.fork/server.log
PORT=8000
BUILD=1
CMD=${1:-status}; shift || true
while [ $# -gt 0 ]; do
  case $1 in
    --no-build) BUILD=0 ;;
    --port) PORT=$2; shift ;;
  esac
  shift
done
export DJANGO_SETTINGS_MODULE=recipes.settings DEBUG=1 ALLOWED_HOSTS='*'

running() { [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; }

start() {
  if running; then echo "[serve] already running (pid $(cat $PID_FILE)) on :$PORT"; return; fi
  if [ "$BUILD" = 1 ]; then
    echo "[serve] building frontend"
    YARN="yarn"; command -v yarn >/dev/null 2>&1 || YARN="npx --yes yarn"
    (cd vue3 && $YARN build >/dev/null 2>&1)
  fi
  # the branch may bring new migrations (kitchen/): the dev database follows
  .venv/bin/python manage.py migrate --noinput -v0 >/dev/null 2>&1 || echo "[serve] WARN migrate failed"
  setsid .venv/bin/python manage.py runserver "127.0.0.1:$PORT" --noreload >"$LOG_FILE" 2>&1 < /dev/null &
  echo $! > "$PID_FILE"
  for _ in $(seq 1 60); do
    CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/accounts/login/" || true)
    if [ "$CODE" -ge 200 ] 2>/dev/null && [ "$CODE" -lt 500 ]; then
      echo "[serve] up on http://127.0.0.1:$PORT (demo / demo)"; return
    fi
    sleep 1
  done
  echo "[serve] ERROR server did not start, see $LOG_FILE"; tail -20 "$LOG_FILE"; exit 1
}

stop() {
  if running; then kill "$(cat "$PID_FILE")" && echo "[serve] stopped"; else echo "[serve] not running"; fi
  rm -f "$PID_FILE"
}

case $CMD in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) running && echo "[serve] running (pid $(cat $PID_FILE))" || echo "[serve] not running" ;;
  *) echo "usage: $0 start|stop|restart|status [--no-build] [--port N]"; exit 2 ;;
esac

#!/bin/sh
set -e

# Ensure data directories exist and are owned by appuser.
# The container starts as root so we can chown the volume mount target,
# then drop to appuser via gosu for the actual application processes.
DATA_DIR="${DATA_DIR:-/data}"
BENCH_DIR="${BENCHMARK_RESULTS_DIR:-/data/benchmark_results}"
mkdir -p "${DATA_DIR}/logs" "${BENCH_DIR}"
chown -R appuser:appuser "${DATA_DIR}"

# Start the backend server (run from /app so 'backend.*' imports resolve)
cd /app
gosu appuser python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready (up to 30s)
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
        break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "Backend process exited unexpectedly" >&2
        wait "$BACKEND_PID"
        exit 1
    fi
    sleep 1
done

# Start the frontend server
cd /app/web
gosu appuser node server.js &
FRONTEND_PID=$!

# Forward termination signals to both children
_cleanup() {
    kill -TERM "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap _cleanup TERM INT

wait "$FRONTEND_PID"
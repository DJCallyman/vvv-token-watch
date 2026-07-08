#!/bin/sh
set -e

# Ensure data directories exist
mkdir -p "${DATA_DIR:-/app/data}/logs" "${BENCHMARK_RESULTS_DIR:-/app/data/benchmark_results}"

# Start the backend server (run from /app so 'backend.*' imports resolve)
cd /app
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
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
node server.js &
FRONTEND_PID=$!

# Forward termination signals to both children
_cleanup() {
    kill -TERM "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap _cleanup TERM INT

wait "$FRONTEND_PID"
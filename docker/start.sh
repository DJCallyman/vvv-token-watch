#!/bin/sh
set -e

# Ensure data directories exist
mkdir -p /data/logs

# Start the backend server (run from /app so 'backend.*' imports resolve)
cd /app
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# Wait for backend to be ready
sleep 2

# Start the frontend server
cd /app/web
node server.js
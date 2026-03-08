#!/usr/bin/env bash
# dev.sh — local development launcher
# Starts: PostgreSQL (Docker), FastAPI backend (uvicorn --reload), Next.js (npm run dev)
# Stop everything with Ctrl+C
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# ── colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[dev]${NC} $*"; }
success() { echo -e "${GREEN}[dev]${NC} $*"; }
warn()    { echo -e "${YELLOW}[dev]${NC} $*"; }
error()   { echo -e "${RED}[dev]${NC} $*"; exit 1; }

# ── pre-flight checks ─────────────────────────────────────────────────────────
command -v docker  >/dev/null 2>&1 || error "Docker is required but not installed."
command -v uvicorn >/dev/null 2>&1 || error "uvicorn not found. Run: pip install -r backend/requirements.txt"
command -v npm     >/dev/null 2>&1 || error "npm is required but not installed."

# ── create .env if missing (values come from your Unraid template) ─────────────
if [[ ! -f ".env" ]]; then
    warn ".env not found. Enter the values from your Unraid Docker template."
    echo ""

    read -rp "  VENICE_ADMIN_KEY      : " _admin_key
    [[ -n "$_admin_key" ]] || error "VENICE_ADMIN_KEY is required."

    read -rp "  COINGECKO_API_KEY     (leave blank if none): " _cg_key
    read -rp "  COINGECKO_HOLDING_AMOUNT [2750]: " _vvv_hold
    _vvv_hold="${_vvv_hold:-2750}"
    read -rp "  DIEM_HOLDING_AMOUNT   [0]: " _diem_hold
    _diem_hold="${_diem_hold:-0}"

    cat > .env <<EOF
# Created by dev.sh — mirrors your Unraid template values
VENICE_ADMIN_KEY=${_admin_key}
COINGECKO_API_KEY=${_cg_key}
COINGECKO_HOLDING_AMOUNT=${_vvv_hold}
DIEM_HOLDING_AMOUNT=${_diem_hold}
COINGECKO_TOKEN_ID=venice-token
DIEM_TOKEN_ID=diem
COINGECKO_CURRENCIES=usd,aud
LOG_LEVEL=INFO
EOF
    success ".env created."
    echo ""
fi

VENICE_KEY=$(grep -E '^VENICE_ADMIN_KEY=' .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" | tr -d '[:space:]')
[[ -n "$VENICE_KEY" ]] || error "VENICE_ADMIN_KEY is empty in .env — edit .env and add it."

# ── local overrides (don't clobber .env, just set in environment) ─────────────
export DATABASE_URL="postgresql://vvvwatch:vvvwatch@localhost:5433/vvvwatch"
export LOG_FILE_PATH="$REPO_ROOT/data/logs/app.log"
export DATA_DIR="$REPO_ROOT/data"
export BACKEND_URL="http://localhost:8000"
mkdir -p "$REPO_ROOT/data/logs"

# Note: Python 3.13 + OpenSSL 3.x may show "unsupported hash type blake2b/blake2s" errors# These are harmless - Python falls back to built-in implementations. The app works fine.

# ── cleanup on exit ───────────────────────────────────────────────────────────
PIDS=()
cleanup() {
    echo ""
    info "Shutting down..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    docker compose -f docker-compose.dev.yml down --timeout 5 2>/dev/null || true
    success "Done."
}
trap cleanup EXIT INT TERM

# ── clear any leftover processes on our ports ────────────────────────────────
for port in 8000 3000; do
    pids=$(lsof -ti :$port 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        warn "Port $port in use — killing leftover process(es): $(echo $pids | tr '\n' ' ')"
        kill -9 $pids 2>/dev/null || true
        # wait until port is actually released
        for i in $(seq 1 10); do
            lsof -ti :$port >/dev/null 2>&1 || break
            sleep 0.5
        done
    fi
done

# ── 1. start postgres ─────────────────────────────────────────────────────────
info "Starting PostgreSQL (port 5433)..."
docker compose -f docker-compose.dev.yml up -d postgres

info "Waiting for PostgreSQL to be ready..."
for i in $(seq 1 30); do
    if docker compose -f docker-compose.dev.yml exec -T postgres \
        pg_isready -U vvvwatch -d vvvwatch >/dev/null 2>&1; then
        success "PostgreSQL is ready."
        break
    fi
    [[ $i -eq 30 ]] && error "PostgreSQL did not become ready in time."
    sleep 1
done

# ── 2. install frontend deps if needed ───────────────────────────────────────
if [[ ! -d "web/node_modules" ]]; then
    info "Installing frontend dependencies..."
    (cd web && npm install)
fi

# ── 3. start backend ─────────────────────────────────────────────────────────
info "Starting FastAPI backend on http://localhost:8000 (hot-reload enabled)..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
PIDS+=($!)

# give the backend a moment to initialise
sleep 2

# ── 4. start frontend ─────────────────────────────────────────────────────────
info "Starting Next.js frontend on http://localhost:3000 ..."
(cd web && npm run dev) &
PIDS+=($!)

success "All services running."
echo ""
echo "  Frontend : http://localhost:3000"
echo "  Backend  : http://localhost:8000"
echo "  API docs : http://localhost:8000/docs"
echo "  Logs     : $LOG_FILE_PATH"
echo ""
echo "  Press Ctrl+C to stop everything."
echo ""

# wait for any child to exit
wait "${PIDS[@]}"

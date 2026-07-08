# Stage 1: Build Next.js frontend
# Pin to linux/amd64 so Next.js SWC native binaries work correctly even when
# building for linux/arm64 targets via QEMU. The build output is plain JS/CSS
# and is platform-independent.
FROM node:20-alpine AS frontend-builder
WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.11-slim AS backend

WORKDIR /app

# Install system dependencies including Node.js 20
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy frontend standalone build
COPY --from=frontend-builder /app/web/.next/standalone ./web/
COPY --from=frontend-builder /app/web/.next/static ./web/.next/static
COPY --from=frontend-builder /app/web/public ./web/public

# Create non-root user and ensure data directory is writable
RUN useradd -m -u 1001 appuser && \
    mkdir -p /app/data /app/data/logs /app/data/benchmark_results && \
    chown -R appuser:appuser /app

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV BACKEND_PORT=8000
ENV FRONTEND_PORT=3000
ENV DATA_DIR=/app/data
ENV LOG_FILE_PATH=/app/data/logs/app.log
ENV BENCHMARK_RESULTS_DIR=/app/data/benchmark_results

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start script
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

USER appuser

CMD ["/start.sh"]
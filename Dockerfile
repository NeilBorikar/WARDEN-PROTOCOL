# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for Warden Protocol (Backend + Compiled React Web Console)

# ==========================================
# Stage 1: Build React Frontend
# ==========================================
FROM node:20-slim AS frontend-builder
WORKDIR /web
COPY web/package*.json ./
RUN npm install --legacy-peer-deps
COPY web/ ./
RUN npm run build

# ==========================================
# Stage 2: Production Python Base
# ==========================================
FROM python:3.11-slim AS runner
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/pyproject.toml backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "uvicorn[standard]" fastapi sqlmodel httpx pynacl pydantic-settings pyyaml respx pytest hypothesis

# Copy backend application source
COPY backend/app /app/backend/app
COPY backend/scripts /app/backend/scripts
COPY results /app/results
COPY backend/results /app/backend/results
COPY docs /app/docs

# Copy compiled frontend from Stage 1 into web/dist
COPY --from=frontend-builder /web/dist /app/web/dist

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD sh -c "curl -f http://localhost:${PORT:-8000}/health || exit 1"

# Start production server
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

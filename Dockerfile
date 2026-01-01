# JJ-Bot Professional Trading Platform
# Multi-stage Docker build for production deployment

# ============================================
# Stage 1: Build frontend
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/dashboard

# Copy package files
COPY dashboard/jj-dashboard/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY dashboard/jj-dashboard/ ./

# Build production bundle
RUN npm run build

# ============================================
# Stage 2: Python backend
# ============================================
FROM python:3.11-slim AS backend

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user for security
RUN groupadd -r jjbot && useradd -r -g jjbot jjbot

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=jjbot:jjbot . .

# Copy frontend build from builder stage
COPY --from=frontend-builder /app/dashboard/dist ./dashboard/jj-dashboard/dist

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/models /app/backups /app/config/ssl \
    && chown -R jjbot:jjbot /app

# Switch to non-root user
USER jjbot

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/system/health')" || exit 1

# Default command
CMD ["python", "scripts/run_server.py", "--host", "0.0.0.0", "--port", "8000"]

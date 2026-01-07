# ===========================================
# Clothify Discord Bot - Dockerfile
# ===========================================
# Multi-stage build for optimized image size

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and build wheels
COPY bot/requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN groupadd -r clothify && useradd -r -g clothify clothify

# Install wheels from builder stage
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

# Copy application code
COPY bot/ ./bot/

# Create directories for mounted volumes
RUN mkdir -p /files/input_image /files/output_image && \
    chown -R clothify:clothify /app /files

# Switch to non-root user
USER clothify

# Environment variables (defaults, overridden by Coolify)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check (optional - bot stays connected)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the bot
CMD ["python", "-m", "bot.main"]

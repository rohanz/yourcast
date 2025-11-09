# Single-stage build to avoid virtual environment path issues
FROM python:3.11-slim

# Security: Install only critical runtime and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Security: Create non-root user with minimal permissions
RUN groupadd -r -g 999 worker && useradd -r -u 999 -g worker -s /sbin/nologin -c "Worker User" worker

# Set working directory and copy app
WORKDIR /app
COPY --chown=worker:worker workers/agent/ .
# Copy shared config module and config directory  
COPY --chown=worker:worker shared/yourcast_config/ /app/yourcast_config/
COPY --chown=worker:worker config/ /app/config/

# Remove any existing virtual environment and give worker user ownership of /app
RUN rm -rf /app/.venv || true \
    && mkdir -p /app/storage /app/temp /app/logs /home/worker/.cache/uv \
    && chown -R worker:worker /app /home/worker \
    && chmod 755 /app/storage /app/temp /app/logs /home/worker/.cache/uv

# Make startup script executable
RUN chmod +x start_worker.sh

# Switch to worker user before installing dependencies
USER worker

# Install Python dependencies using uv as the worker user
RUN uv sync --no-cache --no-dev

# Security: Set secure temporary directory
ENV TMPDIR=/app/temp

# Security: Switch to non-root user
USER worker

# Set environment variables
ENV PATH="/app/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080

# Run HTTP worker for Cloud Tasks
# Use the venv directly instead of 'uv run' to avoid re-syncing at startup
CMD ["/app/.venv/bin/uvicorn", "http_worker:app", "--host", "0.0.0.0", "--port", "8080"]

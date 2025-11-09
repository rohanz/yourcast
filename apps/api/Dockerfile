FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY apps/api/pyproject.toml ./

# Install dependencies  
RUN uv sync --no-cache && \
    uv pip list

# Create non-root user first
RUN groupadd -g 1000 app && useradd -u 1000 -g app --create-home --shell /bin/bash app


# Copy application code and set ownership
COPY --chown=app:app apps/api/ .
# Copy shared config module and config directory
COPY --chown=app:app shared/yourcast_config/ /app/yourcast_config/
COPY --chown=app:app config/ /app/config/
# Fix virtual environment ownership and permissions
RUN chown -R app:app /app/.venv \
    && find /app/.venv -type f -exec chmod 644 {} + \
    && find /app/.venv -type d -exec chmod 755 {} + \
    && find /app/.venv/bin -type f -exec chmod 755 {} +

USER app

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
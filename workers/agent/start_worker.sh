#!/bin/bash
# Start both Redis queue worker and Celery worker

# Start Celery worker in background
echo "Starting Celery worker..."
uv run celery -A agent.celery_app worker --loglevel=info --concurrency=1 &
CELERY_PID=$!

# Start Redis queue worker in foreground
echo "Starting Redis queue worker..."
uv run python redis_worker.py &
REDIS_PID=$!

# Function to kill both processes on exit
cleanup() {
    echo "Shutting down workers..."
    kill $CELERY_PID $REDIS_PID 2>/dev/null
    exit 0
}

# Set trap to cleanup on exit
trap cleanup SIGTERM SIGINT

# Wait for both processes
wait $CELERY_PID $REDIS_PID
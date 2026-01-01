#!/bin/bash
# Startup script for Railway

# Use Railway's PORT or default to 8000
PORT=${PORT:-8000}

echo "Starting uvicorn on port $PORT..."

# Start uvicorn
uvicorn app.main:app --host 0.0.0.0 --port $PORT

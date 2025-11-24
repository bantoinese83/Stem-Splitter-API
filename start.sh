#!/bin/bash
# Start script for Railway deployment
# Handles PORT environment variable properly

# Get port from environment variable, default to 8000
PORT=${PORT:-8000}

# Start uvicorn with the port
# Use 1 worker to reduce memory usage (TensorFlow/Spleeter is memory-intensive)
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1

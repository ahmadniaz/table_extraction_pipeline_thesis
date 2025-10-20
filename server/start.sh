#!/bin/bash

# Check if credentials file exists in secrets directory
if [ -f "/etc/secrets/pdf-tables-extractor-465009-d9172fd0045d.json" ]; then
    echo "✅ Credentials file found in /etc/secrets/"
else
    echo "⚠️  Credentials file not found in /etc/secrets/"
fi

# Enhanced timeout configuration for large file processing
# Use environment variables with fallback defaults
UVICORN_TIMEOUT_KEEP_ALIVE=${UVICORN_TIMEOUT_KEEP_ALIVE:-1800}  # 30 minutes default
UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=${UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN:-60}  # 60 seconds default
UVICORN_WORKERS=${UVICORN_WORKERS:-1}  # Single worker default for stability

echo "🚀 Starting server with timeout configuration:"
echo "   - Keep-alive timeout: ${UVICORN_TIMEOUT_KEEP_ALIVE}s"
echo "   - Graceful shutdown: ${UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN}s"
echo "   - Workers: ${UVICORN_WORKERS}"

# Start the FastAPI application as root (to access secrets)
# Enhanced timeout for large file processing (30 minutes keep-alive)
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers ${UVICORN_WORKERS} \
  --timeout-keep-alive ${UVICORN_TIMEOUT_KEEP_ALIVE} \
  --timeout-graceful-shutdown ${UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN} \
  --limit-concurrency 100 \
  --limit-max-requests 1000 \
  --log-level info 
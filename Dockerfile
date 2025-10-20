# Use Python 3.11.13 slim image as base
FROM python:3.11.13-slim

# Set working directory in the container
WORKDIR /app

# Set environment variables to optimize Python performance
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONHASHSEED=random \
    MALLOC_ARENA_MAX=2 \
    # Model cache directories
    EASYOCR_MODULE_PATH=/tmp/model_cache/easyocr \
    DOCLING_CACHE_DIR=/tmp/model_cache/docling \
    HF_HOME=/tmp/model_cache/transformers \
    TRANSFORMERS_CACHE=/tmp/model_cache/transformers \
    # OpenAI configuration
    OPENAI_API_KEY="" \
    OPENAI_API_BASE="https://api.openai.com/v1" \
    # Mistral AI configuration (REQUIRED for Mistral extraction)
    MISTRAL_API_KEY="" \
    # Anthropic/Claude AI configuration (PRIMARY - Superior accuracy)
    ANTHROPIC_API_KEY="" \
    # Database configuration
    RENDER_DB_KEY="" \
    SUPABASE_DB_KEY="" \
    # Timeout configuration for large file processing (in seconds)
    # WebSocket timeouts
    WEBSOCKET_TIMEOUT=1800 \
    WEBSOCKET_PING_INTERVAL=30 \
    WEBSOCKET_KEEPALIVE=300 \
    # API timeouts
    MISTRAL_TIMEOUT=1800 \
    GPT_TIMEOUT=300 \
    # Process timeouts
    EXTRACTION_TIMEOUT=1800 \
    DOCUMENT_PROCESSING_TIMEOUT=600 \
    TABLE_EXTRACTION_TIMEOUT=1200 \
    METADATA_EXTRACTION_TIMEOUT=300 \
    POST_PROCESSING_TIMEOUT=300 \
    # Server timeouts
    UVICORN_TIMEOUT_KEEP_ALIVE=1800 \
    UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=60 \
    # Document size-based timeouts
    SMALL_DOC_TIMEOUT=300 \
    MEDIUM_DOC_TIMEOUT=600 \
    LARGE_DOC_TIMEOUT=1200 \
    MAX_TIMEOUT=1800

# Install system dependencies required for OpenCV, EasyOCR, Tesseract, and other packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libopenblas-dev \
    libhdf5-dev \
    libhdf5-serial-dev \
    libhdf5-hl-310 \
    python3-dev \
    curl \
    htop \
    procps \
    # Tesseract OCR dependencies
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    # Additional ML dependencies
    liblapack-dev \
    libblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first (for better Docker layer caching)
COPY server/requirements.txt .

# Verify Python version and install Python dependencies
RUN python --version && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Pre-download EasyOCR English model during build to avoid slow first-time downloads
RUN python -c "import easyocr; easyocr.Reader(['en'], gpu=False, download_enabled=True)"

# Pre-download Docling models to avoid runtime downloads
RUN python -c "from docling import document_converter; converter = document_converter.DocumentConverter()"

# Pre-download TableFormer models for the new extraction service
RUN python -c "from transformers import AutoImageProcessor, AutoModelForObjectDetection; AutoImageProcessor.from_pretrained('microsoft/table-transformer-detection', cache_dir='/tmp/model_cache/transformers'); AutoModelForObjectDetection.from_pretrained('microsoft/table-transformer-detection', cache_dir='/tmp/model_cache/transformers')"
RUN python -c "from transformers import AutoImageProcessor, AutoModelForObjectDetection; AutoImageProcessor.from_pretrained('microsoft/table-transformer-structure-recognition-v1.1-all', cache_dir='/tmp/model_cache/transformers'); AutoModelForObjectDetection.from_pretrained('microsoft/table-transformer-structure-recognition-v1.1-all', cache_dir='/tmp/model_cache/transformers')"

# Create persistent model cache directories
RUN mkdir -p /tmp/model_cache/easyocr /tmp/model_cache/docling /tmp/model_cache/transformers

# Copy downloaded models to persistent location
RUN cp -r /root/.cache/easyocr/* /tmp/model_cache/easyocr/ 2>/dev/null || true
RUN cp -r /root/.cache/docling/* /tmp/model_cache/docling/ 2>/dev/null || true
RUN cp -r /root/.cache/huggingface/* /tmp/model_cache/transformers/ 2>/dev/null || true

# Copy the entire server directory
COPY server/ .

# Make the startup script executable
RUN chmod +x start.sh

# Run as root to access Render secrets directory
# Render mounts secrets with root-only permissions

# Expose port 8000
EXPOSE 8000

# Health check optimized for Pro plan with long-running operations
HEALTHCHECK --interval=60s --timeout=30s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command to run the startup script which checks credentials and starts the app
CMD ["./start.sh"] 
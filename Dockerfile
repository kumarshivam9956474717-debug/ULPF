FROM python:3.12-slim

WORKDIR /app

# Set environment variables for Python in containers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AIR_GAPPED_MODE=True

# Install system dependencies required for compilation and postgres client
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY backend/ .

# Expose backend API port and Syslog listener ports
EXPOSE 8000 1514/udp 1514/tcp 16514/tcp

# Run FastAPI with uvicorn supporting dynamic PORT env var (Render/Railway default)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

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

# Create unprivileged application user
RUN groupadd -g 10001 omnilogix && \
    useradd -u 10001 -g omnilogix -s /bin/sh -m omnilogix

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create necessary directories and set ownership for unprivileged execution
RUN mkdir -p /app/data/raw /app/data/processed /app/data/synthetic && \
    chown -R omnilogix:omnilogix /app

USER omnilogix

# Expose backend API port and Syslog listener ports
EXPOSE 8000 1514/udp 1514/tcp 16514/tcp

# Run FastAPI with uvicorn supporting dynamic PORT env var
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]


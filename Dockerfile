# H2SQL API Dockerfile
# Pin base image to Harbor registry mirror to avoid Docker Hub pulls
FROM harbor.int.taqniat.ae/library/python@sha256:2be5d3cb08aa616c6e38d922bd7072975166b2de772004f79ee1bae59fe983dc

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY .env .env

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 11901

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:11901/health || exit 1

# Run the application
CMD ["python", "app/main.py"]

# MediaShare Backend — Dockerfile 
# Backend Developer: PHDB Nayanakantha
# DevOps: KKVRM Kalyanapriya
#
# This runs the Flask API server (app/main.py)
# Entry point: python app/main.py  OR  gunicorn app.main:app

FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies
# gcc and libffi-dev are needed to compile some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies 
# Copy requirements first — Docker caches this layer
# If requirements.txt hasn't changed, this layer is reused (faster rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn flask-cors

# Copy the entire backend source code 
# This copies everything from backend/ folder into /app inside the container
COPY . .

# Create a folder for the JSON database file 
# MockDynamoDB writes media_db.json here — needs a writable directory
RUN mkdir -p /app/data && chmod 777 /app/data

# Environment variables (defaults — override in docker-compose.yml)
ENV FLASK_ENV=development \
    DEBUG=False \
    DB_FILE=/app/data/media_db.json \
    LOG_LEVEL=INFO \
    PORT=5000

# Flask API runs on port 5000
EXPOSE 5000

# Health check 
# Docker will call GET /health every 20s to check if the API is alive
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Start command
# Using gunicorn for production-style serving
# "app.main:app" means: file=app/main.py, Flask object=app
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "--access-logfile", "-", "app.main:app"]

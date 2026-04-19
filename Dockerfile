# Microsoft's official Playwright Python image has Chromium + deps preinstalled
FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY app/       ./app/
COPY template/  ./template/
COPY config/    ./config/
COPY scripts/   ./scripts/

# Render injects $PORT at runtime (usually 10000)
ENV PORT=10000
EXPOSE 10000

# 1 worker + 2 threads = safe for sync_playwright in a low-traffic app
CMD gunicorn \
    --workers 1 \
    --threads 2 \
    --timeout 120 \
    --bind 0.0.0.0:$PORT \
    app.main:app

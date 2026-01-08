# Multi-stage build for Python backend
FROM python:3.12-alpine AS base

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    postgresql-dev \
    gcc \
    g++ \
    musl-dev \
    libffi-dev \
    git \
    make \
    unixodbc-dev

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

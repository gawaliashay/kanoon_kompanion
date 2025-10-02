# ---------------------------
# Stage 1: Build dependencies
# ---------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Prevent writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install CPU-only dependencies
COPY requirements.txt .

RUN pip install --upgrade pip

# Install CPU-only torch to avoid nvidia CUDA packages
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt \
    torch --index-url https://download.pytorch.org/whl/cpu

# ---------------------------
# Stage 2: Production image
# ---------------------------
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy only necessary project files
COPY api/ api/
COPY src/ src/
COPY static/ static/
COPY templates/ templates/
COPY requirements.txt .

# Expose API port
EXPOSE 8000

# Environment variables
ENV FASTAPI_HOST=0.0.0.0
ENV FASTAPI_PORT=8000
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Run API with Uvicorn
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

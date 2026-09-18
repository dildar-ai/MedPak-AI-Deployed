FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for EasyOCR and OpenCV
# Note: libgl1-mesa-glx was renamed to libgl1 in Debian Trixie
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
# CPU-only PyTorch first: the default Linux wheels bundle CUDA (~4 GB) that a
# CPU-only deployment never uses — skipping it shrinks the image and cuts
# build time by more than half.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Hugging Face Spaces runs the container as UID 1000 — create that user and
# make /app writable so SQLite DBs (live_prices, users, history) can update.
RUN useradd -m -u 1000 user
COPY --chown=user:user . .
RUN mkdir -p /app/database && chown -R user:user /app/database

# EasyOCR downloads its models to $HOME/.EasyOCR at runtime
ENV HOME=/home/user \
    PYTHONPATH=/app

USER user

# Expose Hugging Face default port
EXPOSE 7860

# Start FastAPI with uvicorn.
# --proxy-headers: Hugging Face routes traffic through its proxy — without
# this every visitor shares the proxy's IP and one combined rate-limit bucket.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]

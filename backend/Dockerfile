FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for EasyOCR
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend files
COPY . .

# Build RAG vector index
RUN python rag/vectorstore.py

# Expose port
EXPOSE 7860

# Start the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
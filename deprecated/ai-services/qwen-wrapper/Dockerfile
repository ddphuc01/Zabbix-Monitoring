FROM python:3.11-slim

WORKDIR /app

# Install Node.js (required by qwen CLI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install qwen CLI globally
RUN npm install -g @qwen-code/qwen-code

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (using original CLI wrapper)
COPY qwen_wrapper.py .

# Update QWEN_BIN path
ENV QWEN_BIN=/usr/local/bin/qwen

EXPOSE 11434

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:11434/health')" || exit 1

# Run wrapper
CMD ["python", "qwen_wrapper.py"]


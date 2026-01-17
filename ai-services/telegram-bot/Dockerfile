FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot files
COPY bot.py reports.py email_sender.py ./

# Health check  
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD python -c "import sys; sys.exit(0)"

# Run bot
CMD ["python", "bot.py"]

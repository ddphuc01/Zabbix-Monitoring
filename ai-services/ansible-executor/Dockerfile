FROM python:3.11-slim

# Install system dependencies for Ansible
RUN apt-get update && apt-get install -y \
    ssh \
    sshpass \
    openssh-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY ansible_executor.py .
COPY diagnostic_analyzer.py .

# Create directories
RUN mkdir -p /ansible /var/log/ansible /root/.ssh

# Set permissions
RUN chmod 700 /root/.ssh

# Environment
ENV PYTHONUNBUFFERED=1
ENV ANSIBLE_DIR=/ansible
ENV ANSIBLE_HOST_KEY_CHECKING=False

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "print('OK')" || exit 1

# Default command - keep container running
CMD ["sh", "-c", "echo 'Ansible Executor ready' && tail -f /dev/null"]

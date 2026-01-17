#!/bin/bash
# Setup script for Ansible on Host + REST API architecture
# Configures SSH keys, installs dependencies, and sets up the API service

set -e

echo "🚀 Setting up Ansible REST API Service on Host..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_DIR="/home/phuc/zabbix-monitoring"
API_DIR="$PROJECT_DIR/ansible-api-service"
SSH_KEY_DIR="$PROJECT_DIR/ssh-keys"
SSH_KEY="$SSH_KEY_DIR/ansible_key"

echo -e "${YELLOW}Step 1: Configuring SSH Keys${NC}"
# Set correct permissions for SSH keys
if [ -f "$SSH_KEY" ]; then
    chmod 600 "$SSH_KEY"
    chmod 644 "$SSH_KEY.pub"
    echo -e "${GREEN}✅ SSH key permissions set${NC}"
else
    echo -e "${RED}❌ SSH key not found at $SSH_KEY${NC}"
    exit 1
fi

# Configure SSH config if not exists
SSH_CONFIG="/root/.ssh/config"
if [ ! -f "$SSH_CONFIG" ]; then
    mkdir -p /root/.ssh
    cat > "$SSH_CONFIG" << 'EOF'
Host *
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
    IdentityFile /home/phuc/zabbix-monitoring/ssh-keys/ansible_key
EOF
    chmod 600 "$SSH_CONFIG"
    echo -e "${GREEN}✅ SSH config created${NC}"
else
    echo -e "${YELLOW}⚠️  SSH config already exists, skipping${NC}"
fi

echo -e "${YELLOW}Step 2: Installing Python Dependencies${NC}"
cd "$API_DIR"

# Check if pip3 is installed
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip3 not found, installing...${NC}"
    apt-get update
    apt-get install -y python3-pip
fi

# Install requirements (use --break-system-packages for Ubuntu 24.04)
pip3 install --break-system-packages -r requirements.txt
echo -e "${GREEN}✅ Python dependencies installed${NC}"

echo -e "${YELLOW}Step 3: Installing Systemd Service${NC}"
# Copy systemd service file
cp "$API_DIR/systemd/ansible-api.service" /etc/systemd/system/
systemctl daemon-reload
echo -e "${GREEN}✅ Systemd service installed${NC}"

echo -e "${YELLOW}Step 4: Testing Ansible Connectivity${NC}"
# Test SSH connectivity to known hosts
cd "$PROJECT_DIR/ansible"

echo "Testing Linux host connectivity..."
if ansible -i inventory/hosts.yml host-192.168.1.143 -m ping 2>/dev/null; then
    echo -e "${GREEN}✅ Linux host reachable${NC}"
else
    echo -e "${YELLOW}⚠️  Linux host not reachable (will continue)${NC}"
fi

echo "Testing Windows host connectivity..."
if ansible -i inventory/hosts.yml win-pc-129 -m win_ping 2>/dev/null; then
    echo -e "${GREEN}✅ Windows host reachable${NC}"
else
    echo -e "${YELLOW}⚠️  Windows host not reachable (will continue)${NC}"
fi

echo -e "${YELLOW}Step 5: Starting Ansible API Service${NC}"
systemctl enable ansible-api
systemctl start ansible-api

# Wait for service to start
sleep 3

# Check service status
if systemctl is-active --quiet ansible-api; then
    echo -e "${GREEN}✅ Ansible API service is running${NC}"
else
    echo -e "${RED}❌ Service failed to start${NC}"
    systemctl status ansible-api --no-pager
    exit 1
fi

echo -e "${YELLOW}Step 6: Testing API Endpoint${NC}"
# Test health endpoint
if curl -s http://localhost:5001/health | grep -q "healthy"; then
    echo -e "${GREEN}✅ API health check passed${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Ansible REST API is running on: http://localhost:5001"
echo ""
echo "Service commands:"
echo "  - Status:  sudo systemctl status ansible-api"
echo "  - Logs:    sudo journalctl -u ansible-api -f"
echo "  - Restart: sudo systemctl restart ansible-api"
echo "  - Stop:    sudo systemctl stop ansible-api"
echo ""
echo "API endpoints:"
echo "  - Health:       GET  http://localhost:5001/health"
echo "  - Run playbook: POST http://localhost:5001/api/v1/playbook/run"
echo "  - Job status:   GET  http://localhost:5001/api/v1/playbook/status/{job_id}"
echo ""

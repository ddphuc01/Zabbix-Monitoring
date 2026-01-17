#!/bin/bash
# scripts/onboard_host.sh

# Defauts
DEFAULT_USER="root"
DEFAULT_ZABBIX_SERVER="192.168.1.203" # Default Docker Host IP
PRIV_KEY="ssh-keys/ansible_key"
PUB_KEY="ssh-keys/ansible_key.pub"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Zabbix Agent Onboarding Script ===${NC}"

# 1. Get Inputs
read -p "Enter Target Host IP: " TARGET_IP
if [[ -z "$TARGET_IP" ]]; then
    echo -e "${RED}Error: IP is required.${NC}"
    exit 1
fi

read -p "Enter SSH User [default: $DEFAULT_USER]: " SSH_USER
SSH_USER=${SSH_USER:-$DEFAULT_USER}

read -s -p "Enter SSH Password for $SSH_USER: " SSH_PASS
echo ""

read -p "Enter Zabbix Server Public IP [default: $DEFAULT_ZABBIX_SERVER]: " ZABBIX_SERVER_IP
ZABBIX_SERVER_IP=${ZABBIX_SERVER_IP:-$DEFAULT_ZABBIX_SERVER}

# 2. Check/Generate Keys
if [ ! -f "$PRIV_KEY" ]; then
    echo "Generating SSH keys at $PRIV_KEY..."
    ssh-keygen -t rsa -b 4096 -f "$PRIV_KEY" -N ""
fi

# Ensure correct permissions locally
chmod 600 "$PRIV_KEY"

# 3. Copy SSH Key
echo -e "\n${GREEN}[Step 1] Copying SSH Key to $TARGET_IP...${NC}"
export SSHPASS="$SSH_PASS"
sshpass -e ssh-copy-id -i "$PUB_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$TARGET_IP"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to copy SSH key. Please check credentials and connectivity.${NC}"
    exit 1
fi

# 4. Install Agent via SSH (Non-interactive sudo)
echo -e "\n${GREEN}[Step 2] Installing Zabbix Agent on remote host...${NC}"
CMD_INSTALL="
set -e
# Pre-check: Wait for APT lock
if fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; then
   echo '--> Waiting for other apt processes to finish (lock detected)...'
   sleep 10
   # Kill if stuck (optional, but requested for stability in testing)
   # echo '$SSH_PASS' | sudo -S killall apt apt-get 2>/dev/null || true
fi

# Install Zabbix Repo (assuming Ubuntu/Debian)
if ! command -v zabbix_agentd &> /dev/null; then
    echo '--> Detecting OS version...'
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo \"Detected: \$NAME \$VERSION_ID\"
        
        # Install wget if missing
        which wget >/dev/null || (echo '$SSH_PASS' | sudo -S apt-get update && echo '$SSH_PASS' | sudo -S apt-get install -y wget)
        
        # Download and install Zabbix Release deb
        REPO_URL=\"https://repo.zabbix.com/zabbix/7.0/ubuntu/pool/main/z/zabbix-release/zabbix-release_7.0-2+ubuntu\${VERSION_ID}_all.deb\"
        echo \"--> Downloading Zabbix repo: \$REPO_URL\"
        wget -q \"\$REPO_URL\" -O /tmp/zabbix-release.deb || echo 'Failed to download repo, trying default apt...'
        
        if [ -s /tmp/zabbix-release.deb ]; then
             echo '$SSH_PASS' | sudo -S dpkg -i /tmp/zabbix-release.deb
        fi
    fi

    echo '--> Updating apt cache...'
    echo '$SSH_PASS' | sudo -S apt-get update -qq
    echo '--> Installing zabbix-agent...'
    echo '$SSH_PASS' | sudo -S apt-get install -y zabbix-agent -qq
else
    echo '--> Zabbix Agent already installed.'
fi
"
# Use Key explicitly
ssh -i "$PRIV_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$TARGET_IP" "$CMD_INSTALL"

# 5. Configure Agent
echo -e "\n${GREEN}[Step 3] Configuring Zabbix Agent...${NC}"
CMD_CONFIG="
echo '$SSH_PASS' | sudo -S cp /etc/zabbix/zabbix_agentd.conf /etc/zabbix/zabbix_agentd.conf.bak 2>/dev/null || true
echo '--> Updating config...'
echo '$SSH_PASS' | sudo -S sed -i 's/^Server=127.0.0.1/Server=$ZABBIX_SERVER_IP/' /etc/zabbix/zabbix_agentd.conf
echo '$SSH_PASS' | sudo -S sed -i 's/^ServerActive=127.0.0.1/ServerActive=$ZABBIX_SERVER_IP/' /etc/zabbix/zabbix_agentd.conf
echo '$SSH_PASS' | sudo -S sed -i 's/^Hostname=Zabbix server/Hostname=$TARGET_IP/' /etc/zabbix/zabbix_agentd.conf

echo '--> Restarting service...'
echo '$SSH_PASS' | sudo -S systemctl restart zabbix-agent
echo '$SSH_PASS' | sudo -S systemctl enable zabbix-agent
systemctl is-active zabbix-agent
"
ssh -i "$PRIV_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$TARGET_IP" "$CMD_CONFIG"

# 6. Verification
echo -e "\n${GREEN}=== Verification ===${NC}"
echo "Testing SSH Key authentication..."
if ssh -i "$PRIV_KEY" -o BatchMode=yes -o StrictHostKeyChecking=no "$SSH_USER@$TARGET_IP" "echo 'SSH Connection Success'"; then
    echo -e "${GREEN}✅ SSH Key working! Ansible can connect.${NC}"
else
    echo -e "${RED}❌ SSH Key check failed.${NC}"
fi

echo -e "\n${GREEN}=== Completed ===${NC}"
echo "1. Host $TARGET_IP is ready."
echo "2. Add this host to 'ansible/inventory/hosts.yml'."
echo "3. Add this host in Zabbix UI."
echo -e "\nTo verify manually, run:"
echo -e "${GREEN}ssh -i $PRIV_KEY $SSH_USER@$TARGET_IP${NC}"

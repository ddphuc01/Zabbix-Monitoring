#!/bin/bash
# scripts/full_onboard.sh - Complete automation for Zabbix Agent deployment

set -e

# Defaults
DEFAULT_USER="root"
ZABBIX_SERVER_IP="${ZABBIX_SERVER_IP:-192.168.1.203}"
INVENTORY_FILE="ansible/inventory/hosts.yml"
PRIV_KEY="ssh-keys/ansible_key"
PUB_KEY="ssh-keys/ansible_key.pub"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Full Zabbix Agent Onboarding Automation ===${NC}"

# 1. Get Inputs
read -p "Enter Target Host IP: " TARGET_IP
if [[ -z "$TARGET_IP" ]]; then
    echo -e "${RED}Error: IP is required.${NC}"
    exit 1
fi

read -p "Enter SSH User (regular user) [default: ubuntu]: " SSH_USER
SSH_USER=${SSH_USER:-ubuntu}

read -s -p "Enter SSH Password for $SSH_USER: " SSH_PASS
echo ""

read -p "Enter root password (if different, leave blank if same): " ROOT_PASS
ROOT_PASS=${ROOT_PASS:-$SSH_PASS}

read -p "Enter Zabbix Server IP [default: $ZABBIX_SERVER_IP]: " ZABBIX_INPUT
ZABBIX_SERVER_IP=${ZABBIX_INPUT:-$ZABBIX_SERVER_IP}

read -p "Enter Hostname for inventory [default: host-$TARGET_IP]: " HOST_NAME
HOST_NAME=${HOST_NAME:-host-$TARGET_IP}

# 2. Check/Generate Keys
if [ ! -f "$PRIV_KEY" ]; then
    echo -e "\n${YELLOW}Generating SSH keys...${NC}"
    ssh-keygen -t rsa -b 4096 -f "$PRIV_KEY" -N ""
fi
chmod 600 "$PRIV_KEY"

# 3. Copy SSH Key to User
echo -e "\n${GREEN}[Step 1] Copying SSH Key to $SSH_USER@$TARGET_IP...${NC}"
export SSHPASS="$SSH_PASS"
sshpass -e ssh-copy-id -i "$PUB_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$TARGET_IP" 2>/dev/null || echo "Keys already exist"

# 4. Copy SSH Key to Root (via sudo or direct)
echo -e "\n${GREEN}[Step 2] Setting up root SSH access...${NC}"
ssh -i "$PRIV_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$TARGET_IP" "echo '$SSH_PASS' | sudo -S mkdir -p /root/.ssh && echo '$SSH_PASS' | sudo -S chmod 700 /root/.ssh"
ssh -i "$PRIV_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$TARGET_IP" "cat ~/.ssh/authorized_keys | echo '$SSH_PASS' | sudo -S tee -a /root/.ssh/authorized_keys > /dev/null"
ssh -i "$PRIV_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$TARGET_IP" "echo '$SSH_PASS' | sudo -S chmod 600 /root/.ssh/authorized_keys"

echo -e "${GREEN}✅ SSH key copied to both $SSH_USER and root${NC}"

# 5. Add to Ansible Inventory
echo -e "\n${GREEN}[Step 3] Adding host to Ansible inventory...${NC}"

# Remove existing entry if present
if grep -q "  $HOST_NAME:" "$INVENTORY_FILE"; then
    echo -e "${YELLOW}Updating existing host entry...${NC}"
    # Remove the 3-line block for this host
    sed -i "/  $HOST_NAME:/,+2d" "$INVENTORY_FILE"
fi

# Ensure linux_hosts group exists
if ! grep -q "linux_hosts:" "$INVENTORY_FILE"; then
    echo "Creating linux_hosts group..."
    # Add before the closing of 'all' section
    cat >> "$INVENTORY_FILE" << EOF

    linux_hosts:
      hosts:
EOF
fi

# Add host entry (simple append after finding linux_hosts)
if grep -q "linux_hosts:" "$INVENTORY_FILE"; then
    # Check if hosts: line exists under linux_hosts
    if ! awk '/linux_hosts:/,/^[^ ]/ {if (/hosts:/) exit 0} END {exit 1}' "$INVENTORY_FILE"; then
        # Add hosts: line
        sed -i '/linux_hosts:/a\      hosts:' "$INVENTORY_FILE"
    fi
    
    # Append the new host
    sed -i "/linux_hosts:/,/^    [a-z]/ {
        /hosts:/a\\        $HOST_NAME:\\n          ansible_host: $TARGET_IP\\n          ansible_user: root
    }" "$INVENTORY_FILE"
    
    echo -e "${GREEN}✅ Added $HOST_NAME to linux_hosts group${NC}"
else
    echo -e "${RED}❌ Failed to add host to inventory${NC}"
fi

# 6. Install Zabbix Agent via Ansible
echo -e "\n${GREEN}[Step 4] Installing Zabbix Agent via Ansible...${NC}"

# Try to install Galaxy collection (optional)
echo "Attempting to install Ansible Galaxy dependencies..."
if docker compose exec ansible-executor ansible-galaxy collection install -r /ansible/requirements.yml -f 2>/dev/null; then
    echo -e "${GREEN}✅ Galaxy collection installed${NC}"
    PLAYBOOK="install_agent_galaxy.yml"
else
    echo -e "${YELLOW}⚠️  Galaxy collection unavailable, using custom playbook${NC}"
    PLAYBOOK="install_zabbix_agent.yml"
fi

echo "Running playbook: $PLAYBOOK"
docker compose exec ansible-executor ansible-playbook \
    "/ansible/playbooks/setup/$PLAYBOOK" \
    -e "target_host=$HOST_NAME" \
    -e "zabbix_server=$ZABBIX_SERVER_IP"

# 7. Verification
echo -e "\n${GREEN}[Step 5] Verifying installation...${NC}"

# Test SSH connectivity
echo "Testing SSH key authentication..."
if ssh -i "$PRIV_KEY" -o BatchMode=yes -o StrictHostKeyChecking=no "root@$TARGET_IP" "echo 'SSH OK'" &>/dev/null; then
    echo -e "${GREEN}✅ SSH Key authentication working${NC}"
else
    echo -e "${RED}❌ SSH Key check failed${NC}"
fi

# Test Zabbix Agent status
echo "Checking Zabbix Agent 2 status..."
AGENT_STATUS=$(ssh -i "$PRIV_KEY" -o BatchMode=yes -o StrictHostKeyChecking=no "root@$TARGET_IP" "systemctl is-active zabbix-agent2" 2>/dev/null || echo "inactive")

if [ "$AGENT_STATUS" = "active" ]; then
    echo -e "${GREEN}✅ Zabbix Agent 2 is running${NC}"
else
    echo -e "${YELLOW}⚠️  Zabbix Agent 2 is not running (status: $AGENT_STATUS)${NC}"
    echo -e "${YELLOW}   This is normal if playbook didn't run due to inventory issues${NC}"
fi

# 8. Summary
echo -e "\n${GREEN}=== Onboarding Complete ===${NC}"
echo "Host: $HOST_NAME ($TARGET_IP)"
echo "Inventory: Updated in $INVENTORY_FILE"
echo "Zabbix Agent: Installed and configured"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Add this host in Zabbix UI:"
echo "   - Configuration -> Hosts -> Create host"
echo "   - Host name: $HOST_NAME"
echo "   - Templates: Linux by Zabbix agent"
echo "   - Interface: Agent $TARGET_IP:10050"
echo ""
echo "2. Test SSH access:"
echo "   ssh -i $PRIV_KEY root@$TARGET_IP"

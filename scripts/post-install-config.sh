#!/bin/bash
# Post-Installation Configuration Script
# Runs Ansible playbook to configure Zabbix after deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ANSIBLE_DIR="${PROJECT_DIR}/ansible"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Zabbix Post-Installation Configuration${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if Ansible is available
if ! command -v ansible-playbook &> /dev/null; then
    echo -e "${RED}❌ Ansible not found!${NC}"
    echo ""
    echo "Installing Ansible collection..."
    docker compose exec ansible-executor ansible-galaxy collection install -r /ansible/requirements.yml
fi

# Load environment variables
if [ -f "${PROJECT_DIR}/.env" ]; then
    set -a
    source "${PROJECT_DIR}/.env"
    set +a
fi

# Set defaults
export ZABBIX_URL="${ZABBIX_URL:-http://localhost:8080}"
export ZABBIX_API_USER="${ZABBIX_API_USER:-Admin}"
export ZABBIX_API_PASSWORD="${ZABBIX_API_PASSWORD:-zabbix}"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Zabbix URL: ${ZABBIX_URL}"
echo "  API User: ${ZABBIX_API_USER}"
echo ""

# Run playbook inside ansible-executor container
echo -e "${YELLOW}Running post-installation playbook...${NC}"
echo ""

docker compose exec -T ansible-executor ansible-playbook \
    /ansible/playbooks/setup/post_install_config.yml \
    -e "zabbix_url=${ZABBIX_URL}" \
    -e "zabbix_api_user=${ZABBIX_API_USER}" \
    -e "zabbix_api_password=${ZABBIX_API_PASSWORD}" \
    -v

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ Configuration Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Open Zabbix UI: ${ZABBIX_URL}"
    echo "  2. Go to: Monitoring → Hosts"
    echo "  3. Verify 'Zabbix server' ZBX icon is green"
    echo ""
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ Configuration Failed!${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check if Zabbix services are running: docker compose ps"
    echo "  2. Verify web interface is accessible: curl ${ZABBIX_URL}"
    echo "  3. Check API logs: docker compose logs zabbix-server"
    echo ""
    exit 1
fi

#!/bin/bash
# Zabbix Initialization Script
# Prepares and starts the Zabbix monitoring system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Zabbix Monitoring System Installer   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Change to project directory
cd "${PROJECT_DIR}"

# Step 1: Check prerequisites
echo -e "${YELLOW}[1/7] Checking prerequisites...${NC}"
command -v docker >/dev/null 2>&1 || { echo -e "${RED}✗ Docker is required but not installed.${NC}"; exit 1; }
command -v docker compose >/dev/null 2>&1 || command -v docker compose >/dev/null 2>&1 || { echo -e "${RED}✗ Docker Compose is required but not installed.${NC}"; exit 1; }
echo -e "${GREEN}✓ Docker and Docker Compose are installed${NC}"

# Step 2: Generate secrets if not exist
echo -e "${YELLOW}[2/7] Checking secrets...${NC}"
if [ ! -f "${PROJECT_DIR}/env_vars/.POSTGRES_USER" ]; then
    echo -e "${YELLOW}  Secrets not found, generating...${NC}"
    "${SCRIPT_DIR}/generate-secrets.sh"
else
    echo -e "${GREEN}✓ Secrets already exist${NC}"
fi

# Step 3: Create necessary directories
echo -e "${YELLOW}[3/7] Creating directory structure...${NC}"
mkdir -p zbx_env/usr/lib/zabbix/{alertscripts,externalscripts}
mkdir -p zbx_env/var/lib/zabbix/{export,modules,enc,ssh_keys,mibs}
mkdir -p zbx_env/var/lib/zabbix/ssl/{certs,keys,ssl_ca}
mkdir -p zbx_env/backups
echo -e "${GREEN}✓ Directories created${NC}"

# Step 4: Set proper permissions
echo -e "${YELLOW}[4/7] Setting permissions...${NC}"
chmod -R 775 zbx_env/
chmod 600 env_vars/.*
echo -e "${GREEN}✓ Permissions set${NC}"

# Step 5: Pull latest images
echo -e "${YELLOW}[5/7] Pulling Docker images (this may take a while)...${NC}"
docker compose pull

# Step 6: Start services
echo -e "${YELLOW}[6/7] Starting Zabbix services...${NC}"
echo -e "${BLUE}  This will start the following services:${NC}"
echo -e "  - PostgreSQL Database"
echo -e "  - Zabbix Server"
echo -e "  - Zabbix Web Interface (Nginx)"
echo -e "  - Zabbix Agent 2"
echo -e "  - Java Gateway"
echo -e "  - Web Service (Report Generation)"
echo -e "  - SNMP Traps Receiver"
echo ""

docker compose up -d

# Step 7: Wait for services to be healthy
echo -e "${YELLOW}[7/7] Waiting for services to initialize...${NC}"
echo -e "${BLUE}  This may take 1-2 minutes...${NC}"

sleep 10

# Check database initialization
echo -e "${BLUE}  Checking database initialization...${NC}"
TIMEOUT=120
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if docker compose ps | grep -q "server-db-init.*Exit 0"; then
        echo -e "${GREEN}✓ Database initialized successfully${NC}"
        break
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    echo -n "."
done
echo ""

# Check Zabbix Server
echo -e "${BLUE}  Checking Zabbix Server...${NC}"
sleep 15
if docker compose ps | grep -q "zabbix-server.*Up"; then
    echo -e "${GREEN}✓ Zabbix Server is running${NC}"
else
    echo -e "${RED}✗ Zabbix Server failed to start. Check logs with: docker compose logs zabbix-server${NC}"
fi

# Check Web Interface
echo -e "${BLUE}  Checking Web Interface...${NC}"
sleep 10
if docker compose ps | grep -q "zabbix-web.*Up"; then
    echo -e "${GREEN}✓ Web Interface is running${NC}"
else
    echo -e "${RED}✗ Web Interface failed to start. Check logs with: docker compose logs zabbix-web-nginx${NC}"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║    Installation Complete! ✓            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📊 Zabbix Web Interface:${NC}"
echo -e "   URL: ${GREEN}http://localhost:8080${NC}"
echo -e "   Default credentials:"
echo -e "     Username: ${YELLOW}Admin${NC}"
echo -e "     Password: ${YELLOW}zabbix${NC}"
echo ""
echo -e "${RED}⚠  IMPORTANT: Change the default password after first login!${NC}"
echo ""
echo -e "${BLUE}📝 Useful Commands:${NC}"
echo -e "   View logs:        ${YELLOW}docker compose logs -f${NC}"
echo -e "   Stop services:    ${YELLOW}docker compose stop${NC}"
echo -e "   Start services:   ${YELLOW}docker compose start${NC}"
echo -e "   Restart services: ${YELLOW}docker compose restart${NC}"
echo -e "   Service status:   ${YELLOW}docker compose ps${NC}"
echo -e "   Health check:     ${YELLOW}./scripts/health-check.sh${NC}"
echo ""
echo -e "${BLUE}🔧 Port Mappings:${NC}"
echo -e "   Web Interface:    ${GREEN}8080${NC} (HTTP), ${GREEN}8443${NC} (HTTPS)"
echo -e "   Zabbix Server:    ${GREEN}10051${NC}"
echo -e "   Zabbix Agent 2:   ${GREEN}10060${NC}"
echo -e "   Java Gateway:     ${GREEN}10052${NC}"
echo -e "   Web Service:      ${GREEN}10053${NC}"
echo -e "   SNMP Traps:       ${GREEN}162/UDP${NC}"
echo ""

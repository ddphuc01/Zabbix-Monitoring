#!/bin/bash
# Pre-flight Check Script for Zabbix Monitoring
# Validates environment before deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/.."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Zabbix Pre-Flight Checks${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

ERRORS=0
WARNINGS=0

# Check 1: Docker installed
echo -n "Checking Docker installation... "
if command -v docker >/dev/null 2>&1; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    echo -e "${GREEN}✓${NC} Docker ${DOCKER_VERSION}"
else
    echo -e "${RED}✗ Docker not found!${NC}"
    ((ERRORS++))
fi

# Check 2: Docker Compose installed
echo -n "Checking Docker Compose... "
if docker compose version >/dev/null 2>&1; then
    COMPOSE_VERSION=$(docker compose version --short)
    echo -e "${GREEN}✓${NC} Docker Compose v${COMPOSE_VERSION}"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_VERSION=$(docker-compose --version | awk '{print $3}' | tr -d ',')
    echo -e "${YELLOW}⚠${NC} Using legacy docker-compose v${COMPOSE_VERSION}"
    echo -e "  ${YELLOW}Recommendation: Upgrade to Docker Compose v2${NC}"
    ((WARNINGS++))
else
    echo -e "${RED}✗ Docker Compose not found!${NC}"
    ((ERRORS++))
fi

# Check 3: Docker daemon running
echo -n "Checking Docker daemon... "
if docker info >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Running"
else
    echo -e "${RED}✗ Docker daemon not running${NC}"
    ((ERRORS++))
fi

# Check 4: RAM
echo -n "Checking available RAM... "
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -ge 6 ]; then
    echo -e "${GREEN}✓${NC} ${TOTAL_RAM}GB (recommended: 6GB+)"
elif [ "$TOTAL_RAM" -ge 4 ]; then
    echo -e "${YELLOW}⚠${NC} ${TOTAL_RAM}GB (minimum met, 6GB+ recommended)"
    ((WARNINGS++))
else
    echo -e "${RED}✗${NC} ${TOTAL_RAM}GB (minimum 4GB required)"
    ((ERRORS++))
fi

# Check 5: Disk space
echo -n "Checking disk space... "
AVAILABLE_DISK=$(df -BG "$PROJECT_DIR" | awk 'NR==2 {print $4}' | tr -d 'G')
if [ "$AVAILABLE_DISK" -ge 20 ]; then
    echo -e "${GREEN}✓${NC} ${AVAILABLE_DISK}GB available"
elif [ "$AVAILABLE_DISK" -ge 10 ]; then
    echo -e "${YELLOW}⚠${NC} ${AVAILABLE_DISK}GB (low, 20GB+ recommended)"
    ((WARNINGS++))
else
    echo -e "${RED}✗${NC} ${AVAILABLE_DISK}GB (insufficient, need 10GB minimum)"
    ((ERRORS++))
fi

# Check 6: Port availability
echo "Checking port availability..."
PORTS=(8080 10051 5432 6379 5000)
PORT_NAMES=("Web UI" "Zabbix Server" "PostgreSQL" "Redis" "AI Webhook")
for i in "${!PORTS[@]}"; do
    PORT=${PORTS[$i]}
    NAME=${PORT_NAMES[$i]}
    if netstat -tuln 2>/dev/null | grep -q ":${PORT} " || ss -tuln 2>/dev/null | grep -q ":${PORT} "; then
        echo -e "  ${YELLOW}⚠${NC} Port ${PORT} (${NAME}) already in use"
        ((WARNINGS++))
    else
        echo -e "  ${GREEN}✓${NC} Port ${PORT} (${NAME}) available"
    fi
done

# Check 7: .env file exists
echo -n "Checking .env configuration... "
if [ -f "${PROJECT_DIR}/.env" ]; then
    echo -e "${GREEN}✓${NC} Found"
    
    # Check critical variables
    REQUIRED_VARS=("TELEGRAM_BOT_TOKEN" "GROQ_API_KEY")
    for VAR in "${REQUIRED_VARS[@]}"; do
        VALUE=$(grep "^${VAR}=" "${PROJECT_DIR}/.env" 2>/dev/null | cut -d'=' -f2)
        if [ -z "$VALUE" ] || [[ "$VALUE" == YOUR_* ]]; then
            echo -e "  ${YELLOW}⚠${NC} ${VAR} not configured"
            ((WARNINGS++))
        else
            echo -e "  ${GREEN}✓${NC} ${VAR} configured"
        fi
    done
else
    echo -e "${YELLOW}⚠${NC} Not found (will copy from .env.example)"
    ((WARNINGS++))
fi

# Check 8: Database secrets/env files
echo -n "Checking database configuration... "
if [ -f "${PROJECT_DIR}/env_vars/.env_db_pgsql" ]; then
    echo -e "${GREEN}✓${NC} .env_db_pgsql found"
elif [ -f "${PROJECT_DIR}/env_vars/.POSTGRES_PASSWORD" ]; then
    echo -e "${YELLOW}⚠${NC} Using legacy secrets (will auto-migrate)"
    ((WARNINGS++))
else
    echo -e "${YELLOW}⚠${NC} Not initialized (run generate-secrets.sh)"
    ((WARNINGS++))
fi

# Check 9: Docker user namespace (advanced)
echo -n "Checking Docker configuration... "
if docker info 2>/dev/null | grep -q "userns"; then
    echo -e "${YELLOW}⚠${NC} User namespace remapping detected"
    echo -e "  ${YELLOW}This may affect file permissions. Monitor for issues.${NC}"
    ((WARNINGS++))
else
    echo -e "${GREEN}✓${NC} Standard configuration"
fi

# Check 10: SELinux/AppArmor
echo -n "Checking security modules... "
if command -v getenforce >/dev/null 2>&1; then
    SELINUX_STATUS=$(getenforce 2>/dev/null || echo "N/A")
    if [ "$SELINUX_STATUS" = "Enforcing" ]; then
        echo -e "${YELLOW}⚠${NC} SELinux Enforcing (may require context adjustments)"
        ((WARNINGS++))
    else
        echo -e "${GREEN}✓${NC} SELinux: ${SELINUX_STATUS}"
    fi
elif command -v aa-status >/dev/null 2>&1 && aa-status --enabled 2>/dev/null; then
    echo -e "${YELLOW}⚠${NC} AppArmor enabled (usually fine)"
else
    echo -e "${GREEN}✓${NC} No active security modules"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Ready to deploy.${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ ${WARNINGS} warning(s) found. Deployment possible but review recommended.${NC}"
    exit 0
else
    echo -e "${RED}✗ ${ERRORS} error(s) and ${WARNINGS} warning(s) found.${NC}"
    echo -e "${RED}Please fix errors before deploying.${NC}"
    exit 1
fi

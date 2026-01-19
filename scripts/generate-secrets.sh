#!/bin/bash
# Zabbix Secrets Generation Script
# Generates secure random passwords and stores them in env_vars directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_VARS_DIR="${SCRIPT_DIR}/../env_vars"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Zabbix Secrets Generation${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Create env_vars directory if it doesn't exist
mkdir -p "${ENV_VARS_DIR}"

# Function to generate random password
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

# Function to create secret file
create_secret() {
    local secret_name=$1
    local secret_value=$2
    local secret_file="${ENV_VARS_DIR}/.${secret_name}"
    
    if [ -f "${secret_file}" ]; then
        echo -e "${YELLOW}⚠  ${secret_name} already exists, skipping...${NC}"
    else
        echo "${secret_value}" > "${secret_file}"
        chmod 600 "${secret_file}"
        echo -e "${GREEN}✓  Created ${secret_name}${NC}"
    fi
}

# Generate PostgreSQL credentials
echo -e "${YELLOW}Generating PostgreSQL credentials...${NC}"
POSTGRES_USER="zabbix"
POSTGRES_PASSWORD=$(generate_password)

create_secret "POSTGRES_USER" "${POSTGRES_USER}"
create_secret "POSTGRES_PASSWORD" "${POSTGRES_PASSWORD}"

# Generate MySQL credentials (for proxy if needed)
echo -e "${YELLOW}Generating MySQL credentials...${NC}"
MYSQL_USER="zabbix"
MYSQL_PASSWORD=$(generate_password)
MYSQL_ROOT_PASSWORD=$(generate_password)

create_secret "MYSQL_USER" "${MYSQL_USER}"
create_secret "MYSQL_PASSWORD" "${MYSQL_PASSWORD}"
create_secret "MYSQL_ROOT_PASSWORD" "${MYSQL_ROOT_PASSWORD}"

# Create environment file for Zabbix Server
ENV_SRV_FILE="${ENV_VARS_DIR}/.env_srv"
if [ -f "${ENV_SRV_FILE}" ]; then
    echo -e "${YELLOW}⚠  .env_srv already exists, skipping...${NC}"
else
    cat > "${ENV_SRV_FILE}" << EOF
# Zabbix Server Environment Variables

# Database Configuration
DB_SERVER_HOST=postgres-server
POSTGRES_DB=zabbix

# Performance Tuning
ZBX_CACHESIZE=128M
ZBX_HISTORYCACHESIZE=64M
ZBX_HISTORYINDEXCACHESIZE=16M
ZBX_TRENDCACHESIZE=32M
ZBX_VALUECACHESIZE=128M

# Process Configuration
ZBX_STARTPOLLERS=5
ZBX_IPMIPOLLERS=0
ZBX_STARTPOLLERSUNREACHABLE=1
ZBX_STARTTRAPPERS=5
ZBX_STARTPINGERS=1
ZBX_STARTDISCOVERERS=1
ZBX_STARTHTTPPOLLERS=1
ZBX_STARTESCALATORS=1
ZBX_STARTALERTERS=3
ZBX_STARTLLDPROCESSORS=2
ZBX_STARTPREPROCESSORS=3

# Timeout Configuration
ZBX_TIMEOUT=4
ZBX_UNREACHABLEPERIOD=45
ZBX_UNAVAILABLEDELAY=60
ZBX_UNREACHABLEDELAY=15

# Housekeeping
ZBX_HOUSEKEEPINGFREQUENCY=1
ZBX_MAXHOUSEKEEPERDELETE=5000

# TLS Configuration (optional)
# ZBX_TLSCAFILE=/var/lib/zabbix/ssl/ssl_ca/ca.crt
# ZBX_TLSCERTFILE=/var/lib/zabbix/ssl/certs/zabbix_server.crt
# ZBX_TLSKEYFILE=/var/lib/zabbix/ssl/keys/zabbix_server.key
EOF
    chmod 644 "${ENV_SRV_FILE}"
    echo -e "${GREEN}✓  Created .env_srv${NC}"
fi

# Create .env_db_pgsql file (Official Zabbix Docker pattern)
ENV_DB_PGSQL="${ENV_VARS_DIR}/.env_db_pgsql"
if [ -f "${ENV_DB_PGSQL}" ]; then
    echo -e "${YELLOW}⚠  .env_db_pgsql already exists, skipping...${NC}"
else
    # Read passwords from secret files
    POSTGRES_USER_VALUE=$(cat "${ENV_VARS_DIR}/.POSTGRES_USER" 2>/dev/null || echo "zabbix")
    POSTGRES_PASS_VALUE=$(cat "${ENV_VARS_DIR}/.POSTGRES_PASSWORD" 2>/dev/null || generate_password)
    
    cat > "${ENV_DB_PGSQL}" << EOF
# PostgreSQL Database Configuration
# This file follows official Zabbix Docker pattern
# See: https://github.com/zabbix/zabbix-docker

# Database connection
POSTGRES_USER=${POSTGRES_USER_VALUE}
POSTGRES_PASSWORD=${POSTGRES_PASS_VALUE}
POSTGRES_DB=zabbix

# Performance tuning
POSTGRES_SHARED_BUFFERS=256MB
POSTGRES_EFFECTIVE_CACHE_SIZE=512MB
POSTGRES_MAINTENANCE_WORK_MEM=128MB
POSTGRES_WAL_BUFFERS=8MB
POSTGRES_MAX_CONNECTIONS=100
EOF
    chmod 600 "${ENV_DB_PGSQL}"
    echo -e "${GREEN}✓  Created .env_db_pgsql${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Secrets Generation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Important: Secret files created with appropriate permissions.${NC}"
echo -e "${YELLOW}They are stored in: ${ENV_VARS_DIR}${NC}"
echo ""
echo -e "${RED}⚠  SECURITY WARNING: Keep these files secure and never commit to version control!${NC}"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo -e "  1. Configure your .env file with API keys"
echo -e "  2. Run: ./scripts/pre-flight-check.sh"
echo -e "  3. Run: ./scripts/init-setup.sh"
echo ""

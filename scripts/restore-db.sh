#!/bin/bash
# Zabbix Database Restore Script
# Restores Zabbix database from a backup file

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
BACKUP_DIR="${PROJECT_DIR}/zbx_env/backups"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    Zabbix Database Restore             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# List available backups
echo -e "${YELLOW}Available backups:${NC}"
BACKUPS=($(find "${BACKUP_DIR}" -name "zabbix_backup_*.sql.gz" -type f | sort -r))

if [ ${#BACKUPS[@]} -eq 0 ]; then
    echo -e "${RED}✗ No backups found in ${BACKUP_DIR}${NC}"
    exit 1
fi

for i in "${!BACKUPS[@]}"; do
    SIZE=$(du -h "${BACKUPS[$i]}" | cut -f1)
    FILENAME=$(basename "${BACKUPS[$i]}")
    echo -e "  ${BLUE}[$i]${NC} ${FILENAME} (${SIZE})"
done

echo ""
echo -e "${YELLOW}Enter backup number to restore (or 'q' to quit):${NC}"
read -r SELECTION

if [ "${SELECTION}" = "q" ]; then
    echo "Cancelled"
    exit 0
fi

if ! [[ "${SELECTION}" =~ ^[0-9]+$ ]] || [ "${SELECTION}" -ge "${#BACKUPS[@]}" ]; then
    echo -e "${RED}✗ Invalid selection${NC}"
    exit 1
fi

BACKUP_FILE="${BACKUPS[$SELECTION]}"

echo ""
echo -e "${RED}⚠  WARNING: This will replace the current database!${NC}"
echo -e "${YELLOW}Backup file: $(basename "${BACKUP_FILE}")${NC}"
echo -e "${YELLOW}Are you sure you want to continue? (yes/no):${NC}"
read -r CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    echo "Cancelled"
    exit 0
fi

cd "${PROJECT_DIR}"

echo ""
echo -e "${YELLOW}[1/4] Stopping Zabbix Server...${NC}"
docker compose stop zabbix-server
echo -e "${GREEN}✓ Zabbix Server stopped${NC}"

echo -e "${YELLOW}[2/4] Dropping existing database...${NC}"
docker exec zabbix-postgres psql -U zabbix -c "DROP DATABASE IF EXISTS zabbix;"
echo -e "${GREEN}✓ Database dropped${NC}"

echo -e "${YELLOW}[3/4] Creating new database...${NC}"
docker exec zabbix-postgres psql -U zabbix -c "CREATE DATABASE zabbix;"
echo -e "${GREEN}✓ Database created${NC}"

echo -e "${YELLOW}[4/4] Restoring from backup...${NC}"
gunzip -c "${BACKUP_FILE}" | docker exec -i zabbix-postgres psql -U zabbix -d zabbix
echo -e "${GREEN}✓ Database restored${NC}"

echo ""
echo -e "${YELLOW}Restarting services...${NC}"
docker compose start zabbix-server
echo -e "${GREEN}✓ Services restarted${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║    Restore Successful ✓                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}💡 It may take a minute for Zabbix Server to fully start.${NC}"
echo -e "${BLUE}   Use './scripts/health-check.sh' to verify.${NC}"
echo ""

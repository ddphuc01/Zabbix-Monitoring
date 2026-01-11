#!/bin/bash
# Zabbix Database Backup Script
# Creates timestamped backups of the Zabbix PostgreSQL database

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
BACKUP_DIR="${PROJECT_DIR}/zbx_env/backups"
RETENTION_DAYS=7

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/zabbix_backup_${TIMESTAMP}.sql.gz"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    Zabbix Database Backup              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}Starting backup...${NC}"
echo -e "Backup file: ${GREEN}${BACKUP_FILE}${NC}"
echo ""

# Perform backup
cd "${PROJECT_DIR}"

if docker exec zabbix-postgres pg_dump -U zabbix zabbix | gzip > "${BACKUP_FILE}"; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo -e "${GREEN}✓ Backup completed successfully${NC}"
    echo -e "  Size: ${BACKUP_SIZE}"
    echo ""
    
    # Cleanup old backups
    echo -e "${YELLOW}Cleaning up backups older than ${RETENTION_DAYS} days...${NC}"
    find "${BACKUP_DIR}" -name "zabbix_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
    
    REMAINING=$(find "${BACKUP_DIR}" -name "zabbix_backup_*.sql.gz" -type f | wc -l)
    echo -e "${GREEN}✓ Cleanup complete${NC}"
    echo -e "  Backups retained: ${REMAINING}"
    echo ""
    
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║    Backup Successful ✓                 ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    
    exit 0
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi

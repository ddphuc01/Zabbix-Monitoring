#!/bin/bash
# Fix Permissions Script
# Fixes permissions for env_vars secrets to resolve Docker permission issues

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_VARS_DIR="${SCRIPT_DIR}/../env_vars"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Fixing Permissions for Secrets${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if env_vars directory exists
if [ ! -d "${ENV_VARS_DIR}" ]; then
    echo -e "${RED}✗ env_vars directory not found!${NC}"
    echo -e "${YELLOW}  Run ./scripts/generate-secrets.sh first${NC}"
    exit 1
fi

# Fix permissions for secret files (600 for sensitive data)
echo -e "${YELLOW}Setting permissions for secret files...${NC}"
for file in "${ENV_VARS_DIR}"/.POSTGRES_* "${ENV_VARS_DIR}"/.MYSQL_*; do
    if [ -f "$file" ]; then
        chmod 600 "$file"
        echo -e "${GREEN}✓  Set 600 for $(basename $file)${NC}"
    fi
done

# Fix permissions for .env_srv (644 so Docker can read it)
if [ -f "${ENV_VARS_DIR}/.env_srv" ]; then
    chmod 644 "${ENV_VARS_DIR}/.env_srv"
    echo -e "${GREEN}✓  Set 644 for .env_srv${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Permissions Fixed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verify permissions
echo -e "${YELLOW}Current permissions:${NC}"
ls -la "${ENV_VARS_DIR}"/
echo ""

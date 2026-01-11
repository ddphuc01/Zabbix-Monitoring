#!/bin/bash
# Zabbix Health Check Script
# Verifies all Zabbix components are running correctly

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

cd "${PROJECT_DIR}"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    Zabbix Health Check Report         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

PASS=0
FAIL=0

# Function to check service
check_service() {
    local service_name=$1
    local container_name=$2
    
    if docker ps --filter "name=${container_name}" --filter "status=running" | grep -q "${container_name}"; then
        echo -e "${GREEN}✓${NC} ${service_name}: ${GREEN}Running${NC}"
        PASS=$((PASS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} ${service_name}: ${RED}Not Running${NC}"
        FAIL=$((FAIL + 1))
        return 1
    fi
}

# Function to check port
check_port() {
    local port=$1
    local service=$2
    
    if nc -z localhost ${port} 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Port ${port} (${service}): ${GREEN}Open${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} Port ${port} (${service}): ${YELLOW}Not accessible${NC}"
        return 1
    fi
}

echo -e "${YELLOW}[1/5] Container Status${NC}"
check_service "PostgreSQL Database" "zabbix-postgres"
check_service "Zabbix Server" "zabbix-server"
check_service "Web Interface" "zabbix-web"
check_service "Agent 2" "zabbix-agent2"
check_service "Java Gateway" "zabbix-java-gateway"
check_service "Web Service" "zabbix-web-service"
check_service "SNMP Traps" "zabbix-snmptraps"
echo ""

echo -e "${YELLOW}[2/5] Port Connectivity${NC}"
check_port 8080 "Web Interface HTTP"
check_port 10051 "Zabbix Server"
check_port 10060 "Agent 2"
check_port 10052 "Java Gateway"
check_port 10053 "Web Service"
echo ""

echo -e "${YELLOW}[3/5] Database Connectivity${NC}"
if docker exec zabbix-postgres pg_isready -U zabbix >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} PostgreSQL: ${GREEN}Accepting connections${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}✗${NC} PostgreSQL: ${RED}Not accepting connections${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""

echo -e "${YELLOW}[4/5] Zabbix Server Status${NC}"
if docker exec zabbix-server zabbix_server -R config_cache_reload 2>&1 | grep -q "sent successfully"; then
    echo -e "${GREEN}✓${NC} Zabbix Server: ${GREEN}Responding to commands${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${YELLOW}⚠${NC} Zabbix Server: ${YELLOW}May not be fully initialized${NC}"
fi
echo ""

echo -e "${YELLOW}[5/5] Web Interface Accessibility${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ 2>/dev/null || echo "000")
if [ "${HTTP_CODE}" = "200" ] || [ "${HTTP_CODE}" = "302" ]; then
    echo -e "${GREEN}✓${NC} Web Interface: ${GREEN}Accessible (HTTP ${HTTP_CODE})${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}✗${NC} Web Interface: ${RED}Not accessible (HTTP ${HTTP_CODE})${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
if [ $FAIL -eq 0 ]; then
    echo -e "${BLUE}║${NC}  Health Check: ${GREEN}ALL SYSTEMS OPERATIONAL${NC}  ${BLUE}║${NC}"
else
    echo -e "${BLUE}║${NC}  Health Check: ${YELLOW}ISSUES DETECTED${NC}          ${BLUE}║${NC}"
fi
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo -e "  Passed: ${GREEN}${PASS}${NC}  Failed: ${RED}${FAIL}${NC}"
echo ""

if [ $FAIL -gt 0 ]; then
    echo -e "${YELLOW}💡 Troubleshooting Commands:${NC}"
    echo -e "   View all logs:        ${BLUE}docker compose logs${NC}"
    echo -e "   View specific logs:   ${BLUE}docker compose logs <service-name>${NC}"
    echo -e "   Restart services:     ${BLUE}docker compose restart${NC}"
    echo -e "   Check service status: ${BLUE}docker compose ps${NC}"
    echo ""
    exit 1
fi

exit 0

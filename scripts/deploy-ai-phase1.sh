#!/bin/bash
# Deploy Phase 1 AI Integration
# Adds Gemini-powered alert analysis to existing Zabbix setup

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Zabbix AI Integration - Phase 1      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Check if running from correct directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.yml not found${NC}"
    echo "Please run this script from /home/phuc/zabbix-monitoring"
    exit 1
fi

# Check .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    exit 1
fi

# Check Gemini API key
if ! grep -q "GEMINI_API_KEY" .env; then
    echo -e "${YELLOW}⚠️  GEMINI_API_KEY not found in .env${NC}"
    read -p "Enter your Google Gemini API key: " api_key
    echo "" >> .env
    echo "# AI Integration" >> .env
    echo "GEMINI_API_KEY=$api_key" >> .env
    echo -e "${GREEN}✅ API key added to .env${NC}"
fi

echo -e "\n${YELLOW}[1/5] Building AI services...${NC}"
docker compose build ai-webhook

echo -e "\n${YELLOW}[2/5] Starting Redis cache...${NC}"
docker compose up -d redis
sleep 5

echo -e "\n${YELLOW}[3/5] Starting AI webhook handler...${NC}"
docker compose up -d ai-webhook
sleep 10

echo -e "\n${YELLOW}[4/5] Copying alert scripts to Zabbix...${NC}"
if [ -f "zabbix/alertscripts/ai_analysis.sh" ]; then
    docker cp zabbix/alertscripts/ai_analysis.sh zabbix-server:/usr/lib/zabbix/alertscripts/
    docker exec zabbix-server chmod +x /usr/lib/zabbix/alertscripts/ai_analysis.sh
    echo -e "${GREEN}✅ Alert script installed${NC}"
else
    echo -e "${RED}❌ Alert script not found${NC}"
fi

echo -e "\n${YELLOW}[5/5] Running health checks...${NC}"

# Check Redis
echo -n "  Redis: "
if docker exec zabbix-redis redis-cli ping | grep -q "PONG"; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
fi

# Check AI Webhook
echo -n "  AI Webhook: "
if curl -s http://localhost:5000/health | grep -q "healthy"; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
    echo -e "${YELLOW}    Check logs: docker compose logs ai-webhook${NC}"
fi

# Test Gemini connection
echo -n "  Gemini API: "
test_response=$(curl -s -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"trigger":"Test alert","host":"test","severity":"Info","value":"1"}' \
  --max-time 10)

if echo "$test_response" | grep -q "summary"; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
    echo "    Response: $test_response"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║    Phase 1 Deployment Complete! ✓     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📊 Services Status:${NC}"
docker compose ps redis ai-webhook

echo ""
echo -e "${BLUE}🔗 Next Steps:${NC}"
echo "  1. Read the guide: docs/AI_QUICKSTART.md"
echo "  2. Configure Zabbix action for AI analysis"
echo "  3. Test with real alerts"
echo ""
echo -e "${BLUE}📝 Useful Commands:${NC}"
echo "  View AI logs:    docker compose logs -f ai-webhook"
echo "  Check cache:     curl http://localhost:5000/stats"
echo "  Test analysis:   See AI_QUICKSTART.md for examples"
echo ""

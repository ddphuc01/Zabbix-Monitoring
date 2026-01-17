# Zabbix AI Alert Analysis - Deployment Guide

## Quick Start

This webhook service is containerized with Docker. To deploy the updated Vietnamese AI analysis:

### 1. Build and Deploy

```bash
cd /home/phuc/zabbix-monitoring/ai-services/webhook-handler

# Rebuild the Docker container
docker-compose build webhook-handler  # or your compose service name

# Restart the service
docker-compose up -d webhook-handler
```

### 2. Environment Variables Required

Ensure these are set in your docker-compose.yml or .env:

```bash
GROQ_API_KEY=your_groq_api_key_here
REDIS_HOST=redis
REDIS_PORT=6379
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### 3. Test the Service

#### Option A: Using Python Test Suite (Full Tests)

```bash
# Inside the container
docker exec -it <container-name> python3 test_groq_integration.py
```

#### Option B: Using Curl (Quick Tests)

```bash
# Test CPU Alert
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_name": "High CPU usage on web-server-prod-01",
    "host_name": "web-server-prod-01",
    "trigger_severity": "High",
    "trigger_value": "92"
  }'
```

#### Option C: Using Test Script

```bash
./test_webhook.sh
```

## What's New in This Version

### ✨ Comprehensive Vietnamese Prompt
- **Detailed analysis framework** for CPU, Memory, Disk, and Network alerts
- **Special rules** for spike vs trend detection, alert correlation, and false positives
- **Service-aware recommendations** for nginx, MySQL, Redis, Docker/Kubernetes
- **Environment-aware severity** (production vs staging vs testing)

### 🔧 Enhanced Features
1. **Improved Ansible Data Parsing**
   - JSON extraction from Ansible playbook output
   - Structured metrics parsing with fallback to raw output
   
2. **Service Context Extraction**
   - Automatically detects environment from hostname (prod/staging/test)
   - Identifies app type (web/database/api/cache)
   - Adjusts urgency based on severity level

3. **Better Alert Analysis**
   - Handles both dict and string Ansible data
   - Includes service_info in AI analysis context
   - More specific logging with environment details

### 📋 Alert Type Examples

**CPU Alert Output:**
```
🔴 [HIGH] CPU ALERT: web-server-prod-01

📊 Tình trạng: 92% / 80%

⚡ Nguyên nhân: nginx đang xử lý spike traffic (45% CPU)
- Có ~500 connection từ client
- Likely: API endpoint chậm, client đợi response

✅ Khuyến nghị:
1. Tăng worker processes của nginx từ 4 → 8 (tạm thời)
2. Check slow query log nếu backend là PHP/Python
3. Monitor 10 phút tiếp theo

⏱️ Urgency: Monitor 10 phút / Tối ưu configuration
```

**Memory Alert Output:**
```
🔴 [CRITICAL] MEMORY ALERT: db-server-prod-01

📊 Tình trạng: 95% / 85%

💾 Chi tiết:
- Used: 14.5 GB / Total: 16 GB
- Swap: 51% (⚠️)
- Available: 600 MB

⚡ Nguyên nhân:
- PostgreSQL sử dụng 9.6 GB
- Query đột ngột hoặc memory leak

✅ Khuyến nghị:
1. Kiểm tra slow query log
2. Restart PostgreSQL nếu memory leak
3. Monitor swap usage

⏱️ Urgency: Restart trong maintenance window
```

## Verification Checklist

- [x] Updated SYSTEM_PROMPT with comprehensive Vietnamese framework
- [x] Enhanced Ansible data parsing with JSON extraction
- [x] Added service_info context extraction
- [x] Created comprehensive test suite (4 alert types)
- [x] Created quick test scripts (curl + bash)
- [ ] Deploy to Docker and test with real Groq API
- [ ] Trigger real Zabbix alert to test end-to-end
- [ ] Verify Telegram message formatting

## Monitoring & Troubleshooting

### Check Logs
```bash
docker logs -f <webhook-container-name>
```

### Health Check
```bash
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "zabbix-ai-webhook-groq",
  "groq_configured": true,
  "redis_connected": true
}
```

### Common Issues

1. **"Groq client not initialized"**
   - Check GROQ_API_KEY environment variable is set
   
2. **"Ansible execution error"**
   - Verify Ansible playbook path is correct
   - Check inventory file has the target hosts
   - Ensure SSH access to monitored hosts

3. **"Redis connection failed"**
   - Verify redis container is running
   - Check REDIS_HOST and REDIS_PORT settings

## Groq API Limits

- **Rate limit**: 30 requests/minute
- **Max tokens**: 200 per response (optimized for Telegram)
- **Temperature**: 0.3 (consistent output)
- **Caching**: Enabled via Redis (1-hour TTL)

The caching significantly reduces API calls for repeated alerts.

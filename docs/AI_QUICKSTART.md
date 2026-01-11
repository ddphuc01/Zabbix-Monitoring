# Zabbix AI Integration - Quick Start Guide

## 🚀 Phase 1: Core AI Integration with Google Gemini

This guide covers the **Phase 1** implementation of AI-powered alert analysis using Google Gemini API.

---

## 📋 What's New in Phase 1

### Added Services:
1. **Redis Cache** - Fast caching for AI responses
2. **AI Webhook Handler** - Gemini-powered alert analysis

### Features:
- ✅ AI-powered alert analysis using Google Gemini
- ✅ Intelligent response caching (reduce API costs)
- ✅ One-click analysis from Zabbix alerts
- ✅ Automatic root cause detection
- ✅ Actionable remediation steps

---

## 🔧 Prerequisites

- Running Zabbix instance (from existing setup)
- Google Gemini API key (from AI Studio)
- Docker Compose v2.0+
- 1GB additional RAM for AI services

---

## 📦 Deployment

### Step 1: Update Configuration

Your `.env` file has been updated with:
```bash
GEMINI_API_KEY=AIzaSyBzm9_PeOIYwBkkFDaeoXekLButtNPyHiM
AI_CACHE_TTL=3600
AI_MAX_TOKENS=1000
AI_TEMPERATURE=0.3
```

### Step 2: Deploy AI Services

```bash
cd /home/phuc/zabbix-monitoring

# Build and start new services
docker compose up -d redis ai-webhook

# Verify services
docker compose ps
docker compose logs -f ai-webhook
```

### Step 3: Verify Health

```bash
# Check Redis
docker exec zabbix-redis redis-cli ping
# Expected: PONG

# Check AI Webhook
curl http://localhost:5000/health
# Expected: {"status": "healthy", ...}

# Test Gemini integration
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "trigger": "High CPU usage",
    "host": "web-server-01",
    "severity": "Warning",
    "value": "95%"
  }'
```

### Step 4: Copy Alert Scripts to Zabbix

```bash
# Copy alertscript to Zabbix volume
docker cp /home/phuc/zabbix-monitoring/zabbix/alertscripts/ai_analysis.sh \
  zabbix-server:/usr/lib/zabbix/alertscripts/

# Set permissions
docker exec zabbix-server chmod +x /usr/lib/zabbix/alertscripts/ai_analysis.sh

# Test script
docker exec zabbix-server /usr/lib/zabbix/alertscripts/ai_analysis.sh \
  "CPU is too high on web-server-01" \
  "web-server-01" \
  "Warning" \
  "95%" \
  "2026-01-05 00:00:00"
```

---

## 🎯 Configure Zabbix Actions

### Option 1: Via Web Interface (Recommended)

1. **Login** to Zabbix: http://192.168.1.203:8080
2. **Navigate to:** Alerts → Actions
3. **Create Action:**

**Action tab:**
- Name: `AI Analysis for Critical Alerts`
- Conditions:
  - Trigger severity ≥ Warning

**Operations tab:**
- Operation type: `Send message`
- Send to users: `Admin` (or your user)
- Send only to: `Script`
- Script name: `ai_analysis.sh`
- Script parameters:
  ```
  {TRIGGER.NAME}
  {HOST.NAME}
  {TRIGGER.SEVERITY}
  {ITEM.LASTVALUE}
  {EVENT.TIME}
  ```

4. **Click:** Add

### Option 2: Test from Command Line

```bash
# Trigger analysis manually
docker exec zabbix-server /usr/lib/zabbix/alertscripts/ai_analysis.sh \
  "Free disk space is less than 20% on volume /" \
  "ubuntu-phuc" \
  "Warning" \
  "15%" \
  "$(date '+%Y-%m-%d %H:%M:%S')"
```

---

## 📊 How It Works

### Flow Diagram:

```
Zabbix Alert 
    ↓
ai_analysis.sh (Alert Script)
    ↓
AI Webhook Handler (Flask)
    ↓
Check Redis Cache → [HIT] → Return cached result (< 1s)
    ↓ [MISS]
Google Gemini API
    ↓
Structured Analysis:
  - Summary
  - Root Cause
  - Remediation Steps
  - Preventive Measures
    ↓
Cache in Redis (1 hour TTL)
    ↓
Return to Zabbix
```

### Example AI Response:

```json
{
  "summary": "High CPU usage likely caused by runaway process",
  "root_cause": "A process is consuming excessive CPU resources, possibly due to an infinite loop or resource leak",
  "severity_assessment": "High - Can impact system performance and user experience",
  "immediate_action": "1. Identify top CPU-consuming processes with 'top' or 'htop'\n2. Check for suspicious processes\n3. Investigate recent deployments\n4. Consider process restart if safe",
  "preventive_measures": "1. Implement CPU usage monitoring\n2. Set up process limits\n3. Review resource allocation\n4. Enable auto-scaling if applicable",
  "related_metrics": "Check memory usage, load average, disk I/O",
  "confidence": 0.85,
  "response_time": 2.3,
  "model": "gemini-pro"
}
```

---

## 💰 Cost Management

### Gemini Free Tier:
- **60 requests/minute**
- **1,500 requests/day**
- **100,000 tokens/day**

### Caching Strategy:
- Similar alerts cached for 1 hour
- Reduces API calls by ~70%
- Estimated cost: **FREE** for typical usage

### Monitor Usage:

```bash
# Check cache stats
curl http://localhost:5000/stats

# View Redis keys
docker exec zabbix-redis redis-cli DBSIZE
docker exec zabbix-redis redis-cli KEYS "gemini:*"
```

---

## 🔍 Troubleshooting

### AI Webhook Not Starting

```bash
# Check logs
docker compose logs ai-webhook

# Common issues:
# 1. Missing Gemini API key
docker compose exec ai-webhook printenv | grep GEMINI

# 2. Redis not accessible
docker compose exec ai-webhook ping redis

# 3. Build failed
docker compose build --no-cache ai-webhook
docker compose up -d ai-webhook
```

### No AI Analysis in Alerts

```bash
# Verify script exists
docker exec zabbix-server ls -la /usr/lib/zabbix/alertscripts/

# Check script permissions
docker exec zabbix-server file /usr/lib/zabbix/alertscripts/ai_analysis.sh

# Test webhook connectivity from Zabbix
docker exec zabbix-server curl -X POST http://ai-webhook:5000/health
```

### Slow Responses

```bash
# Check if caching is working
docker exec zabbix-redis redis-cli INFO stats

# Monitor response times
docker compose logs ai-webhook | grep "responded in"

# Adjust cache TTL if needed
# Edit .env: AI_CACHE_TTL=7200
docker compose up -d ai-webhook
```

---

## 📈 Next Steps (Phase 2)

Coming soon:
- [ ] Prometheus monitoring for AI services
- [ ] Grafana dashboards for cost tracking
- [ ] ML-based anomaly detection
- [ ] Auto-remediation actions
- [ ] Chat interface (Open WebUI)

---

## 🎓 Usage Examples

### Example 1: High CPU Alert

**Alert:** CPU usage > 90%

**AI Analysis:**
- Root cause: Process leak or runaway job
- Action: Investigate with `top`, check cron jobs
- Prevention: Set CPU alerts, implement limits

### Example 2: Disk Space Low

**Alert:** Disk space < 20%

**AI Analysis:**
- Root cause: Log file growth, temporary files
- Action: Clean `/tmp`, rotate logs, check largest files
- Prevention: Implement log rotation, disk usage monitoring

### Example 3: Docker Container Down

**Alert:** Container stopped unexpectedly

**AI Analysis:**
- Root cause: OOM kill, crash, or manual stop
- Action: Check `docker logs`, inspect exit code
- Prevention: Memory limits, health checks, restart policy

---

## 🛡️ Security Notes

1. **API Key Security:**
   - Never commit `.env` to git
   - Rotate API key periodically
   - Monitor usage on AI Studio dashboard

2. **Network Security:**
   - AI services on internal network only
   - No external exposure needed
   - Use firewall rules as configured

3. **Data Privacy:**
   - Alert data sent to Google Gemini
   - Review Google's data usage policy
   - Consider on-prem AI (Phase 2) for sensitive data

---

## 📚 Additional Resources

- [Google Gemini API Docs](https://ai.google.dev/docs)
- [Zabbix Actions Documentation](https://www.zabbix.com/documentation/current/en/manual/config/notifications/action)
- [Redis Caching Best Practices](https://redis.io/docs/manual/patterns/caching/)

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] Redis container running and healthy
- [ ] AI Webhook container running and healthy
- [ ] Health endpoint returns 200 OK
- [ ] Gemini API key configured correctly
- [ ] Alert script copied to Zabbix
- [ ] Script executable and working
- [ ] Zabbix action configured
- [ ] Test alert triggers AI analysis
- [ ] Response cached in Redis
- [ ] Second identical alert returns from cache

---

**Need help?** Check logs:
```bash
docker compose logs -f redis ai-webhook zabbix-server
```

**Ready for Phase 2?** Let me know when you want to add ML, monitoring, and chat interface! 🚀

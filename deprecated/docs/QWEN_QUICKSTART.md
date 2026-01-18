# Qwen CLI Integration - Simplified Setup

## 🎯 Overview

Hệ thống đã được đơn giản hóa để **chỉ sử dụng Qwen CLI local** (không OAuth, không Gemini).

**Setup:**
- 🧠 **Qwen CLI** - Local subprocess calls (no API limits)
- 📝 **telegram_qwen.sh** - Simple, clean alert script
- ❌ **No Gemini** - Removed (key deleted)
- ❌ **No OAuth** - Using qwen CLI directly

---

## 🚀 Deployed Components

### 1. Qwen CLI Wrapper
- **File:** `qwen_wrapper.py` (original CLI-based)
- **Method:** Subprocess call to `/usr/local/bin/qwen`
- **No rate limits** (local execution)
- **No API keys needed**

### 2. Alert Script
- **File:** `telegram_qwen.sh`
- **Location:** `/usr/lib/zabbix/alertscripts/`
- **Features:**
  - Calls Qwen CLI only
  - No fallback needed
  - Clean, simple code
  - OpenAI-compatible format

---

## ✅ Current Status

```bash
# Container status
docker ps | grep qwen
zabbix-qwen-wrapper  running  Up 2 minutes (healthy)

# Health check
curl http://localhost:11434/health
{
  "status": "ok",
  "backend": "qwen",
  "version": "0.5.2"
}

# Alert script deployed
ls -la /home/phuc/zabbix-monitoring/zbx_env/usr/lib/zabbix/alertscripts/telegram_qwen.sh
-rwxr-xr-x telegram_qwen.sh
```

---

## 🧪 Testing

### Manual Test
```bash
docker exec zabbix-server /usr/lib/zabbix/alertscripts/telegram_qwen.sh \
  "-5285412393" \
  "Test Alert - Disk Space Low" \
  "ubuntu-phuc" \
  "High" \
  "15%" \
  "2026-01-13 22:22:00"
```

**Result:** ✅ Success (exit code 0)

---

## 📋 Configuration in Zabbix

### Create/Update Action

1. **Login to Zabbix:** http://192.168.1.203:8080
2. **Navigate to:** Alerts → Actions → Trigger actions
3. **Create new action** (or modify existing):

**Name:** `Qwen AI Analysis`

**Operations:**
- Operation type: `Send message`
- Send to users: `Admin` (or your user)
- Send only to: `Script`
- Script name: **`telegram_qwen.sh`**
- Script parameters:
  ```
  -5285412393
  {TRIGGER.NAME}
  {HOST.NAME}
  {TRIGGER.SEVERITY}
  {ITEM.LASTVALUE}
  {EVENT.TIME}
  ```

4. **Save**

---

## 📊 Expected Telegram Message

```
🚨 Alert Title

🟠 High | ubuntu-phuc | ⏰ 2026-01-13 22:22:00

━━━━━━━━━━━━━━━━━━━━━━
🧠 Qwen • 85%

🔍 Nguyên nhân:
[Qwen analysis of root cause]

⚡ Giải pháp:
[Qwen recommendations with specific commands]
━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🔧 Troubleshooting

### Script Not found
```bash
# Verify script exists
docker exec zabbix-server ls -la /usr/lib/zabbix/alertscripts/ | grep qwen

# If missing, copy again:
cp /home/phuc/zabbix-monitoring/zabbix/alertscripts/telegram_qwen.sh \
   /home/phuc/zabbix-monitoring/zbx_env/usr/lib/zabbix/alertscripts/
```

### Qwen Wrapper Not Responding
```bash
# Check container
docker ps | grep qwen

# Check logs
docker compose logs qwen-wrapper

# Restart if needed
docker compose restart qwen-wrapper
```

### No Telegram Message
```bash
# Check Telegram bot token in .env
grep TELEGRAM_BOT_TOKEN /home/phuc/zabbix-monitoring/.env

# Test manually:
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=-5285412393" \
  -d "text=Test message"
```

---

## 🎯 Advantages of This Setup

✅ **Simple** - No OAuth complexity  
✅ **No rate limits** - Local CLI execution  
✅ **No API keys** - Qwen CLI uses OAuth creds from file  
✅ **Fast** - No network latency to cloud APIs  
✅ **Reliable** - No dependency on external services  
✅ **Clean code** - Single model, no fallback logic needed

---

## 📝 Files Modified

### Core Files:
1. **Dockerfile** - Restored Node.js + qwen CLI installation
2. **docker-compose.yml** - Removed OAuth env vars
3. **requirements.txt** - Removed httpx, tenacity
4. **telegram_qwen.sh** - New simple alert script

### Removed:
- `qwen_oauth_wrapper.py` (not used)
- `telegram_ai_v4.sh` (dual-model, not needed)
- Gemini integration (key deleted)

---

## 🚀 Next Steps

1. **Configure Zabbix Action** - Use `telegram_qwen.sh` script
2. **Test with real alert** - Wait for actual monitoring trigger
3. **Monitor Telegram** - Verify messages received
4. **Tune prompts** - Adjust system prompt if needed

---

## 📚 Resources

- **Qwen CLI Docs:** https://qwenlm.github.io/
- **Wrapper Code:** `/home/phuc/zabbix-monitoring/ai-services/qwen-wrapper/qwen_wrapper.py`
- **Alert Script:** `/home/phuc/zabbix-monitoring/zabbix/alertscripts/telegram_qwen.sh`
- **Container Logs:** `docker compose logs -f qwen-wrapper`

---

**Setup Date:** 2026-01-13  
**Status:** ✅ Operational  
**Complexity:** Low (simplified from dual-model OAuth)

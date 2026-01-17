# 🤖 Interactive Telegram Bot - Quick Start

## ✅ Status: DEPLOYED

**Container:** `zabbix-telegram-bot` ✅ Running  
**Status:** Healthy, polling Telegram API  
**Logs:** Bot started successfully

---

## 🚀 First Steps

### 1. Add Bot to Telegram

Find your bot on Telegram (you already have it - same token as alerts).

### 2. Send `/start` Command

Open bot chat and send:
```
/start
```

**Expected Response:**
```
🤖 Zabbix AI Bot

Welcome [Your Name]!
Your role: VIEWER

Available Commands:
/help - Show all commands
/list - Active alerts
/status - System status

Your ID: 123456789
```

**Copy your User ID** from this message!

---

### 3. Configure Your Role

**Edit bot.py:**
```bash
# In container or locally before rebuild
vi /home/phuc/zabbix-monitoring/ai-services/telegram-bot/bot.py
```

**Find line ~30 and add your ID:**
```python
USER_ROLES = {
    123456789: 'ADMIN',  # Replace with YOUR ID from /start
    # Add more users:
    # 987654321: 'OPERATOR',
}
```

**Rebuild & restart:**
```bash
docker compose build telegram-bot
docker compose restart telegram-bot
```

**Send `/start` again** - Role should now show ADMIN ✅

---

## 📋 Test Commands

### Basic Commands

```
/help       # Show command reference
/list       # Show active alerts
```

### Test Alert with Buttons

```bash
# Copy interactive script to Zabbix
cp /home/phuc/zabbix-monitoring/zabbix/alertscripts/telegram_interactive.sh \
   /home/phuc/zabbix-monitoring/zbx_env/usr/lib/zabbix/alertscripts/

# Make executable
chmod +x /home/phuc/zabbix-monitoring/zbx_env/usr/lib/zabbix/alertscripts/telegram_interactive.sh

# Test send
docker exec zabbix-server /usr/lib/zabbix/alertscripts/telegram_interactive.sh \
  "-5285412393" \
  "TEST INTERACTIVE ALERT" \
  "test-host" \
  "High" \
  "Test value" \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "TEST$(date +%s)"
```

**Expected Telegram Message:**
```
🚨 TEST INTERACTIVE ALERT

🟠 High | test-host | ⏰ [timestamp]

━━━━━━━━━━━━━━━━━━━━━━
🧠 AI Analysis • [confidence]%

[AI analysis here]

Alert ID: TEST1736...

┌────────────────┬───────────────┐
│ 🔍 Diagnostic  │ 🔧 Auto-Fix  │
├────────────────┼───────────────┤
│ 🔄 Restart     │ 📊 Metrics   │
├────────────────┼───────────────┤
│ ✅ Acknowledge │ 🔇 Ignore    │
└────────────────┴───────────────┘
```

### Test Buttons

**Click any button** (e.g., "🔍 Diagnostic")

**If VIEWER role:**
```
🔍 Running diagnostic for #TEST...

[Diagnostic results]
```

**If not authorized:**
```
🔒 Permission denied. fix requires Admin,  Operator role.
```

---

## 🔐 Role Permissions

| Action | ADMIN | OPERATOR | VIEWER |
|--------|-------|----------|--------|
| View alerts | ✅ | ✅ | ✅ |
| Run diagnostic | ✅ | ✅ | ✅ |
| Acknowledge | ✅ | ✅ | ✅ |
| Restart service | ✅ | ✅ | ❌ |
| Auto-fix | ✅ | ❌ | ❌ |
| Ignore alerts | ✅ | ✅ | ❌ |

---

## 🔧 Update Zabbix to Use Interactive Script

### Option 1: Update Global Script

1. Login to Zabbix: http://192.168.1.203:8080
2. Alerts → Scripts
3. Edit `telegram_qwen.sh` script
4. Change to: `/usr/lib/zabbix/alertscripts/telegram_interactive.sh`
5. Add 7th parameter: `{EVENT.ID}`
6. Save

### Option 2: Create New Action

1. Create new action: "Interactive AI Alerts"
2. Use script: `telegram_interactive.sh`
3. Parameters (7 total):
   ```
   -5285412393
   {TRIGGER.NAME}
   {HOST.NAME}
   {TRIGGER.SEVERITY}
   {ITEM.LASTVALUE}
   {EVENT.TIME}
   {EVENT.ID}
   ```
4. Enable action

---

## ✅ Verification Checklist

- [ ] Bot responds to `/start`
- [ ] User ID obtained
- [ ] Role configured in bot.py
- [ ] Bot rebuilt and restarted
- [ ] Role shows correctly in `/start`
- [ ] `/help` shows available commands
- [ ] Test alert sent with buttons
- [ ] Buttons appear in message
- [ ] Clicking button triggers response
- [ ] Authorization works correctly
- [ ] Zabbix configured to use interactive script

---

## 🎯 Next Steps

### Phase 1 Complete When:
- ✅ Bot deployed and running
- ⏳ Buttons trigger actions
- ⏳ Authorization verified
- ⏳ Real alerts use interactive script

### Phase 2 Features:
- Progress animations
- Natural language commands
- Batch operations
- Analytics & reporting

---

## 🐛 Troubleshooting

### Bot Not Responding

```bash
# Check container
docker compose ps | grep telegram-bot

# Check logs
docker compose logs --tail=50 telegram-bot

# Restart if needed
docker compose restart telegram-bot
```

### Buttons Not Clickable

**Issue:** Buttons show as plain text

**Cause:** Old Telegram app or wrong format

**Fix:** Update Telegram app, check inline_keyboard JSON

### Permission Denied

**Issue:** "Permission denied" on all actions

**Fix:** Configure your role in `USER_ROLES`

---

**Status:** Bot live and ready! 🚀  
**Test it now:** Send `/start` to your bot!

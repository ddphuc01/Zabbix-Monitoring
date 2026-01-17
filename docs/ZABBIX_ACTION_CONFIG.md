# Cấu Hình Zabbix Action Cho Qwen

## 📋 Steps để Configure

### Bước 1: Mở Zabbix Web Interface

URL: http://192.168.1.203:8080

### Bước 2: Navigate to Actions

1. Click **Alerts** (menu trái)
2. Click **Actions**  
3. Click **Trigger actions** tab

### Bước 3: Edit Action "AI Alert Analysis"

Click vào action name để edit hoặc create new:

![Zabbix Actions Page](file:///root/.gemini/antigravity/brain/16ef4f0b-74c4-4465-8780-e945057af667/zabbix_trigger_actions_page_1768318660887.png)

---

## ⚙️ Action Configuration

### Tab: Action

**Name:** `Qwen AI Alert Analysis`

**Conditions:**
```
Trigger severity >= Warning
```

*(hoặc customize theo nhu cầu)*

---

### Tab: Operations

**Operations:**

#### Operation 1: Send Telegram Alert

- **Operation type:** Send message
- **Send to users:** Admin (hoặc user group cần notify)
- **Send only to:** Script
  
**Script configuration:**

**Script name:** `telegram_qwen.sh`

**Script parameters:** (theo thứ tự)
```
1. -5285412393                    (TELEGRAM_CHAT_ID - your chat ID)
2. {TRIGGER.NAME}                 (Alert title)
3. {HOST.NAME}                    (Host name)  
4. {TRIGGER.SEVERITY}             (Severity level)
5. {ITEM.LASTVALUE}               (Current value)
6. {EVENT.TIME}                   (Event timestamp)
```

**Visual format trong Zabbix:**
```
Parameter 1:  -5285412393
Parameter 2:  {TRIGGER.NAME}
Parameter 3:  {HOST.NAME}
Parameter 4:  {TRIGGER.SEVERITY}
Parameter 5:  {ITEM.LASTVALUE}
Parameter 6:  {EVENT.TIME}
```

---

### Tab: Recovery operations (Optional)

Có thể thêm notification khi alert recovered:

**Script:** `telegram_qwen.sh`
**Parameters:** (same as above)

---

### Tab: Update operations (Optional)

Notification khi alert được update/acknowledge.

---

## ✅ Save Configuration

1. Click **Update** (nếu edit) hoặc **Add** (nếu tạo mới)
2. Verify action status = **Enabled**

---

## 🧪 Test Alert

### Option 1: Trigger Real Monitoring Issue

Gây một condition trigger alert thật:

```bash
# Ví dụ: Fake high CPU on monitored host
stress --cpu 4 --timeout 60s
```

### Option 2: Manual Problem Creation (Recommended for testing)

1. Go to **Monitoring → Problems**
2. Có thể manually trigger test item
3. Hoặc tạo một item test với threshold thấp để dễ trigger

### Option 3: Test from Zabbix UI

1. **Monitoring → Latest data**
2. Tìm một item có giá trị gần threshold
3. Temporarily lower threshold để trigger alert
4. Wait for alert
5. Restore threshold

---

## 📱 Expected Telegram Message

Khi alert triggers, bạn sẽ nhận message:

```
🚨 [Alert Title]

[Emoji] [Severity] | [Host] | ⏰ [Time]

━━━━━━━━━━━━━━━━━━━━━━
🧠 Qwen • [Confidence]%

🔍 Nguyên nhân:
[Qwen AI analysis of root cause]

⚡ Giải pháp:
[Qwen recommendations with commands]
━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🔍 Troubleshooting

### Check Alert Script Available

```bash
docker exec zabbix-server ls -la /usr/lib/zabbix/alertscripts/ | grep qwen
# Should show: telegram_qwen.sh
```

### Check Action Enabled

Zabbix UI: Actions list → Status column should show "Enabled"

### View Qwen Wrapper Logs

```bash
docker compose logs -f qwen-wrapper
# Should see: "Calling qwen... prompt length: XXX chars"
```

### Test Script Manually

```bash
docker exec zabbix-server /usr/lib/zabbix/alertscripts/telegram_qwen.sh \
  "-5285412393" \
  "Test Alert" \
  "test-host" \
  "Warning" \
  "95%" \
  "$(date '+%Y-%m-%d %H:%M:%S')"
```

### Check Telegram Bot

```bash
# Verify bot token in .env
grep TELEGRAM_BOT_TOKEN /home/phuc/zabbix-monitoring/.env

# Test bot manually
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
```

---

## ✅ Verification Checklist

After configuration:

- [ ] Action created/updated with script name `telegram_qwen.sh`
- [ ] All 6 parameters configured correctly
- [ ] Action status = Enabled
- [ ] Qwen wrapper container running and healthy
- [ ] Manual test script works
- [ ] Alert triggered from Zabbix
- [ ] Telegram message received with Qwen analysis
- [ ] Message format looks good

---

## 📊 Monitor Performance

### Check Qwen Usage

```bash
# See API calls
docker compose logs qwen-wrapper | grep "Calling qwen"

# Count today's requests
docker compose logs qwen-wrapper | grep "$(date +%Y-%m-%d)" | grep "Calling qwen" | wc -l
```

### Alert Statistics

Zabbix UI: **Reports → Action log**
- Filter by Action name
- Check success rate
- View execution times

---

**Ready to go!** 🚀

Once configured, all Zabbix alerts matching your conditions will automatically get AI analysis from Qwen and send to Telegram!

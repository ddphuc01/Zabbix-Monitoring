# 📘 Hướng Dẫn Cấu Hình Alert và AI Chat Telegram - Từng Bước

**Để UAT Server** | Cập nhật: 20/01/2026

---

## 📋 Mục Lục

1. [Tổng Quan](#1-tổng-quan)
2. [Yêu Cầu Chuẩn Bị](#2-yêu-cầu-chuẩn-bị)
3. [Cấu Hình Telegram Bot](#3-cấu-hình-telegram-bot)
4. [Cấu Hình Zabbix Webhook](#4-cấu-hình-zabbix-webhook)
5. [Cấu Hìn Actions Zabbix](#5-cấu-hình-actions)
6. [Test và Verify](#6-test-và-verify)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Tổng Quan

### Hệ Thống Alert Hoạt Động Như Thế Nào?

```
Zabbix Trigger → Action → Webhook (ai-webhook:5000) 
                               ↓
                         AI Analysis (Groq)
                               ↓
                         Telegram Bot → Bạn nhận alert
                               ↓
                         Click nút → Ansible thực thi
```

### Các Thành Phần:

- **Zabbix Server**: Giám sát và phát hiện vấn đề
- **AI Webhook**: Phân tích lỗi bằng Groq AI
- **Telegram Bot**: Gửi alert và nhận lệnh từ bạn
- **Ansible**: Thực thi remediation tự động

---

## 2. Yêu Cầu Chuẩn Bị

### 2.1. Kiểm Tra Services Đang Chạy

```bash
cd /home/pnj/Zabbix-Monitoring
docker compose ps
```

**Phải thấy các container sau đang chạy:**
- ✅ `zabbix-server` - healthy
- ✅ `zabbix-web` - healthy
- ✅ `zabbix-ai-webhook` - healthy
- ✅ `zabbix-redis` - healthy (cache cho AI)

### 2.2. Kiểm Tra Biến Môi Trường

```bash
# Xem file .env
cat .env | grep -E "TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID|GROQ_API_KEY"
```



---

## 3. Cấu Hình Telegram Bot

### 3.1. Test Bot Hoạt Động

**Bước 1:** Mở Telegram → Tìm bot của bạn (token đã có ở trên)

**Bước 2:** Gửi lệnh:
```
/start
```

**Bước 3:** Bot sẽ trả lời:
```
🤖 Zabbix AI Bot

Welcome [Tên của bạn]!
Your role: VIEWER

Available Commands:
/help - Show all commands
/list - Active alerts
/status - System status

Your ID: 1234567890
```

> 📝 **QUAN TRỌNG**: Copy số **Your ID** này!

### 3.2. Cấu Hình Role Admin Cho Bạn

**Bước 1:** Chỉnh sửa file bot.py:
```bash
nano /home/pnj/Zabbix-Monitoring/ai-services/telegram-bot/bot.py
```

**Bước 2:** Tìm dòng có `USER_ROLES =` (khoảng dòng 30-35), sửa thành:
```python
USER_ROLES = {
    1234567890: 'ADMIN',  # Thay 1234567890 bằng ID của bạn từ /start
    # Có thể thêm user khác:
    # 9876543210: 'OPERATOR',
}
```

**Bước 3:** Lưu file (Ctrl+O, Enter, Ctrl+X)

**Bước 4:** Rebuild container:
```bash
cd /home/pnj/Zabbix-Monitoring
docker compose build telegram-bot
docker compose restart telegram-bot
```

**Bước 5:** Test lại - gửi `/start` trong Telegram

**Kết quả mong đợi:**
```
Your role: ADMIN  ← Đã thay đổi từ VIEWER
```

### 3.3. Test Commands

Thử các lệnh sau trong Telegram:

```
/help       # Xem danh sách lệnh
/list       # Danh sách alert hiện tại
/status     # Trạng thái hệ thống
```

---

## 4. Cấu Hình Zabbix Webhook

### 4.1. Truy Cập Zabbix UI

```
URL: http://<IP-UAT-SERVER>:8080
Username: Admin
Password: zabbix  (hoặc password bạn đã đổi)
```

### 4.2. Tạo Media Type (Webhook)

**Bước 1:** Vào menu:
```
Administration → Media types → Create media type
```

![Danh sách Media Types](file:///home/phuc/zabbix-monitoring/docs/images/telegram-alert-config/02-media-types-list.png)

**Bước 2:** Điền thông tin:

![Form Create Media Type](file:///home/phuc/zabbix-monitoring/docs/images/telegram-alert-config/03-create-media-type-form.png)

| Field | Value |
|-------|-------|
| **Name** | `AI Webhook (Groq)` |
| **Type** | Webhook |

**Bước 3:** Thêm Parameters (click "Add" cho mỗi parameter):

| Name | Value |
|------|-------|
| `trigger_name` | `{ALERT.SUBJECT}` |
| `host_name` | `{HOST.NAME}` |
| `trigger_severity` | `{TRIGGER.SEVERITY}` |
| `trigger_value` | `{ITEM.VALUE}` |
| `event_time` | `{EVENT.TIME}` |
| `trigger_description` | `{TRIGGER.DESCRIPTION}` |
| `event_id` | `{EVENT.ID}` |

**Bước 4:** Thêm Script:

Click vào ô **Script** và paste code sau:

```javascript
var params = JSON.parse(value);
var req = new HttpRequest();
req.addHeader('Content-Type: application/json');

var payload = JSON.stringify({
    trigger_name: params.trigger_name,
    host_name: params.host_name,
    trigger_severity: params.trigger_severity,
    trigger_value: params.trigger_value,
    event_time: params.event_time,
    trigger_description: params.trigger_description,
    event_id: params.event_id
});

var response = req.post('http://ai-webhook:5000/webhook', payload);

if (req.getStatus() !== 200) {
    throw 'Webhook failed: ' + response;
}

return 'OK';
```

**Bước 5:** Các cài đặt khác:
- **Message templates**: Để trống
- **Process tags**: Không check
- **Enabled**: ✅ Check

**Bước 6:** Click **Add** để lưu

### 4.3. Gán Media Type Cho User

**Bước 1:** Vào menu:
```
Administration → Users
```

**Bước 2:** Click vào user **Admin** (hoặc user bạn đang dùng)

**Bước 3:** Chuyển sang tab **Media**

**Bước 4:** Click **Add**

**Bước 5:** Điền thông tin:

| Field | Value |
|-------|-------|
| **Type** | `AI Webhook (Groq)` |
| **Send to** | `ai-webhook` (bất kỳ text nào) |
| **When active** | `1-7,00:00-24:00` |
| **Use if severity** | ✅ Check TẤT CẢ các severity |

**Bước 6:** Click **Add**, rồi **Update** ở cuối trang

![Tab Media của User Admin](file:///home/phuc/zabbix-monitoring/docs/images/telegram-alert-config/04-user-media-tab.png)

---

## 5. Cấu Hình Actions

### 5.1. Tạo Action Mới

**Bước 1:** Vào menu:
```
Configuration → Actions → Trigger actions
```

**Bước 2:** Click **Create action**

### 5.2. Tab "Action"

**Điền thông tin:**

| Field | Value |
|-------|-------|
| **Name** | `AI Alert with Telegram` |
| **Enabled** | ✅ Check |

**Conditions (Điều kiện)** - Click "Add":

| Label | Operator | Value |
|-------|----------|-------|
| `Trigger severity` | `>=` | `High` |

> 💡 Có thể điều chỉnh severity tùy ý (Warning, Average, High, Disaster)

### 5.3. Tab "Operations"

**Bước 1:** Click **Add** trong phần Operations

**Bước 2:** Điền:

| Field | Value |
|-------|-------|
| **Operation type** | `Send message` |
| **Send to users** | Chọn `Admin` (hoặc user của bạn) |
| **Send only to** | `AI Webhook (Groq)` |

**Bước 3:** Click **Add** (trong popup), rồi **Add** (ở cuối form)

![Danh sách Actions đã cấu hình](file:///home/phuc/zabbix-monitoring/docs/images/telegram-alert-config/05-actions-list.png)

---

## 6. Test và Verify

### 6.1. Test Webhook Trực Tiếp

**Từ UAT server, chạy:**

```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_name": "Test High CPU",
    "host_name": "UAT-Server",
    "trigger_severity": "High",
    "trigger_value": "95%",
    "event_time": "2026-01-20 00:10:00",
    "event_id": "TEST123"
  }'
```

**Kiểm tra Telegram** - Bạn phải nhận được message:

```
🚨 Test High CPU

🟠 High | UAT-Server | ⏰ 2026-01-20 00:10:00

━━━━━━━━━━━━━━━━━━━━━━
🧠 AI Analysis • [confidence]%

[Phân tích của AI về lỗi]

Alert ID: TEST123

┌────────────────┬───────────────┐
│ 🔍 Diagnostic  │ 🔧 Auto-Fix  │
├────────────────┼───────────────┤
│ 🔄 Restart     │ 📊 Metrics   │
├────────────────┼───────────────┤
│ ✅ Acknowledge │ 🔇 Ignore    │
└────────────────┴───────────────┘
```

> ✅ **Nếu nhận được message** → Webhook hoạt động!

### 6.2. Test Với Zabbix Trigger Thật

**Bước 1:** Tạo test item trong Zabbix UI:

```
Configuration → Hosts → "Zabbix server" → Items → Create item
```

Điền:
- **Name**: `Test CPU Load`
- **Type**: `Zabbix trapper`
- **Key**: `test.cpu.load`
- **Type of information**: `Numeric (float)`

Click **Add**

**Bước 2:** Tạo trigger:

```
Configuration → Hosts → "Zabbix server" → Triggers → Create trigger
```

Điền:
- **Name**: `High CPU on {HOST.NAME} (TEST)`
- **Severity**: `High`
- **Expression**: `last(/Zabbix server/test.cpu.load)>80`

Click **Add**

**Bước 3:** Gửi dữ liệu test (từ UAT server):

```bash
docker exec zabbix-server zabbix_sender \
  -z localhost \
  -s "Zabbix server" \
  -k test.cpu.load \
  -o 95
```

**Bước 4:** Kiểm tra:

![Monitoring Problems - Alerts đang active](file:///home/phuc/zabbix-monitoring/docs/images/telegram-alert-config/06-monitoring-problems.png)

1. **Zabbix UI** → `Monitoring → Problems` - Phải thấy alert mới
2. **Zabbix UI** → `Reports → Action log` - Phải thấy webhook được gọi
3. **Telegram** - Phải nhận message có AI analysis
4. **Click nút trong Telegram** - Test interactive buttons

### 6.3. Test Interactive Buttons

**Click vào nút "🔍 Diagnostic"** trong alert Telegram

**Mong đợi:**
```
🔍 Running diagnostic for #TEST123...

[Kết quả diagnostic từ Ansible]
```

**Nếu thấy "Permission denied"** → Check lại role trong `bot.py`

---

## 7. Troubleshooting

### Issue 1: Không Nhận Alert trong Telegram

**Nguyên nhân có thể:**

1. **Webhook không được gọi**

```bash
# Check Action log
# Zabbix UI → Reports → Action log
# Phải thấy dòng status "Sent" cho webhook
```

2. **AI Webhook lỗi**

```bash
# Check logs
docker compose logs ai-webhook --tail=50

# Phải thấy:
# "Received webhook request"
# "Sending to Telegram..."
```

3. **Telegram token/chat ID sai**

```bash
# Verify env vars
docker compose exec ai-webhook env | grep TELEGRAM

# Test manual (dùng token của bạn)
curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"
```

### Issue 2: Bot Không Respond Commands

```bash
# Check bot container
docker compose ps | grep telegram

# Check logs
docker compose logs telegram-bot --tail=50

# Restart
docker compose restart telegram-bot
```

### Issue 3: Buttons Không Hoạt Động

**Nguyên nhân**: Role chưa đúng

**Fix:**
1. Kiểm tra lại `USER_ROLES` trong `bot.py`
2. Rebuild: `docker compose build telegram-bot`
3. Restart: `docker compose restart telegram-bot`

### Issue 4: Nhận 2 Alert Cùng Lúc

**Nguyên nhân**: Có 2 actions trong Zabbix cùng trigger

**Fix:**
```
Zabbix UI → Configuration → Actions
→ Disable hoặc xóa actions cũ không dùng
```

---

## 📊 Checklist Hoàn Thành

### Cấu Hình Cơ Bản
- [ ] Services đang chạy (zabbix-server, ai-webhook, telegram-bot)
- [ ] Env vars đã đúng (TELEGRAM_BOT_TOKEN, CHAT_ID, GROQ_API_KEY)
- [ ] Bot respond /start command
- [ ] Role Admin đã được set cho user

### Cấu Hình Zabbix
- [ ] Media Type "AI Webhook (Groq)" đã tạo
- [ ] Script webhook đã config đúng URL
- [ ] Media đã gán cho user Admin
- [ ] Action "AI Alert with Telegram" đã tạo
- [ ] Severity condition đã set (>= High)

### Test và Verify
- [ ] Test webhook trực tiếp → Nhận Telegram message
- [ ] Tạo test trigger → Có trong Problems
- [ ] Gửi dữ liệu test → Alert được trigger
- [ ] Nhận alert trong Telegram với AI analysis
- [ ] Click button diagnostic → Nhận response
- [ ] Check Action log → Webhook status "Sent"

---

## 🎯 Các Lệnh Telegram Hữu Ích

```
/start      - Bắt đầu và hiển thị role
/help       - Danh sách lệnh
/list       - Alert đang active
/status     - Trạng thái hệ thống
```

**Khi nhận alert**, click các nút:
- **Vận Hành diagnostic**: Thu thập thông tin lỗi
- **🔧 Auto-Fix**: Thử tự sửa (chỉ ADMIN)
- **🔄 Restart**: Khởi động lại service (ADMIN/OPERATOR)
- **✅ Acknowledge**: Xác nhận đã biết alert
- **📊 Metrics**: Xem graph

---

## 📚 Tài Liệu Tham Khảo

- `/home/pnj/Zabbix-Monitoring/docs/TELEGRAM_BOT_QUICKSTART.md`
- `/home/pnj/Zabbix-Monitoring/docs/ZABBIX_WEBHOOK_SETUP.md`
- `/home/pnj/Zabbix-Monitoring/docs/ZABBIX_ACTIONS_UPDATE.md`

---

**Hoàn thành!** 🎉 

Nếu có vấn đề, check logs:
```bash
docker compose logs ai-webhook --tail=100
docker compose logs telegram-bot --tail=100
docker compose logs zabbix-server --tail=100
```

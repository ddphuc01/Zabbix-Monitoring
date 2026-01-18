# Zabbix Actions Configuration Update Guide

**Issue:** Vẫn nhận được alerts với template Qwen cũ  
**Reason:** Zabbix Actions trong UI vẫn trỏ đến alertscripts cũ

---

## ✅ Scripts Đã Cleanup

**Di chuyển vào deprecated/scripts/:**
- ❌ `telegram_qwen.sh` - Script cũ dùng Qwen wrapper
- ❌ `telegram_ai_v4.sh` - Script có Qwen fallback
- ❌ `telegram_interactive.sh` - Script dùng Qwen API

**Scripts còn lại trong alertscripts/ (OK to use):**
- ✅ `telegram.sh` - Basic Telegram notification
- ✅ `telegram_ai.sh` - Có thể cần update
- ✅ `ai_analysis.sh` - Basic AI analysis

---

## 🔧 Bước 1: Kiểm tra Zabbix Actions

### Truy cập Zabbix UI
```
http://localhost:8080
Login: Admin / zabbix (hoặc password của bạn)
```

### Vào Configuration → Actions
1. Click **Configuration** (menu trên)
2. Click **Actions**
3. Chọn **Trigger actions** tab

### Tìm Actions sử dụng script cũ
Kiểm tra các actions và tìm xem có action nào:
- **Operations** tab có script: `telegram_qwen.sh`
- **Operations** tab có script: `telegram_ai_v4.sh`
- **Operations** tab có script: `telegram_interactive.sh`

---

## 🔄 Bước 2: Cập nhật Actions

### Option 1: Sử dụng Webhook (RECOMMENDED)

**Tại sao:** Webhook dùng Groq AI, mạnh hơn, có cache Redis

1. **Tạo Media Type mới:**
   - Administration → Media types → Create media type
   - Name: `AI Webhook (Groq)`
   - Type: `Webhook`
   - Script:
   ```javascript
   var params = JSON.parse(value);
   
   var req = new HttpRequest();
   req.addHeader('Content-Type: application/json');
   
   var payload = {
       trigger_name: params.trigger_name,
       host_name: params.host_name,
       trigger_severity: params.trigger_severity,
       trigger_value: params.item_value,
       event_time: params.event_time,
       event_id: params.event_id
   };
   
   var resp = req.post('http://ai-webhook:5000/webhook', JSON.stringify(payload));
   
   Zabbix.log(4, 'AI Webhook response: ' + resp);
   return 'OK';
   ```
   - Parameters:
     - `trigger_name` = `{TRIGGER.NAME}`
     - `host_name` = `{HOST.NAME}`
     - `trigger_severity` = `{TRIGGER.SEVERITY}`
     - `item_value` = `{ITEM.VALUE}`
     - `event_time` = `{EVENT.TIME}`
     - `event_id` = `{EVENT.ID}`

2. **Cập nhật Action:**
   - Configuration → Actions → Chọn action cũ
   - Operations tab
   - Xóa operation với script cũ
   - Add new operation:
     - Operation type: Send message
     - Send to users: Admin (hoặc user của bạn)
     - Send only to: `AI Webhook (Groq)`

### Option 2: Telegram Bot trực tiếp

**Tại sao:** Bot có natural language processing, interactive buttons

Telegram bot đang chạy và tự động nhận alerts từ webhook.

**Không cần thay đổi** - webhook tự động gửi đến Telegram bot.

### Option 3: Simple script (No AI)

Nếu chỉ muốn thông báo đơn giản:
- Dùng `telegram.sh` (basic notification)
- Sửa action để dùng `telegram.sh` thay vì script cũ

---

## 🧪 Bước 3: Test cấu hình mới

### Trigger test alert
```bash
# Từ Zabbix UI
Configuration → Hosts → Chọn host → Items
Tạo item test: test.item với type "Zabbix trapper"

# Trigger test
Configuration → Hosts → Triggers → Create trigger
Expression: last(/hostname/test.item) > 90
```

### Gửi test value
```bash
zabbix_sender -z localhost -s "hostname" -k test.item -o 95
```

### Verify
- ✅ Nhận 1 alert (không phải 2)
- ✅ Alert có AI analysis từ Groq (không phải Qwen)
- ✅ Format mới với Telegram inline buttons

---

## 📋 Checklist

### Trong Zabbix UI:
- [ ] Xóa tất cả actions dùng `telegram_qwen.sh`
- [ ] Xóa tất cả actions dùng `telegram_ai_v4.sh`
- [ ] Xóa tất cả actions dùng `telegram_interactive.sh`
- [ ] Tạo hoặc update action dùng Webhook `http://ai-webhook:5000/webhook`
- [ ] Test trigger alert
- [ ] Verify chỉ nhận 1 notification với Groq AI

### Trong filesystem:
- [x] Di chuyển scripts cũ vào deprecated/
- [x] Verify zbx_env/usr/lib/zabbix/alertscripts/ chỉ có scripts OK

---

## 🚨 Nếu vẫn nhận alert cũ

### Check running services
```bash
docker ps | grep -E "qwen|ollama"
# Không nên thấy service nào

docker logs zabbix-server | grep -i qwen
# Nếu thấy logs về qwen → Zabbix vẫn đang gọi script cũ
```

### Restart Zabbix Server
```bash
docker compose restart zabbix-server
```

### Double-check Zabbix configuration
```bash
# Vào container Zabbix
docker exec -it zabbix-server sh

# Check alertscripts directory
ls -la /usr/lib/zabbix/alertscripts/

# Nếu thấy script cũ → xóa chúng
rm /usr/lib/zabbix/alertscripts/telegram_qwen.sh
rm /usr/lib/zabbix/alertscripts/telegram_ai_v4.sh
```

---

## 📞 Quick Fix (Emergency)

Nếu cần dừng ngay alerts cũ:

```bash
# 1. Disable action trong Zabbix UI
Configuration → Actions → Chọn action → Status: Disabled

# 2. Restart Zabbix server
docker compose restart zabbix-server

# 3. Re-enable sau khi update script/webhook
```

---

**Next Steps:**
1. Update Zabbix Actions theo guide trên
2. Test với trigger mẫu
3. Verify nhận alerts mới với Groq AI
4. Report lại nếu vẫn có issue

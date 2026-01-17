# Zabbix Webhook Configuration Guide

## Bước 1: Tạo Media Type (Webhook)

1. Vào Zabbix UI: **Administration → Media types**
2. Click **Create media type**
3. Cấu hình:
   - **Name**: `AI Webhook (Groq)`
   - **Type**: `Webhook`
   - **Parameters**:
     ```
     trigger_name: {ALERT.SUBJECT}
     host_name: {HOST.NAME}
     trigger_severity: {TRIGGER.SEVERITY}
     trigger_value: {ITEM.VALUE}
     event_time: {EVENT.TIME}
     trigger_description: {TRIGGER.DESCRIPTION}
     event_id: {EVENT.ID}
     ```
   - **Script**:
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
   - **Message templates**: Để trống
   - **Process tags**: Không check

4. Click **Add** để lưu

## Bước 2: Gán Media Type cho User

1. **Administration → Users**
2. Chọn user admin (hoặc user bạn đang dùng)
3. Tab **Media**
4. Click **Add**
5. Cấu hình:
   - **Type**: Chọn `AI Webhook (Groq)`
   - **Send to**: `ai-webhook` (bất kỳ giá trị nào cũng được)
   - **When active**: `1-7,00:00-24:00` (luôn active)
   - **Use if severity**: Check tất cả severity levels
6. Click **Add**, rồi **Update**

## Bước 3: Tạo Action

1. **Configuration → Actions → Trigger actions**
2. Click **Create action**
3. **Action** tab:
   - **Name**: `AI Alert Analysis (Groq)`
   - **Conditions**: 
     - `Trigger severity >= High` (hoặc bất kỳ điều kiện nào)
   - **Enabled**: Check

4. **Operations** tab, click **Add**:
   - **Send to users**: Chọn user admin
   - **Send only to**: `AI Webhook (Groq)`
   - Click **Add**

5. Click **Add** để lưu action

## Bước 4: Test Alert

### Cách 1: Trigger Manual Test
1. Vào **Monitoring → Problems**
2. Chọn một trigger đang có
3. Click **Acknowledge**, thêm comment để trigger action

### Cách 2: Tạo Test Trigger
1. **Configuration → Hosts**
2. Chọn một host (ví dụ: Zabbix server)
3. **Items** → **Create item**:
   - **Name**: `Test CPU`
   - **Key**: `test.cpu`
   - **Type of information**: Numeric (float)
   - **Type**: Zabbix trapper
   - Click **Add**

4. **Triggers** → **Create trigger**:
   - **Name**: `High CPU on {HOST.NAME}`
   - **Expression**: `last(/Zabbix server/test.cpu)>80`
   - **Severity**: High
   - Click **Add**

5. Gửi test data:
   ```bash
   zabbix_sender -z localhost -s "Zabbix server" -k test.cpu -o 95
   ```

## Bước 5: Verify

1. **Monitoring → Problems** - Xem có alert mới không
2. **Reports → Action log** - Kiểm tra webhook đã được gọi
3. **Telegram** - Kiểm tra có nhận message Tiếng Việt không
4. **Logs**: 
   ```bash
   docker logs zabbix-ai-webhook | tail -50
   ```

## Troubleshooting

### Webhook không được gọi
- Check action conditions
- Check user media settings
- Check Reports → Action log

### Webhook failed
```bash
docker logs zabbix-ai-webhook
# Xem lỗi cụ thể
```

### Telegram không nhận message
- Check TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID trong .env
- Test manual:
  ```bash
  curl -X POST http://localhost:5000/webhook -H "Content-Type: application/json" -d '{"trigger_name":"Test","host_name":"test-server","trigger_value":"95"}'
  ```

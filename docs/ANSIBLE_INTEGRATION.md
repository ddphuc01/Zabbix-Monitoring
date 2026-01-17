# AI Webhook - Ansible Integration Guide

## Tại Sao Cần Ansible?

**Hiện tại**: AI chỉ nhận alert info từ Zabbix (trigger name, host, severity)
**Với Ansible**: AI nhận thêm metrics thực tế (CPU, RAM, Disk, Network)

### So Sánh Output:

**Không có Ansible** (Hiện tại):
```
🔴 [HIGH] CPU ALERT: web-server-01
📊 Tình trạng: 92%
⚡ Nguyên nhân: Không có dữ liệu chi tiết
✅ Khuyến nghị: Kiểm tra server
```

**Có Ansible** (Sau khi enable):
```
🔴 [HIGH] CPU ALERT: web-server-01
📊 Tình trạng: 92% / 80%
⚡ Nguyên nhân: nginx đang chiếm 45% CPU
- Có ~500 connection từ client
- Top processes: nginx (45%), mysql (20%)
✅ Khuyến nghị:
1. Tăng worker processes của nginx từ 4 → 8
2. Check slow query log
3. Monitor 10 phút tiếp
```

---

## 🚀 Enable Ansible Integration

### Bước 1: Update Dockerfile

File đã được update với:
- `ansible` - Ansible core
- `openssh-client` - SSH connectivity
- `sshpass` - Password authentication (optional)

### Bước 2: Mount Ansible Directory + SSH Keys

Update `docker-compose.yml` để container có access:

```yaml
ai-webhook:
  volumes:
    - ./ansible:/ansible:ro  # Ansible playbooks
    - ~/.ssh:/root/.ssh:ro   # SSH keys để connect tới hosts
  environment:
    ANSIBLE_CONFIG: /ansible/ansible.cfg
    ANSIBLE_HOST_KEY_CHECKING: "False"
```

### Bước 3: Rebuild Container

```bash
cd /home/phuc/zabbix-monitoring
docker compose build ai-webhook
docker compose up -d ai-webhook
```

### Bước 4: Test

Trigger một alert và check logs:
```bash
docker logs -f zabbix-ai-webhook | grep "Ansible"
```

Nếu thành công, bạn sẽ thấy:
```
🚀 Running Ansible for web-server-01...
✅ Parsed Ansible metrics: ['top', 'ps', 'df', 'free', 'netstat']
```

---

## 📋 Metrics Được Thu Thập

| Alert Type | Ansible Command | AI Sử Dụng Để |
|------------|----------------|--------------|
| **CPU** | `top -b -n 1`<br>`ps aux --sort=-%cpu` | Tìm process chiếm CPU cao<br>Phân tích load average |
| **Memory** | `free -h`<br>`top` | Check swap usage<br>Tìm process ăn RAM nhiều |
| **Disk** | `df -h` | Tìm partition gần đầy<br>Khuyến nghị cleanup |
| **Network** | `netstat -an` | Đếm connections<br>Phát hiện TIME_WAIT, SYN_RECV |

---

## ⚠️ Requirements

### SSH Access
Container cần SSH access tới các monitored hosts:
1. **SSH keys**: Copy vào `~/.ssh/id_rsa` trong container
2. **Known hosts**: Add hosts vào `~/.ssh/known_hosts`
3. **Inventory**: Hosts phải có trong `/ansible/inventory/hosts`

### Ansible Inventory Example
```yaml
# /home/phuc/zabbix-monitoring/ansible/inventory/hosts.yml
linux_hosts:
  hosts:
    web-server-01:
      ansible_host: 192.168.1.10
      ansible_user: ubuntu
    db-server-01:
      ansible_host: 192.168.1.11
      ansible_user: ubuntu
```

---

## 🔍 Troubleshooting

### "No such file or directory: 'ansible-playbook'"
- Container chưa có Ansible installed
- Rebuild container với Dockerfile mới

### "Failed to connect to host"
- Check SSH keys mounted correctly
- Verify `ansible_host` IP đúng
- Test manual: `docker exec -it zabbix-ai-webhook ssh user@host`

### "Permission denied (publickey)"
- SSH key chưa được add vào target hosts
- Run: `ssh-copy-id user@host` từ host machine

---

## 🎯 Kết Luận

**KHÔNG bắt buộc phải có Ansible** - AI vẫn hoạt động tốt với alert info từ Zabbix.

**NÊN có Ansible** nếu muốn:
- Phân tích root cause chính xác hơn
- Khuyến nghị cụ thể (process nào, command gì)
- Metrics thực tế thay vì đoán mò

**Chi phí**: Thêm ~100MB docker image size, cần setup SSH keys

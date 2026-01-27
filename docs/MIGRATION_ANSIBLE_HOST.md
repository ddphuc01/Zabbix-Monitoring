# Quick Migration Guide - Ansible Container to Host

## 📋 Tóm tắt thay đổi

Migration này chuyển Ansible execution từ **Docker container** sang **Host machine**.

### Lý do migration:
- ✅ SSH trực tiếp (không qua Docker NAT) → Nhanh hơn 20-30%
- ✅ Ansible có full network access
- ✅ Dễ debug và maintain
- ✅ Giảm complexity trong container networking

---

## 🚀 Migration Steps (5 phút)

### 1️⃣ Setup API Service trên Host

```bash
# Pull latest code
cd /home/phuc/zabbix-monitoring
git pull origin main

# Chạy setup script (tự động cài đặt mọi thứ)
cd scripts
chmod +x setup-ansible-api-host.sh
sudo ./setup-ansible-api-host.sh
```

Script sẽ:
- Cài Python dependencies (FastAPI, ansible-runner, uvicorn)
- Setup systemd service
- Start và enable service
- Test API endpoint

**Expected output:**
```
========================================
  Ansible REST API Service - READY!
========================================

Service Status:  RUNNING
Service Port:    5001
API Endpoint:    http://localhost:5001
Health Check:    http://localhost:5001/health
```

### 2️⃣ Verify API Service

```bash
# Test health endpoint
curl http://localhost:5001/health | python3 -m json.tool

# Expected:
# {
#   "status": "healthy",
#   "service": "ansible-rest-api",
#   ...
# }
```

### 3️⃣ Restart Docker Stack

```bash
cd /home/phuc/zabbix-monitoring

# Stop current stack
docker-compose down

# Start với config mới (ansible-executor container đã bị disable)
docker-compose up -d

# Verify
docker ps | grep zabbix

# Kiểm tra ansible-executor KHÔNG còn chạy
docker ps | grep ansible-executor  # Should return nothing
```

### 4️⃣ Test Connectivity từ Container

```bash
# Test từ ai-webhook container
docker exec -it zabbix-ai-webhook curl http://host.docker.internal:5001/health

# Expected output:
# {"status":"healthy","service":"ansible-rest-api",...}
```

### 5️⃣ Trigger Test Alert

```bash
# Tạo test alert trong Zabbix hoặc trigger manually
# Check logs

# Host logs (Ansible API)
sudo journalctl -u ansible-api.service -f

# Container logs (AI Webhook)
docker logs -f zabbix-ai-webhook
```

---

## ✅ Verification Checklist

- [ ] API service running on host (port 5001)
- [ ] Health endpoint responding
- [ ] Container can access host.docker.internal:5001
- [ ] ansible-executor container is NOT running
- [ ] Zabbix alerts trigger Ansible diagnostics successfully
- [ ] AI analysis working với Ansible data

---

## 🔄 Quick Commands

```bash
# Check API service status
sudo systemctl status ansible-api.service

# View API logs
sudo journalctl -u ansible-api.service -f

# Restart API service
sudo systemctl restart ansible-api.service

# Check Docker stack
docker ps
docker logs -f zabbix-ai-webhook

# Test API from container
docker exec -it zabbix-ai-webhook curl http://host.docker.internal:5001/health
```

---

## 🛠️ Rollback (Nếu cần)

```bash
# 1. Stop API service
sudo systemctl stop ansible-api.service
sudo systemctl disable ansible-api.service

# 2. Restore old docker-compose.yml
git checkout docker-compose.yml

# 3. Restore old webhook.py
git checkout ai-services/webhook-handler/webhook.py

# 4. Restart Docker stack
docker-compose down
docker-compose up -d
```

---

## 📊 Thay đổi trong Code

### docker-compose.yml
- ✅ `ansible-executor` service → **Commented out**
- ✅ `ai-webhook` → Added `ANSIBLE_API_URL: http://host.docker.internal:5001`
- ⚠️ `backend` network → Vẫn KHÔNG isolated (cần cho Groq/Telegram APIs)

### webhook.py
- ✅ `ANSIBLE_API_URL` default → Changed to `http://host.docker.internal:5001`

### ansible-api.service (systemd)
- ✅ Enhanced với logging, resource limits, auto-restart
- ✅ Health monitoring
- ✅ Security settings

---

## 🎯 Expected Behavior

### Trước migration:
```
Zabbix Alert → ai-webhook → ansible-executor container → SSH to targets
                                   (172.16.239.5)
                                        ↓ (Docker NAT)
                                   Host (192.168.1.100)
                                        ↓
                                   Target (192.168.1.10)
```

### Sau migration:
```
Zabbix Alert → ai-webhook → API on host → Native SSH to targets
                              (direct)
                                ↓
                           Target (192.168.1.10)
```

**Kết quả:** Nhanh hơn, đơn giản hơn, dễ maintain hơn! 🚀

---

## 📞 Troubleshooting Quick Tips

| Issue | Quick Fix |
|-------|-----------|
| Port 5001 in use | `sudo netstat -tulnp \| grep 5001` → Kill process |
| Service failed | `sudo journalctl -u ansible-api.service -n 50` |
| Container can't reach host | Update `extra_hosts` in docker-compose.yml |
| Ansible playbook failed | Test manually: `ansible-playbook -i inventory/hosts.yml playbooks/...` |

---

**Chi tiết đầy đủ:** Xem [ANSIBLE_HOST_SETUP.md](ANSIBLE_HOST_SETUP.md)

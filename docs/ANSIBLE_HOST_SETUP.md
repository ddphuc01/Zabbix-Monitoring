# Ansible Host Setup Guide

## 📋 Overview

Hướng dẫn này giúp bạn setup **Ansible REST API Service** trên **host machine** thay vì chạy trong Docker container.

## 🎯 Lợi ích

### ✅ Performance
- **SSH trực tiếp** từ host → target hosts (không qua Docker NAT)
- **Giảm latency** khi chạy Ansible playbooks (20-30% nhanh hơn)
- **Native network access** - không bị giới hạn bởi container network

### ✅ Security  
- **Backend network có thể isolate** (tuy nhiên vẫn cần external access cho Groq/Telegram APIs)
- **Ansible chạy native** trên host với full permissions
- **SSH keys management** dễ dàng hơn

### ✅ Debugging
- **Logs trực tiếp** trên host: `journalctl -u ansible-api.service -f`
- **Dễ dàng debug** Ansible playbook issues
- **Update Ansible version** không cần rebuild container

---

## 🔧 Prerequisites

### System Requirements
- **OS:** Ubuntu 20.04+ / Debian 11+ / RHEL 8+ / CentOS 8+
- **Python:** 3.8 hoặc mới hơn
- **RAM:** Tối thiểu 512MB available
- **Disk:** 500MB free space

### Network Requirements
- **Port 5001** chưa bị sử dụng
- Host có thể SSH tới các target hosts (192.168.x.x)

### Software Requirements
- Python 3.8+
- Ansible 2.9+
- SSH client
- systemd (để quản lý service)

---

## 📦 Installation

### Phương án 1: Automatic Setup (Khuyến nghị)

```bash
# 1. Clone hoặc pull latest code
cd /home/phuc/zabbix-monitoring
git pull

# 2. Chạy setup script
cd scripts
chmod +x setup-ansible-api-host.sh
sudo ./setup-ansible-api-host.sh
```

Script sẽ tự động:
- ✅ Kiểm tra Python version
- ✅ Cài đặt dependencies (ansible, python packages)
- ✅ Setup systemd service
- ✅ Start và enable service
- ✅ Test API endpoint

### Phương án 2: Manual Setup

#### Bước 1: Cài đặt dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip ansible openssh-client curl
```

**RHEL/CentOS:**
```bash
sudo yum install -y python3 python3-pip ansible openssh-clients curl
```

#### Bước 2: Cài Python packages

```bash
cd /home/phuc/zabbix-monitoring/ansible-api-service
sudo pip3 install -r requirements.txt

# Hoặc cài thủ công:
sudo pip3 install fastapi uvicorn ansible-runner pydantic requests
```

#### Bước 3: Copy systemd service file

```bash
sudo cp /home/phuc/zabbix-monitoring/ansible-api-service/systemd/ansible-api.service \
        /etc/systemd/system/

sudo systemctl daemon-reload
```

#### Bước 4: Start service

```bash
sudo systemctl enable ansible-api.service
sudo systemctl start ansible-api.service
```

#### Bước 5: Verify

```bash
# Check status
sudo systemctl status ansible-api.service

# Test health endpoint
curl http://localhost:5001/health
```

---

## ✅ Verification

### 1. Service Status

```bash
# Check if service is running
sudo systemctl status ansible-api.service

# Expected output:
# ● ansible-api.service - Ansible REST API Service for Zabbix Monitoring
#    Loaded: loaded (/etc/systemd/system/ansible-api.service; enabled)
#    Active: active (running) since ...
```

### 2. Health Endpoint

```bash
curl http://localhost:5001/health | python3 -m json.tool
```

Expected response:
```json
{
  "status": "healthy",
  "service": "ansible-rest-api",
  "timestamp": "2026-01-27T10:00:00.000000",
  "ansible_dir": "/home/phuc/zabbix-monitoring/ansible",
  "inventory": "/home/phuc/zabbix-monitoring/ansible/inventory/hosts.yml",
  "playbook_dir": "/home/phuc/zabbix-monitoring/ansible/playbooks"
}
```

### 3. Test API từ Container

```bash
# Từ host machine, test connectivity từ container
docker exec -it zabbix-ai-webhook curl http://host.docker.internal:5001/health

# Nếu thành công → Container có thể access API trên host ✓
```

### 4. Test Ansible Playbook Execution

```bash
# Test chạy playbook qua API
curl -X POST http://localhost:5001/api/v1/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook": "gather_system_metrics",
    "target_host": "localhost",
    "extra_vars": {}
  }'
```

---

## 🐳 Docker Stack Update

Sau khi setup xong API service trên host, restart Docker stack:

```bash
cd /home/phuc/zabbix-monitoring

# Stop current stack
docker-compose down

# Start với config mới
docker-compose up -d

# Verify containers
docker ps | grep -E "zabbix-ai-webhook|redis|zabbix-server"

# ansible-executor container KHÔNG nên xuất hiện
docker ps | grep ansible-executor  # Should be empty
```

---

## 📊 Monitoring & Logs

### Xem logs của service

```bash
# Real-time logs
sudo journalctl -u ansible-api.service -f

# Last 50 lines
sudo journalctl -u ansible-api.service -n 50

# Logs từ thời điểm cụ thể
sudo journalctl -u ansible-api.service --since "2026-01-27 10:00:00"

# Export logs to file
sudo journalctl -u ansible-api.service --since today > ansible-api.log
```

### Check service metrics

```bash
# Service uptime
systemctl show ansible-api.service --property=ActiveEnterTimestamp

# Resource usage
systemctl status ansible-api.service
```

---

## 🔥 Troubleshooting

### Issue 1: Service Failed to Start

**Triệu chứng:**
```bash
sudo systemctl status ansible-api.service
# ● ansible-api.service - failed
```

**Giải pháp:**
```bash
# 1. Check logs
sudo journalctl -u ansible-api.service -n 50

# 2. Common issues:
#    - Python dependencies missing → Re-run pip install
#    - Port 5001 in use → Check with netstat -tuln | grep 5001
#    - Permission issues → Check file ownership

# 3. Fix và restart
sudo systemctl restart ansible-api.service
```

### Issue 2: Port 5001 Already in Use

```bash
# Find process using port 5001
sudo netstat -tulnp | grep :5001
# or
sudo lsof -i :5001

# Kill process
sudo kill -9 <PID>

# Restart service
sudo systemctl restart ansible-api.service
```

### Issue 3: Container Cannot Access host.docker.internal

**Triệu chứng:**
```bash
docker exec -it zabbix-ai-webhook curl http://host.docker.internal:5001/health
# curl: (6) Could not resolve host: host.docker.internal
```

**Giải pháp:**

```bash
# Option 1: Dùng IP của host
HOST_IP=$(ip -4 addr show docker0 | grep -Po 'inet \K[\d.]+')
echo $HOST_IP

# Update docker-compose.yml
# ai-webhook:
#   extra_hosts:
#     - "host.docker.internal:172.17.0.1"  # Thay bằng IP của bạn

# Option 2: Dùng bridge IP
docker inspect bridge | grep Gateway
# Update ANSIBLE_API_URL với IP này
```

### Issue 4: Ansible Playbook Failed

**Triệu chứng:**
```bash
curl localhost:5001/api/v1/playbook/run ...
# Response: "status": "failed"
```

**Giải pháp:**
```bash
# 1. Test Ansible manually
cd /home/phuc/zabbix-monitoring/ansible
ansible -i inventory/hosts.yml localhost -m ping

# 2. Check inventory file
cat inventory/hosts.yml

# 3. Check SSH keys
ls -la /home/phuc/.ssh/
ansible-vault view secrets.yml  # If using vault

# 4. Check playbook syntax
ansible-playbook playbooks/diagnostics/gather_system_metrics.yml --syntax-check

# 5. Test playbook manually
ansible-playbook -i inventory/hosts.yml \
  playbooks/diagnostics/gather_system_metrics.yml \
  -e "target_host=localhost" -vvv
```

### Issue 5: Permission Denied Errors

```bash
# Ansible cần quyền root để chạy một số commands
# Fix: Chạy service với user root (đã config trong systemd)

# Hoặc setup sudo no-password cho ansible
sudo visudo
# Add:
# ansible ALL=(ALL) NOPASSWD: ALL
```

---

## 🔄 Service Management

### Start/Stop/Restart

```bash
# Start service
sudo systemctl start ansible-api.service

# Stop service
sudo systemctl stop ansible-api.service

# Restart service
sudo systemctl restart ansible-api.service

# Reload systemd config (sau khi sửa service file)
sudo systemctl daemon-reload
sudo systemctl restart ansible-api.service
```

### Enable/Disable Auto-start

```bash
# Enable (start on boot)
sudo systemctl enable ansible-api.service

# Disable
sudo systemctl disable ansible-api.service

# Check if enabled
systemctl is-enabled ansible-api.service
```

### Update Service Configuration

Sau khi sửa file `/etc/systemd/system/ansible-api.service`:

```bash
# 1. Reload config
sudo systemctl daemon-reload

# 2. Restart service
sudo systemctl restart ansible-api.service

# 3. Verify
sudo systemctl status ansible-api.service
```

---

## 🔐 Security Recommendations

### 1. Firewall Rules

```bash
# Chỉ cho phép Docker containers access port 5001
sudo ufw allow from 172.16.239.0/24 to any port 5001 proto tcp comment 'Ansible API - Docker backend'

# Block external access
sudo ufw deny 5001/tcp
```

### 2. SSH Keys Setup

```bash
# Copy SSH keys to target hosts
ssh-copy-id -i ~/.ssh/id_rsa user@target-host

# Test SSH connectivity
ssh user@target-host "hostname"

# Add to known_hosts
ssh-keyscan -H target-host >> ~/.ssh/known_hosts
```

### 3. Ansible Vault (Cho secrets)

```bash
# Create vault file
ansible-vault create inventory/secrets.yml

# Edit vault
ansible-vault edit inventory/secrets.yml

# Use in playbook
ansible-playbook playbook.yml --ask-vault-pass
```

---

## 📈 Performance Tuning

### 1. Increase Worker Processes

```bash
# Edit service file
sudo nano /etc/systemd/system/ansible-api.service

# Change:
ExecStart=/usr/bin/python3 -m uvicorn app:app --host 0.0.0.0 --port 5001 --workers 4

# Restart
sudo systemctl daemon-reload
sudo systemctl restart ansible-api.service
```

### 2. Ansible Optimization

```bash
# Edit ansible.cfg
nano /home/phuc/zabbix-monitoring/ansible/ansible.cfg

# Add:
[defaults]
forks = 10              # Parallel execution
gathering = smart       # Smart fact gathering
fact_caching = jsonfile # Cache facts
fact_caching_timeout = 3600
```

---

## 🔄 Rollback to Container-based Ansible

Nếu cần quay lại dùng ansible-executor trong container:

```bash
# 1. Stop API service trên host
sudo systemctl stop ansible-api.service
sudo systemctl disable ansible-api.service

# 2. Sửa docker-compose.yml
#    - Uncomment ansible-executor service
#    - Update ai-webhook ANSIBLE_API_URL về 'http://ansible-executor:5001'

# 3. Restart Docker stack
docker-compose down
docker-compose up -d
```

---

## 📞 Support

Nếu gặp vấn đề:
1. ✅ Check logs: `sudo journalctl -u ansible-api.service -f`
2. ✅ Check health endpoint: `curl localhost:5001/health`
3. ✅ Test Ansible manually: `ansible localhost -m ping`
4. ✅ Review GitHub Issues: https://github.com/ddphuc01/Zabbix-Monitoring/issues

---

## ✨ Summary

- ✅ API service chạy trên host machine (port 5001)
- ✅ Docker containers call API qua `http://host.docker.internal:5001`
- ✅ Ansible chạy native trên host với full network access
- ✅ Systemd quản lý service (auto-start, logging, resource limits)
- ✅ Logs available qua `journalctl`

**Next:** Trigger test alert từ Zabbix và verify Ansible diagnostics hoạt động! 🚀

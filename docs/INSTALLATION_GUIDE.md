# 🚀 Hướng Dẫn Cài Đặt Chi Tiết - Zabbix Monitoring với AI

> **Phiên bản:** Zabbix 7.4 LTS + AI Services  
> **Thời gian cài đặt:** 30-45 phút  
> **Độ khó:** Trung bình

---

## 📋 Mục Lục

1. [Kiểm Tra Yêu Cầu Hệ Thống](#1-kiểm-tra-yêu-cầu-hệ-thống)
2. [Clone Repository](#2-clone-repository)
3. [Cấu Hình Credentials](#3-cấu-hình-credentials)
4. [Tạo Docker Secrets](#4-tạo-docker-secrets)
5. [Khởi Động Services](#5-khởi-động-services)
6. [Xác Minh Deployment](#6-xác-minh-deployment)
7. [Cấu Hình Telegram Bot](#7-cấu-hình-telegram-bot)
8. [Cấu Hình Zabbix Webhook](#8-cấu-hình-zabbix-webhook)
9. [Thêm Host Đầu Tiên](#9-thêm-host-đầu-tiên)
10. [Kiểm Tra AI Integration](#10-kiểm-tra-ai-integration)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Kiểm Tra Yêu Cầu Hệ Thống

### Hardware Requirements

| Cấu Hình | Minimum | Recommended | Production |
|-----------|---------|-------------|------------|
| **CPU** | 2 cores | 4 cores | 8 cores |
| **RAM** | 4 GB | 8 GB | 16 GB |
| **Disk** | 20 GB | 50 GB | 100 GB SSD |
| **Network** | 100 Mbps | 1 Gbps | 1 Gbps+ |

### Software Requirements

```bash
# 1. Kiểm tra Docker
docker --version
# Yêu cầu: Docker 20.10+

# 2. Kiểm tra Docker Compose
docker-compose --version
# Yêu cầu: Docker Compose 2.x

# 3. Kiểm tra Git
git --version
# Yêu cầu: Git 2.x+
```

### Cài Đặt Nếu Thiếu

#### Ubuntu/Debian:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Install Git
sudo apt install git -y

# Verify installations
docker --version
docker compose version
git --version
```

#### CentOS/RHEL:
```bash
# Install Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin -y
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER

# Install Git
sudo yum install git -y
```

---

## 2. Clone Repository

```bash
# Chọn thư mục cài đặt
cd /home/$USER  # hoặc /opt/

# Clone repository
git clone https://github.com/ddphuc01/Zabbix-Monitoring.git
cd Zabbix-Monitoring

# Xem cấu trúc
ls -la

# Output:
# .env.example
# docker-compose.yml
# README.md
# SECURITY_SETUP.md
# ai-services/
# ansible/
# scripts/
# ...
```

---

## 3. Cấu Hình Credentials

### 3.1. Tạo File .env

```bash
# Copy template
cp .env.example .env

# Edit với editor yêu thích
nano .env
# hoặc: vim .env
# hoặc: code .env
```

### 3.2. Lấy API Keys

#### A. Telegram Bot Token

1. Mở Telegram, tìm [@BotFather](https://t.me/BotFather)
2. Gửi: `/newbot`
3. Đặt tên bot: `Zabbix Monitoring Bot`
4. Đặt username: `YourNameZabbixBot`
5. Copy token: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

#### B. Telegram Chat ID

```bash
# 1. Gửi tin nhắn cho bot
# 2. Chạy lệnh (thay YOUR_BOT_TOKEN):
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates

# Output sẽ có:
# "chat":{"id":123456789, ...}
# Copy số ID này
```

#### C. Groq API Key (FREE - 14,400 req/day)

1. Truy cập: https://console.groq.com
2. Đăng ký tài khoản (Google/GitHub)
3. Vào "API Keys"
4. Click "Create API Key"
5. Copy key: `gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### D. Gemini API Key (Backup)

1. Truy cập: https://aistudio.google.com/app/apikey
2. Đăng nhập Google account
3. Click "Create API Key"
4. Copy key: `AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### E. Gmail App Password

1. Truy cập: https://myaccount.google.com/apppasswords
2. Tên app: `Zabbix Monitoring`
3. Click "Generate"
4. Copy password 16 ký tự

#### F. WebUI Secret Key

```bash
# Generate random secret
openssl rand -hex 32

# Copy output
```

### 3.3. Cập Nhật .env

Mở file `.env` và điền các giá trị:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789

# Groq AI
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Gemini AI (backup)
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Email
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_16_char_app_password
EMAIL_FROM=Zabbix Monitoring <your_email@gmail.com>
EMAIL_TO=your_email@gmail.com

# WebUI Secret
WEBUI_SECRET_KEY=your_generated_secret_key_here

# Zabbix API (đổi sau khi login!)
ZABBIX_API_USER=Admin
ZABBIX_API_PASSWORD=zabbix
```

**Lưu file (Ctrl+O trong nano, :wq trong vim)**

---

## 4. Tạo Docker Secrets

```bash
# Chạy script tự động
./scripts/generate-secrets.sh

# Script sẽ tạo:
# ✅ env_vars/.POSTGRES_USER
# ✅ env_vars/.POSTGRES_PASSWORD
# ✅ Các directories cần thiết

# Xác minh
ls -la env_vars/
# Output:
# -rw------- .POSTGRES_USER
# -rw------- .POSTGRES_PASSWORD
```

---

## 5. Khởi Động Services

### 5.1. Chạy Init Setup

```bash
# Chạy script khởi tạo tự động
./scripts/init-setup.sh

# Script sẽ:
# 1. Kiểm tra Docker/Docker Compose
# 2. Tạo directories
# 3. Pull Docker images (có thể mất 5-10 phút)
# 4. Start tất cả services
# 5. Verify health status
```

### 5.2. Hoặc Khởi Động Thủ Công

```bash
# Pull images
docker-compose pull

# Start services
docker-compose up -d

# Xem logs
docker-compose logs -f
```

### 5.3. Kiểm Tra Services

```bash
# Xem status
docker-compose ps

# Kết quả mong đợi (tất cả healthy):
# NAME                  STATUS
# zabbix-server         Up (healthy)
# zabbix-web            Up (healthy)
# zabbix-postgres       Up (healthy)
# zabbix-agent2         Up
# zabbix-java-gateway   Up
# zabbix-web-service    Up
# zabbix-snmptraps      Up
# zabbix-redis          Up (healthy)
# ai-webhook            Up (healthy)
# telegram-bot          Up
# ansible-executor      Up
# ollama                Up
# open-webui            Up
```

---

## 6. Xác Minh Deployment

### 6.1. Truy Cập Zabbix Web UI

```bash
# Mở browser
http://YOUR_SERVER_IP:8080

# Hoặc từ local machine
http://localhost:8080
```

**Login:**
- Username: `Admin`
- Password: `zabbix`

**⚠️ ĐỔI PASSWORD NGAY:**
1. Click "User settings" (góc phải trên)
2. Tab "Password"
3. Đổi sang password mạnh
4. Save

### 6.2. Cập Nhật Password Trong .env

```bash
# Mở .env
nano .env

# Cập nhật
ZABBIX_API_PASSWORD=your_new_strong_password

# Restart services cần API
docker-compose restart zabbix-api-connector telegram-bot
```

### 6.3. Kiểm Tra Các Services Khác

```bash
# Open WebUI (Chat Interface)
http://localhost:3000

# Ollama (Local LLM)
http://localhost:11434

# Redis
docker exec -it zabbix-redis redis-cli ping
# Output: PONG
```

---

## 7. Cấu Hình Telegram Bot

### 7.1. Kiểm Tra Bot Running

```bash
# Xem logs
docker-compose logs telegram-bot

# Tìm dòng:
# "Bot started successfully"
```

### 7.2. Test Bot

1. Mở Telegram
2. Tìm bot của bạn: `@YourNameZabbixBot`
3. Gửi: `/start`

**Mong đợi:**
```
🤖 Zabbix AI Bot

Welcome [Tên]!
Your role: VIEWER

Available Commands:
/help - Show all commands
/list - Active alerts
/status - System status
```

### 7.3. Thêm User ID Làm Admin

```bash
# Lấy User ID từ message
# Bot sẽ reply: "Your ID: 123456789"

# Edit bot.py
nano ai-services/telegram-bot/bot.py

# Tìm dòng:
USER_ROLES = {
    1081490318: 'ADMIN',  # Dương Duy
}

# Thêm ID của bạn:
USER_ROLES = {
    1081490318: 'ADMIN',  # Dương Duy
    123456789: 'ADMIN',   # Your Name
}

# Rebuild container
docker-compose up -d --build telegram-bot
```

### 7.4. Test Commands

```
/help     → Xem tất cả commands
/status   → Kiểm tra services
/list     → Xem active alerts (chưa có vì chưa add hosts)
```

---

## 8. Cấu Hình Zabbix Webhook

### 8.1. Tạo Media Type

1. Login Zabbix Web UI
2. **Administration** → **Media types**
3. Click **Create media type**
4. Điền:
   - **Name:** `AI Webhook`
   - **Type:** `Webhook`
   - **Script:** (copy từ `docs/ZABBIX_WEBHOOK_SETUP.md`)
   - **Parameters:**
     ```
     webhook_url: http://ai-webhook:5000/webhook
     ```
5. Click **Add**

### 8.2. Tạo Action

1. **Configuration** → **Actions** → **Trigger actions**
2. Click **Create action**
3. **Action tab:**
   - **Name:** `AI Analysis`
   - **Conditions:**
     - Trigger severity >= Warning
4. **Operations tab:**
   - Click **Add**
   - **Send to users:** Admin
   - **Send only to:** AI Webhook
   - Click **Add**
5. Click **Add** (tạo action)

Chi tiết xem: `docs/ZABBIX_WEBHOOK_SETUP.md`

---

## 9. Thêm Host Đầu Tiên

### 9.1. Chuẩn Bị Ansible

```bash
# Copy inventory template
cp ansible/inventory/hosts.yml.example ansible/inventory/hosts.yml

# Edit
nano ansible/inventory/hosts.yml
```

### 9.2. Thêm Linux Host

```yaml
linux_hosts:
  hosts:
    web-server-01:
      ansible_host: 192.168.1.100
      ansible_user: root
      ansible_ssh_private_key_file: /root/.ssh/id_rsa
```

**Setup SSH key:**
```bash
# Generate key (nếu chưa có)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa

# Copy to target
ssh-copy-id root@192.168.1.100

# Test connection
ssh root@192.168.1.100 "echo 'Connected!'"
```

### 9.3. Thêm Windows Host

```yaml
windows:
  hosts:
    win-server-01:
      ansible_host: 192.168.1.200
      ansible_user: Administrator
      ansible_password: 'YourWindowsPassword'
      zabbix_hostid: win-001
```

**Setup WinRM trên Windows:**
```powershell
# Chạy PowerShell as Administrator trên Windows
winrm quickconfig -q
winrm set winrm/config/service/auth '@{Basic="true"}'
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
```

### 9.4. Thêm Vào Zabbix

#### Cách 1: Script Tự Động
```bash
# Linux host
./scripts/onboard_host.sh web-server-01 192.168.1.100

# Windows host
python3 ./scripts/add-windows-host.py win-server-01 192.168.1.200 Administrator YourPassword
```

#### Cách 2: Thủ Công Qua Web UI

1. **Configuration** → **Hosts** → **Create host**
2. **Host tab:**
   - **Host name:** `web-server-01`
   - **Groups:** `Linux servers`
   - **Interfaces:** Add Agent
     - IP: `192.168.1.100`
     - Port: `10050`
3. **Templates tab:**
   - Link template: `Linux by Zabbix agent`
4. Click **Add**

### 9.5. Deploy Zabbix Agent

```bash
# Ansible playbook
cd ansible
ansible-playbook -i inventory/hosts.yml \
  playbooks/deploy/install_zabbix_agent.yml \
  --limit web-server-01
```

---

## 10. Kiểm Tra AI Integration

### 10.1. Trigger Test Alert

**Tạo CPU Alert giả lập:**

1. Login vào host test
2. Chạy stress test:
```bash
# Linux
yes > /dev/null &
yes > /dev/null &
yes > /dev/null &

# Chờ 2-3 phút để trigger alert
```

### 10.2. Kiểm Tra Workflow

**Xem trong Telegram:**
1. Alert notification sẽ đến (2-5 phút)
2. Message có format:
```
🔴 [HIGH] CPU ALERT: web-server-01

📊 Tình trạng: 92% / 80%

⚡ Nguyên nhân: ...
✅ Khuyến nghị: ...

[🔧 Fix] [🔍 Diagnostic] [✅ Ack]
```

**Xem logs:**
```bash
# AI Webhook
docker-compose logs ai-webhook

# Telegram Bot
docker-compose logs telegram-bot
```

### 10.3. Test Interactive Buttons

Click vào button trong Telegram message:
- **🔧 Fix** → Chạy auto-fix
- **🔍 Diagnostic** → Thu thập system metrics
- **✅ Ack** → Acknowledge alert

---

## 11. Troubleshooting

### Issue 1: Services Không Start

```bash
# Kiểm tra logs
docker-compose logs

# Check cụ thể service
docker-compose logs zabbix-server

# Xem tất cả errors
docker-compose logs | grep -i error
```

**Nguyên nhân thường gặp:**
- Port đã được sử dụng
- Thiếu secrets trong `env_vars/`
- RAM không đủ

**Giải pháp:**
```bash
# Kiểm tra port
netstat -tulpn | grep 8080

# Regenerate secrets
./scripts/generate-secrets.sh

# Restart
docker-compose down
docker-compose up -d
```

### Issue 2: Telegram Bot Không Reply

```bash
# Check logs
docker-compose logs telegram-bot

# Verify token
docker-compose exec telegram-bot env | grep TELEGRAM
```

**Test token thủ công:**
```bash
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```

### Issue 3: AI Webhook Error

```bash
# Check Groq API key
docker-compose logs ai-webhook | grep -i "groq"

# Test API key
curl -H "Authorization: Bearer $GROQ_API_KEY" \
  https://api.groq.com/openai/v1/models
```

### Issue 4: Ansible Connection Failed

```bash
# Test connectivity
ansible -i ansible/inventory/hosts.yml all -m ping

# Test specific host
ansible -i ansible/inventory/hosts.yml web-server-01 -m ping

# Debug mode
ansible -i ansible/inventory/hosts.yml web-server-01 -m ping -vvv
```

### Issue 5: Database Connection Error

```bash
# Check PostgreSQL
docker exec zabbix-postgres pg_isready -U zabbix

# View database
docker exec -it zabbix-postgres psql -U zabbix -d zabbix -c "\l"

# Restart database
docker-compose restart postgres-server
```

### Issue 6: Web UI 502 Bad Gateway

```bash
# Check Zabbix server
docker-compose logs zabbix-server

# Check if server is healthy
docker-compose ps zabbix-server

# Restart web + server
docker-compose restart zabbix-web-nginx zabbix-server
```

---

## 📚 Tài Liệu Tham Khảo

### Nội Bộ Repository
- [README.md](../README.md) - Tổng quan dự án
- [SECURITY_SETUP.md](../SECURITY_SETUP.md) - Bảo mật
- [docs/TELEGRAM_BOT_QUICKSTART.md](TELEGRAM_BOT_QUICKSTART.md) - Telegram bot
- [docs/ANSIBLE_INTEGRATION.md](ANSIBLE_INTEGRATION.md) - Ansible
- [docs/WINDOWS_DEPLOYMENT.md](WINDOWS_DEPLOYMENT.md) - Windows hosts
- [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Chi tiết troubleshooting

### Official Documentation
- [Zabbix Documentation](https://www.zabbix.com/documentation/current/)
- [Docker Documentation](https://docs.docker.com/)
- [Ansible Documentation](https://docs.ansible.com/)
- [Groq API Docs](https://console.groq.com/docs)

---

## ✅ Checklist Hoàn Thành

Sau khi hoàn tất tất cả bước, bạn nên có:

- [x] Docker containers chạy healthy
- [x] Zabbix Web UI accessible
- [x] Telegram bot responding
- [x] AI webhook working
- [x] Ít nhất 1 host được monitor
- [x] Test alert đã trigger thành công
- [x] AI analysis hiển thị trong Telegram

---

## 🎉 Hoàn Thành!

Hệ thống Zabbix Monitoring với AI của bạn đã sẵn sàng!

**Next Steps:**
1. Thêm thêm hosts cần monitor
2. Tùy chỉnh alert thresholds
3. Tạo custom templates
4. Setup scheduled reports
5. Monitor và optimize system

**Cần hỗ trợ?**
- Mở issue trên GitHub
- Check troubleshooting guide
- Review logs với `docker-compose logs`

---

*Được tạo bởi AI Assistant - 2026-01-18*
*GitHub: https://github.com/ddphuc01/Zabbix-Monitoring*

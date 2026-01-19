# Zabbix Monitoring System

<p align="center">
  <img src="https://assets.zabbix.com/img/logo/zabbix_logo_500x131.png" alt="Zabbix Logo" width="400"/>
</p>

<p align="center">
  <strong>Production-Ready Zabbix 7.4 LTS + AI Monitoring Platform</strong><br/>
  Complete Docker-based deployment with AI-powered alert analysis<br/>
  <a href="https://github.com/ddphuc01/Zabbix-Monitoring">🔗 GitHub Repository</a>
</p>

> **🔒 Security Notice:** This repository contains templates only. Actual credentials must be configured separately. See [SECURITY_SETUP.md](SECURITY_SETUP.md) for setup instructions.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Quick Start](#-quick-start-5-minutes)
- [Full Installation Guide](#-full-installation-guide)
- [Architecture](#-architecture)
- [System Components](#-system-components)
- [Troubleshooting](#-troubleshooting)
- [Documentation](#-documentation)
- [FAQ](#-faq)
- [Management Commands](#-management-commands)

---

## 📖 Overview

This is a comprehensive, production-ready implementation of **Zabbix 7.4 LTS** monitoring system with **AI-powered alert analysis**. Based on the official [Zabbix Docker repository](https://github.com/zabbix/zabbix-docker), it extends standard Zabbix with intelligent automation and interactive management.

### ✨ Key Features

#### Core Monitoring
- **🖥️ Complete Zabbix Stack** - All official components (Server, Web UI, Agent 2, Java Gateway, SNMP)
- **🔒 Security First** - Secrets management, network isolation, encrypted connections
- **📊 Production Ready** - Resource limits, health checks, automated backups
- **📈 Scalable Architecture** - Support for 1000+ hosts with distributed monitoring

#### AI & Automation
- **🤖 AI Alert Analysis** - Groq (Llama 3.3-70B) analyzes alerts with real system metrics
- **📱 Interactive Telegram Bot** - Natural language queries, inline action buttons
- **🔧 Automated Diagnostics** - Ansible gathers system data (CPU, memory, disk, network)
- **🇻🇳 Vietnamese Support** - AI responses and reports in Vietnamese
- **⚡ Smart Caching** - Redis caches AI responses (3600s TTL)

#### Advanced Features
- **📧 Automated Reports** - Daily/weekly summaries via Telegram & email
- **🎛️ Role-Based Access** - Admin/Operator/Viewer permissions
- **🪟 Windows Support** - WinRM-based monitoring and diagnostics
- **🐧 Linux Automation** - SSH-based deployment and management

> **⚠️ Note:** Ollama and Open-WebUI services have been deprecated (2026-01-18). The system now uses Groq API exclusively for better performance and reliability.

---

## 🚀 Quick Start (5 Minutes)

**For experienced users with Docker already installed:**

```bash
# Quick prerequisites check
docker --version && docker compose version || echo "❌ Install Docker first!"

# Clone and setup
git clone https://github.com/ddphuc01/Zabbix-Monitoring.git
cd Zabbix-Monitoring

# Configure credentials (REQUIRED!)
cp .env.example .env
nano .env  # Fill in TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GROQ_API_KEY

# Generate secrets and start
./scripts/generate-secrets.sh
./scripts/init-setup.sh

# Access Zabbix Web UI
# http://localhost:8080 (Admin/zabbix)
```

**⚠️ First time with Docker?** Follow the [Full Installation Guide](#-full-installation-guide) below instead.

---

## 📚 Full Installation Guide

### Step 0: System Requirements Check

**BEFORE YOU START - Verify these:**

```bash
# Check Docker (20.10+ required)
docker --version

# Check Docker Compose (2.x required)
docker compose version

# Check available RAM (6GB+ recommended)
free -h

# Check free disk space (20GB+ required)
df -h .
```

**✅ All checks passed?** Continue to Step 1.  
**❌ Missing Docker?** See installation guides below:

#### Installing Docker

<details>
<summary><b>Ubuntu/Debian Installation</b></summary>

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (avoid sudo)
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose plugin
sudo apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version
```
</details>

<details>
<summary><b>CentOS/RHEL Installation</b></summary>

```bash
# Install Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin -y

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER

# Verify installation
docker --version
docker compose version
```
</details>

<details>
<summary><b>macOS Installation</b></summary>

1. Download [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
2. Install and start Docker Desktop
3. Verify in terminal:
```bash
docker --version
docker compose version
```
</details>

---

### Step 1: Clone Repository

```bash
# Choose installation directory
cd /home/$USER  # or /opt/ for system-wide

# Clone repository
git clone https://github.com/ddphuc01/Zabbix-Monitoring.git
cd Zabbix-Monitoring

# Verify structure
ls -la
```

**Expected output:**
```
.env.example
docker-compose.yml
README.md
SECURITY_SETUP.md
ai-services/
ansible/
scripts/
...
```

---

### Step 2: Configure Environment (.env)

**⚠️ CRITICAL STEP:** Services will NOT start without proper configuration!

```bash
# Create .env from template
cp .env.example .env

# Edit with your preferred editor
nano .env
# or: vim .env
# or: code .env
```

#### Required Fields (Must Configure These)

| Field | Purpose | Where to Get | Used By |
|-------|---------|--------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot notifications | [Get from @BotFather](#getting-telegram-bot-token) | AI Webhook, Alerts |
| `TELEGRAM_CHAT_ID` | Your chat ID | [Get your ID](#getting-telegram-chat-id) | Alert notifications |
| `GROQ_API_KEY` | AI analysis (FREE) | [console.groq.com](https://console.groq.com) | AI Webhook |

#### Optional Fields (Services work without these)

| Field | Purpose | Default Behavior |
|-------|---------|------------------|
| `SMTP_USER`, `SMTP_PASSWORD` | Email reports | Email reports disabled |
| `GEMINI_API_KEY` | Backup AI provider | Uses Groq only |

#### Getting Telegram Bot Token

1. Open Telegram, find [@BotFather](https://t.me/BotFather)
2. Send: `/newbot`
3. Follow prompts:
   - Bot name: `Zabbix Monitoring Bot`
   - Username: `YourNameZabbixBot` (must end with 'bot')
4. Copy the token: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

#### Getting Telegram Chat ID

```bash
# 1. Send /start to your bot in Telegram
# 2. Run this command (replace YOUR_BOT_TOKEN):
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates

# Output will show:
# "chat":{"id":123456789, ...}
# Copy that ID number
```

#### Getting Groq API Key (FREE - 14,400 requests/day)

1. Visit: [console.groq.com](https://console.groq.com)
2. Sign up (Google/GitHub login)
3. Go to "API Keys" section
4. Click "Create API Key"
5. Copy key: `gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### Example Filled .env

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=7891234567:AAHdqTcvbXYZ-1a2b3c4d5e6f7g8h9i0j1k
TELEGRAM_CHAT_ID=123456789

# AI Configuration  
GROQ_API_KEY=gsk_abcdefghijklmnopqrstuvwxyz1234567890

# Optional: Email (leave as-is to disable)
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=YOUR_APP_SPECIFIC_PASSWORD_HERE
```

**Save and close** (Ctrl+O, Enter, Ctrl+X in nano)

#### Validation

```bash
# Verify required fields are filled
grep -E "TELEGRAM_BOT_TOKEN|GROQ_API_KEY" .env | grep -v "YOUR_.*_HERE" && echo "✅ Configuration looks good!" || echo "❌ Missing required API keys!"
```

---

### Step 3: Check Port Availability

**These ports will be used:**

| Port | Service | Required |
|------|---------|----------|
| **8080** | Zabbix Web UI | ✅ Main access point |
| 10051 | Zabbix Server | ✅ Required |
| 5000 | AI Webhook | ✅ For AI features |
| 6379 | Redis Cache | ✅ For AI caching |
| 10052 | Java Gateway | Optional (JMX monitoring) |
| 10053 | Web Service | Optional (PDF reports) |
| 10060 | Agent 2 | Optional (Docker monitoring) |

**Quick port conflict check:**

```bash
netstat -tuln | grep -E ':(8080|10051|5000|6379)' && echo "❌ Port conflict detected!" || echo "✅ All ports available"
```

**If port 8080 is in use:**

```bash
# Find what's using it
sudo netstat -tulpn | grep 8080

# Option 1: Stop that service
sudo systemctl stop <service-name>

# Option 2: Change Zabbix port in .env (BEFORE starting services)
nano .env
# Change: ZABBIX_WEB_NGINX_HTTP_PORT=9080
```

---

### Step 4: Generate Secrets

```bash
# Make script executable
chmod +x scripts/generate-secrets.sh

# Generate database credentials
./scripts/generate-secrets.sh
```

**Expected output:**

```
========================================
Zabbix Secrets Generation
========================================

✓  Created POSTGRES_USER
✓  Created POSTGRES_PASSWORD
✓  Created MYSQL_USER
✓  Created MYSQL_PASSWORD
✓  Created MYSQL_ROOT_PASSWORD
✓  Created .env_srv

========================================
Secrets Generation Complete!
========================================
```

**Verify secrets were created:**

```bash
ls -la env_vars/

# Should show files with 600 permissions:
# -rw------- .POSTGRES_USER
# -rw------- .POSTGRES_PASSWORD
# -rw------- .env_srv
```

---

### Step 5: Start Services

```bash
# Make init script executable
chmod +x scripts/init-setup.sh

# Start all services (will take 5-10 minutes first time)
./scripts/init-setup.sh
```

**What this script does:**

1. ✅ Checks Docker/Docker Compose prerequisites
2. ✅ Creates necessary directories
3. ✅ Sets proper permissions
4. ✅ Pulls Docker images (~2-3GB, takes 5-10 min)
5. ✅ Starts all containers
6. ✅ Waits for services to become healthy

**Expected final output:**

```
╔════════════════════════════════════════╗
║    Installation Complete! ✓            ║
╚════════════════════════════════════════╝

📊 Zabbix Web Interface:
   URL: http://localhost:8080
   Default credentials:
     Username: Admin
     Password: zabbix

⚠  IMPORTANT: Change the default password after first login!
```

---

### Step 6: Verify Installation

**Run health check script:**

```bash
chmod +x scripts/health-check.sh
./scripts/health-check.sh
```

**Expected output (all green checkmarks):**

```
╔════════════════════════════════════════╗
║    Zabbix Health Check Report         ║
╚════════════════════════════════════════╝

[1/5] Container Status
✓ PostgreSQL Database: Running
✓ Zabbix Server: Running
✓ Web Interface: Running
✓ Agent 2: Running
✓ Java Gateway: Running
✓ Web Service: Running
✓ SNMP Traps: Running

[2/5] Port Connectivity
✓ Port 8080 (Web Interface HTTP): Open
✓ Port 10051 (Zabbix Server): Open
...

╔════════════════════════════════════════╗
║  Health Check: ALL SYSTEMS OPERATIONAL ║
╚════════════════════════════════════════╝
  Passed: 12  Failed: 0
```

**❌ If any service shows red,** see [Troubleshooting](#-troubleshooting) section below.

---

### Step 7: Access Zabbix Web UI

```bash
# Open in browser
http://localhost:8080

# Or from another machine:
http://YOUR_SERVER_IP:8080
```

**Default login credentials:**
- **Username:** `Admin` (capital A)
- **Password:** `zabbix`

**🔴 IMMEDIATELY after first login:**

1. Click user icon (top right corner)
2. Select **"User settings"**
3. Go to **"Password"** tab
4. Change to a strong password
5. Click **"Update"**

**Update password in .env:**

```bash
nano .env

# Find and update this line:
ZABBIX_API_PASSWORD=your_new_strong_password

# Save and restart AI services
docker compose restart ai-webhook
```

---

### Step 8: Test Telegram Integration

**Test your Telegram bot:**

1. Open Telegram app
2. Search for your bot username (e.g., `@YourNameZabbixBot`)
3. Click **"Start"** or send `/start`

**Expected bot response:**

```
🤖 Zabbix AI Bot

Welcome [Your Name]!
Your role: VIEWER

Available Commands:
/help - Show all commands
/list - View active alerts
/status - System status
```

**❌ If bot doesn't respond:**

```bash
# Check webhook logs
docker compose logs ai-webhook | grep -i telegram

# Verify token is loaded
docker compose exec ai-webhook env | grep TELEGRAM_BOT_TOKEN

# Test token manually
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# If test fails, check .env has correct token
cat .env | grep TELEGRAM_BOT_TOKEN

# Restart webhook
docker compose restart ai-webhook
```

---

## ✅ Installation Complete!

**You should now have:**

- ✅ All Docker containers running (check with `docker compose ps`)
- ✅ Zabbix Web UI accessible at http://localhost:8080
- ✅ Default admin password changed
- ✅ Telegram bot responding to commands
- ✅ All health checks passing

**🎉 Next Steps:**

1. **Add hosts to monitor:** See [docs/INSTALLATION_GUIDE.md](./docs/INSTALLATION_GUIDE.md#9-thêm-host-đầu-tiên)
2. **Configure alerts:** See [docs/ZABBIX_WEBHOOK_SETUP.md](./docs/ZABBIX_WEBHOOK_SETUP.md)
3. **Setup Ansible automation:** See [docs/ANSIBLE_INTEGRATION.md](./docs/ANSIBLE_INTEGRATION.md)
4. **Configure reports:** See [docs/TELEGRAM_BOT_QUICKSTART.md](./docs/TELEGRAM_BOT_QUICKSTART.md)

---

## 🏗️ Architecture

### System Architecture

The system implements a microservices architecture with three isolated network layers:

```
┌─────────────────────────────────────────────────────┐
│ Frontend Network (172.16.238.0/24)                  │
│  └─ Zabbix Web (Nginx) - Ports: 8080, 8443         │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│ Backend Network (172.16.239.0/24 - Internal)        │
│  ├─ Zabbix Server - Port: 10051                     │
│  ├─ AI Webhook Handler - Port: 5000                 │
│  ├─ Redis Cache - Port: 6379                        │
│  ├─ Java Gateway - Port: 10052                      │
│  ├─ Web Service - Port: 10053                       │
│  ├─ Agent 2 - Port: 10060                           │
│  └─ SNMP Traps - Port: 162/UDP                      │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│ Database Network (Internal Only)                    │
│  └─ PostgreSQL 17 - Port: 5432                      │
└─────────────────────────────────────────────────────┘
```

### Alert Flow with AI

```
1. Alert Triggered → Zabbix Server detects issue
2. Webhook Called → AI Webhook Handler receives alert
3. Diagnostics Gathered → Ansible Executor runs playbook on target host
4. AI Analysis → Groq analyzes metrics + context
5. Telegram Notification → Bot sends message with inline buttons
6. User Interaction → Admin clicks [Fix] / [Diagnostic] / [Ack]
7. Auto-Remediation → Ansible executes fix playbook
8. Alert Closed → Zabbix updates status
```

**📖 Detailed architecture:** See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)

---

## 📦 System Components

### Core Zabbix Services (7 containers)

| Component | Version | Purpose | Port |
|-----------|---------|---------|------|
| **Zabbix Server** | 7.4-alpine | Core monitoring engine | 10051 |
| **PostgreSQL** | 17-alpine | Primary database | 5432 (internal) |
| **Web Interface** | 7.4-alpine | Nginx + PHP-FPM UI | 8080, 8443 |
| **Agent 2** | 7.4-alpine | Modern monitoring agent | 10060 |
| **Java Gateway** | 7.4-alpine | JMX monitoring | 10052 |
| **Web Service** | 7.4-alpine | PDF report generation | 10053 |
| **SNMP Traps** | 7.4-alpine | Network device monitoring | 162/UDP |

### AI & Automation Services (4 containers)

| Component | Technology | Purpose | Port |
|-----------|-----------|---------|------|
| **AI Webhook Handler** | Python/Flask + Groq | Analyzes alerts with AI | 5000 |
| **Ansible Executor** | Ansible + Python | Automated diagnostics | - |
| **Redis** | Redis 7-alpine | AI response caching | 6379 |

**Total:** 11 active Docker containers

> **Note:** Telegram Bot functionality is integrated into the AI Webhook Handler service.

### Resource Requirements

| Configuration | Hosts | CPU | RAM | Disk |
|---------------|-------|-----|-----|------|
| **Development** | 1-10 | 2 cores | 4 GB | 20 GB |
| **Small Production** | 10-100 | 4 cores | 6 GB | 50 GB |
| **Production** | 100-1000 | 4-8 cores | 8-16 GB | 100 GB SSD |
| **Enterprise** | 1000+ | 8+ cores | 16+ GB | 200+ GB SSD |

---

## 🔧 Troubleshooting

### Quick Diagnosis

```bash
# Check all service status
docker compose ps

# View logs for all services
docker compose logs

# View specific service logs
docker compose logs <service-name>

# Follow logs in real-time
docker compose logs -f

# Run health check
./scripts/health-check.sh
```

### Common Issues & Solutions

#### ❌ Issue: "Services won't start" or containers exit immediately

**Symptoms:**
- `docker compose ps` shows "Exit 1" or "Exit 127"
- Services keep restarting

**Causes:**
- Missing secrets in `env_vars/`
- Missing `.env` configuration
- Insufficient permissions

**Solutions:**

```bash
# 1. Verify secrets exist
ls -la env_vars/
# Should show: .POSTGRES_USER, .POSTGRES_PASSWORD, .env_srv

# 2. Regenerate secrets if missing
./scripts/generate-secrets.sh

# 3. Verify .env exists and has required fields
cat .env | grep -E "TELEGRAM_BOT_TOKEN|GROQ_API_KEY"

# 4. Check permissions
chmod 600 env_vars/.*
chmod -R 775 zbx_env/

# 5. Restart services
docker compose down
docker compose up -d

# 6. Check logs for specific errors
docker compose logs zabbix-server
```

---

#### ❌ Issue: "Port already in use" errors

**Symptoms:**
- Error: "bind: address already in use"
- Services fail to start

**Solutions:**

```bash
# Find what's using port 8080
sudo netstat -tulpn | grep 8080
# or: sudo lsof -i :8080

# Option 1: Stop the conflicting service
sudo systemctl stop <service-name>

# Option 2: Change Zabbix ports in .env (before starting)
nano .env
# Modify these lines:
ZABBIX_WEB_NGINX_HTTP_PORT=9080
ZABBIX_SERVER_PORT=10151

# Restart with new ports
docker compose down
docker compose up -d
```

---

#### ❌ Issue: "Cannot connect to database"

**Symptoms:**
- Zabbix Server logs: "database is unavailable"
- Web UI shows database connection error

**Solutions:**

```bash
# 1. Check PostgreSQL status
docker exec zabbix-postgres pg_isready -U zabbix
# Should output: "accepting connections"

# 2. Check if database exists
docker exec zabbix-postgres psql -U zabbix -l | grep zabbix

# 3. View database logs
docker compose logs postgres-server

# 4. Restart database and server
docker compose restart postgres-server
sleep 10
docker compose restart zabbix-server

# 5. If still failing, check secrets
cat env_vars/.POSTGRES_USER
cat env_vars/.POSTGRES_PASSWORD
```

---

#### ❌ Issue: Telegram bot not responding

**Symptoms:**
- Bot doesn't reply to `/start`
- No response to commands

**Solutions:**

```bash
# 1. Test token validity
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
# Should return bot info JSON

# 2. Check webhook logs
docker compose logs ai-webhook | grep -i telegram

# 3. Verify environment variable is loaded
docker compose exec ai-webhook env | grep TELEGRAM_BOT_TOKEN

# 4. Check .env has correct token (no spaces/quotes)
cat .env | grep TELEGRAM_BOT_TOKEN

# 5. Restart AI webhook
docker compose restart ai-webhook

# 6. Wait 30 seconds, then test bot again
```

---

#### ❌ Issue: Web UI shows "502 Bad Gateway"

**Symptoms:**
- Browser shows 502 error
- Cannot access Zabbix UI

**Solutions:**

```bash
# 1. Check if Zabbix Server is running
docker compose ps zabbix-server
# Should show "Up (healthy)"

# 2. Check server logs
docker compose logs zabbix-server | tail -50

# 3. Check web interface logs
docker compose logs zabbix-web-nginx | tail -50

# 4. Restart both services
docker compose restart zabbix-web-nginx zabbix-server

# 5. Wait 60 seconds for initialization
sleep 60

# 6. Check health
./scripts/health-check.sh
```

---

#### ❌ Issue: "Out of memory" or containers keep crashing

**Symptoms:**
- Containers randomly exit
- System becomes unresponsive
- `docker stats` shows high memory usage

**Solutions:**

```bash
# 1. Check current memory usage
free -h
docker stats --no-stream

# 2. Check system requirements
# You need at least 6GB RAM for AI services
# Or 4GB if disabling AI features

# 3. Reduce PostgreSQL memory limit
nano docker-compose.yml
# Under postgres-server → deploy → resources → limits:
memory: 1G  # Change from 2G

# 4. Restart with new limits
docker compose down
docker compose up -d

# 5. Monitor memory
watch -n 2 docker stats
```

---

#### ❌ Issue: AI features not working / Groq API errors

**Symptoms:**
- Alerts arrive but no AI analysis
- Webhook logs show API errors

**Solutions:**

```bash
# 1. Test Groq API key
curl -H "Authorization: Bearer $GROQ_API_KEY" \
  https://api.groq.com/openai/v1/models

# 2. Check webhook logs
docker compose logs ai-webhook | grep -i groq

# 3. Verify API key in environment
docker compose exec ai-webhook env | grep GROQ_API_KEY

# 4. Check .env has correct key (starts with gsk_)
cat .env | grep GROQ_API_KEY

# 5. Restart webhook
docker compose restart ai-webhook
```

---

### Still Having Issues?

**Collect debug information:**

```bash
# 1. Create debug bundle
docker compose ps > debug.txt
docker compose logs >> debug.txt
free -h >> debug.txt
df -h >> debug.txt
cat .env | grep -v "PASSWORD\|TOKEN\|KEY" >> debug.txt

# 2. Review the debug.txt file

# 3. Check detailed troubleshooting guide
# See: docs/TROUBLESHOOTING.md

# 4. Search existing issues
# https://github.com/ddphuc01/Zabbix-Monitoring/issues
```

---

## 📚 Documentation

### Getting Started (Read in Order)

1. **[README.md](./README.md)** ← You are here - Quick start guide
2. **[INSTALLATION_GUIDE.md](./docs/INSTALLATION_GUIDE.md)** - Detailed step-by-step (Vietnamese)
3. **[SECURITY_SETUP.md](./SECURITY_SETUP.md)** - Security best practices

### Feature Configuration

- **[Telegram Bot Quickstart](./docs/TELEGRAM_BOT_QUICKSTART.md)** - Interactive bot setup
- **[AI Webhook Setup](./docs/ZABBIX_WEBHOOK_SETUP.md)** - Configure AI alert analysis
- **[Ansible Integration](./docs/ANSIBLE_INTEGRATION.md)** - Automated diagnostics
- **[Windows Deployment](./docs/WINDOWS_DEPLOYMENT.md)** - Monitor Windows hosts

### Reference & Advanced

- **[Troubleshooting Guide](./docs/TROUBLESHOOTING.md)** - Comprehensive problem solving
- **[API Guide](./docs/API_GUIDE.md)** - Zabbix API usage examples
- **[Best Practices](./docs/BEST_PRACTICES.md)** - Production recommendations
- **[Architecture](./docs/ARCHITECTURE.md)** - System design details

---

## ❓ FAQ

<details>
<summary><b>Q: Do I need all the API keys to start?</b></summary>

**A:** Minimum required for AI features:
- `TELEGRAM_BOT_TOKEN` - For notifications
- `TELEGRAM_CHAT_ID` - Your Telegram chat
- `GROQ_API_KEY` - For AI analysis (FREE tier is sufficient)

Email (`SMTP_*`) and Gemini API key are optional.

For basic Zabbix without AI, you only need to run `generate-secrets.sh`.
</details>

<details>
<summary><b>Q: Can I run this without AI features?</b></summary>

**A:** Yes! To run basic Zabbix:

1. Don't configure Telegram/Groq in `.env`
2. Remove these services from `docker-compose.yml`:
   - `ai-webhook`
   - `redis`
   - `ansible-executor`
3. Run `docker compose up -d`

You'll have a standard Zabbix 7.4 LTS deployment.
</details>

<details>
<summary><b>Q: Is Groq's free tier enough for production?</b></summary>

**A:** Yes, for most use cases:
- Free tier: 14,400 requests/day (~600/hour)
- Typical alert volume: 10-50/day even with 100+ hosts
- Redis caching reduces API calls by ~70%

Only very high-volume environments (1000+ hosts, aggressive monitoring) might need paid tier.
</details>

<details>
<summary><b>Q: What if ports 8080 or 10051 are already in use?</b></summary>

**A:** Change ports in `.env` BEFORE first start:

```bash
ZABBIX_WEB_NGINX_HTTP_PORT=9080
ZABBIX_SERVER_PORT=10151
```

Then access UI at `http://localhost:9080`
</details>

<details>
<summary><b>Q: How do I add more administrators to Telegram bot?</b></summary>

**A:** Edit `ai-services/telegram-bot/bot.py` (if bot is standalone) or `ai-services/webhook-handler/telegram_handler.py`:

```python
USER_ROLES = {
    1081490318: 'ADMIN',  # Original admin
    YOUR_ID: 'ADMIN',     # Add your ID
}
```

Get your ID by sending `/start` to the bot. Then rebuild:
```bash
docker compose up -d --build ai-webhook
```
</details>

<details>
<summary><b>Q: Where are database backups stored?</b></summary>

**A:** Backups are in `zbx_env/backups/` directory.

Create backup:
```bash
./scripts/backup-db.sh
```

Backups are kept for 7 days by default.
</details>

<details>
<summary><b>Q: Can I use Docker Desktop instead of Docker CE?</b></summary>

**A:** Yes! Docker Desktop includes:
- Docker Engine
- Docker Compose V2
- GUI management

Works perfectly for development and small deployments.
</details>

<details>
<summary><b>Q: What happened to Ollama and Open-WebUI?</b></summary>

**A:** Deprecated on 2026-01-18 in favor of Groq API:
- **Why:** Better performance, no local GPU needed, faster responses
- **Impact:** System now lighter (removed 2 containers, ~8GB RAM savings)
- **Migration:** Groq provides better model (Llama 3.3-70B vs Qwen-7B)

If you still want local LLM, you can uncomment the Ollama sections in `docker-compose.yml`.
</details>

---

## 🛠️ Management Commands

### Service Control

```bash
# Start all services
docker compose start

# Stop all services
docker compose stop

# Restart all services
docker compose restart

# Restart specific service
docker compose restart zabbix-server

# View service status
docker compose ps

# View resource usage
docker stats
```

### Logs & Debugging

```bash
# View all logs
docker compose logs

# Follow logs (real-time)
docker compose logs -f

# Specific service logs
docker compose logs zabbix-server

# Last 100 lines
docker compose logs --tail=100

# With timestamps
docker compose logs --timestamps
```

### Health & Maintenance

```bash
# Run health check
./scripts/health-check.sh

# Create database backup
./scripts/backup-db.sh

# Restore from backup
./scripts/restore-db.sh

# Access PostgreSQL
docker exec -it zabbix-postgres psql -U zabbix -d zabbix

# Access Redis CLI
docker exec -it zabbix-redis redis-cli
```

### Updates & Cleanup

```bash
# Pull latest images
docker compose pull

# Rebuild custom images
docker compose build

# Remove stopped containers
docker compose down

# Remove everything including volumes (⚠️ deletes data!)
docker compose down -v

# Clean up unused Docker resources
docker system prune -a
```

---

## 🔒 Security Recommendations

After installation, implement these security measures:

1. **✅ Change default password** (covered in Step 7)
2. **✅ Keep `.env` secure** - Never commit to Git
3. **✅ Regular backups** - Run `./scripts/backup-db.sh` daily
4. **✅ Enable HTTPS** - Use reverse proxy (Traefik/Nginx)
5. **✅ Firewall rules** - Restrict port 8080 to trusted IPs
6. **✅ Update regularly** - `docker compose pull && docker compose up -d`
7. **✅ Monitor logs** - Check for suspicious activity

See [SECURITY_SETUP.md](./SECURITY_SETUP.md) for detailed security hardening.

---

## 🤝 Support & Contributing

- **Official Zabbix Docs:** https://www.zabbix.com/documentation/current/
- **Report Issues:** [GitHub Issues](https://github.com/ddphuc01/Zabbix-Monitoring/issues)
- **Discussions:** [GitHub Discussions](https://github.com/ddphuc01/Zabbix-Monitoring/discussions)
- **Docker Hub:** https://hub.docker.com/u/zabbix/

---

## 📄 License

This implementation follows the official Zabbix Docker repository structure.
Zabbix is licensed under GPL v2.0.

---

<p align="center">
  Made with ❤️ for production monitoring | Zabbix 7.4 LTS
</p>

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

## 📋 Overview

This is a comprehensive, production-ready implementation of **Zabbix 7.4 LTS** monitoring system with **AI-powered alert analysis**. Based on the official [Zabbix Docker repository](https://github.com/zabbix/zabbix-docker), it extends standard Zabbix with intelligent automation and interactive management.

### ✨ Key Features

#### Core Monitoring
- **🖥️ Complete Zabbix Stack** - All official components (Server, Web UI, Agent 2, Java Gateway, SNMP)
- **🔒 Security First** - Secrets management, network isolation, encrypted connections
- **📊 Production Ready** - Resource limits, health checks, automated backups
- **� Scalable Architecture** - Support for 1000+ hosts with distributed monitoring

#### AI & Automation
- **🤖 AI Alert Analysis** - Groq (Llama 3.3-70B) analyzes alerts with real system metrics
- **� Interactive Telegram Bot** - Natural language queries, inline action buttons
- **🔧 Automated Diagnostics** - Ansible gathers system data (CPU, memory, disk, network)
- **🇻🇳 Vietnamese Support** - AI responses and reports in Vietnamese
- **⚡ Smart Caching** - Redis caches AI responses (3600s TTL)

#### Advanced Features
- **� Automated Reports** - Daily/weekly summaries via Telegram & email
- **🎛️ Role-Based Access** - Admin/Operator/Viewer permissions
- **🪟 Windows Support** - WinRM-based monitoring and diagnostics
- **🐧 Linux Automation** - SSH-based deployment and management

---

## 🏗️ Architecture

The system implements a microservices architecture with three isolated network layers:

```
┌─────────────────────────────────────────────────────┐
│ Frontend Network (172.16.238.0/24)                  │
│  ├─ Zabbix Web (Nginx) - Ports: 8080, 8443         │
└─────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────┐
│ Backend Network (172.16.239.0/24 - Internal)        │
│  ├─ Zabbix Server - Port: 10051                     │
│  ├─ Java Gateway - Port: 10052                      │
│  ├─ Web Service - Port: 10053                       │
│  ├─ Agent 2 - Port: 10060                           │
│  ├─ SNMP Traps - Port: 162/UDP                      │
└─────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────┐
│ Database Network (Internal Only)                    │
│  └─ PostgreSQL 17 - Port: 5432                      │
└─────────────────────────────────────────────────────┘
```

**[📖 View Full Architecture Diagram](./docs/ARCHITECTURE.md)**

---

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+ and Docker Compose 2.x
- 4GB RAM minimum (8GB recommended for AI services)
- 20GB free disk space
- Linux host (Ubuntu, Debian, CentOS, etc.)

### Installation (5 Minutes)

```bash
# 1. Clone repository
git clone https://github.com/ddphuc01/Zabbix-Monitoring.git
cd Zabbix-Monitoring

# 2. Configure credentials (REQUIRED!)
cp .env.example .env
nano .env  # Fill in your API keys (Telegram, Groq, etc.)

# 3. Generate secrets
./scripts/generate-secrets.sh

# 4. Start all services
./scripts/init-setup.sh
```

**� Detailed Instructions:** See [docs/INSTALLATION_GUIDE.md](docs/INSTALLATION_GUIDE.md) for step-by-step setup guide with screenshots.

### Access Points

- **Zabbix Web UI:** `http://localhost:8080` (Admin/zabbix)
- **Open WebUI (Chat):** `http://localhost:3000`
- **Ollama (Local LLM):** `http://localhost:11434`

> ⚠️ **SECURITY:** Change default password immediately after first login!
> 
> ⚠️ **API KEYS:** You MUST configure Telegram Bot Token, Groq API key, and other credentials in `.env` before starting services. See [SECURITY_SETUP.md](SECURITY_SETUP.md).

---

## 🏗️ System Architecture Comparison

### Standard Zabbix vs AI-Enhanced

| Feature | Standard Zabbix | This AI-Enhanced Setup |
|---------|----------------|------------------------|
| **Monitoring** | ✅ Core monitoring | ✅ Core monitoring |
| **Alert Notifications** | ✅ Email/SMS | ✅ Email/SMS + **Telegram Bot** |
| **Alert Analysis** | ❌ Manual | ✅ **AI-powered (Groq/Gemini)** |
| **Diagnostics** | ❌ Manual SSH | ✅ **Automated via Ansible** |
| **Interactive Control** | ❌ Web UI only | ✅ **Telegram commands + buttons** |
| **Natural Language** | ❌ None | ✅ **Ask AI about system status** |
| **Auto-Remediation** | ❌ Manual fixes | ✅ **One-click fixes via Telegram** |
| **Reports** | ✅ Basic | ✅ Basic + **AI summaries (Vietnamese)** |
| **Local LLM** | ❌ None | ✅ **Ollama + Qwen (offline capable)** |
| **Chat Interface** | ❌ None | ✅ **Open WebUI for conversations** |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         🌐 User Interfaces                          │
├─────────────────────────────────────────────────────────────────────┤
│  Zabbix Web UI (8080)  │  Open WebUI (3000)  │  Telegram Bot       │
└──────────┬──────────────┴─────────────────────┴─────────────┬───────┘
           │                                                    │
┌──────────▼────────────────────────────────────────────────────▼───────┐
│                    🔧 Application Layer                               │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐                │
│  │   Zabbix    │  │  AI Webhook  │  │  Telegram   │                │
│  │   Server    │  │   Handler    │  │     Bot     │                │
│  │   (10051)   │  │   (5000)     │  │             │                │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘                │
│         │                │                  │                        │
│  ┌──────▼──────┐  ┌─────▼──────┐  ┌───────▼────────┐              │
│  │ Java Gateway│  │   Groq AI  │  │    Ansible     │              │
│  │  Web Service│  │  Gemini AI │  │   Executor     │              │
│  │  SNMP Traps │  │  Qwen (Local)│ │   (Diagnostics)│              │
│  └─────────────┘  └────────────┘  └────────────────┘              │
│                                                                       │
└───────────────────────────────┬───────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────┐
│                    💾 Data Layer                                      │
├───────────────────────────────────────────────────────────────────────┤
│  PostgreSQL 17  │  Redis Cache  │  Ollama Models                      │
│  (Metrics DB)   │  (AI Cache)   │  (Local LLM)                        │
└───────────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────┐
│                    🖥️ Monitored Infrastructure                       │
├───────────────────────────────────────────────────────────────────────┤
│  Linux Servers  │  Windows Servers  │  Docker Containers  │  Network  │
│  (SSH/Agent)    │  (WinRM/Agent)    │  (Docker API)       │  (SNMP)   │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Complete Component List

### 🔵 Core Zabbix Components (7 services)

| Component | Version | Purpose | Port |
|-----------|---------|---------|------|
| **Zabbix Server** | 7.4-alpine | Core monitoring engine | 10051 |
| **PostgreSQL** | 17-alpine | Primary database | 5432 (internal) |
| **Web Interface** | 7.4-alpine | Nginx + PHP-FPM UI | 8080, 8443 |
| **Agent 2** | 7.4-alpine | Modern monitoring agent | 10060 |
| **Java Gateway** | 7.4-alpine | JMX monitoring | 10052 |
| **Web Service** | 7.4-alpine | PDF report generation | 10053 |
| **SNMP Traps** | 7.4-alpine | Network device monitoring | 162/UDP |

### 🤖 AI & Automation Services (6 services)

| Component | Technology | Purpose | Port |
|-----------|-----------|---------|------|
| **AI Webhook Handler** | Python/Flask + Groq | Analyzes alerts with AI | 5000 |
| **Telegram Bot** | python-telegram-bot 20.7 | Interactive alert management | - |
| **Ansible Executor** | Ansible + Python | Automated diagnostics | - |
| **Zabbix API Connector** | FastAPI | Bridge for Open WebUI | 8001 |
| **Ollama** | Ollama + Qwen | Local LLM (offline capable) | 11434 |
| **Open WebUI** | Open WebUI | Chat interface for AI | 3000 |
| **Redis** | Redis 7-alpine | AI response caching | 6379 |

**Total Services:** 13 Docker containers

### 🔄 Data Flow

1. **Alert Triggered** → Zabbix Server detects issue
2. **Webhook Called** → AI Webhook Handler receives alert
3. **Diagnostics Gathered** → Ansible Executor runs playbook on target host
4. **AI Analysis** → Groq/Gemini analyzes metrics + context
5. **Telegram Notification** → Bot sends message with inline buttons
6. **User Interaction** → Admin clicks button (Fix/Diagnostic/Ack)
7. **Auto-Remediation** → Ansible executes fix playbook
8. **Alert Closed** → Zabbix updates status

---

## 📂 Project Structure

```
zabbix-monitoring/
├── docker-compose.yml          # Main orchestration file
├── .env                        # Environment configuration
├── env_vars/                   # Secrets (credentials)
│   ├── .POSTGRES_USER
│   ├── .POSTGRES_PASSWORD
│   └── .env_srv               # Zabbix Server config
├── zbx_env/                    # Persistent data
│   ├── var/lib/zabbix/        # Zabbix data
│   ├── usr/lib/zabbix/        # Scripts & modules
│   └── backups/               # Database backups
├── scripts/                    # Automation scripts
│   ├── init-setup.sh          # Installation script
│   ├── health-check.sh        # System health check
│   ├── backup-db.sh           # Database backup
│   ├── restore-db.sh          # Database restore
│   └── generate-secrets.sh    # Secrets generator
├── templates/                  # Monitoring templates
├── config/                     # Configuration files
└── docs/                       # Documentation
    ├── INSTALLATION.md
    ├── ARCHITECTURE.md
    ├── TROUBLESHOOTING.md
    └── API_GUIDE.md
```

---

## 🔧 Management Commands

### Service Control
```bash
# Start services
docker-compose start

# Stop services
docker-compose stop

# Restart services
docker-compose restart

# View service status
docker-compose ps

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f zabbix-server
```

### Health & Maintenance
```bash
# Run health check
./scripts/health-check.sh

# Create database backup
./scripts/backup-db.sh

# Restore database
./scripts/restore-db.sh
```

### Database Access
```bash
# Access PostgreSQL
docker exec -it zabbix-postgres psql -U zabbix -d zabbix

# View database size
docker exec zabbix-postgres psql -U zabbix -d zabbix -c "\l+"
```

---

## 🔒 Security Features

- ✅ **Secrets Management** - Credentials stored in separate files with 600 permissions
- ✅ **Network Isolation** - Three-tier network segmentation
- ✅ **No Root Passwords** - All services run as non-root users
- ✅ **Resource Limits** - CPU and memory constraints prevent resource exhaustion
- ✅ **Health Checks** - Automatic container health monitoring
- ✅ **SSL/TLS Ready** - HTTPS support configuration included

---

## 📊 Resource Usage

### Minimum Configuration (100 hosts)
- CPU: 2 cores
- RAM: 4GB
- Disk: 20GB+

### Recommended Production (1000+ hosts)
- CPU: 4-8 cores
- RAM: 8-16GB
- Disk: 100GB+ (SSD recommended)

---

## 🔄 Backup & Recovery

### Automated Backups

```bash
# Manual backup
./scripts/backup-db.sh

# Setup automatic daily backups (cron)
0 2 * * * /home/phuc/zabbix-monitoring/scripts/backup-db.sh >> /var/log/zabbix-backup.log 2>&1
```

Backups are:
- Stored in `zbx_env/backups/`
- Compressed with gzip
- Retained for 7 days by default
- Named with timestamps: `zabbix_backup_YYYYMMDD_HHMMSS.sql.gz`

### Restore from Backup

```bash
./scripts/restore-db.sh
```

Interactive script will:
1. List available backups
2. Confirm restoration
3. Stop Zabbix Server
4. Restore database
5. Restart services

---

## 📚 Documentation

### Getting Started
- **[📖 Installation Guide](./docs/INSTALLATION_GUIDE.md)** - **START HERE!** Step-by-step setup (30-45 min)
- **[🔒 Security Setup](./SECURITY_SETUP.md)** - Credentials & secrets configuration
- **[🏗️ Architecture Overview](./docs/ARCHITECTURE.md)** - System design and components

### AI Features
- **[📱 Telegram Bot Quickstart](./docs/TELEGRAM_BOT_QUICKSTART.md)** - Interactive bot setup
- **[🤖 AI Integration](./docs/AI_QUICKSTART.md)** - Groq/Gemini configuration
- **[🧠 Qwen Local LLM](./docs/QWEN_QUICKSTART.md)** - Ollama setup guide
- **[🔗 Zabbix Webhook](./docs/ZABBIX_WEBHOOK_SETUP.md)** - AI webhook configuration

### Automation
- **[⚙️ Ansible Integration](./docs/ANSIBLE_INTEGRATION.md)** - Automated diagnostics setup
- **[🪟 Windows Deployment](./docs/WINDOWS_DEPLOYMENT.md)** - WinRM host onboarding

### Reference
- **[🔧 Troubleshooting](./docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[📊 API Guide](./docs/API_GUIDE.md)** - Zabbix API usage examples
- **[✅ Best Practices](./docs/BEST_PRACTICES.md)** - Production recommendations
- **[📋 Zabbix Actions](./docs/ZABBIX_ACTION_CONFIG.md)** - Alert action configuration

---

## 🔗 Integration

### Traefik Reverse Proxy

To integrate with Traefik, add these labels to `zabbix-web-nginx` service:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.zabbix.rule=Host(`zabbix.yourdomain.com`)"
  - "traefik.http.routers.zabbix.entrypoints=websecure"
  - "traefik.http.routers.zabbix.tls.certresolver=letsencrypt"
  - "traefik.http.services.zabbix.loadbalancer.server.port=8080"
```

### Grafana Visualization

Zabbix datasource plugin available for enhanced dashboards.

---

## 🛠️ Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs

# Verify secrets exist
ls -la env_vars/

# Regenerate secrets if needed
./scripts/generate-secrets.sh
```

### Database connection errors
```bash
# Check PostgreSQL health
docker exec zabbix-postgres pg_isready -U zabbix

# View database logs
docker-compose logs postgres-server
```

### Web interface not accessible
```bash
# Check if port is available
netstat -tulpn | grep 8080

# Verify container is running
docker ps | grep zabbix-web
```

**[📖 Full Troubleshooting Guide](./docs/TROUBLESHOOTING.md)**

---

## 📈 Monitoring Templates

Ready-to-use templates included in `templates/`:

- **Linux Servers** - CPU, memory, disk, network monitoring
- **Docker Containers** - Container metrics and health
- **Network Devices** - SNMP-based monitoring
- **Web Applications** - HTTP checks and performance
- **Zabbix Self-Monitoring** - Monitor the monitoring system

---

## 🤝 Support & Contributing

- **Official Docs**: https://www.zabbix.com/documentation/current/
- **Docker Hub**: https://hub.docker.com/u/zabbix/
- **GitHub**: https://github.com/zabbix/zabbix-docker
- **Community**: https://www.zabbix.com/forum/

---

## 📄 License

This implementation follows the official Zabbix Docker repository structure.
Zabbix is licensed under GPL v2.0.

---

## ⚡ Quick Reference

```bash
# Start everything
./scripts/init-setup.sh

# Health check
./scripts/health-check.sh

# Backup database
./scripts/backup-db.sh

# View logs
docker-compose logs -f

# Web access
http://localhost:8080
```

**Default Credentials:**
- Username: `Admin`
- Password: `zabbix`

---

<p align="center">
  Made with ❤️ for production monitoring | Zabbix 7.4 LTS
</p>
# Zabbix-Monitoring
# Zabbix-Monitoring

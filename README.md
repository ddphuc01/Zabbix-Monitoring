# Zabbix Monitoring System

<p align="center">
  <img src="https://assets.zabbix.com/img/logo/zabbix_logo_500x131.png" alt="Zabbix Logo" width="400"/>
</p>

<p align="center">
  <strong>Production-Ready Zabbix 7.4 LTS Monitoring Platform</strong><br/>
  Complete Docker-based deployment with all components
</p>

---

## 📋 Overview

This is a comprehensive, production-ready implementation of **Zabbix 7.4 LTS** monitoring system based on the official [Zabbix Docker repository](https://github.com/zabbix/zabbix-docker). It includes all core and advanced components configured for enterprise use.

### ✨ Features

- **🖥️ Complete Monitoring Stack** - All Zabbix components included
- **🔒 Security First** - Secrets management, network isolation, encrypted connections
- **📊 Production Ready** - Resource limits, health checks, automated backups
- **🚀 Easy Deployment** - One-command installation with automated setup
- **📈 Scalable Architecture** - Support for distributed monitoring with proxies
- **🔧 Fully Automated** - Scripts for backup, restore, and health monitoring

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
- 4GB RAM minimum (8GB recommended)
- 20GB free disk space
- Linux host (Ubuntu, Debian, CentOS, etc.)

### Installation

```bash
# Clone or download this repository
cd /home/phuc/zabbix-monitoring

# Run the automated installer
./scripts/init-setup.sh
```

The installer will:
1. ✅ Check prerequisites
2. 🔐 Generate secure secrets
3. 📁 Create directory structure
4. 🐳 Pull Docker images
5. 🚀 Start all services
6. ✔️  Verify health status

**Access Zabbix Web Interface:**
- URL: `http://localhost:8080`
- Username: `Admin`
- Password: `zabbix`

> ⚠️ **IMPORTANT**: Change the default password after first login!

---

## 📦 Components

| Component | Version | Purpose | Port |
|-----------|---------|---------|------|
| **Zabbix Server** | 7.4-alpine | Core monitoring engine | 10051 |
| **PostgreSQL** | 17-alpine | Primary database | 5432 (internal) |
| **Web Interface** | 7.4-alpine | Nginx + PHP-FPM UI | 8080, 8443 |
| **Agent 2** | 7.4-alpine | Modern monitoring agent | 10060 |
| **Java Gateway** | 7.4-alpine | JMX monitoring | 10052 |
| **Web Service** | 7.4-alpine | PDF report generation | 10053 |
| **SNMP Traps** | 7.4-alpine | Network device monitoring | 162/UDP |

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

- **[Installation Guide](./docs/INSTALLATION.md)** - Step-by-step setup instructions
- **[Architecture Overview](./docs/ARCHITECTURE.md)** - System design and components
- **[Troubleshooting](./docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[API Guide](./docs/API_GUIDE.md)** - Zabbix API usage examples
- **[Best Practices](./docs/BEST_PRACTICES.md)** - Production recommendations

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

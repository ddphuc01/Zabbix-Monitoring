# Zabbix Installation Guide

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 4GB
- Disk: 20GB free space
- OS: Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+, or similar)

**Recommended for Production:**
- CPU: 4-8 cores
- RAM: 8-16GB
- Disk: 100GB+ SSD
- OS: Ubuntu 22.04 LTS or Debian 12

### Software Requirements

- Docker Engine 20.10 or later
- Docker Compose 2.x or later
- Internet connection (for pulling images)

### Installing Docker (if not installed)

**Ubuntu/Debian:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**CentOS/RHEL:**
```bash
sudo yum install -y docker docker-compose
sudosystemctl enable --now docker
sudo usermod -aG docker $USER
```

Log out and back in for group changes to take effect.

---

## Installation Steps

### Step 1: Download Project

```bash
cd /home/phuc
git clone <repository-url> zabbix-monitoring
# OR if using existing files:
cd /home/phuc/zabbix-monitoring
```

### Step 2: Verify Directory Structure

```bash
ls -la
```

Expected files:
- `docker-compose.yml`
- `.env`
- `scripts/` directory
- `env_vars/` directory (or will be created)
- `README.md`

### Step 3: Run Installation Script

```bash
chmod +x scripts/*.sh
./scripts/init-setup.sh
```

The installer will:
1. Check Docker and Docker Compose
2. Generate secure passwords
3. Create directory structure
4. Pull Docker images (~2GB download)
5. Start all services
6. Verify component health

**Expected output:**
```
╔════════════════════════════════════════╗
║    Installation Complete! ✓            ║
╚════════════════════════════════════════╝
```

### Step 4: Verify Installation

```bash
# Check service status
docker-compose ps

# Run health check
./scripts/health-check.sh

# View logs
docker-compose logs -f
```

All services should show "Up" or "healthy" status.

### Step 5: Access Web Interface

Open browser to: `http://your-server-ip:8080`

**Default Credentials:**
- Username: `Admin` (capital A)
- Password: `zabbix`

> ⚠️ **SECURITY**: Change password immediately after login!

---

## Post-Installation Configuration

### 1. Change Admin Password

1. Login to web interface
2. Click user icon (top right) → "User profile"
3. Click "Change password"
4. Enter new strong password
5. Save

### 2. Configure Timezone

1. Go to "Administration" → "General"
2. Select "GUI" from dropdown
3. Set your timezone
4. Click "Update"

### 3. Set up Email Notifications

1. Go to "Administration" → "Media types"
2. Click "Email"
3. Configure SMTP server:
   ```
   SMTP server: smtp.gmail.com
   SMTP server port: 587
   SMTP helo: yourdomain.com
   SMTP email: your-email@gmail.com
   Authentication: Username and password
   Username: your-email@gmail.com
   Password: your-app-password
   ```
4. Test and save

### 4. Create User Accounts

1. Go to "Administration" → "Users"
2. Click "Create user"
3. Fill in details
4. Assign to user groups
5. Set up media (email, SMS, etc.)
6. Save

---

## Configuring Monitored Hosts

### Auto-Registration (Recommended)

1. Go to "Configuration" → "Actions"
2. Select "Autoregistration actions"
3. Create action "Auto-register Linux servers"
4. Conditions: `Host metadata` contains `Linux`
5. Operations:
   - Add host
   - Link to template "Linux by Zabbix agent active"
   - Add to host group "Linux servers"

### Manual Host Addition

1. Go to "Configuration" → "Hosts"
2. Click "Create host"
3. Fill in:
   - Host name: `server-01`
   - Groups: Select or create group
   - Interfaces: Add agent interface (IP + port 10050)
4. Go to "Templates" tab
5. Link template (e.g., "Linux by Zabbix agent")
6. Save

---

## Installing Zabbix Agent on Monitored Hosts

### Ubuntu/Debian
```bash
wget https://repo.zabbix.com/zabbix/7.4/ubuntu/pool/main/z/zabbix-release/zabbix-release_7.4-1+ubuntu$(lsb_release -rs)_all.deb
sudo dpkg -i zabbix-release_7.4-1+ubuntu$(lsb_release -rs)_all.deb
sudo apt update
sudo apt install zabbix-agent2
```

### Configure Agent
```bash
sudo vim /etc/zabbix/zabbix_agent2.conf
```

Edit:
```ini
Server=<zabbix-server-ip>
ServerActive=<zabbix-server-ip>:10051
Hostname=<this-host-fqdn>
```

Start agent:
```bash
sudo systemctl enable --now zabbix-agent2
sudo systemctl status zabbix-agent2
```

---

## Automated Backups

### Setup Daily Backup Cron Job

```bash
sudo crontab -e
```

Add:
```cron
# Daily Zabbix database backup at 2 AM
0 2 * * * /home/phuc/zabbix-monitoring/scripts/backup-db.sh >> /var/log/zabbix-backup.log 2>&1
```

### Test Backup
```bash
./scripts/backup-db.sh
ls -lh zbx_env/backups/
```

---

## SSL/TLS Configuration (Optional)

### Generate Self-Signed Certificate

```bash
cd zbx_env/var/lib/zabbix/ssl/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ../keys/nginx.key \
  -out nginx.crt \
  -subj "/C=VN/ST=HCM/L=HoChiMinh/O=MyOrg/CN=zabbix.local"
```

### Use Let's Encrypt (with Traefik)

Add to `docker-compose.yml` under `zabbix-web-nginx`:
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.zabbix.rule=Host(`zabbix.yourdomain.com`)"
  - "traefik.http.routers.zabbix.entrypoints=websecure"
  - "traefik.http.routers.zabbix.tls.certresolver=letsencrypt"
  - "traefik.http.services.zabbix.loadbalancer.server.port=8080"
networks:
  - traefik-network
```

---

## Upgrade Procedure

### Backup Before Upgrade
```bash
./scripts/backup-db.sh
```

### Upgrade Steps
```bash
cd /home/phuc/zabbix-monitoring

# Pull new images
docker-compose pull

# Stop services
docker-compose down

# Start with new images
docker-compose up -d

# Verify
./scripts/health-check.sh
```

---

## Uninstallation

### Remove Containers and Volumes
```bash
cd /home/phuc/zabbix-monitoring
docker-compose down -v
```

### Remove All Data (Warning: Destructive!)
```bash
rm -rf /home/phuc/zabbix-monitoring
```

---

## Next Steps

1. ✅ [Configure monitoring templates](./BEST_PRACTICES.md)
2. ✅ [Set up alerting](./API_GUIDE.md)
3. ✅ [Review architecture](./ARCHITECTURE.md)
4. ✅ [Learn troubleshooting](./TROUBLESHOOTING.md)

---

**Need Help?** Check the [Troubleshooting Guide](./TROUBLESHOOTING.md)

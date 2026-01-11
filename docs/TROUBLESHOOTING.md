# Zabbix Troubleshooting Guide

## Common Issues and Solutions

### 1. Containers Won't Start

**Symptoms:**
- Services exit immediately
- `docker-compose ps` shows "Exit 1" or "Exit 127"

**Solutions:**

**Check Secrets Exist:**
```bash
ls -la env_vars/
```

Should show:
- `.POSTGRES_USER`
- `.POSTGRES_PASSWORD`
- `.env_srv`

If missing:
```bash
./scripts/generate-secrets.sh
```

**Check Permissions:**
```bash
chmod 600 env_vars/.*
chmod -R 775 zbx_env/
```

**View Specific Service Logs:**
```bash
docker-compose logs postgres-server
docker-compose logs zabbix-server
```

---

### 2. Database Connection Errors

**Symptoms:**
- Zabbix Server logs: "cannot connect to database"
- Web interface:  "Error connecting to database"

**Solutions:**

**Check PostgreSQL Status:**
```bash
docker exec zabbix-postgres pg_isready -U zabbix
```

Should return: `accepting connections`

**Check Database Exists:**
```bash
docker exec zabbix-postgres psql -U zabbix -l
```

Should list `zabbix` database.

**Verify Credentials:**
```bash
cat env_vars/.POSTGRES_USER
cat env_vars/.POSTGRES_PASSWORD
```

**Reinitialize Database:**
```bash
docker-compose stop zabbix-server
docker-compose up -d server-db-init
docker-compose logs -f server-db-init
# Wait for "Exit 0"
docker-compose start zabbix-server
```

---

### 3. Web Interface Not Accessible

**Symptoms:**
- Browser shows "Connection refused"
- Port 8080 not responding

**Solutions:**

**Check Port Availability:**
```bash
netstat -tulpn | grep 8080
# OR
ss -tulpn | grep 8080
```

If port in use, change in `.env`:
```ini
ZABBIX_WEB_NGINX_HTTP_PORT=8090
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

**Check Container Status:**
```bash
docker ps | grep zabbix-web
```

Should show "Up" status.

**Check Nginx Logs:**
```bash
docker-compose logs zabbix-web-nginx
```

**Test Local Connection:**
```bash
curl -I http://localhost:8080
```

Should return HTTP 200 or 302.

---

### 4. Zabbix Server Not Starting

**Symptoms:**
- Container starts then exits
- Logs show configuration errors

**Solutions:**

**Check Logs:**
```bash
docker-compose logs zabbix-server | tail -100
```

**Common Errors:**

**"Cannot connect to Java Gateway":**
```bash
# Ensure Java Gateway is running
docker-compose ps zabbix-java-gateway

# Restart if needed
docker-compose restart zabbix-java-gateway zabbix-server
```

**"Cannot allocate memory":**
Reduce cache sizes in `env_vars/.env_srv`:
```ini
ZBX_CACHESIZE=64M
ZBX_HISTORYCACHESIZE=32M
ZBX_VALUECACHESIZE=64M
```

**Database schema outdated:**
```bash
# View server-db-init logs
docker-compose logs server-db-init

# Re-run initialization
docker-compose run --rm server-db-init
```

---

### 5. Agent Not Connecting

**Symptoms:**
- Host shows as "Down" or "Unknown"
- "ZBX" icon is red in web interface

**Solutions:**

**Check Network Connectivity:**
```bash
# From monitored host
telnet <zabbix-server-ip> 10051
# OR
nc -zv <zabbix-server-ip> 10051
```

**Check Agent Status:**
```bash
# On monitored host
sudo systemctl status zabbix-agent2
```

**Test Agent Connection:**
```bash
# On Zabbix Server
zabbix_get -s <agent-ip> -k agent.ping
```

Should return: `1`

**Check Agent Configuration:**
```bash
# On monitored host
sudo cat /etc/zabbix/zabbix_agent2.conf | grep -E "^Server|^ServerActive|^Hostname"
```

Should show correct Zabbix Server IP.

**Check Firewall:**
```bash
# On monitored host
sudo ufw status
sudo firewall-cmd --list-all

# Allow port if needed
sudo ufw allow 10050/tcp
sudo firewall-cmd --add-port=10050/tcp --permanent
```

---

### 6. High Resource Usage

**Symptoms:**
- Server sluggish
- `docker stats` shows high CPU/RAM

**Solutions:**

**Check Container Resource Usage:**
```bash
docker stats --no-stream
```

**Optimize Zabbix Server:**

Edit `env_vars/.env_srv`:
```ini
# Reduce pollers
ZBX_STARTPOLLERS=3
ZBX_STARTHTTPPOLLERS=1

# Reduce cache
ZBX_CACHESIZE=64M
ZBX_HISTORYCACHESIZE=32M
```

**Optimize PostgreSQL:**

Edit `docker-compose.yml`, add under `postgres-server` → `environment`:
```yaml
POSTGRES_SHARED_BUFFERS: 256MB
POSTGRES_EFFECTIVE_CACHE_SIZE: 1GB
POSTGRES_MAINTENANCE_WORK_MEM: 128MB
```

**Enable Database Partitioning:**

Connect to database:
```bash
docker exec -it zabbix-postgres psql -U zabbix -d zabbix
```

Run housekeeping:
```sql
CALL partition_maintenance('history', 7);
CALL partition_maintenance('history_uint', 7);
```

---

### 7. Java Gateway Issues

**Symptoms:**
- JMX monitoring not working
- Java items show "Not supported"

**Solutions:**

**Check Java Gateway Logs:**
```bash
docker-compose logs zabbix-java-gateway
```

**Verify Configuration:**

In `docker-compose.yml` under `zabbix-server`:
```yaml
environment:
  ZBX_JAVAGATEWAY_ENABLE: "true"
  ZBX_JAVAGATEWAY: zabbix-java-gateway
  ZBX_JAVAGATEWAYPORT: 10052
```

**Test JMX Connection:**
```bash
# Should show Java Gateway listening
docker exec zabbix-java-gateway netstat -tulpn | grep 10052
```

---

### 8. SNMP Traps Not Received

**Symptoms:**
- SNMP traps not appearing in Zabbix
- Log file empty

**Solutions:**

**Check SNMP Traps Container:**
```bash
docker-compose logs zabbix-snmptraps
```

**Verify Port Binding:**
```bash
sudo netstat -uln | grep162
```

Should show 0.0.0.0:162

**Test Trap Reception:**

Send test trap:
```bash
snmptrap -v 2c -c public <zabbix-server-ip>:162 '' 1.3.6.1.4.1.8072.2.3.0.1
```

Check logs:
```bash
docker exec zabbix-server cat /var/lib/zabbix/snmptraps/snmptraps.log
```

---

### 9. Report Generation Fails

**Symptoms:**
- PDF reports not generating
- Web Service errors in logs

**Solutions:**

**Check Web Service Status:**
```bash
docker-compose ps zabbix-web-service
```

**Check Logs:**
```bash
docker-compose logs zabbix-web-service
```

**Verify Connection:**

In `docker-compose.yml` under `zabbix-web-service`:
```yaml
environment:
  ZBX_ALLOWEDIP: zabbix-server
```

**Restart Service:**
```bash
docker-compose restart zabbix-web-service
```

---

### 10. Backup/Restore Issues

**Symptoms:**
- Backup script fails
- Restore doesn't complete

**Solutions:**

**Backup Fails:**
```bash
# Check disk space
df -h

# Check PostgreSQL access
docker exec zabbix-postgres pg_dump -U zabbix --version

# Manual backup
docker exec zabbix-postgres pg_dump -U zabbix zabbix | gzip > manual_backup.sql.gz
```

**Restore Fails:**
```bash
# Check backup file integrity
gunzip -t zbx_env/backups/zabbix_backup_*.sql.gz

# Manual restore
docker-compose stop zabbix-server
gunzip -c backup.sql.gz | docker exec -i zabbix-postgres psql -U zabbix -d zabbix
docker-compose start zabbix-server
```

---

## Performance Tuning

### Database Optimization

```sql
-- Connect to database
docker exec -it zabbix-postgres psql -U zabbix -d zabbix

-- Create indexes
CREATE INDEX history_1_clock ON history_uint USING BRIN (clock);
CREATE INDEX trends_1_clock ON trends_uint USING BRIN (clock);

-- Analyze tables
ANALYZE;

-- Vacuum
VACUUM ANALYZE;
```

### Zabbix Server Tuning

For 1000+ hosts, edit `env_vars/.env_srv`:
```ini
ZBX_STARTPOLLERS=10
ZBX_STARTHTTPPOLLERS=5
ZBX_CACHESIZE=256M
ZBX_HISTORYCACHESIZE=128M
ZBX_VALUECACHESIZE=256M
```

---

## Log Locations

| Component | Log Location |
|-----------|-------------|
| Zabbix Server | `docker-compose logs zabbix-server` |
| Web Interface | `docker-compose logs zabbix-web-nginx` |
| PostgreSQL | `docker-compose logs postgres-server` |
| Agent | `/var/log/zabbix/zabbix_agent2.log` (on host) |
| SNMP Traps | `docker exec zabbix-server cat /var/lib/zabbix/snmptraps/snmptraps.log` |

---

## Emergency Recovery

### Complete System Reset

⚠️ **WARNING: This will delete all data!**

```bash
cd /home/phuc/zabbix-monitoring

# Stop and remove everything
docker-compose down -v

# Remove data
rm -rf zbx_env/*
rm env_vars/.*

# Reinitialize
./scripts/init-setup.sh
```

### Restore from Backup Only

```bash
# Stop services
docker-compose stop

# Restore database
./scripts/restore-db.sh

# Start services
docker-compose start

# Verify
./scripts/health-check.sh
```

---

## Getting More Help

**Official Resources:**
- [Zabbix Documentation](https://www.zabbix.com/documentation/current/)
- [Zabbix Forums](https://www.zabbix.com/forum/)
- [GitHub Issues](https://github.com/zabbix/zabbix-docker/issues)

**Log Analysis:**
```bash
# View all logs with timestamps
docker-compose logs --timestamps --tail=100

# Follow logs in real-time
docker-compose logs -f

# Export logs to file
docker-compose logs > zabbix-debug.log
```

**System Information:**
```bash
# Docker version
docker version

# Docker Compose version
docker-compose version

# System resources
free -h
df -h
docker system df
```

---

**Still having issues?** Collect the above information and seek help on [Zabbix Community Forums](https://www.zabbix.com/forum/).

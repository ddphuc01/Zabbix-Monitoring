# Zabbix Best Practices Guide

## Production Deployment

### Server Sizing

**Small Environment (< 100 hosts):**
- CPU: 2 cores
- RAM: 4GB
- Disk: 50GB
- Database: Keep 30 days of data

**Medium Environment (100-1000 hosts):**
- CPU: 4 cores
- RAM: 8GB
- Disk: 200GB SSD
- Database: Keep 30 days detailed, 1 year trends

**Large Environment (1000+ hosts):**
- CPU: 8+ cores
- RAM: 16GB+
- Disk: 500GB+ SSD with RAID
- Database: TimescaleDB with partitioning
- Consider database on separate server

### Database Optimization

**1. Use TimescaleDB (Recommended for large deployments):**

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Convert tables to hypertables
SELECT create_hypertable('history', 'clock', chunk_time_interval => 86400);
SELECT create_hypertable('history_uint', 'clock', chunk_time_interval => 86400);
SELECT create_hypertable('trends', 'clock', chunk_time_interval => 2592000);
SELECT create_hypertable('trends_uint', 'clock', chunk_time_interval => 2592000);
```

**2. Implement Partitioning:**

Edit `env_vars/.env_srv`:
```ini
ZBX_HISTORYSTORAGEURL=
ZBX_HISTORYSTORAGEDATEINDEX=1
```

**3. Configure Housekeeping:**

```ini
ZBX_HOUSEKEEPINGFREQUENCY=1
ZBX_MAXHOUSEKEEPERDELETE=5000
ZBX_OVERRIDE_EVENT_DB_HISTORY_DAYS=7
ZBX_OVERRIDE_ITEM_DB_HISTORY_DAYS=30
ZBX_OVERRIDE_ITEM_DB_TRENDS_DAYS=365
```

---

## Monitoring Strategy

### 1. Template Organization

**Create Template Hierarchy:**
```
Template OS Linux
├── Template App SSH Service
├── Template App Docker
│   └── Template App Docker Swarm
└── Template Module CPU
```

**Best Practices:**
- Use template inheritance
- Keep templates focused (one service per template)
- Use macros for flexibility
- Tag templates properly

### 2. Item Collection

**Optimize Update Intervals:**

| Metric Type | Update Interval | Keep History |
|-------------|-----------------|--------------|
| Critical (CPU, Memory) | 1m | 7 days |
| Important (Disk, Network) | 5m | 14 days |
| Less Important | 10-30m | 7 days |
| Static (OS version) | 1h or 1d | 30 days |

**Use Active vs Passive Checks:**
- **Active**: Agent pushes data to server (better scalability)
- **Passive**: Server polls agent (better for firewalled environments)

**Recommendation**: Use active checks for most items.

### 3. Trigger Configuration

**Trigger Severity Guidelines:**

| Severity | Usage | Example |
|----------|-------|---------|
| Disaster (5) | Service down | Web server not responding |
| High (4) | Critical resource | Disk > 90% full |
| Average (3) | Important metrics | CPU > 80% for 5min |
| Warning (2) | Early warning | Memory > 70% |
| Information (1) | FYI | Service restarted |

**Trigger Expression Tips:**

```javascript
// ✓ Good: Use averaging to avoid false alarms// CPU > 90% for 5 minutes
last(/Linux/system.cpu.util,#5)>90

// ✓ Better: Hysteresis to prevent flapping
(last(/Linux/system.cpu.util)>90 and
 min(/Linux/system.cpu.util,5m)>90)

// ✗ Bad: Single check, prone to false positives
last(/Linux/system.cpu.util)>90
```

### 4. Alert Fatigue Prevention

**Implement Escalations:**
1. First notification: Email to on-call engineer
2. After 15 min: SMS
3. After 30 min: Call manager
4. After 1 hour: Execute auto-remediation script

**Use Dependencies:**
- Link application triggers to infrastructure triggers
- If router down, suppress all hosts behind it

**Maintenance Windows:**
- Schedule maintenance for known changes
- Suppress alerts during maintenance

---

## Performance Tuning

### Zabbix Server

**Edit `env_vars/.env_srv`:**

```ini
# Increase for more polling capacity
ZBX_STARTPOLLERS=10
ZBX_STARTPOLLERSUNREACHABLE=2
ZBX_STARTHTTPPOLLERS=5

# Increase cache for large environments
ZBX_CACHESIZE=256M
ZBX_HISTORYCACHESIZE=128M
ZBX_HISTORYSIZEINDEXCACHESIZE=32M
ZBX_TRENDCACHESIZE=64M
ZBX_VALUECACHESIZE=256M

# Optimize timeouts
ZBX_TIMEOUT=4
ZBX_UNREACHABLEPERIOD=45
ZBX_UNAVAILABLEDELAY=60

# Database optimization
ZBX_STARTDBSYNCERS=8
```

### PostgreSQL

Add to `docker-compose.yml` under `postgres-server`:

```yaml
command:
  - "postgres"
  - "-c"
  - "max_connections=200"
  - "-c"
  - "shared_buffers=1GB"
  - "-c"
  - "effective_cache_size=4GB"
  - "-c"
  - "maintenance_work_mem=256MB"
  - "-c"
  - "checkpoint_completion_target=0.9"
  - "-c"
  - "wal_buffers=16MB"
  - "-c"
  - "default_statistics_target=100"
  - "-c"
  - "random_page_cost=1.1"
  - "-c"
  - "effective_io_concurrency=200"
  - "-c"
  - "work_mem=5242kB"
  - "-c"
  - "min_wal_size=1GB"
  - "-c"
  - "max_wal_size=4GB"
```

---

## Security Hardening

### 1. Change Default Credentials

**Immediately after installation:**
```sql
-- Change Admin password
docker exec -it zabbix-postgres psql -U zabbix -d zabbix -c \
  "UPDATE users SET passwd=md5('NewStrongPassword123!') WHERE username='Admin';"
```

### 2. Disable Guest Access

Web UI: Administration → Authentication → Disable guest access

### 3. Implement User Roles

**Create role structure:**
- **Super Admin**: Full access (1-2 users)
- **Admin**: Configuration, no user management
- **Operator**: View + acknowledge problems
- **Read-only**: View only

### 4. Enable HTTPS

**Option A: Use Traefik (Recommended)**

Already configured in your infrastructure.

**Option B: Self-signed certificate:**

```bash
cd zbx_env/var/lib/zabbix/ssl/
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout keys/nginx.key -out certs/nginx.crt
```

### 5. API Token Management

- Use API tokens instead of passwords
- Rotate tokens regularly
- Limit token permissions
- Log API access

### 6. Database Security

- Use strong passwords (already generated)
- Restrict database network (already internal-only)
- Regular backups
- Encrypt connections (configure TLS)

---

## High Availability

### Active-Passive Cluster

**Architecture:**
```
Load Balancer (Virtual IP)
    ↓
Zabbix Server 1 (Active) ← Database Replication → Zabbix Server 2 (Standby)
    ↓                                                     ↓
PostgreSQL Primary  ←──── Streaming Replication ────→ PostgreSQL Replica
```

**Implementation:**
1. Set up PostgreSQL streaming replication
2. Configure heartbeat/keepalived for VIP
3. Use shared storage for config files
4. Automate failover scripts

### Load Balancing Web Interface

```yaml
# Add multiple web instances
zabbix-web-nginx-1:
  ...
zabbix-web-nginx-2:
  ...

# Use external load balancer (HAProxy/Nginx)
```

---

## Backup Strategy

### What to Backup

**Critical:**
1. Database (automated via `backup-db.sh`)
2. Configuration files (`env_vars/`)
3. Custom scripts (`zbx_env/usr/lib/zabbix/`)
4. SSL certificates (`zbx_env/var/lib/zabbix/ssl/`)

**Nice to have:**
5. Zabbix exports (templates, hosts)

### Backup Schedule

```bash
# Daily database backup (2 AM)
0 2 * * * /home/phuc/zabbix-monitoring/scripts/backup-db.sh

# Weekly configuration export (Sunday 3 AM)
0 3 * * 0 /home/phuc/zabbix-monitoring/scripts/export-config.sh

# Copy to remote location (4 AM)
0 4 * * * rsync -az /home/phuc/zabbix-monitoring/zbx_env/backups/ backup-server:/zabbix-backups/
```

### Disaster Recovery Plan

**Recovery Time Objective (RTO): < 1 hour**

1. Install fresh Zabbix (10 min)
2. Restore database from backup (20 min)
3. Restore configuration files (5 min)
4. Verify and test (15 min)

---

## Monitoring Best Practices Checklist

### Initial Setup
- [ ] Change default Admin password
- [ ] Disable guest access
- [ ] Configure timezone
- [ ] Set up email notifications
- [ ] Configure HTTPS
- [ ] Enable automated backups

### Host Configuration
- [ ] Use meaningful host names
- [ ] Apply consistent naming convention
- [ ] Use host groups logically
- [ ] Tag hosts appropriately
- [ ] Document in inventory fields

### Item Configuration
- [ ] Use appropriate update intervals
- [ ] Set realistic history retention
- [ ] Use active checks when possible
- [ ] Implement preprocessing
- [ ] Use value mapping

### Trigger Configuration
- [ ] Use averaging to reduce false positives
- [ ] Implement severity correctly
- [ ] Add trigger dependencies
- [ ] Use meaningful trigger names
- [ ] Include recovery expressions

### Alert Configuration
- [ ] Configure escalations
- [ ] Set up maintenance windows
- [ ] Test notifications regularly
- [ ] Document runbooks
- [ ] Implement on-call rotation

---

## Maintenance Tasks

### Daily
- Monitor active problems
- Check service health (`health-check.sh`)
- Review new alerts

### Weekly
- Review performance metrics
- Check database size growth
- Analyze slow queries
- Review and acknowledge old alerts

### Monthly
- Review and update templates
- Audit user access
- Test backup restoration
- Review capacity planning
- Update documentation

### Quarterly
- Review SLAs/SLOs
- Optimize item intervals
- Clean up unused hosts/templates
- Update Zabbix version
- Security audit

---

## Integration Examples

### Slack Notifications

Create `alertscripts/slack.sh`:
```bash
#!/bin bash
WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
MESSAGE="$1"

curl -X POST -H 'Content-type: application/json' \
  --data "{\"text\":\"${MESSAGE}\"}" \
  "${WEBHOOK}"
```

### ServiceNow Integration

Use Zabbix webhook media type with ServiceNow API.

### Grafana Dashboards

1. Install Zabbix plugin in Grafana
2. Configure Zabbix datasource
3. Create enhanced visualizations

---

## Cost Optimization

### Reduce Data Retention

For non-critical metrics:
- History: 7 days → 3 days
- Trends: 365 days → 90 days

### Use Calculated Items

Instead of storing raw values, calculate on-demand:
```
// Store: bytes received
// Calculate on-demand: MB/s
last(//net.if.in[eth0])/1024/1024
```

### Implement Data Compression

PostgreSQL: Enable table compression
TimescaleDB: Use compression policies

---

This guide should help you build and maintain a robust, efficient, and secure Zabbix monitoring infrastructure!

# Hướng dẫn Fix Setup cho UAT Server

## 🎯 Vấn đề

UAT Server gặp lỗi "Permission denied" khi đọc Docker secrets do:
- Docker secrets trong Compose mode không reliable trên mọi môi trường
- File permissions và user namespaces khác nhau giữa các hệ thống
- SELinux/AppArmor có thể block file mounts

## ✅ Giải pháp

Đã refactor để support **Official Zabbix Docker pattern** sử dụng `.env_db_pgsql` file thay vì secrets.

### Ưu điểm:
- ✅ Work 100% trên mọi Docker environment
- ✅ Follow official Zabbix Docker repository pattern
- ✅ Dễ debug và troubleshoot
- ✅ Backward compatible với setup hiện tại

---

## 📋 Trên UAT Server - Chạy các lệnh sau:

### Bước 1: Pull code mới nhất
```bash
cd /home/pnj/Zabbix-Monitoring
git pull origin main
```

### Bước 2: Chạy pre-flight check
```bash
./scripts/pre-flight-check.sh
```

**Kết quả expected:**
- ✓ Docker và Docker Compose installed
- ✓ Ít nhất 4GB RAM (6GB+ recommended)
- ✓ 20GB+ disk space
- ⚠ Port warnings (nếu có services cũ đang chạy)

### Bước 3: Stop containers cũ
```bash
docker compose down
```

### Bước 4: Regenerate secrets
```bash
# Xóa secrets cũ (nếu có lỗi)
rm -rf env_vars/.POSTGRES_* env_vars/.MYSQL_* env_vars/.env_srv env_vars/.env_db_pgsql

# Generate lại
./scripts/generate-secrets.sh
```

**Kết quả expected:**
```
✓  Created POSTGRES_USER
✓  Created POSTGRES_PASSWORD
✓  Created .env_srv
✓  Created .env_db_pgsql
```

### Bước 5: Verify files generated
```bash
ls -la env_vars/
```

**Should see:**
- `.env_db_pgsql` (600 permissions) - **MỚI, quan trọng!**
- `.POSTGRES_PASSWORD` (600)
- `.POSTGRES_USER` (600)
- `.env_srv` (644)

### Bước 6: Start services
```bash
docker compose up -d
```

**Monitor logs:**
```bash
# Xem logs real-time
docker compose logs -f zabbix-server postgres-server

# Hoặc check status
docker compose ps
```

### Bước 7: Wait & Verify
```bash
# Đợi 60 giây
sleep 60

# Check health
docker compose ps

# Run health check script
./scripts/health-check.sh
```

**Expected output:**
- PostgreSQL: `(healthy)`
- Zabbix Server: `(healthy)`
- Zabbix Web: `(healthy)`

---

## 🔍 Troubleshooting

### Nếu vẫn lỗi "Permission denied":

**Option 1: Sử dụng docker-compose.override.yml (Quick fix)**

```bash
cd /home/pnj/Zabbix-Monitoring

# Đọc password từ file
POSTGRES_PASS=$(cat env_vars/.POSTGRES_PASSWORD)
POSTGRES_USER=$(cat env_vars/.POSTGRES_USER)

# Tạo override file
cat > docker-compose.override.yml << EOF
version: '3.8'

services:
  postgres-server:
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASS}
      POSTGRES_DB: zabbix
    secrets: []

  zabbix-server:
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASS}
    secrets: []
    
  zabbix-web-nginx:
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASS}
    secrets: []
EOF

# Restart
docker compose down -v
docker compose up -d
```

### Nếu PostgreSQL không start:

```bash
# Check logs chi tiết
docker compose logs postgres-server

# Xóa volume cũ nếu bị corrupt
docker compose down -v
docker volume rm zabbix-monitoring_postgres-data

# Start lại
docker compose up -d
```

### Nếu port conflicts:

```bash
# Check port đang dùng
netstat -tuln | grep -E ':(8080|10051|5432)'

# Stop service cũ hoặc change port trong .env
# Ví dụ:
echo "ZABBIX_WEB_NGINX_HTTP_PORT=8081" >> .env
```

---

## 📊 So sánh Changes

### Trước (Old way):
```yaml
# docker-compose.yml
postgres-server:
  environment:
    POSTGRES_PASSWORD_FILE: /run/secrets/POSTGRES_PASSWORD  # ❌ Fails on some systems
  secrets:
    - POSTGRES_PASSWORD
```

### Sau (New way):
```yaml
# docker-compose.yml  
postgres-server:
  env_file:
    - path: ${ENV_VARS_DIRECTORY}/.env_db_pgsql  # ✅ Works everywhere
      required: false
  environment:
    POSTGRES_PASSWORD_FILE: /run/secrets/POSTGRES_PASSWORD  # Fallback
  secrets:
    - POSTGRES_PASSWORD  # Fallback
```

**File: env_vars/.env_db_pgsql**
```bash
POSTGRES_USER=zabbix
POSTGRES_PASSWORD=nEArpbRbcF8bl0ud1OyD3ujmX  # Auto-generated
POSTGRES_DB=zabbix
```

---

## ✨ New Features Added

### 1. Pre-flight Check Script
```bash
./scripts/pre-flight-check.sh
```

Checks:
- Docker version
- RAM & disk space
- Port availability
- .env configuration
- Database files
- SELinux/AppArmor status

### 2. Auto .env_db_pgsql Generation
```bash
./scripts/generate-secrets.sh
```

Now creates:
- Individual secret files (backward compatible)
- `.env_db_pgsql` (new, official pattern)
- Proper file permissions automatically

### 3. Dual-mode Support

System tự động detect và dùng:
1. `.env_db_pgsql` file nếu có → **Recommended**
2. Docker secrets nếu không có .env_db_pgsql → Fallback
3. Environment variables → Last resort

---

## 🎓 Root Cause Explained

**Tại sao máy dev work mà UAT fail?**

| Factor | Dev Machine | UAT Server | Result |
|--------|-------------|------------|--------|
| Docker | Desktop with bypasses | Engine strict mode | Different behavior |
| User namespace | Default | May have remapping | Permission issues |
| SELinux/AppArmor | Disabled | May be enforcing | Mount blocked |
| Filesystem | Local ext4 | May be NFS/network | Different permissions |

**Solution:** Sử dụng `.env` file thay vì bind-mounted secrets = work on ALL systems!

---

## 📝 Verification Checklist

Sau khi setup xong, verify:

- [ ] `docker compose ps` - All services `(healthy)`
- [ ] `curl http://localhost:8080` - Returns Zabbix login page
- [ ] Login `Admin`/`zabbix` - Successfully login
- [ ] Check monitoring data - Graphs showing
- [ ] Test Telegram bot - `/start` responds
- [ ] AI webhook - `/health` returns OK

---

## 🚀 Next Steps

1. Update other documentation files to reference new pattern
2. Add monitoring for permission issues
3. Create migration guide từ secrets → env_file cho existing deployments

---

*Document created: 2026-01-19*  
*Updated docker-compose.yml to support official Zabbix Docker pattern*

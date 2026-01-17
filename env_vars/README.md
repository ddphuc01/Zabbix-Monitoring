# Docker Secrets for Zabbix

This directory contains sensitive credentials used by Docker services.

## ⚠️ CRITICAL: Never Commit These Files

All files in this directory (except this README) are protected by `.gitignore`.

## Files

- `.POSTGRES_USER` - PostgreSQL username
- `.POSTGRES_PASSWORD` - PostgreSQL password
- `.env_srv` - Zabbix Server environment variables
- `.gitkeep` - Keeps directory in Git

## Setup

Run the generator script to create secrets:

```bash
cd /home/phuc/zabbix-monitoring
./scripts/generate-secrets.sh
```

This creates all required secret files with secure random passwords.

## Manual Creation

If you need to create secrets manually:

```bash
# PostgreSQL username
echo "zabbix" > .POSTGRES_USER

# PostgreSQL password (generate strong password!)
openssl rand -base64 32 > .POSTGRES_PASSWORD

# Set proper permissions
chmod 600 .POSTGRES_*
```

## Security Best Practices

1. ✅ Use strong passwords (32+ characters)
2. ✅ Set file permissions to 600 (read/write owner only)
3. ✅ Never echo passwords in terminal
4. ✅ Rotate credentials regularly
5. ❌ Never commit to Git
6. ❌ Never share via email/chat

## Verification

```bash
# Check permissions
ls -la

# Should show:
# -rw------- (600) for secret files
# -rw-r--r-- (644) for README.md
```

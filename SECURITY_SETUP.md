# Security Setup Guide

## ⚠️ IMPORTANT: Protecting Sensitive Files

This project contains sensitive credentials that must **NEVER** be committed to Git.

---

## 📋 Quick Setup Checklist

### 1. Create Your Environment File

```bash
# Copy the template
cp .env.example .env

# Edit with your actual credentials
nano .env  # or vim, code, etc.
```

### 2. Fill in Required Credentials

Update these critical values in `.env`:

| Variable | Where to Get |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram |
| `TELEGRAM_CHAT_ID` | Send message to bot, then check `https://api.telegram.org/bot<TOKEN>/getUpdates` |
| `GROQ_API_KEY` | [Groq Console](https://console.groq.com) (FREE 14,400 req/day) |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `SMTP_PASSWORD` | [Gmail App Password](https://myaccount.google.com/apppasswords) |
| `WEBUI_SECRET_KEY` | Generate: `openssl rand -hex 32` |

### 3. Secure Docker Secrets

```bash
# Generate PostgreSQL credentials
./scripts/generate-secrets.sh

# This creates files in env_vars/ directory
# These are already in .gitignore
```

### 4. Verify Protection

```bash
# Check that .env is NOT tracked
git status

# Should NOT show .env in changes
# If it does, run: git rm --cached .env
```

---

## 🔒 Protected Files (Already in .gitignore)

- ✅ `.env` - Main environment file
- ✅ `env_vars/.*` - Docker secrets (PostgreSQL, etc.)
- ✅ `ssh-keys/*` - Ansible SSH keys
- ✅ `ansible/vault_*` - Ansible vault files
- ✅ `zbx_env/` - Zabbix persistent data
- ✅ Database backups (`*.sql`, `*.sql.gz`)
- ✅ Log files and artifacts

---

## 🚨 If You Already Committed Secrets

### Option 1: Remove from Last Commit (If Not Pushed)

```bash
git rm --cached .env
git commit --amend -m "Remove sensitive .env file"
```

### Option 2: Clean Git History (If Already Pushed)

**⚠️ WARNING: This rewrites history!**

```bash
# Install BFG Repo-Cleaner
# https://rtyley.github.io/bfg-repo-cleaner/

# Remove .env from all history
bfg --delete-files .env

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push (⚠️ coordinate with team!)
git push --force
```

### Option 3: Rotate All Credentials

If secrets are already public:
1. ❌ **Immediately revoke** all exposed credentials
2. 🔄 Generate new API keys/tokens
3. ✅ Update `.env` with new values
4. 🔐 Commit only `.env.example`

---

## 📝 Safe to Commit

These files **ARE safe** to push to GitHub:

- ✅ `.env.example` - Template with placeholders
- ✅ `docker-compose.yml` - No secrets here
- ✅ `README.md` - Documentation
- ✅ `scripts/*` - Automation scripts
- ✅ `docs/*` - Documentation
- ✅ `.gitignore` - Protection rules

---

## 🔐 Best Practices

### 1. Never Hardcode Secrets
```bash
# ❌ BAD
TELEGRAM_BOT_TOKEN=123456:ABC-DEF  

# ✅ GOOD - Use environment variables
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
```

### 2. Use Docker Secrets for Production
```yaml
secrets:
  my_secret:
    external: true  # Loaded from Docker Swarm/Kubernetes
```

### 3. Rotate Credentials Regularly
- Change passwords every 90 days
- Regenerate API keys quarterly
- Review access logs monthly

### 4. Use App-Specific Passwords
- Gmail: Create app password, not main password
- Never reuse passwords across services

### 5. Limit Access
- Use read-only API keys where possible
- Set IP whitelist restrictions
- Enable 2FA on all accounts

---

## 🆘 Emergency Response

If you accidentally pushed secrets:

1. ⏱️ **Act immediately** (every second counts!)
2. 🔄 Rotate all exposed credentials
3. 🔍 Check for unauthorized access
4. 📋 Follow cleanup guide above
5. 📢 Notify team members

---

## 📞 Support

- Check [TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)
- Review [BEST_PRACTICES.md](./docs/BEST_PRACTICES.md)
- Open an issue if you need help

---

**Remember:** Security is everyone's responsibility! 🔐

# Post-Installation Configuration

This playbook automatically configures Zabbix after deployment.

## What It Does

1. **Fixes Zabbix Server Interface**
   - Updates "Zabbix server" host interface from `127.0.0.1` to `zabbix-agent2` container
   - Ensures monitoring works correctly in Docker environment

2. **Validates Configuration**
   - Waits for Zabbix API to be ready
   - Verifies interface update was successful
   - Provides clear success/failure messages

## Usage

### Quick Run

```bash
# After running docker compose up -d
./scripts/post-install-config.sh
```

### Manual Run (inside container)

```bash
docker compose exec ansible-executor ansible-playbook \
  /ansible/playbooks/setup/post_install_config.yml
```

### With Custom Credentials

```bash
# Set environment variables
export ZABBIX_URL="http://your-server:8080"
export ZABBIX_API_USER="Admin"
export ZABBIX_API_PASSWORD="your-password"

# Run script
./scripts/post-install-config.sh
```

## When to Use

Run this playbook:
- ✅ **After first deployment** - Fix default Zabbix server interface
- ✅ **After recreating containers** - Reconfigure if containers were removed
- ✅ **After database restore** - Ensure interface is correct

**You do NOT need to run this:**
- ❌ After restarting containers (config persists in database)
- ❌ Multiple times (idempotent - safe but unnecessary)

## Troubleshooting

### Error: "Cannot connect to Zabbix API"

**Cause:** Zabbix services not ready yet

**Fix:**
```bash
# Wait for services to fully start
docker compose ps
docker compose logs zabbix-server | tail -20

# Retry after 1-2 minutes
./scripts/post-install-config.sh
```

### Error: "Authentication failed"

**Cause:** Incorrect API credentials

**Fix:**
```bash
# Check if you changed default password
# Update .env file:
ZABBIX_API_PASSWORD=your_new_password

# Or override temporarily:
export ZABBIX_API_PASSWORD="your_password"
./scripts/post-install-config.sh
```

### Error: "community.zabbix collection not found"

**Cause:** Ansible collection not installed

**Fix:**
```bash
docker compose exec ansible-executor \
  ansible-galaxy collection install -r /ansible/requirements.yml
```

## Integration with Init Setup

To run automatically after deployment, the `init-setup.sh` script will call this automatically.

## Files

- `playbooks/setup/post_install_config.yml` - Main Ansible playbook
- `scripts/post-install-config.sh` - Wrapper script for easy execution
- `ansible/requirements.yml` - Ansible dependencies (includes community.zabbix)

## Future Enhancements

This playbook can be extended to:
- Configure AI webhook integration automatically
- Setup default alert actions
- Import templates
- Configure user permissions
- Enable/disable features based on `.env` settings

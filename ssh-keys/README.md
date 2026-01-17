# SSH Keys for Ansible

This directory stores SSH keys used by Ansible for managing remote hosts.

## ⚠️ SECURITY WARNING

**NEVER commit private keys to Git!**

This directory is protected by `.gitignore` to prevent accidental commits.

## Setup Instructions

### 1. Generate SSH Key Pair

```bash
ssh-keygen -t rsa -b 4096 -f ansible_key -C "ansible@zabbix-monitoring"
```

This creates:
- `ansible_key` - Private key (NEVER share!)
- `ansible_key.pub` - Public key (safe to share)

### 2. Copy Public Key to Target Hosts

```bash
# For Linux hosts
ssh-copy-id -i ansible_key.pub user@target-host

# OR manually
cat ansible_key.pub | ssh user@target-host "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### 3. Set Proper Permissions

```bash
chmod 600 ansible_key
chmod 644 ansible_key.pub
```

### 4. Configure Ansible Inventory

Update `ansible/inventory/hosts.yml`:

```yaml
all:
  children:
    linux_hosts:
      hosts:
        myserver:
          ansible_host: 192.168.1.100
          ansible_user: root
          ansible_ssh_private_key_file: /path/to/ssh-keys/ansible_key
```

## Files

- `ansible_key` - Private key (gitignored)
- `ansible_key.pub` - Public key (gitignored)
- `README.md` - This file (safe to commit)

## Troubleshooting

**Permission denied:**
```bash
# Check key permissions
ls -la ansible_key

# Should show: -rw------- (600)
chmod 600 ansible_key
```

**Key not found:**
```bash
# Verify key exists
ls -la

# Regenerate if needed
ssh-keygen -t rsa -b 4096 -f ansible_key
```

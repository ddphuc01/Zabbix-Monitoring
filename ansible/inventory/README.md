# Ansible Inventory

This directory contains your Ansible inventory files defining managed hosts.

## ⚠️ SECURITY WARNING

**NEVER commit `hosts.yml` to Git!**

This file contains:
- 🔐 Host IP addresses
- 🔐 Usernames
- 🔐 Passwords (especially for Windows hosts!)
- 🔐 SSH key paths

---

## 📋 Setup Instructions

### 1. Create Your Inventory

```bash
# Copy the template
cp hosts.yml.example hosts.yml

# Edit with your actual hosts
nano hosts.yml  # or vim, code, etc.
```

### 2. Add Your Hosts

Example for Linux host:
```yaml
linux_hosts:
  hosts:
    web-server-01:
      ansible_host: 192.168.1.100
      ansible_user: root
      ansible_ssh_private_key_file: /path/to/ssh-keys/ansible_key
```

Example for Windows host:
```yaml
windows:
  hosts:
    win-server-01:
      ansible_host: 192.168.1.200
      ansible_user: Administrator
      ansible_password: 'SecurePassword123!'
      zabbix_hostid: win-001
```

### 3. Security Best Practices

#### ❌ DON'T Store Passwords in Plaintext

Instead of:
```yaml
ansible_password: 'MyPassword123'  # ❌ BAD
```

Use Ansible Vault:
```bash
# Create vault file
ansible-vault create vault_passwords.yml

# Add password
windows_admin_password: 'MyPassword123'

# Reference in hosts.yml
ansible_password: "{{ windows_admin_password }}"
```

#### ✅ DO Use SSH Keys for Linux

```bash
# Generate key
ssh-keygen -t rsa -b 4096 -f ../ssh-keys/ansible_key

# Copy to target
ssh-copy-id -i ../ssh-keys/ansible_key.pub user@target-host

# Reference in hosts.yml
ansible_ssh_private_key_file: /path/to/ssh-keys/ansible_key
```

---

## 🧪 Testing Connectivity

```bash
# Test all hosts
ansible -i hosts.yml all -m ping

# Test specific group
ansible -i hosts.yml linux_hosts -m ping
ansible -i hosts.yml windows -m ping

# Test single host
ansible -i hosts.yml web-server-01 -m ping
```

---

## 📁 Files

- `hosts.yml` - **YOUR ACTUAL INVENTORY** (gitignored, never commit!)
- `hosts.yml.example` - Template with examples (safe to commit)
- `README.md` - This file (safe to commit)

---

## 🔒 Protection Status

✅ `hosts.yml` is protected by `.gitignore`  
✅ Will NOT be committed to Git  
✅ Template `hosts.yml.example` is safe to share

---

## 📚 More Info

- [Ansible Inventory Documentation](https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html)
- [Ansible Vault Guide](https://docs.ansible.com/ansible/latest/user_guide/vault.html)
- [WinRM Setup for Windows](https://docs.ansible.com/ansible/latest/user_guide/windows_setup.html)

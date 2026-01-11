#!/bin/bash
# Deploy Zabbix Agent to Windows using Ansible

TARGET_HOST="${1:-win-pc-129}"

echo "=========================================="
echo "  Ansible Windows Agent Deployment"
echo "=========================================="
echo ""
echo "Target: $TARGET_HOST"
echo "Method: Ansible + WinRM"
echo ""

# Check if pywinrm is installed
echo "[1/4] Checking dependencies..."
docker exec zabbix-ansible-executor pip list | grep -q pywinrm
if [ $? -ne 0 ]; then
    echo "  Installing pywinrm..."
    docker exec zabbix-ansible-executor pip install pywinrm
fi
echo "  ✓ Dependencies OK"

# Test WinRM connectivity
echo ""
echo "[2/4] Testing WinRM connectivity to 192.168.1.129..."
docker exec zabbix-ansible-executor python3 << 'PYEOF'
import winrm
try:
    session = winrm.Session('192.168.1.129', auth=('rog', '123'), transport='ntlm')
    result = session.run_cmd('echo', ['Connection test'])
    if result.status_code == 0:
        print("  ✓ WinRM connection successful")
    else:
        print(f"  ✗ WinRM test failed: {result.std_err.decode()}")
except Exception as e:
    print(f"  ✗ Cannot connect via WinRM: {e}")
    print("")
    print("  WinRM may not be enabled on Windows host.")
    print("  Enable with:")
    print("    winrm quickconfig")
    print("    Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value '*' -Force")
PYEOF

echo ""
echo "[3/4] Running Ansible playbook..."
docker exec zabbix-ansible-executor \
    ansible-playbook /ansible/playbooks/deploy/deploy_agent_windows.yml \
    -i /ansible/inventory/hosts.yml \
    -e "target_host=$TARGET_HOST" \
    -v

echo ""
echo "[4/4] Deployment complete!"
echo ""
echo "Check Zabbix UI: http://192.168.1.203:8080"
echo "Configuration → Hosts → Look for 'WIN-PC-129'"
echo ""

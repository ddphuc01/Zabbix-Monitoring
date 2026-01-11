#!/usr/bin/env python3
"""
Deploy Zabbix Agent to Windows via WinRM from Ubuntu host
"""

import winrm
import sys
import time

# Configuration
WIN_HOST = "192.168.1.129"
WIN_USER = "rog"
WIN_PASS = "123"
ZABBIX_SERVER = "192.168.1.203"
AGENT_VERSION = "7.4.0"
DOWNLOAD_URL = f"https://cdn.zabbix.com/zabbix/binaries/stable/7.4/{AGENT_VERSION}/zabbix_agent2-{AGENT_VERSION}-windows-amd64-openssl.msi"

print("=" * 60)
print("  🪟 Windows Zabbix Agent Deployment via WinRM")
print("=" * 60)
print(f"Target: {WIN_HOST}")
print(f"Zabbix Server: {ZABBIX_SERVER}")
print("")

# Connect to Windows
print("[1/7] Connecting to Windows PC...")
try:
    session = winrm.Session(WIN_HOST, auth=(WIN_USER, WIN_PASS), transport='ntlm')
    # Test connection
    result = session.run_cmd('echo', ['Connected'])
    if result.status_code == 0:
        print("  ✓ WinRM connection established")
    else:
        print("  ✗ Connection test failed")
        sys.exit(1)
except Exception as e:
    print(f"  ✗ Cannot connect: {e}")
    sys.exit(1)

# Create temp directory
print("\n[2/7] Creating temp directory...")
result = session.run_ps("New-Item -Path C:\\Temp -ItemType Directory -Force | Out-Null")
if result.status_code == 0:
    print("  ✓ Temp directory ready")
else:
    print("  ✗ Failed to create directory")

# Download Zabbix Agent
print(f"\n[3/7] Downloading Zabbix Agent {AGENT_VERSION}...")
ps_script = f"""
$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri '{DOWNLOAD_URL}' -OutFile 'C:\\Temp\\zabbix_agent2.msi' -UseBasicParsing
if (Test-Path 'C:\\Temp\\zabbix_agent2.msi') {{
    Write-Output 'Downloaded'
}} else {{
    Write-Error 'Download failed'
}}
"""
result = session.run_ps(ps_script)
if 'Downloaded' in result.std_out.decode():
    print("  ✓ Agent downloaded")
else:
    print(f"  ✗ Download failed: {result.std_err.decode()}")
    sys.exit(1)

# Stop existing service
print("\n[4/7] Checking for existing agent...")
result = session.run_ps("Get-Service 'Zabbix Agent 2' -ErrorAction SilentlyContinue")
if result.status_code == 0 and result.std_out:
    print("  Found existing agent, stopping...")
    session.run_ps("Stop-Service 'Zabbix Agent 2' -Force")
    print("  ✓ Service stopped")
else:
    print("  ✓ No existing agent")

# Install agent
print("\n[5/7] Installing Zabbix Agent 2...")
install_cmd = f"""
Start-Process msiexec.exe -ArgumentList '/i', 'C:\\Temp\\zabbix_agent2.msi', '/qn', '/norestart', 'SERVER={ZABBIX_SERVER}', 'SERVERACTIVE={ZABBIX_SERVER}', 'HOSTNAME=WIN-PC-129', 'HOSTMETADATA=windows auto', 'ENABLEPATH=1' -Wait -NoNewWindow
"""
result = session.run_ps(install_cmd)
time.sleep(5)  # Wait for installation
print("  ✓ Installation complete")

# Configure firewall
print("\n[6/7] Configuring firewall...")
firewall_script = """
$ruleName = 'Zabbix Agent 2'
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existingRule) {
    Remove-NetFirewallRule -DisplayName $ruleName
}
New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 10050 -Description 'Allow Zabbix Server' | Out-Null
Write-Output 'Firewall configured'
"""
result = session.run_ps(firewall_script)
if result.status_code == 0:
    print("  ✓ Firewall rule created")

# Start service
print("\n[7/7] Starting Zabbix Agent service...")
start_script = """
Start-Service 'Zabbix Agent 2'
Start-Sleep -Seconds 2
$service = Get-Service 'Zabbix Agent 2'
if ($service.Status -eq 'Running') {
    Write-Output 'Service is running'
} else {
    Write-Error 'Service failed to start'
}
"""
result = session.run_ps(start_script)
if 'running' in result.std_out.decode().lower():
    print("  ✓ Service started successfully")
else:
    print("  ✗ Service may not be running")

# Test connectivity
print("\n[*] Testing connectivity to Zabbix Server...")
test_script = f"Test-NetConnection -ComputerName {ZABBIX_SERVER} -Port 10051"
result = session.run_ps(test_script)
if 'TcpTestSucceeded' in result.std_out.decode() and 'True' in result.std_out.decode():
    print("  ✓ Connectivity to Zabbix Server OK")
else:
    print("  ⚠ Could not verify connectivity")

# Cleanup
print("\n[*] Cleaning up...")
session.run_ps("Remove-Item C:\\Temp\\zabbix_agent2.msi -Force -ErrorAction SilentlyContinue")

print("\n" + "=" * 60)
print("  ✅ Deployment Complete!")
print("=" * 60)
print("\nNext steps:")
print("  1. Wait 1-2 minutes for auto-registration")
print("  2. Check Zabbix UI: http://192.168.1.203:8080")
print("  3. Configuration → Hosts → Look for WIN-PC-129")
print("")

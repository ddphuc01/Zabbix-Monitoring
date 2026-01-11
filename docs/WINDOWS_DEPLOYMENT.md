# Windows Agent Deployment Guide

Complete guide for deploying Zabbix Agent 2 on Windows systems and adding them to your Zabbix monitoring.

## Quick Start

### Method 1: Automated Deployment (Recommended)

**On Windows machine:**

1. Download the PowerShell deployment script:
   ```powershell
   # Download from Zabbix server
   Invoke-WebRequest -Uri "http://192.168.1.203:8000/deploy-agent.ps1" -OutFile "deploy-agent.ps1"
   ```

2. Run as Administrator:
   ```powershell
   # Basic deployment
   .\deploy-agent.ps1
   
   # Custom configuration
   .\deploy-agent.ps1 -ServerIP 192.168.1.203 -HostName "WIN-PC01" -HostMetadata "windows production"
   ```

3. Wait 1-2 minutes for auto-registration

### Method 2: Manual Deployment

#### Step 1: Download Zabbix Agent 2

Download from official Zabbix website:
- URL: https://www.zabbix.com/download_agents
- Version: 7.4.0 LTS
- Platform: Windows
- Architecture: x64
- Format: MSI installer

#### Step 2: Install Agent

Run MSI installer with parameters:
```cmd
msiexec /i zabbix_agent2-7.4.0-windows-amd64-openssl.msi ^
  /qn ^
  SERVER=192.168.1.203 ^
  SERVERACTIVE=192.168.1.203 ^
  HOSTNAME=WIN-PC01 ^
  HOSTMETADATA="windows auto" ^
  ENABLEPATH=1
```

#### Step 3: Configure Firewall

```powershell
New-NetFirewallRule -DisplayName "Zabbix Agent 2" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 10050
```

#### Step 4: Start Service

```powershell
Start-Service -Name "Zabbix Agent 2"
```

---

## Auto-Registration Setup

### Enable on Zabbix Server

1. **Login** to Zabbix web interface
2. **Go to:** Configuration → Actions → Autoregistration actions
3. **Click:** Create action
4. **Configure:**

**Action tab:**
- Name: `Auto-register Windows hosts`
- Conditions:
  - Host metadata contains `windows`

**Operations tab:**
- Add to host groups: `Windows servers` (auto-created)
- Link to templates:
  - `Windows by Zabbix agent`
  - `Windows by Zabbix agent active`
- Set host inventory mode: `Automatic`

---

## Adding Hosts Manually

### Via Python Script

**On Zabbix server:**

```bash
cd /home/phuc/zabbix-monitoring

# Make script executable
chmod +x scripts/add-windows-host.py

# Add Windows host
python3 scripts/add-windows-host.py \
  --hostname "WIN-PC01" \
  --ip "192.168.1.100" \
  --description "Windows 11 Pro - Office PC" \
  --group "Windows servers"
```

### Via Web Interface

1. **Go to:** Configuration → Hosts
2. **Click:** Create host
3. **Configure:**

**Host tab:**
- Host name: `WIN-PC01`
- Visible name: `Windows 11 Pro - Office PC`
- Groups: `Windows servers`

**Templates tab:**
- Link templates:
  - `Windows by Zabbix agent`
  - `Windows by Zabbix agent active`

**Interfaces:**
- Type: `Agent`
- IP address: `192.168.1.100`
- Port: `10050`

4. **Click:** Add

---

## Configuration Files

### Agent Configuration

Location: `C:\Program Files\Zabbix Agent 2\zabbix_agent2.conf`

**Key parameters:**
```ini
# Zabbix Server IP
Server=192.168.1.203

# Active checks
ServerActive=192.168.1.203

# Hostname (must be unique)
Hostname=WIN-PC01

# Auto-registration metadata
HostMetadata=windows production

# Allow remote commands (0=disabled, 1=enabled)
EnableRemoteCommands=0

# Log file
LogFile=C:\Program Files\Zabbix Agent 2\zabbix_agent2.log

# Log level (0=none, 3=warning, 4=debug)
DebugLevel=3
```

### Service Management

```powershell
# Start service
Start-Service "Zabbix Agent 2"

# Stop service
Stop-Service "Zabbix Agent 2"

# Restart service
Restart-Service "Zabbix Agent 2"

# Check status
Get-Service "Zabbix Agent 2"

# View logs
Get-Content "C:\Program Files\Zabbix Agent 2\zabbix_agent2.log" -Tail 50
```

---

## Monitoring Metrics

### Default Windows Metrics

**System:**
- CPU usage, load
- Memory usage (total, free, cached)
- Disk space, I/O
- Network interfaces
- System uptime

**Services:**
- Windows services status
- Critical service monitoring

**Performance:**
- Processor queue length
- Page faults
- Context switches

**Event Log:**
- System errors
- Application errors
- Security events

### Custom Metrics

Add custom monitoring via User Parameters in config:

```ini
# Custom disk monitoring
UserParameter=custom.disk.free[*],Get-PSDrive $1 | Select -Expand Free

# Custom service check
UserParameter=custom.service.status[*],(Get-Service $1).Status
```

---

## Troubleshooting

### Agent Not Connecting

**Check network connectivity:**
```powershell
Test-NetConnection -ComputerName 192.168.1.203 -Port 10051
```

**Check agent log:**
```powershell
Get-Content "C:\Program Files\Zabbix Agent 2\zabbix_agent2.log" -Tail 50
```

**Common issues:**
- Firewall blocking port 10050
- Wrong Server IP in config
- Hostname mismatch
- Service not running

### Host Not Auto-Registering

1. Check HostMetadata in agent config
2. Verify auto-registration action on server
3. Check agent log for active check errors
4. Ensure ServerActive is set correctly

### Service Won't Start

```powershell
# Check service status
sc query "Zabbix Agent 2"

# View service dependencies
sc qc "Zabbix Agent 2"

# Check for config errors
& "C:\Program Files\Zabbix Agent 2\zabbix_agent2.exe" -t "agent.ping"
```

---

## Security Best Practices

### 1. PSK Encryption

**Generate PSK on server:**
```bash
openssl rand -hex 32 > /home/phuc/zabbix-monitoring/psk/WIN-PC01.psk
```

**Configure agent:**
```ini
TLSConnect=psk
TLSAccept=psk
TLSPSKIdentity=PSK_WIN-PC01
TLSPSKFile=C:\Program Files\Zabbix Agent 2\psk\WIN-PC01.psk
```

### 2. Restrict Access

**Agent config:**
```ini
# Only allow specific Zabbix server
Server=192.168.1.203

# Disable remote commands
EnableRemoteCommands=0

# Limit allowed remote commands
AllowKey=system.run[*]
DenyKey=system.run[rm *]
```

### 3. Firewall Rules

```powershell
# Restrict to Zabbix server only
New-NetFirewallRule -DisplayName "Zabbix Agent 2" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 10050 `
  -RemoteAddress 192.168.1.203
```

---

## Bulk Deployment

### PowerShell Remoting

Deploy to multiple Windows machines:

```powershell
$servers = @("WIN-PC01", "WIN-PC02", "WIN-PC03")
$credential = Get-Credential

foreach ($server in $servers) {
    Invoke-Command -ComputerName $server -Credential $credential -FilePath .\deploy-agent.ps1
}
```

### Group Policy

1. Create GPO for agent installation
2. Use MSI deployment via Group Policy
3. Configure startup script for configuration

---

## Monitoring Templates

### Windows by Zabbix agent

**Includes:**
- System metrics (CPU, memory, disk)
- Network interfaces
- Windows services
- Event log monitoring

### Windows by Zabbix agent active

**Additional features:**
- Active checks for faster response
- Lower server load
- Better for remote/WAN monitoring

### Custom Templates

Create custom templates for:
- Specific applications (IIS, SQL Server, Exchange)
- Custom services monitoring
- Application-specific metrics

---

## Next Steps

1. ✅ Deploy agent on Windows machines
2. ✅ Verify connectivity and data collection
3. Configure alerting (email, SMS, etc.)
4. Set up dashboards for Windows hosts
5. Implement custom monitoring as needed

---

## Useful Commands

```powershell
# Test agent connectivity
& "C:\Program Files\Zabbix Agent 2\zabbix_agent2.exe" -t "agent.ping"

# Get all available metrics
& "C:\Program Files\Zabbix Agent 2\zabbix_agent2.exe" -p

# Test specific metric
& "C:\Program Files\Zabbix Agent 2\zabbix_agent2.exe" -t "system.cpu.load"

# Reload configuration
Restart-Service "Zabbix Agent 2"
```

---

## Support

For issues or questions:
- Check logs: `C:\Program Files\Zabbix Agent 2\zabbix_agent2.log`
- Zabbix documentation: https://www.zabbix.com/documentation/current/
- Server health check: `./scripts/health-check.sh`

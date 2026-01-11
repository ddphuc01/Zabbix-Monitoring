<#
.SYNOPSIS
    Automated Zabbix Agent 2 deployment script for Windows

.DESCRIPTION
    Downloads, installs, and configures Zabbix Agent 2 on Windows systems
    Supports auto-registration with Zabbix Server

.PARAMETER ServerIP
    Zabbix Server IP address (default: 192.168.1.203)

.PARAMETER ServerPort
    Zabbix Server port (default: 10051)

.PARAMETER HostName
    Hostname for this agent (default: computer name)

.PARAMETER HostMetadata
    Metadata for auto-registration (default: "windows auto")

.EXAMPLE
    .\deploy-agent.ps1 -ServerIP 192.168.1.203 -HostName "WIN-PC01"
#>

param(
    [string]$ServerIP = "192.168.1.203",
    [int]$ServerPort = 10051,
    [string]$HostName = $env:COMPUTERNAME,
    [string]$HostMetadata = "windows auto"
)

# Configuration
$AgentVersion = "7.4.0"
$DownloadURL = "https://cdn.zabbix.com/zabbix/binaries/stable/7.4/$AgentVersion/zabbix_agent2-$AgentVersion-windows-amd64-openssl.msi"
$InstallPath = "C:\Program Files\Zabbix Agent 2"
$TempPath = "$env:TEMP\zabbix_agent2.msi"
$ConfigPath = "$InstallPath\zabbix_agent2.conf"

# Function to write colored output
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-ColorOutput "ERROR: This script must be run as Administrator!" "Red"
    exit 1
}

Write-ColorOutput "`n========================================" "Cyan"
Write-ColorOutput "  Zabbix Agent 2 Deployment Script" "Cyan"
Write-ColorOutput "========================================`n" "Cyan"

# Step 1: Download Zabbix Agent 2
Write-ColorOutput "[1/6] Downloading Zabbix Agent 2 v$AgentVersion..." "Yellow"
try {
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $DownloadURL -OutFile $TempPath -UseBasicParsing
    Write-ColorOutput "  ✓ Downloaded successfully" "Green"
} catch {
    Write-ColorOutput "  ✗ Download failed: $_" "Red"
    exit 1
}

# Step 2: Stop existing service if running
Write-ColorOutput "`n[2/6] Checking for existing Zabbix Agent..." "Yellow"
$service = Get-Service -Name "Zabbix Agent 2" -ErrorAction SilentlyContinue
if ($service) {
    Write-ColorOutput "  Found existing agent, stopping service..." "Yellow"
    Stop-Service -Name "Zabbix Agent 2" -Force
    Write-ColorOutput "  ✓ Service stopped" "Green"
} else {
    Write-ColorOutput "  ✓ No existing agent found" "Green"
}

# Step 3: Install Zabbix Agent 2
Write-ColorOutput "`n[3/6] Installing Zabbix Agent 2..." "Yellow"
try {
    $arguments = @(
        "/i"
        "`"$TempPath`""
        "/qn"
        "/norestart"
        "SERVER=$ServerIP"
        "SERVERACTIVE=$ServerIP"
        "HOSTNAME=$HostName"
        "HOSTMETADATA=`"$HostMetadata`""
        "ENABLEPATH=1"
    )
    
    Start-Process "msiexec.exe" -ArgumentList $arguments -Wait -NoNewWindow
    Write-ColorOutput "  ✓ Agent installed successfully" "Green"
} catch {
    Write-ColorOutput "  ✗ Installation failed: $_" "Red"
    exit 1
}

# Step 4: Configure agent
Write-ColorOutput "`n[4/6] Configuring Zabbix Agent 2..." "Yellow"
if (Test-Path $ConfigPath) {
    # Backup original config
    Copy-Item $ConfigPath "$ConfigPath.backup" -Force
    
    # Read and modify config
    $config = Get-Content $ConfigPath
    $newConfig = @()
    
    foreach ($line in $config) {
        # Update Server
        if ($line -match '^Server=') {
            $newConfig += "Server=$ServerIP"
        }
        # Update ServerActive
        elseif ($line -match '^ServerActive=') {
            $newConfig += "ServerActive=$ServerIP"
        }
        # Update Hostname
        elseif ($line -match '^Hostname=') {
            $newConfig += "Hostname=$HostName"
        }
        # Add HostMetadata if not exists
        elseif ($line -match '^# HostMetadata=') {
            $newConfig += "HostMetadata=$HostMetadata"
        }
        # Enable remote commands
        elseif ($line -match '^# EnableRemoteCommands=') {
            $newConfig += "EnableRemoteCommands=0"
        }
        else {
            $newConfig += $line
        }
    }
    
    # Add missing HostMetadata if needed
    if ($newConfig -notmatch 'HostMetadata=') {
        $newConfig += "`nHostMetadata=$HostMetadata"
    }
    
    # Save config
    $newConfig | Set-Content $ConfigPath -Encoding UTF8
    Write-ColorOutput "  ✓ Configuration updated" "Green"
} else {
    Write-ColorOutput "  ✗ Config file not found at $ConfigPath" "Red"
}

# Step 5: Configure Windows Firewall
Write-ColorOutput "`n[5/6] Configuring Windows Firewall..." "Yellow"
try {
    $ruleName = "Zabbix Agent 2"
    $existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    
    if ($existingRule) {
        Remove-NetFirewallRule -DisplayName $ruleName
    }
    
    New-NetFirewallRule -DisplayName $ruleName `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort 10050 `
        -Description "Allow Zabbix Server to connect to agent" | Out-Null
    
    Write-ColorOutput "  ✓ Firewall rule created" "Green"
} catch {
    Write-ColorOutput "  ✗ Firewall configuration failed: $_" "Red"
}

# Step 6: Start service
Write-ColorOutput "`n[6/6] Starting Zabbix Agent 2 service..." "Yellow"
try {
    Start-Service -Name "Zabbix Agent 2"
    
    # Wait a moment and check status
    Start-Sleep -Seconds 2
    $service = Get-Service -Name "Zabbix Agent 2"
    
    if ($service.Status -eq "Running") {
        Write-ColorOutput "  ✓ Service started successfully" "Green"
    } else {
        Write-ColorOutput "  ✗ Service failed to start" "Red"
    }
} catch {
    Write-ColorOutput "  ✗ Failed to start service: $_" "Red"
}

# Cleanup
Write-ColorOutput "`n[*] Cleaning up..." "Yellow"
Remove-Item $TempPath -Force -ErrorAction SilentlyContinue
Write-ColorOutput "  ✓ Temporary files removed" "Green"

# Summary
Write-ColorOutput "`n========================================" "Cyan"
Write-ColorOutput "  Installation Complete!" "Cyan"
Write-ColorOutput "========================================`n" "Cyan"

Write-ColorOutput "Configuration:" "White"
Write-ColorOutput "  Server IP:    $ServerIP" "White"
Write-ColorOutput "  Hostname:     $HostName" "White"
Write-ColorOutput "  Metadata:     $HostMetadata" "White"
Write-ColorOutput "  Config File:  $ConfigPath" "White"

Write-ColorOutput "`nNext Steps:" "Yellow"
Write-ColorOutput "  1. Check agent log: C:\Program Files\Zabbix Agent 2\zabbix_agent2.log" "White"
Write-ColorOutput "  2. Verify connectivity: Test-NetConnection -ComputerName $ServerIP -Port $ServerPort" "White"
Write-ColorOutput "  3. Wait 1-2 minutes for auto-registration on Zabbix Server" "White"
Write-ColorOutput "  4. Check Zabbix web interface: Configuration → Hosts`n" "White"

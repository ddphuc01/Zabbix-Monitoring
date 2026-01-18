#!/bin/bash

# CPU Stress Test Script for Windows Hosts
# Usage: ./stress_test_cpu.sh <hostname> <cpu_percentage>

if [ $# -lt 2 ]; then
    echo "Usage: $0 <hostname> <cpu_percentage>"
    echo "Example: $0 WIN-PC-129 90"
    exit 1
fi

HOST=$1
CPU_PERCENT=${2:-90}
DURATION=${3:-180}  # Default 3 minutes

echo "=========================================="
echo "CPU Stress Test for Windows Host"
echo "=========================================="
echo "Target Host: $HOST"
echo "CPU Target: ${CPU_PERCENT}%"
echo "Duration: ${DURATION} seconds"
echo "=========================================="
echo ""

# PowerShell script to stress CPU
STRESS_SCRIPT='
$duration = '$DURATION'
$targetCpu = '$CPU_PERCENT'
$cores = (Get-WmiObject Win32_Processor).NumberOfLogicalProcessors
$endTime = (Get-Date).AddSeconds($duration)

Write-Host "Starting CPU stress test..."
Write-Host "Cores: $cores"
Write-Host "Target CPU: $targetCpu%"
Write-Host "Duration: $duration seconds"
Write-Host ""

# Create jobs for each core
$jobs = @()
for ($i = 0; $i -lt $cores; $i++) {
    $jobs += Start-Job -ScriptBlock {
        param($endTime)
        $result = 1
        while ((Get-Date) -lt $endTime) {
            $result = 1..1000 | ForEach-Object { $_ * $_ }
        }
    } -ArgumentList $endTime
}

# Monitor progress
$startTime = Get-Date
while ((Get-Date) -lt $endTime) {
    $elapsed = [math]::Round(((Get-Date) - $startTime).TotalSeconds)
    $remaining = [math]::Round(($endTime - (Get-Date)).TotalSeconds)
    $cpu = Get-Counter "\Processor(_Total)\% Processor Time" | Select-Object -ExpandProperty CounterSamples | Select-Object -ExpandProperty CookedValue
    $cpu = [math]::Round($cpu, 2)
    
    Write-Host ("[{0:D3}s] CPU: {1:F2}% | Remaining: {2}s" -f $elapsed, $cpu, $remaining)
    Start-Sleep -Seconds 5
}

# Cleanup
Write-Host ""
Write-Host "Stopping stress test..."
$jobs | Stop-Job
$jobs | Remove-Job
Write-Host "Stress test completed!"
'

# Execute via Ansible
echo "Executing stress test on $HOST..."
echo ""

ansible "$HOST" -i /home/phuc/zabbix-monitoring/ansible/inventory/hosts.yml \
    -m win_shell \
    -a "$STRESS_SCRIPT" \
    --become

echo ""
echo "=========================================="
echo "Stress test execution finished!"
echo "Check Telegram for CPU alert (should arrive in ~1-2 minutes)"
echo "=========================================="

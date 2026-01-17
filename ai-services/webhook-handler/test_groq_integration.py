#!/usr/bin/env python3
"""
Comprehensive Test Suite for Zabbix AI Alert Analysis
Tests all 4 alert types with realistic Ansible data
"""

import os
import json
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from webhook import GroqAnalyzer, AnsibleExecutor

# Sample Ansible outputs for different scenarios
SAMPLE_ANSIBLE_OUTPUTS = {
    "cpu_high": {
        "os_family": "Debian",
        "top": """top - 14:30:00 up 10 days,  2:00,  1 user,  load average: 4.50, 3.00, 2.50
Tasks: 150 total,   3 running, 147 sleeping,   0 stopped,   0 zombie
%Cpu(s): 92.0 us,  5.0 sy,  0.0 ni,  3.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :   8000.0 total,   1200.0 free,   6000.0 used,   800.0 buff/cache
MiB Swap:   2048.0 total,   2048.0 free,      0.0 used.   1500.0 avail Mem""",
        "ps": """USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
www-data  1234 45.0  2.3 500000 200000 ?      R    14:20   5:23 nginx: worker process
www-data  1235 20.0  2.1 490000 180000 ?      R    14:20   2:45 nginx: worker process
mysql     2345 15.0  5.5 800000 450000 ?      S    10:00  15:30 /usr/sbin/mysqld""",
        "df": "Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        50G   30G   18G  63% /",
        "free": "              total        used        free      shared  buff/cache   available\nMem:           8000        6000        1200         100         800        1500\nSwap:          2048           0        2048",
        "netstat": "Active Internet connections (servers and established)\nProto Recv-Q Send-Q Local Address           Foreign Address         State\ntcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN\ntcp        0      0 192.168.1.10:80         192.168.1.50:45000      ESTABLISHED (500 connections total)"
    },
    "memory_high": {
        "os_family": "Debian", 
        "top": """top - 14:35:00 up 5 days,  1:00,  2 users,  load average: 2.00, 1.80, 1.50
%Cpu(s): 15.0 us,  3.0 sy,  0.0 ni, 82.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :  16000.0 total,    800.0 free,  14500.0 used,   700.0 buff/cache
MiB Swap:   4096.0 total,   2000.0 free,   2096.0 used.   600.0 avail Mem""",
        "ps": """USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
postgres  3456  5.0 60.0 15000000 9600000 ?  S    12:00  25:30 /usr/lib/postgresql/bin/postgres
redis     4567  2.0 25.0  5000000 4000000 ?  S    10:00  10:15 redis-server *:6379
www-data  5678  1.5  3.5   800000  560000 ?  S    14:00   0:45 php-fpm: pool www""",
        "df": "Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1       100G   45G   50G  48% /",
        "free": "              total        used        free      shared  buff/cache   available\nMem:          16000       14500         800         200         700         600\nSwap:          4096        2096        2000",
        "netstat": "tcp        0      0 0.0.0.0:5432            0.0.0.0:*               LISTEN (PostgreSQL)"
    },
    "disk_high": {
        "os_family": "Debian",
        "top": """top - 14:40:00 up 30 days,  5:00,  1 user,  load average: 0.50, 0.40, 0.35
%Cpu(s):  5.0 us,  2.0 sy,  0.0 ni, 93.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :   4000.0 total,   2500.0 free,   1000.0 used,   500.0 buff/cache""",
        "ps": """USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root       123  1.0  0.5 100000  20000 ?      S    Jan01   5:30 /usr/sbin/rsyslogd
www-data   456  0.5  1.0 200000  40000 ?      S    14:00   0:15 nginx: worker""",
        "df": """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        50G   48G   1.5G  97% /
/dev/sda2       100G   15G   80G  16% /home
tmpfs           2.0G  100M  1.9G   5% /tmp""",
        "free": "              total        used        free      shared  buff/cache   available\nMem:           4000        1000        2500          50         500        2800\nSwap:          2048           0        2048",
        "netstat": "tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN"
    },
    "network_high": {
        "os_family": "Debian",
        "top": """top - 14:45:00 up 15 days,  3:00,  1 user,  load average: 3.00, 2.80, 2.50
%Cpu(s): 35.0 us, 10.0 sy,  0.0 ni, 50.0 id,  5.0 wa,  0.0 hi,  0.0 si,  0.0 st""",
        "ps": """USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
www-data  7890 25.0  3.0 600000 240000 ?      R    14:30   2:30 nginx: worker
www-data  7891 18.0  2.8 580000 224000 ?      R    14:30   1:45 nginx: worker""",
        "df": "Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        50G   20G   28G  42% /",
        "free": "              total        used        free      shared  buff/cache   available\nMem:           8000        3500        3000         100        1500        4000\nSwap:          2048           0        2048",
        "netstat": """Active Internet connections (servers and established)
Proto Recv-Q Send-Q Local Address           Foreign Address         State      
tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN
tcp      450    200 192.168.1.10:80         192.168.1.20:50001      ESTABLISHED
tcp      320    150 192.168.1.10:80         192.168.1.21:50002      ESTABLISHED
tcp      280    100 192.168.1.10:80         192.168.1.22:50003      TIME_WAIT
tcp        0      0 192.168.1.10:80         192.168.1.23:50004      TIME_WAIT
... (1500 total connections, 350 ESTABLISHED, 800 TIME_WAIT, 50 SYN_RECV)"""
    }
}

# Test cases for all 4 alert types
TEST_CASES = [
    {
        "name": "CPU Alert - High nginx usage",
        "alert_data": {
            "trigger": "High CPU utilization on web-server-prod-01",
            "host": "web-server-prod-01",
            "value": "92",
            "severity": "High",
            "time": "2026-01-16 14:30:00",
            "threshold": "80"
        },
        "ansible_data": SAMPLE_ANSIBLE_OUTPUTS["cpu_high"]
    },
    {
        "name": "Memory Alert - PostgreSQL high memory",
        "alert_data": {
            "trigger": "High memory usage on db-server-prod-01",
            "host": "db-server-prod-01",
            "value": "95",
            "severity": "Critical",
            "time": "2026-01-16 14:35:00",
            "threshold": "85"
        },
        "ansible_data": SAMPLE_ANSIBLE_OUTPUTS["memory_high"]
    },
    {
        "name": "Disk Alert - Root partition almost full",
        "alert_data": {
            "trigger": "Low disk space on /dev/sda1 on app-server-prod-01",
            "host": "app-server-prod-01",
            "value": "97",
            "severity": "Critical",
            "time": "2026-01-16 14:40:00",
            "threshold": "90"
        },
        "ansible_data": SAMPLE_ANSIBLE_OUTPUTS["disk_high"]
    },
    {
        "name": "Network Alert - Too many connections",
        "alert_data": {
            "trigger": "High network connections on api-server-prod-01",
            "host": "api-server-prod-01",
            "value": "1500",
            "severity": "High",
            "time": "2026-01-16 14:45:00",
            "threshold": "1000"
        },
        "ansible_data": SAMPLE_ANSIBLE_OUTPUTS["network_high"]
    }
]

def run_tests():
    """Run all test cases"""
    print("=" * 80)
    print("ZABBIX AI ALERT ANALYSIS - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    
    if not os.getenv('GROQ_API_KEY'):
        print("\n⚠️  WARNING: GROQ_API_KEY not set. API calls will fail.")
        print("Set GROQ_API_KEY environment variable to test with real API.\n")
        return
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}/{len(TEST_CASES)}: {test_case['name']}")
        print(f"{'=' * 80}")
        
        alert_data = test_case['alert_data']
        ansible_data = test_case['ansible_data']
        
        # Display test inputs
        print(f"\n📋 Alert Info:")
        print(f"  - Trigger: {alert_data['trigger']}")
        print(f"  - Host: {alert_data['host']}")
        print(f"  - Value: {alert_data['value']}")
        print(f"  - Severity: {alert_data['severity']}")
        print(f"  - Threshold: {alert_data.get('threshold', 'N/A')}")
        
        # Determine alert type
        alert_type = GroqAnalyzer.determine_alert_type(alert_data['trigger'])
        print(f"\n🔍 Detected Alert Type: {alert_type}")
        
        # Extract service info
        service_info = GroqAnalyzer.extract_service_info(alert_data['host'], alert_data)
        print(f"\n🏷️  Service Context:")
        print(f"  - Environment: {service_info['environment']}")
        print(f"  - App Type: {service_info['app_type']}")
        print(f"  - Expected Load: {service_info['expected_load']}")
        
        # Call Groq API
        print(f"\n🤖 Calling Groq API...")
        try:
            result = GroqAnalyzer.analyze(alert_data, ansible_data)
            
            if 'error' in result:
                print(f"\n❌ ERROR: {result['error']}")
            else:
                print(f"\n✅ Analysis Generated:")
                print(f"\n{'-' * 80}")
                print(result['analysis'])
                print(f"{'-' * 80}")
                print(f"\n📊 Metadata:")
                print(f"  - Model: {result.get('model', 'N/A')}")
                print(f"  - Timestamp: {result.get('timestamp', 'N/A')}")
        
        except Exception as e:
            print(f"\n❌ Exception: {e}")
        
        # Pause between tests
        if i < len(TEST_CASES):
            print(f"\n{'─' * 80}")
            input("Press Enter to continue to next test...")

def test_ansible_parser():
    """Test the Ansible output parser"""
    print("\n" + "=" * 80)
    print("TESTING ANSIBLE OUTPUT PARSER")
    print("=" * 80)
    
    # Mock Ansible stdout with JSON structure
    mock_stdout = """
PLAY [Gather System Metrics] ***********************************************

TASK [Gathering Facts] *****************************************************
ok: [test-host]

TASK [Return collected metrics] ********************************************
ok: [test-host] => {
    "msg": {
        "os_family": "Debian",
        "top": "top - 14:30:00...",
        "ps": "USER PID...",
        "df": "Filesystem...",
        "free": "total used...",
        "netstat": "Active connections..."
    }
}

PLAY RECAP *****************************************************************
test-host                  : ok=2    changed=0    unreachable=0    failed=0
"""
    
    result = AnsibleExecutor.parse_ansible_output(mock_stdout)
    
    if isinstance(result, dict):
        print("\n✅ Successfully parsed JSON structure")
        print(f"Keys found: {list(result.keys())}")
    else:
        print("\n⚠️  Fallback to raw output")
        print(f"Output length: {len(result)} chars")

if __name__ == '__main__':
    print("\n🚀 Starting Comprehensive Test Suite\n")
    
    # Test Ansible parser first
    test_ansible_parser()
    
    # Run main tests
    print("\n")
    run_tests()
    
    print("\n" + "=" * 80)
    print("✅ TEST SUITE COMPLETED")
    print("=" * 80)

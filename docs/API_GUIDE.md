# Zabbix API Guide

## Overview

The Zabbix API allows you to programmatically interact with Zabbix for automation, integration, and custom tooling. It uses JSON-RPC 2.0 protocol over HTTP.

**API Endpoint:** `http://your-zabbix-server:8080/api_jsonrpc.php`

---

## Authentication

### Get API Token

```bash
curl -X POST http://localhost:8080/api_jsonrpc.php \
  -H "Content-Type: application/json-rpc" \
  -d  '{
    "jsonrpc": "2.0",
    "method": "user.login",
    "params": {
      "username": "Admin",
      "password": "zabbix"
    },
    "id": 1
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": "0424bd59b807674191e7d77572075f33",
  "id": 1
}
```

Save the token for subsequent requests.

### Using Python

```python
import requests
import json

ZABBIX_URL = " http://localhost:8080/api_jsonrpc.php"
USERNAME = "Admin"
PASSWORD = "zabbix"

# Login
payload = {
    "jsonrpc": "2.0",
    "method": "user.login",
    "params": {
        "username": USERNAME,
        "password": PASSWORD
    },
    "id": 1
}

response = requests.post(ZABBIX_URL, json=payload)
auth_token = response.json()['result']
print(f"Auth Token: {auth_token}")
```

---

## Common Operations

### 1. Get Hosts

```bash
curl -X POST http://localhost:8080/api_jsonrpc.php \
  -H "Content-Type: application/json-rpc" \
  -d '{
    "jsonrpc": "2.0",
    "method": "host.get",
    "params": {
      "output": ["hostid", "host", "name", "status"],
      "selectInterfaces": ["interfaceid", "ip"]
    },
    "auth": "YOUR_AUTH_TOKEN",
    "id": 2
  }'
```

**Python:**
```python
def get_hosts(auth_token):
    payload = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": ["hostid", "host", "name", "status"],
            "selectInterfaces": ["interfaceid", "ip"]
        },
        "auth": auth_token,
        "id": 2
    }
    response = requests.post(ZABBIX_URL, json=payload)
    return response.json()['result']

hosts = get_hosts(auth_token)
for host in hosts:
    print(f"ID: {host['hostid']}, Name: {host['name']}, IP: {host['interfaces'][0]['ip']}")
```

### 2. Create Host

```python
def create_host(auth_token, hostname, ip_address, group_id):
    payload = {
        "jsonrpc": "2.0",
        "method": "host.create",
        "params": {
            "host": hostname,
            "interfaces": [
                {
                    "type": 1,  # Agent interface
                    "main": 1,
                    "useip": 1,
                    "ip": ip_address,
                    "dns": "",
                    "port": "10050"
                }
            ],
            "groups": [
                {
                    "groupid": group_id
                }
            ],
            "templates": [
                {
                    "templateid": "10001"  # Linux by Zabbix agent
                }
            ]
        },
        "auth": auth_token,
        "id": 3
    }
    response = requests.post(ZABBIX_URL, json=payload)
    return response.json()['result']

# Create host
result = create_host(auth_token, "web-server-01", "192.168.1.100", "2")
print(f"Created host ID: {result['hostids'][0]}")
```

### 3. Get Items

```python
def get_items(auth_token, hostid):
    payload = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": ["itemid", "name", "key_", "lastvalue"],
            "hostids": hostid,
            "sortfield": "name"
        },
        "auth": auth_token,
        "id": 4
    }
    response = requests.post(ZABBIX_URL, json=payload)
    return response.json()['result']

items = get_items(auth_token, "10084")
for item in items:
    print(f"{item['name']}: {item.get('lastvalue', 'N/A')}")
```

### 4. Get Latest Data

```python
def get_history(auth_token, itemid, limit=10):
    payload = {
        "jsonrpc": "2.0",
        "method": "history.get",
        "params": {
            "output": "extend",
            "itemids": itemid,
            "sortfield": "clock",
            "sortorder": "DESC",
            "limit": limit
        },
        "auth": auth_token,
        "id": 5
    }
    response = requests.post(ZABBIX_URL, json=payload)
    return response.json()['result']

# Get CPU usage history
history = get_history(auth_token, "23296")
for record in history:
    from datetime import datetime
    timestamp = datetime.fromtimestamp(int(record['clock']))
    print(f"{timestamp}: {record['value']}")
```

### 5. Create Trigger

```python
def create_trigger(auth_token, description, expression, priority=3):
    payload = {
        "jsonrpc": "2.0",
        "method": "trigger.create",
        "params": {
            "description": description,
            "expression": expression,
            "priority": priority,  # 0-5 (Not classified to Disaster)
            "manual_close": 1
        },
        "auth": auth_token,
        "id": 6
    }
    response = requests.post(ZABBIX_URL, json=payload)
    return response.json()['result']

# Create high CPU trigger
trigger = create_trigger(
    auth_token,
    "High CPU usage on {HOST.NAME}",
    "last(/Linux by Zabbix agent/system.cpu.util)>90",
    priority=4  # High
)
print(f"Created trigger ID: {trigger['triggerids'][0]}")
```

### 6. Acknowledge Problem

```python
def acknowledge_problem(auth_token, eventid, message):
    payload = {
        "jsonrpc": "2.0",
        "method": "event.acknowledge",
        "params": {
            "eventids": eventid,
            "message": message,
            "action": 1  # Close problem
        },
        "auth": auth_token,
        "id": 7
    }
    response = requests.post(ZABBIX_URL, json=payload)
    return response.json()['result']

# Acknowledge event
result = acknowledge_problem(auth_token, "12345", "Fixed by restarting service")
```

### 7. Get Active Problems

```python
def get_problems(auth_token, severity=None):
    params = {
        "output": "extend",
        "selectAcknowledges": "extend",
        "selectTags": "extend",
        "recent": "false",
        "sortfield": ["eventid"],
        "sortorder": "DESC"
    }
    
    if severity:
        params["severities"] = severity  # 0-5
    
    payload = {
        "jsonrpc": "2.0",
        "method": "problem.get",
        "params": params,
        "auth": auth_token,
        "id": 8
    }
    response = requests.post(ZABBIX_URL, json=payload)
    return response.json()['result']

# Get high severity problems
problems = get_problems(auth_token, severity=[4, 5])
print(f"Active problems: {len(problems)}")
for problem in problems:
    print(f"- {problem['name']} (Severity: {problem['severity']})")
```

### 8. Create/Update User

```python
def create_user(auth_token, username, password, role_id):
    payload = {
        "jsonrpc": "2.0",
        "method": "user.create",
        "params": {
            "username": username,
            "passwd": password,
            "roleid": role_id,  # 1=Super admin, 2=Admin, 3=User
            "usrgrps": [
                {"usrgrpid": "7"}  # Zabbix administrators
            ]
        },
        "auth": auth_token,
        "id": 9
    }
    response = requests.post(ZABBIX_URL, json=payload)
    return response.json()['result']
```

---

## Automation Examples

### Bulk Host Creation

```python
import csv

def bulk_create_hosts(auth_token, csv_file):
    """Create hosts from CSV file"""
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                result = create_host(
                    auth_token,
                    row['hostname'],
                    row['ip_address'],
                    row['group_id']
                )
                print(f"✓ Created: {row['hostname']}")
            except Exception as e:
                print(f"✗ Failed: {row['hostname']} - {e}")

# CSV format: hostname,ip_address,group_id
# web-01,192.168.1.10,2
# web-02,192.168.1.11,2
bulk_create_hosts(auth_token, "hosts.csv")
```

### Export Configuration

```python
def export_configuration(auth_token, config_type, ids):
    """Export hosts, templates, or groups"""
    payload = {
        "jsonrpc": "2.0",
        "method": "configuration.export",
        "params": {
            "format": "yaml",
            "options": {
                config_type: ids
            }
        },
        "auth": auth_token,
        "id": 10
    }
    response = requests.post(ZABBIX_URL, json=payload)
    return response.json()['result']

# Export hosts
config = export_configuration(auth_token, "hosts", ["10084", "10085"])
with open("hosts_export.yaml", "w") as f:
    f.write(config)
```

### Monitoring Report

```python
def generate_monitoring_report(auth_token):
    """Generate daily monitoring report"""
    hosts = get_hosts(auth_token)
    problems = get_problems(auth_token)
    
    report = f"""
    Zabbix Monitoring Report - {datetime.now().strftime('%Y-%m-%d')}
    
    Total Hosts: {len(hosts)}
    Active Problems: {len(problems)}
    
    Critical Problems:
    """
    
    critical = [p for p in problems if int(p['severity']) >= 4]
    for prob in critical:
        report += f"  - {prob['name']}\n"
    
    return report

print(generate_monitoring_report(auth_token))
```

---

## Complete Example Script

```python
#!/usr/bin/env python3
"""
Zabbix API Example Script
Demonstrates authentication and common operations
"""

import requests
import json
from datetime import datetime

class ZabbixAPI:
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password
        self.auth_token = None
        self.request_id = 0
        
    def login(self):
        """Authenticate and get token"""
        response = self._call("user.login", {
            "username": self.username,
            "password": self.password
        })
        self.auth_token = response
        return self.auth_token
    
    def _call(self, method, params):
        """Make API call"""
        self.request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.request_id
        }
        
        if self.auth_token:
            payload["auth"] = self.auth_token
        
        response = requests.post(self.url, json=payload)
        result = response.json()
        
        if "error" in result:
            raise Exception(f"API Error: {result['error']}")
        
        return result.get("result")
    
    def get_hosts(self):
        """Get all hosts"""
        return self._call("host.get", {
            "output": ["hostid", "host", "name", "status"],
            "selectInterfaces": ["ip"]
        })
    
    def get_problems(self):
        """Get active problems"""
        return self._call("problem.get", {
            "output": "extend",
            "recent": "false"
        })

# Usage
if __name__ == "__main__":
    zapi = ZabbixAPI(
        "http://localhost:8080/api_jsonrpc.php",
        "Admin",
        "zabbix"
    )
    
    # Login
    token = zapi.login()
    print(f"Logged in, token: {token[:20]}...")
    
    # Get hosts
    hosts = zapi.get_hosts()
    print(f"\nMonitored Hosts: {len(hosts)}")
    for host in hosts:
        status = "Enabled" if host['status'] == '0' else "Disabled"
        print(f"  - {host['name']} ({status})")
    
    # Get problems
    problems = zapi.get_problems()
    print(f"\nActive Problems: {len(problems)}")
    for problem in problems[:5]:  # Show first 5
        print(f"  - {problem['name']}")
```

---

## Error Handling

```python
def safe_api_call(auth_token, method, params):
    """Wrapper with error handling"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "auth": auth_token,
            "id": 1
        }
        
        response = requests.post(ZABBIX_URL, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if "error" in result:
            print(f"API Error: {result['error']['message']}")
            print(f"Error Data: {result['error'].get('data', 'N/A')}")
            return None
        
        return result.get("result")
        
    except requests.exceptions.Timeout:
        print("Request timeout")
    except requests.exceptions.ConnectionError:
        print("Connection error")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    return None
```

---

## Useful Methods Reference

| Method | Purpose |
|--------|---------|
| `user.login` | Authenticate |
| `host.get` | Get hosts |
| `host.create` | Create host |
| `host.update` | Update host |
| `host.delete` | Delete host |
| `item.get` | Get items |
| `trigger.get` | Get triggers |
| `problem.get` | Get active problems |
| `event.acknowledge` | Acknowledge event |
| `template.get` | Get templates |
| `hostgroup.get` | Get host groups |
| `history.get` | Get historical data |
| `configuration.export` | Export configuration |
| `configuration.import` | Import configuration |

---

## References

- [Official API Documentation](https://www.zabbix.com/documentation/current/en/manual/api)
- [API Reference](https://www.zabbix.com/documentation/current/en/manual/api/reference)
- [Python Library: pyzabbix](https://github.com/lukecyca/pyzabbix)

---

**Next Steps:**
- Create automation scripts for your workflows
- Integrate with ticketing systems
- Build custom dashboards
- Automate reporting

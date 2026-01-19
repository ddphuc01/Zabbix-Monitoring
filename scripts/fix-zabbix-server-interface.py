#!/usr/bin/env python3
"""
Fix Zabbix Server Host Interface
Automatically updates the "Zabbix server" host interface from 127.0.0.1 to zabbix-agent2 container
"""

import os
import sys
import requests
from requests.auth import HTTPBasicAuth
import json

# Configuration
ZABBIX_URL = os.getenv('ZABBIX_URL', 'http://localhost:8080')
ZABBIX_USER = os.getenv('ZABBIX_USER', 'Admin')
ZABBIX_PASSWORD = os.getenv('ZABBIX_PASSWORD', 'zabbix')

# Zabbix API endpoint
API_URL = f"{ZABBIX_URL}/api_jsonrpc.php"

class ZabbixAPI:
    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password
        self.auth_token = None
        self.request_id = 1
        
    def call(self, method, params=None, include_auth=True):
        """Make a Zabbix API call"""
        headers = {'Content-Type': 'application/json-rpc'}
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.request_id,
        }
        
        # Only include auth token for methods that need it (not user.login)
        if self.auth_token and include_auth and method != "user.login":
            payload["auth"] = self.auth_token
            
        self.request_id += 1
        
        try:
            response = requests.post(self.url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if 'error' in result:
                raise Exception(f"Zabbix API error: {result['error']}")
                
            return result.get('result')
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")
    
    def login(self):
        """Authenticate with Zabbix API"""
        print("🔑 Logging in to Zabbix...")
        result = self.call("user.login", {
            "username": self.user,
            "password": self.password
        }, include_auth=False)
        self.auth_token = result
        print("✅ Login successful!")
        return result
    
    def get_host_by_name(self, hostname):
        """Get host by name"""
        return self.call("host.get", {
            "filter": {"host": [hostname]},
            "selectInterfaces": "extend",
            "output": "extend"
        })
    
    def update_host_interface(self, interface_id, dns_name):
        """Update host interface to use DNS"""
        return self.call("hostinterface.update", {
            "interfaceid": interface_id,
            "useip": 0,  # Use DNS instead of IP
            "dns": dns_name,
            "ip": ""  # Clear IP
        })

def main():
    print("=" * 60)
    print("  Zabbix Server Interface Fix")
    print("=" * 60)
    print()
    
    # Initialize API
    api = ZabbixAPI(API_URL, ZABBIX_USER, ZABBIX_PASSWORD)
    
    try:
        # Login
        api.login()
        
        # Find "Zabbix server" host
        print("\n🔍 Finding 'Zabbix server' host...")
        hosts = api.get_host_by_name("Zabbix server")
        
        if not hosts:
            print("❌ 'Zabbix server' host not found!")
            sys.exit(1)
        
        host = hosts[0]
        print(f"✅ Found host: {host['host']} (ID: {host['hostid']})")
        
        # Get agent interface
        agent_interfaces = [iface for iface in host['interfaces'] if iface['type'] == '1']
        
        if not agent_interfaces:
            print("❌ No agent interface found!")
            sys.exit(1)
        
        interface = agent_interfaces[0]
        interface_id = interface['interfaceid']
        
        print(f"\n📋 Current interface:")
        print(f"   - Type: Agent")
        print(f"   - IP: {interface['ip']}")
        print(f"   - DNS: {interface['dns']}")
        print(f"   - Port: {interface['port']}")
        print(f"   - Use IP: {interface['useip']}")
        
        # Check if already configured correctly
        if interface['dns'] == 'zabbix-agent2' and interface['useip'] == '0':
            print("\n✅ Interface already configured correctly!")
            print("   No changes needed.")
            sys.exit(0)
        
        # Update interface
        print(f"\n🔧 Updating interface to use DNS 'zabbix-agent2'...")
        api.update_host_interface(interface_id, "zabbix-agent2")
        
        print("✅ Interface updated successfully!")
        print()
        print("New configuration:")
        print("   - DNS: zabbix-agent2")
        print("   - Connect to: DNS")
        print("   - Port: 10050")
        print()
        print("🎉 Done! The Zabbix server host should now be able to monitor itself.")
        print("   Wait a few seconds and check the web UI - ZBX icon should turn green.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

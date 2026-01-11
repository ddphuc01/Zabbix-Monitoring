#!/usr/bin/env python3
"""
Zabbix Host Interface Auto-Configuration Script
Automatically configures the default "Zabbix server" host to use agent2 container
"""

import os
import sys
import time
import requests
import json

# Zabbix API Configuration
ZABBIX_URL = os.getenv('ZABBIX_URL', 'http://zabbix-web:8080')
ZABBIX_USER = os.getenv('ZABBIX_USER', 'Admin')
ZABBIX_PASS = os.getenv('ZABBIX_PASS', 'zabbix')

class ZabbixAPI:
    def __init__(self, url, user, password):
        self.url = f"{url}/api_jsonrpc.php"
        self.user = user
        self.password = password
        self.auth_token = None
        self.request_id = 0
        
    def call(self, method, params):
        """Make Zabbix API call"""
        self.request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.request_id
        }
        
        if self.auth_token and method != "user.login":
            payload["auth"] = self.auth_token
        
        try:
            response = requests.post(self.url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                raise Exception(f"API Error: {result['error']}")
            
            return result.get("result")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Connection error: {e}")
    
    def login(self):
        """Authenticate with Zabbix"""
        print("🔐 Logging in to Zabbix...")
        result = self.call("user.login", {
            "username": self.user,
            "password": self.password
        })
        self.auth_token = result
        print("✅ Logged in successfully")
        return self.auth_token
    
    def get_host_by_name(self, hostname):
        """Get host by name"""
        return self.call("host.get", {
            "filter": {"host": hostname},
            "selectInterfaces": "extend"
        })
    
    def update_host_interface(self, hostid, interfaceid, dns, port=10050):
        """Update host interface to use DNS instead of IP"""
        return self.call("hostinterface.update", {
            "interfaceid": interfaceid,
            "dns": dns,
            "ip": "",
            "useip": 0,
            "port": port
        })

def main():
    print("=" * 60)
    print("🔧 Zabbix Host Interface Auto-Configuration")
    print("=" * 60)
    
    # Wait for Zabbix to be ready
    print("\n⏳ Waiting for Zabbix Server to be ready...")
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{ZABBIX_URL}/", timeout=5)
            if response.status_code == 200:
                print("✅ Zabbix web interface is ready")
                break
        except:
            pass
        
        if i < max_retries - 1:
            print(f"   Waiting... ({i+1}/{max_retries})")
            time.sleep(10)
    else:
        print("❌ Zabbix web interface not ready after 5 minutes")
        sys.exit(1)
    
    # Wait a bit more for API to be fully ready
    time.sleep(20)
    
    try:
        # Initialize API client
        api = ZabbixAPI(ZABBIX_URL, ZABBIX_USER, ZABBIX_PASS)
        
        # Login
        api.login()
        
        # Get "Zabbix server" host
        print("\n🔍 Looking for 'Zabbix server' host...")
        hosts = api.get_host_by_name("Zabbix server")
        
        if not hosts:
            print("⚠️  'Zabbix server' host not found")
            sys.exit(1)
        
        host = hosts[0]
        hostid = host['hostid']
        print(f"✅ Found host: {host['name']} (ID: {hostid})")
        
        # Find agent interface
        agent_interface = None
        for interface in host['interfaces']:
            if interface['type'] == '1':  # Type 1 = Zabbix agent
                agent_interface = interface
                break
        
        if not agent_interface:
            print("⚠️  No agent interface found")
            sys.exit(1)
        
        interfaceid = agent_interface['interfaceid']
        current_ip = agent_interface['ip']
        current_dns = agent_interface['dns']
        current_useip = agent_interface['useip']
        
        print(f"\n📋 Current interface configuration:")
        print(f"   Interface ID: {interfaceid}")
        print(f"   IP: {current_ip}")
        print(f"   DNS: {current_dns}")
        print(f"   Use IP: {'Yes' if current_useip == '1' else 'No'}")
        
        # Check if already configured correctly
        if current_dns == "zabbix-agent2" and current_useip == '0':
            print("\n✅ Interface already configured correctly!")
            print("   No changes needed.")
            sys.exit(0)
        
        # Update interface
        print(f"\n🔄 Updating interface to use DNS 'zabbix-agent2'...")
        api.update_host_interface(
            hostid=hostid,
            interfaceid=interfaceid,
            dns="zabbix-agent2",
            port=10050
        )
        
        print("\n✅ Interface updated successfully!")
        print("   - DNS: zabbix-agent2")
        print("   - Port: 10050")
        print("   - Use IP: No (using DNS)")
        
        print("\n" + "=" * 60)
        print("✅ Configuration complete!")
        print("=" * 60)
        print("\nThe 'Zabbix server' host now uses the zabbix-agent2 container.")
        print("You can verify in: Configuration → Hosts → Zabbix server")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

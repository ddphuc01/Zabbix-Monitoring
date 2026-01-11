#!/usr/bin/env python3
"""
Zabbix Windows Host Management Script
Automatically adds Windows hosts to Zabbix with proper templates
"""

import os
import sys
import argparse
import requests
import json

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
    
    def get_hostgroup_id(self, group_name):
        """Get host group ID by name"""
        result = self.call("hostgroup.get", {
            "filter": {"name": group_name}
        })
        if result:
            return result[0]['groupid']
        
        # Create group if doesn't exist
        print(f"📁 Creating host group '{group_name}'...")
        result = self.call("hostgroup.create", {
            "name": group_name
        })
        return result['groupids'][0]
    
    def get_template_id(self, template_name):
        """Get template ID by name"""
        result = self.call("template.get", {
            "filter": {"host": template_name}
        })
        if result:
            return result[0]['templateid']
        raise Exception(f"Template '{template_name}' not found")
    
    def get_host(self, hostname):
        """Get host by name"""
        return self.call("host.get", {
            "filter": {"host": hostname},
            "selectInterfaces": "extend",
            "selectGroups": "extend",
            "selectParentTemplates": "extend"
        })
    
    def create_host(self, hostname, ip_address, group_ids, template_ids, description=""):
        """Create new host"""
        print(f"➕ Creating host '{hostname}'...")
        
        result = self.call("host.create", {
            "host": hostname,
            "name": description or hostname,
            "interfaces": [
                {
                    "type": 1,  # Agent
                    "main": 1,
                    "useip": 1,
                    "ip": ip_address,
                    "dns": "",
                    "port": "10050"
                }
            ],
            "groups": [{"groupid": gid} for gid in group_ids],
            "templates": [{"templateid": tid} for tid in template_ids]
        })
        
        return result['hostids'][0]
    
    def update_host(self, hostid, group_ids, template_ids):
        """Update existing host"""
        print(f"🔄 Updating host...")
        
        self.call("host.update", {
            "hostid": hostid,
            "groups": [{"groupid": gid} for gid in group_ids],
            "templates": [{"templateid": tid} for tid in template_ids]
        })

def main():
    parser = argparse.ArgumentParser(description='Add Windows host to Zabbix')
    parser.add_argument('--hostname', required=True, help='Windows hostname')
    parser.add_argument('--ip', required=True, help='Windows IP address')
    parser.add_argument('--description', default='', help='Host description')
    parser.add_argument('--url', default='http://192.168.1.203:8080', help='Zabbix URL')
    parser.add_argument('--user', default='Admin', help='Zabbix username')
    parser.add_argument('--password', default='zabbix', help='Zabbix password')
    parser.add_argument('--group', default='Windows servers', help='Host group name')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🪟 Zabbix Windows Host Management")
    print("=" * 60 + "\n")
    
    try:
        # Initialize API
        api = ZabbixAPI(args.url, args.user, args.password)
        api.login()
        
        # Check if host already exists
        print(f"\n🔍 Checking if host '{args.hostname}' exists...")
        existing_hosts = api.get_host(args.hostname)
        
        # Get group ID
        group_id = api.get_hostgroup_id(args.group)
        
        # Get Windows template IDs
        print("\n📋 Getting Windows templates...")
        templates = [
            "Windows by Zabbix agent",
            "Windows by Zabbix agent active"
        ]
        
        template_ids = []
        for template_name in templates:
            try:
                tid = api.get_template_id(template_name)
                template_ids.append(tid)
                print(f"  ✓ Found: {template_name}")
            except Exception as e:
                print(f"  ⚠ Template not found: {template_name}")
        
        if not template_ids:
            print("\n⚠️  Warning: No Windows templates found!")
            print("    Host will be created without templates.")
        
        # Create or update host
        if existing_hosts:
            print(f"\n⚠️  Host '{args.hostname}' already exists")
            host = existing_hosts[0]
            hostid = host['hostid']
            
            print(f"  Current groups: {', '.join([g['name'] for g in host['groups']])}")
            print(f"  Current templates: {', '.join([t['name'] for t in host['parentTemplates']])}")
            
            response = input("\nUpdate host? (y/N): ")
            if response.lower() == 'y':
                api.update_host(hostid, [group_id], template_ids)
                print("\n✅ Host updated successfully!")
            else:
                print("\n❌ Host update cancelled")
        else:
            hostid = api.create_host(
                args.hostname,
                args.ip,
                [group_id],
                template_ids,
                args.description
            )
            print(f"\n✅ Host created successfully! (ID: {hostid})")
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ Operation Complete!")
        print("=" * 60 + "\n")
        
        print(f"Host Details:")
        print(f"  Hostname:     {args.hostname}")
        print(f"  IP Address:   {args.ip}")
        print(f"  Group:        {args.group}")
        print(f"  Templates:    {len(template_ids)} linked")
        
        print(f"\n🌐 View host in web interface:")
        print(f"  {args.url}/zabbix.php?action=host.list")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

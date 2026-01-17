#!/usr/bin/env python3
"""
Zabbix Host Auto-Registration Script
Automatically creates a host in Zabbix via API after Agent installation
"""

import os
import sys
import requests
import json

# Configuration
ZABBIX_API_URL = os.getenv('ZABBIX_API_URL', 'http://192.168.1.203:8080/api_jsonrpc.php')
ZABBIX_USER = os.getenv('ZABBIX_USER', 'Admin')
ZABBIX_PASSWORD = os.getenv('ZABBIX_PASSWORD', 'zabbix')

class ZabbixAPI:
    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password
        self.auth_token = None
        
    def _call(self, method, params):
        """Make JSON-RPC call to Zabbix API"""
        headers = {'Content-Type': 'application/json'}
        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': 1
        }
        
        if self.auth_token and method != 'user.login':
            payload['auth'] = self.auth_token
            
        response = requests.post(self.url, json=payload, headers=headers)
        result = response.json()
        
        if 'error' in result:
            raise Exception(f"Zabbix API Error: {result['error']}")
            
        return result.get('result')
    
    def login(self):
        """Authenticate with Zabbix"""
        self.auth_token = self._call('user.login', {
            'username': self.user,
            'password': self.password
        })
        return self.auth_token
    
    def get_template_id(self, template_name):
        """Get template ID by name"""
        templates = self._call('template.get', {
            'filter': {'host': template_name}
        })
        return templates[0]['templateid'] if templates else None
    
    def get_hostgroup_id(self, group_name):
        """Get or create host group"""
        groups = self._call('hostgroup.get', {
            'filter': {'name': group_name}
        })
        if groups:
            return groups[0]['groupid']
        
        # Create group if doesn't exist
        result = self._call('hostgroup.create', {'name': group_name})
        return result['groupids'][0]
    
    def host_exists(self, hostname):
        """Check if host already exists"""
        hosts = self._call('host.get', {
            'filter': {'host': hostname}
        })
        return len(hosts) > 0
    
    def create_host(self, hostname, ip_address, template_name='Linux by Zabbix agent', group_name='Linux servers'):
        """Create a new host in Zabbix"""
        if self.host_exists(hostname):
            print(f"✅ Host {hostname} already exists in Zabbix")
            return
        
        # Get template and group IDs
        template_id = self.get_template_id(template_name)
        group_id = self.get_hostgroup_id(group_name)
        
        if not template_id:
            print(f"⚠️  Template '{template_name}' not found, creating host without template")
            templates = []
        else:
            templates = [{'templateid': template_id}]
        
        # Create host
        result = self._call('host.create', {
            'host': hostname,
            'interfaces': [{
                'type': 1,  # Agent interface
                'main': 1,
                'useip': 1,
                'ip': ip_address,
                'dns': '',
                'port': '10050'
            }],
            'groups': [{'groupid': group_id}],
            'templates': templates
        })
        
        print(f"✅ Successfully created host {hostname} (ID: {result['hostids'][0]})")
        return result['hostids'][0]


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 zabbix_register_host.py <hostname> <ip_address> [template_name]")
        print("Example: python3 zabbix_register_host.py host-192.168.1.143 192.168.1.143")
        sys.exit(1)
    
    hostname = sys.argv[1]
    ip_address = sys.argv[2]
    template_name = sys.argv[3] if len(sys.argv) > 3 else 'Linux by Zabbix agent'
    
    try:
        # Connect to Zabbix
        zapi = ZabbixAPI(ZABBIX_API_URL, ZABBIX_USER, ZABBIX_PASSWORD)
        print(f"🔐 Logging in to Zabbix at {ZABBIX_API_URL}...")
        zapi.login()
        print("✅ Authentication successful")
        
        # Create host
        print(f"📝 Creating host {hostname} ({ip_address})...")
        zapi.create_host(hostname, ip_address, template_name)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

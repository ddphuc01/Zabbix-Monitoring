#!/usr/bin/env python3
"""
Update Zabbix Actions to use new AI Webhook instead of old scripts
Removes references to deprecated Qwen/Ollama scripts
"""

import requests
import json
import os
import sys

# Zabbix API configuration
ZABBIX_URL = os.getenv('ZABBIX_API_URL', 'http://localhost:8080/api_jsonrpc.php')
ZABBIX_USER = os.getenv('ZABBIX_API_USER', 'Admin')
ZABBIX_PASSWORD = os.getenv('ZABBIX_API_PASSWORD', 'zabbix')

# Deprecated scripts to find and replace
DEPRECATED_SCRIPTS = [
    'telegram_qwen.sh',
    'telegram_ai_v4.sh',
    'telegram_interactive.sh'
]

# New webhook URL
NEW_WEBHOOK_URL = 'http://ai-webhook:5000/webhook'


class ZabbixAPI:
    """Simple Zabbix API client"""
    
    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password
        self.auth_token = None
        self.request_id = 1
    
    def _request(self, method, params):
        """Make API request"""
        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': self.request_id
        }
        
        if self.auth_token:
            payload['auth'] = self.auth_token
        
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = requests.post(self.url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                raise Exception(f"API Error: {data['error']}")
            
            self.request_id += 1
            return data.get('result')
        
        except Exception as e:
            print(f"❌ API Request failed: {e}")
            raise
    
    def login(self):
        """Authenticate with Zabbix"""
        print(f"🔐 Logging in to Zabbix as {self.user}...")
        
        # Zabbix 7.x uses 'username' and 'password' instead of 'user'
        result = self._request('user.login', {
            'username': self.user,  # Changed from 'user' to 'username'
            'password': self.password
        })
        
        self.auth_token = result
        print("✅ Logged in successfully")
        return result
    
    def get_actions(self):
        """Get all trigger actions"""
        print("📋 Fetching all trigger actions...")
        result = self._request('action.get', {
            'output': 'extend',
            'selectOperations': 'extend',
            'selectRecoveryOperations': 'extend',
            'filter': {
                'eventsource': 0  # Trigger events
            }
        })
        print(f"✅ Found {len(result)} actions")
        return result
    
    def get_media_types(self):
        """Get all media types"""
        print("📱 Fetching media types...")
        result = self._request('mediatype.get', {
            'output': 'extend'
        })
        return result
    
    def create_webhook_mediatype(self):
        """Create new webhook media type if not exists"""
        print("🔗 Creating AI Webhook media type...")
        
        # Check if already exists
        existing = self._request('mediatype.get', {
            'output': 'extend',
            'filter': {
                'name': 'AI Webhook (Groq)'
            }
        })
        
        if existing:
            print(f"✅ Webhook media type already exists (ID: {existing[0]['mediatypeid']})")
            return existing[0]['mediatypeid']
        
        # Create new webhook media type
        result = self._request('mediatype.create', {
            'name': 'AI Webhook (Groq)',
            'type': 4,  # Webhook
            'webhook_url': NEW_WEBHOOK_URL,
            'webhook_script': '''
var params = JSON.parse(value);
var req = new CurlHttpRequest();
req.AddHeader('Content-Type: application/json');

var payload = {
    trigger_name: params.trigger_name || '{TRIGGER.NAME}',
    host_name: params.host_name || '{HOST.NAME}',
    trigger_severity: params.trigger_severity || '{TRIGGER.SEVERITY}',
    trigger_value: params.trigger_value || '{ITEM.VALUE}',
    event_time: params.event_time || '{EVENT.TIME}',
    event_id: params.event_id || '{EVENT.ID}'
};

var resp = req.Post(params.webhook_url, JSON.stringify(payload));
Zabbix.log(4, 'AI Webhook response: ' + resp);
return 'OK';
            ''',
            'process_tags': 0,
            'parameters': [
                {'name': 'trigger_name', 'value': '{TRIGGER.NAME}'},
                {'name': 'host_name', 'value': '{HOST.NAME}'},
                {'name': 'trigger_severity', 'value': '{TRIGGER.SEVERITY}'},
                {'name': 'trigger_value', 'value': '{ITEM.VALUE}'},
                {'name': 'event_time', 'value': '{EVENT.TIME}'},
                {'name': 'event_id', 'value': '{EVENT.ID}'},
                {'name': 'webhook_url', 'value': NEW_WEBHOOK_URL}
            ]
        })
        
        mediatype_id = result['mediatypeids'][0]
        print(f"✅ Created webhook media type (ID: {mediatype_id})")
        return mediatype_id
    
    def update_action(self, action_id, action_name, operations):
        """Update action operations"""
        print(f"🔄 Updating action '{action_name}' (ID: {action_id})...")
        
        result = self._request('action.update', {
            'actionid': action_id,
            'operations': operations
        })
        
        print(f"✅ Updated action '{action_name}'")
        return result


def find_deprecated_actions(zabbix):
    """Find actions using deprecated scripts"""
    actions = zabbix.get_actions()
    deprecated_actions = []
    
    print("\n🔍 Scanning for actions using deprecated scripts...")
    
    for action in actions:
        action_id = action['actionid']
        action_name = action['name']
        has_deprecated = False
        
        # Check operations
        for op in action.get('operations', []):
            # Check if operation uses script
            if 'opcommand' in op:
                script_name = op['opcommand'].get('scriptid', '')
                command = op['opcommand'].get('command', '')
                
                # Check if it's one of our deprecated scripts
                for deprecated in DEPRECATED_SCRIPTS:
                    if deprecated in command or deprecated in str(script_name):
                        has_deprecated = True
                        print(f"  ❌ Action '{action_name}' uses deprecated script: {deprecated}")
                        break
        
        if has_deprecated:
            deprecated_actions.append({
                'id': action_id,
                'name': action_name,
                'action': action
            })
    
    return deprecated_actions


def main():
    """Main execution"""
    print("=" * 60)
    print("Zabbix Actions Update Script")
    print("Removing deprecated Qwen/Ollama script references")
    print("=" * 60)
    print()
    
    try:
        # Connect to Zabbix
        zabbix = ZabbixAPI(ZABBIX_URL, ZABBIX_USER, ZABBIX_PASSWORD)
        zabbix.login()
        
        # Find deprecated actions
        deprecated_actions = find_deprecated_actions(zabbix)
        
        if not deprecated_actions:
            print("\n✅ No actions found using deprecated scripts!")
            print("Your Zabbix configuration is clean.")
            return 0
        
        print(f"\n⚠️  Found {len(deprecated_actions)} action(s) to update:")
        for action in deprecated_actions:
            print(f"   - {action['name']}")
        
        # Ask for confirmation
        print("\n" + "=" * 60)
        print("⚠️  WARNING: This will modify your Zabbix actions!")
        print("=" * 60)
        response = input("\nDo you want to proceed? (yes/no): ")
        
        if response.lower() not in ['yes', 'y']:
            print("❌ Cancelled by user")
            return 1
        
        # Create webhook media type
        webhook_id = zabbix.create_webhook_mediatype()
        
        # Update each action
        print("\n🔧 Updating actions...")
        for action_data in deprecated_actions:
            action = action_data['action']
            action_id = action['actionid']
            action_name = action['name']
            
            # Filter out operations using deprecated scripts
            new_operations = []
            for op in action.get('operations', []):
                # Skip operations with deprecated scripts
                skip = False
                if 'opcommand' in op:
                    command = op['opcommand'].get('command', '')
                    for deprecated in DEPRECATED_SCRIPTS:
                        if deprecated in command:
                            skip = True
                            print(f"   ⚠️  Removing deprecated operation from '{action_name}'")
                            break
                
                if not skip:
                    new_operations.append(op)
            
            # Update action
            if len(new_operations) != len(action.get('operations', [])):
                zabbix.update_action(action_id, action_name, new_operations)
            else:
                print(f"   ℹ️  No changes needed for '{action_name}'")
        
        print("\n" + "=" * 60)
        print("✅ UPDATE COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Restart Zabbix server: docker compose restart zabbix-server")
        print("2. Configure webhook in UI if needed")
        print("3. Test with a sample alert")
        print()
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

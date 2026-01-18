#!/usr/bin/env python3
"""
Ansible Executor REST API
Provides HTTP endpoints to execute Ansible playbooks
"""

import os
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import tempfile
from datetime import datetime
from typing import Dict, Any

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
CORS(app)

# Configuration
ANSIBLE_DIR = os.getenv('ANSIBLE_DIR', '/ansible')
PLAYBOOK_DIR = os.path.join(ANSIBLE_DIR, 'playbooks')
INVENTORY_FILE = os.path.join(ANSIBLE_DIR, 'inventory/hosts.yml')


class AnsibleRunner:
    """Execute Ansible playbooks and return results"""
    
    @staticmethod
    def run_playbook(playbook_name: str, target_host: str, extra_vars: Dict = None) -> Dict[str, Any]:
        """
        Execute an Ansible playbook
        
        Args:
            playbook_name: Playbook name (e.g., 'restart_service', 'check_service')
            target_host: Target hostname
            extra_vars: Extra variables for playbook
            
        Returns:
            {
                'status': 'success' or 'failed',
                'result': dict with playbook output,
                'duration': float (seconds),
                'error': str or None
            }
        """
        start_time = datetime.now()
        
        try:
            # Read inventory to detect host OS
            import yaml
            with open(INVENTORY_FILE, 'r') as f:
                inventory = yaml.safe_load(f)
            
            # Check if host is in windows group
            is_windows = False
            if inventory and 'all' in inventory:
                windows_group = inventory['all'].get('children', {}).get('windows', {})
                windows_hosts = windows_group.get('hosts', {})
                if target_host in windows_hosts:
                    is_windows = True
            
            # Determine playbook path based on type and OS
            if playbook_name in ['restart_service', 'check_service']:
                playbook_path = os.path.join(PLAYBOOK_DIR, 'services', f'{playbook_name}.yml')
            elif playbook_name == 'gather_system_metrics':
                # Auto-detect Windows and use appropriate playbook
                if is_windows:
                    playbook_path = os.path.join(PLAYBOOK_DIR, 'diagnostics', 'gather_windows_metrics.yml')
                    logger.info(f"Detected Windows host: {target_host}, using Windows metrics playbook")
                else:
                    playbook_path = os.path.join(PLAYBOOK_DIR, 'diagnostics', f'{playbook_name}.yml')
            elif playbook_name == 'diagnostic_cpu':
                playbook_path = os.path.join(PLAYBOOK_DIR, 'diagnostics', f'{playbook_name}.yml')
            else:
                playbook_path = os.path.join(PLAYBOOK_DIR, f'{playbook_name}.yml')
            
            # Check if playbook exists
            if not os.path.exists(playbook_path):
                return {
                    'status': 'failed',
                    'result': {},
                    'duration': 0,
                    'error': f'Playbook not found: {playbook_path}'
                }
            
            # Build ansible-playbook command
            cmd = [
                'ansible-playbook',
                playbook_path,
                '-i', INVENTORY_FILE,
                '-e', f'target_host={target_host}'
            ]
            
            # Add extra vars
            if extra_vars:
                for key, value in extra_vars.items():
                    cmd.extend(['-e', f'{key}={value}'])
            
            logger.info(f"Executing: {' '.join(cmd)}")
            
            # Execute playbook
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes max
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # Parse output
            if result.returncode == 0:
                return {
                    'status': 'success',
                    'result': {
                        'stdout': result.stdout,
                        'changed': 'changed=' in result.stdout,
                        'failed': False
                    },
                    'duration': duration,
                    'error': None
                }
            else:
                return {
                    'status': 'failed',
                    'result': {
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'failed': True
                    },
                    'duration': duration,
                    'error': f'Playbook failed (exit code {result.returncode})'
                }
                
        except subprocess.TimeoutExpired:
            duration = (datetime.now() - start_time).total_seconds()
            return {
                'status': 'failed',
                'result': {},
                'duration': duration,
                'error': 'Playbook execution timeout (5 minutes)'
            }
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Playbook execution error: {e}")
            return {
                'status': 'failed',
                'result': {},
                'duration': duration,
                'error': str(e)
            }


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ansible-executor-api',
        'ansible_dir': ANSIBLE_DIR,
        'playbook_dir': PLAYBOOK_DIR,
        'inventory': INVENTORY_FILE
    }), 200


@app.route('/api/v1/playbook/run', methods=['POST'])
def run_playbook():
    """
    Execute an Ansible playbook
    
    POST /api/v1/playbook/run
    Body:
    {
        "playbook": "restart_service",
        "target_host": "WIN-PC-129",
        "extra_vars": {
            "service_name": "Spooler"
        }
    }
    
    Response:
    {
        "status": "success",
        "result": {...},
        "duration": 5.2,
        "error": null
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'failed',
                'error': 'No JSON data provided'
            }), 400
        
        playbook = data.get('playbook')
        target_host = data.get('target_host')
        extra_vars = data.get('extra_vars', {})
        
        if not playbook:
            return jsonify({
                'status': 'failed',
                'error': 'Missing required field: playbook'
            }), 400
        
        if not target_host:
            return jsonify({
                'status': 'failed',
                'error': 'Missing required field: target_host'
            }), 400
        
        # Normalize hostname to lowercase to match inventory
        target_host = target_host.lower()

        logger.info(f"API request: playbook={playbook}, host={target_host}, vars={extra_vars}")
        
        # Execute playbook
        result = AnsibleRunner.run_playbook(playbook, target_host, extra_vars)
        
        status_code = 200 if result['status'] == 'success' else 500
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500


@app.route('/api/v1/playbooks', methods=['GET'])
def list_playbooks():
    """List available playbooks"""
    try:
        playbooks = []
        
        # Scan playbook directories
        for root, dirs, files in os.walk(PLAYBOOK_DIR):
            for file in files:
                if file.endswith('.yml') or file.endswith('.yaml'):
                    rel_path = os.path.relpath(os.path.join(root, file), PLAYBOOK_DIR)
                    playbooks.append(rel_path)
        
        return jsonify({
            'playbooks': sorted(playbooks),
            'count': len(playbooks)
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


if __name__ == '__main__':
    logger.info("🚀 Starting Ansible Executor REST API on port 5001")
    logger.info(f"   Playbook directory: {PLAYBOOK_DIR}")
    logger.info(f"   Inventory: {INVENTORY_FILE}")
    
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=False
    )

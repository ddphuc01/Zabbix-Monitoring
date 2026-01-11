#!/usr/bin/env python3
"""
Ansible Executor - Execute Ansible playbooks and parse results
Integrates Ansible automation with Zabbix AI system
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import ansible_runner

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ANSIBLE_DIR = os.getenv('ANSIBLE_DIR', '/ansible')
PLAYBOOK_DIR = os.path.join(ANSIBLE_DIR, 'playbooks')
INVENTORY_FILE = os.path.join(ANSIBLE_DIR, 'inventory/hosts.yml')
MAX_EXECUTION_TIME = int(os.getenv('DIAGNOSTIC_TIMEOUT', 60))


class AnsibleExecutor:
    """Execute Ansible playbooks and parse results"""
    
    def __init__(self):
        self.playbook_dir = PLAYBOOK_DIR
        self.inventory = INVENTORY_FILE
        logger.info(f"✅ AnsibleExecutor initialized")
        logger.info(f"   Playbook dir: {self.playbook_dir}")
        logger.info(f"   Inventory: {self.inventory}")
    
    async def run_diagnostic(
        self, 
        playbook_name: str, 
        host: str, 
        extra_vars: Optional[Dict] = None
    ) -> Dict:
        """
        Run diagnostic playbook and return structured results
        
        Args:
            playbook_name: Name without extension (e.g., 'diagnostic_cpu')
            host: Target hostname or IP
            extra_vars: Additional variables for playbook
            
        Returns:
            {
                'success': True/False,
                'data': {...},  # Parsed diagnostic data
                'duration': 5.2,  # seconds
                'error': None or str
            }
        """
        start_time = datetime.now()
        playbook_path = os.path.join('diagnostics', f'{playbook_name}.yml')
        
        logger.info(f"🔍 Running diagnostic: {playbook_name} on {host}")
        
        try:
            # Build extra vars
            extravars = extra_vars or {}
            extravars['target_host'] = host
            
            # Run playbook using ansible-runner
            result = await self._execute_playbook(
                playbook_path,
                extravars,
                timeout=MAX_EXECUTION_TIME
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if result['status'] == 'successful':
                diagnostic_data = self._parse_diagnostic_output(result)
                
                logger.info(f"✅ Diagnostic completed in {duration:.2f}s")
                
                return {
                    'success': True,
                    'data': diagnostic_data,
                    'duration': duration,
                    'host': host,
                    'playbook': playbook_name,
                    'timestamp': datetime.utcnow().isoformat(),
                    'error': None
                }
            else:
                error_msg = result.get('error', 'Playbook execution failed')
                logger.error(f"❌ Diagnostic failed: {error_msg}")
                
                return {
                    'success': False,
                    'data': {},
                    'duration': duration,
                    'host': host,
                    'playbook': playbook_name,
                    'error': error_msg
                }
                
        except asyncio.TimeoutError:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"⏱️  Diagnostic timeout after {duration}s")
            return {
                'success': False,
                'data': {},
                'duration': duration,
                'error': f'Timeout after {MAX_EXECUTION_TIME}s'
            }
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Unexpected error: {e}")
            return {
                'success': False,
                'data': {},
                'duration': duration,
                'error': str(e)
            }
    
    async def _execute_playbook(
        self, 
        playbook: str, 
        extravars: Dict,
        timeout: int
    ) -> Dict:
        """Execute playbook using ansible-runner"""
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        def _run():
            # ansible-runner execution
            r = ansible_runner.run(
                playbook=playbook,
                private_data_dir=ANSIBLE_DIR,
                inventory=self.inventory,
                extravars=extravars,
                quiet=False,
                verbosity=0,
                json_mode=True
            )
            
            return {
                'status': r.status,
                'rc': r.rc,
                'stats': r.stats,
                'events': list(r.events),
                'error': r.stderr.read() if r.stderr else None
            }
        
        # Run with timeout
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, _run),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.error(f"Playbook execution timeout")
            raise
    
    def _parse_diagnostic_output(self, result: Dict) -> Dict:
        """Parse ansible-runner output to extract diagnostic data"""
        
        try:
            # Find the task that sets diagnostic_report
            for event in result['events']:
                if event.get('event') == 'runner_on_ok':
                    event_data = event.get('event_data', {})
                    
                    # Check if this task set the diagnostic_report fact
                    res = event_data.get('res', {})
                    ansible_facts = res.get('ansible_facts', {})
                    
                    if 'diagnostic_report' in ansible_facts:
                        diagnostic_data = ansible_facts['diagnostic_report']
                        logger.info(f"📊 Parsed diagnostic data: {len(str(diagnostic_data))} bytes")
                        return diagnostic_data
            
            # Fallback: extract from final stats
            logger.warning("⚠️  diagnostic_report not found, using fallback parsing")
            return {
                'success': True,
                'message': 'Diagnostic completed but data structure not found',
                'raw_stats': result.get('stats', {})
            }
            
        except Exception as e:
            logger.error(f"❌ Error parsing diagnostic output: {e}")
            return {
                'success': False,
                'error': f'Parse error: {str(e)}'
            }
    
    async def deploy_agent(
        self, 
        hosts: List[str], 
        version: str = '7.4',
        extra_vars: Optional[Dict] = None
    ) -> Dict:
        """
        Deploy Zabbix Agent to hosts
        
        Args:
            hosts: List of target hosts
            version: Zabbix version to install
            extra_vars: Additional variables
            
        Returns:
            {
                'success': True/False,
                'deployed_hosts': [],
                'failed_hosts': [],
                'summary': str
            }
        """
        logger.info(f"🚀 Deploying Zabbix Agent {version} to {len(hosts)} hosts")
        
        playbook_path = os.path.join('deploy', 'deploy_agent.yml')
        
        extravars = extra_vars or {}
        extravars['target_hosts'] = ','.join(hosts)
        extravars['zabbix_version'] = version
        
        try:
            result = await self._execute_playbook(
                playbook_path,
                extravars,
                timeout=300  # 5 minutes for deployment
            )
            
            if result['status'] == 'successful':
                return {
                    'success': True,
                    'deployed_hosts': hosts,
                    'failed_hosts': [],
                    'summary': f'Successfully deployed to {len(hosts)} hosts'
                }
            else:
                return {
                    'success': False,
                    'deployed_hosts': [],
                    'failed_hosts': hosts,
                    'summary': 'Deployment failed',
                    'error': result.get('error')
                }
                
        except Exception as e:
            logger.error(f"❌ Deployment error: {e}")
            return {
                'success': False,
                'deployed_hosts': [],
                'failed_hosts': hosts,
                'summary': 'Deployment exception',
                'error': str(e)
            }
    
    def validate_playbook(self, playbook_name: str) -> bool:
        """Check if playbook exists and is valid"""
        playbook_file = os.path.join(self.playbook_dir, 'diagnostics', f'{playbook_name}.yml')
        exists = os.path.isfile(playbook_file)
        
        if exists:
            logger.info(f"✅ Playbook found: {playbook_file}")
        else:
            logger.warning(f"⚠️  Playbook not found: {playbook_file}")
        
        return exists


# Singleton instance
_executor = None

def get_executor() -> AnsibleExecutor:
    """Get singleton executor instance"""
    global _executor
    if _executor is None:
        _executor = AnsibleExecutor()
    return _executor

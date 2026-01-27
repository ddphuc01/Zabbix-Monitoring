#!/usr/bin/env python3
"""
Ansible REST API Service
Execute Ansible playbooks from host machine via REST API
Allows containerized services to trigger Ansible without running Ansible in containers
"""

import os
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import ansible_runner

# Configuration
ANSIBLE_DIR = os.getenv('ANSIBLE_DIR', '/home/phuc/zabbix-monitoring/ansible')
PLAYBOOK_DIR = os.path.join(ANSIBLE_DIR, 'playbooks')
INVENTORY_FILE = os.path.join(ANSIBLE_DIR, 'inventory/hosts.yml')
MAX_EXECUTION_TIME = int(os.getenv('DIAGNOSTIC_TIMEOUT', 120))
API_KEY = os.getenv('ANSIBLE_API_KEY', 'changeme')

# Force Ansible to use project's ansible.cfg instead of /etc/ansible/ansible.cfg
ANSIBLE_CONFIG = os.path.join(ANSIBLE_DIR, 'ansible.cfg')
os.environ['ANSIBLE_CONFIG'] = ANSIBLE_CONFIG

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Ansible REST API",
    description="Execute Ansible playbooks via REST API",
    version="1.0.0"
)

# Request/Response models
class PlaybookRunRequest(BaseModel):
    playbook: str = Field(..., description="Playbook name without .yml extension")
    target_host: str = Field(..., description="Target hostname from inventory")
    extra_vars: Optional[Dict] = Field(default={}, description="Additional variables")

class PlaybookRunResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict] = None
    error: Optional[str] = None
    duration: Optional[float] = None

# In-memory job storage (for simple implementation)
jobs: Dict[str, Dict] = {}


async def execute_playbook_async(
    job_id: str,
    playbook_name: str, 
    target_host: str, 
    extra_vars: Dict
) -> Dict:
    """Execute Ansible playbook asynchronously"""
    start_time = datetime.now()
    playbook_path = os.path.join('diagnostics', f'{playbook_name}.yml')
    
    logger.info(f"[{job_id}] Starting playbook: {playbook_name} on {target_host}")
    
    try:
        # Prepare extra vars
        extravars = extra_vars.copy()
        extravars['target_host'] = target_host
        
        # Run Ansible playbook
        loop = asyncio.get_event_loop()
        
        def _run_ansible():
            """Run ansible-runner in thread"""
            # ansible-runner expects playbooks in private_data_dir/project/
            # Create symlink if it doesn't exist or fix if broken
            project_link = os.path.join(ANSIBLE_DIR, 'project')
            
            # Remove broken symlink if exists
            if os.path.islink(project_link) and not os.path.exists(project_link):
                os.unlink(project_link)
            
            # Create symlink with relative path (more portable)
            if not os.path.exists(project_link):
                os.symlink('playbooks', project_link)
            
            # Force default callback to prevent ansible-runner from injecting awx_display
            # which conflicts with ansible.posix.json missing json_indent option
            import os as local_os
            env_backup = local_os.environ.get('ANSIBLE_STDOUT_CALLBACK')
            local_os.environ['ANSIBLE_STDOUT_CALLBACK'] = 'default'
            
            try:
                r = ansible_runner.run(
                    playbook=playbook_path,
                    private_data_dir=ANSIBLE_DIR,
                    inventory=INVENTORY_FILE,
                    extravars=extravars,
                    quiet=False,
                    verbosity=1,
                    json_mode=False,  # Disabled - conflicts with ansible callback plugins
                    suppress_env_files=True  # Don't load env files that might override settings
                )
            finally:
                # Restore original env var
                if env_backup is not None:
                    local_os.environ['ANSIBLE_STDOUT_CALLBACK'] = env_backup
                elif 'ANSIBLE_STDOUT_CALLBACK' in local_os.environ:
                    del local_os.environ['ANSIBLE_STDOUT_CALLBACK']
            
            return {
                'status': r.status,
                'rc': r.rc,
                'stats': r.stats,
                'events': list(r.events) if r.events else []
            }
        
        # Execute with timeout
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _run_ansible),
            timeout=MAX_EXECUTION_TIME
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Parse result
        if result['status'] == 'successful':
            diagnostic_data = parse_ansible_output(result)
            
            logger.info(f"[{job_id}] ✅ Success in {duration:.2f}s")
            
            return {
                'status': 'success',
                'result': diagnostic_data,
                'duration': duration,
                'host': target_host,
                'playbook': playbook_name,
                'timestamp': datetime.utcnow().isoformat(),
                'error': None
            }
        else:
            error_msg = f"Playbook execution failed with status: {result['status']}"
            logger.error(f"[{job_id}] ❌ {error_msg}")
            
            return {
                'status': 'failed',
                'result': {},
                'duration': duration,
                'error': error_msg
            }
            
    except asyncio.TimeoutError:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = f'Timeout after {MAX_EXECUTION_TIME}s'
        logger.error(f"[{job_id}] ⏱️ {error_msg}")
        
        return {
            'status': 'failed',
            'result': {},
            'duration': duration,
            'error': error_msg
        }
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = str(e)
        logger.error(f"[{job_id}] ❌ Exception: {error_msg}")
        
        return {
            'status': 'failed',
            'result': {},
            'duration': duration,
            'error': error_msg
        }


def parse_ansible_output(result: Dict) -> Dict:
    """Parse Ansible output to extract diagnostic data"""
    try:
        # Look for debug task output with metrics
        for event in result.get('events', []):
            if event.get('event') == 'runner_on_ok':
                event_data = event.get('event_data', {})
                res = event_data.get('res', {})
                
                # Check if this is our debug output with metrics
                msg = res.get('msg', {})
                if isinstance(msg, dict) and 'os_family' in msg:
                    logger.info(f"📊 Found diagnostic data: {list(msg.keys())}")
                    return msg
        
        # Fallback: return stats
        logger.warning("⚠️ Diagnostic data not found in expected format")
        return {
            'success': True,
            'message': 'Completed but data structure not in expected format',
            'raw_stats': result.get('stats', {})
        }
        
    except Exception as e:
        logger.error(f"❌ Error parsing output: {e}")
        return {
            'success': False,
            'error': f'Parse error: {str(e)}'
        }


# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ansible-rest-api",
        "timestamp": datetime.utcnow().isoformat(),
        "ansible_dir": ANSIBLE_DIR,
        "inventory": INVENTORY_FILE,
        "playbook_dir": PLAYBOOK_DIR
    }


@app.post("/api/v1/playbook/run", response_model=PlaybookRunResponse)
async def run_playbook(request: PlaybookRunRequest):
    """
    Execute Ansible playbook
    
    Returns immediately with job_id and executes playbook synchronously
    For this implementation, we wait for completion before returning
    """
    
    # Validate playbook exists
    playbook_file = Path(PLAYBOOK_DIR) / 'diagnostics' / f'{request.playbook}.yml'
    if not playbook_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Playbook not found: {request.playbook}"
        )
    
    # Validate inventory contains target host
    # (Skip detailed validation for now, Ansible will handle it)
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Store job
    jobs[job_id] = {
        'status': 'running',
        'playbook': request.playbook,
        'target_host': request.target_host,
        'created_at': datetime.utcnow().isoformat()
    }
    
    # Execute playbook (synchronous for simplicity)
    result = await execute_playbook_async(
        job_id,
        request.playbook,
        request.target_host,
        request.extra_vars
    )
    
    # Update job
    jobs[job_id].update(result)
    
    return PlaybookRunResponse(
        job_id=job_id,
        status=result['status'],
        result=result.get('result'),
        error=result.get('error'),
        duration=result.get('duration')
    )


@app.get("/api/v1/playbook/status/{job_id}")
async def get_job_status(job_id: str):
    """Get job status by ID"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]


@app.get("/api/v1/jobs")
async def list_jobs():
    """List all jobs (last 100)"""
    return {
        "total": len(jobs),
        "jobs": list(jobs.values())[-100:]
    }


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting Ansible REST API Service")
    logger.info(f"   Ansible Dir: {ANSIBLE_DIR}")
    logger.info(f"   Inventory: {INVENTORY_FILE}")
    logger.info(f"   Playbook Dir: {PLAYBOOK_DIR}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5001,
        log_level="info"
    )

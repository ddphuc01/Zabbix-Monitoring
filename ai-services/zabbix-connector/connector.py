"""
Zabbix API Connector for Open WebUI
Provides REST API endpoints to query Zabbix data
"""

import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Zabbix API Connector")

# CORS for Open WebUI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
ZABBIX_API_URL = os.getenv("ZABBIX_API_URL", "http://zabbix-web:8080/api_jsonrpc.php")
ZABBIX_USER = os.getenv("ZABBIX_USER", "Admin")
ZABBIX_PASSWORD = os.getenv("ZABBIX_PASSWORD", "zabbix")

class ZabbixAPI:
    def __init__(self):
        self.url = ZABBIX_API_URL
        self.auth_token = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate and get auth token"""
        try:
            response = self.call_api("user.login", {
                "username": ZABBIX_USER,
                "password": ZABBIX_PASSWORD
            }, auth_required=False)
            
            if "result" in response:
                self.auth_token = response["result"]
                logger.info(f"✅ Authenticated with Zabbix as {ZABBIX_USER}")
                return True
            else:
                logger.error(f"❌ Authentication failed: {response.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"❌ Authentication error: {str(e)}")
            return False
    
    def call_api(self, method: str, params: dict, auth_required: bool = True) -> dict:
        """Call Zabbix API"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        
        if auth_required and self.auth_token:
            payload["auth"] = self.auth_token
        
        try:
            r = requests.post(self.url, json=payload, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"API call failed: {method} - {str(e)}")
            return {"error": str(e)}

# Initialize Zabbix API client
zabbix = ZabbixAPI()

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "zabbix_connected": zabbix.auth_token is not None
    }

@app.get("/hosts")
def get_hosts(status: Optional[int] = None, limit: int = 100):
    """
    Get monitored hosts
    
    Args:
        status: Filter by status (0=monitored, 1=unmonitored)
        limit: Max results (default 100)
    """
    params = {
        "output": ["hostid", "host", "name", "status"],
        "limit": limit
    }
    
    if status is not None:
        params["filter"] = {"status": str(status)}
    
    result = zabbix.call_api("host.get", params)
    
    if "result" in result:
        hosts = result["result"]
        # Format for readability
        return {
            "total": len(hosts),
            "hosts": [
                {
                    "id": h["hostid"],
                    "hostname": h["host"],
                    "display_name": h["name"],
                    "status": "monitored" if h["status"] == "0" else "unmonitored"
                }
                for h in hosts
            ]
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "API error"))

@app.get("/problems")
def get_problems(severity: Optional[int] = None, limit: int = 20):
    """
    Get active problems
    
    Args:
        severity: 0=Not classified, 1=Information, 2=Warning, 3=Average, 4=High, 5=Disaster
        limit: Max results (default 20)
    """
    params = {
        "output": "extend",
        "sortfield": ["eventid"],
        "sortorder": "DESC",
        "limit": limit,
        "recent": "true"
    }
    
    if severity is not None:
        params["severities"] = [severity]
    
    result = zabbix.call_api("problem.get", params)
    
    if "result" in result:
        problems = result["result"]
        severity_map = {
            "0": "Not classified",
            "1": "Information",
            "2": "Warning",
            "3": "Average",
            "4": "High",
            "5": "Disaster"
        }
        
        return {
            "total": len(problems),
            "problems": [
                {
                    "id": p["eventid"],
                    "name": p.get("name", "N/A"),
                    "severity": severity_map.get(p.get("severity", "0"), "Unknown"),
                    "time": p.get("clock", "0"),
               "acknowledged": p.get("acknowledged", "0") == "1"
                }
                for p in problems
            ]
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "API error"))

@app.get("/host/{hostid}/items")
def get_host_items(hostid: str, search: Optional[str] = None, limit: int = 50):
    """
    Get items for a specific host
    
    Args:
        hostid: Host ID
        search: Search in item name/key
        limit: Max results (default 50)
    """
    params = {
        "output": ["itemid", "name", "key_", "lastvalue", "units"],
        "hostids": hostid,
        "limit": limit
    }
    
    if search:
        params["search"] = {"name": search}
    
    result = zabbix.call_api("item.get", params)
    
    if "result" in result:
        return {
            "total": len(result["result"]),
            "items": result["result"]
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "API error"))

@app.get("/triggers")
def get_triggers(priority: Optional[int] = None, limit: int = 50):
    """
    Get triggers
    
    Args:
        priority: 0-5 (same as severity)
        limit: Max results
    """
    params = {
        "output": "extend",
        "sortfield": ["priority"],
        "sortorder": "DESC",
        "limit": limit
    }
    
    if priority is not None:
        params["min_severity"] = priority
    
    result = zabbix.call_api("trigger.get", params)
    
    if "result" in result:
        return {
            "total": len(result["result"]),
            "triggers": result["result"]
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "API error"))

@app.get("/")
def root():
    """API info"""
    return {
        "name": "Zabbix API Connector",
        "version": "1.0.0",
        "endpoints": [
            "/health - Health check",
            "/hosts - Get monitored hosts",
            "/problems - Get active problems",
            "/host/{hostid}/items - Get host items",
            "/triggers - Get triggers"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

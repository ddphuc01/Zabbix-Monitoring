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
        
        # Zabbix 7.4+ uses Authorization header instead of "auth" in payload
        headers = {"Content-Type": "application/json"}
        if auth_required and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            r = requests.post(self.url, json=payload, headers=headers, timeout=10)
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
    Get active problems with host information
    
    Args:
        severity: 0=Not classified, 1=Information, 2=Warning, 3=Average, 4=High, 5=Disaster
        limit: Max results (default 20)
    """
    params = {
        "output": "extend",
        "sortfield": ["eventid"],
        "sortorder": "DESC",
        "limit": limit,
        "recent": True
    }
    
    if severity is not None:
        params["severities"] = [severity]
    
    result = zabbix.call_api("problem.get", params)
    
    if "result" not in result:
        raise HTTPException(status_code=500, detail=result.get("error", "API error"))
    
    problems = result["result"]
    severity_map = {
        "0": "Not classified",
        "1": "Information",
        "2": "Warning",
        "3": "Average",
        "4": "High",
        "5": "Disaster"
    }
    
    # Get trigger IDs from problems to fetch host information
    trigger_ids = [p.get("objectid") for p in problems if p.get("objectid")]
    
    # Fetch host info via triggers if we have trigger IDs
    host_map = {}
    if trigger_ids:
        trigger_result = zabbix.call_api("trigger.get", {
            "triggerids": trigger_ids,
            "selectHosts": ["hostid", "host", "name"],
            "output": ["triggerid"]
        })
        
        if "result" in trigger_result:
            for trigger in trigger_result["result"]:
                trigger_id = trigger.get("triggerid")
                hosts = trigger.get("hosts", [])
                if hosts and trigger_id:
                    host_map[trigger_id] = hosts[0].get("name", "Unknown")
    
    # Format timestamps to readable date-time
    from datetime import datetime
    
    return {
        "total": len(problems),
        "problems": [
            {
                "id": p["eventid"],
                "name": p.get("name", "N/A"),
                "severity": severity_map.get(p.get("severity", "0"), "Unknown"),
                "time": datetime.fromtimestamp(int(p.get("clock", "0"))).strftime("%Y-%m-%d %H:%M:%S"),
                "acknowledged": p.get("acknowledged", "0") == "1",
                "host": host_map.get(p.get("objectid"), "Unknown")
            }
            for p in problems
        ]
    }

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

@app.get("/metrics")
def get_metrics(hostid: Optional[str] = None, search: Optional[str] = None, limit: int = 50):
    """
    Get all items/metrics with latest values
    
    Args:
        hostid: Filter by host ID (optional)
        search: Search in item name (optional)
        limit: Max results (default 50)
    """
    params = {
        "output": ["itemid", "name", "key_", "lastvalue", "units", "lastclock"],
        "selectHosts": ["hostid", "host", "name"],
        "monitored": True,
        "limit": limit,
        "sortfield": "name"
    }
    
    if hostid:
        params["hostids"] = hostid
    
    if search:
        params["search"] = {"name": search}
    
    result = zabbix.call_api("item.get", params)
    
    if "result" in result:
        items = result["result"]
        return {
            "total": len(items),
            "metrics": [
                {
                    "id": item["itemid"],
                    "name": item.get("name", "N/A"),
                    "key": item.get("key_", "N/A"),
                    "value": item.get("lastvalue", "N/A"),
                    "units": item.get("units", ""),
                    "updated": item.get("lastclock", "0"),
                    "host": item["hosts"][0]["name"] if item.get("hosts") else "Unknown"
                }
                for item in items
            ]
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "API error"))

@app.get("/metrics/search")
def search_metrics(keyword: str, limit: int = 50):
    """
    Search metrics by keyword across all hosts
    
    Args:
        keyword: Keyword to search (e.g., 'cpu', 'memory', 'disk')
        limit: Max results (default 50)
    """
    params = {
        "output": ["itemid", "name", "key_", "lastvalue", "units"],
        "selectHosts": ["hostid", "host", "name"],
        "search": {"name": keyword},
        "searchWildcardsEnabled": True,
        "monitored": True,
        "limit": limit
    }
    
    result = zabbix.call_api("item.get", params)
    
    if "result" in result:
        items = result["result"]
        return {
            "keyword": keyword,
            "total": len(items),
            "metrics": [
                {
                    "id": item["itemid"],
                    "name": item.get("name", "N/A"),
                    "key": item.get("key_", "N/A"),
                    "value": item.get("lastvalue", "N/A"),
                    "units": item.get("units", ""),
                    "host": item["hosts"][0]["name"] if item.get("hosts") else "Unknown"
                }
                for item in items
            ]
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "API error"))

@app.get("/hosts/{hostid}/status")
def get_host_status(hostid: str):
    """
    Get comprehensive host health status
    
    Args:
        hostid: Host ID
    """
    # Get host info
    host_result = zabbix.call_api("host.get", {
        "hostids": hostid,
        "output": ["hostid", "host", "name", "status"],
        "selectInterfaces": ["ip"]
    })
    
    if "result" not in host_result or not host_result["result"]:
        raise HTTPException(status_code=404, detail="Host not found")
    
    host = host_result["result"][0]
    
    # Get active problems for this host
    problems_result = zabbix.call_api("problem.get", {
        "hostids": hostid,
        "output": "extend",
        "recent": True,
        "limit": 10
    })
    
    problems = problems_result.get("result", [])
    
    # Get key metrics (CPU, Memory, Disk, etc.)
    metrics_result = zabbix.call_api("item.get", {
        "hostids": hostid,
        "output": ["name", "key_", "lastvalue", "units"],
        "search": {
            "key_": "system."
        },
        "searchWildcardsEnabled": True,
        "monitored": True,
        "limit": 20
    })
    
    metrics = metrics_result.get("result", [])
    
    return {
        "host": {
            "id": host["hostid"],
            "hostname": host["host"],
            "display_name": host["name"],
            "status": "monitored" if host["status"] == "0" else "unmonitored",
            "ip": host["interfaces"][0]["ip"] if host.get("interfaces") else "N/A"
        },
        "health": {
            "active_problems": len(problems),
            "status": "healthy" if len(problems) == 0 else "warning" if len(problems) < 5 else "critical"
        },
        "problems": [
            {
                "id": p["eventid"],
                "name": p.get("name", "N/A"),
                "severity": p.get("severity", "0")
            }
            for p in problems[:5]  # Top 5 problems
        ],
        "key_metrics": [
            {
                "name": m.get("name", "N/A"),
                "value": f"{m.get('lastvalue', 'N/A')} {m.get('units', '')}"
            }
            for m in metrics[:10]  # Top 10 metrics
        ]
    }

@app.get("/host/{hostid}/history")
def get_metric_history(hostid: str, itemid: str, time_from: Optional[int] = None, limit: int = 100):
    """
    Get metric history for a specific item
    
    Args:
        hostid: Host ID
        itemid: Item ID
        time_from: Unix timestamp to start from (optional, defaults to 1 hour ago)
        limit: Max results (default 100)
    """
    import time
    
    if not time_from:
        time_from = int(time.time()) - 3600  # Last hour
    
    # First, get item info to determine value type
    item_result = zabbix.call_api("item.get", {
        "itemids": itemid,
        "hostids": hostid,
        "output": ["name", "value_type"]
    })
    
    if "result" not in item_result or not item_result["result"]:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item = item_result["result"][0]
    value_type = int(item.get("value_type", 0))
    
    # Get history
    history_result = zabbix.call_api("history.get", {
        "itemids": itemid,
        "time_from": time_from,
        "output": "extend",
        "sortfield": "clock",
        "sortorder": "DESC",
        "limit": limit,
        "history": value_type
    })
    
    if "result" in history_result:
        history = history_result["result"]
        return {
            "item_name": item.get("name", "N/A"),
            "total": len(history),
            "time_from": time_from,
            "history": [
                {
                    "timestamp": h.get("clock", "0"),
                    "value": h.get("value", "N/A")
                }
                for h in history
            ]
        }
    else:
        raise HTTPException(status_code=500, detail=history_result.get("error", "API error"))

@app.get("/")
def root():
    """API info"""
    return {
        "name": "Zabbix API Connector",
        "version": "1.1.0",
        "endpoints": [
            "/health - Health check",
            "/hosts - Get monitored hosts",
            "/problems - Get active problems",
            "/host/{hostid}/items - Get host items",
            "/triggers - Get triggers",
            "/metrics - Get all metrics with latest values",
            "/metrics/search?keyword= - Search metrics by keyword",
            "/hosts/{hostid}/status - Get host health summary",
            "/host/{hostid}/history?itemid= - Get metric history"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

#!/usr/bin/env python3
"""
Zabbix AI Webhook Handler - Groq & Ansible Integration
Receives alerts from Zabbix, gathers system metrics via Ansible, and analyzes them using Groq API
"""

import os
import sys
import json
import hashlib
import time
import subprocess
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from groq import Groq
import redis
import requests
from functools import wraps

# Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
CACHE_TTL = int(os.getenv('CACHE_TTL', 7200))  # Increased to 2 hours to reduce duplicate AI calls
MAX_TOKENS = int(os.getenv('MAX_TOKENS', 200))
TEMPERATURE = float(os.getenv('TEMPERATURE', 0.3))

# Alert Filtering Configuration - Skip non-critical repetitive alerts
IGNORED_SERVICES = [
    'AppXSvc',  # AppX Deployment - auto-stops when not needed
    'GoogleUpdater',  # Google auto-updater services  
    'GoogleUpdaterInternal',
    'GoogleUpdaterService',
    'edgeupdate',  # Edge updater
    'gupdate',  # Chrome updater
    'RemoteRegistry',  # Usually disabled for security
]

IGNORED_DISK_PATHS = [
    '/etc/hostname',
    '/etc/hosts',
    '/etc/resolv.conf',
    '/etc/localtime', 
    '/etc/timezone',
    '/run/secrets',  # Docker secrets mount
]

# Ansible Configuration
ANSIBLE_PLAYBOOK_PATH = "/home/phuc/zabbix-monitoring/ansible/playbooks/diagnostics/gather_system_metrics.yml"
ANSIBLE_INVENTORY_PATH = "/home/phuc/zabbix-monitoring/ansible/inventory/hosts"

# Initialize Flask
app = Flask(__name__)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Groq
try:
    groq_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    logger.error(f"❌ Failed to initialize Groq client: {e}")
    groq_client = None

# Initialize Redis
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
        socket_timeout=5
    )
    redis_client.ping()
    logger.info("✅ Connected to Redis")
except Exception as e:
    logger.warning(f"⚠️  Redis connection failed: {e}, caching disabled")
    redis_client = None


def should_skip_alert(alert_data):
    """Check if alert should be skipped to save API quota"""
    trigger = alert_data.get('trigger', '')
    
    # Skip non-critical Windows services that flap frequently
    for service in IGNORED_SERVICES:
        if service.lower() in trigger.lower():
            logger.info(f"⏭️  Skipping non-critical service alert: {service}")
            return True
    
    # Skip Docker mount point disk alerts
    for path in IGNORED_DISK_PATHS:
        if path in trigger:
            logger.info(f"⏭️  Skipping Docker mount disk alert: {path}")
            return True
    
    return False


class CacheManager:
    """Manage Redis caching for AI responses"""
    
    @staticmethod
    def get_cache_key(alert_data):
        """Generate cache key from alert data"""
        key_data = f"{alert_data.get('trigger', '')}{alert_data.get('severity', '')}{alert_data.get('host', '')}"
        return f"groq:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    @staticmethod
    def get(key):
        """Get cached response"""
        if not redis_client:
            return None
        try:
            cached = redis_client.get(key)
            if cached:
                logger.info(f"✅ Cache HIT: {key[:16]}...")
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None
    
    @staticmethod
    def set(key, value, ttl=CACHE_TTL):
        """Cache response"""
        if not redis_client:
            return
        try:
            redis_client.setex(key, ttl, json.dumps(value))
            logger.info(f"✅ Cached: {key[:16]}... (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Cache set error: {e}")

class AnsibleExecutor:
    """Execute Ansible playbooks via REST API on host machine"""
    
    # API Configuration - Points to Ansible REST API service running on host
    # host.docker.internal resolves to host machine IP from within container
    ANSIBLE_API_URL = os.getenv('ANSIBLE_API_URL', 'http://host.docker.internal:5001')
    API_TIMEOUT = int(os.getenv('ANSIBLE_API_TIMEOUT', 90))

    @staticmethod
    def run_diagnostics(hostname):
        """Run diagnostics playbook via REST API"""
        try:
            api_endpoint = f"{AnsibleExecutor.ANSIBLE_API_URL}/api/v1/playbook/run"
            
            payload = {
                "playbook": "gather_system_metrics",
                "target_host": hostname,
                "extra_vars": {}
            }
            
            logger.info(f"🚀 Calling Ansible API for {hostname}...")
            logger.info(f"   Endpoint: {api_endpoint}")
            
            response = requests.post(
                api_endpoint,
                json=payload,
                timeout=AnsibleExecutor.API_TIMEOUT
            )
            
            if response.status_code != 200:
                logger.error(f"❌ API returned status {response.status_code}: {response.text}")
                return None
            
            response_data = response.json()
            
            # Check execution status
            if response_data.get('status') != 'success':
                error_msg = response_data.get('error', 'Unknown error')
                logger.error(f"❌ Ansible execution failed: {error_msg}")
                return None
            
            # Extract result data
            result_data = response_data.get('result', {})
            logger.info(f"✅ Received diagnostics data from API")
            
            return result_data
            
        except requests.exceptions.Timeout:
            logger.error(f"⏱️  API timeout after {AnsibleExecutor.API_TIMEOUT}s")
            return None
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Cannot connect to Ansible API: {e}")
            logger.error(f"   Make sure API service is running on {AnsibleExecutor.ANSIBLE_API_URL}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ansible API error: {e}")
            return None


class GroqAnalyzer:
    """Analyze Zabbix alerts using Groq API"""
    
    SYSTEM_PROMPT = """Ban la System Administrator phan tich Zabbix alerts.

INPUT: JSON voi alert_type, hostname, current_value, threshold, ansible_output, service_info

NHIEM VU:
1. Doc ansible_output (top, ps, df, free) de tim nguyen nhan
2. Phan tich theo alert_type: CPU/MEMORY/DISK/NETWORK/SERVICE
3. Dua khuyen nghi hanh dong cu the

OUTPUT FORMAT (150-200 words, Tieng Viet, dung emoji):
- Severity icon + Alert type + hostname
- Tinh trang hien tai vs threshold
- Nguyen nhan chinh
- Khuyen nghi cu the (commands neu can)
- Urgency level

ALERT TYPES:

CPU: Tim top 3 process tu ps aux, so voi baseline, phan biet spike vs trend

MEMORY: Check Used/Available, top RAM processes, swap usage (>50% = nguy hiem), detect memory leak

DISK: Partition nao full, top directories chiem space, check logs/cache/temp, inode usage

NETWORK: Connection count, states (ESTABLISHED/TIME_WAIT/SYN_RECV), port nao traffic cao

SERVICE: Service name, tai sao stop (crashed/disabled/manual), anh huong gi, cach start
  - Critical (DB, Web): Start ngay
  - System services: Co the doi
  - Optional (RGB, bloatware): Ignore

RULES:
- Spike <5min: "Monitor them"
- Trend >10min: "Action ngay"
- Production: Recommend maintenance window
- Staging/Testing: Restart ngay OK


### INPUT DATA FORMAT (từ Ansible)
Bạn sẽ nhận:
{
  "alert_type": "CPU|MEMORY|DISK|NETWORK",
  "hostname": "web-server-01",
  "current_value": 85,
  "threshold": 80,
  "timestamp": "2024-01-15 14:30:00",
  "ansible_output": {
    "top": "...",          // top -b -n 1 output
    "ps": "...",           // ps aux output
    "df": "...",           // df -h output
    "free": "...",         // free -h output
    "netstat": "...",      // netstat -an output (nếu có)
  },
  "service_info": {
    "environment": "production|staging|testing",
    "app_type": "web|api|database|cache",
    "expected_load": "normal|high|critical"
  }
}

### ANALYSIS FRAMEWORK

#### 1. ALERT TYPE: CPU
**Phân tích:**
- Kiểm tra top 3 process chiếm CPU cao nhất
- So sánh với baseline bình thường
- Kiểm tra context: spike tạm thời hay trend tăng?

**Output format:**
```
🔴 [CRITICAL/HIGH/MEDIUM] CPU ALERT: {hostname}

📊 Tình trạng: {current_value}% / {threshold}% ngưỡng

⚡ Nguyên nhân chính:
- [Process name] đang chiếm {X}% CPU
- [Mô tả hành động của process]
- [Lý do tại sao nó cao]

✅ Khuyến nghị:
1. [Hành động ngay lập tức - ví dụ: restart service, kill process]
2. [Hành động dài hạn - ví dụ: scale up, optimize query]
3. [Monitoring cần chú ý]

⏱️ Urgency: [Restart now / Monitor 5min / Can wait]
```

#### 2. ALERT TYPE: MEMORY
**Phân tích:**
- Kiểm tra Used vs Available
- Top 3 process sử dụng RAM cao nhất
- Kiểm tra swap usage - nếu cao = vấn đề
- Kiểm tra memory leak pattern

**Output format:**
```
🔴 [CRITICAL/HIGH/MEDIUM] MEMORY ALERT: {hostname}

📊 Tình trạng: {current_value}% / {threshold}%

💾 Chi tiết:
- Used: {X} GB / Total: {Y} GB
- Swap: {swap_used}% (⚠️ nếu > 50%)
- Available: {Z} GB

⚡ Nguyên nhân chính:
- [Process/Service] sử dụng {X} GB
- [Mô tả vấn đề]

✅ Khuyến nghị:
1. [Immediate action]
2. [Follow-up action]
3. [Prevention measure]

⏱️ Urgency: [Restart now / Monitor / Schedule maintenance]
```

#### 3. ALERT TYPE: DISK
**Phân tích:**
- Kiểm tra partition nào full
- Top 3 thư mục chiếm space lớn nhất
- Kiểm tra logs, cache, temp directories
- Inode usage (nếu có) - nếu 100% = không ghi file được

**Output format:**
```
🔴 [CRITICAL/HIGH/MEDIUM] DISK ALERT: {hostname}

📊 Tình trạng: {current_value}% / {threshold}%

💿 Chi tiết:
- Partition: {partition_name}
- Used: {X} GB / Total: {Y} GB
- Inode: {inode_percent}% ⚠️

⚡ Nguyên nhân chính:
- Thư mục {path} chiếm {X} GB
- [Mô tả: logs quá cũ, cache không clear, data không rotate]

✅ Khuyến nghị:
1. Xóa {path}/{file_pattern} (hoặc rotate logs)
2. Kiểm tra {specific_service} configuration
3. Thiết lập log rotation/cleanup policy

⏱️ Urgency: [Delete now / Schedule cleanup / Monitor]
```

#### 4. ALERT TYPE: NETWORK
**Phân tích:**
- Kiểm tra connection count
- Phát hiện connection state bất thường (ESTABLISHED, TIME_WAIT, SYN_RECV)
- Port nào có traffic cao
- Kiểm tra dropped packets (nếu có)

**Output format:**
```
🔴 [CRITICAL/HIGH/MEDIUM] NETWORK ALERT: {hostname}

📊 Tình trạng: {current_value}

🌐 Chi tiết:
- Tổng connection: {total}
- ESTABLISHED: {established}
- TIME_WAIT: {time_wait}
- SYN_RECV: {syn_recv}

⚡ Nguyên nhân chính:
- Port {port} có {X} connection
- [Mô tả: client không close connection, slow query, DDoS signal]

✅ Khuyến nghị:
1. Kiểm tra service lắng nghe port {port}
2. Tăng connection limit nếu cần
3. Thêm firewall rules nếu nhận DDoS

⏱️ Urgency: [Check immediately / Increase limits / Monitor]
```

#### 5. ALERT TYPE: SERVICE (Windows/Linux Service Monitoring)
**Phân tích:**
- Service name và trạng thái (Running/Stopped)
- Kiểm tra lý do service stop (auto-start disabled, crashed, manual stop)
- Ảnh hưởng đến hệ thống
- Service phụ thuộc (dependent services)

**Output format:**
```
🔴 [CRITICAL/HIGH/MEDIUM] SERVICE ALERT: {hostname}

📊 Tình trạng: Dịch vụ "{service_name}" đang stopped

⚡ Nguyên nhân:
- Service bị stop (manual hoặc crashed)
- [Nếu critical service] Có thể ảnh hưởng đến: {dependent_features}

✅ Khuyến nghị:
1. **Start lại service:** `Start-Service "{service_name}"` (Windows) hoặc `systemctl start {service_name}` (Linux)
2. Kiểm tra startup type: Nên đặt 'Automatic' nếu service này quan trọng
3. [Nếu service liên tục stop] Kiểm tra Event Logs/journalctl để tìm lỗi

⏱️ Urgency: [Start now / Monitor / Can ignore if non-critical]
```

**Service Classification:**
- **Critical Services:** Database, Web Server, Application Server → Start ngay
- **System Services:** Windows Update, Diagnostic services → Có thể đợi
- **Optional Services:** RGB lighting, manufacturer bloatware → Có thể ignore

### SPECIAL CASES & RULES

**Rule 1: Spike vs Trend**
- Spike tạm thời (1-2 phút): "Monitor, có thể là traffic bình thường"
- Trend tăng (> 10 phút): "Cần action ngay"

**Rule 2: Correlation (nếu có nhiều alert cùng lúc)**
- CPU cao + Memory cao + Disk I/O cao = Process quay vòng lặp / query kém
- CPU cao + Network cao = Có thể DDoS hoặc malware
- Memory cao + Disk I/O cao = Swap thrashing - rất nguy hiểm

**Rule 3: Service-aware**
- nginx/httpd CPU cao: Check slow queries, client connections
- MySQL/PostgreSQL high memory: Nếu < 10min = query đột ngột, > 30min = memory leak
- Redis memory: Clear expired keys, check LRU policy
- Docker/Kubernetes: Kiểm tra container restart loop

**Rule 4: Environment-aware**
- Production: Severity cao hơn, recommend restart vào maintenance window
- Staging: Có thể restart ngay
- Testing: Có thể tạm thời ignore

**Rule 5: False Positive Detection**
- Nếu spike nhỏ (< 5% vượt threshold): "Có thể false positive, monitor thêm 5 phút"
- Nếu baseline data không rõ: "Cần baseline hiểu rõ để xác định chính xác"

### OUTPUT CONSTRAINTS
- **Length**: 150-200 words (phù hợp Telegram message)
- **Language**: Tiếng Việt, chuyên nghiệp nhưng dễ hiểu
- **Tone**: Cấp báo nhưng không alarming
- **Format**: Markdown (✅, ⚠️, 🔴, ⏱️ icons)
- **Actionable**: User phải biết làm gì trong 30 giây

### TONE GUIDELINES
- Tin xấu ❌: Không dùng "server đang chết", dùng "cần action trong 5 phút"
- Cấp độ: "Ngay lập tức" > "Trong 5 phút" > "Trong 1 giờ" > "Schedule maintenance"
- Ích lợi: Luôn nêu lợi ích của action: "Restart sẽ clear cache, process sẽ chạy lại = system bình thường"

### EXAMPLES

**Example 1 - CPU Alert**
Input: CPU 92%, nginx process 45%, apache 20%
Output:
```
🔴 [HIGH] CPU ALERT: web-server-01

📊 Tình trạng: 92% / 80%

⚡ Nguyên nhân: nginx đang xử lý spike traffic (45% CPU)
- Có ~500 connection từ client
- Likely: API endpoint chậm, client đợi response

✅ Khuyến nghị:
1. Tăng worker processes của nginx từ 4 → 8 (tạm thời)
2. Check slow query log nếu backend là PHP/Python
3. Monitor 10 phút tiếp theo - nếu traffic hạ = OK, không cần restart

⏱️ Urgency: Monitor 10 phút / Tối ưu configuration
```

**Example 2 - Disk Alert**
Input: Disk 95%, /var/log chiếm 500GB
Output:
```
🔴 [CRITICAL] DISK ALERT: app-server-01

📊 Tình trạng: 95% / 80%

💿 Chi tiết: /var/log = 500 GB (nguyên nhân chính!)
- Logs cũ hơn 30 ngày không bị rotate
- Có multiple large log files từ nginx, syslog, app logs

✅ Khuyến nghị:
1. **Ngay lập tức**: Chạy log rotation
   `find /var/log -name "*.log.*" -mtime +30 | xargs rm`
2. Kiểm tra logrotate config - ensure weekly rotation
3. Thiết lập max log size = 100MB để auto rotate

⏱️ Urgency: Delete now (an toàn, logs cũ có thể xóa)
```
"""

    @staticmethod
    def determine_alert_type(trigger_name):
        """Determine alert type from trigger name"""
        trigger_upper = trigger_name.upper()
        if 'CPU' in trigger_upper or 'LOAD' in trigger_upper:
            return 'CPU'
        elif 'MEMORY' in trigger_upper or 'SWAP' in trigger_upper or 'RAM' in trigger_upper:
            return 'MEMORY'
        elif 'DISK' in trigger_upper or 'SPACE' in trigger_upper or 'VOLUME' in trigger_upper:
            return 'DISK'
        elif 'NETWORK' in trigger_upper or 'INTERFACE' in trigger_upper or 'BANDWIDTH' in trigger_upper:
            return 'NETWORK'
        elif 'SERVICE' in trigger_upper or 'NOT RUNNING' in trigger_upper or 'IS NOT RUNNING' in trigger_upper or 'STOPPED' in trigger_upper:
            return 'SERVICE'
        return 'UNKNOWN'
    
    @staticmethod
    def extract_service_info(hostname, alert_data):
        """Extract service context from hostname and alert data"""
        # Default values
        service_info = {
            "environment": "production",
            "app_type": "web",
            "expected_load": "normal"
        }
        
        # Try to determine environment from hostname
        hostname_lower = hostname.lower()
        if 'prod' in hostname_lower or 'prd' in hostname_lower:
            service_info['environment'] = 'production'
        elif 'staging' in hostname_lower or 'stg' in hostname_lower:
            service_info['environment'] = 'staging'
        elif 'test' in hostname_lower or 'dev' in hostname_lower:
            service_info['environment'] = 'testing'
        
        # Try to determine app type from hostname
        if 'web' in hostname_lower or 'nginx' in hostname_lower or 'apache' in hostname_lower:
            service_info['app_type'] = 'web'
        elif 'db' in hostname_lower or 'mysql' in hostname_lower or 'postgres' in hostname_lower:
            service_info['app_type'] = 'database'
        elif 'api' in hostname_lower:
            service_info['app_type'] = 'api'
        elif 'cache' in hostname_lower or 'redis' in hostname_lower:
            service_info['app_type'] = 'cache'
        
        # Determine expected load based on severity
        severity = str(alert_data.get('severity', '')).lower()
        if 'critical' in severity or 'disaster' in severity:
            service_info['expected_load'] = 'critical'
        elif 'high' in severity or 'warning' in severity:
            service_info['expected_load'] = 'high'
        else:
            service_info['expected_load'] = 'normal'
        
        return service_info

    @staticmethod
    def analyze(alert_data, ansible_data=None):
        """Analyze alert with Groq"""
        if not groq_client:
             return {"error": "Groq client not initialized"}

        try:
            alert_type = GroqAnalyzer.determine_alert_type(alert_data.get('trigger', ''))
            hostname = alert_data.get('host', 'Unknown')
            
            # Extract service context
            service_info = GroqAnalyzer.extract_service_info(hostname, alert_data)
            
            # Prepare Ansible output - handle both dict and string
            if isinstance(ansible_data, dict):
                ansible_output = ansible_data
            elif ansible_data:
                ansible_output = {"raw": ansible_data}
            else:
                ansible_output = "No Ansible data available (Execution failed or not configured)"
            
            # Construct user message
            user_content = {
                "alert_type": alert_type,
                "hostname": hostname,
                "current_value": alert_data.get('value', 'N/A'),
                "threshold": alert_data.get('threshold', '80'),  # Default threshold
                "timestamp": alert_data.get('time', datetime.utcnow().isoformat()),
                "ansible_output": ansible_output,
                "service_info": service_info
            }
            
            logger.info(f"🤖 Calling Groq API for {alert_type} alert on {hostname} (env: {service_info['environment']})...")
            start_time = time.time()
            
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": GroqAnalyzer.SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": json.dumps(user_content)
                    }
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                top_p=0.9,
                frequency_penalty=0.5
            )
            
            analysis_text = completion.choices[0].message.content
            elapsed = time.time() - start_time
            logger.info(f"✅ Groq responded in {elapsed:.2f}s")
            
            return {
                "analysis": analysis_text,
                "model": "llama-3.3-70b-versatile",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Groq API error: {e}")
            return {
                "error": str(e),
                "analysis": "AI Analysis Failed due to API Error."
            }


def require_api_key(f):
    """Decorator to check API key"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not GROQ_API_KEY:
            return jsonify({
                "error": "GROQ_API_KEY not configured",
                "status": "error"
            }), 500
        return f(*args, **kwargs)
    return decorated


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "zabbix-ai-webhook-groq",
        "timestamp": datetime.utcnow().isoformat(),
        "groq_configured": bool(GROQ_API_KEY),
        "redis_connected": redis_client is not None
    }), 200


@app.route('/webhook', methods=['POST'])
@require_api_key
def webhook():
    """Zabbix webhook endpoint"""
    try:
        data = request.get_json()
        
        # Standardize Zabbix Data
        alert_data = {
            'trigger': data.get('trigger_name', data.get('TRIGGER.NAME', 'Unknown')),
            'host': data.get('host_name', data.get('HOST.NAME', 'Unknown')),
            'severity': data.get('trigger_severity', data.get('TRIGGER.SEVERITY', 'Unknown')),
            'value': data.get('trigger_value', data.get('ITEM.VALUE', 'N/A')),
            'time': data.get('event_time', data.get('EVENT.TIME', 'N/A')),
            'description': data.get('trigger_description', data.get('TRIGGER.DESCRIPTION', '')),
            'event_id': data.get('event_id', data.get('EVENT.ID', ''))
        }
        
        logger.info(f"📨 Received alert: {alert_data['trigger']} for {alert_data['host']}")
        
        # Skip non-critical repetitive alerts to save quota
        if should_skip_alert(alert_data):
            logger.info(f"⏭️  Alert skipped (filtered): {alert_data['trigger']}")
            # Still send to Telegram but without diagnostics
            simple_message = f"⚪ **{alert_data['trigger']}**\n"
            simple_message += f"🖥️ Host: `{alert_data['host']}`\n"
            simple_message += f"⏰ Time: {alert_data['time']}\n"
            simple_message += f"📊 Severity: {alert_data['severity']}\n\n"
            simple_message += "_ℹ️ Alert filtered (non-critical service)._"
            send_telegram_alert(simple_message, alert_data=alert_data, enable_ai_button=False)
            return "Alert filtered", 200

        # Execute Ansible diagnostics to get system metrics
        ansible_data = AnsibleExecutor.run_diagnostics(alert_data['host'])
        
        # Format message with metadata and diagnostics
        alert_name = alert_data.get('trigger', 'Alert')
        hostname = alert_data.get('host', 'Unknown')
        severity = alert_data.get('severity', 'Unknown')
        event_time = alert_data.get('time', 'N/A')
        event_id = alert_data.get('event_id', '')
        
        # Severity emoji mapping
        severity_emojis = {
            'Disaster': '🔴',
            'High': '🟠',
            'Average': '🟡',
            'Warning': '🟢',
            'Information': '🔵'
        }
        severity_emoji = severity_emojis.get(severity, '⚪')
        
        # Build header with metadata
        # Format datetime properly: dd/mm/yyyy HH:MM:SS
        from datetime import datetime
        try:
            # Parse and reformat time if it's in HH:MM:SS format
            if ':' in event_time and len(event_time.split(':')) == 3:
                now = datetime.now()
                formatted_time = now.strftime('%d/%m/%Y') + ' ' + event_time
            else:
                formatted_time = event_time
        except:
            formatted_time = event_time
        
        header = f"{severity_emoji} **Vấn đề: {alert_name}**\n"
        header += f"🖥️ Máy chủ: `{hostname}`\n"
        header += f"⏰ Thời gian: {formatted_time}\n"
        header += f"📊 Mức độ: {severity}"
        if event_id:
            header += f" | ID: `{event_id}`"
        header += "\n\n"
        
        # Add Ansible diagnostics if available
        if ansible_data and isinstance(ansible_data, dict):
            # Determine alert type from trigger name
            alert_name_lower = alert_name.lower()
            is_cpu_alert = 'cpu' in alert_name_lower or 'load' in alert_name_lower
            is_memory_alert = 'memory' in alert_name_lower or 'ram' in alert_name_lower or 'swap' in alert_name_lower
            is_disk_alert = 'disk' in alert_name_lower or 'space' in alert_name_lower or 'filesystem' in alert_name_lower
            
            header += "**📈 Thông Số Hệ Thống:**\n"
            
            metrics_found = False
            
            # NEW FORMAT: Check for structured metrics dict
            if 'metrics' in ansible_data:
                metrics = ansible_data['metrics']
                
                # ==================== CPU ALERT ====================
                if is_cpu_alert:
                    # Show CPU usage line (parse and simplify)
                    cpu_data = metrics.get('cpu', '')
                    if cpu_data:
                        for line in cpu_data.split('\n'):
                            if '%Cpu(s):' in line:
                                # Parse: %Cpu(s): 95.5 us,  4.5 sy,  0.0 ni,  0.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
                                # Extract key values
                                try:
                                    parts = line.split(',')
                                    us = float(parts[0].split(':')[1].strip().replace('us', '').strip())  # user
                                    sy = float(parts[1].strip().replace('sy', '').strip())  # system
                                    id_val = float(parts[3].strip().replace('id', '').strip())  # idle
                                    
                                    total_used = 100.0 - id_val
                                    
                                    # Simplified format
                                    header += f"• 🔥 **CPU Usage:** {total_used:.1f}% sử dụng (User: {us:.1f}%, System: {sy:.1f}% | Idle: {id_val:.1f}%)\n"
                                except:
                                    # Fallback to raw format if parsing fails
                                    header += f"• 🔥 **CPU Usage:** {line.strip()}\n"
                                
                                metrics_found = True
                                break
                    
                    # Show TOP 10 CPU PROCESSES
                    proc_data = metrics.get('processes', '')
                    if proc_data:
                        lines = proc_data.strip().split('\n')
                        header += f"• ⚡ **Top 10 CPU Processes:**\n"
                        
                        count = 0
                        for line in lines[1:]:  # Skip header
                            if count >= 10:
                                break
                            parts = line.split()
                            if len(parts) >= 11:
                                user = parts[0]
                                cpu_pct = parts[2]
                                mem_pct = parts[3]
                                cmd = ' '.join(parts[10:])[:40]  # Truncate long commands
                                
                                # Format nicely
                                header += f"   `{count+1:2d}.` **{cpu_pct:>5s}%** CPU | {mem_pct:>4s}% RAM | `{cmd}`\n"
                                count += 1
                                metrics_found = True
                
                # ==================== MEMORY ALERT ====================
                elif is_memory_alert:
                    # Show Memory usage line
                    mem_data = metrics.get('memory', '')
                    if mem_data:
                        for line in mem_data.split('\n'):
                            if 'Mem:' in line:
                                header += f"• 💾 **RAM Usage:** {line.strip()}\n"
                                metrics_found = True
                                break
                    
                    # Show TOP 10 MEMORY PROCESSES
                    proc_data = metrics.get('processes', '')
                    if proc_data:
                        # Need to re-sort by memory (column 4)
                        lines = proc_data.strip().split('\n')
                        header += f"• ⚡ **Top 10 RAM Processes:**\n"
                        
                        # Parse and sort by memory
                        process_list = []
                        for line in lines[1:]:  # Skip header
                            parts = line.split()
                            if len(parts) >= 11:
                                try:
                                    mem_pct = float(parts[3])
                                    cpu_pct = parts[2]
                                    cmd = ' '.join(parts[10:])[:40]
                                    process_list.append((mem_pct, cpu_pct, cmd))
                                except ValueError:
                                    continue
                        
                        # Sort by memory descending
                        process_list.sort(reverse=True, key=lambda x: x[0])
                        
                        for i, (mem_pct, cpu_pct, cmd) in enumerate(process_list[:10]):
                            header += f"   `{i+1:2d}.` **{mem_pct:>5.1f}%** RAM | {cpu_pct:>5s}% CPU | `{cmd}`\n"
                            metrics_found = True
                
                # ==================== DISK ALERT ====================
                elif is_disk_alert:
                    # Show ALL disk partitions sorted by usage
                    disk_data = metrics.get('disk', '')
                    if disk_data:
                        header += f"• 💿 **Disk Usage:**\n"
                        
                        # Parse disk lines and sort by usage%
                        disk_list = []
                        for line in disk_data.split('\n'):
                            if '/dev/' in line and '%' in line:
                                parts = line.split()
                                if len(parts) >= 6:
                                    filesystem = parts[0]
                                    size = parts[1]
                                    used = parts[2]
                                    avail = parts[3]
                                    use_pct = parts[4].rstrip('%')
                                    mount = parts[5]
                                    
                                    try:
                                        use_pct_int = int(use_pct)
                                        disk_list.append((use_pct_int, filesystem, size, used, avail, use_pct, mount))
                                    except ValueError:
                                        continue
                        
                        # Sort by usage descending
                        disk_list.sort(reverse=True, key=lambda x: x[0])
                        
                        for use_pct_int, filesystem, size, used, avail, use_pct, mount in disk_list[:5]:
                            header += f"   • `{filesystem}` **{use_pct}%** used ({used}/{size}) on `{mount}`\n"
                            metrics_found = True
                
                # ==================== GENERIC ALERT (show summary) ====================
                else:
                    # Show brief summary of all metrics
                    cpu_data = metrics.get('cpu', '')
                    if cpu_data:
                        for line in cpu_data.split('\n'):
                            if '%Cpu(s):' in line:
                                header += f"• 🔥 CPU: {line.strip()}\n"
                                metrics_found = True
                                break
                    
                    mem_data = metrics.get('memory', '')
                    if mem_data:
                        for line in mem_data.split('\n'):
                            if 'Mem:' in line:
                                header += f"• 💾 RAM: {line.strip()}\n"
                                metrics_found = True
                                break
                    
                    disk_data = metrics.get('disk', '')
                    if disk_data:
                        for line in disk_data.split('\n'):
                            if '/dev/' in line and '%' in line:
                                parts = line.split()
                                if len(parts) >= 5:
                                    header += f"• 💿 Disk: {parts[0]} {parts[4]} used\n"
                                    metrics_found = True
                                    break
                    
                    proc_data = metrics.get('processes', '')
                    if proc_data:
                        lines = proc_data.strip().split('\n')
                        if len(lines) > 1:
                            parts = lines[1].split()
                            if len(parts) >= 11:
                                cpu_pct = parts[2]
                                cmd = ' '.join(parts[10:])[:30]
                                header += f"• ⚡ Top Process: {cmd} ({cpu_pct}%)\n"
                                metrics_found = True
            
            # OLD FORMAT FALLBACK: Try parsing stdout/stderr
            elif 'stdout' in ansible_data or 'stderr' in ansible_data:
                stdout = ansible_data.get('stdout', '')
                stderr = ansible_data.get('stderr', '')
                
                # Try to parse as JSON or plain text (old code path)
                try:
                    if stdout and isinstance(stdout, str):
                        # Try to parse as JSON
                        ansible_json = json.loads(stdout)
                        
                        # Extract from plays -> tasks -> hosts -> msg
                        if 'plays' in ansible_json:
                            for play in ansible_json['plays']:
                                if 'tasks' in play:
                                    for task in play['tasks']:
                                        if 'hosts' in task:
                                            for host_name, host_data in task['hosts'].items():
                                                if 'msg' in host_data and isinstance(host_data['msg'], list):
                                                    # msg is a list with sections
                                                    current_section = None
                                                    for line in host_data['msg']:
                                                        if '=== CPU ===' in line:
                                                            current_section = 'cpu'
                                                        elif '=== MEMORY ===' in line:
                                                            current_section = 'memory'
                                                        elif '=== DISK ===' in line:
                                                            current_section = 'disk'
                                                        elif current_section and line.strip():
                                                            # Extract key metrics
                                                            if current_section == 'cpu' and '%Cpu' in line:
                                                                header += f"• 🔥 CPU: {line.strip()}\n"
                                                                metrics_found = True
                                                            elif current_section == 'memory' and 'Mem:' in line:
                                                                header += f"• 💾 RAM: {line.strip()}\n"
                                                                metrics_found = True
                                                            elif current_section == 'disk' and '/dev/' in line and '%' in line:
                                                                parts = line.split()
                                                                if len(parts) >= 5:
                                                                    header += f"• 💿 Disk: {parts[0]} {parts[4]} used\n"
                                                                    metrics_found = True
                                                                    break
                except (json.JSONDecodeError, Exception) as e:
                    logger.error(f"Error parsing old format Ansible output: {e}")
            
            # If no specific metrics found, show generic message
            if not metrics_found:
                if 'status' in ansible_data and ansible_data.get('status') == 'success':
                    header += f"• ✅ Ansible đã chạy thành công\n"
                    header += f"• 📊 Nhấn 'Phân Tích AI' bên dưới để nhận khuyến nghị chi tiết\n"
                else:
                    header += f"• ✅ Ansible đã chạy thành công\n"
                    header += f"• 📊 Nhấn 'Chạy Chẩn Đoán' để xem chi tiết\n"
            
            header += "\n"
        
        # Add footer note about AI
        header += "_💡 Nhấn 'Phân Tích AI' bên dưới để nhận khuyến nghị chi tiết._"
        
        # Store alert+ansible data in cache for AI button later
        cache_key = f"alert_data:{event_id}"
        if redis_client:
            try:
                full_alert_data = {
                    'alert': alert_data,
                    'ansible': ansible_data
                }
                redis_client.setex(cache_key, 3600, json.dumps(full_alert_data))
                logger.info(f"💾 Cached alert data: {cache_key}")
            except Exception as e:
                logger.error(f"Failed to cache alert data: {e}")
        
        # Send to Telegram with AI analysis button
        send_telegram_alert(header, alert_data=alert_data, enable_ai_button=True)
        
        return "Alert sent (AI on-demand)", 200
        
    except Exception as e:
        logger.error(f"❌ Error in /webhook: {e}")
        return f"❌ AI Analysis Error: {str(e)}", 500


def send_telegram_alert(message, alert_data=None, enable_ai_button=False):
    """Send alert message to Telegram with inline keyboard buttons"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        logger.warning("⚠️ Telegram credentials not configured, skipping notification")
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        
        # Build inline keyboard with action buttons
        keyboard = None
        if alert_data:
            hostname = alert_data.get('host', 'Unknown')
            trigger_name = alert_data.get('trigger', '')
            event_id = alert_data.get('event_id', '')
            
            # Determine alert type for appropriate buttons
            alert_type = GroqAnalyzer.determine_alert_type(trigger_name)
            
            buttons = []
            
            # AI Analysis button (only if enabled)
            if enable_ai_button and event_id:
                buttons.append(
                    [{"text": "🤖 Get AI Analysis", "callback_data": f"ai_analysis:{event_id}"}]
                )
            
            # Service-specific buttons
            if alert_type == 'SERVICE':
                # Extract service name from trigger (e.g., "Service XYZ is not running")
                service_name = trigger_name.split('"')[1] if '"' in trigger_name else 'Unknown'
                buttons.append(
                    [{"text": "🔄 Restart Service", "callback_data": f"restart_service:{hostname}:{service_name}"}]
                )
                buttons.append(
                    [{"text": "📊 Check Status", "callback_data": f"check_service:{hostname}:{service_name}"}]
                )
            else:
                # Generic diagnostic button for other alert types
                buttons.append(
                    [{"text": "🔍 Run Diagnostics", "callback_data": f"diagnostics:{hostname}"}]
                )
            
            # Common buttons for all alerts
            buttons.append([
                {"text": "✅ Acknowledge", "callback_data": f"ack:{event_id}"},
                {"text": "🔕 Ignore", "callback_data": f"ignore:{event_id}"}
            ])
            
            keyboard = {"inline_keyboard": buttons}
        
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        # Add keyboard if available
        if keyboard:
            payload["reply_markup"] = keyboard
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Sent Telegram notification with inline buttons")
            
            # Cache original alert message for "Back to Alert" button
            if redis_client and alert_data and event_id:
                try:
                    response_data = response.json()
                    if response_data.get('ok'):
                        message_id = response_data['result']['message_id']
                        
                        # Store original alert with buttons for restoration
                        original_alert_data = {
                            'message_text': message,
                            'message_id': message_id,
                            'buttons': buttons if keyboard else []
                        }
                        
                        cache_key = f"original_alert:{event_id}"
                        redis_client.setex(cache_key, 3600, json.dumps(original_alert_data))
                        logger.info(f"💾 Cached original alert: {cache_key}")
                except Exception as e:
                    logger.error(f"Failed to cache original alert: {e}")
        else:
            logger.error(f"❌ Failed to send Telegram: {response.text}")
    except Exception as e:
        logger.error(f"❌ Telegram send error: {e}")


if __name__ == '__main__':
    logger.info("🚀 Starting Zabbix AI Webhook Handler (Groq Edition)")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.getenv('DEBUG', 'false').lower() == 'true'
    )

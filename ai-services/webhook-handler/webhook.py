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
CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))
MAX_TOKENS = int(os.getenv('MAX_TOKENS', 200))
TEMPERATURE = float(os.getenv('TEMPERATURE', 0.3))

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
    
    # API Configuration
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
    
    SYSTEM_PROMPT = """Bạn là một System Administrator chuyên gia đang phân tích alert từ hệ thống Zabbix monitoring.
- Đọc dữ liệu thực tế từ Ansible (top, ps, df, free, netstat)
- Xác định nguyên nhân gốc (root cause)
- Đưa ra khuyến nghị hành động cụ thể
- Trả lời bằng Tiếng Việt, ngắn gọn, actionable
- Mục tiêu: Giúp admin nhanh chóng xử lý sự cố

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
        
        # Check cache first
        cache_key = CacheManager.get_cache_key(alert_data)
        cached_result = CacheManager.get(cache_key)
        if cached_result:
            return cached_result['analysis'], 200

        # Execute Ansible diagnostics
        ansible_data = AnsibleExecutor.run_diagnostics(alert_data['host'])
        
        # Analyze with Groq
        result = GroqAnalyzer.analyze(alert_data, ansible_data)
        
        # Cache Result
        if 'error' not in result:
             CacheManager.set(cache_key, result)
        
        # Format message with alert name
        alert_name = alert_data.get('trigger', 'Alert')
        hostname = alert_data.get('host', 'Unknown')
        message_with_header = f"**{alert_name}** on {hostname}\n\n{result['analysis']}"
        
        # Send to Telegram
        send_telegram_alert(message_with_header)
        
        return result['analysis'], 200
        
        return result['analysis'], 200
        
    except Exception as e:
        logger.error(f"❌ Error in /webhook: {e}")
        return f"❌ AI Analysis Error: {str(e)}", 500


def send_telegram_alert(message):
    """Send alert message to Telegram"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        logger.warning("⚠️ Telegram credentials not configured, skipping notification")
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Sent Telegram notification")
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

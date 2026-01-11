#!/usr/bin/env python3
"""
Zabbix AI Webhook Handler - Gemini Integration
Receives alerts from Zabbix and analyzes them using Google Gemini API
"""

import os
import sys
import json
import hashlib
import time
from datetime import datetime
from flask import Flask, request, jsonify
import google.generativeai as genai
import redis
import logging
from functools import wraps

# Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))
MAX_TOKENS = int(os.getenv('MAX_TOKENS', 1000))
TEMPERATURE = float(os.getenv('TEMPERATURE', 0.3))

# Initialize Flask
app = Flask(__name__)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-flash-latest')  # Working model!

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
        key_data = f"{alert_data.get('trigger', '')}{alert_data.get('severity', '')}"
        return f"gemini:{hashlib.md5(key_data.encode()).hexdigest()}"
    
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


class GeminiAnalyzer:
    """Analyze Zabbix alerts using Gemini API"""
    
    SYSTEM_PROMPT = """Bạn là Senior SysAdmin chuyên Zabbix monitoring.

QUAN TRỌNG: 
- Viết TIẾNG VIỆT ngắn gọn, TECHNICAL
- Dùng thuật ngữ kỹ thuật (giữ nguyên tiếng Anh nếu quen thuộc)
- Viết theo BULLET POINTS, KHÔNG phải đoạn văn dài
- Đưa COMMANDS cụ thể, có thể chạy ngay
- Straight to the point - NO fluff

Khi phân tích alert:
1. Tóm tắt vấn đề (1 câu)
2. List nguyên nhân có thể (bullets)
3. Commands để fix (copy-paste được)
4. Cách prevent (bullets ngắn)

Response format JSON (values bằng tiếng Việt):
{
  "summary": "Mô tả ngắn vấn đề - 1 câu",
  "root_cause": "Nguyên nhân:\n- Khả năng 1\n- Khả năng 2\n- Khả năng 3",
  "severity_assessment": "Mức độ (Cao/Trung bình/Thấp) - lý do ngắn",
  "immediate_action": "Các bước fix:\n1. Command cụ thể hoặc hành động\n2. Command kế tiếp\n3. Verify",
  "preventive_measures": "Phòng ngừa:\n- Action 1\n- Action 2",
  "related_metrics": "Metrics cần check:\n- metric1\n- metric2",
  "confidence": 0.0-1.0
}

Example style:
❌ Không viết: "Máy chủ web sản xuất đang chịu tải CPU cực cao có nguy cơ gây ra độ trễ cao và sập dịch vụ"
✅ Viết: "CPU quá cao (98%) - service có thể sập"

❌ Không: "Nguyên nhân gốc rễ có khả năng nhất là một tiến trình ứng dụng bị lỗi"  
✅ Viết: "Nguyên nhân:\n- Process bị leak\n- Traffic spike đột ngột\n- Resource limit thiếu"

❌ Không: "Bạn nên thực hiện các bước sau để khắc phục"
✅ Viết: "Fix ngay:\n1. ssh user@host\n2. top -n 1\n3. kill -9 <PID>"
"""



    
    @staticmethod
    def build_alert_context(alert_data):
        """Build context from alert data"""
        context = f"""
Alert Details:
- Trigger: {alert_data.get('trigger', 'Unknown')}
- Host: {alert_data.get('host', 'Unknown')}
- Severity: {alert_data.get('severity', 'Unknown')}
- Value: {alert_data.get('value', 'N/A')}
- Time: {alert_data.get('time', 'N/A')}

Description: {alert_data.get('description', 'No description')}

Historical Context: {alert_data.get('history', 'No history available')}

Please analyze this alert and provide recommendations.
"""
        return context
    
    @staticmethod
    def analyze(alert_data):
        """Analyze alert with Gemini"""
        try:
            # Build prompt
            user_prompt = GeminiAnalyzer.build_alert_context(alert_data)
            full_prompt = f"{GeminiAnalyzer.SYSTEM_PROMPT}\n\n{user_prompt}"
            
            # Call Gemini API
            logger.info("🤖 Calling Gemini API...")
            start_time = time.time()
            
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                )
            )
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Gemini responded in {elapsed:.2f}s")
            
            # Parse response
            result = GeminiAnalyzer.parse_response(response.text, alert_data)
            result['response_time'] = elapsed
            result['model'] = 'gemini-flash-latest'
            result['timestamp'] = datetime.utcnow().isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Gemini API error: {e}")
            return {
                "error": str(e),
                "summary": "AI analysis failed",
                "root_cause": "Unable to analyze - API error",
                "immediate_action": "Please investigate manually",
                "confidence": 0.0
            }
    
    @staticmethod
    def parse_response(text, alert_data):
        """Parse Gemini response, handle both JSON and text"""
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in text:
                json_start = text.find("```json") + 7
                json_end = text.find("```", json_start)
                json_str = text[json_start:json_end].strip()
                return json.loads(json_str)
            elif "```" in text:
                json_start = text.find("```") + 3
                json_end = text.find("```", json_start)
                json_str = text[json_start:json_end].strip()
                return json.loads(json_str)
            else:
                # Try direct JSON parse
                return json.loads(text)
        except:
            # Fallback: create structured response from text
            return {
                "summary": f"Analysis for {alert_data.get('trigger', 'alert')}",
                "root_cause": text[:200],
                "severity_assessment": alert_data.get('severity', 'Unknown'),
                "immediate_action": text,
                "preventive_measures": "Review analysis for recommendations",
                "related_metrics": "Check related monitoring data",
                "confidence": 0.7,
                "note": "Response was not in expected JSON format"
            }


def require_api_key(f):
    """Decorator to check API key"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not GEMINI_API_KEY:
            return jsonify({
                "error": "GEMINI_API_KEY not configured",
                "status": "error"
            }), 500
        return f(*args, **kwargs)
    return decorated


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "service": "zabbix-ai-webhook",
        "timestamp": datetime.utcnow().isoformat(),
        "gemini_configured": bool(GEMINI_API_KEY),
        "redis_connected": redis_client is not None
    }
    
    # Test Redis
    if redis_client:
        try:
            redis_client.ping()
            status['redis_status'] = 'connected'
        except:
            status['redis_status'] = 'disconnected'
            status['status'] = 'degraded'
    
    return jsonify(status), 200


@app.route('/analyze', methods=['POST'])
@require_api_key
def analyze_alert():
    """Main endpoint to analyze alerts"""
    try:
        # Parse request
        alert_data = request.get_json()
        if not alert_data:
            return jsonify({"error": "No data provided"}), 400
        
        logger.info(f"📨 Received alert: {alert_data.get('trigger', 'Unknown')}")
        
        # Check cache
        cache_key = CacheManager.get_cache_key(alert_data)
        cached_result = CacheManager.get(cache_key)
        
        if cached_result:
            cached_result['from_cache'] = True
            return jsonify(cached_result), 200
        
        # Analyze with Gemini
        result = GeminiAnalyzer.analyze(alert_data)
        result['from_cache'] = False
        
        # Cache result
        CacheManager.set(cache_key, result)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"❌ Error in /analyze: {e}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500


@app.route('/webhook', methods=['POST'])
@require_api_key
def webhook():
    """Zabbix webhook endpoint"""
    try:
        # Zabbix sends different format
        data = request.get_json()
        
        # Transform Zabbix webhook format to our format
        alert_data = {
            'trigger': data.get('trigger_name', data.get('TRIGGER.NAME', 'Unknown')),
            'host': data.get('host_name', data.get('HOST.NAME', 'Unknown')),
            'severity': data.get('trigger_severity', data.get('TRIGGER.SEVERITY', 'Unknown')),
            'value': data.get('trigger_value', data.get('ITEM.VALUE', 'N/A')),
            'time': data.get('event_time', data.get('EVENT.TIME', 'N/A')),
            'description': data.get('trigger_description', data.get('TRIGGER.DESCRIPTION', '')),
            'event_id': data.get('event_id', data.get('EVENT.ID', ''))
        }
        
        # Analyze
        result = GeminiAnalyzer.analyze(alert_data)
        
        # Format for Zabbix (plain text response)
        response_text = f"""🤖 AI Analysis:

📊 Summary: {result.get('summary', 'N/A')}

🔍 Root Cause: {result.get('root_cause', 'N/A')}

⚡ Immediate Action:
{result.get('immediate_action', 'No recommendations')}

🛡️ Prevention:
{result.get('preventive_measures', 'No preventive measures')}

📈 Related Metrics: {result.get('related_metrics', 'N/A')}

🎯 Confidence: {result.get('confidence', 0)*100:.0f}%
"""
        
        return response_text, 200
        
    except Exception as e:
        logger.error(f"❌ Error in /webhook: {e}")
        return f"❌ AI Analysis Error: {str(e)}", 500


@app.route('/stats', methods=['GET'])
def stats():
    """Get statistics"""
    stats_data = {
        "service": "zabbix-ai-webhook",
        "uptime": time.time(),  # Would need to track actual uptime
        "cache_enabled": redis_client is not None
    }
    
    if redis_client:
        try:
            info = redis_client.info()
            stats_data['redis'] = {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', '0'),
                'total_keys': redis_client.dbsize()
            }
        except:
            pass
    
    return jsonify(stats_data), 200


if __name__ == '__main__':
    logger.info("🚀 Starting Zabbix AI Webhook Handler")
    logger.info(f"   Redis: {REDIS_HOST}:{REDIS_PORT}")
    logger.info(f"   Cache TTL: {CACHE_TTL}s")
    logger.info(f"   Gemini configured: {bool(GEMINI_API_KEY)}")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.getenv('DEBUG', 'false').lower() == 'true'
    )

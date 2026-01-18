#!/bin/bash
# Zabbix Telegram Alert Script - Qwen Only (No Fallback)
# Simple, clean integration with Qwen CLI

# Configuration
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-YOUR_BOT_TOKEN_HERE}"
QWEN_WEBHOOK_URL="${QWEN_WEBHOOK_URL:-http://qwen-wrapper:11434/api/chat}"


# Parse parameters from Zabbix
CHAT_ID="$1"
TRIGGER_NAME="$2"
HOST_NAME="$3"
TRIGGER_SEVERITY="$4"
ITEM_VALUE="$5"
EVENT_TIME="$6"

# Severity emoji mapping
case "$TRIGGER_SEVERITY" in
    "Disaster") SEVERITY_EMOJI="🔴" ;;
    "High") SEVERITY_EMOJI="🟠" ;;
    "Average") SEVERITY_EMOJI="🟡" ;;
    "Warning") SEVERITY_EMOJI="🟢" ;;
    "Information") SEVERITY_EMOJI="🔵" ;;
    *) SEVERITY_EMOJI="⚪" ;;
esac

# Build Qwen request (OpenAI-compatible format)
qwen_request=$(cat <<EOF
{
    "model": "qwen",
    "messages": [
        {
            "role": "system",
            "content": "Bạn là Senior SysAdmin expert về Zabbix monitoring. Phân tích alerts ngắn gọn, technical, đưa root cause + fix commands CỤ THỂ. Response JSON format: {\"summary\": \"...\", \"root_cause\": \"...\", \"immediate_action\": \"...\", \"confidence\": 0.0-1.0}"
        },
        {
            "role": "user",
            "content": "Alert: ${TRIGGER_NAME}\nHost: ${HOST_NAME}\nSeverity: ${TRIGGER_SEVERITY}\nValue: ${ITEM_VALUE}\nTime: ${EVENT_TIME}\n\nPhân tích ngắn gọn với commands cụ thể."
        }
    ],
    "temperature": 0.3,
    "max_tokens": 1500,
    "stream": false
}
EOF
)

# Call Qwen API
ai_response=$(curl -s -X POST "${QWEN_WEBHOOK_URL}" \
    -H "Content-Type: application/json" \
    -d "${qwen_request}" \
    --max-time 30 2>/dev/null)

# Parse response
if [ $? -eq 0 ] && [ -n "$ai_response" ]; then
    # Extract content from Ollama-compatible response (message.content)
    content=$(echo "$ai_response" | jq -r '.message.content // empty' 2>/dev/null)
    
    if [ -n "$content" ]; then
        # Try parse as JSON
        parsed=$(echo "$content" | jq -r '.' 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            # Successfully parsed JSON
            summary=$(echo "$parsed" | jq -r '.summary // ""' 2>/dev/null)
            root_cause=$(echo "$parsed" | jq -r '.root_cause // ""' 2>/dev/null)
            immediate_action=$(echo "$parsed" | jq -r '.immediate_action // ""' 2>/dev/null)
            confidence=$(echo "$parsed" | jq -r '.confidence // 0.8' 2>/dev/null)
        else
            # Content is plain text, use as-is
            summary="AI Analysis"
            root_cause=$(echo "$content" | head -c 400)
            immediate_action="Xem phân tích trên"
            confidence="0.7"
        fi

        
        # Defaults if empty
        [ -z "$summary" ] && summary="Phân tích alert"
        [ -z "$root_cause" ] && root_cause="Đang phân tích..."
        [ -z "$immediate_action" ] && immediate_action="Kiểm tra host và services"
        
        # Confidence percentage
        confidence_pct=$(echo "$confidence * 100" | bc 2>/dev/null | cut -d. -f1)
        [ -z "$confidence_pct" ] && confidence_pct="75"
        
        model_used="🧠 Qwen"
        
    else
        # Failed to extract content
        summary="Lỗi parse response"
        root_cause="Qwen response format không đúng"
        immediate_action="Kiểm tra Qwen wrapper logs"
        confidence_pct="0"
        model_used="⚠️ Qwen"
    fi
else
    # Qwen service unavailable
    summary="Qwen không khả dụng"
    root_cause="Service timeout hoặc down"
    immediate_action="Kiểm tra container zabbix-qwen-wrapper:\ndocker logs zabbix-qwen-wrapper"
    confidence_pct="0"
    model_used="❌ Qwen"
fi

# Build clean Telegram message
telegram_message="🚨 <b>${TRIGGER_NAME}</b>

${SEVERITY_EMOJI} ${TRIGGER_SEVERITY} | ${HOST_NAME} | ⏰ ${EVENT_TIME}

━━━━━━━━━━━━━━━━━━━━━━
${model_used} • ${confidence_pct}%

🔍 <b>Nguyên nhân:</b>
${root_cause}

⚡ <b>Giải pháp:</b>
${immediate_action}
━━━━━━━━━━━━━━━━━━━━━━"

# Send to Telegram
response=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${telegram_message}" \
    -d "parse_mode=HTML" \
    -d "disable_web_page_preview=true")

# Check success
if echo "$response" | grep -q '"ok":true'; then
    exit 0
else
    echo "Telegram send failed: $response" >&2
    exit 1
fi

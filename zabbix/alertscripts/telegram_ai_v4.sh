#!/bin/bash
# Zabbix Telegram Alert Script - V4 Dual-Model AI
# Supports Qwen (primary) + Gemini (fallback)
# Clean, ultra-compact output

# Configuration
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-YOUR_BOT_TOKEN_HERE}"
PRIMARY_AI_MODEL="${PRIMARY_AI_MODEL:-qwen}"
QWEN_WEBHOOK_URL="${QWEN_WEBHOOK_URL:-http://qwen-wrapper:11434/v1/chat/completions}"
GEMINI_WEBHOOK_URL="${GEMINI_WEBHOOK_URL:-http://ai-webhook:5000/analyze}"

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

# Function: Call Qwen API
call_qwen_api() {
    local payload="$1"
    local timeout="${2:-5}"
    
    # Build Qwen OpenAI-compatible request
    local qwen_request=$(cat <<EOF
{
    "model": "qwen-2.5-coder-32b-instruct",
    "messages": [
        {
            "role": "system",
            "content": "Bạn là Senior SysAdmin expert về Zabbix monitoring. Phân tích alerts ngắn gọn, technical, đưa root cause + fix commands CỤ THỂ. Response JSON: {\"summary\": \"...\", \"root_cause\": \"...\", \"immediate_action\": \"...\", \"confidence\": 0.0-1.0}"
        },
        {
            "role": "user",
            "content": "Alert: ${TRIGGER_NAME}\nHost: ${HOST_NAME}\nSeverity: ${TRIGGER_SEVERITY}\nValue: ${ITEM_VALUE}\nTime: ${EVENT_TIME}\n\nPhân tích ngắn gọn."
        }
    ],
    "temperature": 0.3,
    "max_tokens": 1000,
    "stream": false
}
EOF
)
    
    # Call Qwen API
    local response=$(curl -s -X POST "${QWEN_WEBHOOK_URL}" \
        -H "Content-Type: application/json" \
        -d "${qwen_request}" \
        --max-time "$timeout" 2>/dev/null)
    
    # Check for errors
    if [ $? -ne 0 ] || [ -z "$response" ]; then
        return 1
    fi
    
    # Check for rate limit (HTTP 429 in response)
    if echo "$response" | grep -qi "rate limit\|429"; then
        echo "RATE_LIMIT"
        return 1
    fi
    
    # Extract content from OpenAI response format
    local content=$(echo "$response" | jq -r '.choices[0].message.content // empty' 2>/dev/null)
    
    if [ -z "$content" ]; then
        return 1
    fi
    
    # Parse JSON from content
    local parsed=$(echo "$content" | jq -r '.' 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "$parsed"
        return 0
    else
        # Content might be plain JSON already
        echo "$content"
        return 0
    fi
}

# Function: Call Gemini API
call_gemini_api() {
    local payload="$1"
    local timeout="${2:-30}"
    
    # Gemini uses simple payload format (existing)
    local response=$(curl -s -X POST "${GEMINI_WEBHOOK_URL}" \
        -H "Content-Type: application/json" \
        -d "${payload}" \
        --max-time "$timeout" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo "$response"
        return 0
    else
        return 1
    fi
}

# Build common alert payload for Gemini
alert_payload=$(cat <<EOF
{
    "trigger": "${TRIGGER_NAME}",
    "host": "${HOST_NAME}",
    "severity": "${TRIGGER_SEVERITY}",
    "value": "${ITEM_VALUE}",
    "time": "${EVENT_TIME}"
}
EOF
)

# Attempt AI analysis with priority model
ai_response=""
model_used=""
fallback_reason=""

if [ "$PRIMARY_AI_MODEL" = "qwen" ]; then
    # Try Qwen first
    ai_response=$(call_qwen_api "$alert_payload" 5)
    if [ $? -eq 0 ] && [ -n "$ai_response" ] && [ "$ai_response" != "RATE_LIMIT" ]; then
        model_used="🧠 Qwen"
    elif [ "$ai_response" = "RATE_LIMIT" ]; then
        # Rate limit hit, fallback to Gemini
        fallback_reason="(Qwen rate limited)"
        ai_response=$(call_gemini_api "$alert_payload" 30)
        if [ $? -eq 0 ]; then
            model_used="💎 Gemini"
        fi
    else
        # Qwen failed, fallback to Gemini
        fallback_reason="(Qwen timeout)"
        ai_response=$(call_gemini_api "$alert_payload" 30)
        if [ $? -eq 0 ]; then
            model_used="💎 Gemini"
        fi
    fi
else
    # Gemini primary (backward compatibility)
    ai_response=$(call_gemini_api "$alert_payload" 30)
    if [ $? -eq 0 ]; then
        model_used="💎 Gemini"
    fi
fi

# Parse AI response
if [ -n "$ai_response" ] && [ "$ai_response" != "RATE_LIMIT" ]; then
    # Extract fields with jq
    clean_json=$(echo "$ai_response" | grep -o '{.*}' | head -1)
    
    if [ -n "$clean_json" ]; then
        summary=$(echo "$clean_json" | jq -r '.summary // ""' 2>/dev/null)
        root_cause_raw=$(echo "$clean_json" | jq -r '.root_cause // ""' 2>/dev/null)
        immediate_action_raw=$(echo "$clean_json" | jq -r '.immediate_action // ""' 2>/dev/null)
        confidence=$(echo "$clean_json" | jq -r '.confidence // 0.7' 2>/dev/null)
        from_cache=$(echo "$clean_json" | jq -r '.from_cache // false' 2>/dev/null)
        
        # Clean nested JSON artifacts
        if echo "$root_cause_raw" | grep -q '^{'; then
            root_cause=$(echo "$root_cause_raw" | jq -r '.root_cause // .summary // .' 2>/dev/null | head -c 300)
        else
            root_cause=$(echo "$root_cause_raw" | sed 's/```json//g; s/```//g' | head -c 300)
        fi
        
        if echo "$immediate_action_raw" | grep -q '^{'; then
            immediate_action=$(echo "$immediate_action_raw" | jq -r '.immediate_action // .summary // .' 2>/dev/null | head -c 250)
        else
            immediate_action=$(echo "$immediate_action_raw" | sed 's/```json//g; s/```//g' | head -c 250)
        fi
        
        # Remove markdown artifacts
        root_cause=$(echo "$root_cause" | sed 's/^```.*//; s/```$//; s/Nguyên nhân://g' | xargs)
        immediate_action=$(echo "$immediate_action" | sed 's/^```.*//; s/```$//; s/Các bước fix://g' | xargs)
        
        # Defaults if empty
        [ -z "$root_cause" ] && root_cause="Đang phân tích..."
        [ -z "$immediate_action" ] && immediate_action="Kiểm tra host và services"
        
        # Confidence percentage
        confidence_pct=$(echo "$confidence * 100" | bc 2>/dev/null | cut -d. -f1)
        [ -z "$confidence_pct" ] && confidence_pct="0"
        
        # Cache indicator
        [ "$from_cache" = "true" ] && cache="💾" || cache=""
        
    else
        # JSON parsing failed
        summary="AI phân tích lỗi"
        root_cause="Không parse được response"
        immediate_action="Kiểm tra AI logs"
        confidence_pct="0"
        cache="⚠️"
    fi
else
    # AI service unavailable
    summary="AI không khả dụng"
    root_cause="Cả Qwen và Gemini đều timeout/down"
    immediate_action="Kiểm tra containers: qwen-wrapper, ai-webhook"
    confidence_pct="0"
    model_used="❌ No AI"
    cache=""
fi

# Build ultra-compact Telegram message
telegram_message="🚨 <b>${TRIGGER_NAME}</b>

${SEVERITY_EMOJI} ${TRIGGER_SEVERITY} | ${HOST_NAME} | ⏰ ${EVENT_TIME}

━━━━━━━━━━━━━━━━━━━━━━
${model_used}${cache} ${fallback_reason} • ${confidence_pct}%

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

#!/bin/bash
# Zabbix Telegram Alert Script - Optimized Version
# Concise, easy-to-read format

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-YOUR_BOT_TOKEN_HERE}"
AI_WEBHOOK_URL="${AI_WEBHOOK_URL:-http://ai-webhook:5000/analyze}"

# Parse parameters
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

# Build AI request payload
ai_payload=$(cat <<EOF
{
    "trigger": "${TRIGGER_NAME}",
    "host": "${HOST_NAME}",
    "severity": "${TRIGGER_SEVERITY}",
    "value": "${ITEM_VALUE}",
    "time": "${EVENT_TIME}"
}
EOF
)

# Call AI webhook
ai_response=$(curl -s -X POST "${AI_WEBHOOK_URL}" \
    -H "Content-Type: application/json" \
    -d "${ai_payload}" \
    --max-time 30)

# Parse AI response with better error handling
if [ $? -eq 0 ] && [ -n "$ai_response" ]; then
    # Extract only the root JSON (strip any surrounding text/markdown)
    clean_response=$(echo "$ai_response" | grep -o '{.*}' | head -1)
    
    # Extract fields
    summary=$(echo "$clean_response" | jq -r '.summary // "N/A"' 2>/dev/null)
    root_cause=$(echo "$clean_response" | jq -r '.root_cause // "N/A"' 2>/dev/null)
    immediate_action=$(echo "$clean_response" | jq -r '.immediate_action // "N/A"' 2>/dev/null)
    confidence=$(echo "$clean_response" | jq -r '.confidence // 0' 2>/dev/null)
    from_cache=$(echo "$clean_response" | jq -r '.from_cache // false' 2>/dev/null)
    
    # If extraction failed, fallback
    if [ "$summary" = "N/A" ] || [ -z "$summary" ]; then
        summary="AI phân tích: ${TRIGGER_NAME} trên ${HOST_NAME}"
        root_cause="Đang kiểm tra nguyên nhân..."
        immediate_action="Vui lòng kiểm tra host và dịch vụ liên quan"
    fi
    
    # Compact multi-line text into bullet points
    root_cause=$(echo "$root_cause" | head -c 500)
    immediate_action=$(echo "$immediate_action" | head -c 400)
    
    # Calculate confidence percentage
    confidence_pct=$(echo "$confidence * 100" | bc 2>/dev/null | cut -d. -f1)
    [ -z "$confidence_pct" ] && confidence_pct="0"
    
    # Cache indicator
    [ "$from_cache" = "true" ] && cache_indicator="💾 Cache" || cache_indicator="🧠 Fresh"
else
    summary="AI không khả dụng"
    root_cause="Không thể kết nối đến AI service"
    immediate_action="Kiểm tra thủ công"
    confidence_pct="0"
    cache_indicator="⚠️ Error"
fi

# Build COMPACT Telegram message
telegram_message="🚨 <b>${TRIGGER_NAME}</b>

${SEVERITY_EMOJI} <b>${TRIGGER_SEVERITY}</b> | 🖥️ ${HOST_NAME}
⏰ ${EVENT_TIME}

━━━━━━━━━━━━━━━━━━━━━━
🤖 <b>AI Analysis</b> ${cache_indicator}

📝 <b>Tóm tắt:</b>
${summary}

🔍 <b>Nguyên nhân:</b>
${root_cause}

⚡ <b>Cần làm:</b>
${immediate_action}

━━━━━━━━━━━━━━━━━━━━━━
🎯 Confidence: ${confidence_pct}%"

# Send to Telegram
response=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${telegram_message}" \
    -d "parse_mode=HTML" \
    -d "disable_web_page_preview=true")

# Check if send was successful
if echo "$response" | grep -q '"ok":true'; then
    exit 0
else
    echo "Failed to send Telegram message: $response" >&2
    exit 1
fi

#!/bin/bash
# Zabbix Telegram Alert Script - V3 Ultra-Compact
# Clean text extraction, no JSON leak, ultra concise

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-YOUR_BOT_TOKEN_HERE}"
AI_WEBHOOK_URL="${AI_WEBHOOK_URL:-http://ai-webhook:5000/analyze}"

# Parse parameters
CHAT_ID="$1"
TRIGGER_NAME="$2"
HOST_NAME="$3"
TRIGGER_SEVERITY="$4"
ITEM_VALUE="$5"
EVENT_TIME="$6"

# Severity emoji
case "$TRIGGER_SEVERITY" in
    "Disaster") SEVERITY_EMOJI="🔴" ;;
    "High") SEVERITY_EMOJI="🟠" ;;
    "Average") SEVERITY_EMOJI="🟡" ;;
    "Warning") SEVERITY_EMOJI="🟢" ;;
    "Information") SEVERITY_EMOJI="🔵" ;;
    *) SEVERITY_EMOJI="⚪" ;;
esac

# Build AI request
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
    --max-time 30 2>/dev/null)

# Extract and clean AI response
if [ $? -eq 0 ] && [ -n "$ai_response" ]; then
    # Extract only the first complete JSON object
    clean_json=$(echo "$ai_response" | grep -o '{.*}' | head -1)
    
    if [ -n "$clean_json" ]; then
        # Extract main fields with fallback
        summary=$(echo "$clean_json" | jq -r '.summary // ""' 2>/dev/null)
        root_cause_raw=$(echo "$clean_json" | jq -r '.root_cause // ""' 2>/dev/null)
        immediate_action_raw=$(echo "$clean_json" | jq -r '.immediate_action // ""' 2>/dev/null)
        confidence=$(echo "$clean_json" | jq -r '.confidence // 0' 2>/dev/null)
        from_cache=$(echo "$clean_json" | jq -r '.from_cache // false' 2>/dev/null)
        
        # Clean up nested JSON/markdown in root_cause
        if echo "$root_cause_raw" | grep -q '^{'; then
            # It's JSON, extract the actual text field
            root_cause=$(echo "$root_cause_raw" | jq -r '.root_cause // .summary // .' 2>/dev/null | head -c 300)
        else
            # Plain text, just trim
            root_cause=$(echo "$root_cause_raw" | sed 's/```json//g; s/```//g' | head -c 300)
        fi
        
        # Clean up nested JSON/markdown in immediate_action
        if echo "$immediate_action_raw" | grep -q '^{'; then
            immediate_action=$(echo "$immediate_action_raw" | jq -r '.immediate_action // .summary // .' 2>/dev/null | head -c 250)
        else
            immediate_action=$(echo "$immediate_action_raw" | sed 's/```json//g; s/```//g' | head -c 250)
        fi
        
        # Remove any remaining markdown artifacts
        root_cause=$(echo "$root_cause" | sed 's/^```.*//; s/```$//; s/Nguyên nhân://g' | xargs)
        immediate_action=$(echo "$immediate_action" | sed 's/^```.*//; s/```$//; s/Các bước fix://g' | xargs)
        
        # If still empty, provide defaults
        [ -z "$root_cause" ] && root_cause="Đang phân tích..."
        [ -z "$immediate_action" ] && immediate_action="Kiểm tra host và services"
        
        # Confidence percentage
        confidence_pct=$(echo "$confidence * 100" | bc 2>/dev/null | cut -d. -f1)
        [ -z "$confidence_pct" ] && confidence_pct="0"
        
        # Cache indicator
        [ "$from_cache" = "true" ] && cache="💾" || cache="🧠"
    else
        # JSON parsing failed
        summary="AI phân tích lỗi"
        root_cause="Không parse được JSON response"
        immediate_action="Kiểm tra AI webhook logs"
        confidence_pct="0"
        cache="⚠️"
    fi
else
    # AI service unavailable
    summary="AI không khả dụng"
    root_cause="Service timeout hoặc down"
    immediate_action="Kiểm tra container zabbix-ai-webhook"
    confidence_pct="0"
    cache="❌"
fi

# Build ULTRA-COMPACT message
telegram_message="🚨 <b>${TRIGGER_NAME}</b>

${SEVERITY_EMOJI} ${TRIGGER_SEVERITY} | ${HOST_NAME} | ⏰ ${EVENT_TIME}

━━━━━━━━━━━━━━━━━━━━━━
${cache} <b>AI Analysis</b> • ${confidence_pct}%

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

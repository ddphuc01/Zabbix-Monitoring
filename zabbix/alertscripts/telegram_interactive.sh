#!/bin/bash
# Enhanced Telegram Alert Script with Interactive Buttons
# Sends alerts with inline action buttons

# Configuration
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-YOUR_BOT_TOKEN_HERE}"
QWEN_WEBHOOK_URL="${QWEN_WEBHOOK_URL:-http://qwen-wrapper:11434/api/chat}"

# Parse parameters
CHAT_ID="$1"
TRIGGER_NAME="$2"
HOST_NAME="$3"
TRIGGER_SEVERITY="$4"
ITEM_VALUE="$5"
EVENT_TIME="$6"
EVENT_ID="${7:-$(date +%s)}"  # Use timestamp if no event ID

# Severity emoji
case "$TRIGGER_SEVERITY" in
    "Disaster") SEVERITY_EMOJI="🔴" ;;
    "High") SEVERITY_EMOJI="🟠" ;;
    "Average") SEVERITY_EMOJI="🟡" ;;
    "Warning") SEVERITY_EMOJI="🟢" ;;
    "Information") SEVERITY_EMOJI="🔵" ;;
    *) SEVERITY_EMOJI="⚪" ;;
esac

# Build Qwen request
qwen_request=$(cat <<EOF
{
    "model": "qwen",
    "messages": [
        {
            "role": "system",
            "content": "Senior SysAdmin - analyze và đưa JSON: {\"summary\": \"...\", \"root_cause\": \"...\", \"immediate_action\": \"...\", \"confidence\": 0.8}"
        },
        {
            "role": "user",
            "content": "Alert: ${TRIGGER_NAME}\nHost: ${HOST_NAME}\nSeverity: ${TRIGGER_SEVERITY}\nValue: ${ITEM_VALUE}\nTime: ${EVENT_TIME}"
        }
    ],
    "stream": false
}
EOF
)

# Call Qwen API
ai_response=$(curl -s -X POST "${QWEN_WEBHOOK_URL}" -H "Content-Type: application/json" -d "${qwen_request}" --max-time 30)

# Parse response (Ollama format)
if [ $? -eq 0 ] && [ -n "$ai_response" ]; then
    content=$(echo "$ai_response" | jq -r '.message.content // empty')
    
    if [ -n "$content" ]; then
        summary=$(echo "$content" | jq -r '.summary // "Phân tích alert"')
        root_cause=$(echo "$content" | jq -r '.root_cause // "Đang phân tích..."' | head -c 300)
        immediate_action=$(echo "$content" | jq -r '.immediate_action // "Kiểm tra host"' | head -c 250)
        confidence=$(echo "$content" | jq -r '.confidence // 0.75')
        confidence_pct=$(echo "$confidence * 100" | bc | cut -d. -f1)
    else
        summary="Phân tích alert"
        root_cause="Qwen response không đọc được"
        immediate_action="Kiểm tra Qwen logs"
        confidence_pct="0"
    fi
else
    summary="Qwen unavailable"
    root_cause="Service timeout"
    immediate_action="Kiểm tra qwen-wrapper"
    confidence_pct="0"
fi

# Build message with AI analysis
telegram_text="🚨 <b>${TRIGGER_NAME}</b>

${SEVERITY_EMOJI} ${TRIGGER_SEVERITY} | ${HOST_NAME} | ⏰ ${EVENT_TIME}

━━━━━━━━━━━━━━━━━━━━━━
🧠 AI Analysis • ${confidence_pct}%

🔍 <b>Nguyên nhân:</b>
${root_cause}

⚡ <b>Giải pháp:</b>
${immediate_action}
━━━━━━━━━━━━━━━━━━━━━━

Alert ID: <code>${EVENT_ID}</code>"

# Build inline keyboard with action buttons
inline_keyboard=$(cat <<EOF
{
  "inline_keyboard": [
    [
      {"text": "🔍 Run Diagnostic", "callback_data": "diag:${EVENT_ID}"},
      {"text": "🔧 Auto-Fix", "callback_data": "confirm_fix:${EVENT_ID}"}
    ],
    [
      {"text": "🔄 Restart Service", "callback_data": "restart:${EVENT_ID}"},
      {"text": "📊 Show Metrics", "callback_data": "metrics:${EVENT_ID}"}
    ],
    [
      {"text": "✅ Acknowledge", "callback_data": "ack:${EVENT_ID}"},
      {"text": "🔇 Ignore", "callback_data": "ignore:${EVENT_ID}"}
    ]
  ]
}
EOF
)

# Send to Telegram with buttons
response=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${telegram_text}" \
    -d "parse_mode=HTML" \
    --data-urlencode "reply_markup=${inline_keyboard}")

# Check success
if echo "$response" | grep -q '"ok":true'; then
    exit 0
else
    echo "Telegram send failed: $response" >&2
    exit 1
fi

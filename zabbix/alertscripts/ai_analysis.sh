#!/bin/bash
# Zabbix Alert Script - AI Analysis with Gemini
# Usage: Called from Zabbix Actions

WEBHOOK_URL="${WEBHOOK_URL:-http://ai-webhook:5000/analyze}"
TRIGGER_NAME="$1"
HOST_NAME="$2"
TRIGGER_SEVERITY="$3"
ITEM_VALUE="$4"
EVENT_TIME="$5"

# Build JSON payload
payload=$(cat <<EOF
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
response=$(curl -s -X POST "${WEBHOOK_URL}" \
    -H "Content-Type: application/json" \
    -d "${payload}" \
    --max-time 30)

# Check if response is valid
if [ $? -eq 0 ]; then
    echo "${response}" | jq -r '.summary // .error // "AI analysis completed"'
else
    echo "⚠️  AI service unavailable"
fi

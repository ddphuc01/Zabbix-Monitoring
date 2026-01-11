#!/bin/bash
# Zabbix Telegram Alert Script with AI Analysis
# Usage: telegram.sh <TO> <SUBJECT> <MESSAGE>

# Telegram Bot Token (replace with your bot token)
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-YOUR_BOT_TOKEN_HERE}"

# Parse parameters
CHAT_ID="$1"
SUBJECT="$2"
MESSAGE="$3"

# Function to send Telegram message
send_telegram() {
    local chat_id="$1"
    local text="$2"
    
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${chat_id}" \
        -d "text=${text}" \
        -d "parse_mode=HTML" \
        -d "disable_web_page_preview=true" > /dev/null 2>&1
}

# Build message with emojis and formatting
TELEGRAM_MESSAGE="🚨 <b>Zabbix Alert</b>

📋 <b>Subject:</b> ${SUBJECT}

${MESSAGE}"

# Send to Telegram
send_telegram "${CHAT_ID}" "${TELEGRAM_MESSAGE}"

exit 0

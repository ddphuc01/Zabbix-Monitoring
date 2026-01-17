#!/bin/bash
# Quick Webhook Test Script
# Tests the webhook endpoint with sample alert data

set -e

WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:5000/webhook}"

echo "=================================================="
echo "Zabbix AI Webhook - Quick Test"
echo "=================================================="
echo ""
echo "Webhook URL: $WEBHOOK_URL"
echo ""

# Test 1: CPU Alert
echo "Test 1: CPU Alert"
echo "--------------------------------------------------"
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_name": "High CPU usage on web-server-prod-01",
    "host_name": "web-server-prod-01",
    "trigger_severity": "High",
    "trigger_value": "92",
    "event_time": "2026-01-16 00:00:00"
  }' \
  --silent --show-error | head -c 500
echo -e "\n"

echo ""
echo "Test 2: Memory Alert"
echo "--------------------------------------------------"
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_name": "High memory usage on db-server-prod-01",
    "host_name": "db-server-prod-01",
    "trigger_severity": "Critical",
    "trigger_value": "95",
    "event_time": "2026-01-16 00:05:00"
  }' \
  --silent --show-error | head -c 500
echo -e "\n"

echo ""
echo "Test 3: Disk Alert"
echo "--------------------------------------------------"
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_name": "Low disk space on /dev/sda1 on app-server-prod-01",
    "host_name": "app-server-prod-01",
    "trigger_severity": "Critical",
    "trigger_value": "97",
    "event_time": "2026-01-16 00:10:00"
  }' \
  --silent --show-error | head -c 500
echo -e "\n"

echo ""
echo "Test 4: Network Alert"
echo "--------------------------------------------------"
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_name": "High network connections on api-server-prod-01",
    "host_name": "api-server-prod-01",
    "trigger_severity": "High",
    "trigger_value": "1500",
    "event_time": "2026-01-16 00:15:00"
  }' \
  --silent --show-error | head -c 500
echo -e "\n"

echo ""
echo "=================================================="
echo "Tests completed!"
echo "=================================================="

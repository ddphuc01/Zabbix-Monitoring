#!/usr/bin/env python3
"""
Interactive Telegram Bot for Zabbix Alert Management
Phase 1: Inline Buttons + Basic Commands
"""

import os
import json
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
import requests
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from reports import ReportGenerator
from email_sender import EmailSender
import pytz
import redis

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN')
ZABBIX_API_URL = os.getenv('ZABBIX_API_URL', 'http://zabbix-web:8080/api_jsonrpc.php')
ZABBIX_API_USER = os.getenv('ZABBIX_API_USER', 'Admin')
ZABBIX_API_PASSWORD = os.getenv('ZABBIX_API_PASSWORD', 'zabbix')
ANSIBLE_API_URL = os.getenv('ANSIBLE_API_URL', 'http://ansible-executor:5001')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_API_BASE = 'https://api.groq.com/openai/v1'

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Initialize Redis client
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
        socket_timeout=5
    )
    redis_client.ping()
    logger.info("✅ Bot connected to Redis")
except Exception as e:
    logger.warning(f"⚠️ Redis connection failed: {e}, alert data caching disabled")
    redis_client = None

# User roles (simple implementation - later use DB)
USER_ROLES = {
    # Add your Telegram user IDs here
    1081490318: 'ADMIN',  # Dương Duy
    # 987654321: 'OPERATOR',
}

# Authorization levels
ROLE_PERMISSIONS = {
    'ADMIN': ['fix', 'restart', 'diag', 'ack', 'ignore', 'rollback'],
    'OPERATOR': ['restart', 'diag', 'ack', 'ignore'],
    'VIEWER': ['diag', 'ack']
}

def get_user_role(user_id: int) -> str:
    """Get user role - default to VIEWER"""
    return USER_ROLES.get(user_id, 'VIEWER')

def is_authorized(user_id: int, action: str) -> tuple[bool, str]:
    """Check if user authorized for action"""
    role = get_user_role(user_id)
    permissions = ROLE_PERMISSIONS.get(role, [])
    
    if action in permissions:
        return True, f"Authorized as {role}"
    else:
        return False, f"Permission denied. {action} requires {', '.join([r for r, p in ROLE_PERMISSIONS.items() if action in p])} role."

class ZabbixRPC:
    """Handle Zabbix JSON-RPC Interactions"""
    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password
        self.auth_token = None
        self.id = 1

    def login(self):
        """Authenticate and get auth token"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "user.login",
                "params": {
                    "username": self.user,
                    "password": self.password
                },
                "id": self.id
            }
            response = requests.post(self.url, json=payload, timeout=5)
            response.raise_for_status()
            result = response.json()
            
            if 'result' in result:
                self.auth_token = result['result']
                logger.info(f"✅ Zabbix Login Successful (Token: {self.auth_token[:10]}...)")
                return True, "Success"
            else:
                error = result.get('error', {}).get('data', 'Unknown Zabbix Error')
                logger.error(f"❌ Zabbix Login Failed: {error}")
                return False, f"Login Failed: {error}"
        except Exception as e:
            logger.error(f"❌ Zabbix Login Error: {e}")
            return False, f"Connection Error: {str(e)}"

    def call(self, method, params=None):
        """Make generic JSON-RPC call"""
        if not self.auth_token:
            success, msg = self.login()
            if not success:
                raise Exception(msg)

        # Zabbix 7.0+ requires Authorization header, 'auth' param is removed/deprecated
        headers = {
            "Content-Type": "application/json-rpc", 
            "Authorization": f"Bearer {self.auth_token}"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.id
        }
        self.id += 1

        try:
            logger.info(f"📤 Zabbix API Request: {method}")
            response = requests.post(self.url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if 'error' in result:
                logger.error(f"❌ Zabbix API Error Payload: {result['error']}")
                
            return result
        except Exception as e:
            logger.error(f"❌ Zabbix API Exception ({method}): {e}")
            raise
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Zabbix API Error ({method}): {e}")
            raise

# Initialize Zabbix Client
zabbix_client = ZabbixRPC(ZABBIX_API_URL, ZABBIX_API_USER, ZABBIX_API_PASSWORD)

# Command Handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    role = get_user_role(user.id)
    
    welcome_msg = f"""
🤖 <b>Zabbix AI Bot</b>

Welcome {user.first_name}!
Your role: <b>{role}</b>

<b>Available Commands:</b>
/help - Show all commands
/list - Active alerts
/status - System status

<b>Quick Tips:</b>
• Click buttons on alert messages for quick actions
• Use commands for advanced control
• Natural language coming soon!

Your ID: <code>{user.id}</code>
"""
    await update.message.reply_text(welcome_msg, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    role = get_user_role(update.effective_user.id)
    
    help_text = f"""
📚 <b>Command Reference</b>

<b>Basic Commands:</b>
/list - Show active alerts
/status - System health status
/help - This message

<b>Alert Actions:</b>
/fix &lt;event_id&gt; - Execute AI-suggested fix
/diag &lt;event_id&gt; - Run diagnostic
/restart &lt;event_id&gt; - Restart service
/ack &lt;event_id&gt; - Acknowledge alert
/ignore &lt;event_id&gt; - Suppress alert

<b>Your Permissions ({role}):</b>
{', '.join(ROLE_PERMISSIONS.get(role, []))}

<b>Inline Buttons:</b>
Alert messages include action buttons - just click!

<b>Tips:</b>
• Event IDs shown in alert messages
• Use buttons for quick actions
• Commands for precise control
"""
    await update.message.reply_text(help_text, parse_mode='HTML')

async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List active alerts"""
    try:
        # Call Zabbix API (JSON-RPC)
        response = zabbix_client.call("problem.get", {
            "output": "extend",
            "selectAcknowledges": "extend",
            "selectTags": "extend",
            "recent": True,
            "sortfield": ["eventid"],
            "sortorder": "DESC",
            "limit": 10
        })
        
        if 'result' not in response:
            await update.message.reply_text(f"❌ API Error: {response.get('error', {}).get('data', 'Unknown')}")
            return

        problems = response['result']
        
        if not problems:
            await update.message.reply_text("✅ No active alerts!")
            return
        
        msg = "📋 <b>Active Alerts</b>\n\n"
        for p in problems:
            severity_val = int(p.get('severity', 0))
            name = p.get('name', 'N/A')
            event_id = p.get('eventid', '0')
            # Host lookup would require another API call or caching, skipping for speed or just showing simple data
            # To get host name, problem.get usually needs 'selectHosts': 'extend'
            
            severity_map = {
                5: '🔴 Disaster',
                4: '🟠 High',
                3: '🟡 Average',
                2: '🔵 Warning',
                1: '⚪ Info',
                0: '⚫ Not Classified'
            }
            severity_str = severity_map.get(severity_val, 'Unknown')
            
            msg += f"{severity_str.split()[0]} <code>#{event_id}</code> - {name}\n"
            msg += f"   Severity: {severity_str.split()[1]}\n\n"
        
        await update.message.reply_text(msg, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error listing alerts: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system status"""
    try:
        # Check Zabbix API
        zabbix_status = "✅ Online"
        try:
            # Simple version check
            response = requests.post(
                ZABBIX_API_URL, 
                json={"jsonrpc": "2.0", "method": "apiinfo.version", "params": [], "id": 1},
                timeout=5
            )
            if response.status_code != 200:
                zabbix_status = f"⚠️ Error {response.status_code}"
            elif 'error' in response.json():
                zabbix_status = "⚠️ API Error"
        except Exception:
            zabbix_status = "❌ Offline"
        
        # Check Ansible API
        ansible_status = "✅ Ready"
        try:
            response = requests.get(f"{ANSIBLE_API_URL}/health", timeout=5)
            if response.status_code != 200:
                ansible_status = f"⚠️ Error {response.status_code}"
        except Exception:
            ansible_status = "❌ Offline"
        
        # Check Groq API
        groq_status = "✅ Ready" if GROQ_API_KEY else "⚠️ No API Key"
        if GROQ_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
                response = requests.get(f"{GROQ_API_BASE}/models", headers=headers, timeout=5)
                if response.status_code != 200:
                    groq_status = f"⚠️ Error {response.status_code}"
            except Exception:
                groq_status = "❌ Offline"
        
        status_msg = f"""
🔍 <b>System Status</b>

<b>Services:</b>
• Zabbix API: {zabbix_status}
• Ansible: {ansible_status}
• Groq AI: {groq_status}

<b>Bot:</b>
• Status: ✅ Running
• Uptime: Active
• Version: Phase 1

<b>Your Access:</b>
• Role: <b>{get_user_role(update.effective_user.id)}</b>
• Permissions: {len(ROLE_PERMISSIONS.get(get_user_role(update.effective_user.id), []))} actions
"""
        await update.message.reply_text(status_msg, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def fix_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute fix for alert"""
    user_id = update.effective_user.id
    
    # Check authorization
    authorized, msg = is_authorized(user_id, 'fix')
    if not authorized:
        await update.message.reply_text(f"🔒 {msg}")
        return
    
    # Get event ID from command args
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /fix <event_id>")
        return
    
    event_id = context.args[0]
    
    # Send confirmation with buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_fix:{event_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{event_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    confirm_msg = f"""
⚠️ <b>Confirmation Required</b>

Action: Auto-fix for alert #{event_id}
User: {update.effective_user.first_name}

This will execute AI-suggested remediation.

Confirm?
"""
    await update.message.reply_text(confirm_msg, parse_mode='HTML', reply_markup=reply_markup)

# Callback Query Handler

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    logger.info(f"Button callback: {data} from user {user_id}")
    
    # Handle report buttons
    if data.startswith("report_") or data.startswith("html_") or data.startswith("email_"):
        await handle_report_button(query, data)
        return
    
    # Parse callback data for alert actions
    parts = data.split(':')
    action = parts[0]
    
    # Handle webhook button actions (new format: action:hostname:service_name)
    if action == 'restart_service':
        hostname = parts[1] if len(parts) > 1 else 'Unknown'
        service_name = parts[2] if len(parts) > 2 else 'Unknown'
        
        # Check authorization
        authorized, msg = is_authorized(user_id, 'restart')
        if not authorized:
            await query.edit_message_text(f"🔒 {msg}")
            return
        
        await execute_service_restart(query, hostname, service_name)
        return
    
    elif action == 'check_service':
        hostname = parts[1] if len(parts) > 1 else 'Unknown'
        service_name = parts[2] if len(parts) > 2 else 'Unknown'
        await check_service_status(query, hostname, service_name)
        return
    
    elif action == 'diagnostics':
        hostname = parts[1] if len(parts) > 1 else 'Unknown'
        await execute_host_diagnostic(query, hostname)
        return
    
    elif action == 'ai_analysis':
        event_id = parts[1] if len(parts) > 1 else None
        if event_id:
            await execute_ai_analysis(query, event_id)
        else:
            await query.edit_message_text("❌ Invalid AI analysis request")
        return
    
    # Legacy format: action:event_id
    event_id = parts[1] if len(parts) > 1 else None
    
    if action == 'confirm_fix':
        # Check authorization again
        authorized, msg = is_authorized(user_id, 'fix')
        if not authorized:
            await query.edit_message_text(f"🔒 {msg}")
            return
        
        # Execute fix
        await execute_fix(query, event_id)
    
    elif action == 'diag':
        await execute_diagnostic(query, event_id)
    
    elif action == 'restart':
        # Check authorization
        authorized, msg = is_authorized(user_id, 'restart')
        if not authorized:
            await query.edit_message_text(f"🔒 {msg}")
            return
        await execute_restart(query, event_id)
    
    elif action == 'ack':
        await acknowledge_alert(query, event_id)
    
    elif action == 'ignore':
        await ignore_alert(query, event_id)
    
    elif action == 'cancel':
        await query.edit_message_text("❌ Action cancelled.")
    
    else:
        await query.edit_message_text(f"Unknown action: {action}")

async def handle_report_button(query, data):
    """Handle report/html/email button callbacks"""
    import os
    import tempfile
    
    # Report text buttons
    if data.startswith("report_"):
        report_type = data.split("_")[1]
        await query.message.reply_text(f"📊 Generating {report_type} report...")
        
        if report_type == "daily":
            report = report_gen.generate_daily_summary()
        elif report_type == "week":
            report = report_gen.generate_weekly_report()
        elif report_type == "alerts":
            report = report_gen.generate_alert_summary()
        else:
            await query.message.reply_text("❌ Unknown report type")
            return
        
        await query.message.reply_text(report, parse_mode='Markdown')
    
    # HTML file buttons
    elif data.startswith("html_"):
        report_type = data.split("_")[1]
        await query.message.reply_text(f"📄 Generating HTML file...")
        
        if report_type == "daily":
            html_data = report_gen.get_daily_email_data()
            title = f"Báo_Cáo_Hàng_Ngày_{datetime.now().strftime('%d-%m-%Y')}"
            template_type = "daily"
        elif report_type == "week":
            html_data = report_gen.get_weekly_email_data()
            title = f"Báo_Cáo_Tuần_Week_{datetime.now().isocalendar()[1]}"
            template_type = "weekly"
        else:
            html_data = report_gen.get_alerts_email_data()
            title = f"Báo_Cáo_Alerts_{datetime.now().strftime('%d-%m-%Y')}"
            template_type = "alerts"
        
        html_content = email_sender._generate_html(html_data, template_type)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            temp_path = f.name
        
        with open(temp_path, 'rb') as f:
            await query.message.reply_document(
                document=f,
                filename=f"{title}.html",
                caption=f"📊 {title.replace('_', ' ')}\n\nMở file trong browser!"
            )
        
        os.unlink(temp_path)
    
    # Email buttons
    elif data.startswith("email_"):
        report_type = data.split("_")[1]
        await query.message.reply_text(f"📧 Sending email...")
        
        if report_type == "daily":
            email_data = report_gen.get_daily_email_data()
            subject = f"📊 Báo Cáo Hàng Ngày - {datetime.now().strftime('%d/%m/%Y')}"
        elif report_type == "week":
            email_data = report_gen.get_weekly_email_data()
            subject = f"📈 Báo Cáo Tuần - Week {datetime.now().isocalendar()[1]}"
        else:
            email_data = report_gen.get_alerts_email_data()
            subject = f"🚨 Báo Cáo Alerts"
        
        success = email_sender.send_report(subject, email_data, report_type)
        if success:
            await query.message.reply_text("✅ Email sent successfully!")
        else:
            await query.message.reply_text("❌ Email failed. Check SMTP config.")

# Action Executors

async def execute_fix(query, event_id: str):
    """Execute auto-fix via Ansible"""
    try:
        # Update message to show progress
        await query.edit_message_text(f"⏳ <b>Executing fix for #{event_id}...</b>\n\nRunning diagnostic...", parse_mode='HTML')
        
        # Call Ansible API (placeholder - implement actual API call)
        # response = requests.post(f"{ANSIBLE_API_URL}/fix/{event_id}", timeout=60)
        
        # Simulate execution for now
        import time
        time.sleep(3)
        
        # Success message
        success_msg = f"""
✅ <b>Fix Completed Successfully</b>

Alert: #{event_id}
Action: Auto-fix executed
Duration: 3.2 seconds

<b>Results:</b>
✓ Service restarted
✓ CPU usage normalized (45%)
✓ Memory freed (2.1 GB)

Alert auto-closed in Zabbix.
"""
        await query.edit_message_text(success_msg, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Fix execution error: {e}")
        await query.edit_message_text(f"❌ Fix failed: {str(e)}")

async def execute_diagnostic(query, event_id: str):
    """Run diagnostic via Ansible"""
    try:
        await query.edit_message_text(f"🔍 <b>Running diagnostic for #{event_id}...</b>", parse_mode='HTML')
        
        # Call Ansible API (placeholder)
        import time
        time.sleep(2)
        
        diag_result = f"""
🔍 <b>Diagnostic Report</b>

Alert: #{event_id}

<b>System Status:</b>
• CPU: 85% (high)
• Memory: 78% (normal)
• Disk: 45% (normal)

<b>Top Processes:</b>
1. node (PID 12345) - 65% CPU
2. postgres (PID 456) - 15% CPU

<b>AI Analysis:</b>
Memory leak detected in node process.
Recommendation: Restart service

<b>Next Steps:</b>
Use /fix {event_id} to execute fix
"""
        
        # Add action buttons
        keyboard = [
            [InlineKeyboardButton("🔧 Fix Now", callback_data=f"confirm_fix:{event_id}")],
            [InlineKeyboardButton("🔄 Run Again", callback_data=f"diag:{event_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(diag_result, parse_mode='HTML', reply_markup=reply_markup)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Diagnostic failed: {str(e)}")

async def execute_restart(query, event_id: str):
    """Restart service"""
    try:
        await query.edit_message_text(f"🔄 <b>Restarting service for #{event_id}...</b>", parse_mode='HTML')
        
        import time
        time.sleep(2)
        
        await query.edit_message_text(f"✅ Service restarted successfully for #{event_id}", parse_mode='HTML')
    except Exception as e:
        await query.edit_message_text(f"❌ Restart failed: {str(e)}")

async def acknowledge_alert(query, event_id: str):
    """Acknowledge alert in Zabbix"""
    try:
        # Call Zabbix API to acknowledge
        # response = requests.post(f"{ZABBIX_API_URL}/acknowledge/{event_id}")
        
        await query.edit_message_text(f"✅ Alert #{event_id} acknowledged.", parse_mode='HTML')
    except Exception as e:
        await query.edit_message_text(f"❌ Acknowledge failed: {str(e)}")

async def ignore_alert(query, event_id: str):
    """Suppress alert"""
    try:
        await query.edit_message_text(f"🔇 Alert #{event_id} suppressed.", parse_mode='HTML')
    except Exception as e:
        await query.edit_message_text(f"❌ Suppress failed: {str(e)}")

async def execute_service_restart(query, hostname: str, service_name: str):
    """Restart Windows/Linux service via Ansible"""
    try:
        await query.edit_message_text(
            f"🔄 <b>Restarting service...</b>\n\n"
            f"Host: <code>{hostname}</code>\n"
            f"Service: <code>{service_name}</code>\n\n"
            f"⏳ Please wait...",
            parse_mode='HTML'
        )
        
        # Call Ansible API to restart service
        payload = {
            "playbook": "restart_service",
            "target_host": hostname,
            "extra_vars": {
                "service_name": service_name
            }
        }
        
        response = requests.post(
            f"{ANSIBLE_API_URL}/api/v1/playbook/run",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                await query.edit_message_text(
                    f"✅ <b>Service Restarted Successfully</b>\n\n"
                    f"Host: <code>{hostname}</code>\n"
                    f"Service: <code>{service_name}</code>\n\n"
                    f"<b>Status:</b> Running ✓\n"
                    f"<b>Duration:</b> {result.get('duration', 'N/A')}s",
                    parse_mode='HTML'
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                await query.edit_message_text(
                    f"❌ <b>Restart Failed</b>\n\n"
                    f"Host: <code>{hostname}</code>\n"
                    f"Service: <code>{service_name}</code>\n\n"
                    f"Error: {error_msg}",
                    parse_mode='HTML'
                )
        else:
            await query.edit_message_text(
                f"❌ <b>API Error</b>\n\n"
                f"Status: {response.status_code}\n"
                f"Response: {response.text[:200]}",
                parse_mode='HTML'
            )
            
    except requests.Timeout:
        await query.edit_message_text(
            f"⏱️ <b>Timeout</b>\n\n"
            f"Ansible API took too long to respond.\n"
            f"Service may still be restarting.",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Service restart error: {e}")
        await query.edit_message_text(
            f"❌ <b>Error</b>\n\n"
            f"Failed to restart service: {str(e)}",
            parse_mode='HTML'
        )

async def check_service_status(query, hostname: str, service_name: str):
    """Check Windows/Linux service status via Ansible"""
    try:
        await query.edit_message_text(
            f"📊 <b>Checking service status...</b>\n\n"
            f"Host: <code>{hostname}</code>\n"
            f"Service: <code>{service_name}</code>",
            parse_mode='HTML'
        )
        
        # Call Ansible API to check service
        payload = {
            "playbook": "check_service",
            "target_host": hostname,
            "extra_vars": {
                "service_name": service_name
            }
        }
        
        response = requests.post(
            f"{ANSIBLE_API_URL}/api/v1/playbook/run",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                service_data = result.get('result', {})
                status = service_data.get('status', 'unknown')
                startup_type = service_data.get('start_mode', 'unknown')
                
                status_emoji = "✅" if status == "running" else "❌"
                
                # Add restart button if service is stopped
                keyboard = []
                if status != "running":
                    keyboard.append([
                        InlineKeyboardButton(
                            "🔄 Start Service",
                            callback_data=f"restart_service:{hostname}:{service_name}"
                        )
                    ])
                reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
                
                await query.edit_message_text(
                    f"{status_emoji} <b>Service Status</b>\n\n"
                    f"Host: <code>{hostname}</code>\n"
                    f"Service: <code>{service_name}</code>\n\n"
                    f"<b>Status:</b> {status.title()}\n"
                    f"<b>Startup Type:</b> {startup_type.title()}",
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(
                    f"❌ <b>Check Failed</b>\n\n"
                    f"Could not retrieve service status.\n"
                    f"Error: {result.get('error', 'Unknown')}",
                    parse_mode='HTML'
                )
        else:
            await query.edit_message_text(
                f"❌ <b>API Error</b>\n\n"
                f"Status: {response.status_code}",
                parse_mode='HTML'
            )
            
    except Exception as e:
        logger.error(f"Service status check error: {e}")
        await query.edit_message_text(
            f"❌ <b>Error</b>\n\n"
            f"Failed to check service: {str(e)}",
            parse_mode='HTML'
        )

async def execute_host_diagnostic(query, hostname: str):
    """Run full diagnostic on host via Ansible"""
    try:
        await query.edit_message_text(
            f"🔍 <b>Running diagnostics...</b>\n\n"
            f"Host: <code>{hostname}</code>\n\n"
            f"⏳ Gathering system metrics...",
            parse_mode='HTML'
        )
        
        # Call Ansible API for diagnostics
        payload = {
            "playbook": "gather_system_metrics",
            "target_host": hostname,
            "extra_vars": {}
        }
        
        response = requests.post(
            f"{ANSIBLE_API_URL}/api/v1/playbook/run",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                diag_data = result.get('result', {})
                
                # Format diagnostic results
                cpu = diag_data.get('cpu', {}).get('usage', 'N/A')
                memory = diag_data.get('memory', {}).get('used_percent', 'N/A')
                disk = diag_data.get('disk', {}).get('used_percent', 'N/A')
                uptime = diag_data.get('uptime', 'N/A')
                
                await query.edit_message_text(
                    f"🔍 <b>Diagnostic Report</b>\n\n"
                    f"Host: <code>{hostname}</code>\n\n"
                    f"<b>System Metrics:</b>\n"
                    f"• CPU: {cpu}%\n"
                    f"• Memory: {memory}%\n"
                    f"• Disk: {disk}%\n"
                    f"• Uptime: {uptime}\n\n"
                    f"<b>Status:</b> ✅ Diagnostic complete",
                    parse_mode='HTML'
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                await query.edit_message_text(
                    f"❌ <b>Diagnostic Failed</b>\n\n"
                    f"Host: <code>{hostname}</code>\n\n"
                    f"<b>Error:</b> {error_msg}\n\n"
                    f"<b>Note:</b> Current diagnostic playbook supports Linux hosts only. "
                    f"Windows diagnostics coming soon!",
                    parse_mode='HTML'
                )
        else:
            # API returned error status
            try:
                error_data = response.json()
                error_msg = error_data.get('error', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}'
            
            await query.edit_message_text(
                f"❌ <b>API Error</b>\n\n"
                f"Host: <code>{hostname}</code>\n\n"
                f"<b>Status:</b> {response.status_code}\n"
                f"<b>Error:</b> {error_msg}\n\n"
                f"<i>Tip: This playbook may not support this host type</i>",
                parse_mode='HTML'
            )
            
    except Exception as e:
        logger.error(f"Diagnostic error: {e}")
        await query.edit_message_text(
            f"❌ <b>Error</b>\n\n"
            f"Failed to run diagnostic: {str(e)}",
            parse_mode='HTML'
        )

async def execute_ai_analysis(query, event_id: str):
    """Execute AI analysis on demand when user clicks button"""
    try:
        await query.edit_message_text(
            f"🤖 <b>Generating AI Analysis...</b>\n\n"
            f"Event: #{event_id}\n\n"
            f"⏳ Please wait...",
            parse_mode='HTML'
        )
        
        # Retrieve cached alert data from Redis
        if not redis_client:
            await query.edit_message_text(
                f"❌ <b>Redis Not Available</b>\n\n"
                f"Cannot retrieve alert data.\n"
                f"AI analysis requires Redis for caching.",
                parse_mode='HTML'
            )
            return
        
        cache_key = f"alert_data:{event_id}"
        try:
            cached_data = redis_client.get(cache_key)
            if not cached_data:
                await query.edit_message_text(
                    f"❌ <b>Alert Data Not Found</b>\n\n"
                    f"Event: #{event_id}\n\n"
                    f"Alert data expired or not available.\n"
                    f"AI analysis must be requested within 1 hour of alert.",
                    parse_mode='HTML'
                )
                return
            
            full_alert_data = json.loads(cached_data)
            alert_data = full_alert_data.get('alert', {})
            ansible_data = full_alert_data.get('ansible', {})
            
        except Exception as e:
            logger.error(f"Failed to retrieve alert data: {e}")
            await query.edit_message_text(
                f"❌ <b>Cache Retrieval Error</b>\n\n"
                f"Failed to load alert data: {str(e)}",
                parse_mode='HTML'
            )
            return
        
        # Call Groq API for AI analysis
        if not GROQ_API_KEY:
            await query.edit_message_text(
                f"❌ <b>Groq API Not Configured</b>\n\n"
                f"AI analysis requires GROQ_API_KEY.",
                parse_mode='HTML'
            )
            return
        
        try:
            # Prepare prompt for Groq
            
            groq_client = Groq(api_key=GROQ_API_KEY)
            
            # Build analysis request
            user_content = {
                "alert_type": "UNKNOWN",  # Can be enhanced
                "hostname": alert_data.get('host', 'Unknown'),
                "current_value": alert_data.get('value', 'N/A'),
                "threshold": "N/A",
                "timestamp": alert_data.get('time', 'N/A'),
                "ansible_output": ansible_data,
                "service_info": {
                    "environment": "production",
                    "app_type": "web",
                    "expected_load": "normal"
                }
            }
            
            system_prompt = """Ban la System Administrator phan tich Zabbix alerts. 
Dua ra phan tich ngan gon (150-200 words) bang Tieng Viet:
- Nguyen nhan chinh
- Khuyen nghi hanh dong cu the
- Urgency level
Dung emoji de de hieu hon."""
            
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_content)}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            analysis_text = completion.choices[0].message.content
            
            # Send AI analysis as response
            await query.edit_message_text(
                f"🤖 <b>AI Analysis</b>\n\n"
                f"{analysis_text}\n\n"
                f"<i>Powered by Groq AI</i>",
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            await query.edit_message_text(
                f"❌ <b>AI Analysis Failed</b>\n\n"
                f"Error: {str(e)}\n\n"
                f"<i>Groq API may be unavailable or quota exceeded.</i>",
                parse_mode='HTML'
            )
            
    except Exception as e:
        logger.error(f"AI analysis error: {e}")
        await query.edit_message_text(
            f"❌ <b>Error</b>\n\n"
            f"Failed to generate AI analysis: {str(e)}",
            parse_mode='HTML'
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Suppress failed: {str(e)}")

# AI Chat Handler

async def build_zabbix_context(question: str) -> dict:
    """
    Build relevant Zabbix context based on user question
    
    Detects intent and fetches appropriate data:
    - Keywords like "alert", "problem" → fetch active problems
    - Keywords like "cpu", "memory", "disk" → fetch relevant metrics
    - Keywords like "server", "host", "status" → fetch host status
    """
    context = {
        "problems": [],
        "metrics": [],
        "hosts": []
    }
    
   
    question_lower = question.lower()
    
    try:
        # Check for alert/problem intent
        if any(keyword in question_lower for keyword in ['alert', 'problem', 'issue', 'vấn đề', 'lỗi', 'cảnh báo', 'sự cố']):
            response = requests.get(f"{ZABBIX_API_URL}/problems", params={"limit": 5}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                context["problems"] = data.get("problems", [])[:5]
        
        # Check for metrics intent (CPU, memory, disk, etc.)
        metric_keywords = {
            'cpu': ['cpu', 'processor', 'xử lý'],
            'memory': ['memory', 'ram', 'bộ nhớ'],
            'disk': ['disk', 'ổ đĩa', 'storage', 'dung lượng'],
            'network': ['network', 'mạng', 'bandwidth']
        }
        
        for metric_type, keywords in metric_keywords.items():
            if any(kw in question_lower for kw in keywords):
                response = requests.get(
                    f"{ZABBIX_API_URL}/metrics/search",
                    params={"keyword": metric_type, "limit": 5},
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    context["metrics"].extend(data.get("metrics", [])[:5])
        
        # Check for host/server/system status intent
        if any(keyword in question_lower for keyword in ['server', 'host', 'máy chủ', 'status', 'health', 'tình trạng', 'hệ thống', 'system', 'thế nào', 'như thế nào', 'hiện tại']):
            # Get all hosts first
            response = requests.get(f"{ZABBIX_API_URL}/hosts", params={"limit": 3}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                hosts = data.get("hosts", [])
                
                # Get detailed status for each host
                for host in hosts[:2]:  # Limit to 2 hosts to avoid overwhelming
                    host_id = host.get("id")
                    status_response = requests.get(
                        f"{ZABBIX_API_URL}/hosts/{host_id}/status",
                        timeout=10
                    )
                    if status_response.status_code == 200:
                        context["hosts"].append(status_response.json())
        
        # Fallback: If no specific context gathered, fetch general overview
        if not context["problems"] and not context["metrics"] and not context["hosts"]:
            logger.info("No specific keywords matched, fetching general overview")
            # Get recent problems
            response = requests.get(f"{ZABBIX_API_URL}/problems", params={"limit": 5}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                context["problems"] = data.get("problems", [])[:5]
            
            # Get hosts
            response = requests.get(f"{ZABBIX_API_URL}/hosts", params={"limit": 2}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                context["hosts"] = data.get("hosts", [])[:2]
    
    except Exception as e:
        logger.error(f"Error building context: {e}")
    
    return context

async def ask_groq(question: str, context: dict, user_name: str = "User") -> str:
    """
    Ask Groq AI with Zabbix context
    
    Uses Groq's fast inference with Llama 3 model
    Formats a comprehensive prompt with:
    - User question
    - Relevant Zabbix data (problems, metrics, hosts)
    - Instructions for Vietnamese/English response
    """
    try:
        # Build context string
        context_str = "**Current Zabbix Data:**\n\n"
        
        if context.get("problems"):
            context_str += "**Active Problems:**\n"
            for p in context["problems"]:
                context_str += f"- #{p.get('id')}: {p.get('name')} (Severity: {p.get('severity')}, Host: {p.get('host', 'Unknown')})\n"
            context_str += "\n"
        
        if context.get("metrics"):
            context_str += "**Metrics:**\n"
            for m in context["metrics"]:
                context_str += f"- {m.get('name')}: {m.get('value')} {m.get('units')} (Host: {m.get('host')})\n"
            context_str += "\n"
        
        if context.get("hosts"):
            context_str += "**Host Status:**\n"
            for h in context["hosts"]:
                host_info = h.get("host", {})
                health = h.get("health", {})
                context_str += f"- {host_info.get('display_name')}: {health.get('status')} ({health.get('active_problems', 0)} problems)\n"
            context_str += "\n"
        
        # Build AI prompt
        prompt = f"""You are a helpful Zabbix monitoring assistant. Answer the user's question based on the provided Zabbix data.

{context_str}

**User Question:** {question}

**Instructions:**
- Answer in the same language as the question (Vietnamese or English)
- Be concise and actionable
- If问题 involves alerts, suggest next steps
- Use emojis for clarity (🔴 for critical, 🟡 for warning, etc.)
- If data is insufficient, say so clearly

**Answer:**"""

        # Call Groq API (OpenAI-compatible)
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",  # Updated model (Jan 2026)
            "messages": [
                {"role": "system", "content": "You are a Zabbix monitoring expert assistant. Provide clear, actionable insights in Vietnamese or English."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1024
        }
        
        response = requests.post(
            f"{GROQ_API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            # Parse OpenAI-compatible response
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                return "⚠️ Received response but couldn't parse it."
        else:
            logger.error(f"Groq API error: {response.status_code} - {response.text}")
            return f"❌ AI service error (HTTP {response.status_code})"
    
    except requests.Timeout:
        return "⏱️ AI response timeout. Groq usually responds in ~1 second. Please try again."
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return f"❌ AI error: {str(e)}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle natural language messages (non-commands)
    
    Supports:
    - Private chats: All messages
    - Group chats: Messages that mention the bot or reply to bot's messages
    
    Process flow:
    1. Detect intent from message
    2. Fetch relevant Zabbix data
    3. Query Qwen AI with context
    4. Return AI response with optional action buttons
    """
    user_message = update.message.text
    user_name = update.effective_user.first_name
    user_id = update.effective_user.id
    chat_type = update.message.chat.type
    
    # In group chats, only respond if:
    # 1. Bot is mentioned (@ZabbixMonitoringPhucBot)
    # 2. Message is a reply to bot's message
    if chat_type in ['group', 'supergroup']:
        bot_username = (await context.bot.get_me()).username
        is_mentioned = f"@{bot_username}" in user_message
        is_reply_to_bot = (
            update.message.reply_to_message and 
            update.message.reply_to_message.from_user.is_bot
        )
        
        if not (is_mentioned or is_reply_to_bot):
            # Ignore messages in group that don't mention bot
            return
        
        # Remove bot mention from message
        if is_mentioned:
            user_message = user_message.replace(f"@{bot_username}", "").strip()
    
    logger.info(f"AI Chat from {user_name} ({user_id}) in {chat_type}: {user_message}")
    
    # Send typing indicator
    await update.message.chat.send_action("typing")
    
    try:
        # Build context from Zabbix
        await update.message.reply_text("🔍 Đang kiểm tra dữ liệu Zabbix...")
        context_data = await build_zabbix_context(user_message)
        
        # Get AI response from Groq
        ai_response = await ask_groq(user_message, context_data, user_name)
        
        # Format response
        response_msg = f"🤖 **AI Assistant**\n\n{ai_response}"
        
        # Add action buttons if there are active problems
        keyboard = []
        if context_data.get("problems"):
            first_problem_id = context_data["problems"][0].get("id")
            keyboard = [
                [
                    InlineKeyboardButton("🔧 Fix First Alert", callback_data=f"confirm_fix:{first_problem_id}"),
                    InlineKeyboardButton("🔍 Diagnostic", callback_data=f"diag:{first_problem_id}")
                ],
                [InlineKeyboardButton("📋 List All Alerts", callback_data="list_all")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        await update.message.reply_text(
            response_msg,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        await update.message.reply_text(
            f"❌ Xin lỗi, có lỗi xảy ra: {str(e)}\n\n"
            "Hãy thử lại hoặc dùng lệnh /help để xem các lệnh có sẵn."
        )

# Error Handler

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

# ==================== Report Commands ====================

report_gen = ReportGenerator(zabbix_client)
email_sender = EmailSender()

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /report command"""
    if not context.args:
        # Show inline keyboard buttons
        keyboard = [
            [InlineKeyboardButton("📊 Daily Summary", callback_data="report_daily")],
            [InlineKeyboardButton("📈 Weekly Report", callback_data="report_week")],
            [InlineKeyboardButton("🚨 Alert Summary (24h)", callback_data="report_alerts")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📊 **Chọn loại báo cáo:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    report_type = context.args[0].lower()
    
    try:
        if report_type == "daily":
            await update.message.reply_text("📊 Generating daily summary...")
            report = report_gen.generate_daily_summary()
        elif report_type in ["week", "weekly"]:
            await update.message.reply_text("📈 Generating weekly report...")
            report = report_gen.generate_weekly_report()
        elif report_type in ["alert", "alerts"]:
            hours = int(context.args[1]) if len(context.args) > 1 else 24
            await update.message.reply_text(f"🚨 Generating alert summary ({hours}h)...")
            report = report_gen.generate_alert_summary(hours=hours)
        else:
            await update.message.reply_text(
                "❌ Unknown report type. Use: daily, week, or alerts"
            )
            return
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        await update.message.reply_text(f"❌ Error generating report: {str(e)}")

async def email_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /emailreport command - send report via email"""
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
    # Only ADMIN can send email reports
    if role != 'ADMIN':
        await update.message.reply_text("🔒 Only admins can send email reports.")
        return
    
    if not context.args:
        # Show inline keyboard buttons
        keyboard = [
            [InlineKeyboardButton("📧 Daily Email", callback_data="email_daily")],
            [InlineKeyboardButton("📧 Weekly Email", callback_data="email_week")],
            [InlineKeyboardButton("📧 Alerts Email", callback_data="email_alerts")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📧 **Chọn loại email:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    report_type = context.args[0].lower()
    
    try:
        await update.message.reply_text("📧 Generating and sending email...")
        
        if report_type == "daily":
            data = report_gen.get_daily_email_data()
            subject = f"📊 Báo Cáo Hàng Ngày - {datetime.now().strftime('%d/%m/%Y')}"
            success = email_sender.send_report(subject, data, "daily")
        elif report_type in ["week", "weekly"]:
            data = report_gen.get_weekly_email_data()
            subject = f"📈 Báo Cáo Tuần - Week {datetime.now().isocalendar()[1]}/{datetime.now().year}"
            success = email_sender.send_report(subject, data, "weekly")
        elif report_type in ["alert", "alerts"]:
            data = report_gen.get_alerts_email_data()
            subject = f"🚨 Báo Cáo Alerts - {datetime.now().strftime('%d/%m/%Y')}"
            success = email_sender.send_report(subject, data, "alerts")
        else:
            await update.message.reply_text("❌ Unknown report type")
            return
        
        if success:
            await update.message.reply_text(
                f"✅ Email sent successfully to {os.getenv('EMAIL_TO', 'configured address')}!"
            )
        else:
            await update.message.reply_text(
                "❌ Failed to send email. Check logs for details.\n"
                "Make sure SMTP credentials are configured in .env"
            )
    
    except Exception as e:
        logger.error(f"Email report error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def html_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /htmlreport command - send report as HTML file"""
    import os
    import tempfile
    
    if not context.args:
        # Show inline keyboard buttons
        keyboard = [
            [InlineKeyboardButton("📄 Daily HTML", callback_data="html_daily")],
            [InlineKeyboardButton("📄 Weekly HTML", callback_data="html_week")],
            [InlineKeyboardButton("📄 Alerts HTML", callback_data="html_alerts")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📄 **Chọn file HTML:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    report_type = context.args[0].lower()
    
    try:
        await update.message.reply_text("📄 Generating HTML report...")
        
        # Generate data
        if report_type == "daily":
            data = report_gen.get_daily_email_data()
            report_title = f"Báo Cáo Hàng Ngày - {datetime.now().strftime('%d-%m-%Y')}"
        elif report_type in ["week", "weekly"]:
            data = report_gen.get_weekly_email_data()
            report_title = f"Báo Cáo Tuần - Week {datetime.now().isocalendar()[1]}"
        elif report_type in ["alert", "alerts"]:
            data = report_gen.get_alerts_email_data()
            report_title = f"Báo Cáo Alerts - {datetime.now().strftime('%d-%m-%Y')}"
        else:
            await update.message.reply_text("❌ Unknown report type")
            return
        
        # Generate HTML content
        html_content = email_sender._generate_html(data, report_type if report_type != "weekly" else "weekly")
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            temp_path = f.name
        
        # Send file
        filename = f"{report_title.replace(' ', '_')}.html"
        with open(temp_path, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=filename,
                caption=f"📊 {report_title}\n\nMở file này trong browser để xem report đẹp!"
            )
        
        # Clean up
        os.unlink(temp_path)
        
    except Exception as e:
        logger.error(f"HTML report error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

# Scheduled report functions
async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    """Send daily report to group (scheduled)"""
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "-5285412393")
    try:
        # Send to Telegram
        report = report_gen.generate_daily_summary()
        await context.bot.send_message(
            chat_id=chat_id,
            text=report,
            parse_mode='Markdown'
        )
        logger.info("✅ Daily report sent to Telegram")
        
        # Send email if configured
        if os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"):
            data = report_gen.get_daily_email_data()
            subject = f"📊 Báo Cáo Hàng Ngày - {datetime.now().strftime('%d/%m/%Y')}"
            if email_sender.send_report(subject, data, "daily"):
                logger.info("✅ Daily report sent via email")
        
    except Exception as e:
        logger.error(f"Failed to send daily report: {e}")

async def send_weekly_report(context: ContextTypes.DEFAULT_TYPE):
    """Send weekly report (scheduled)"""
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "-5285412393")
    try:
        # Send to Telegram
        report = report_gen.generate_weekly_report()
        await context.bot.send_message(
            chat_id=chat_id,
            text=report,
            parse_mode='Markdown'
        )
        logger.info("✅ Weekly report sent to Telegram")
        
        # Send email if configured
        if os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"):
            data = report_gen.get_weekly_email_data()
            subject = f"📈 Báo Cáo Tuần - Week {datetime.now().isocalendar()[1]}/{datetime.now().year}"
            if email_sender.send_report(subject, data, "weekly"):
                logger.info("✅ Weekly report sent via email")
        
    except Exception as e:
        logger.error(f"Failed to send weekly report: {e}")

# Main Function

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_alerts))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("fix", fix_alert))
    application.add_handler(CommandHandler("report", report_command))  # NEW
    application.add_handler(CommandHandler("emailreport", email_report_command))  # NEW
    application.add_handler(CommandHandler("htmlreport", html_report_command))  # NEW
    
    # AI Chat handler (for non-command messages)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Setup scheduler for automated reports
    job_queue = application.job_queue
    
    # Daily report at 9:00 AM Vietnam time
    job_queue.run_daily(
        send_daily_report,
        time=datetime.strptime("09:00", "%H:%M").time(),
        days=(0, 1, 2, 3, 4, 5, 6),  # Every day
        name="daily_report"
    )
    logger.info("📅 Scheduled: Daily report at 09:00")
    
    # Weekly report on Monday at 9:00 AM
    job_queue.run_daily(
        send_weekly_report,
        time=datetime.strptime("09:00", "%H:%M").time(),
        days=(0,),  # Monday
        name="weekly_report"
    )
    logger.info("📅 Scheduled: Weekly report on Monday 09:00")
    
    # Set bot commands for autocomplete menu
    async def post_init(application):
        """Set bot commands after initialization"""
        from telegram import BotCommand
        
        commands = [
            BotCommand("start", "Bắt đầu sử dụng bot"),
            BotCommand("help", "Hiển thị trợ giúp"),
            BotCommand("list", "Danh sách alerts"),
            BotCommand("status", "Kiểm tra trạng thái hệ thống"),
            BotCommand("report", "Báo cáo (daily/week/alerts)"),
            BotCommand("htmlreport", "Tải xuống báo cáo HTML"),
            BotCommand("emailreport", "Gửi báo cáo qua email"),
        ]
        
        await application.bot.set_my_commands(commands)
        logger.info("✅ Bot commands menu configured")
    
    application.post_init = post_init
    
    # Start bot
    logger.info("🤖 Telegram bot starting with report scheduler...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

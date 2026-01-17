"""
Report Generator for Zabbix Telegram Bot
Generates various types of monitoring reports
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List
import logging
from collections import Counter

logger = logging.getLogger(__name__)

ZABBIX_API_URL = os.getenv("ZABBIX_API_URL", "http://zabbix-api-connector:8000")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_BASE = "https://api.groq.com/openai/v1"


class ReportGenerator:
    def __init__(self):
        self.zabbix_url = ZABBIX_API_URL
    
    def generate_daily_summary(self) -> str:
        """
        Daily Summary Report
        
        Contains:
        - Total alerts in last 24h
        - Active alerts by severity
        - Top 3 hosts with most problems
        - System health overview
        """
        # Fetch data from Zabbix
        problems = self._get_recent_problems()
        hosts = self._get_host_summary()
        
        # AI analysis via Groq
        ai_insights = self._get_ai_insights(problems, "daily")
        
        # Format report
        report = f"""📊 **Báo Cáo Hàng Ngày - {datetime.now().strftime('%Y-%m-%d')}**

━━━━━━━━━━━━━━━━━━━━━━━━

🔔 **Tổng Quan Alerts (24h qua)**
• Tổng số alerts: {len(problems)}
• Disaster: {self._count_by_severity(problems, 'Disaster')} 🔴
• High: {self._count_by_severity(problems, 'High')} 🟠
• Average: {self._count_by_severity(problems, 'Average')} 🟡
• Warning: {self._count_by_severity(problems, 'Warning')} 🟢

🖥️ **Top Hosts Có Vấn Đề**
{self._format_top_hosts(problems, limit=3)}

🌐 **System Overview**
• Total Hosts: {len(hosts)}
• Monitored: {sum(1 for h in hosts if h.get('status') == 'monitored')}

💡 **AI Analysis**
{ai_insights}

━━━━━━━━━━━━━━━━━━━━━━━━
📅 Report Time: {datetime.now().strftime('%H:%M:%S')}
"""
        return report
    
    def generate_weekly_report(self) -> str:
        """
        Weekly Performance Report
        
        Contains:
        - Alert trends
        - Host performance
        - Most common issues
        """
        problems = self._get_recent_problems()
        
        report = f"""📈 **Báo Cáo Tuần - Week {datetime.now().isocalendar()[1]}/{datetime.now().year}**

━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Alert Overview (7 ngày qua)**
• Total Alerts: {len(problems)}
• Disaster: {self._count_by_severity(problems, 'Disaster')} 🔴
• High: {self._count_by_severity(problems, 'High')} 🟠
• Average: {self._count_by_severity(problems, 'Average')} 🟡

🎯 **Top Alert Types**
{self._get_common_alert_types(problems, limit=5)}

✅ **Response Status**
• Acknowledged: {self._count_ack(problems)}
• Unacknowledged: {self._count_unack(problems)}

🖥️ **Most Affected Hosts**
{self._format_top_hosts(problems, limit=5)}

━━━━━━━━━━━━━━━━━━━━━━━━
📅 Period: {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} → {datetime.now().strftime('%Y-%m-%d')}
"""
        return report
    
    def generate_alert_summary(self, hours: int = 24) -> str:
        """
        Alert Summary Report (On-Demand)
        
        Tổng hợp alerts theo severity và status
        """
        problems = self._get_recent_problems()
        
        report = f"""🚨 **Báo Cáo Tổng Hợp Alerts**

━━━━━━━━━━━━━━━━━━━━━━━━

⏰ **Khoảng thời gian**: {hours} giờ qua

📋 **Theo Mức Độ**
{self._breakdown_by_severity(problems)}

✅ **Theo Trạng Thái**
• Đã xác nhận: {self._count_ack(problems)} ✓
• Chưa xác nhận: {self._count_unack(problems)} ⚠️

🖥️ **Theo Host (Top 5)**
{self._breakdown_by_host(problems, limit=5)}

📊 **Thống Kê**
• Tổng số alerts: {len(problems)}
• Trung bình/ngày: {len(problems) / (hours / 24):.1f}

━━━━━━━━━━━━━━━━━━━━━━━━
Tạo lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return report
    
    # ==================== Helper Methods ====================
    
    def _get_recent_problems(self) -> List[Dict]:
        """Fetch problems from Zabbix API"""
        try:
            response = requests.get(
                f"{self.zabbix_url}/problems",
                params={"limit": 100},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("problems", [])
            logger.error(f"Zabbix API error: {response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error fetching problems: {e}")
            return []
    
    def _get_host_summary(self) -> List[Dict]:
        """Get host summary"""
        try:
            response = requests.get(f"{self.zabbix_url}/hosts", timeout=10)
            if response.status_code == 200:
                return response.json().get("hosts", [])
            return []
        except Exception as e:
            logger.error(f"Error fetching hosts: {e}")
            return []
    
    def _count_by_severity(self, problems: List[Dict], severity: str) -> int:
        """Count problems by severity"""
        return sum(1 for p in problems if p.get("severity") == severity)
    
    def _format_top_hosts(self, problems: List[Dict], limit: int = 3) -> str:
        """Format top hosts with most problems"""
        hosts = [p.get("host", "Unknown") for p in problems]
        top = Counter(hosts).most_common(limit)
        
        if not top:
            return "No problems found"
        
        result = ""
        for i, (host, count) in enumerate(top, 1):
            result += f"{i}. {host}: {count} alerts\n"
        return result.strip()
    
    def _get_common_alert_types(self, problems: List[Dict], limit: int = 5) -> str:
        """Get most common alert types"""
        alert_names = [p.get("name", "Unknown")[:50] for p in problems]  # Truncate long names
        common = Counter(alert_names).most_common(limit)
        
        if not common:
            return "No alerts"
        
        result = ""
        for i, (name, count) in enumerate(common, 1):
            result += f"{i}. {name}: {count}x\n"
        return result.strip()
    
    def _count_ack(self, problems: List[Dict]) -> int:
        """Count acknowledged problems"""
        return sum(1 for p in problems if p.get("acknowledged", False))
    
    def _count_unack(self, problems: List[Dict]) -> int:
        """Count unacknowledged problems"""
        return sum(1 for p in problems if not p.get("acknowledged", False))
    
    def _breakdown_by_severity(self, problems: List[Dict]) -> str:
        """Breakdown alerts by severity"""
        result = ""
        severity_vn = {
            "Disaster": "Thảm họa",
            "High": "Cao",
            "Average": "Trung bình",
            "Warning": "Cảnh báo",
            "Information": "Thông tin"
        }
        for severity, emoji in [
            ("Disaster", "🔴"),
            ("High", "🟠"),
            ("Average", "🟡"),
            ("Warning", "🟢"),
            ("Information", "🔵")
        ]:
            count = self._count_by_severity(problems, severity)
            if count > 0:
                result += f"• {severity_vn[severity]}: {count} {emoji}\n"
        return result.strip() or "Không có alerts"
    
    def _breakdown_by_host(self, problems: List[Dict], limit: int = 5) -> str:
        """Breakdown alerts by host"""
        hosts = [p.get("host", "Unknown") for p in problems]
        top = Counter(hosts).most_common(limit)
        
        if not top:
            return "Không có dữ liệu"
        
        result = ""
        for i, (host, count) in enumerate(top, 1):
            result += f"{i}. {host}: {count}\n"
        return result.strip()
    
    def _get_ai_insights(self, problems: List[Dict], report_type: str) -> str:
        """Get AI insights from Groq"""
        if not problems or not GROQ_API_KEY:
            return "AI insights not available (no data or API key missing)"
        
        # Summarize problems for AI
        summary = f"{len(problems)} alerts total. "
        summary += f"Disaster: {self._count_by_severity(problems, 'Disaster')}, "
        summary += f"High: {self._count_by_severity(problems, 'High')}, "
        summary += f"Average: {self._count_by_severity(problems, 'Average')}"
        
        prompt = f"""Analyze this Zabbix monitoring data briefly (max 3 sentences, Vietnamese):
Data: {summary}
Report type: {report_type}

Provide actionable insights and recommendations."""
        
        try:
            response = requests.post(
                f"{GROQ_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "You are a Zabbix expert. Provide brief, actionable insights in Vietnamese."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 150,
                    "temperature": 0.7
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"Groq API error: {response.status_code}")
                return "AI analysis temporarily unavailable"
                
        except Exception as e:
            logger.error(f"AI insights error: {e}")
            return "AI analysis error"
    
    # ==================== Email Data Generation ====================
    
    def get_daily_email_data(self) -> dict:
        """Generate data structure for daily email"""
        problems = self._get_recent_problems()
        hosts = self._get_host_summary()
        
        # Prepare data
        data = {
            'total_alerts': len(problems),
            'disaster': self._count_by_severity(problems, 'Disaster'),
            'high': self._count_by_severity(problems, 'High'),
            'average': self._count_by_severity(problems, 'Average'),
            'warning': self._count_by_severity(problems, 'Warning'),
            'top_hosts': self._get_top_hosts_list(problems, limit=5),
            'ai_insights': self._get_ai_insights(problems, 'daily'),
            'total_hosts': len(hosts),
            'monitored_hosts': sum(1 for h in hosts if h.get('status') == 'monitored')
        }
        return data
    
    def get_weekly_email_data(self) -> dict:
        """Generate data structure for weekly email"""
        problems = self._get_recent_problems()
        
        data = {
            'total_alerts': len(problems),
            'disaster': self._count_by_severity(problems, 'Disaster'),
            'high': self._count_by_severity(problems, 'High'),
            'average': self._count_by_severity(problems, 'Average'),
            'period': f"{(datetime.now() - timedelta(days=7)).strftime('%d/%m')} - {datetime.now().strftime('%d/%m/%Y')}",
            'top_hosts': self._get_top_hosts_list(problems, limit=5),
            'top_types': self._get_common_types_list(problems, limit=5)
        }
        return data
    
    def get_alerts_email_data(self, hours: int = 24) -> dict:
        """Generate data structure for alerts email"""
        problems = self._get_recent_problems()
        
        data = {
            'total_alerts': len(problems),
            'disaster': self._count_by_severity(problems, 'Disaster'),
            'high': self._count_by_severity(problems, 'High'),
            'average': self._count_by_severity(problems, 'Average'),
            'warning': self._count_by_severity(problems, 'Warning'),
            'top_hosts': self._get_top_hosts_list(problems, limit=5),
            'ai_insights': self._get_ai_insights(problems, 'alerts'),
            'hours': hours
        }
        return data
    
    def _get_top_hosts_list(self, problems: List[Dict], limit: int = 5) -> List[tuple]:
        """Get top hosts as list of tuples for email"""
        hosts = [p.get("host", "Unknown") for p in problems]
        return Counter(hosts).most_common(limit)
    
    def _get_common_types_list(self, problems: List[Dict], limit: int = 5) -> List[tuple]:
        """Get common alert types as list for email"""
        alert_names = [p.get("name", "Unknown")[:50] for p in problems]
        return Counter(alert_names).most_common(limit)

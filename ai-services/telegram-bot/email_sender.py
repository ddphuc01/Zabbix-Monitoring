"""
Email sender for Zabbix reports
Sends beautiful HTML emails with monitoring data
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
EMAIL_TO = os.getenv("EMAIL_TO", "phuc.alert02@gmail.com")


class EmailSender:
    def __init__(self):
        self.smtp_server = SMTP_SERVER
        self.smtp_port = SMTP_PORT
        self.smtp_user = SMTP_USER
        self.smtp_password = SMTP_PASSWORD
        self.email_from = EMAIL_FROM
        self.email_to = EMAIL_TO
    
    def send_report(self, subject: str, report_data: dict, report_type: str = "daily"):
        """
        Send HTML email report
        
        Args:
            subject: Email subject
            report_data: Dictionary containing report data
            report_type: Type of report (daily, weekly, alerts)
        """
        try:
            # Generate HTML content
            html_content = self._generate_html(report_data, report_type)
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✅ Email sent successfully to {self.email_to}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email send failed: {e}")
            return False
    
    def _generate_html(self, data: dict, report_type: str) -> str:
        """Generate beautiful HTML email"""
        
        if report_type == "daily":
            return self._daily_html(data)
        elif report_type == "weekly":
            return self._weekly_html(data)
        elif report_type == "alerts":
            return self._alerts_html(data)
        else:
            return self._generic_html(data)
    
    def _daily_html(self, data: dict) -> str:
        """HTML template for daily report"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1a73e8;
            border-bottom: 3px solid #1a73e8;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        h2 {{
            color: #5f6368;
            margin-top: 25px;
            font-size: 18px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-card.disaster {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .stat-card.high {{
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        }}
        .stat-card.average {{
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            color: #333;
        }}
        .stat-card.warning {{
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
            color: #333;
        }}
        .stat-number {{
            font-size: 36px;
            font-weight: bold;
            margin: 0;
        }}
        .stat-label {{
            font-size: 14px;
            opacity: 0.9;
            margin-top: 5px;
        }}
        .table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        .table th {{
            background: #f1f3f4;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #dadce0;
        }}
        .table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e8eaed;
        }}
        .ai-insight {{
            background: #e8f0fe;
            border-left: 4px solid #1a73e8;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e8eaed;
            text-align: center;
            color: #5f6368;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Báo Cáo Hàng Ngày - {datetime.now().strftime('%d/%m/%Y')}</h1>
        
        <h2>🔔 Tổng Quan Alerts (24h qua)</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <p class="stat-number">{data.get('total_alerts', 0)}</p>
                <p class="stat-label">Tổng Alerts</p>
            </div>
            <div class="stat-card disaster">
                <p class="stat-number">{data.get('disaster', 0)}</p>
                <p class="stat-label">Thảm Họa</p>
            </div>
            <div class="stat-card high">
                <p class="stat-number">{data.get('high', 0)}</p>
                <p class="stat-label">Cao</p>
            </div>
            <div class="stat-card average">
                <p class="stat-number">{data.get('average', 0)}</p>
                <p class="stat-label">Trung Bình</p>
            </div>
            <div class="stat-card warning">
                <p class="stat-number">{data.get('warning', 0)}</p>
                <p class="stat-label">Cảnh Báo</p>
            </div>
        </div>
        
        <h2>🖥️ Top Hosts Có Vấn Đề</h2>
        <table class="table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Host</th>
                    <th>Số Alerts</th>
                </tr>
            </thead>
            <tbody>
                {self._format_top_hosts_html(data.get('top_hosts', []))}
            </tbody>
        </table>
        
        <h2>💡 AI Analysis</h2>
        <div class="ai-insight">
            {data.get('ai_insights', 'Không có phân tích AI')}
        </div>
        
        <div class="footer">
            <p>Báo cáo tự động từ Zabbix Monitoring System</p>
            <p>Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _weekly_html(self, data: dict) -> str:
        """HTML template for weekly report"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #34a853;
            border-bottom: 3px solid #34a853;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #5f6368;
            margin-top: 25px;
        }}
        .highlight-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        .table th {{
            background: #f1f3f4;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        .table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e8eaed;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e8eaed;
            text-align: center;
            color: #5f6368;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 Báo Cáo Tuần - Week {datetime.now().isocalendar()[1]}/{datetime.now().year}</h1>
        
        <div class="highlight-box">
            <h3 style="margin-top:0;">Tổng Số Alerts: {data.get('total_alerts', 0)}</h3>
            <p>Khoảng thời gian: {data.get('period', '7 ngày qua')}</p>
        </div>
        
        <h2>🎯 Top Alert Types</h2>
        <table class="table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Alert Type</th>
                    <th>Số lần</th>
                </tr>
            </thead>
            <tbody>
                {self._format_alert_types_html(data.get('top_types', []))}
            </tbody>
        </table>
        
        <h2>🖥️ Hosts Ảnh Hưởng Nhiều Nhất</h2>
        <table class="table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Host</th>
                    <th>Alerts</th>
                </tr>
            </thead>
            <tbody>
                {self._format_top_hosts_html(data.get('top_hosts', []))}
            </tbody>
        </table>
        
        <div class="footer">
            <p>Báo cáo tuần từ Zabbix Monitoring System</p>
            <p>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _alerts_html(self, data: dict) -> str:
        """HTML template for alerts summary - Red theme, severity focused"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #ffeef0 0%, #fff5f5 100%);
        }}
        .container {{
            background: white;
            border-radius: 12px;
            padding: 35px;
            box-shadow: 0 4px 6px rgba(234, 67, 53, 0.1);
            border: 2px solid #fce4e4;
        }}
        h1 {{
            color: #ea4335;
            border-bottom: 4px solid #ea4335;
            padding-bottom: 12px;
            margin-top: 0;
            font-size: 28px;
            display: flex;
            align-items: center;
        }}
        h2 {{
            color: #d33b2c;
            margin-top: 30px;
            font-size: 20px;
            border-left: 4px solid #ea4335;
            padding-left: 12px;
        }}
        .alert-header {{
            background: linear-gradient(135deg, #ea4335 0%, #d33b2c 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }}
        .alert-header h3 {{
            margin: 0;
            font-size: 24px;
        }}
        .alert-header p {{
            margin: 10px 0 0 0;
            opacity: 0.95;
            font-size: 16px;
        }}
        .severity-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 25px 0;
        }}
        .severity-card {{
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .severity-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        .severity-card.disaster {{
            background: linear-gradient(135deg, #d93025 0%, #a50e0e 100%);
            color: white;
        }}
        .severity-card.high {{
            background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
            color: white;
        }}
        .severity-card.average {{
            background: linear-gradient(135deg, #fbbc04 0%, #f9ab00 100%);
            color: #333;
        }}
        .severity-card.warning {{
            background: linear-gradient(135deg, #34a853 0%, #0f9d58 100%);
            color: white;
        }}
        .severity-number {{
            font-size: 42px;
            font-weight: bold;
            margin: 0;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .severity-label {{
            font-size: 15px;
            margin-top: 8px;
            font-weight: 500;
        }}
        .info-box {{
            background: #f8f9fa;
            border-left: 4px solid #ea4335;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .info-box strong {{
            color: #ea4335;
        }}
        .table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .table thead {{
            background: linear-gradient(135deg, #ea4335 0%, #d33b2c 100%);
            color: white;
        }}
        .table th {{
            padding: 14px 12px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
        }}
        .table td {{
            padding: 12px;
            border-bottom: 1px solid #e8eaed;
        }}
        .table tbody tr:hover {{
            background: #fff5f5;
        }}
        .stats-row {{
            display: flex;
            justify-content: space-around;
            margin: 25px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-item .number {{
            font-size: 32px;
            font-weight: bold;
            color: #ea4335;
        }}
        .stat-item .label {{
            font-size: 13px;
            color: #5f6368;
            margin-top: 5px;
        }}
        .footer {{
            margin-top: 35px;
            padding-top: 20px;
            border-top: 2px solid #fce4e4;
            text-align: center;
            color: #5f6368;
            font-size: 12px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge.critical {{
            background: #d93025;
            color: white;
        }}
        .badge.warning {{
            background: #fbbc04;
            color: #333;
        }}
        .badge.ok {{
            background: #34a853;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚨 Báo Cáo Alerts Chi Tiết</h1>
        
        <div class="alert-header">
            <h3>Tổng Số Alerts: {data.get('total_alerts', 0)}</h3>
            <p>Thời gian phân tích: {data.get('period', 'Không xác định')}</p>
        </div>
        
        <h2>📊 Phân Loại Theo Mức Độ Nghiêm Trọng</h2>
        <div class="severity-grid">
            <div class="severity-card disaster">
                <p class="severity-number">{data.get('disaster', 0)}</p>
                <p class="severity-label">🔴 THẢM HỌA</p>
            </div>
            <div class="severity-card high">
                <p class="severity-number">{data.get('high', 0)}</p>
                <p class="severity-label">🟠 CAO</p>
            </div>
            <div class="severity-card average">
                <p class="severity-number">{data.get('average', 0)}</p>
                <p class="severity-label">🟡 TRUNG BÌNH</p>
            </div>
            <div class="severity-card warning">
                <p class="severity-number">{data.get('warning', 0)}</p>
                <p class="severity-label">🟢 CẢNH BÁO</p>
            </div>
        </div>
        
        <div class="info-box">
            <strong>Phân tích nhanh:</strong> 
            {self._generate_alert_analysis(data)}
        </div>
        
        <h2>📈 Thống Kê Tổng Quan</h2>
        <div class="stats-row">
            <div class="stat-item">
                <div class="number">{data.get('total_alerts', 0)}</div>
                <div class="label">Tổng Alerts</div>
            </div>
            <div class="stat-item">
                <div class="number">{data.get('acknowledged', 0)}</div>
                <div class="label">Đã Xác Nhận</div>
            </div>
            <div class="stat-item">
                <div class="number">{data.get('unacknowledged', 0)}</div>
                <div class="label">Chưa Xử Lý</div>
            </div>
            <div class="stat-item">
                <div class="number">{len(data.get('top_hosts', []))}</div>
                <div class="label">Hosts Ảnh Hưởng</div>
            </div>
        </div>
        
        <h2>🖥️ Top Hosts Cần Chú Ý</h2>
        <table class="table">
            <thead>
                <tr>
                    <th>Thứ Tự</th>
                    <th>Tên Host</th>
                    <th>Số Alerts</th>
                    <th>Mức Độ</th>
                </tr>
            </thead>
            <tbody>
                {self._format_hosts_with_severity(data.get('top_hosts', []))}
            </tbody>
        </table>
        
        <div class="footer">
            <p><strong>Zabbix Alert Analysis System</strong></p>
            <p>Tạo lúc: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</p>
            <p style="margin-top: 8px; color: #ea4335;">⚠️ Priorities: Disaster → High → Average → Warning</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _generic_html(self, data: dict) -> str:
        """Generic HTML template"""
        return self._daily_html(data)
    
    def _format_top_hosts_html(self, hosts: list) -> str:
        """Format top hosts as HTML table rows"""
        if not hosts:
            return '<tr><td colspan="3">Không có dữ liệu</td></tr>'
        
        rows = ""
        for i, (host, count) in enumerate(hosts, 1):
            rows += f"<tr><td>{i}</td><td>{host}</td><td><strong>{count}</strong></td></tr>"
        return rows
    
    def _format_alert_types_html(self, types: list) -> str:
        """Format alert types as HTML table rows"""
        if not types:
            return '<tr><td colspan="3">Không có dữ liệu</td></tr>'
        
        rows = ""
        for i, (alert_type, count) in enumerate(types, 1):
            rows += f"<tr><td>{i}</td><td>{alert_type}</td><td><strong>{count}x</strong></td></tr>"
        return rows

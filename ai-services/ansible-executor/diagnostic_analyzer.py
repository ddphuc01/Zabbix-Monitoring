#!/usr/bin/env python3
"""
Diagnostic Analyzer - AI analyzes diagnostic data from Ansible
Enhances Gemini analysis with real host data
"""

import logging
from typing import Dict
import google.generativeai as genai

logger = logging.getLogger(__name__)


class DiagnosticAnalyzer:
    """Analyze alerts with diagnostic data using Gemini"""
    
    def __init__(self, gemini_model):
        self.model = gemini_model
        logger.info("✅ DiagnosticAnalyzer initialized")
    
    async def analyze_with_diagnostics(
        self, 
        alert_data: Dict, 
        diagnostic_data: Dict
    ) -> Dict:
        """
        Analyze alert with full diagnostic context from Ansible
        
        Args:
            alert_data: Original Zabbix alert
                {
                    'trigger': 'CPU > 95%',
                    'host': 'web-server',
                    'severity': 'High',
                    'value': '97%',
                    'time': '2026-01-05 20:00:00'
                }
            
            diagnostic_data: Data collected by Ansible
                {
                    'success': True,
                    'hostname': 'web-server',
                    'data': {
                        'top_processes': [...],
                        'load_average': '15.32 8.21 3.45',
                        ...
                    }
                }
        
        Returns:
            Enhanced AI analysis with specific recommendations
        """
        
        if not diagnostic_data.get('success'):
            logger.warning("⚠️  Diagnostic failed, falling back to basic analysis")
            return await self._basic_analysis(alert_data)
        
        try:
            # Build enhanced prompt
            enhanced_prompt = self._build_enhanced_prompt(alert_data, diagnostic_data)
            
            logger.info("🤖 Calling Gemini with diagnostic context...")
            
            # Call Gemini with enhanced context
            response = self.model.generate_content(
                enhanced_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1500,
                    temperature=0.3,
                )
            )
            
            # Parse response
            analysis = self._parse_gemini_response(response.text)
            analysis['diagnostic_used'] = True
            analysis['diagnostic_host'] = diagnostic_data.get('hostname')
            
            logger.info("✅ Enhanced analysis complete")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Diagnostic analysis error: {e}")
            return await self._basic_analysis(alert_data)
    
    def _build_enhanced_prompt(self, alert_data: Dict, diagnostic_data: Dict) -> str:
        """Build enhanced prompt with diagnostic data"""
        
        diag = diagnostic_data.get('data', {})
        
        # Format diagnostic data for AI
        diagnostic_summary = self._format_diagnostic_data(diag)
        
        prompt = f"""BẠN LÀ SENIOR SYSADMIN đang troubleshoot REALTIME.

ALERT HIỆN TẠI:
- Trigger: {alert_data.get('trigger')}
- Host: {alert_data.get('host')} 
- Severity: {alert_data.get('severity')}
- Value: {alert_data.get('value')}
- Time: {alert_data.get('time')}

✅ ĐÃ THU THẬP DIAGNOSTIC DATA TỰ ĐỘNG TỪ HOST:

{diagnostic_summary}

NHIỆM VỤ:
Phân tích với DATA THỰC TẾ này và đưa ra:
1. Root cause CỤ THỂ (dựa trên processes/metrics thực tế)
2. Commands FIX NGAY (với PID, service names chính xác)
3. Verify steps

Response format JSON:
{{
  "summary": "Vấn đề cụ thể - 1 câu ngắn",
  "root_cause": "Root cause XÁC ĐỊNH từ data:\\n- Điểm 1\\n- Điểm 2",
  "severity_assessment": "Mức độ và lý do",
  "immediate_action": "Fix steps CỤ THỂ:\\n1. ssh {alert_data.get('host')}\\n2. command với PID/service thực tế\\n3. verify",
  "preventive_measures": "Phòng ngừa:\\n- Action 1\\n- Action 2",
  "related_metrics": "Metrics cần check:\\n- metric1\\n- metric2",
  "confidence": 0.9
}}

CRITICAL: Dùng DATA THỰC TẾ từ diagnostic, KHÔNG generic suggestions!
"""
        
        return prompt
    
    def _format_diagnostic_data(self, diag: Dict) -> str:
        """Format diagnostic data for AI prompt"""
        
        formatted = []
        
        # Top processes
        if 'top_processes' in diag:
            processes = diag['top_processes'][:5]  # Top 5
            formatted.append("TOP PROCESSES (CPU):")
            for proc in processes:
                formatted.append(f"  {proc}")
        
        # Load average
        if 'load_average' in diag:
            formatted.append(f"\nLOAD AVERAGE: {diag['load_average']}")
        
        # High CPU processes (>50%)
        if 'high_cpu_processes' in diag and diag['high_cpu_processes']:
            formatted.append("\nPROCESSES >50% CPU:")
            for proc in diag['high_cpu_processes'][:3]:
                formatted.append(f"  {proc}")
        
        # Process count
        if 'process_count' in diag:
            formatted.append(f"\nTOTAL PROCESSES: {diag['process_count']}")
        
        # CPU info
        if 'cpu_info' in diag:
            formatted.append("\nCPU INFO:")
            for info in diag['cpu_info'][:3]:
                formatted.append(f"  {info}")
        
        # CPU frequency
        if 'cpu_frequency' in diag:
            formatted.append("\nCPU FREQUENCY:")
            for freq in diag['cpu_frequency'][:2]:
                formatted.append(f"  {freq}")
        
        # Recent logs
        if 'recent_logs' in diag and diag['recent_logs']:
            formatted.append("\nRECENT LOGS (CPU-related):")
            for log in diag['recent_logs'][:3]:
                formatted.append(f"  {log}")
        
        return "\n".join(formatted)
    
    def _parse_gemini_response(self, text: str) -> Dict:
        """Parse Gemini JSON response"""
        
        import json
        import re
        
        try:
            # Clean markdown if present
            cleaned = text
            if '```json' in text:
                cleaned = re.sub(r'```json\n?', '', text)
                cleaned = re.sub(r'\n?```', '', cleaned)
            elif '```' in text:
                cleaned = re.sub(r'```\n?', '', text)
                cleaned = re.sub(r'\n?```', '', cleaned)
            
            # Parse JSON
            parsed = json.loads(cleaned.strip())
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse error: {e}")
            # Fallback
            return {
                'summary': 'Analysis completed',
                'root_cause': text[:500],
                'immediate_action': 'Check diagnostic data manually',
                'confidence': 0.5,
                'parse_error': True
            }
    
    async def _basic_analysis(self, alert_data: Dict) -> Dict:
        """Fallback to basic analysis without diagnostic data"""
        
        logger.info("📊 Using basic analysis (no diagnostic data)")
        
        # Simple prompt without diagnostic context
        basic_prompt = f"""Phân tích alert Zabbix:
- {alert_data.get('trigger')} 
- Host: {alert_data.get('host')}
- Severity: {alert_data.get('severity')}

Đưa ra root cause có thể và fix steps chung."""
        
        try:
            response = self.model.generate_content(basic_prompt)
            return {
                'summary': f"Analysis for {alert_data.get('trigger')}",
                'root_cause': response.text[:500],
                'immediate_action': 'Investigate manually',
                'confidence': 0.6,
                'diagnostic_used': False
            }
        except Exception as e:
            logger.error(f"❌ Basic analysis error: {e}")
            return {
                'summary': 'AI analysis unavailable',
                'root_cause': 'Unable to analyze',
                'immediate_action': 'Manual investigation required',
                'confidence': 0.0
            }

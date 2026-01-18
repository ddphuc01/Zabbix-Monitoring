"""
Unit tests for AI Webhook Handler
Tests the webhook.py functionality including Groq integration and caching
"""
import pytest
import json
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add ai-services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../ai-services/webhook-handler'))


class TestCacheManager:
    """Test CacheManager class"""
    
    def test_get_cache_key_generates_consistent_hash(self, sample_zabbix_alert):
        """Test that same alert data generates same cache key"""
        from webhook import CacheManager
        
        key1 = CacheManager.get_cache_key(sample_zabbix_alert)
        key2 = CacheManager.get_cache_key(sample_zabbix_alert)
        
        assert key1 == key2
        assert key1.startswith('groq:')
    
    def test_get_cache_key_different_for_different_alerts(self, sample_zabbix_alert):
        """Test that different alerts generate different cache keys"""
        from webhook import CacheManager
        
        alert2 = sample_zabbix_alert.copy()
        alert2['trigger'] = 'Different alert'
        
        key1 = CacheManager.get_cache_key(sample_zabbix_alert)
        key2 = CacheManager.get_cache_key(alert2)
        
        assert key1 != key2


class TestGroqAnalyzer:
    """Test GroqAnalyzer class"""
    
    def test_determine_alert_type_cpu(self):
        """Test CPU alert detection"""
        from webhook import GroqAnalyzer
        
        assert GroqAnalyzer.determine_alert_type('High CPU usage') == 'CPU'
        assert GroqAnalyzer.determine_alert_type('Load average too high') == 'CPU'
    
    def test_determine_alert_type_memory(self):
        """Test Memory alert detection"""
        from webhook import GroqAnalyzer
        
        assert GroqAnalyzer.determine_alert_type('Memory usage high') == 'MEMORY'
        assert GroqAnalyzer.determine_alert_type('SWAP usage critical') == 'MEMORY'
        assert GroqAnalyzer.determine_alert_type('Low RAM available') == 'MEMORY'
    
    def test_determine_alert_type_disk(self):
        """Test Disk alert detection"""
        from webhook import GroqAnalyzer
        
        assert GroqAnalyzer.determine_alert_type('Disk space low') == 'DISK'
        assert GroqAnalyzer.determine_alert_type('/ volume 95% full') == 'DISK'
    
    def test_determine_alert_type_network(self):
        """Test Network alert detection"""
        from webhook import GroqAnalyzer
        
        assert GroqAnalyzer.determine_alert_type('Network interface down') == 'NETWORK'
        assert GroqAnalyzer.determine_alert_type('High bandwidth usage') == 'NETWORK'
    
    def test_determine_alert_type_unknown(self):
        """Test unknown alert type"""
        from webhook import GroqAnalyzer
        
        assert GroqAnalyzer.determine_alert_type('Some random alert') == 'UNKNOWN'
    
    def test_extract_service_info_production(self):
        """Test service info extraction for production"""
        from webhook import GroqAnalyzer
        
        alert_data = {'severity': 'critical'}
        info = GroqAnalyzer.extract_service_info('prod-web-01', alert_data)
        
        assert info['environment'] == 'production'
        assert info['app_type'] == 'web'
        assert info['expected_load'] == 'critical'
    
    def test_extract_service_info_staging(self):
        """Test service info extraction for staging"""
        from webhook import GroqAnalyzer
        
        alert_data = {'severity': 'high'}
        info = GroqAnalyzer.extract_service_info('staging-db-01', alert_data)
        
        assert info['environment'] == 'staging'
        assert info['app_type'] == 'database'
        assert info['expected_load'] == 'high'
    
    @patch('webhook.groq_client')
    def test_analyze_with_ansible_data(self, mock_groq, sample_zabbix_alert, sample_ansible_output):
        """Test analyze function with Ansible data"""
        from webhook import GroqAnalyzer
        
        # Setup mock
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content='AI analysis'))]
        mock_groq.chat.completions.create.return_value = mock_completion
        
        result = GroqAnalyzer.analyze(sample_zabbix_alert, sample_ansible_output)
        
        assert 'analysis' in result
        assert result['analysis'] == 'AI analysis'
        assert result['model'] == 'llama-3.3-70b-versatile'
    
    @patch('webhook.groq_client', None)
    def test_analyze_without_groq_client(self, sample_zabbix_alert):
        """Test analyze when Groq client not initialized"""
        from webhook import GroqAnalyzer
        
        result = GroqAnalyzer.analyze(sample_zabbix_alert)
        
        assert 'error' in result


class TestWebhookEndpoints:
    """Test Flask webhook endpoints"""
    
    @patch('webhook.GROQ_API_KEY', 'test_key')
    def test_health_endpoint(self, mock_env_vars):
        """Test /health endpoint returns status"""
        # This is a placeholder - full implementation would need Flask test client
        # For now, just test the logic
        pass
    
    def test_webhook_endpoint_requires_groq_key(self):
        """Test webhook endpoint validation"""
        # Placeholder for webhook endpoint testing
        pass


class TestAnsibleExecutor:
    """Test AnsibleExecutor class"""
    
    @patch('webhook.requests.post')
    def test_run_diagnostics_success(self, mock_post):
        """Test successful diagnostic execution"""
        from webhook import AnsibleExecutor
        
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'success',
            'result': {'cpu': '85%', 'memory': '70%'}
        }
        mock_post.return_value = mock_response
        
        result = AnsibleExecutor.run_diagnostics('test-host')
        
        assert result is not None
        assert 'cpu' in result
    
    @patch('webhook.requests.post')
    def test_run_diagnostics_timeout(self, mock_post):
        """Test diagnostic execution timeout handling"""
        from webhook import AnsibleExecutor
        import requests
        
        mock_post.side_effect = requests.exceptions.Timeout
        
        result = AnsibleExecutor.run_diagnostics('test-host')
        
        assert result is None
    
    @patch('webhook.requests.post')
    def test_run_diagnostics_connection_error(self, mock_post):
        """Test diagnostic execution connection error"""
        from webhook import AnsibleExecutor
        import requests
        
        mock_post.side_effect = requests.exceptions.ConnectionError
        
        result = AnsibleExecutor.run_diagnostics('test-host')
        
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

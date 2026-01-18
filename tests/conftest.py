"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import sys
from unittest.mock import Mock, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing"""
    env_vars = {
        'GROQ_API_KEY': 'test_groq_key_123',
        'TELEGRAM_BOT_TOKEN': '123456:ABC-DEF',
        'TELEGRAM_CHAT_ID': '1234567890',
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379',
        'CACHE_TTL': '3600',
        'ZABBIX_API_URL': 'http://localhost:8080/api_jsonrpc.php',
        'ANSIBLE_API_URL': 'http://localhost:5001',
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def mock_groq_client():
    """Mock Groq client for testing"""
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="AI analysis response"))
    ]
    mock_client.chat.completions.create.return_value = mock_completion
    return mock_client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True
    return mock_redis


@pytest.fixture
def sample_zabbix_alert():
    """Sample Zabbix alert data for testing"""
    return {
        'trigger': 'High CPU usage on server-01',
        'host': 'web-server-01',
        'severity': 'High',
        'value': '95',
        'time': '2026-01-18 02:00:00',
        'description': 'CPU usage is above threshold',
        'event_id': '12345'
    }


@pytest.fixture
def sample_ansible_output():
    """Sample Ansible diagnostic output"""
    return {
        'top': 'top - 02:00:00 up 5 days...',
        'ps': 'PID  USER  %CPU  %MEM  COMMAND\n1234 nginx 65.0  2.0   nginx',
        'df': 'Filesystem  Size  Used  Avail  Use%\n/dev/sda1   50G   30G   18G   63%',
        'free': 'total  used  free  shared  buff/cache  available\n8G     6G    1G    200M    1G          1.5G',
        'netstat': 'Proto  Local Address  Foreign Address  State\ntcp    0.0.0.0:80     0.0.0.0:*        LISTEN'
    }


@pytest.fixture
def sample_telegram_update():
    """Sample Telegram update object"""
    mock_update = MagicMock()
    mock_update.message.text = "/status"
    mock_update.effective_user.id = 1081490318
    mock_update.effective_user.first_name = "Test User"
    mock_update.message.reply_text = MagicMock()
    return mock_update


@pytest.fixture
def sample_telegram_context():
    """Sample Telegram context object"""
    mock_context = MagicMock()
    mock_context.args = []
    mock_context.bot.get_me = MagicMock()
    return mock_context

"""
Unit tests for Telegram Bot
Tests command handlers and bot functionality
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import sys
import os

# Add telegram-bot to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../ai-services/telegram-bot'))


class TestUserRoles:
    """Test user role management"""
    
    def test_get_user_role_admin(self):
        """Test admin role retrieval"""
        from bot import get_user_role
        
        role = get_user_role(1081490318)
        assert role == 'ADMIN'
    
    def test_get_user_role_default_viewer(self):
        """Test default viewer role for unknown user"""
        from bot import get_user_role
        
        role = get_user_role(999999999)
        assert role == 'VIEWER'
    
    def test_is_authorized_admin_can_fix(self):
        """Test admin can execute fix action"""
        from bot import is_authorized
        
        authorized, msg = is_authorized(1081490318, 'fix')
        assert authorized is True
        assert 'ADMIN' in msg
    
    def test_is_authorized_viewer_cannot_fix(self):
        """Test viewer cannot execute fix action"""
        from bot import is_authorized
        
        authorized, msg = is_authorized(999999999, 'fix')
        assert authorized is False
        assert 'Permission denied' in msg
    
    def test_is_authorized_viewer_can_diag(self):
        """Test viewer can run diagnostics"""
        from bot import is_authorized
        
        authorized, msg = is_authorized(999999999, 'diag')
        assert authorized is True


class TestCommandHandlers:
    """Test bot command handlers"""
    
    @pytest.mark.asyncio
    async def test_start_command(self, sample_telegram_update, sample_telegram_context):
        """Test /start command"""
        from bot import start
        
        await start(sample_telegram_update, sample_telegram_context)
        
        # Check that reply was sent
        sample_telegram_update.message.reply_text.assert_called_once()
        call_args = sample_telegram_update.message.reply_text.call_args[0][0]
        assert 'Welcome' in call_args
        assert 'ADMIN' in call_args  # User ID 1081490318 is ADMIN
    
    @pytest.mark.asyncio
    async def test_help_command(self, sample_telegram_update, sample_telegram_context):
        """Test /help command"""
        from bot import help_command
        
        await help_command(sample_telegram_update, sample_telegram_context)
        
        sample_telegram_update.message.reply_text.assert_called_once()
        call_args = sample_telegram_update.message.reply_text.call_args[0][0]
        assert 'Command Reference' in call_args
    
    @pytest.mark.asyncio
    @patch('bot.requests.get')
    async def test_status_command_success(self, mock_get, sample_telegram_update, sample_telegram_context):
        """Test /status command when services are online"""
        from bot import status_command
        
        # Mock all API calls as successful
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        await status_command(sample_telegram_update, sample_telegram_context)
        
        sample_telegram_update.message.reply_text.assert_called_once()
        call_args = sample_telegram_update.message.reply_text.call_args[0][0]
        assert 'System Status' in call_args
    
    @pytest.mark.asyncio
    @patch('bot.requests.get')
    async def test_list_alerts_no_problems(self, mock_get, sample_telegram_update, sample_telegram_context):
        """Test /list command with no active alerts"""
        from bot import list_alerts
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'problems': []}
        mock_get.return_value = mock_response
        
        await list_alerts(sample_telegram_update, sample_telegram_context)
        
        sample_telegram_update.message.reply_text.assert_called_once()
        call_args = sample_telegram_update.message.reply_text.call_args[0][0]
        assert 'No active alerts' in call_args
    
    @pytest.mark.asyncio
    @patch('bot.requests.get')
    async def test_list_alerts_with_problems(self, mock_get, sample_telegram_update, sample_telegram_context):
        """Test /list command with active alerts"""
        from bot import list_alerts
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'problems': [
                {
                    'id': '12345',
                    'name': 'High CPU usage',
                    'severity': 'High',
                    'host': 'web-server-01'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        await list_alerts(sample_telegram_update, sample_telegram_context)
        
        sample_telegram_update.message.reply_text.assert_called_once()
        call_args = sample_telegram_update.message.reply_text.call_args[0][0]
        assert 'Active Alerts' in call_args
        assert 'High CPU usage' in call_args


class TestNaturalLanguageChat:
    """Test natural language chat functionality"""
    
    @pytest.mark.asyncio
    @patch('bot.build_zabbix_context')
    @patch('bot.ask_groq')
    async def test_handle_message_with_alert_intent(self, mock_ask_groq, mock_context, sample_telegram_update, sample_telegram_context):
        """Test handling message with alert-related intent"""
        from bot import handle_message
        
        sample_telegram_update.message.text = "Có vấn đề gì không?"
        sample_telegram_update.message.chat.type = 'private'
        
        mock_context.return_value = {'problems': [{'id': '123', 'name': 'CPU high'}]}
        mock_ask_groq.return_value = "Hiện tại có 1 vấn đề về CPU"
        
        await handle_message(sample_telegram_update, sample_telegram_context)
        
        # Should call Groq and reply
        mock_ask_groq.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_message_ignores_group_without_mention(self, sample_telegram_update, sample_telegram_context):
        """Test bot ignores group messages without @mention"""
        from bot import handle_message
        
        sample_telegram_update.message.text = "Random message"
        sample_telegram_update.message.chat.type = 'group'
        sample_telegram_update.message.reply_to_message = None
        
        mock_bot_user = MagicMock()
        mock_bot_user.username = 'ZabbixBot'
        sample_telegram_context.bot.get_me = AsyncMock(return_value=mock_bot_user)
        
        await handle_message(sample_telegram_update, sample_telegram_context)
        
        # Should not reply
        sample_telegram_update.message.reply_text.assert_not_called()


class TestButtonCallbacks:
    """Test inline button callback handlers"""
    
    @pytest.mark.asyncio
    async def test_button_callback_cancel(self):
        """Test cancel button callback"""
        from bot import button_callback
        
        mock_query = MagicMock()
        mock_query.data = 'cancel:12345'
        mock_query.from_user.id = 1081490318
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()
        
        mock_update = MagicMock()
        mock_update.callback_query = mock_query
        
        await button_callback(mock_update, None)
        
        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args[0][0]
        assert 'cancelled' in call_args.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

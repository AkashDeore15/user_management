# tests/test_services/test_email_service.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.email_service import EmailService
from app.utils.template_manager import TemplateManager
from app.models.user_model import User
import urllib.parse

@pytest.fixture
def mock_template_manager():
    manager = MagicMock(spec=TemplateManager)
    manager.render_template.return_value = "<html>Test email content</html>"
    return manager

@pytest.fixture
def email_service(mock_template_manager):
    with patch('app.services.email_service.SMTPClient') as mock_smtp:
        email_service = EmailService(template_manager=mock_template_manager)
        return email_service

# tests/test_services/test_email_service.py

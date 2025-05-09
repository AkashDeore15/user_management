# email_service.py
import urllib.parse
from builtins import ValueError, dict, str
from settings.config import settings
from app.utils.smtp_connection import SMTPClient
from app.utils.template_manager import TemplateManager
from app.models.user_model import User
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self, template_manager: TemplateManager):
        self.smtp_client = SMTPClient(
            server=settings.smtp_server,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password
        )
        self.template_manager = template_manager

    async def send_user_email(self, user_data: dict, email_type: str):
        subject_map = {
            'email_verification': "Verify Your Account",
            'password_reset': "Password Reset Instructions",
            'account_locked': "Account Locked Notification",
            'professional_upgrade': "Professional Status Upgrade"  # Add this line
        }

        if email_type not in subject_map:
            raise ValueError("Invalid email type")

        try:
            html_content = self.template_manager.render_template(email_type, **user_data)
            self.smtp_client.send_email(subject_map[email_type], html_content, user_data['email'])
            logger.info(f"Email of type {email_type} sent to {user_data['email']}")
        except Exception as e:
            logger.error(f"Failed to send {email_type} email to {user_data['email']}: {str(e)}")
            raise

    async def send_verification_email(self, user: User):
        token = urllib.parse.quote(user.verification_token) if user.verification_token else ""
        verification_url = f"{settings.server_base_url}verify-email/{user.id}/{token}"
        
        logger.info(f"Generated verification URL: {verification_url}")
        
        await self.send_user_email({
            "name": user.first_name or "User",  # Fallback to "User" if first_name is None
            "verification_url": verification_url,
            "email": user.email
        }, 'email_verification')
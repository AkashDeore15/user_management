# tests/test_services/test_password_reset.py
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from app.services.user_service import UserService
from app.models.user_model import User

pytestmark = pytest.mark.asyncio

async def test_generate_password_reset(db_session, verified_user, email_service):
    # Generate a password reset token
    user = await UserService.generate_password_reset(db_session, verified_user.email)
    
    # Verify token was generated
    assert user is not None
    assert user.password_reset_token is not None
    assert user.password_reset_token_expires_at is not None
    assert user.password_reset_token_expires_at > datetime.now(timezone.utc)

async def test_generate_password_reset_nonexistent_user(db_session, email_service):
    # Try to generate a token for a non-existent user
    user = await UserService.generate_password_reset(db_session, "nonexistent@example.com")
    
    # Should return None
    assert user is None

async def test_verify_password_reset_token_valid(db_session, verified_user):
    # Generate a token
    user = await UserService.generate_password_reset(db_session, verified_user.email)
    
    # Verify the token
    result = await UserService.verify_password_reset_token(
        db_session, 
        user.id, 
        user.password_reset_token
    )
    
    # Should be valid
    assert result is True

async def test_verify_password_reset_token_expired(db_session, verified_user):
    # Generate a token
    user = await UserService.generate_password_reset(db_session, verified_user.email)
    
    # Force the token to be expired
    user.password_reset_token_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    await db_session.commit()
    
    # Verify the token
    result = await UserService.verify_password_reset_token(
        db_session, 
        user.id, 
        user.password_reset_token
    )
    
    # Should be invalid
    assert result is False

async def test_reset_password_with_token_success(db_session, verified_user):
    # Generate a token
    user = await UserService.generate_password_reset(db_session, verified_user.email)
    
    # Reset the password
    result = await UserService.reset_password_with_token(
        db_session,
        user.id,
        user.password_reset_token,
        "NewSecurePassword123!"
    )
    
    # Should be successful
    assert result is True
    
    # Verify token is cleared
    await db_session.refresh(user)
    assert user.password_reset_token is None
    assert user.password_reset_token_expires_at is None

async def test_reset_password_with_invalid_token(db_session, verified_user):
    # Generate a token
    user = await UserService.generate_password_reset(db_session, verified_user.email)
    
    # Reset with invalid token
    result = await UserService.reset_password_with_token(
        db_session,
        user.id,
        "invalid-token",
        "NewSecurePassword123!"
    )
    
    # Should fail
    assert result is False
# tests/test_api/test_password_reset_api.py

import pytest
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from app.services.user_service import UserService

pytestmark = pytest.mark.asyncio

async def test_request_password_reset_existing_user(async_client, verified_user, email_service):
    # Request a password reset
    form_data = {"email": verified_user.email}
    response = await async_client.post(
        "/forgot-password/", 
        data=urlencode(form_data),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    # Should be successful
    assert response.status_code == 200
    assert "message" in response.json()

async def test_request_password_reset_nonexistent_user(async_client, email_service):
    # Request a password reset for non-existent user
    form_data = {"email": "nonexistent@example.com"}
    response = await async_client.post(
        "/forgot-password/", 
        data=urlencode(form_data),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    # Should still return success to prevent email enumeration
    assert response.status_code == 200
    assert "message" in response.json()

async def test_show_reset_password_form_valid_token(async_client, db_session, verified_user):
    # Generate a token
    user = await UserService.generate_password_reset(db_session, verified_user.email)
    
    # Access the reset password form
    response = await async_client.get(f"/reset-password/{user.id}/{user.password_reset_token}")
    
    # Should be successful
    assert response.status_code == 200
    assert "message" in response.json()
    assert "user_id" in response.json()
    assert "token" in response.json()

async def test_show_reset_password_form_invalid_token(async_client, verified_user):
    # Access with invalid token
    response = await async_client.get(f"/reset-password/{verified_user.id}/invalid-token")
    
    # Should fail
    assert response.status_code == 400
    assert "message" in response.json()

async def test_process_reset_password_success(async_client, db_session, verified_user):
    # Generate a token
    user = await UserService.generate_password_reset(db_session, verified_user.email)
    
    # Reset the password
    form_data = {
        "user_id": str(user.id),
        "token": user.password_reset_token,
        "new_password": "NewSecurePassword123!"
    }
    response = await async_client.post(
        "/reset-password/", 
        data=urlencode(form_data),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    # Should be successful
    assert response.status_code == 200
    assert "message" in response.json()
    assert "Password reset successful" in response.json()["message"]

async def test_process_reset_password_invalid_token(async_client, verified_user):
    # Reset with invalid token
    form_data = {
        "user_id": str(verified_user.id),
        "token": "invalid-token",
        "new_password": "NewSecurePassword123!"
    }
    response = await async_client.post(
        "/reset-password/", 
        data=urlencode(form_data),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    # Should fail
    assert response.status_code == 400
    assert "message" in response.json()
    assert "Failed to reset password" in response.json()["message"]
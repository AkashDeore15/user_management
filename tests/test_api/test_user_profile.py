# tests/test_api/test_user_profile.py
from builtins import str
import pytest
from httpx import AsyncClient
from app.models.user_model import User, UserRole

@pytest.mark.asyncio
async def test_update_own_profile(async_client, verified_user, user_token):
    """Test that a user can update their own profile."""
    headers = {"Authorization": f"Bearer {user_token}"}
    
    update_data = {
        "first_name": "Updated",
        "last_name": "Name",
        "bio": "This is my updated bio",
        "github_profile_url": "https://github.com/updateduser",
        "linkedin_profile_url": "https://linkedin.com/in/updateduser"
    }
    
    response = await async_client.put("/profile/", json=update_data, headers=headers)
    
    assert response.status_code == 200
    assert response.json()["first_name"] == update_data["first_name"]
    assert response.json()["last_name"] == update_data["last_name"]
    assert response.json()["bio"] == update_data["bio"]
    assert response.json()["github_profile_url"] == update_data["github_profile_url"]
    assert response.json()["linkedin_profile_url"] == update_data["linkedin_profile_url"]

@pytest.mark.asyncio
async def test_update_own_profile_unauthorized(async_client):
    """Test that authentication is required to update profile."""
    update_data = {"first_name": "Updated"}
    
    response = await async_client.put("/profile/", json=update_data)
    
    assert response.status_code == 401  # Unauthorized

@pytest.mark.asyncio
async def test_update_own_profile_invalid_url(async_client, verified_user, user_token):
    """Test that profile update validates URLs properly."""
    headers = {"Authorization": f"Bearer {user_token}"}
    
    update_data = {
        "github_profile_url": "invalid-url"
    }
    
    response = await async_client.put("/profile/", json=update_data, headers=headers)
    
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_update_own_profile_role_change_attempt(async_client, verified_user, user_token):
    """Test that users cannot update their own role through profile update."""
    headers = {"Authorization": f"Bearer {user_token}"}
    
    # Attempt to change role to admin
    update_data = {
        "first_name": "Updated",
        "role": "ADMIN"
    }
    
    response = await async_client.put("/profile/", json=update_data, headers=headers)
    
    assert response.status_code == 200
    # Verify role hasn't changed
    assert response.json()["role"] == "AUTHENTICATED"
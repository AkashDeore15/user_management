# tests/test_api/test_user_profile.py
from builtins import str
import pytest
from httpx import AsyncClient
from app.models.user_model import User, UserRole
from app.services.user_service import UserService

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

@pytest.mark.asyncio
async def test_update_professional_status_as_admin(async_client, verified_user, admin_token, email_service):
    """Test that an admin can upgrade a user to professional status."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    response = await async_client.put(f"/users/{verified_user.id}/professional-status?professional_status=true", headers=headers)
    
    assert response.status_code == 200
    assert response.json()["is_professional"] is True

@pytest.mark.asyncio
async def test_update_professional_status_as_manager(async_client, verified_user, manager_token, email_service):
    """Test that a manager can upgrade a user to professional status."""
    headers = {"Authorization": f"Bearer {manager_token}"}
    
    response = await async_client.put(f"/users/{verified_user.id}/professional-status?professional_status=true", headers=headers)
    
    assert response.status_code == 200
    assert response.json()["is_professional"] is True

@pytest.mark.asyncio
async def test_update_professional_status_as_user(async_client, verified_user, user_token):
    """Test that a regular user cannot upgrade another user to professional status."""
    headers = {"Authorization": f"Bearer {user_token}"}
    
    response = await async_client.put(f"/users/{verified_user.id}/professional-status?professional_status=true", headers=headers)
    
    assert response.status_code == 403  # Forbidden

@pytest.mark.asyncio
async def test_update_professional_status_user_not_found(async_client, admin_token):
    """Test handling of non-existent user."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    
    response = await async_client.put(f"/users/{non_existent_id}/professional-status?professional_status=true", headers=headers)
    
    assert response.status_code == 404  # Not Found

# Add these tests to tests/test_api/test_user_profile.py

@pytest.mark.asyncio
async def test_full_profile_workflow(async_client, verified_user, admin_user, email_service):
    """Test the entire user profile management workflow."""
    # Create tokens directly in the test
    from app.services.jwt_service import create_access_token
    from datetime import timedelta
    
    # Generate a fresh token with verified_user's ID
    user_token = create_access_token(
        data={"sub": str(verified_user.id), "role": verified_user.role.name},
        expires_delta=timedelta(minutes=30)
    )
    
    admin_token = create_access_token(
        data={"sub": str(admin_user.id), "role": admin_user.role.name},
        expires_delta=timedelta(minutes=30)
    )
    
    # 1. User updates their own profile
    headers_user = {"Authorization": f"Bearer {user_token}"}
    profile_update = {
        "first_name": "John",
        "last_name": "Developer",
        "bio": "A passionate developer",
        "github_profile_url": "https://github.com/johndeveloper",
        "linkedin_profile_url": "https://linkedin.com/in/johndeveloper"
    }
    
    response = await async_client.put("/profile/", json=profile_update, headers=headers_user)
    assert response.status_code == 200
    assert response.json()["first_name"] == profile_update["first_name"]
    assert response.json()["github_profile_url"] == profile_update["github_profile_url"]
    
    # 2. Admin upgrades user to professional
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    upgrade_response = await async_client.put(
        f"/users/{verified_user.id}/professional-status?professional_status=true",
        headers=headers_admin
    )
    assert upgrade_response.status_code == 200
    assert upgrade_response.json()["is_professional"] is True
    
    # 3. Verify user can still update their profile after upgrade
    profile_update2 = {
        "bio": "A professional developer with extensive experience"
    }
    response2 = await async_client.put("/profile/", json=profile_update2, headers=headers_user)
    assert response2.status_code == 200
    assert response2.json()["bio"] == profile_update2["bio"]
    assert response2.json()["is_professional"] is True
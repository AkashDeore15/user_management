# tests/test_utils/test_validators.py
import pytest
from app.utils.validators import validate_email_address
from unittest.mock import patch

@pytest.mark.asyncio
async def test_validate_email_address_valid():
    # We need to mock the email_validator function to prevent it from checking real domains
    with patch('app.utils.validators.validate_email') as mock_validator:
        # Return some mock data instead of raising an exception
        mock_validator.return_value = {"email": "test@example.com"}
        assert validate_email_address("test@example.com") is True

# tests/test_utils/test_validators.py
@pytest.mark.asyncio
async def test_validate_email_address_invalid():
    # We want to raise an EmailNotValidError, not a generic Exception
    from email_validator import EmailNotValidError
    
    with patch('app.utils.validators.validate_email', side_effect=EmailNotValidError("Invalid email")):
        assert validate_email_address("invalid-email") is False

@pytest.mark.asyncio
async def test_validate_email_address_empty():
    assert validate_email_address("") is False

@pytest.mark.asyncio
async def test_validate_email_address_missing_domain():
    assert validate_email_address("user@") is False

@pytest.mark.asyncio
async def test_validate_email_address_special_chars():
    with patch('app.utils.validators.validate_email') as mock_validator:
        # Return some mock data instead of raising an exception
        mock_validator.return_value = {"email": "test+filter@example.com"}
        assert validate_email_address("test+filter@example.com") is True
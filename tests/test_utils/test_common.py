import os
import pytest
import logging.config
from app.utils.common import setup_logging
from unittest.mock import patch, mock_open

@pytest.mark.asyncio
async def test_setup_logging():
    # Mock the file path normalization
    with patch('os.path.normpath', return_value='/mock/logging.conf'):
        # Mock the fileConfig function
        with patch('logging.config.fileConfig') as mock_fileconfig:
            # Mock the file existence check
            with patch('os.path.exists', return_value=True):
                # Call the function
                setup_logging()
                # Verify fileConfig was called with the correct path
                mock_fileconfig.assert_called_once_with('/mock/logging.conf', disable_existing_loggers=False)
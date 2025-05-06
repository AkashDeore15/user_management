# tests/test_utils/test_template_manager.py
import pytest
from unittest.mock import patch, mock_open, MagicMock
from app.utils.template_manager import TemplateManager
from pathlib import Path

@pytest.fixture
def template_manager():
    with patch('pathlib.Path.resolve') as mock_resolve:
        # Create a proper Path object instead of a string
        mock_path = MagicMock(spec=Path)
        mock_path.parent.parent.parent = Path('/mock/root')
        mock_resolve.return_value = mock_path
        
        # Mock the / operator behavior
        mock_path.__truediv__.return_value = Path('/mock/root/email_templates')
        
        # Return a template manager with the mocked path
        with patch('pathlib.Path.__new__', return_value=mock_path):
            tm = TemplateManager()
            tm.templates_dir = Path('/mock/root/email_templates')
            return tm

@pytest.mark.asyncio
async def test_read_template(template_manager):
    mock_content = "# Test Template\n\nThis is a test template."
    with patch("builtins.open", mock_open(read_data=mock_content)):
        with patch.object(Path, 'exists', return_value=True):
            content = template_manager._read_template("test_template.md")
            assert content == mock_content

@pytest.mark.asyncio
async def test_read_template_file_not_found(template_manager):
    with patch("builtins.open", side_effect=FileNotFoundError):
        with pytest.raises(ValueError, match="Template file not found"):
            template_manager._read_template("nonexistent_template.md")

@pytest.mark.asyncio
async def test_apply_email_styles(template_manager):
    html = "<h1>Test Header</h1><p>Test paragraph</p>"
    styled_html = template_manager._apply_email_styles(html)
    assert "style=" in styled_html
    assert "<div" in styled_html

@pytest.mark.asyncio
async def test_render_template(template_manager):
    # Mock template files
    header = "# Header"
    footer = "# Footer"
    main_template = "Hello {name}, visit {verification_url}"
    
    with patch.object(template_manager, "_read_template") as mock_read:
        mock_read.side_effect = [header, footer, main_template]
        with patch("markdown2.markdown", return_value="<p>Converted HTML</p>"):
            with patch.object(template_manager, "_apply_email_styles", return_value="<div>Styled HTML</div>"):
                result = template_manager.render_template(
                    "email_verification", 
                    name="John", 
                    verification_url="http://example.com/verify"
                )
                assert result == "<div>Styled HTML</div>"

@pytest.mark.asyncio
async def test_render_template_error_handling(template_manager):
    with patch.object(template_manager, "_read_template", side_effect=Exception("Template error")):
        result = template_manager.render_template(
            "email_verification", 
            name="John", 
            verification_url="http://example.com/verify"
        )
        # Check that the fallback template is returned
        assert "Hello" in result
        assert "User" in result or "John" in result
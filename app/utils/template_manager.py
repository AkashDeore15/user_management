import markdown2
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class TemplateManager:
    def __init__(self):
        # Dynamically determine the root path of the project
        self.root_dir = Path(__file__).resolve().parent.parent.parent  # Adjust this depending on the structure
        self.templates_dir = self.root_dir / 'email_templates'
        logger.info(f"Template directory set to: {self.templates_dir}")

    def _read_template(self, filename: str) -> str:
        """Private method to read template content."""
        template_path = self.templates_dir / filename
        logger.debug(f"Reading template from: {template_path}")
        
        try:
            with open(template_path, 'r', encoding='utf-8') as file:
                content = file.read()
                return content
        except FileNotFoundError:
            logger.error(f"Template file not found: {template_path}")
            raise ValueError(f"Template file not found: {filename}")
        except Exception as e:
            logger.error(f"Error reading template {filename}: {str(e)}")
            raise

    def _apply_email_styles(self, html: str) -> str:
        """Apply advanced CSS styles inline for email compatibility with excellent typography."""
        styles = {
            'body': 'font-family: Arial, sans-serif; font-size: 16px; color: #333333; background-color: #ffffff; line-height: 1.5;',
            'h1': 'font-size: 24px; color: #333333; font-weight: bold; margin-top: 20px; margin-bottom: 10px;',
            'p': 'font-size: 16px; color: #666666; margin: 10px 0; line-height: 1.6;',
            'a': 'color: #0056b3; text-decoration: none; font-weight: bold;',
            'footer': 'font-size: 12px; color: #777777; padding: 20px 0;',
            'ul': 'list-style-type: none; padding: 0;',
            'li': 'margin-bottom: 10px;'
        }
        # Wrap entire HTML content in <div> with body style
        styled_html = f'<div style="{styles["body"]}">{html}</div>'
        # Apply styles to each HTML element
        for tag, style in styles.items():
            if tag != 'body':  # Skip the body style since it's already applied to the <div>
                styled_html = styled_html.replace(f'<{tag}>', f'<{tag} style="{style}">')
        return styled_html

    def render_template(self, template_name: str, **context) -> str:
        """Render a markdown template with given context, applying advanced email styles."""
        try:
            logger.debug(f"Rendering template: {template_name} with context keys: {list(context.keys())}")
            
            header = self._read_template('header.md')
            footer = self._read_template('footer.md')

            # Read main template and format it with provided context
            main_template = self._read_template(f'{template_name}.md')
            
            # Ensure all required keys are present in the context
            required_keys = ["name", "verification_url"] if template_name == "email_verification" else []
            for key in required_keys:
                if key not in context:
                    logger.warning(f"Missing required key '{key}' in context for template '{template_name}'")
                    context[key] = f"[Missing {key}]"  # Provide a fallback
            
            main_content = main_template.format(**context)
            
            full_markdown = f"{header}\n{main_content}\n{footer}"
            html_content = markdown2.markdown(full_markdown)
            styled_html = self._apply_email_styles(html_content)
            
            logger.debug(f"Successfully rendered template: {template_name}")
            return styled_html
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {str(e)}")
            # Provide a very basic fallback template in case of errors
            return f"""
            <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <h2>Important Notification</h2>
                <p>Hello {context.get('name', 'User')},</p>
                <p>Please visit the following link to continue: <a href="{context.get('verification_url', '#')}">{context.get('verification_url', 'Click here')}</a></p>
                <p>Thank you,<br>The Team</p>
            </div>
            """
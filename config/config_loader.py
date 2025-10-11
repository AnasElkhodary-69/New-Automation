"""
Configuration Loader Module

Loads configuration from JSON files and .env variables
Prioritizes environment variables over JSON for sensitive data
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class ConfigLoader:
    """Load and manage configuration from multiple sources"""

    def __init__(self, config_dir: str = "config"):
        """
        Initialize config loader

        Args:
            config_dir: Directory containing config files
        """
        self.config_dir = Path(config_dir)
        self._configs = {}

    def load_email_config(self) -> Dict[str, Any]:
        """
        Load email configuration
        Environment variables override JSON config

        Returns:
            Email configuration dictionary
        """
        # Load from JSON
        config_path = self.config_dir / "email_config.json"
        config = self._load_json(config_path)

        # Override with environment variables (more secure)
        config['email'] = os.getenv('EMAIL_ADDRESS', config.get('email'))
        config['password'] = os.getenv('EMAIL_PASSWORD', config.get('password'))
        config['imap_server'] = os.getenv('IMAP_SERVER', config.get('imap_server'))
        config['imap_port'] = int(os.getenv('IMAP_PORT', config.get('imap_port', 993)))
        config['smtp_server'] = os.getenv('SMTP_SERVER', config.get('smtp_server'))
        config['smtp_port'] = int(os.getenv('SMTP_PORT', config.get('smtp_port', 587)))

        # Validate required fields
        if not config['email'] or not config['password']:
            logger.warning("Email credentials not configured!")

        return config

    def load_odoo_config(self) -> Dict[str, Any]:
        """
        Load Odoo database configuration
        Environment variables override JSON config

        Returns:
            Odoo configuration dictionary
        """
        # Load from JSON
        config_path = self.config_dir / "odoo_config.json"
        config = self._load_json(config_path)

        # Override with environment variables (more secure)
        config['host'] = os.getenv('ODOO_DB_HOST', config.get('host'))
        config['port'] = int(os.getenv('ODOO_DB_PORT', config.get('port', 5432)))
        config['database'] = os.getenv('ODOO_DB_NAME', config.get('database'))
        config['user'] = os.getenv('ODOO_DB_USER', config.get('user'))
        config['password'] = os.getenv('ODOO_DB_PASSWORD', config.get('password'))

        # Validate required fields
        if not config['database'] or not config['user'] or not config['password']:
            logger.warning("Odoo database credentials not configured!")

        return config

    def load_settings(self) -> Dict[str, Any]:
        """
        Load main settings
        Environment variables override JSON config for sensitive data

        Returns:
            Settings dictionary
        """
        # Load from JSON
        config_path = self.config_dir / "settings.json"
        config = self._load_json(config_path)

        # Override sensitive values with environment variables
        if 'claude' in config:
            config['claude']['api_key'] = os.getenv(
                'CLAUDE_API_KEY',
                config['claude'].get('api_key')
            )

        if 'vector_store' in config:
            config['vector_store']['openai_api_key'] = os.getenv(
                'OPENAI_API_KEY',
                config['vector_store'].get('openai_api_key')
            )
            if 'qdrant' in config['vector_store']:
                config['vector_store']['qdrant']['url'] = os.getenv(
                    'QDRANT_URL',
                    config['vector_store']['qdrant'].get('url')
                )
                config['vector_store']['qdrant']['api_key'] = os.getenv(
                    'QDRANT_API_KEY',
                    config['vector_store']['qdrant'].get('api_key', '')
                )

        if 'notifications' in config:
            config['notifications']['notification_email'] = os.getenv(
                'ADMIN_EMAIL',
                config['notifications'].get('notification_email')
            )

        # Environment-specific overrides
        environment = os.getenv('ENVIRONMENT', 'development')
        config['environment'] = environment

        return config

    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """
        Load JSON configuration file

        Args:
            file_path: Path to JSON file

        Returns:
            Configuration dictionary
        """
        try:
            if file_path.exists():
                with open(file_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Config file not found: {file_path}")
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON file {file_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading config file {file_path}: {e}")
            return {}

    def get_all_configs(self) -> Dict[str, Dict]:
        """
        Load all configuration files

        Returns:
            Dictionary with all configurations
        """
        return {
            'email': self.load_email_config(),
            'odoo': self.load_odoo_config(),
            'settings': self.load_settings()
        }

    def validate_config(self) -> Dict[str, list]:
        """
        Validate that all required configuration is present

        Returns:
            Dictionary with validation results
        """
        issues = {
            'errors': [],
            'warnings': []
        }

        # Validate email config
        email_config = self.load_email_config()
        if not email_config.get('email'):
            issues['errors'].append("EMAIL_ADDRESS not configured")
        if not email_config.get('password'):
            issues['errors'].append("EMAIL_PASSWORD not configured")

        # Validate Odoo config
        odoo_config = self.load_odoo_config()
        if not odoo_config.get('database'):
            issues['warnings'].append("ODOO_DB_NAME not configured")
        if not odoo_config.get('password'):
            issues['warnings'].append("ODOO_DB_PASSWORD not configured")

        # Validate settings
        settings = self.load_settings()
        if not settings.get('claude', {}).get('api_key'):
            issues['errors'].append("CLAUDE_API_KEY not configured")
        if not settings.get('vector_store', {}).get('openai_api_key'):
            issues['warnings'].append("OPENAI_API_KEY not configured (needed for embeddings)")

        return issues


# Convenience function
def load_config() -> Dict[str, Dict]:
    """
    Load all configuration

    Returns:
        Dictionary with all configurations
    """
    loader = ConfigLoader()
    return loader.get_all_configs()


def validate_config() -> Dict[str, list]:
    """
    Validate configuration

    Returns:
        Validation results
    """
    loader = ConfigLoader()
    return loader.validate_config()

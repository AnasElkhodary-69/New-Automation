"""
Setup and Configuration Validator

Run this script to validate your configuration before starting the system
"""

import os
import sys
from pathlib import Path
from config.config_loader import ConfigLoader, validate_config


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_status(item, status, message=""):
    """Print status with color"""
    status_symbol = "✓" if status else "✗"
    status_text = "OK" if status else "MISSING"
    print(f"  {status_symbol} {item:30} [{status_text}] {message}")


def check_env_file():
    """Check if .env file exists"""
    print_header("Environment File Check")

    env_path = Path(".env")
    env_example_path = Path(".env.example")

    if env_path.exists():
        print_status(".env file", True)
        return True
    else:
        print_status(".env file", False, "NOT FOUND!")
        print("\n  ⚠️  Please create .env file from .env.example:")
        print(f"     cp {env_example_path} {env_path}")
        print(f"     Then edit {env_path} with your credentials")
        return False


def check_required_env_vars():
    """Check if required environment variables are set"""
    print_header("Required Environment Variables")

    required_vars = {
        'EMAIL_ADDRESS': 'Email address for IMAP/SMTP',
        'EMAIL_PASSWORD': 'Email password or app password',
        'CLAUDE_API_KEY': 'Claude API key from Anthropic',
    }

    optional_vars = {
        'ODOO_DB_HOST': 'Odoo database host',
        'ODOO_DB_NAME': 'Odoo database name',
        'ODOO_DB_USER': 'Odoo database user',
        'ODOO_DB_PASSWORD': 'Odoo database password',
        'OPENAI_API_KEY': 'OpenAI API key for embeddings',
    }

    all_ok = True

    # Check required
    for var, description in required_vars.items():
        value = os.getenv(var)
        is_set = bool(value and value.strip() and not value.startswith('your_'))
        print_status(var, is_set, description)
        if not is_set:
            all_ok = False

    print("\n  Optional (for full functionality):")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        is_set = bool(value and value.strip() and not value.startswith('your_'))
        symbol = "✓" if is_set else "○"
        status_text = "SET" if is_set else "NOT SET"
        print(f"  {symbol} {var:30} [{status_text}] {description}")

    return all_ok


def check_directories():
    """Check if required directories exist"""
    print_header("Directory Structure")

    required_dirs = [
        'email_module',
        'retriever_module',
        'orchestrator',
        'prompts',
        'config',
        'logs',
    ]

    all_ok = True
    for directory in required_dirs:
        path = Path(directory)
        exists = path.exists() and path.is_dir()
        print_status(directory, exists)
        if not exists:
            all_ok = False

    return all_ok


def check_config_files():
    """Check if configuration files exist"""
    print_header("Configuration Files")

    config_files = [
        'config/email_config.json',
        'config/odoo_config.json',
        'config/settings.json',
        'prompts/intent_prompt.txt',
        'prompts/extraction_prompt.txt',
    ]

    all_ok = True
    for config_file in config_files:
        path = Path(config_file)
        exists = path.exists() and path.is_file()
        print_status(config_file, exists)
        if not exists:
            all_ok = False

    return all_ok


def test_config_loading():
    """Test loading configuration"""
    print_header("Configuration Loading Test")

    try:
        loader = ConfigLoader()

        # Test email config
        email_config = loader.load_email_config()
        print_status("Email config", bool(email_config))

        # Test Odoo config
        odoo_config = loader.load_odoo_config()
        print_status("Odoo config", bool(odoo_config))

        # Test settings
        settings = loader.load_settings()
        print_status("Settings", bool(settings))

        return True

    except Exception as e:
        print_status("Config loading", False, str(e))
        return False


def validate_configuration():
    """Validate complete configuration"""
    print_header("Configuration Validation")

    try:
        issues = validate_config()

        if issues['errors']:
            print("\n  ❌ ERRORS (must fix):")
            for error in issues['errors']:
                print(f"     • {error}")
        else:
            print("  ✓ No critical errors")

        if issues['warnings']:
            print("\n  ⚠️  WARNINGS (optional):")
            for warning in issues['warnings']:
                print(f"     • {warning}")
        else:
            print("  ✓ No warnings")

        return len(issues['errors']) == 0

    except Exception as e:
        print(f"  ✗ Validation failed: {e}")
        return False


def check_dependencies():
    """Check if required Python packages are installed"""
    print_header("Python Dependencies")

    required_packages = [
        ('anthropic', 'Claude API client'),
        ('openai', 'OpenAI API client'),
        ('psycopg2', 'PostgreSQL adapter'),
        ('dotenv', 'Environment variable loader'),
        ('numpy', 'Numerical computing'),
    ]

    optional_packages = [
        ('faiss', 'Vector search (CPU)'),
        ('qdrant_client', 'Qdrant vector database'),
        ('sentence_transformers', 'Local embeddings'),
    ]

    all_ok = True

    for package, description in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print_status(package, True, description)
        except ImportError:
            print_status(package, False, f"{description} - Run: pip install {package}")
            all_ok = False

    print("\n  Optional packages:")
    for package, description in optional_packages:
        try:
            __import__(package.replace('-', '_'))
            symbol = "✓"
            status_text = "INSTALLED"
        except ImportError:
            symbol = "○"
            status_text = "NOT INSTALLED"
        print(f"  {symbol} {package:30} [{status_text}] {description}")

    return all_ok


def main():
    """Main validation function"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "RAG Email System - Setup Validator" + " " * 13 + "║")
    print("╚" + "=" * 58 + "╝")

    # Run all checks
    checks = [
        ("Environment File", check_env_file),
        ("Environment Variables", check_required_env_vars),
        ("Directory Structure", check_directories),
        ("Configuration Files", check_config_files),
        ("Dependencies", check_dependencies),
        ("Configuration Loading", test_config_loading),
        ("Configuration Validation", validate_configuration),
    ]

    results = {}
    for check_name, check_func in checks:
        try:
            results[check_name] = check_func()
        except Exception as e:
            print(f"\n  ✗ {check_name} failed with error: {e}")
            results[check_name] = False

    # Summary
    print_header("Summary")

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for check_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status:8} {check_name}")

    print(f"\n  Total: {passed}/{total} checks passed")

    if passed == total:
        print("\n  ✅ Configuration is valid! You can run the system.")
        print("\n  Start the system with:")
        print("     python main.py")
        return 0
    else:
        print("\n  ❌ Please fix the issues above before running the system.")
        print("\n  Quick start guide:")
        print("     1. Copy .env.example to .env")
        print("     2. Edit .env with your credentials")
        print("     3. Run: pip install -r requirements.txt")
        print("     4. Run this script again: python setup.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())

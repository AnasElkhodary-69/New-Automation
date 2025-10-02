# Configuration Guide

## Overview: .env vs JSON Config Files

### Why Two Types of Configuration?

Your RAG Email System uses **two layers of configuration** for security and flexibility:

```
┌──────────────────────────────────────────────────┐
│                                                  │
│  .env File (SECRETS)                            │
│  ├─ Passwords                                   │
│  ├─ API Keys                                    │
│  ├─ Database credentials                        │
│  └─ Environment-specific values                 │
│                                                  │
│  🔒 NEVER commit to git                         │
│  🔒 Different per environment (dev/staging/prod)│
│                                                  │
└──────────────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────────────┐
│                                                  │
│  JSON Config Files (SETTINGS)                   │
│  ├─ Server addresses (imap.gmail.com)           │
│  ├─ Port numbers (993, 587)                     │
│  ├─ Feature flags (enable_auto_response)        │
│  ├─ Timeouts and retries                        │
│  └─ Table names and schemas                     │
│                                                  │
│  ✅ Safe to commit to git                       │
│  ✅ Shared across environments                  │
│                                                  │
└──────────────────────────────────────────────────┘
```

## Quick Start

### Step 1: Create .env file

```bash
cp .env.example .env
```

### Step 2: Edit .env with your credentials

```env
# Email
EMAIL_ADDRESS=support@mycompany.com
EMAIL_PASSWORD=app-specific-password-here

# Odoo
ODOO_DB_HOST=10.0.0.50
ODOO_DB_NAME=production_db
ODOO_DB_USER=readonly_user
ODOO_DB_PASSWORD=secure_password_123

# API Keys
CLAUDE_API_KEY=sk-ant-api03-xxx
OPENAI_API_KEY=sk-xxx
```

### Step 3: Customize JSON configs (optional)

Edit `config/*.json` files only for **non-sensitive settings**:
- Port numbers
- Feature toggles
- Timeout values
- Retry logic

### Step 4: Validate setup

```bash
python setup.py
```

## Detailed Comparison

| Aspect | .env File | JSON Config Files |
|--------|-----------|-------------------|
| **Contains** | 🔐 Secrets & credentials | ⚙️ Application settings |
| **Git** | ❌ In .gitignore | ✅ Committed to repo |
| **Format** | `KEY=value` | `{"key": "value"}` |
| **Changes** | Per environment | Rarely changes |
| **Risk if exposed** | 🚨 High (security breach) | ℹ️ Low (just settings) |
| **Examples** | `EMAIL_PASSWORD=xyz` | `"smtp_port": 587` |

## Configuration Loading Priority

The system loads configuration in this order (later overrides earlier):

```
1. JSON config files (defaults)
   ↓
2. .env file (overrides JSON)
   ↓
3. System environment variables (overrides both)
```

**Example:**

```json
// config/email_config.json
{
  "imap_server": "imap.gmail.com",
  "email": "default@example.com"  // ← This will be overridden
}
```

```env
# .env file
EMAIL_ADDRESS=real@mycompany.com  # ← This wins!
```

**Result:** System uses `real@mycompany.com`

## What Goes Where?

### ✅ Put in .env file:

- ✓ Passwords
- ✓ API keys
- ✓ Database credentials
- ✓ Secret tokens
- ✓ Private URLs with tokens
- ✓ Webhook secrets

### ✅ Put in JSON config files:

- ✓ Server hostnames (public)
- ✓ Port numbers
- ✓ Timeout values
- ✓ Feature flags (true/false)
- ✓ Retry attempts
- ✓ Max token limits
- ✓ Table/column names
- ✓ Log levels

## Real-World Example

**Scenario:** You want to test with a development database but use production email.

### Development (.env)
```env
EMAIL_ADDRESS=support@mycompany.com
ODOO_DB_HOST=localhost
ODOO_DB_NAME=dev_database
ENVIRONMENT=development
```

### Production (.env)
```env
EMAIL_ADDRESS=support@mycompany.com
ODOO_DB_HOST=10.0.0.100
ODOO_DB_NAME=production
ENVIRONMENT=production
```

### Shared (JSON configs - same for both)
```json
{
  "connection_timeout": 30,
  "pool_size": 5,
  "tables": {
    "customers": "res_partner"
  }
}
```

## Security Best Practices

### 1. Never Commit .env
```bash
# Already in .gitignore
.env
```

### 2. Use App Passwords
For Gmail, create an App Password:
1. Go to Google Account → Security
2. Enable 2-Step Verification
3. Generate App Password
4. Use that instead of your real password

### 3. Rotate Keys Regularly
```bash
# Update .env with new keys
CLAUDE_API_KEY=new_key_here

# Restart application
python main.py
```

### 4. Limit Database Permissions
```sql
-- Create read-only user for Odoo
CREATE USER rag_readonly WITH PASSWORD 'secure_pass';
GRANT CONNECT ON DATABASE odoo TO rag_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO rag_readonly;
```

## Troubleshooting

### "Environment variable not found"

**Problem:** System can't find credentials

**Solution:**
```bash
# Check .env exists
ls -la .env

# Check .env is loaded
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('EMAIL_ADDRESS'))"

# Should print your email, not None
```

### "Using default/placeholder values"

**Problem:** .env values not overriding JSON

**Solution:** Ensure `.env` is in the project root:
```
rag_email_system/
├── .env          ← Here!
├── main.py
└── config/
```

### "Config file not found"

**Problem:** Running from wrong directory

**Solution:**
```bash
# Always run from project root
cd rag_email_system
python main.py
```

## Advanced: Multiple Environments

### Using different .env files

```bash
# Development
cp .env.example .env.dev

# Production
cp .env.example .env.prod

# Load specific environment
python main.py --env-file .env.prod
```

### Environment-specific JSON configs

```bash
config/
├── email_config.json          # Default
├── email_config.dev.json      # Development overrides
└── email_config.prod.json     # Production overrides
```

## Migration from JSON to .env

If you accidentally put secrets in JSON:

### Before (❌ INSECURE):
```json
{
  "email": "support@company.com",
  "password": "my_secret_password"  ← BAD!
}
```

### After (✅ SECURE):

**JSON:**
```json
{
  "comment": "Credentials in .env file"
}
```

**.env:**
```env
EMAIL_ADDRESS=support@company.com
EMAIL_PASSWORD=my_secret_password
```

## Summary Cheat Sheet

```
┌─────────────────────────────────────────────────┐
│  Configuration Decision Tree                    │
└─────────────────────────────────────────────────┘

Is it a secret/password/API key?
├─ YES → Put in .env file
└─ NO → Put in JSON config

Will it differ between dev/staging/prod?
├─ YES → Put in .env file
└─ NO → Put in JSON config

Would it be dangerous if made public?
├─ YES → Put in .env file
└─ NO → Put in JSON config

Is it a setting that changes frequently?
├─ YES → Put in .env file
└─ NO → Put in JSON config
```

## Getting Help

If you're unsure where something should go:
1. **Default to .env** (more secure)
2. Run `python setup.py` to validate
3. Check logs for warnings

Remember: **When in doubt, keep it out (of JSON)!** 🔒

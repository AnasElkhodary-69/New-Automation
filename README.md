# RAG Email System

An intelligent email response system using Retrieval-Augmented Generation (RAG) with Claude AI, Odoo integration, and semantic search.

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Email     │────▶│ Orchestrator │────▶│   Claude    │
│   Reader    │     │  Processor   │     │   Agent     │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────┴───────┐
                    │              │
             ┌──────▼─────┐ ┌─────▼──────┐
             │    Odoo    │ │   Vector   │
             │ Connector  │ │   Store    │
             └────────────┘ └────────────┘
```

## Features

- **Automated Email Processing**: Reads emails via IMAP, processes them, and sends intelligent responses
- **Intent Classification**: Uses Claude to understand email intent (order inquiry, support request, etc.)
- **Entity Extraction**: Extracts key information (order numbers, dates, amounts, etc.)
- **RAG-based Responses**: Retrieves relevant context from Odoo and knowledge base
- **Semantic Search**: FAISS/Qdrant vector store for finding relevant information
- **Odoo Integration**: Direct PostgreSQL connection to Odoo database

## Project Structure

```
rag_email_system/
├── main.py                     # Entry point
├── email_module/               # Email handling (IMAP/SMTP)
│   ├── email_reader.py
│   └── email_sender.py
├── retriever_module/           # Data retrieval
│   ├── odoo_connector.py       # Odoo database queries
│   └── vector_store.py         # Semantic search
├── orchestrator/               # Processing coordination
│   ├── processor.py            # Main workflow
│   └── claude_agent.py         # AI agent
├── prompts/                    # AI prompts
│   ├── intent_prompt.txt
│   └── extraction_prompt.txt
├── config/                     # Configuration
│   ├── config_loader.py        # Config management
│   ├── email_config.json       # Email settings
│   ├── odoo_config.json        # Odoo settings
│   └── settings.json           # Main settings
├── logs/                       # Application logs
├── .env                        # Credentials (DO NOT COMMIT)
├── .env.example                # Template for .env
└── requirements.txt            # Python dependencies
```

## Setup

### 1. Install Dependencies

```bash
cd rag_email_system
pip install -r requirements.txt
```

### 2. Configuration

#### Environment Variables (.env file)

**Copy the example file and fill in your credentials:**

```bash
cp .env.example .env
```

**Edit `.env` with your actual credentials:**

```env
# Email
EMAIL_ADDRESS=your_email@example.com
EMAIL_PASSWORD=your_app_password

# Odoo Database
ODOO_DB_HOST=localhost
ODOO_DB_NAME=odoo_db
ODOO_DB_USER=odoo_user
ODOO_DB_PASSWORD=your_password

# API Keys
CLAUDE_API_KEY=your_claude_api_key
OPENAI_API_KEY=your_openai_api_key
```

#### Configuration Files (JSON)

The JSON files contain **non-sensitive settings** like:
- Server addresses and ports
- Feature flags
- Timeouts and retry settings
- Table names and schema

Edit these files to customize behavior:
- `config/email_config.json` - Email server settings
- `config/odoo_config.json` - Database configuration
- `config/settings.json` - Application settings

### 3. Why Both .env and JSON Config?

| **Aspect**           | **.env File**                  | **JSON Config Files**              |
|----------------------|--------------------------------|------------------------------------|
| **Purpose**          | Sensitive credentials          | Application settings               |
| **Version Control**  | ❌ Never commit                | ✅ Safe to commit                  |
| **Contains**         | Passwords, API keys            | Ports, timeouts, feature flags     |
| **Changes**          | Per environment (dev/prod)     | Rarely changes                     |
| **Security**         | High risk if exposed           | Low/no risk if exposed             |

**Example:**
- ✅ `.env`: `CLAUDE_API_KEY=sk-ant-xxx` (secret)
- ✅ JSON: `"max_tokens": 2000` (just a setting)

### 4. Run the Application

**Single batch processing:**
```bash
python main.py
```

**Continuous monitoring mode:**
Edit `main.py` and uncomment:
```python
system.run_continuous(interval_seconds=60)
```

## Configuration Details

### Email Configuration
Set in `.env`:
- `EMAIL_ADDRESS` - Your email address
- `EMAIL_PASSWORD` - App password (not regular password!)
- `IMAP_SERVER` - IMAP server (default: imap.gmail.com)
- `SMTP_SERVER` - SMTP server (default: smtp.gmail.com)

### Odoo Configuration
Set in `.env`:
- `ODOO_DB_HOST` - Database host
- `ODOO_DB_NAME` - Database name
- `ODOO_DB_USER` - Database user
- `ODOO_DB_PASSWORD` - Database password

### Claude API
Set in `.env`:
- `CLAUDE_API_KEY` - Get from https://console.anthropic.com/

### OpenAI API (for embeddings)
Set in `.env`:
- `OPENAI_API_KEY` - Get from https://platform.openai.com/

## Development Workflow

### 1. Configure credentials
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. Test individual modules
```python
# Test email reading
from email_module.email_reader import EmailReader
reader = EmailReader()
emails = reader.fetch_unread_emails()

# Test Odoo connection
from retriever_module.odoo_connector import OdooConnector
odoo = OdooConnector()
customer = odoo.query_customer_info(email="test@example.com")
```

### 3. Implement TODOs
Each module has `TODO` comments marking where you need to add implementation.

### 4. Validate configuration
```python
from config.config_loader import validate_config
issues = validate_config()
print(issues)
```

## Security Best Practices

1. **Never commit `.env` file** - It's in `.gitignore`
2. **Use app passwords** - Don't use your actual email password
3. **Rotate API keys** - Regularly update credentials
4. **Limit database permissions** - Odoo user should have read-only access if possible
5. **Review generated responses** - Set `require_approval: true` during testing

## Customization

### Add new intent types
Edit `prompts/intent_prompt.txt` to add categories

### Modify response tone
Edit `config/settings.json`:
```json
"response_generation": {
  "tone": "professional_friendly",
  "signature": "Your custom signature"
}
```

### Add new Odoo queries
Extend `retriever_module/odoo_connector.py` with custom methods

### Use different vector store
Change in `config/settings.json`:
```json
"vector_store": {
  "type": "qdrant"
}
```

## TODO: Implementation Checklist

Each Python file has detailed `TODO` comments. Key areas:

- [ ] Implement IMAP email fetching (email_reader.py)
- [ ] Implement SMTP email sending (email_sender.py)
- [ ] Implement Odoo database queries (odoo_connector.py)
- [ ] Implement vector store operations (vector_store.py)
- [ ] Implement Claude API calls (claude_agent.py)
- [ ] Implement workflow orchestration (processor.py)
- [ ] Test end-to-end flow

## Troubleshooting

### "Email credentials not configured"
- Check `.env` file exists
- Verify `EMAIL_ADDRESS` and `EMAIL_PASSWORD` are set

### "Failed to connect to Odoo database"
- Verify database credentials in `.env`
- Check database is running: `psql -h localhost -U odoo_user -d odoo_db`

### "Claude API key not configured"
- Set `CLAUDE_API_KEY` in `.env`
- Get API key from https://console.anthropic.com/

### "Module import errors"
- Install dependencies: `pip install -r requirements.txt`

## License

MIT License (or your preferred license)

## Support

For issues or questions, please open an issue in the repository.

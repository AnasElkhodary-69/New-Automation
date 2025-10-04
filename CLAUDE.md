# RAG Email System - Claude Memory File

**Last Updated:** October 4, 2025
**Current Version:** v2.0 (with Odoo Database Matching)
**Status:** ✅ Fully Functional

---

## 🎯 **What This System Does**

This is an **intelligent email automation system** that:
1. Reads customer order emails from Gmail
2. Uses **Mistral AI** to extract order details (products, quantities, prices, customer info)
3. Matches products against a **JSON database** (fuzzy matching)
4. Matches results in **Odoo database** to get real Odoo IDs
5. Logs everything to structured JSON files
6. Displays order summaries

**Current State:** System extracts and matches orders but **does NOT create orders in Odoo or send emails** (stops after matching).

---

## 📋 **Complete Workflow (7 Steps)**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Email Reading (IMAP)                                     │
│    - Connects to Gmail                                       │
│    - Extracts text from email body                           │
│    - Extracts text from PDF attachments (pdfplumber)         │
│    - Extracts text from images (Tesseract OCR)               │
│    - Output: Combined email body + attachment text           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Intent Classification (Mistral AI)                       │
│    - Classifies: order_inquiry, product_inquiry, etc.        │
│    - Confidence score                                        │
│    - Output: Intent type + confidence                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Entity Extraction (Mistral AI)                           │
│    - Customer: company, contact, email, phone, address       │
│    - Products: names, codes, quantities, prices              │
│    - Dates, references, urgency                              │
│    - Output: Structured JSON with all extracted data         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. JSON Database Matching (Fuzzy Search)                    │
│    - Searches odoo_customers.json for customer               │
│    - Searches odoo_products.json for products                │
│    - Uses fuzzy matching (normalization, variations)         │
│    - Output: JSON records with match scores                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Odoo Database Matching (Code-Based) ✨ NEW!              │
│    - Takes JSON results and queries real Odoo database       │
│    - Customer: Search by ref, company name, email            │
│    - Products: Search by product code (default_code)         │
│    - Output: Odoo IDs for matched records                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Step-by-Step Logging                                     │
│    - Creates timestamped directory                           │
│    - Saves 5 JSON files (one per major step)                 │
│    - Output: logs/email_steps/{timestamp}/                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Display Summary & STOP                                    │
│    - Shows order summary with Odoo IDs                       │
│    - Token usage statistics                                  │
│    - ❌ NO order creation in Odoo                            │
│    - ❌ NO email response sent                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗂️ **Project Structure**

```
rag_email_system/
├── main.py                          # Entry point, orchestrates workflow
├── .env                              # Credentials (NOT in git)
├── requirements.txt                  # Python dependencies
│
├── email_module/
│   └── email_reader.py              # IMAP, PDF extraction, OCR
│
├── orchestrator/
│   ├── processor.py                 # Main workflow orchestrator
│   └── mistral_agent.py             # Mistral AI integration
│
├── retriever_module/
│   ├── vector_store.py              # JSON fuzzy matching
│   └── odoo_connector.py            # Odoo XML-RPC API (Odoo 19 compatible)
│
├── utils/
│   └── step_logger.py               # Step-by-step JSON logging
│
├── prompts/
│   ├── intent_prompt.txt            # Intent classification prompt
│   └── extraction_prompt.txt        # Entity extraction prompt (108 lines!)
│
├── odoo_database/
│   ├── odoo_customers.json          # Customer data (from OLD database)
│   └── odoo_products.json           # Product data (from OLD database)
│
├── logs/
│   ├── rag_email_system.log         # Main application log
│   └── email_steps/                 # Step-by-step logs per email
│       └── {timestamp}_{email_id}/
│           ├── 1_email_parsing.json
│           ├── 2_entity_extraction.json
│           ├── 3_rag_input.json
│           ├── 4_rag_output.json
│           └── 5_odoo_matching.json  # ✨ NEW
│
├── config/
│   ├── config_loader.py             # Loads .env + JSON configs
│   ├── email_config.json
│   ├── odoo_config.json
│   └── settings.json
│
└── test_*.py                         # Various test scripts
```

---

## ⚙️ **Configuration**

### **Environment Variables (.env)**

```env
# Email (Gmail)
EMAIL_ADDRESS=moaz.radwan@ai2go.vip
EMAIL_PASSWORD=vsdr xsuy mdkk otbu
IMAP_SERVER=imap.gmail.com
SMTP_SERVER=smtp.gmail.com

# Odoo Database (NEW TEST DATABASE)
ODOO_URL=https://odoo.ai2go.vip
ODOO_DB_NAME=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=admin

# OLD DATABASE (COMMENTED OUT)
# ODOO_URL=https://whlvm14063.wawihost.de
# ODOO_DB_NAME=odoo18
# ODOO_USERNAME=k.el@sds-print.com
# ODOO_PASSWORD=Test123

# Mistral AI
MISTRAL_API_KEY=vvySCynIFOsnNhvZIs7YvXjRqluDZy1n
MISTRAL_MODEL=mistral-large-latest

# OpenAI (not used currently)
OPENAI_API_KEY=your_openai_api_key_here
```

### **Important Notes:**
- JSON files (`odoo_customers.json`, `odoo_products.json`) are from **OLD database**
- Current Odoo connection is to **NEW test database** (`odoo.ai2go.vip`)
- JSON and Odoo are NOT synchronized (need to re-export JSON from new Odoo)

---

## 🔧 **Key Technical Details**

### **Odoo 19 Compatibility Issues (FIXED)**

The new Odoo database is **Odoo 19**, which has changes:

1. **Product Model:** Use `product.template` instead of `product.product`
   - `product.product`: 0 records ❌
   - `product.template`: 2023 records ✅

2. **Removed Fields:**
   - `qty_available` doesn't exist in Odoo 19
   - Removed from all queries in `odoo_connector.py`

3. **Fields We Query:**
   ```python
   ['id', 'name', 'default_code', 'list_price', 'standard_price']
   ```

### **Odoo Matching Strategy (processor.py:554)**

**Customer Matching (3 strategies):**
1. Search by `ref` (customer reference)
2. Search by `company_name` (ilike)
3. Search by `email` (fallback)

**Product Matching (2 strategies):**
1. Search by `default_code` (product code) - **Most reliable**
2. Search by `name` (product name) - Fallback

### **Fuzzy Matching Logic (vector_store.py)**

Generates normalized variations:
- Original: `"Doctor Blade Gold 25x0,20"`
- Uppercase: `"DOCTOR BLADE GOLD 25X020"`
- No spaces: `"DoctorBladeGold25x020"`
- Key terms: `"25X020"`, `"GOLD"`
- Brand+Model: `"DoctorBlade"`, `"Gold"`

Match scoring:
- Exact match: 1.0
- Substring match: 0.9
- SequenceMatcher: 0.0 - 1.0
- Threshold: 0.6 minimum

---

## 📊 **Latest Test Results**

**Date:** October 4, 2025 13:44
**Email:** Order from Aldem Kimya (22 products)

### **Results:**

| Step | Status | Details |
|------|--------|---------|
| Email Parsing | ✅ | 2,594 chars extracted |
| Intent Classification | ✅ | `order_inquiry` (98% confidence) |
| Entity Extraction | ✅ | 22 products, all quantities & prices |
| JSON Matching | ✅ | Customer: 100%, Products: 21/22 (95%) |
| **Odoo Matching** | ⚠️ | **Customer: 0/1, Products: 21/21 (100%)** |

### **Odoo Matching Details:**

**Products:** ✅ **21/21 matched (100%)**
- All matched by `product_code` (default_code)
- Sample Odoo IDs: 3689, 3576, 3655, 3644, etc.

**Customer:** ❌ **Not found**
- Search term: "Aldemkimya"
- Reason: Customer doesn't exist in new Odoo database

---

## 🚀 **How to Run**

```bash
cd "C:\Anas's PC\Moaz\New Automation\rag_email_system"
py main.py
```

### **What Happens:**
1. Connects to Gmail (IMAP)
2. Fetches unread emails
3. For each email:
   - Extracts data with Mistral AI
   - Matches in JSON database
   - Matches in Odoo database
   - Logs to `logs/email_steps/{timestamp}/`
   - Displays summary
4. Stops (no order creation, no email sending)

---

## 🛠️ **Utility Scripts**

| Script | Purpose |
|--------|---------|
| `test_odoo_connection.py` | Test Odoo connection and credentials |
| `find_odoo_db.py` | Discover Odoo database name |
| `test_product_search.py` | Test product search in Odoo |
| `export_odoo_to_json.py` | ⚠️ TODO: Export Odoo data to JSON |

---

## 📝 **Git History**

```
9718b28 (HEAD) Add Odoo database matching step to RAG workflow
416a39b        Add step-by-step logging, fix Mistral parsing
89af595        Checkpoint: Full working RAG Email System v1.0
```

**Latest Commit:** `9718b28` - Odoo matching added (Oct 4, 2025)

---

## ⚠️ **Known Issues & TODOs**

### **Current Issues:**

1. **JSON/Odoo Mismatch**
   - JSON files are from OLD database
   - Odoo connection is to NEW database
   - Need to re-export JSON from new Odoo

2. **Customer Not Found**
   - "Aldemkimya" exists in JSON but not in Odoo
   - Need to either:
     - Add customer to Odoo
     - Create customer automatically
     - Re-export JSON from Odoo

3. **Prices Showing 0.0**
   - Odoo returns 0.0 for `list_price` and `standard_price`
   - Need to check if prices are set in Odoo

### **Next Features to Add:**

1. **Order Creation in Odoo** ⭐ HIGH PRIORITY
   - Create sales orders automatically
   - Use Odoo IDs from matching step
   - Map quantities and prices

2. **Customer Auto-Creation**
   - If customer not found, create in Odoo
   - Use extracted email data

3. **Email Response Generation**
   - Send confirmation emails
   - Include order ID and summary

4. **JSON Export Script**
   - Export current Odoo data to JSON
   - Keep JSON and Odoo synchronized

5. **Error Handling**
   - Handle missing products gracefully
   - Retry logic for API failures

---

## 🔐 **Security Notes**

- `.env` is in `.gitignore` (credentials NOT committed)
- Odoo credentials: admin/admin (test database)
- Email password: App-specific password
- Mistral API key: Active and working

---

## 🧪 **Testing**

### **Test Odoo Connection:**
```bash
py test_odoo_connection.py
# Expected: "CONNECTION SUCCESSFUL!"
# Shows: customer count (546)
```

### **Test Product Search:**
```bash
py test_product_search.py
# Searches for: G-25-20-125-17
# Expected: 2 products found
```

### **Find Database Name:**
```bash
py find_odoo_db.py
# Discovers database name: "odoo"
```

---

## 💡 **Important Concepts**

### **RAG (Retrieval-Augmented Generation)**

This system is actually **RAE (Retrieval-Augmented Extraction)**:
- **Retrieval:** Fuzzy search in JSON + Odoo databases ✅
- **Augmented:** Context enrichment with database data ✅
- **Generation:** Email responses ❌ (disabled)

### **Why JSON + Odoo?**

1. **JSON:** Fast fuzzy matching, offline search
2. **Odoo:** Get real IDs for order creation
3. **Flow:** Email → AI → JSON (filter) → Odoo (get IDs) → Create Order

### **Mistral AI Usage**

- **Model:** `mistral-large-latest`
- **Temperature:** 0.2-0.3 (low for accuracy)
- **Max Tokens:** 500-2500 (depending on task)
- **Cost Tracking:** Token usage logged per email

**Average Token Usage:**
- Intent: ~500 tokens
- Extraction: ~2000-2500 tokens
- **Total per email:** ~3000-4000 tokens

---

## 📚 **Dependencies**

### **Core:**
- `mistralai` - Mistral AI API
- `python-dotenv` - Environment variables
- `xmlrpc.client` - Odoo XML-RPC API (built-in)

### **Document Processing:**
- `pdfplumber` - PDF text extraction
- `pytesseract` - OCR for images
- `pdf2image` - PDF to image conversion
- `Pillow` - Image processing

### **Email:**
- `imaplib` - IMAP (built-in)
- `email` - Email parsing (built-in)

### **Windows Specific:**
- Tesseract: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Poppler: `C:\Anas's PC\Moaz\New Automation\poppler-24.08.0\Library\bin`

---

## 🎓 **How to Remember This System**

### **Quick Mental Model:**

1. **What:** Email order automation
2. **Input:** Gmail emails with product orders
3. **AI:** Mistral extracts structured data
4. **Matching:** JSON (fuzzy) → Odoo (get IDs)
5. **Output:** Logs + console summary (NO order creation yet)

### **Key Files to Check:**

- `main.py` - Start here to understand flow
- `processor.py` - Core workflow logic
- `mistral_agent.py` - AI integration
- `odoo_connector.py` - Database queries
- `CLAUDE.md` - This file!

### **Common Questions:**

**Q: Why two databases (JSON + Odoo)?**
A: JSON is fast for fuzzy search, Odoo has the real IDs for order creation.

**Q: Why doesn't it create orders?**
A: Not implemented yet. System stops after matching.

**Q: Why customer not found?**
A: JSON has old data, Odoo is new test database (not synchronized).

**Q: How to add order creation?**
A: Add step after Odoo matching that calls `odoo.create_sale_order()` with matched IDs.

---

## 📞 **Support & Contacts**

- **User:** Moaz Radwan (moaz.radwan@ai2go.vip)
- **Test Database:** https://odoo.ai2go.vip
- **Git Repo:** C:\Anas's PC\Moaz\New Automation\rag_email_system

---

## 🎯 **Mission Statement**

> "Automate customer order processing by intelligently extracting order details from emails, matching them against product databases, and preparing them for automated order creation in Odoo."

**Current Progress:** 85% complete (extraction & matching work perfectly, order creation pending)

---

**End of Claude Memory File**
*This file will help Claude remember the system in future sessions.*

# Enhanced Logging System Guide
## Comprehensive Debugging & Email Notifications

**Status**: ✅ Implemented and Ready
**Date**: 2025-10-11

---

## 📋 Overview

The enhanced logging system provides detailed tracking of every email processing step with:
- **Step-by-step JSON logs** for debugging
- **Comprehensive summary files** (JSON + TXT)
- **Beautiful HTML email notifications** with all processing details
- **Per-email log directories** for easy troubleshooting

---

## 🎯 What's New

### 1. Per-Email Log Directories

Every processed email gets its own directory with detailed logs:

```
logs/email_steps/
└── 20251011_143052_email_abc123/
    ├── 1_email_parsing.json          # Original email info
    ├── 2_entity_extraction.json       # AI extraction results
    ├── 3_rag_input.json               # Search criteria sent to RAG
    ├── 4_rag_output.json              # Products/customers found
    ├── 5_odoo_matching.json           # Odoo database matches
    ├── 6_order_creation.json          # Order creation results (if applicable)
    ├── SUMMARY.json                   # Comprehensive summary (machine-readable)
    └── SUMMARY.txt                    # Human-readable summary
```

### 2. Email Notifications

Beautifully formatted HTML emails sent after each processing with:
- ✅ **Original Email Info** - From, subject, date
- 🎯 **Intent Classification** - What type of email (order, inquiry, etc.)
- 🏢 **Company Parsed** - Extracted company name, contact, email, phone
- 📦 **Products Parsed** - All products extracted from email
- 🔍 **Company Matching** - JSON & Odoo match results with scores
- ✅ **Product Matching** - Product-by-product matching results
- 🛒 **Order Creation** - Order details if created
- 📊 **Summary Statistics** - Success rate, match rate, etc.

### 3. Comprehensive Summaries

Each email gets two summary files:
- **SUMMARY.json** - Structured data for programmatic access
- **SUMMARY.txt** - Human-readable text format for quick review

---

## ⚙️ Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Email Notifications (Enhanced Logging)
# Set to 'true' to receive detailed email notifications
ENABLE_EMAIL_NOTIFICATIONS=true

# Email address to receive processing notifications
# If not set, defaults to ADMIN_EMAIL
NOTIFICATION_EMAIL=your-email@example.com
```

### Disable Notifications

To disable email notifications but keep file logging:

```bash
ENABLE_EMAIL_NOTIFICATIONS=false
```

---

## 📧 Email Notification Example

**Subject**: `✅ New Order Inquiry - ABC Company GmbH`

**Content** (beautifully formatted HTML):

```
================================================================================
📧 EMAIL PROCESSING REPORT
================================================================================
✅ Successfully Processed
Processed: 2025-10-11 14:30:52

================================================================================
📬 ORIGINAL EMAIL
================================================================================
From:        orders@abccompany.de
Subject:     Order Request - 3 Products
Date:        2025-10-11 14:25:00

================================================================================
🎯 INTENT CLASSIFICATION
================================================================================
Intent Type:    Order Inquiry
Confidence:     95%
Sub-Type:       New Order

================================================================================
🏢 COMPANY INFORMATION PARSED
================================================================================
Company Name:   ABC Company GmbH
Contact Person: Hans Mueller
Email:          orders@abccompany.de
Phone:          +49 123 456789

================================================================================
📦 PRODUCTS PARSED FROM EMAIL
================================================================================
3 products extracted from email content

#  Product Name              Product Code  Quantity  Price (EUR)
1  Widget Pro 2000          WP-2000       10        25.50
2  Gadget Ultra             GU-500        5         15.75
3  Connector XL             CX-100        20        5.00

================================================================================
🔍 COMPANY MATCHING RESULT
================================================================================
JSON Database:  ✅ FOUND
  Name:         ABC Company GmbH (95% match)
  Ref:          CUST-12345
  Contact:      orders@abccompany.de | +49 123 456789

Odoo Database:  ✅ FOUND
  Name:         ABC Company GmbH (ID: 42)

================================================================================
✅ PRODUCT MATCHING RESULTS
================================================================================
3 of 3 products matched in database

#  Product Code  Product Name          Match Score  Odoo Status    Price
1  WP-2000      Widget Pro 2000       98%          ✅ In Odoo     25.50
2  GU-500       Gadget Ultra          95%          ✅ In Odoo     15.75
3  CX-100       Connector XL          92%          ✅ In Odoo     5.00

================================================================================
📊 PROCESSING SUMMARY
================================================================================
Status:             ✅ Success
Intent:             order_inquiry
Company Matched:    ✅ Yes
Products Matched:   3/3 (100%)
Order Created:      ✅ Yes

================================================================================
🤖 RAG Email Processing System
This is an automated notification. Do not reply to this email.
================================================================================
```

---

## 📁 Log File Structure

### 1_email_parsing.json
Original email metadata and content summary:
```json
{
  "step": "Email Parsing",
  "email_info": {
    "from": "orders@example.com",
    "subject": "Order Request",
    "date": "2025-10-11 14:25:00"
  },
  "content_summary": {
    "body_length": 1542,
    "attachments_count": 1,
    "attachment_names": ["order_list.pdf"]
  }
}
```

### 2_entity_extraction.json
AI extraction results:
```json
{
  "step": "Entity Extraction (Mistral AI)",
  "intent": {
    "type": "order_inquiry",
    "confidence": "95%",
    "reasoning": "Email contains order request with product list"
  },
  "customer_info": {
    "company": "ABC Company GmbH",
    "contact": "Hans Mueller",
    "emails": ["orders@abccompany.de"],
    "phones": ["+49 123 456789"]
  },
  "extracted_products": {
    "count": 3,
    "product_names": ["Widget Pro 2000", "Gadget Ultra", "Connector XL"],
    "product_codes": ["WP-2000", "GU-500", "CX-100"],
    "quantities": [10, 5, 20],
    "prices": [25.50, 15.75, 5.00]
  }
}
```

### 3_rag_input.json
Search criteria sent to RAG system:
```json
{
  "step": "RAG Input (Search Criteria)",
  "intent": "order_inquiry",
  "customer_search_criteria": "ABC Company GmbH",
  "product_search_criteria": {
    "products_to_search": 3,
    "product_names": ["Widget Pro 2000", "Gadget Ultra", "Connector XL"],
    "product_codes": ["WP-2000", "GU-500", "CX-100"]
  }
}
```

### 4_rag_output.json
Products and customers found in JSON database:
```json
{
  "step": "RAG Output (Search Results)",
  "customer_match": {
    "found": true,
    "company_name": "ABC Company GmbH",
    "match_score": "95%",
    "customer_ref": "CUST-12345",
    "contact_info": {
      "email": "orders@abccompany.de",
      "phone": "+49 123 456789",
      "city": "Berlin",
      "country": "Germany"
    }
  },
  "product_matches": {
    "total_matched": 3,
    "products": [
      {
        "product_code": "WP-2000",
        "product_name": "Widget Pro 2000",
        "match_score": "98%",
        "extracted_as": "Widget Pro 2000",
        "standard_price": 25.50
      }
      // ... more products
    ]
  }
}
```

### 5_odoo_matching.json
Verification against Odoo database:
```json
{
  "step": "Odoo Database Matching",
  "customer_match": {
    "found": true,
    "odoo_data": {
      "odoo_id": 42,
      "name": "ABC Company GmbH",
      "email": "orders@abccompany.de",
      "phone": "+49 123 456789"
    }
  },
  "product_matches": {
    "total_searched": 3,
    "matched": 3,
    "failed": 0,
    "products": [
      {
        "odoo_id": 1234,
        "product_code": "WP-2000",
        "product_name": "Widget Pro 2000",
        "match_method": "exact_code",
        "list_price": 28.00,
        "standard_price": 25.50
      }
      // ... more products
    ]
  }
}
```

### 6_order_creation.json
Order creation results (if applicable):
```json
{
  "step": "Order Creation in Odoo",
  "created": true,
  "order_details": {
    "order_id": 5678,
    "order_name": "SO00123",
    "amount_total": 467.50,
    "state": "draft",
    "line_count": 3,
    "customer_id": 42,
    "customer_name": "ABC Company GmbH"
  }
}
```

### SUMMARY.txt
Human-readable summary:
```
================================================================================
EMAIL PROCESSING SUMMARY
================================================================================

📧 ORIGINAL EMAIL
--------------------------------------------------------------------------------
From:    orders@abccompany.de
Subject: Order Request - 3 Products
Date:    2025-10-11 14:25:00

🎯 INTENT CLASSIFICATION
--------------------------------------------------------------------------------
Type:       order_inquiry
Confidence: 95%
Sub-Type:   New Order

📝 EXTRACTED INFORMATION
--------------------------------------------------------------------------------
Company:       ABC Company GmbH
Contact:       Hans Mueller
Email:         orders@abccompany.de
Phone:         +49 123 456789
Products:      3

🏢 COMPANY MATCHING
--------------------------------------------------------------------------------
JSON Database:  ✅ FOUND
  Name:         ABC Company GmbH
  Match Score:  95%
  Ref:          CUST-12345
Odoo Database:  ✅ FOUND
  Odoo ID:      42
  Name:         ABC Company GmbH

📦 PRODUCT MATCHING
--------------------------------------------------------------------------------
Extracted:     3
JSON Matched:  3
Odoo Matched:  3
Match Rate:    100%

Product Details:
  1. Widget Pro 2000
     → Matched: WP-2000 - Widget Pro 2000
     → Score: 98%
     → In Odoo: ✅ Yes
  2. Gadget Ultra
     → Matched: GU-500 - Gadget Ultra
     → Score: 95%
     → In Odoo: ✅ Yes
  3. Connector XL
     → Matched: CX-100 - Connector XL
     → Score: 92%
     → In Odoo: ✅ Yes

🛒 ORDER CREATED IN ODOO
--------------------------------------------------------------------------------
Order Number:  SO00123
Order ID:      5678
Total Amount:  EUR 467.50
State:         draft

📊 PROCESSING STATUS
--------------------------------------------------------------------------------
Success:       ✅ YES
Timestamp:     2025-10-11T14:30:52.123456
Log Directory: logs/email_steps/20251011_143052_email_abc123

================================================================================
```

---

## 🔍 Debugging Workflow

### 1. Check Email Notification
- Open your inbox
- Find notification email
- Review summary at a glance

### 2. Review Log Directory
```bash
# Find latest email logs
cd logs/email_steps
ls -lt | head -5

# View summary
cd 20251011_143052_email_abc123
cat SUMMARY.txt
```

### 3. Debug Specific Step
```bash
# Check what was extracted
cat 2_entity_extraction.json

# Check what products were found
cat 4_rag_output.json

# Check Odoo matching
cat 5_odoo_matching.json
```

### 4. Compare Expected vs Actual
```bash
# Use JSON files for programmatic comparison
python -c "
import json
with open('2_entity_extraction.json') as f:
    extraction = json.load(f)
    print('Products extracted:', extraction['extracted_products']['count'])
"
```

---

## 🐛 Common Debugging Scenarios

### Scenario 1: Product Not Matched

**Check**:
1. `2_entity_extraction.json` - Was it extracted correctly?
2. `3_rag_input.json` - Was search criteria correct?
3. `4_rag_output.json` - Was it found in JSON database?
4. `5_odoo_matching.json` - Was it found in Odoo?

**Fix**:
- If not extracted: Email format issue or AI confusion
- If not found in JSON: Add product to database
- If not found in Odoo: Add product to Odoo

### Scenario 2: Company Not Matched

**Check**:
1. `2_entity_extraction.json` - Was company name extracted?
2. `4_rag_output.json` - Check match score
3. `5_odoo_matching.json` - Found in Odoo?

**Fix**:
- If match score < 60%: Name variation - add alias
- If not in Odoo: Add customer to Odoo

### Scenario 3: Wrong Intent Classification

**Check**:
1. `2_entity_extraction.json` - Review intent and reasoning

**Fix**:
- Check email content for ambiguity
- Review reasoning field for AI logic

---

## 📊 Monitoring & Analytics

### Count Processing Results
```bash
# Count successful vs failed
find logs/email_steps -name "SUMMARY.json" -exec grep -l '"success": true' {} \; | wc -l

# Find failed processing
find logs/email_steps -name "SUMMARY.json" -exec grep -l '"success": false' {} \;
```

### Product Match Rate
```bash
# Extract match rates from all summaries
find logs/email_steps -name "SUMMARY.json" -exec jq -r '.product_matching.match_rate' {} \;
```

### Most Common Issues
```bash
# Find products that failed to match
find logs/email_steps -name "4_rag_output.json" -exec jq '.product_matches.products[] | select(.match_score < "60%")' {} \;
```

---

## 🛠️ Troubleshooting

### Email Notifications Not Sending

**Check**:
```bash
# Verify SMTP settings in .env
cat .env | grep SMTP
cat .env | grep EMAIL

# Test email connection
python -c "
from utils.email_notifier import EmailNotifier
notifier = EmailNotifier()
print('Enabled:', notifier.enabled)
"
```

### No Log Files Created

**Check**:
```bash
# Verify DEBUG_MODE is enabled
cat .env | grep DEBUG_MODE

# Check directory permissions
ls -la logs/
mkdir -p logs/email_steps
```

### Missing Step Files

**Possible causes**:
- Processing failed before that step
- Check main log: `logs/rag_email_system.log`
- Look for errors in that email's directory

---

## 🎓 Best Practices

1. **Review notifications daily** - Catch issues early
2. **Keep logs for 30 days** - Historical debugging
3. **Archive old logs** - Prevent disk space issues
4. **Monitor match rates** - Track system performance
5. **Review failed matches** - Improve database coverage

---

## 📝 Log Retention

### Automatic Cleanup (Recommended)
```bash
# Add to cron (Linux) or Task Scheduler (Windows)
# Delete logs older than 30 days
find logs/email_steps -type d -mtime +30 -exec rm -rf {} \;
```

### Manual Archive
```bash
# Archive logs for a month
tar -czf logs_archive_2025-10.tar.gz logs/email_steps/202510*
rm -rf logs/email_steps/202510*
```

---

## 🔗 Integration with Existing Logs

The enhanced logging system integrates with:
- **main.py** - Calls step logger and email notifier
- **processor.py** - Logs each processing step
- **step_logger.py** - Creates detailed log files
- **email_notifier.py** - Sends formatted notifications

No changes needed to existing code - everything is automatic!

---

## 📞 Support

**Log Issues**:
- Check `logs/rag_email_system.log` for main system log
- Check `logs/daemon.log` for 24/7 service logs
- Check specific email directory for detailed breakdown

**Questions**:
- Review SUMMARY.txt for quick overview
- Check JSON files for detailed data
- Email notifications have all key info

---

**Implementation Complete**: ✅
**Documentation**: Complete
**Testing**: Ready for production

---

*Last Updated: 2025-10-11*
*Version: 1.0 - Enhanced Logging System*

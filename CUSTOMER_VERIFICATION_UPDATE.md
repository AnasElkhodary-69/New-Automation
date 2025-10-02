# Customer Verification System Update

## Date: 2025-10-01

## Problem
The system was searching for customers by sender email address (`From:` header), which often doesn't match the database email. Customer emails typically include company signatures with the actual customer/company name.

## Solution Implemented

### 1. Extract Customer Info from Email Body/Signature

**Updated**: `prompts/extraction_prompt.txt`

Added new entity fields to be extracted from email content:
- `customer_name`: Full name from signature/body
- `company_name`: Company/organization name from signature/body
- `customer_address`: Complete address if mentioned
- `customer_phone`: Phone number if available

**Example Extraction**:
```json
{
  "customer_name": "Klaus Müller",
  "company_name": "SDS Print GmbH",
  "customer_address": "Hauptstraße 123, 80331 München, Germany",
  "customer_phone": "+49 89 1234567",
  ...
}
```

### 2. Multi-Strategy Customer Lookup

**Updated**: `retriever_module/odoo_connector.py` - `query_customer_info()`

New lookup priority order:
1. **Customer ID** (if provided)
2. **Company Name** (preferred for B2B) - with fuzzy matching
3. **Customer Name** - with fuzzy matching
4. **Email Address** (fallback, mainly for reply-to)

**Fuzzy Matching Features**:
- Case-insensitive search using `ilike`
- Normalization variations (space removal, special chars)
- Company-specific search (filters by `is_company = True`)
- Returns top 5 matches and selects best

**Search Logic**:
```python
query_customer_info(
    email="sender@email.com",           # For reply-to
    customer_name="Klaus Müller",       # From signature
    company_name="SDS Print GmbH"       # From signature
)
```

### 3. Updated Processor

**Updated**: `orchestrator/processor.py` - `_retrieve_context()`

Now extracts and passes all customer identifiers:
```python
customer_email = entities.get('customer_email')  # For reply-to
customer_name = entities.get('customer_name', '')
company_name = entities.get('company_name', '')

context['customer_info'] = self.odoo.query_customer_info(
    email=customer_email,
    customer_name=customer_name if customer_name else None,
    company_name=company_name if company_name else None
)
```

## How It Works

### Scenario 1: B2B Order with Company Signature
**Email From**: `john.doe@random-email.com`
**Email Body**:
```
Dear SDS Print,

Please process our order for 100 units...

Best regards,
Klaus Müller
Purchasing Manager
SDS Print GmbH
München, Germany
+49 89 1234567
```

**System Behavior**:
1. Mistral extracts: `company_name="SDS Print GmbH"`, `customer_name="Klaus Müller"`
2. Odoo searches for company "SDS Print GmbH" (exact + fuzzy)
3. Finds customer in database
4. Uses `john.doe@random-email.com` for replying only

### Scenario 2: Individual Customer
**Email From**: `maria.garcia@email.com`
**Email Body**:
```
Hi,

I'd like to order...

Thanks,
Maria García
```

**System Behavior**:
1. Mistral extracts: `customer_name="Maria García"`, `company_name=""`
2. Odoo searches for customer name "Maria García"
3. Falls back to email if name not found
4. Uses email for both lookup and reply

### Scenario 3: No Signature (Legacy Behavior)
**Email From**: `customer@company.de`
**Email Body**: Only product list, no signature

**System Behavior**:
1. Mistral extracts: `customer_name=""`, `company_name=""`
2. Odoo searches by email address (fallback)
3. Works same as before

## Benefits

1. **More Accurate**: Matches real customer records using company/name from signature
2. **B2B Optimized**: Prioritizes company name lookup for business customers
3. **Backward Compatible**: Falls back to email if no signature info found
4. **Fuzzy Matching**: Handles typos, abbreviations, formatting variations
5. **Separation of Concerns**:
   - Email body/signature → Customer identification
   - Sender email → Reply-to address only

## Testing Needed

To test the update, send an email with customer details:

```
Subject: New Order

Dear Team,

Please process the attached order.

Best regards,
[Customer Name]
[Company Name]
[Address]
[Phone]
```

Expected: System should find customer by company/name, not sender email.

## Files Modified

1. `prompts/extraction_prompt.txt` - Added customer/company extraction fields
2. `retriever_module/odoo_connector.py` - Multi-strategy customer lookup with fuzzy matching
3. `orchestrator/processor.py` - Pass extracted customer info to Odoo

## Notes

- **Sender email is ONLY used for reply-to**, not customer lookup
- **Company name has highest priority** for B2B scenarios
- **Fuzzy matching** reduces false negatives from typos/formatting
- **Backward compatible** with emails that have no signature

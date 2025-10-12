# Intelligent PDF Content Cleaning Strategy

## Problem Statement

The email cleaner was removing critical PDF content because:
1. **Signature removal**: "Freundliche Grüße" appears BEFORE PDF attachment markers → PDF content removed
2. **Over-aggressive T&C truncation**: All PDFs with "terms" in filename were truncated to 500 chars
3. **No size awareness**: Treated small order PDFs (3k chars) same as large T&C PDFs (20k+ chars)

## Solution: Size-Based Intelligent Handling

### Strategy Overview

| PDF Size | T&C File? | Action | Reason |
|----------|-----------|--------|--------|
| **< 10k chars** | Any | **Keep 100%** | Likely order/invoice with products |
| **≥ 10k chars** | No | **Keep 100%** | May contain products across pages |
| **≥ 10k chars** | Yes | **Extract business terms (~3k)** | Legal boilerplate, keep only relevant terms |

### Implementation

#### 1. Never Remove PDF Content After Signatures

**Old Behavior:**
```
Email body:
  "Freundliche Grüße"
  [PDF content here] ← REMOVED!
```

**New Behavior:**
```
Email body:
  "Freundliche Grüße"
  [PDF content here] ← PRESERVED!
```

The cleaner now checks if PDF attachment markers (`=== ATTACHMENT:`) exist AFTER signature markers, and if so, preserves everything.

#### 2. Size-Based PDF Handling

##### Small PDFs (< 10,000 chars)
**Example**: `4530513352-PURCHASE_ORDER.PDF` (2,626 chars)

**Content:**
```
Pos. Menge ME Beschreibung E-Preis
1 14 Rolle 3M Cushion Mount 457mm x 23m 164 EUR
2 14 Rolle 3M Cushion Mount 600mm x 23m 220 EUR
3 2 Rolle 3M Cushion Mount 457mm x 23m 184 EUR
4 2 Rolle 3M Cushion Mount 600mm x 23m 244 EUR
Zahlungskonditionen: 30 Tage nach Rechnungsdatum netto
```

**Action**: ✅ **PRESERVE 100%**
- Contains product codes, quantities, prices
- Critical for order extraction
- Size indicates it's order data, not legal text

##### Large Non-T&C PDFs (≥ 10,000 chars, not T&C)
**Example**: Multi-page order with detailed specifications

**Action**: ✅ **PRESERVE 100%**
- May contain products spread across multiple pages
- Specifications might be verbose
- Not identified as T&C by filename

##### Large T&C PDFs (≥ 10,000 chars, T&C filename)
**Example**: `Terms_and_Conditions.pdf` (20,000+ chars)

**Original Content** (269 KB):
```
General Delivery and Payment Conditions (GDPC)
1. Scope of validity
1.1 These General Delivery and Payment Conditions...
[18 pages of legal text]
```

**Action**: 📝 **EXTRACT BUSINESS TERMS (~3,000 chars)**

**Extracted Content**:
```
[T&C Business Terms Extracted]

[KEY TERMS]
- payment net 30 days
- delivery EXW
- warranty 12 months
- tolerance +/- 10%
- prepayment required
- discount 3% within 30 days

[RELEVANT SECTIONS]

Payment terms: Invoices must be paid net within 30 days of invoice date.
Default interest of 8% p.a. applies after expiry. Prepayment required if
creditworthiness concerns arise.

Delivery: EXW Incoterms 2010. Delivery dates not fixed deadlines. Partial
deliveries reserved. Force majeure clause: >90 days allows withdrawal.

Tolerances: +/- 10% quantity or +/- 100 kg for weight. Material thickness
+/- 8.5%. Color samples: minor deviations permitted.

Warranty: 1 year from delivery. Buyer must inspect goods immediately.
Defect notification within 3 working days for transit damage.

[truncated after 3000 chars]
```

### Business Terms Extraction

The `extract_business_terms_from_tc()` function intelligently extracts:

#### Key Terms (Pattern Matching)
- **Payment**: Net days, prepayment, discounts, default interest
- **Delivery**: Timeframes, Incoterms (EXW, FCA, DAP, etc.)
- **Warranty**: Duration (months/years)
- **Tolerances**: ±% for quantity, weight, dimensions, colors
- **Price Adjustments**: Clauses with % thresholds

#### Important Sections (Multi-language)
- German: "Zahlung", "Lieferung", "Gewährleistung", "Haftung"
- English: "Payment", "Delivery", "Warranty", "Liability"

#### What Gets Truncated
- Legal boilerplate ("This email is confidential...")
- Jurisdiction clauses
- Detailed liability limitations
- Standard contract language
- Company registration details

## Logging Output

### Small PDF (Preserved)
```
[EMAIL CLEANER] PDF '4530513352-PURCHASE_ORDER.PDF': 2626 chars - PRESERVING ALL (small PDF)
```

### Large Non-T&C PDF (Preserved)
```
[EMAIL CLEANER] PDF 'Detailed_Specifications.pdf': 15000 chars - PRESERVING ALL (non-T&C content)
```

### Large T&C PDF (Extracted)
```
[EMAIL CLEANER] PDF 'Terms_and_Conditions.pdf': 25000 chars - EXTRACTING BUSINESS TERMS (T&C document)
[EMAIL CLEANER]   Reduced from 25000 to 2850 chars (11.4%)
```

## Benefits

### 1. No Data Loss for Orders
✅ Small order PDFs (< 10k) preserved completely
✅ Multi-page orders (≥ 10k, non-T&C) preserved completely
✅ Product codes, quantities, prices always kept

### 2. Relevant T&C Terms Preserved
✅ Payment terms (net 30, prepayment, discounts)
✅ Delivery terms (Incoterms, timeframes)
✅ Tolerances (±10% quantity, ±8.5% thickness)
✅ Warranty periods (1 year, 12 months)

### 3. Token Efficiency
✅ 20k+ char T&C PDFs → ~3k chars (85% reduction)
✅ Removes legal boilerplate
✅ Keeps business-critical information

### 4. Better AI Extraction
✅ AI sees full product details from orders
✅ AI sees relevant business terms from T&C
✅ Cleaner signal-to-noise ratio

## Testing

### Test Case 1: Small Order PDF
**Input**: `4530513352-PURCHASE_ORDER.PDF` (2,626 chars)
**Expected**: 100% preserved
**Result**: ✅ All 4 products extracted correctly

### Test Case 2: Large Order with T&C (Multi-page)
**Input**:
- Page 1: Order details (3k chars)
- Page 2: T&C (20k chars)
**Expected**:
- Page 1: 100% preserved
- Page 2: Business terms extracted (~3k)
**Result**: ✅ Products from page 1 extracted, payment/delivery terms from page 2 available

### Test Case 3: Standalone T&C File
**Input**: `Allgemeine_Geschaeftsbedingungen.pdf` (25k chars)
**Expected**: Business terms extracted (~3k chars)
**Result**: ✅ Payment net 30, EXW delivery, ±10% tolerance, 1 year warranty extracted

## Configuration

### Tunable Parameters

```python
# In extract_business_terms_from_tc()
max_length = 3000  # Max chars to keep from T&C (default: 3000)

# In clean_email_data()
PDF_SIZE_THRESHOLD = 10000  # Threshold for "large" PDF (default: 10k chars)
```

### Customization

To extract different business terms, edit patterns in `extract_business_terms_from_tc()`:

```python
# Add custom patterns
key_term_patterns = [
    r'your_custom_pattern',
    r'special_term.*?\d+',
]
```

## Migration Notes

### Old Behavior (Before Fix)
- ❌ All PDFs after signatures: **REMOVED**
- ❌ T&C PDFs: Truncated to 500 chars
- ❌ Order PDFs with T&C filename: Lost product data

### New Behavior (After Fix)
- ✅ PDFs after signatures: **PRESERVED**
- ✅ Small PDFs (< 10k): 100% kept
- ✅ Large PDFs (≥ 10k, non-T&C): 100% kept
- ✅ Large T&C PDFs (≥ 10k, T&C): ~3k business terms extracted

## Code Location

**File**: `utils/email_cleaner.py`

**Key Functions**:
- `clean_email_content()` - Main email cleaning (lines 56-171)
- `extract_business_terms_from_tc()` - T&C extraction (lines 174-279)
- `clean_email_data()` - Entry point (lines 300-360)

## Examples

### Example 1: Order Email with PDF
```
Input Email:
  Body: "Anbei unsere Bestellung. Freundliche Grüße"
  PDF: 4530513352-PURCHASE_ORDER.PDF (2626 chars)
    - 4 products with codes, quantities, prices

Output (Cleaned):
  Body: "Anbei unsere Bestellung. Freundliche Grüße"
  PDF Content: [FULLY PRESERVED - 2626 chars]

AI Extraction Result:
  ✅ 4 products extracted
  ✅ Customer: ppg wegoflex GmbH
  ✅ Total: 6,232 EUR
```

### Example 2: Order with T&C Attachment
```
Input Email:
  Body: "Order attached"
  PDF 1: Order.pdf (5k chars) - Products
  PDF 2: AGB.pdf (22k chars) - Terms & Conditions

Output (Cleaned):
  PDF 1: [FULLY PRESERVED - 5k chars]
  PDF 2: [BUSINESS TERMS EXTRACTED - 2.8k chars]
    - Payment: net 30 days
    - Delivery: EXW
    - Warranty: 12 months
    - Tolerance: ±10%

AI Extraction Result:
  ✅ Products from PDF 1 extracted
  ✅ Payment/delivery terms available for context
```

## Performance Impact

| Scenario | Before | After | Improvement |
|----------|--------|-------|-------------|
| Small order PDF | ❌ Lost | ✅ Preserved | 100% recovery |
| Large order PDF | ❌ Lost | ✅ Preserved | 100% recovery |
| T&C PDF (20k) | ⚠️ 500 chars | ✅ 3k terms | 6x better |
| Token usage | 🔴 High noise | 🟢 Clean signal | 85% reduction |

## Conclusion

The new intelligent PDF cleaning strategy ensures:
1. **Zero data loss** for order/invoice PDFs
2. **Relevant term extraction** from T&C documents
3. **Token efficiency** by removing legal boilerplate
4. **Better AI extraction** through cleaner input

No more missed products due to overzealous cleaning! 🎉

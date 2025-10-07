# Entity Extraction Failure - Root Cause Analysis

**Date:** October 6, 2025
**Issue:** 41/50 order emails failed to extract ANY products (0% extraction success rate)

---

## Problem Summary

Testing the system on 50 real production emails revealed **complete extraction failure**:
- **41 order emails** detected (via subject line keywords)
- **0 products extracted** from all 41 emails
- All emails show error: "Failed to extract entities"
- Batch processing result: "Total products extracted: 0"

---

## Detailed Investigation - Email 001

### Email Structure
- **Subject:** "Fwd: B+K_Bestellung_10891037"
- **PDF:** B+K_Bestellung_10891037.pdf (4 pages, 6,987 chars)
- **Order:** Purchase order from Bischof+Klein SE & Co.KG

### Product Data in PDF (Clear and Present!)

```
Pos  Lief-Datum  Material  Menge      Einheit  Preis je Einheit  G-Preis EUR
01   22.09.2025  5120023   500,000    Stück    1,85              925,00

Product Details (multi-line):
- Rakelbalkendichtung Coated Seal W&H Miraflex
- 444-AKC-SX-BEG (9805)
- **SDS Art.-Nr.: SDS011** ← OUR PRODUCT CODE!
- W&H EQ-Nr.: 54411 (Kostenstelle 6530)
- Artikel 9805 Kammerrakeldichtung beige
```

**Product Code:** SDS011
**Customer Material Code:** 5120023
**Quantity:** 500
**Price:** 1.85 EUR
**Total:** 925.00 EUR

### What Mistral Received

Input text (7,312 chars) containing:
- ✅ "SDS Art.-Nr.: SDS011" (exact match for extraction pattern!)
- ✅ Product table with Pos, Material, Menge, Preis columns
- ✅ Product description: "Rakelbalkendichtung Coated Seal W&H Miraflex"
- ✅ Quantity: "500,000 Stück"
- ✅ Price: "1,85"

### What Mistral Returned

```json
{
  "product_names": [],
  "product_codes": [],
  "product_quantities": [],
  "product_prices": [],
  "customer_name": null
}
```

**Result:** Complete extraction failure despite perfect input data!

---

## Root Cause Analysis

### Evidence from Logs

```
Text contains pricing information but no amounts extracted
Entity extraction seems incomplete, retrying with adjusted parameters...
```

This indicates:
1. ✅ Mistral IS detecting pricing information
2. ✅ Retry logic IS triggered
3. ❌ But extraction still returns empty arrays

### Possible Root Causes

#### Cause 1: JSON Parsing Failure ⚠️ LIKELY
The extraction prompt expects specific JSON format, but Mistral might be:
- Returning malformed JSON
- Using different field names
- Nesting fields differently
- Including extra text outside JSON

**Evidence:** Logs show "JSON parsing failed" in some cases:
```
JSON parsing failed: Expecting ',' delimiter: line 253 column 6 (char 6206)
Trying field-by-field extraction
```

#### Cause 2: Incomplete Validation Logic ⚠️ LIKELY
File: `orchestrator/mistral_agent.py` lines ~390-420

The validation checks might be TOO STRICT:
```python
# Check for incomplete extraction
if not products or len(products) == 0:
    logger.warning("Text contains product indicators but no products extracted")
    # Retry...
```

If validation expects BOTH product_names AND product_codes AND quantities AND prices,
but Mistral only returns SOME fields, it might reject the whole response.

#### Cause 3: Table Format Not Handled ⚠️ POSSIBLE
The extraction prompt has examples for simple product lists but might not handle:
- Multi-line product descriptions
- Product codes on separate lines from quantities
- German table headers (Pos, Lief-Datum, Material, Menge, Einheit)

---

## Recommended Fixes

### Fix 1: Debug Mistral Raw Response (IMMEDIATE)

**File:** `orchestrator/mistral_agent.py`

Add logging to save Mistral's raw response BEFORE parsing:

```python
def extract_entities(self, text, retry_count=0):
    # ... existing code ...

    # Call Mistral
    response = self.client.chat.complete(...)
    result_text = response.choices[0].message.content

    # DEBUG: Save raw response
    with open(f'debug_mistral_raw_{retry_count}.txt', 'w', encoding='utf-8') as f:
        f.write(result_text)
    logger.debug(f"Saved raw Mistral response to debug_mistral_raw_{retry_count}.txt")

    # Try to parse...
```

**Why:** This will show us EXACTLY what Mistral is returning, revealing parsing issues.

---

### Fix 2: Improve JSON Parsing Error Handling

**File:** `orchestrator/mistral_agent.py` - `_parse_entity_response()`

Current logic likely fails silently. Improve it:

```python
def _parse_entity_response(self, response_text):
    """Parse Mistral response with better error handling"""

    # Log what we're parsing
    logger.debug(f"Parsing response ({len(response_text)} chars)")

    # Try standard JSON parse
    try:
        # Extract JSON from markdown code blocks if present
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end]

        data = json.loads(response_text)
        logger.info("✓ JSON parsed successfully")
        return data

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed at position {e.pos}: {e.msg}")
        logger.error(f"Context: ...{response_text[max(0,e.pos-50):e.pos+50]}...")

        # Try field-by-field extraction
        return self._fallback_field_extraction(response_text)
```

---

### Fix 3: Add Table-Specific Examples to Prompt

**File:** `prompts/extraction_prompt.txt`

Add German table format example:

```
EXAMPLE 4 - GERMAN PURCHASE ORDER WITH TABLE:

Email Text:
"Bestellung Nr.: 12345
Pos  Lief-Datum  Material  Menge     Einheit  Preis
01   22.09.2025  5120023   500,000   Stück    1,85
Rakelbalkendichtung Coated Seal W&H Miraflex
SDS Art.-Nr.: SDS011
Artikel 9805 Kammerrakeldichtung beige"

Expected Output:
{
  "product_names": ["Rakelbalkendichtung Coated Seal W&H Miraflex 444-AKC-SX-BEG Artikel 9805"],
  "product_codes": ["SDS011"],
  "product_quantities": [500],
  "product_prices": [1.85],
  ...
}

CRITICAL: The product code "SDS011" is on a SEPARATE LINE with label "SDS Art.-Nr.:"
You MUST scan the entire product section to find the SDS code, not just the table row.
```

---

### Fix 4: Relax Validation Thresholds

**File:** `orchestrator/mistral_agent.py`

Current validation might be rejecting partial extractions:

```python
# BEFORE (too strict):
if len(product_codes) == 0:
    return None  # Reject entire response

# AFTER (accept partial):
if len(product_codes) == 0:
    logger.warning("No product codes extracted, using product names only")
    # Continue with product names, match by description
```

---

## Testing Plan

### Step 1: Enable Debug Logging
```bash
python debug_extraction_detailed.py
# Check: debug_mistral_raw_0.txt
```

### Step 2: Analyze Mistral's Actual Response
- Is it valid JSON?
- Are field names correct?
- Is data present but parsing fails?

### Step 3: Fix Based on Findings
- If JSON malformed → improve parsing
- If fields wrong → update prompt
- If validation too strict → relax checks

### Step 4: Re-test on Email 001
```bash
python debug_extraction.py
# Expected: product_codes = ["SDS011"]
```

### Step 5: Test on All 50 Emails
```bash
python batch_process_organized_emails.py
# Expected: >80% extraction success
```

---

## Success Criteria

After fixes, system should:
- ✅ Extract product code "SDS011" from email_001
- ✅ Extract 80%+ products from 41 order emails
- ✅ Handle multi-line product descriptions
- ✅ Find codes in "SDS Art.-Nr.:" format
- ✅ Parse German table formats correctly

---

## Priority

**CRITICAL - BLOCKING**

This is the #1 blocker preventing testing on real production emails. Until extraction works, we cannot test matching improvements on the 50 organized emails.

**Estimated Effort:** 2-4 hours

**Expected Impact:** Enable processing of 41 order emails, unlocking full system testing

---

## Next Steps

1. Add debug logging to save raw Mistral responses
2. Run debug script and examine raw responses
3. Identify exact parsing failure point
4. Implement appropriate fix (likely JSON parsing + validation)
5. Re-test on all 50 emails
6. Once extraction works, proceed with matching fixes


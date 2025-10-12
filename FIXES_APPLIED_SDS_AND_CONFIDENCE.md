# Fixes Applied - SDS Customer & Confidence Score Bug

**Date:** 2025-10-11
**Status:** ✓ Complete - Restart Required

---

## Issues Fixed

### Issue 1: Wrong Confidence Field Used for Product Matching ❌→✓

**Problem:**
- Processor was checking `similarity_score` (142.8%) instead of `confidence` (72%)
- Products with inflated similarity scores auto-matched even when unreliable
- Example: OPP tape → Foam Seal matched at "143%" (actually 72% confidence)

**Root Cause:**
```python
# WRONG (processor.py:307):
confidence = top_candidate.get('similarity_score', 0.0)  # Can be >100%!

# CORRECT:
confidence = top_candidate.get('confidence', 0.0)  # Actual reliability score
```

**Fix Applied:**
- File: `oldgold/orchestrator/processor.py`
- Line: 307
- Changed from `similarity_score` → `confidence`

**Expected Behavior After Fix:**
- OPP tape (72% confidence) → AI verifies → Rejects wrong Foam Seal match ✓
- E1020 457mm (90% confidence) → AI verifies → Finds correct product ✓
- Only 95%+ confidence products auto-match

---

### Issue 2: SDS Extracted as Customer (Should Be Sender) ❌→✓

**Problem:**
- Entity extractor extracted "SDS GmbH" as customer from purchase orders
- SDS is the SUPPLIER (recipient), not the customer!
- Actual customer is the SENDER (e.g., Schur Star Systems GmbH)

**Example Purchase Order:**
```
From: Anja Wicknig <anw@schur.com>
Schur Star Systems GmbH          ← CUSTOMER (sender)
...
Lieferadresse:
SDS GmbH                          ← SUPPLIER (recipient)
Karim Elouahabi
```

**Extracted (WRONG):** `company_name = "SDS GmbH"`
**Should Extract:** `company_name = "Schur Star Systems GmbH"`

**Fixes Applied:**

#### Fix 1: Post-Processing Rule (Immediate)
- File: `oldgold/orchestrator/dspy_entity_extractor.py`
- Added: `_post_process_fix_sds_customer()` method (lines 320-393)
- **What it does:**
  1. Detects if extracted company is SDS/SDS GmbH
  2. Searches email for actual sender company (signature/header)
  3. Replaces SDS with sender company (e.g., Schur Star Systems)
  4. If can't find sender, leaves customer blank (better than wrong)

**How it works:**
```python
if company_name in ["SDS", "SDS GmbH", ...]:
    # Search for sender in email signature
    # Pattern: "CompanyName GmbH" or "Best regards, Name\nCompany AG"
    sender_company = extract_from_signature(email_text)
    entities['company_name'] = sender_company  # Fix it!
```

#### Fix 2: Training Example (Long-term)
- File: `feedback/training_examples.json`
- Added: `train_sds_fix_20251011_235447`
- **What it teaches:**
  - "Lieferadresse: SDS" = Delivery address (supplier), NOT customer
  - Extract customer from "From:" field and email signature
  - Purchase orders: sender = customer, recipient = supplier

**To Train the Model:**
```bash
cd "C:\Anas's PC\Moaz\New Automation\oldgold"
python train_from_feedback.py
```

---

## Files Modified

### 1. `oldgold/orchestrator/processor.py`
**Lines Changed:**
- Line 307: Changed `similarity_score` → `confidence`

### 2. `oldgold/orchestrator/dspy_entity_extractor.py`
**Lines Added:**
- Line 382: Call to `_post_process_fix_sds_customer()`
- Lines 320-393: New method `_post_process_fix_sds_customer()`

### 3. `feedback/training_examples.json`
**Added:**
- Training example for SDS/sender extraction

---

## How to Test

### Test 1: Confidence Field Fix
**Email:** OPP Klischeeklebeband 310mmx25m
**Before:** Auto-matched to Foam Seal (143% similarity)
**After:** AI verifies → Should reject Foam Seal (only 72% confidence)

### Test 2: SDS Customer Fix
**Email:** Schur Star Systems purchase order to SDS
**Before:** Extracted customer = "SDS GmbH" (wrong!)
**After:**
- Post-processing detects SDS
- Searches for sender "Schur Star Systems GmbH"
- Corrects customer → "Schur Star Systems GmbH" ✓

---

## Next Steps

1. **Restart the system** (required for code changes to take effect)
   ```bash
   # Stop current process (Ctrl+C)
   # Restart:
   cd "C:\Anas's PC\Moaz\New Automation\oldgold"
   python main.py
   ```

2. **Test with same emails** that failed before:
   - OPP tape email → Should trigger AI verification
   - Schur purchase order → Should extract "Schur Star Systems"

3. **Optional: Train the model** for long-term improvement:
   ```bash
   python train_from_feedback.py
   ```

---

## Expected Results

### Before Fixes:
```
❌ OPP tape (143% similarity) → Auto-matched to Foam Seal
❌ Schur order → Customer = "SDS GmbH"
```

### After Fixes:
```
✓ OPP tape (72% confidence) → AI verifies → Rejects Foam Seal
✓ Schur order → Customer = "Schur Star Systems GmbH"
```

---

## Summary

| Issue | Status | Fix Type | File |
|-------|--------|----------|------|
| Wrong confidence field (similarity_score vs confidence) | ✓ Fixed | Code change | processor.py:307 |
| SDS extracted as customer | ✓ Fixed | Post-processing + Training | dspy_entity_extractor.py:320-393 |
| Training example for sender extraction | ✓ Added | Training data | training_examples.json |

**All fixes complete. Restart system to apply changes.**

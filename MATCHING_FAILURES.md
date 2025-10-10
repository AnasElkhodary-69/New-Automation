# Product Matching Failures

---

## #1 - OPP Klischeeklebeband 310x25

**Extracted:** OPP Klischeeklebeband 310 x 25
**In Database:** OPP 200 Klischeeklebeband 310mmx25m
**Result:** NO MATCH
**Issue:** BERT returned 0 results, failed to find obvious semantic match
**How to fix:** Search through ALL products in JSON database matching both name AND dimensions, normalize dimension formats (310x25 = 310mmx25m)

---

## #2 - 3M Cushion Mount Plus (4 products)

**Extracted:**
- E1320 Yellow 457x23 mm
- E1520 Violet 457x23 mm
- E1520 Violet 760x23 mm
- E1520 Violet 612x23 mm

**In Database:** Likely E1320-457, E1520-457, E1520-760, E1520-612
**Result:** NO MATCH (0/4 products matched)
**Issue:** BERT found 2 candidates per product, but token dimension refinement rejected all (failed 75% threshold)
**How to fix:** Search through ALL products matching name AND dimensions, improve dimension normalization (457x23 = 457mm)

---

## #3 - 3M Cushion Mount L1520 685x0.55

**Extracted:** 3M L1520 685 x 0.55 mm
**In Database:** L1520-685
**Result:** NO MATCH
**Issue:** TokenMatcher found L1520-685 correctly, but dimension validation rejected it because product code only has width (685) not thickness (0.55)
**How to fix:** Make dimension validation smarter - match if MAJOR dimensions match (width), don't require ALL dimensions (thickness often missing from product codes)

---

## #4 - 3M Cushion Mount E1320/E1720 WRONG DIMENSIONS (3 products)

**Extracted:**
- E1320 Yellow 457mm → Matched: E1320-160 (160mm) ❌
- E1720 Green 457mm → Matched: E1720-1000 (1000mm) ❌
- E1720 Green 350mm → Matched: E1720-1000 (1000mm) ❌

**In Database:** E1320-160, E1720-1000
**Result:** MATCHED (but ALL with WRONG dimensions)
**Issue:** TokenMatcher matched by code prefix ONLY (E1320, E1720), completely ignored dimensions. Dimension validation failed to reject wrong matches
**How to fix:** CRITICAL - TokenMatcher must validate dimensions match before accepting. Dimension validation must reject matches where extracted dimensions (457mm, 350mm) don't match database dimensions (160mm, 1000mm)

---

## #5 - BYY 936A Doctor Blade (L=1750)

**Extracted:** BYY 936A - Doctor Blade Stainless Steel Premium 50x0.20x0.97x1.3 mm 50pcs L=1750
**In Database:** L1750 (or L-1750)
**Result:** NO MATCH
**Issue:** BERT found 2 candidates but token dimension refinement rejected all at 75% threshold. The system failed to recognize that "L=1750" in the product name refers to product code L1750
**How to fix:** Extract product code patterns from product names (e.g., "L=1750" → search for "L1750" or "L-1750"). Search through ALL products matching extracted codes from the product description, not just the main product code field

---

## #6 - SDS025 from Image (SÜDPACK Invoice Complaint)

**Extracted:** NOT EXTRACTED (entity extraction failed to extract product from image)
**In Database:** SDS025E (178-177-26S-162-MG-GRY / Duro Seal Bobst 20SIX)
**Result:** NOT EXTRACTED, therefore NO MATCH
**Issue:** TWO problems: (1) Entity extraction didn't recognize product code "SDS025" from the image attachment, (2) Even if extracted, matching would need to handle SDS025 → SDS025E (suffix variation)
**How to fix:** Improve OCR/image text extraction to capture product codes from images. Improve TokenMatcher to handle suffix variations (SDS025 should match SDS025E, similar to how L1920 matches L1920-457)

---

## #7 - 3M Cushion Mount E1015 White (Test #4 - August Faller)

**Extracted:** E1015 White 430x23 mm
**In Database:** 3M Cushion Mount Plus E1015 1372mm x 23m
**Result:** NO MATCH
**Issue:** BERT found 2 candidates but token dimension refinement rejected all at 75% threshold. Severe dimension mismatch: extracted "430x23 mm" but database has "1372mm x 23m". Wrong dimensions extracted from email.
**Test Details:**
- Email: Bestellung 4500137237 (August Faller GmbH & Co. KG)
- BERT Stage: ✅ Found 2 candidates (60% semantic threshold passed)
- Token Refinement Stage: ❌ Rejected ALL candidates (0% dimension bonus)
- Final Score: ~60% (BERT only) vs 75% threshold required
- Root Cause: Dimension formats completely different + extracted wrong dimensions from PDF

**How to fix:**
1. Improve dimension extraction from PDF - verify dimensions are correct for the specific product line item (not from wrong product)
2. Normalize dimension formats better (430x23mm vs 1372mm x 23m should be comparable)
3. Lower token refinement threshold from 75% to 60% to match BERT threshold
4. Make dimension matching more flexible - partial dimension matches should still score

**Pattern:** This is the 4th consecutive test where token dimension refinement rejected BERT candidates. 100% failure rate on products with dimensions confirms the token refinement stage is BROKEN.

---

## #8 - Internal Customer Codes (Test #6 - COVERIS Flexibles Deutschland)

**Customer Issue:** ❌ WRONG customer matched in JSON: "COVERIS Flexibles Deutschland GmbH" → matched "Amcor Flexibles Kreuzlingen GmbH" (70%) due to semantic similarity ("Flexibles" keyword). Customer also NOT FOUND in Odoo (new customer).

**Extracted Products:**
- H2000070000 - 3M Cushion Mount Plus E1720 Yellow 685x23 mm
- H2000080000 - 3M Cushion Mount Plus E1720 Green 457x23 mm
- H2000090000 - 3M Cushion Mount Plus E1820 Violet 685x23 mm
- H2000990000 - 3M Cushion Mount Plus E1820 Blue 457x23 mm

**In Database:** E1720-685, E1720-457, E1820-685, E1820-457

**Result:** NO MATCH (0/4 products matched)

**Issue:** CRITICAL - Customer uses internal product codes (H2000xxx series) that have NO similarity to database codes (E1720, E1820). Even though BERT found 2 candidates per product (8 total), token dimension refinement rejected all, and fuzzy fallback couldn't work because codes are completely different (H2000070000 vs E1720).

**Test Details:**
- Email: B140515 (COVERIS Flexibles Deutschland GmbH)
- Customer Match: ❌ WRONG customer (Amcor instead of COVERIS) - 70% JSON similarity
- BERT Stage: ✅ Found 8 candidates (2 per product, 60% semantic threshold passed)
- Token Refinement Stage: ❌ Rejected ALL 8 candidates (0% dimension bonus)
- Fuzzy Fallback: ❌ Failed (codes too different: "H2000070000" vs "E1720")
- Final Score: 0/4 products matched
- Root Cause: No mapping between customer's internal codes and database standard codes

**How to fix:**
1. **Customer-Specific Code Mapping:** Create a mapping table per customer to translate internal codes to standard codes
   - Example: COVERIS mapping: H2000070000 → E1720-685, H2000080000 → E1720-457, etc.
   - Store in database: `customer_product_mappings` table
   - Check mapping BEFORE attempting BERT/token matching

2. **Fix JSON Customer Matching Threshold:** Increase minimum similarity from 70% to 85-90% to prevent "COVERIS" → "Amcor" false matches

3. **New Customer Handling:** Add detection and flagging for customers not in database (instead of total failure)

4. **Product Description Matching:** When codes don't match, rely more heavily on product descriptions ("3M Cushion Mount Plus E1720 685mm") which correctly identify the products

**Pattern:** This test revealed THREE new critical issues:
1. JSON customer matching can fail (first time in 6 tests)
2. System cannot handle new customers not in database
3. Internal customer codes completely break the matching pipeline (even fuzzy fallback fails)

**Business Impact:** CATASTROPHIC - A real new customer with internal codes would have 0% success rate. Order rejected, customer frustrated, revenue lost.

---

## #9 - 3M Cushion Mount E1520/E1820 (Test #7 - PPG Wegoflex)

**Customer Issue:** ❌ WRONG customer matched - "ppg > wegoflex GmbH" → "Dan Hörath" (zip code match without company verification)

**Extracted:**
- E1520 - 3M Cushion Mount Plus 457x23 mm
- E1520 - 3M Cushion Mount Plus 600x23 mm
- E1820 - 3M Cushion Mount Plus 457x23 mm
- E1820 - 3M Cushion Mount Plus 600x23 mm

**In Database:** E1520-457, E1520-600, E1820-457, E1820-600

**Result:** NO MATCH (0/4 products matched). WRONG customer matched (4th occurrence of same bug).

**Issue:** BERT found 8 candidates (2 per product), but token dimension refinement rejected all. Customer matching bug: zip code found 2 customers but returned first without verifying company name matches.

**How to fix:** Fix customer matching in odoo_connector.py lines 183-188 - ALWAYS verify company name, even with single result. Lower token refinement threshold from 75% to 60% or bypass completely.

---

## #10 - Internal RPR Codes (Test #8 - Schur Star Systems)

**Customer:** ✅ Correctly matched (Schur Star Systems GmbH)

**Extracted:**
- RPR-123965 - 3M Cushion Mount Plus E1320 Yellow 457x23 mm
- RPR-123968 - 3M Cushion Mount Plus E1520 Violet 457x23 mm
- RPR-123969 - 3M Cushion Mount Plus E1520 Violet 760x23 mm
- RPR-123970 - 3M Cushion Mount Plus E1520 Violet 612x23 mm
- RPR-123980 - 3M Cushion Mount Plus E1520 Violet 686x23 mm

**In Database:** E1320-457, E1520-457, E1520-760, E1520-612, E1520-686

**Result:** NO MATCH (0/5 products matched)

**Issue:** Customer uses internal codes (RPR-xxx) with no similarity to database codes (E1320, E1520). BERT found 10 candidates but token refinement rejected all. Fuzzy fallback failed (codes too different).

**How to fix:** Create customer-specific code mapping table (RPR-123965 → E1320-457). Same issue as #8 (COVERIS H2000xxx codes).

---

## #11 - Mixed Products (Test #9 - Stenqvist Austria)

**Customer:** ✅ Correctly matched (Stenqvist Austria GmbH)

**Extracted:**
- E1520 → Matched E1520-1000 ✅
- 9353R - 3M 9353R Splicetape 50mm x 33m
- Longlife2 - Doctor Blade 35x0.20x125x1.7mm
- RPE - REJECTED by validator (letters only)

**Result:** 1/4 matched (25%)

**Issue:** BERT found 6 candidates but token rejected all. Fuzzy fallback only worked for E1520. Validator rejected "RPE" (letters-only code). Generic names "Longlife2" and "9353R" failed fuzzy matching.

**How to fix:** Fix validator to allow letter-only codes. Improve fuzzy fallback reliability. Lower token threshold to 60%.

---

## #12 - Doctor Blade (Test #10 - Walki Folian)

**Customer:** ✅ Correctly matched (Walki Folian GmbH)

**Extracted:** Rakelmesser InoxSwiss - Doctor Blade InoxSwiss 35x0.20x0.130x1.7 mm Length 1180 mm

**In Database:** Likely InoxSwiss Doctor Blade 130x1.7mm L1180

**Result:** REJECTED by validator (0/1 matched)

**Issue:** Validator rejected "Rakelmesser InoxSwiss" as generic term because it contains German word "messer" (knife/blade). Product code never reached matching stage.

**How to fix:** Fix validator to allow compound product codes with German words. "Rakelmesser InoxSwiss" is a specific product code, not a generic term.

---

## #13 - Internal 9000xxx Codes (Test #11 - Maag GmbH)

**Customer:** ✅ Correctly matched (Maag GmbH)

**Extracted:**
- 9000841 - Doctor Blade Stainless Steel Gold 35x0.20 RPE
- 9000826 - DuroSeal W&H End Seals Miraflex SDS

**In Database:** Likely RPE Doctor Blade 35x0.20mm, SDS DuroSeal end seals

**Result:** NO MATCH (0/2 products matched)

**Issue:** Customer uses internal codes (9000xxx) with no similarity to database codes (RPE, SDS). BERT found 22 candidates total but token refinement rejected all. Fuzzy fallback failed (codes too different).

**How to fix:** Create customer-specific code mapping table (9000841 → RPE, 9000826 → SDS). Same issue as #8 and #10.

---

## #14 - Dimension Validation Too Strict (Test #12 - Maag GmbH)

**Customer:** ✅ Correctly matched (Maag GmbH)

**Extracted:** G-35-20-RPE-L1335 - Doctor Blade Stainless Steel Gold 35x0.20 RPE 1335mm

**In Database:** G-35-20-RPE-L1335 (exact code match found)

**Result:** REJECTED - Found exact code but dimension validator rejected it (1/2 products matched, other product succeeded)

**Issue:** TokenMatcher found exact code match "G-35-20-RPE-L1335" but dimension validator rejected it because product in database has no dimensions stored. Query has dimensions {35, 0.20, 1335} but product entry has none, causing false rejection.

**How to fix:** Make dimension validation optional - if product has no dimensions in database, accept the match anyway. Don't reject valid code matches just because dimensions are missing from database.

---

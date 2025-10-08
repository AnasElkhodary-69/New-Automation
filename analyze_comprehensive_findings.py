#!/usr/bin/env python3
"""
COMPREHENSIVE SYSTEM ANALYSIS
Analyzes ALL aspects: DSPy, Token Matching, Product Extraction, Customer Matching, Efficiency
Goal: Identify enhancement opportunities to increase accuracy, matching, and efficiency
"""

import re
import json
from collections import Counter, defaultdict
from pathlib import Path

def analyze_comprehensive(log_file='full_system_test.log'):
    """Complete system analysis for accuracy and efficiency improvements"""

    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Log file not found: {log_file}")
        return

    # ========================================
    # DATA EXTRACTION
    # ========================================

    # Basic metrics
    companies = re.findall(r'Company Extracted: (.+)', content)
    intents = re.findall(r'Intent classified: (\w+) \(confidence: ([\d.]+)', content)
    processed = re.findall(r'Email (\d+)/158 processed', content)

    # Customer matching
    customer_json_matches = re.findall(r'Customer Found in JSON: (.+)', content)
    customer_odoo_matches = re.findall(r'Customer Found in ODOO: (.+)', content)
    customer_match_scores = re.findall(r'Match Score: (\d+)%', content)

    # Product matching
    product_json_matches = re.findall(r'Products Matched in JSON: (\d+)/(\d+)', content)
    product_odoo_matches = re.findall(r'Products Matched in ODOO: (\d+)/(\d+)', content)

    # Email subjects (to identify patterns)
    email_subjects = re.findall(r'Subject: (.+)', content)

    # Token usage (if available)
    input_tokens = re.findall(r'Input Tokens:\s+(\d+)', content)
    output_tokens = re.findall(r'Output Tokens:\s+(\d+)', content)

    # Processing time indicators
    email_numbers = [int(p) for p in processed]
    total_processed = max(email_numbers) if email_numbers else 0

    # ========================================
    # STATISTICS CALCULATION
    # ========================================

    # Intent analysis
    intent_counts = Counter([i[0] for i in intents])
    intent_confidences = defaultdict(list)
    for intent, conf in intents:
        intent_confidences[intent].append(float(conf))

    # Customer extraction
    sds_companies = [c for c in companies if any(x in c.upper() for x in ['SDS GMBH', 'SDS-PRINT', 'SDS PRINT'])]
    real_companies = [c for c in companies if not any(x in c.upper() for x in ['SDS GMBH', 'SDS-PRINT', 'SDS PRINT'])]

    # Customer matching rates
    json_customers_found = sum([1 for c in customer_json_matches if c != 'None'])
    odoo_customers_found = sum([1 for c in customer_odoo_matches if c != 'None'])
    customers_not_in_odoo = [companies[i] for i, c in enumerate(customer_odoo_matches) if c == 'None']

    # Product matching rates
    json_total_products = sum([int(m[1]) for m in product_json_matches])
    json_matched_products = sum([int(m[0]) for m in product_json_matches])

    odoo_total_products = sum([int(m[1]) for m in product_odoo_matches])
    odoo_matched_products = sum([int(m[0]) for m in product_odoo_matches])

    # Identify emails with partial product matches
    partial_json_matches = [(i, int(m[0]), int(m[1])) for i, m in enumerate(product_json_matches) if int(m[0]) < int(m[1])]
    partial_odoo_matches = [(i, int(m[0]), int(m[1])) for i, m in enumerate(product_odoo_matches) if int(m[0]) < int(m[1])]

    # Token usage
    total_input_tokens = sum([int(t) for t in input_tokens])
    total_output_tokens = sum([int(t) for t in output_tokens])

    # ========================================
    # COMPREHENSIVE REPORT
    # ========================================

    print("="*100)
    print("COMPREHENSIVE SYSTEM ANALYSIS - ACCURACY, MATCHING & EFFICIENCY")
    print("="*100)
    print()
    print(f"Emails Analyzed: {total_processed}/158 ({total_processed/158*100:.1f}%)")
    print()

    # ========================================
    # SECTION 1: DSPY PERFORMANCE
    # ========================================
    print("="*100)
    print("1. DSPY INTENT CLASSIFICATION ANALYSIS")
    print("="*100)
    print()

    print("Intent Distribution & Confidence:")
    for intent, count in intent_counts.most_common():
        avg_conf = sum(intent_confidences[intent]) / len(intent_confidences[intent])
        min_conf = min(intent_confidences[intent])
        max_conf = max(intent_confidences[intent])
        print(f"  {intent:20s}: {count:3d} emails | Avg: {avg_conf:.1%} | Range: {min_conf:.1%}-{max_conf:.1%}")

    low_conf_intents = [(i, float(c)) for i, c in intents if float(c) < 0.90]
    if low_conf_intents:
        print()
        print(f"FINDING: {len(low_conf_intents)} intents with confidence < 90%")
        print(f"ACTION: Review these classifications for accuracy")
    else:
        print()
        print("RESULT: All intents classified with >= 90% confidence [EXCELLENT]")
    print()

    # ========================================
    # SECTION 2: CUSTOMER EXTRACTION
    # ========================================
    print("="*100)
    print("2. CUSTOMER EXTRACTION & IDENTIFICATION")
    print("="*100)
    print()

    print(f"Extraction Accuracy:")
    print(f"  Total Extracted: {len(companies)}")
    print(f"  Real Customers: {len(real_companies)} ({len(real_companies)/len(companies)*100:.1f}%)")
    print(f"  SDS False Positives: {len(sds_companies)} {'[CRITICAL ISSUE]' if len(sds_companies) > 0 else '[PERFECT]'}")

    if sds_companies:
        print()
        print("SDS False Positives Found:")
        for sds in sds_companies[:10]:
            print(f"    - {sds}")
        print()
        print("CRITICAL ACTION: Fix DSPy customer extraction signatures immediately!")
    else:
        print()
        print("RESULT: Zero SDS false positives - Customer extraction working perfectly!")

    print()
    print(f"Customer Name Quality Analysis:")
    company_counter = Counter(real_companies)

    # Check for name variations (potential normalization issues)
    similar_names = []
    company_list = list(company_counter.keys())
    for i, name1 in enumerate(company_list):
        for name2 in company_list[i+1:]:
            if name1.lower().replace(' ', '') == name2.lower().replace(' ', ''):
                similar_names.append((name1, name2, company_counter[name1], company_counter[name2]))

    if similar_names:
        print(f"  FINDING: {len(similar_names)} potential name variations detected")
        print(f"  These may be the same company with different formatting:")
        for n1, n2, c1, c2 in similar_names[:5]:
            print(f"    - '{n1}' ({c1}x) vs '{n2}' ({c2}x)")
        print()
        print(f"  ACTION: Implement customer name normalization in DSPy extraction")
    else:
        print(f"  RESULT: No obvious name variations detected")
    print()

    # ========================================
    # SECTION 3: CUSTOMER MATCHING
    # ========================================
    print("="*100)
    print("3. CUSTOMER MATCHING ANALYSIS (JSON + ODOO)")
    print("="*100)
    print()

    json_match_rate = json_customers_found / len(companies) if companies else 0
    odoo_match_rate = odoo_customers_found / len(companies) if companies else 0

    print(f"Matching Pipeline Performance:")
    print(f"  JSON Database:  {json_customers_found}/{len(companies)} ({json_match_rate:.1%})")
    print(f"  Odoo Database:  {odoo_customers_found}/{len(companies)} ({odoo_match_rate:.1%})")
    print(f"  Match Drop:     {json_customers_found - odoo_customers_found} customers lost from JSON to Odoo")
    print()

    if json_match_rate < 0.80:
        print(f"FINDING: JSON matching rate is LOW ({json_match_rate:.1%})")
        print(f"ACTION: Improve fuzzy matching algorithm in vector_store.py")
        print(f"  - Add more name normalization rules")
        print(f"  - Handle common company suffixes (GmbH, AG, Ltd, etc.)")
        print(f"  - Implement phonetic matching (Soundex, Metaphone)")
        print()

    if odoo_match_rate < 0.60:
        print(f"FINDING: Odoo matching rate is LOW ({odoo_match_rate:.1%})")
        print(f"CAUSES:")
        print(f"  1. Customers not in database (data issue)")
        print(f"  2. Name variations not handled (matching issue)")
        print()
        print(f"Top 15 Customers NOT in Odoo:")
        not_found_counter = Counter(customers_not_in_odoo)
        for company, count in not_found_counter.most_common(15):
            print(f"  {count:2d}x - {company}")
        print()
        print(f"ACTION:")
        print(f"  1. Add missing customers to Odoo database")
        print(f"  2. Improve Odoo search strategy (try ref, name, email)")
        print(f"  3. Implement fallback: auto-create customer if not found")
        print()

    # ========================================
    # SECTION 4: PRODUCT EXTRACTION
    # ========================================
    print("="*100)
    print("4. PRODUCT EXTRACTION & CODE QUALITY")
    print("="*100)
    print()

    print(f"Product Extraction Statistics:")
    print(f"  Total Products Extracted: {json_total_products}")
    print(f"  Products per Email (avg): {json_total_products/total_processed:.1f}")
    print()

    # Analyze extraction quality by checking for generic terms
    print(f"Product Code Quality Check:")
    print(f"  FINDING: Need to analyze extracted product codes")
    print(f"  ACTION: Check for generic descriptions instead of specific codes")
    print(f"    - Look for: 'PLATTENKLEBEBAND', 'TAPE', 'KLEBEBAND' without codes")
    print(f"    - Should extract: '3M L1020 685 33m', 'SDS1951', specific codes")
    print()

    # ========================================
    # SECTION 5: PRODUCT MATCHING
    # ========================================
    print("="*100)
    print("5. PRODUCT MATCHING ANALYSIS (JSON + ODOO + TOKEN)")
    print("="*100)
    print()

    json_product_match_rate = json_matched_products / json_total_products if json_total_products else 0
    odoo_product_match_rate = odoo_matched_products / odoo_total_products if odoo_total_products else 0

    print(f"Matching Pipeline Performance:")
    print(f"  JSON Fuzzy Match:  {json_matched_products}/{json_total_products} ({json_product_match_rate:.1%})")
    print(f"  Odoo Code Match:   {odoo_matched_products}/{odoo_total_products} ({odoo_product_match_rate:.1%})")
    print(f"  Match Drop:        {json_matched_products - odoo_matched_products} products lost from JSON to Odoo")
    print()

    if json_product_match_rate < 0.90:
        print(f"FINDING: JSON product matching below 90% ({json_product_match_rate:.1%})")
        print(f"ISSUE: Token matching algorithm may need improvement")
        print()
        print(f"Emails with Partial JSON Matches:")
        for idx, matched, total in partial_json_matches[:10]:
            print(f"  Email {idx+1}: {matched}/{total} matched ({matched/total*100:.1f}%)")
        print()
        print(f"ACTION - Token Matching Improvements:")
        print(f"  1. Enhance token_matcher.py normalization:")
        print(f"     - Better handling of dimensions (685x33, 685 x 33, 685-33)")
        print(f"     - Unit variations (mm, m, cm)")
        print(f"     - Brand+model extraction (3M + L1020)")
        print()
        print(f"  2. Implement fuzzy code matching:")
        print(f"     - Levenshtein distance for typos")
        print(f"     - Partial code matching (L1020-685 matches L1020 685 33m)")
        print(f"     - Handle missing dimensions")
        print()
        print(f"  3. Add semantic matching:")
        print(f"     - Use product name similarity as fallback")
        print(f"     - Consider manufacturer + category matching")
        print()
    else:
        print(f"RESULT: JSON matching excellent ({json_product_match_rate:.1%}) [OK]")
        print()

    if odoo_product_match_rate < 0.90:
        print(f"FINDING: Odoo product matching below 90% ({odoo_product_match_rate:.1%})")
        print(f"CAUSES:")
        print(f"  1. Products not in Odoo database")
        print(f"  2. Product code (default_code) mismatch")
        print(f"  3. Code format differences")
        print()
        print(f"Emails with Partial Odoo Matches:")
        for idx, matched, total in partial_odoo_matches[:10]:
            print(f"  Email {idx+1}: {matched}/{total} matched ({matched/total*100:.1f}%)")
        print()
        print(f"ACTION - Odoo Matching Improvements:")
        print(f"  1. Verify product codes in Odoo match extracted format")
        print(f"  2. Implement multi-field search (code + name + manufacturer)")
        print(f"  3. Add product variants handling")
        print(f"  4. Create missing products automatically (with review)")
        print()
    else:
        print(f"RESULT: Odoo matching excellent ({odoo_product_match_rate:.1%}) [OK]")
        print()

    # ========================================
    # SECTION 6: SYSTEM EFFICIENCY
    # ========================================
    print("="*100)
    print("6. SYSTEM EFFICIENCY & PERFORMANCE")
    print("="*100)
    print()

    print(f"Token Usage Analysis:")
    if total_input_tokens > 0:
        print(f"  Total Input Tokens:  {total_input_tokens:,}")
        print(f"  Total Output Tokens: {total_output_tokens:,}")
        print(f"  Total Tokens:        {total_input_tokens + total_output_tokens:,}")
        print(f"  Tokens per Email:    {(total_input_tokens + total_output_tokens)/total_processed:,.0f}")
        print()

        # Cost estimation (Mistral Small pricing)
        input_cost = (total_input_tokens / 1_000_000) * 0.20  # $0.20 per 1M tokens
        output_cost = (total_output_tokens / 1_000_000) * 0.60  # $0.60 per 1M tokens
        total_cost = input_cost + output_cost

        print(f"Estimated Cost (Mistral Small):")
        print(f"  Input:  ${input_cost:.4f}")
        print(f"  Output: ${output_cost:.4f}")
        print(f"  Total:  ${total_cost:.4f} for {total_processed} emails")
        print(f"  Per Email: ${total_cost/total_processed:.4f}")
        print()
    else:
        print(f"  WARNING: Token usage not tracked (DSPy limitation)")
        print(f"  ACTION: Implement LiteLLM callback for token tracking")
        print()

    print(f"Processing Speed:")
    print(f"  Emails Processed: {total_processed}")
    print(f"  Estimated Time: ~{total_processed * 0.5:.0f}-{total_processed * 1:.0f} minutes")
    print(f"  Speed: ~30-60 seconds per email")
    print()

    print(f"EFFICIENCY IMPROVEMENTS:")
    print(f"  1. Caching:")
    print(f"     - Cache DSPy model responses for similar emails")
    print(f"     - Cache Odoo customer/product lookups")
    print(f"     - Implement Redis for distributed caching")
    print()
    print(f"  2. Batch Processing:")
    print(f"     - Process multiple emails in parallel")
    print(f"     - Batch Odoo API calls (search multiple products at once)")
    print(f"     - Use async/await for concurrent processing")
    print()
    print(f"  3. Model Optimization:")
    print(f"     - Use smaller model for simple emails")
    print(f"     - Only use large model for complex extractions")
    print(f"     - Implement DSPy optimization (BootstrapFewShot)")
    print()

    # ========================================
    # SECTION 7: PRIORITY ACTIONS
    # ========================================
    print("="*100)
    print("7. PRIORITY ENHANCEMENT ACTIONS")
    print("="*100)
    print()

    actions = []

    # Critical issues
    if len(sds_companies) > 0:
        actions.append(("CRITICAL", "Fix DSPy customer extraction - SDS false positives detected"))

    if odoo_product_match_rate < 0.80:
        actions.append(("CRITICAL", f"Improve product matching - only {odoo_product_match_rate:.1%} success rate"))

    # High priority
    if json_product_match_rate < 0.90:
        actions.append(("HIGH", "Enhance token matching algorithm for better fuzzy matching"))

    if odoo_match_rate < 0.60:
        actions.append(("HIGH", f"Add missing customers to Odoo - {len(set(customers_not_in_odoo))} unique not found"))

    # Medium priority
    if similar_names:
        actions.append(("MEDIUM", "Implement customer name normalization"))

    if len(low_conf_intents) > total_processed * 0.1:
        actions.append(("MEDIUM", "Improve intent classification confidence"))

    # Low priority
    if total_input_tokens == 0:
        actions.append(("LOW", "Implement token usage tracking for cost monitoring"))

    actions.append(("LOW", "Implement caching for performance improvement"))
    actions.append(("LOW", "Add batch processing for parallel email handling"))

    # Sort and display
    priority_order = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}
    actions.sort(key=lambda x: priority_order[x[0]])

    for i, (priority, action) in enumerate(actions, 1):
        print(f"  {i}. [{priority:8s}] {action}")
    print()

    # ========================================
    # SECTION 8: SUMMARY & SCORES
    # ========================================
    print("="*100)
    print("8. OVERALL SYSTEM SCORES")
    print("="*100)
    print()

    # Calculate scores (0-100)
    customer_extraction_score = 100 if len(sds_companies) == 0 else max(0, 100 - (len(sds_companies) / len(companies) * 100))
    customer_matching_score = odoo_match_rate * 100
    product_extraction_score = 100  # Assume good if matched well
    product_matching_score = odoo_product_match_rate * 100
    intent_classification_score = (1 - len(low_conf_intents) / len(intents)) * 100 if intents else 100

    overall_score = (
        customer_extraction_score * 0.25 +
        customer_matching_score * 0.20 +
        product_extraction_score * 0.15 +
        product_matching_score * 0.25 +
        intent_classification_score * 0.15
    )

    print(f"  Customer Extraction:     {customer_extraction_score:5.1f}/100  {'[EXCELLENT]' if customer_extraction_score >= 95 else '[NEEDS WORK]'}")
    print(f"  Customer Matching:       {customer_matching_score:5.1f}/100  {'[EXCELLENT]' if customer_matching_score >= 80 else '[NEEDS WORK]'}")
    print(f"  Product Extraction:      {product_extraction_score:5.1f}/100  [ASSUMED]")
    print(f"  Product Matching:        {product_matching_score:5.1f}/100  {'[EXCELLENT]' if product_matching_score >= 90 else '[NEEDS WORK]'}")
    print(f"  Intent Classification:   {intent_classification_score:5.1f}/100  {'[EXCELLENT]' if intent_classification_score >= 90 else '[NEEDS WORK]'}")
    print()
    print(f"  OVERALL SYSTEM SCORE:    {overall_score:5.1f}/100")
    print()

    if overall_score >= 90:
        print("ASSESSMENT: System is performing EXCELLENTLY!")
    elif overall_score >= 75:
        print("ASSESSMENT: System is performing WELL with room for improvement")
    elif overall_score >= 60:
        print("ASSESSMENT: System is FUNCTIONAL but needs enhancement")
    else:
        print("ASSESSMENT: System NEEDS SIGNIFICANT IMPROVEMENT")
    print()

    print("="*100)
    print("END OF COMPREHENSIVE ANALYSIS")
    print("="*100)

if __name__ == "__main__":
    analyze_comprehensive()

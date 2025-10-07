# QUICK IMPLEMENTATION GUIDE - 95% Product Accuracy

**Goal:** Handle all real-world scenarios where customers don't provide our product codes

---

## 4 REAL-WORLD SCENARIOS

### A: No Product Code
- Customer: "DuroSeal for Bobst 16S, Grey, 177mm"
- Solution: Extract attributes → Match by brand+machine+dimensions

### B: Customer's Own Code
- Customer: "Article 8060104" (their internal code)
- Solution: Customer code mapping database → Translate to our code

### C: Generic Description
- Customer: "Heat seal tape, 1282mm width"
- Solution: RAG semantic search + dimension filtering

### D: Mixed Codes
- PDF: "Customer: 8060104 / Supplier: SDS025A"
- Solution: Multi-pass extraction → Prioritize supplier code

---

## IMPLEMENTATION (3 WEEKS)

### Week 1: Core Matching (Days 1-5)

**Day 1-2: Multi-Pass Extraction**
```python
# In mistral_agent.py

def extract_product_attributes(text):
    """Extract brand, machine type, dimensions, color"""
    return {
        'brand': 'DuroSeal',
        'machine_type': '16S',
        'dimensions': {'width': 177},
        'color': 'Grey'
    }

def normalize_product_codes(extracted):
    """Extract codes from name if not found in code field"""
    # Try extracting: SDS025, L1520, E1015, HEAT SEAL 1282
    # Return: {'primary_code': 'SDS025', 'use_name_matching': False}
```

**Day 3-4: 7-Level Smart Matcher**
```python
# In vector_store.py - NEW CLASS

class SmartProductMatcher:
    def find_match(self, product, customer_id):
        # L0: Customer code translation
        # L1: Exact code + attributes
        # L2: Fuzzy code + attributes
        # L3: Pure attribute matching (NO CODE)
        # L4: RAG semantic search
        # L5: Keyword matching
        # L6: Human review
        # L7: No match
```

**Day 5: Customer Code Mapper**
```python
# New file: retriever_module/customer_code_mapper.py

class CustomerCodeMapper:
    def translate_code(self, customer_id, code):
        """Translate 8060104 → SDS025A"""

    def add_mapping(self, customer_id, customer_code, our_code):
        """Auto-learn mappings"""
```

### Week 2: Testing & Refinement (Days 6-10)

**Day 6-7: Enhanced RAG**
- Add dimension filtering
- Keyword boosting
- Attribute validation

**Day 8-9: Integration Testing**
- Test all 4 scenarios (A, B, C, D)
- Fix edge cases
- Tune confidence thresholds

**Day 10: Real Email Testing**
- Test 20 customer emails
- Measure accuracy per scenario
- Build initial customer code mappings

### Week 3: Production Ready (Days 11-15)

**Day 11-13: Scale Testing**
- Test 50 more emails
- Build comprehensive mapping database
- Performance optimization

**Day 14-15: Deploy**
- Documentation
- User training
- Production deployment

---

## KEY FILES TO CREATE/MODIFY

### New Files:
1. `retriever_module/customer_code_mapper.py` - Customer code translation
2. `odoo_database/customer_code_mappings.json` - Mapping database

### Modify:
1. `prompts/extraction_prompt.txt` - Multi-pass extraction instructions
2. `orchestrator/mistral_agent.py` - Add attribute extraction
3. `retriever_module/vector_store.py` - Replace with SmartProductMatcher
4. `retriever_module/simple_rag.py` - Add dimension filtering

---

## SUCCESS METRICS

| Scenario | Method | Target |
|----------|--------|--------|
| A: No Code | Attributes + RAG | 85% |
| B: Customer Code | Code mapping | 95% |
| C: Generic Name | RAG + review | 70% |
| D: Mixed Codes | Smart extraction | 98% |
| E: Our Codes | Exact match | 99% |
| **OVERALL** | **Combined** | **95%** |

---

## CURRENT vs TARGET

**Current (0% accuracy):**
- Email 1: L1520, L1320 → E1015-685 (WRONG)
- Email 2: 8060104 → HEAT SEAL 1282 (WRONG)

**Target (95% accuracy):**
- Email 1: L1520 → L1520-685-33 ✅
- Email 2: 8060104 → translate → SDS025A ✅

---

## NEXT STEP

Start with **PHASE 1: Multi-Pass Extraction**
1. Update `prompts/extraction_prompt.txt`
2. Add `extract_product_attributes()` to `mistral_agent.py`
3. Add `normalize_product_codes()` to handle name-based code extraction
4. Test with 2 failed emails to verify extraction improvements

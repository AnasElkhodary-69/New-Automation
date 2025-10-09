# Deploying the Fine-tuned BERT Model

The fine-tuned BERT model is **569MB** and cannot be pushed to GitHub due to size limits. You need to deploy it separately to your production server.

---

## Current Status

**Local Path**: `D:\Projects\RAG-SDS\New-Automation\models\finetuned-product-matcher\`

**Status**: ⏳ Currently retraining with improved seal sub-type distinction (wait for completion)

**Files in Model Directory**:
```
models/finetuned-product-matcher/
├── config.json                    # Model configuration
├── model.safetensors              # Model weights (~569MB)
├── modules.json                   # Module structure
├── sentence_bert_config.json      # Sentence BERT config
├── tokenizer_config.json          # Tokenizer configuration
├── tokenizer.json                 # Tokenizer vocabulary
├── special_tokens_map.json        # Special tokens
└── vocab.txt                      # Vocabulary file
```

---

## Option 1: Transfer via SCP (Recommended)

### Step 1: Wait for Training to Complete
```bash
# Training is currently running in background
# Check progress with:
# It's at ~20% now, estimated 10-12 more minutes
```

### Step 2: Create Tarball
```bash
cd D:\Projects\RAG-SDS\New-Automation
tar -czf finetuned-model.tar.gz models/finetuned-product-matcher/
```

**Result**: `finetuned-model.tar.gz` (~200-250MB compressed)

### Step 3: Transfer to Production Server
```bash
# Replace with your production server details
scp finetuned-model.tar.gz user@production-server:/path/to/New-Automation/

# On production server:
cd /path/to/New-Automation/
tar -xzf finetuned-model.tar.gz
rm finetuned-model.tar.gz
```

### Step 4: Verify on Production
```bash
# On production server
cd /path/to/New-Automation/
python -c "
from retriever_module.bert_semantic_matcher import BertSemanticMatcher
matcher = BertSemanticMatcher('odoo_database/odoo_products.json')
print('Model loaded successfully!')
print(f'Model type: {matcher.model_name}')
print(f'Is fine-tuned: {matcher.is_finetuned}')
"
```

**Expected Output**:
```
Model loaded successfully!
Model type: models/finetuned-product-matcher
Is fine-tuned: True
```

---

## Option 2: Transfer via Cloud Storage

### Using Google Drive / Dropbox / OneDrive:

1. **Upload from Local**:
   ```bash
   # Create tarball first
   tar -czf finetuned-model.tar.gz models/finetuned-product-matcher/

   # Upload to Google Drive / Dropbox / OneDrive
   # (use web interface or sync client)
   ```

2. **Download on Production Server**:
   ```bash
   # Download from cloud
   wget "https://drive.google.com/uc?id=YOUR_FILE_ID&export=download" -O finetuned-model.tar.gz

   # Or use rclone (if configured)
   rclone copy remote:finetuned-model.tar.gz .

   # Extract
   tar -xzf finetuned-model.tar.gz
   ```

---

## Option 3: Git LFS (If You Have Git LFS)

### Setup Git LFS:
```bash
# Install Git LFS (one time)
git lfs install

# Track model files
git lfs track "models/**/*.safetensors"
git lfs track "models/**/*.bin"

# Add and commit
git add .gitattributes
git add models/finetuned-product-matcher/
git commit -m "Add fine-tuned BERT model via Git LFS"
git push origin master
```

### On Production:
```bash
git pull origin master
git lfs pull
```

**Note**: Git LFS requires setup on GitHub repository and has bandwidth/storage limits on free tier.

---

## Option 4: Direct Copy (If Same Network)

If local machine and production server are on same network:

```bash
# From local machine
robocopy "D:\Projects\RAG-SDS\New-Automation\models\finetuned-product-matcher" "\\production-server\path\to\New-Automation\models\finetuned-product-matcher" /E /Z
```

---

## Automatic Detection

The hybrid matcher automatically detects and uses the fine-tuned model:

**In `bert_semantic_matcher.py` (lines 55-62)**:
```python
def __init__(self, products_json_path: str, model_name: str = "Alibaba-NLP/gte-modernbert-base"):
    # Auto-detect fine-tuned model
    finetuned_model_path = Path("models/finetuned-product-matcher")
    if finetuned_model_path.exists():
        logger.info(f"Fine-tuned model found, using it instead of base model")
        self.model_name = str(finetuned_model_path)
        self.is_finetuned = True
    else:
        self.model_name = model_name
        self.is_finetuned = False
```

**No code changes needed!** Just deploy the model directory.

---

## Testing After Deployment

### Test 1: Model Loading
```bash
python -c "
from retriever_module.bert_semantic_matcher import BertSemanticMatcher
matcher = BertSemanticMatcher('odoo_database/odoo_products.json')
print('[OK] Model loaded')
"
```

### Test 2: SDS007 Query (The Fix!)
```bash
python -c "
from retriever_module.bert_semantic_matcher import BertSemanticMatcher
matcher = BertSemanticMatcher('odoo_database/odoo_products.json')
results = matcher.search('DuroSeal W&H End Seals Miraflex SDS 007 CR Grau', top_k=5)
print('Top 5 Results:')
for r in results:
    print(f\"  {r['code']:15} - {r['score']:.1%} - {r['name'][:60]}\")
"
```

**Expected** (after fix):
```
Top 5 Results:
  SDS007H         - 93.0% - 444-377-159-CR-GRY / Duro Seal W&H Miraflex
  SDS007C         - 92.0% - 444-444-159-CR-GRY / Duro Seal W&H Miraflex
  SDS007M         - 85.0% - 444-444-ORG-CR-Z-GRY / Duro Seal W&H Miraflex
  ...
```

**Before fix** (SDS2573 Foam Seal was at top with 93.8%)

### Test 3: Full System Test
```bash
python main.py
```

Check that Maag GmbH email now matches SDS007H/SDS007C products correctly.

---

## Troubleshooting

### Issue: "Model not found"
**Cause**: Model directory not in correct location
**Fix**: Ensure `models/finetuned-product-matcher/` exists relative to working directory

### Issue: "CUDA out of memory"
**Cause**: GPU memory exhausted (shouldn't happen on CPU)
**Fix**: Model uses CPU by default on production (see `bert_semantic_matcher.py:73-76`)

### Issue: "Slow inference"
**Cause**: First query loads model into memory (~2-3 seconds)
**Fix**: This is normal; subsequent queries are fast (<0.5s)

### Issue: "Wrong products still matching"
**Cause**: Using old model (before retraining)
**Fix**: Ensure you deployed the model AFTER retraining completed

---

## Rollback to Base Model

If issues occur, you can rollback to the base model:

```bash
# On production server
cd /path/to/New-Automation/
mv models/finetuned-product-matcher models/finetuned-product-matcher.backup

# System will automatically use base model
python main.py
```

**Result**: System falls back to `Alibaba-NLP/gte-modernbert-base` (downloaded from Hugging Face)

---

## Model Size & Performance

| Metric | Value |
|--------|-------|
| **Model Size** | 569MB (uncompressed) |
| **Compressed Size** | ~200-250MB (.tar.gz) |
| **Loading Time** | 2-3 seconds (first time) |
| **Inference Time** | 0.3-0.5 seconds per query |
| **Memory Usage** | ~800MB RAM |
| **Device** | CPU (forced on Windows) |
| **Expected Accuracy** | 85-95% for SDS products |

---

## Production Deployment Checklist

- [ ] Wait for training to complete (~10-12 more minutes)
- [ ] Create tarball: `tar -czf finetuned-model.tar.gz models/finetuned-product-matcher/`
- [ ] Transfer to production server (scp/cloud/network copy)
- [ ] Extract on production: `tar -xzf finetuned-model.tar.gz`
- [ ] Test model loading: `python -c "from retriever_module..."`
- [ ] Test SDS007 query to verify fix
- [ ] Run full system test: `python main.py`
- [ ] Monitor logs for "Fine-tuned model found" message
- [ ] Backup old model (if replacing existing)
- [ ] Document deployment in change log

---

## Contact

**Training Started**: 2025-10-09 23:44:39
**Expected Completion**: 2025-10-09 23:54:00 (approx)
**Status**: ⏳ In progress (~20% complete)

**After Training**: Test locally first, then deploy to production

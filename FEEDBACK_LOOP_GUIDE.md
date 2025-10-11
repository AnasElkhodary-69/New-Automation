# 🔄 Human-in-the-Loop Feedback System

## Overview

The RAG-SDS system includes a complete **Human-in-the-Loop (HITL) feedback system** that allows users to correct extraction errors via Telegram, and the system learns from these corrections in real-time.

---

## 🎯 Complete Flow

### Step 1: Email Processing & Notification
1. System processes incoming email
2. Extracts customer, products, and order details using DSPy
3. Sends Telegram notification with:
   - Order ID (e.g., `ORDER_1_20251012_015116`)
   - Extracted information
   - Match results (✅ Matched / ⚠️ Partial Match)
   - Feedback instructions

### Step 2: User Sends Correction (Telegram Reply)
User replies to the notification with **plain text** corrections:

**Examples:**
```
"Company should be Schur Flexibles"
"Product 2 should be code E1820-600"
"Quantity for product 1 is 20"
"Everything looks good, approve"
```

### Step 3: Telegram Bot Captures Feedback
- `telegram_bot_listener.py` polls Telegram every 2 seconds
- Detects reply to order notification
- Extracts Order ID (3 methods: reply detection, text parsing, recent order fallback)

### Step 4: Mistral AI Parses Feedback
- `mistral_feedback_parser.py` analyzes the user message
- Understands:
  - **Correction type**: `company_match`, `product_match`, `quantity`, `confirm`, `reject`
  - **Corrected values**: Extracts what needs to be fixed
  - **Confidence**: How certain the AI is (0.0-1.0)

### Step 5: Confirmation Message
System sends confirmation:
```
✅ UNDERSTOOD (Order #ORDER_123)

📝 Company Correction:
  New company: Schur Flexibles

📊 Confidence: 95%

💾 This feedback will improve future processing.
```

### Step 6: Store Feedback & Generate Training Data
- Stores correction in `feedback/corrections.json`
- Generates DSPy training example in `feedback/training_examples.json`
- Updates statistics in `feedback/feedback_stats.json`

### Step 7: 🔥 **IMMEDIATE RETRAINING & VALIDATION** (NEW!)
If `FEEDBACK_IMMEDIATE_RETRAIN=true`:

1. **Retrain DSPy model** with the correction
2. **Re-process the same email** with updated model
3. **Compare results**: Old vs New vs Expected
4. **Send validation report** to user:

```
🔬 TRAINING VALIDATION (Order #ORDER_123)
✅ Status: LEARNED SUCCESSFULLY

📝 What was corrected: Company Match

Before Training:
  Company: SDS GmbH

After Training:
  Company: Schur Flexibles

Expected:
  Company: Schur Flexibles

✅ The model learned your correction!
```

---

## 🚀 How to Enable & Test

### Prerequisites
1. Telegram bot configured (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)
2. Telegram notifications enabled (`TELEGRAM_ENABLE_NOTIFICATIONS=true`)

### Enable Immediate Retraining
Add to your `.env` file:
```bash
FEEDBACK_IMMEDIATE_RETRAIN=true
```

### Start the Feedback System

**Terminal 1: Start Telegram Bot Listener**
```bash
python telegram_bot_listener.py
```

**Terminal 2: Process Emails**
```bash
python main.py
```

### Test Flow

1. **Process a test email** (triggers notification to Telegram)
2. **Reply in Telegram** with a correction:
   ```
   Company should be Schur Flexibles
   ```
3. **Watch the bot respond** with:
   - ✅ Confirmation message
   - 🔬 Validation report showing if training worked

---

## 📂 File Structure

```
feedback/
├── order_results.json        # All processed orders
├── corrections.json           # User corrections history
├── training_examples.json     # DSPy training data
└── feedback_stats.json        # Statistics

orchestrator/
├── feedback_processor.py            # Main feedback orchestrator
├── mistral_feedback_parser.py       # Parse user feedback with Mistral
├── dspy_training_generator.py       # Generate DSPy training examples
└── dspy_entity_extractor.py         # DSPy entity extraction (gets retrained)

telegram_bot_listener.py       # Background service listening for feedback
utils/
├── feedback_storage.py        # Feedback storage operations
└── telegram_notifier.py       # Send Telegram messages
```

---

## 🔧 Configuration Options

### Environment Variables

```bash
# Enable/disable Telegram notifications
TELEGRAM_ENABLE_NOTIFICATIONS=true

# Feedback storage location
FEEDBACK_DB_PATH=feedback/

# Auto-retraining threshold (batch mode)
FEEDBACK_ENABLE_AUTO_TRAINING=false
DSPY_AUTO_RETRAIN_THRESHOLD=10

# Immediate retraining (after each feedback)
FEEDBACK_IMMEDIATE_RETRAIN=true

# Minimum confidence to accept correction
FEEDBACK_CONFIDENCE_THRESHOLD=0.8
```

---

## 📊 Supported Correction Types

1. **Company Match** (`company_match`)
   - Example: `"Company should be Schur Flexibles"`
   - Corrects customer/company extraction

2. **Product Match** (`product_match`)
   - Example: `"Product 2 should be code E1820-600"`
   - Corrects product code or name

3. **Quantity** (`quantity`)
   - Example: `"Quantity for product 1 is 20"`
   - Corrects quantity extraction

4. **Confirm** (`confirm`)
   - Example: `"Everything looks good, approve"`
   - Approves the extraction

5. **Reject** (`reject`)
   - Example: `"This is wrong, reject it"`
   - Rejects the entire extraction

---

## 🧪 Testing Without Telegram

If you want to test the feedback system without Telegram, you can directly call the feedback processor:

```python
from orchestrator.feedback_processor import FeedbackProcessor
from orchestrator.mistral_feedback_parser import MistralFeedbackParser
from orchestrator.dspy_training_generator import DSPyTrainingGenerator
from utils.feedback_storage import FeedbackStorage
from utils.telegram_notifier import TelegramNotifier

# Initialize components
storage = FeedbackStorage()
notifier = TelegramNotifier()
parser = MistralFeedbackParser(use_chain_of_thought=True)
generator = DSPyTrainingGenerator(use_chain_of_thought=True)

processor = FeedbackProcessor(
    feedback_parser=parser,
    training_generator=generator,
    feedback_storage=storage,
    telegram_notifier=notifier
)

# Process feedback
processor.process_feedback(
    order_id="ORDER_1_20251012_015116",
    user_message="Company should be Schur Flexibles",
    telegram_user_id=None
)
```

---

## 🎯 Benefits

✅ **Real-time Learning** - Model improves immediately after each correction
✅ **Instant Validation** - User sees if their feedback worked
✅ **Confidence Building** - Users trust the system is learning
✅ **Quick Debugging** - Catch training issues immediately
✅ **No Manual Retraining** - Fully automated learning loop

---

## 🔍 Order ID Detection Methods

The bot uses **3 methods** to identify which order you're referring to:

1. **Reply Detection** (Best) ⭐
   - Reply to the original notification
   - Bot extracts Order ID from replied message

2. **Text Parsing**
   - Include Order ID in your message
   - Example: `"Order ORDER_123 company should be..."`

3. **Recent Order Fallback**
   - If sent within 10 minutes of last order
   - Assumes you mean the most recent order

---

## 📈 Future Enhancements

- [ ] Batch retraining (accumulate N feedbacks, then retrain)
- [ ] A/B testing (compare old vs new model on test set)
- [ ] Persistent model storage (save retrained models)
- [ ] Multi-user feedback voting (consensus-based corrections)
- [ ] Feedback analytics dashboard

---

## 🐛 Troubleshooting

**Bot not responding?**
- Check `telegram_bot_listener.py` is running
- Verify `TELEGRAM_ENABLE_NOTIFICATIONS=true` in `.env`
- Check logs at `logs/telegram_bot.log`

**Validation shows "NOT IMPROVED"?**
- Model might need more examples (DSPy learns from patterns)
- Try providing 2-3 similar corrections
- Check if correction format matches expected format

**Order ID not detected?**
- Reply to the original notification (most reliable)
- Or include `Order ID: XXX` in your message
- Make sure feedback sent within 10 minutes of processing

---

**Ready to test?** Start the bot listener and send your first correction! 🚀

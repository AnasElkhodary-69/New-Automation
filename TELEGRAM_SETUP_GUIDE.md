# Telegram + Mistral AI Feedback System - Setup Guide

## Overview

This system sends Telegram notifications for each processed order and uses Mistral AI to intelligently parse user corrections, converting them into DSPy training data for continuous model improvement.

## Features

✅ **Real-time Telegram notifications** with parsed vs matched comparison
✅ **Natural language feedback** - no strict commands needed
✅ **Mistral AI parsing** - understands corrections automatically
✅ **DSPy training data generation** - improves model over time
✅ **Two-way communication** - clarification questions when needed
✅ **Feedback storage** - audit trail of all corrections

## Quick Start (5 minutes)

### Step 1: Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow instructions to name your bot
4. **Save the bot token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Get Your Chat ID

1. Search for `@userinfobot` on Telegram
2. Send `/start` command
3. **Save your chat ID** (looks like: `123456789`)

### Step 3: Configure Environment

Edit your `.env` file:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
TELEGRAM_ENABLE_NOTIFICATIONS=true

# Feedback System
FEEDBACK_DB_PATH=feedback/
FEEDBACK_ENABLE_AUTO_TRAINING=false
FEEDBACK_CONFIDENCE_THRESHOLD=0.8
DSPY_AUTO_RETRAIN_THRESHOLD=10
```

### Step 4: Test Connection

```bash
python -c "from utils.telegram_notifier import TelegramNotifier; n = TelegramNotifier(); n.test_connection()"
```

You should receive a test message on Telegram!

### Step 5: Start the Listener

Open a **new terminal window** and run:

```bash
python telegram_bot_listener.py
```

Keep this running in the background to receive feedback.

### Step 6: Process Emails as Normal

```bash
python main.py
```

You'll now receive Telegram notifications for each order!

## How It Works

### 1. Order Processing Flow

```
Email → Process → Send Email Notification → Send Telegram Notification → Store for Feedback
```

### 2. Feedback Processing Flow

```
User Message → Mistral Parsing → Validation → Confirmation → Storage → Training Data Generation
```

### 3. Example Notification

```
🔔 NEW ORDER #ORDER_1_20251011_143000

📧 Email Info:
  From: customer@company.com
  Subject: Order Request #12345

🏢 COMPANY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Parsed: "ABC Manufacturing"
  ✅ Matched: "ABC Manufacturing GmbH" (95%)
  📊 Odoo ID: 12345

📦 PRODUCTS (2/3 matched)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ✅ Rakelmesser Gold 35x0.20
   Parsed: "Rakelmesser Edelstahl Gold 35x0,20"
   Match: 9000841 (92%) | Odoo: #67890
   Qty: 50 | Price: €12.50

2. ✅ Cushion Mount Tape
   Parsed: "Cushion Mount 1.5mm"
   Match: CM-1500 (88%) | Odoo: #67891
   Qty: 100 | Price: €8.75

3. ❌ No match found
   Parsed: "Special blade custom"
   Qty: 25 | Price: N/A

📊 SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Intent: Order Inquiry (98%)
  Company Match: ✅
  Products: ⚠️ 2/3 (67%)
  Order Total: €1,487.50
  Order Created: ⏸️ Pending

💬 FEEDBACK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reply with corrections in plain text, e.g.:
• "Company should be XYZ GmbH"
• "Product 2 should be code 9000842"
• "Quantity for product 1 is 100"
• "Everything looks good, approve"

Order ID: ORDER_1_20251011_143000
```

## User Feedback Examples

### Simple Product Correction

**User:** "Product 3 is code 9000842"

**Bot Response:**
```
✅ UNDERSTOOD (Order #ORDER_1_20251011_143000)

📝 Product #3 Correction:
  Code: 9000842

📊 Confidence: 95%

💾 This feedback will improve future processing.
```

### Company Correction

**User:** "Actually the company is ABC GmbH & Co KG"

**Bot Response:**
```
✅ UNDERSTOOD (Order #ORDER_1_20251011_143000)

📝 Company Correction:
  New company: ABC GmbH & Co KG

📊 Confidence: 92%

💾 This feedback will improve future processing.
```

### Complex Correction

**User:** "Product 1 quantity is 100, not 50, and product 3 should be 9000842"

**Bot Response:**
```
✅ UNDERSTOOD (Order #ORDER_1_20251011_143000)

📝 Quantity Correction:
  Product #1: 100 units

📝 Product #3 Correction:
  Code: 9000842

📊 Confidence: 88%

💾 This feedback will improve future processing.
```

### Clarification Needed

**User:** "Fix product 2"

**Bot Response:**
```
❓ NEED CLARIFICATION (Order #ORDER_1_20251011_143000)

What would you like to change about product 2?
Currently matched: Cushion Mount 1.5mm (88%)

Please specify:
- Different product code?
- Different quantity?
- Different specifications?

Please provide more details so I can help you correctly.
```

### Confirmation

**User:** "Everything looks good, create the order"

**Bot Response:**
```
✅ UNDERSTOOD (Order #ORDER_1_20251011_143000)

✅ All matches confirmed!
  Order approved for creation.

📊 Confidence: 100%

💾 This feedback will improve future processing.
```

## Feedback Data Storage

All feedback is stored in `feedback/` directory:

### feedback/corrections.json
Stores all user corrections with Mistral parsing results.

### feedback/order_results.json
Stores original order processing results for comparison.

### feedback/training_examples.json
DSPy training data generated from corrections.

### feedback/feedback_stats.json
Statistics about feedback and training.

## DSPy Training Workflow

### 1. Collect Feedback
User corrections are automatically stored with Mistral parsing.

### 2. Generate Training Data
Each correction is converted to DSPy training format:

```json
{
  "training_id": "train_20251011_143000",
  "feedback_id": "fb_20251011_142500",
  "signature_type": "EntityExtractor",
  "training_data": {
    "input": {"email_body": "..."},
    "correct_output": {"products": [...]},
    "incorrect_output": {"products": [...]}
  },
  "error_analysis": "System confused similar product codes...",
  "training_weight": 8.5,
  "training_priority": "next_batch"
}
```

### 3. Export Training Data

```bash
python -c "from orchestrator.feedback_processor import FeedbackProcessor; from utils.feedback_storage import FeedbackStorage; from orchestrator.mistral_feedback_parser import MistralFeedbackParser; from orchestrator.dspy_training_generator import DSPyTrainingGenerator; from utils.telegram_notifier import TelegramNotifier; storage = FeedbackStorage(); parser = MistralFeedbackParser(); generator = DSPyTrainingGenerator(); notifier = TelegramNotifier(); processor = FeedbackProcessor(parser, generator, storage, notifier); processor.export_training_data('dspy_training/training_examples.json')"
```

### 4. View Training Statistics

```bash
python -c "from orchestrator.feedback_processor import FeedbackProcessor; from utils.feedback_storage import FeedbackStorage; from orchestrator.mistral_feedback_parser import MistralFeedbackParser; from orchestrator.dspy_training_generator import DSPyTrainingGenerator; from utils.telegram_notifier import TelegramNotifier; storage = FeedbackStorage(); parser = MistralFeedbackParser(); generator = DSPyTrainingGenerator(); notifier = TelegramNotifier(); processor = FeedbackProcessor(parser, generator, storage, notifier); import json; print(json.dumps(processor.get_training_statistics(), indent=2))"
```

## Monitoring & Analytics

### Check Feedback Stats

```python
from utils.feedback_storage import FeedbackStorage

storage = FeedbackStorage()
stats = storage.get_feedback_stats()

print(f"Feedback received: {stats['feedback_received']}")
print(f"Training examples: {stats['training_examples_generated']}")
print(f"Examples used: {stats['training_examples_used']}")
```

### View Recent Corrections

```python
from utils.feedback_storage import FeedbackStorage

storage = FeedbackStorage()
feedback_list = storage._read_json(storage.feedback_file)

# Get last 5 corrections
for fb in feedback_list[-5:]:
    print(f"Order: {fb['order_id']}")
    print(f"Type: {fb['mistral_parsing']['correction_type']}")
    print(f"Message: {fb['user_message']}")
    print("---")
```

## Troubleshooting

### Bot Not Receiving Messages

1. **Check bot token:**
   ```bash
   python -c "from utils.telegram_notifier import TelegramNotifier; n = TelegramNotifier(); print(n.get_bot_info())"
   ```

2. **Check chat ID:**
   - Send a message to your bot
   - Run: `curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Look for `"chat":{"id":123456789}` in the response

3. **Check listener is running:**
   ```bash
   # Should show telegram_bot_listener.py process
   ps aux | grep telegram
   ```

### Listener Not Responding

1. **Check logs:**
   ```bash
   tail -f logs/telegram_bot.log
   ```

2. **Restart listener:**
   ```bash
   # Kill old process
   pkill -f telegram_bot_listener.py

   # Start new one
   python telegram_bot_listener.py
   ```

### Mistral Parsing Errors

1. **Check DSPy configuration:**
   ```bash
   python -c "from orchestrator.dspy_config import setup_dspy; setup_dspy(); print('DSPy configured')"
   ```

2. **Test feedback parser:**
   ```bash
   python -c "from orchestrator.mistral_feedback_parser import MistralFeedbackParser; parser = MistralFeedbackParser(); print('Parser ready')"
   ```

### Feedback Not Storing

1. **Check feedback directory:**
   ```bash
   ls -la feedback/
   ```

2. **Check permissions:**
   ```bash
   chmod -R 755 feedback/
   ```

## Advanced Configuration

### Auto-Retraining

Enable automatic DSPy retraining when feedback threshold is reached:

```bash
# .env
FEEDBACK_ENABLE_AUTO_TRAINING=true
DSPY_AUTO_RETRAIN_THRESHOLD=10  # Retrain after 10 corrections
```

### Custom Confidence Threshold

Adjust when Mistral should ask for clarification:

```bash
# .env
FEEDBACK_CONFIDENCE_THRESHOLD=0.8  # Ask clarification below 80%
```

### Multiple Users

Add multiple authorized chat IDs (requires code modification):

```python
# telegram_bot_listener.py
AUTHORIZED_CHAT_IDS = [123456789, 987654321]

# In _process_update method:
if chat_id not in AUTHORIZED_CHAT_IDS:
    logger.warning(f"Unauthorized chat: {chat_id}")
    return
```

## Running in Production

### 1. Use systemd (Linux)

Create `/etc/systemd/system/telegram-bot.service`:

```ini
[Unit]
Description=Telegram Feedback Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/before-bert
ExecStart=/usr/bin/python3 telegram_bot_listener.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

### 2. Use screen (Simple)

```bash
# Start in detached screen session
screen -dmS telegram-bot python telegram_bot_listener.py

# View logs
screen -r telegram-bot

# Detach: Ctrl+A then D

# Kill
screen -X -S telegram-bot quit
```

### 3. Use nohup (Simplest)

```bash
nohup python telegram_bot_listener.py > logs/telegram_bot_nohup.log 2>&1 &

# View logs
tail -f logs/telegram_bot_nohup.log

# Kill
pkill -f telegram_bot_listener.py
```

## Cost Estimation

**Mistral API Calls per Order with Feedback:**
- 1 call for feedback parsing (~500 tokens) = $0.001
- 1 call for training data generation (~800 tokens) = $0.002
- Optional clarification (~300 tokens) = $0.0005

**Total per corrected order:** ~$0.003

**Monthly estimate (100 orders, 30% need corrections):**
- 30 orders × $0.003 = **$0.09/month**

**Extremely affordable!**

## Support & Documentation

- **Full plan:** `TELEGRAM_MISTRAL_FEEDBACK_PLAN.md`
- **DSPy signatures:** `orchestrator/dspy_feedback_signatures.py`
- **Main system:** `main.py` (line 221-239)
- **Bot listener:** `telegram_bot_listener.py`

## Security Notes

1. **Never commit .env** to version control
2. **Bot token is sensitive** - treat like a password
3. **Validate chat IDs** before processing feedback
4. **Audit all corrections** before applying to production
5. **Review training data** before retraining models

## Next Steps

1. ✅ Complete this setup guide
2. 📊 Monitor first 10-20 orders with feedback
3. 📈 Review training data quality
4. 🔄 Implement automated retraining (optional)
5. 🎯 Expand to multiple users (optional)
6. 📱 Add voice message support (future)

---

**Setup complete!** You now have intelligent Telegram notifications with Mistral AI-powered feedback processing for continuous DSPy improvement. 🎉

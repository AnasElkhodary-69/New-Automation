# Telegram Integration - Quick Start Guide

## ✅ Status: READY TO TEST

All components have been implemented and connected. Follow these steps to activate the Telegram feedback system.

## 🚀 5-Minute Setup

### Step 1: Create Your Telegram Bot (2 minutes)

1. **Open Telegram** on your phone or computer
2. **Search for** `@BotFather`
3. **Send** `/newbot` command
4. **Follow the prompts:**
   - Enter bot name (e.g., "SDS Order Bot")
   - Enter username (e.g., "sds_order_bot")
5. **Copy the bot token** - looks like:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

### Step 2: Get Your Chat ID (1 minute)

1. **Search for** `@userinfobot` on Telegram
2. **Send** `/start` command
3. **Copy your chat ID** - looks like: `123456789`

### Step 3: Configure .env (1 minute)

Edit your `.env` file and add:

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

Replace with your actual bot token and chat ID!

### Step 4: Test Connection (1 minute)

Run the integration test:

```bash
python test_telegram_integration.py
```

You should see:
```
[1/7] Testing environment configuration...
  [OK] Token: 123456789:ABCdefGH...
  [OK] Chat ID: 123456789
  [OK] Enabled: True

[2/7] Testing component imports...
  [OK] All components imported successfully

[3/7] Initializing components...
  [OK] Telegram notifier initialized
  [OK] Message formatter initialized
  [OK] Feedback storage initialized

[4/7] Testing Telegram bot connection...
  [OK] Bot connected: @sds_order_bot
  [OK] Bot name: SDS Order Bot

[5/7] Sending test notification...
  [OK] Test notification sent
  [OK] Order ID: TEST_ORDER_20251011_234500
  [OK] Message ID: 12345
  [OK] Check your Telegram for the notification!

[6/7] Storing order result for feedback...
  [OK] Order result stored
  [OK] Feedback tracking enabled

[7/7] Verifying feedback storage...
  [OK] Order retrieved from storage
  [OK] Total feedback received: 0
  [OK] Training examples generated: 0

INTEGRATION TEST COMPLETE
```

**Check your Telegram!** You should receive a test notification.

## 🎯 Usage

### Start the Feedback Listener

Open a **new terminal window** and run:

```bash
python telegram_bot_listener.py
```

Keep this running in the background. You should see:

```
================================================================
Telegram Bot Listener Starting...
================================================================
Initializing DSPy...
Initializing feedback components...
Telegram bot listener initialized
Starting Telegram bot listener (polling every 2s)
Press Ctrl+C to stop
```

### Process Emails as Normal

In your main terminal:

```bash
python main.py
```

For each order processed, you'll receive:
1. ✅ Console output (as before)
2. ✅ Email notification (as before)
3. ✅ **NEW: Telegram notification** with parsed vs matched comparison

### Give Feedback

Reply to any Telegram notification naturally:

**Examples:**

```
"Product 3 should be code 9000842"

"Company is actually XYZ GmbH & Co KG"

"Quantity for product 1 is 100, not 50"

"Everything looks good, approve it"
```

The system will:
1. ✅ Parse your message with Mistral AI
2. ✅ Understand your intent
3. ✅ Send confirmation
4. ✅ Store feedback
5. ✅ Generate DSPy training data

## 📱 Example Notification

You'll receive messages like this:

```
🔔 NEW ORDER #ORDER_1_20251011_143000

📧 Email Info:
  From: customer@company.com
  Subject: Order #12345

🏢 COMPANY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Parsed: "ABC Manufacturing"
  ✅ Matched: "ABC Manufacturing GmbH" (95%)
  📊 Odoo ID: 12345

📦 PRODUCTS (2/3 matched)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ✅ Rakelmesser Gold 35x0.20
   Match: 9000841 (92%) | Odoo: #67890
   Qty: 50 | Price: €12.50

2. ✅ Cushion Mount Tape
   Match: CM-1500 (88%) | Odoo: #67891
   Qty: 100 | Price: €8.75

3. ❌ No match found
   Parsed: "Special blade custom"

📊 SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Intent: Order Inquiry (98%)
  Company Match: ✅
  Products: ⚠️ 2/3 (67%)
  Order Total: €1,487.50

💬 FEEDBACK
Reply with corrections in plain text
Order ID: ORDER_1_20251011_143000
```

## 🧪 Testing Feedback

### Test 1: Simple Product Correction

Send to your bot:
```
"Product 3 is code 9000842"
```

Expected response:
```
✅ UNDERSTOOD (Order #ORDER_1_...)

📝 Product #3 Correction:
  Code: 9000842

📊 Confidence: 95%

💾 This feedback will improve future processing.
```

### Test 2: Company Correction

```
"Company should be XYZ GmbH"
```

Expected response:
```
✅ UNDERSTOOD (Order #ORDER_1_...)

📝 Company Correction:
  New company: XYZ GmbH

📊 Confidence: 90%

💾 This feedback will improve future processing.
```

### Test 3: Unclear Feedback

```
"Fix product 2"
```

Expected response:
```
❓ NEED CLARIFICATION (Order #ORDER_1_...)

What would you like to change about product 2?
Currently matched: Cushion Mount 1.5mm (88%)

Please provide more details so I can help you correctly.
```

## 📊 Monitor Feedback

### Check Stored Feedback

```bash
python -c "from utils.feedback_storage import FeedbackStorage; s = FeedbackStorage(); import json; print(json.dumps(s.get_feedback_stats(), indent=2))"
```

### View Training Examples

```bash
ls -la feedback/
```

You'll see:
- `corrections.json` - User corrections
- `order_results.json` - Original results
- `training_examples.json` - DSPy training data
- `feedback_stats.json` - Statistics

## 🔧 Troubleshooting

### Bot Not Receiving Test Message?

1. **Check bot token:**
   ```bash
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('TELEGRAM_BOT_TOKEN'))"
   ```

2. **Verify bot is active:**
   - Go to Telegram
   - Search for your bot
   - Send `/start` command
   - Bot should respond

### Listener Not Responding?

1. **Check if running:**
   ```bash
   ps aux | grep telegram_bot_listener
   ```

2. **Check logs:**
   ```bash
   tail -f logs/telegram_bot.log
   ```

3. **Restart:**
   ```bash
   # Kill if stuck
   pkill -f telegram_bot_listener

   # Start again
   python telegram_bot_listener.py
   ```

### Imports Failing?

```bash
# Test individual components
python -c "from utils.telegram_notifier import TelegramNotifier; print('OK')"
python -c "from orchestrator.mistral_feedback_parser import MistralFeedbackParser; print('OK')"
python -c "from orchestrator.feedback_processor import FeedbackProcessor; print('OK')"
```

## 📂 File Structure

```
before-bert/
├── utils/
│   ├── telegram_notifier.py          # Send Telegram messages
│   ├── telegram_message_formatter.py # Format messages
│   └── feedback_storage.py           # Store feedback
├── orchestrator/
│   ├── dspy_feedback_signatures.py   # DSPy signatures
│   ├── mistral_feedback_parser.py    # Parse feedback
│   ├── dspy_training_generator.py    # Generate training data
│   └── feedback_processor.py         # Orchestrate workflow
├── feedback/                          # Feedback database
│   ├── corrections.json
│   ├── order_results.json
│   ├── training_examples.json
│   └── feedback_stats.json
├── telegram_bot_listener.py          # Background service
├── test_telegram_integration.py      # Integration test
└── main.py                            # Updated with Telegram
```

## 💰 Cost

**Per corrected order:** ~$0.003 (Mistral API)
**Monthly (100 orders, 30% corrections):** ~$0.09

Extremely affordable!

## 🎓 Learn More

- **Full documentation:** `TELEGRAM_SETUP_GUIDE.md`
- **Architecture plan:** `TELEGRAM_MISTRAL_FEEDBACK_PLAN.md`
- **Implementation summary:** `TELEGRAM_IMPLEMENTATION_SUMMARY.md`

## ✅ Checklist

Before going live:

- [ ] Bot token configured in .env
- [ ] Chat ID configured in .env
- [ ] Test notification received on Telegram
- [ ] Listener running in background
- [ ] Feedback directory exists
- [ ] DSPy configured (USE_DSPY=true in .env)
- [ ] Mistral API key working

## 🎉 You're Ready!

Everything is connected and ready to use. Start processing emails and receive intelligent Telegram notifications with AI-powered feedback!

**Next:** Process a real email and test the complete workflow!

```bash
# Terminal 1: Start listener
python telegram_bot_listener.py

# Terminal 2: Process emails
python main.py
```

Then reply to any Telegram notification with feedback! 🚀

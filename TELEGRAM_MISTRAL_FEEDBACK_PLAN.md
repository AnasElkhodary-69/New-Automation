# Telegram + Mistral AI Feedback System Implementation Plan

## Overview
Intelligent two-way communication system where Mistral AI interprets natural language feedback from Telegram users and converts it into structured DSPy training data.

## Architecture

```
Email Processing → Telegram Notification → User Feedback (Natural Language)
                                                    ↓
                                          Mistral AI Parser
                                                    ↓
                                    Structured Correction + Confirmation
                                                    ↓
                                          Feedback Storage
                                                    ↓
                                    DSPy Training Data Generator
                                                    ↓
                                    Continuous Model Improvement
```

## Components to Implement

### 1. Telegram Notifier (`utils/telegram_notifier.py`)

**Purpose:** Send structured order processing results to Telegram

**Key Functions:**
- `send_order_notification(email, result)` - Send parsed vs matched comparison
- `format_comparison_message(result)` - Format message with emoji indicators
- `create_inline_keyboard(order_id)` - Quick action buttons

**Message Format:**
```
🔔 NEW ORDER #SO12345

🏢 COMPANY
  Parsed: "ABC Manufacturing"
  Matched: "ABC Manufacturing GmbH" (95%)
  Odoo ID: 12345

📦 PRODUCTS (2/3 matched)
1. ✅ Rakelmesser Gold 35x0.20
   Match: 9000841 (92%) | Qty: 50

2. ✅ Cushion Mount Tape
   Match: CM-1500 (88%) | Qty: 100

3. ⚠️ Special blade custom
   No match found

💬 Reply with corrections or 'confirm' to approve
```

### 2. Telegram Bot Listener (`telegram_bot_listener.py`)

**Purpose:** Listen for user feedback messages

**Key Functions:**
- `start_listener()` - Start polling for messages
- `handle_message(message)` - Route message to Mistral parser
- `handle_callback(callback)` - Handle button clicks
- `send_confirmation(chat_id, message)` - Confirm receipt

**Supported Input Types:**
- Natural language corrections
- Voice messages (convert to text)
- Reply to specific notification
- Quick action buttons

### 3. Mistral AI Feedback Parser (`orchestrator/mistral_feedback_parser.py`)

**Purpose:** Understand user intent and extract structured corrections

**DSPy Signature:**
```python
class FeedbackParser(dspy.Signature):
    """Parse natural language feedback into structured corrections"""

    original_result = dspy.InputField(
        desc="Original processing result (JSON with company, products, matches)"
    )
    user_message = dspy.InputField(
        desc="User's natural language feedback from Telegram"
    )
    order_id = dspy.InputField()

    correction_type = dspy.OutputField(
        desc="company_match | product_match | quantity | price | confirm | reject | clarify"
    )
    corrections = dspy.OutputField(
        desc="Structured JSON with specific field corrections"
    )
    confidence = dspy.OutputField(desc="0.0-1.0")
    needs_clarification = dspy.OutputField(desc="true/false")
    clarification_question = dspy.OutputField()
```

**Example Conversations:**

| User Input | Mistral Parsing | Bot Response |
|------------|----------------|--------------|
| "Product 2 should be 9000842" | `{type: "product_match", product_index: 2, correct_code: "9000842"}` | "✅ Got it! Product #2 → 9000842" |
| "Company is XYZ not ABC" | `{type: "company_match", correct_name: "XYZ"}` | "✅ Corrected company to XYZ" |
| "Everything correct" | `{type: "confirm"}` | "✅ Order confirmed!" |
| "Fix product 3" | `{type: "clarify", needs_clarification: true}` | "❓ What should product 3 be?" |

### 4. Feedback Storage (`utils/feedback_storage.py`)

**Purpose:** Store corrections for DSPy training

**Database Schema:**
```json
{
  "feedback_id": "fb_20251011_001",
  "order_id": "SO12345",
  "email_id": "msg_12345",
  "timestamp": "2025-10-11T14:30:00Z",

  "original_extraction": {
    "company_parsed": "ABC Manufacturing",
    "company_matched": "ABC Manufacturing GmbH",
    "products_parsed": [...],
    "products_matched": [...]
  },

  "user_feedback": {
    "raw_message": "Product 3 should be code 9000999, qty 75",
    "parsed_by_mistral": {
      "correction_type": "product_match",
      "product_index": 3,
      "correct_code": "9000999",
      "correct_quantity": 75
    },
    "confidence": 0.95
  },

  "dspy_training_data": {
    "signature": "entity_extraction",
    "input": "Original email text...",
    "expected_output": {"products": [{"code": "9000999", "quantity": 75}]},
    "actual_output": {"products": [{"code": null, "quantity": 50}]},
    "training_ready": true
  },

  "status": "pending_review",
  "applied_to_model": false
}
```

**Key Functions:**
- `store_feedback(order_id, user_message, mistral_parsing)`
- `get_training_examples(signature_type)` - Export for DSPy
- `mark_as_applied(feedback_id)` - Track what's been used
- `get_feedback_stats()` - Analytics

### 5. DSPy Training Data Generator (`orchestrator/dspy_training_generator.py`)

**Purpose:** Convert corrections to DSPy training format

**Mistral Agent Function:**
```python
def generate_dspy_training_example(
    original_email: str,
    original_extraction: Dict,
    user_correction: Dict
) -> Dict:
    """
    Use Mistral to analyze what went wrong and create training example

    Returns:
        {
            "signature_type": "EntityExtractor" | "ProductConfirmer",
            "training_example": {
                "input": "...",
                "expected_output": "...",
                "rationale": "Why this is correct..."
            }
        }
    """
```

**DSPy Signature:**
```python
class TrainingExampleGenerator(dspy.Signature):
    """Generate DSPy training examples from user corrections"""

    email_text = dspy.InputField(desc="Original email content")
    system_output = dspy.InputField(desc="What the system extracted")
    user_correction = dspy.InputField(desc="What user said was correct")

    dspy_signature = dspy.OutputField(
        desc="Which DSPy signature to train: EntityExtractor, ProductConfirmer, IntentClassifier"
    )
    training_input = dspy.OutputField(desc="Input for training example")
    correct_output = dspy.OutputField(desc="Expected output")
    error_analysis = dspy.OutputField(
        desc="Why did the system make this mistake? What pattern should it learn?"
    )
    training_weight = dspy.OutputField(
        desc="How important is this correction? 1-10"
    )
```

### 6. Feedback Processor (`orchestrator/feedback_processor.py`)

**Purpose:** Apply corrections and trigger retraining

**Key Functions:**
```python
class FeedbackProcessor:
    def __init__(self, mistral_agent, feedback_storage, dspy_trainer):
        self.mistral = mistral_agent
        self.storage = feedback_storage
        self.trainer = dspy_trainer

    def process_telegram_feedback(self, order_id, user_message):
        """Main entry point for processing feedback"""
        # 1. Get original result
        original = self.storage.get_order_result(order_id)

        # 2. Use Mistral to parse feedback
        parsed = self.mistral.parse_feedback(original, user_message)

        # 3. Validate and confirm with user
        confirmation = self._confirm_understanding(parsed)

        # 4. Store feedback
        self.storage.store_feedback(order_id, user_message, parsed)

        # 5. Generate training data
        training = self.generate_training_data(original, parsed)

        # 6. (Optional) Trigger retraining
        if self.should_retrain():
            self.trainer.retrain_with_feedback()

    def generate_training_data(self, original, correction):
        """Use Mistral to convert correction to DSPy training format"""
        return self.mistral.generate_training_example(
            email_text=original['email']['body'],
            system_output=original['extraction'],
            user_correction=correction
        )
```

### 7. Integration Point (`main.py`)

**Modification at line 209:**
```python
# Step 6: Send email notification (existing)
self.email_notifier.send_processing_notification(email, result)

# Step 7: Send Telegram notification (NEW)
if self.telegram_notifier:
    telegram_msg = self.telegram_notifier.send_order_notification(
        email,
        result,
        order_id=result.get('order_id', f"ORDER_{idx}")
    )

    # Store for feedback tracking
    self.feedback_processor.store_order_result(
        order_id=telegram_msg['order_id'],
        result=result,
        telegram_message_id=telegram_msg['message_id']
    )
```

## Environment Variables (Add to .env)

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id  # Use @userinfobot to get
TELEGRAM_ENABLE_NOTIFICATIONS=true

# Feedback System
FEEDBACK_DB_PATH=feedback/corrections.json
FEEDBACK_ENABLE_AUTO_TRAINING=false  # Manual review first
FEEDBACK_MISTRAL_MODEL=mistral-large-latest
FEEDBACK_CONFIDENCE_THRESHOLD=0.8  # Ask for clarification if below

# Training
DSPY_TRAINING_DIR=dspy_training/
DSPY_AUTO_RETRAIN_THRESHOLD=10  # Retrain after 10 corrections
```

## Implementation Phases

### Phase 1: Read-Only Notifications (Week 1)
✅ Telegram notification sending
✅ Message formatting
✅ Basic order summary
**Goal:** Get notifications working

### Phase 2: Feedback Collection (Week 2)
✅ Telegram bot listener
✅ Message storage
✅ Basic Mistral parsing
**Goal:** Collect and understand feedback

### Phase 3: Mistral AI Integration (Week 3)
✅ FeedbackParser DSPy signature
✅ Intelligent correction parsing
✅ Clarification questions
**Goal:** Accurately parse user intent

### Phase 4: DSPy Training Generation (Week 4)
✅ Training data format
✅ TrainingExampleGenerator signature
✅ Export training examples
**Goal:** Generate quality training data

### Phase 5: Automated Improvement (Week 5)
✅ Periodic retraining
✅ Performance tracking
✅ A/B testing new models
**Goal:** Continuous improvement loop

## Example User Conversations

### Conversation 1: Simple Product Correction
```
🤖 Bot: [Sends order notification]
      Product 3: ⚠️ No match found

👤 User: "Product 3 is 9000842"

🤖 Bot: "✅ Got it! Updating product 3 to code 9000842.
         Should I search Odoo for this product?"

👤 User: "yes"

🤖 Bot: "✅ Found: Rakelmesser Gold 40x0.25 (€15.50)
         Order updated! Total: €1,650.00"
```

### Conversation 2: Complex Correction
```
🤖 Bot: [Sends order notification]
      Company: ABC Manufacturing (95%)
      Product 1: Rakelmesser Gold (92%)
      Product 2: Cushion Mount (88%)

👤 User: "Actually the company is ABC GmbH & Co KG,
         and product 1 quantity should be 100 not 50"

🤖 Bot: "✅ Understood! I'll update:
         - Company: ABC GmbH & Co KG
         - Product 1 quantity: 50 → 100

         New order total: €2,100.00
         Confirm these changes?"

👤 User: "yes confirm"

🤖 Bot: "✅ Order updated and saved!
         This feedback will help improve future orders."
```

### Conversation 3: Clarification Needed
```
👤 User: "Fix product 2"

🤖 Bot: "❓ I need more details about product 2:
         Currently matched: Cushion Mount 1.5mm (88%)

         What would you like to change?
         - Different product?
         - Different quantity?
         - Different specifications?"

👤 User: "Different product, it should be 2.0mm not 1.5mm"

🤖 Bot: "✅ Searching for Cushion Mount 2.0mm...
         Found: Cushion Mount Tape 2.0mm (Code: CM-2000)
         Update product 2 to this?"

👤 User: "yes"

🤖 Bot: "✅ Updated! Product 2 → CM-2000"
```

## Benefits

### For Operations
- **Instant notifications** of new orders
- **Mobile corrections** without accessing system
- **Voice input support** for hands-free operation
- **Audit trail** of all corrections

### For DSPy Improvement
- **Real corrections** from actual use cases
- **Pattern learning** from recurring mistakes
- **Confidence calibration** based on feedback
- **Targeted improvement** of specific weaknesses

### For Development
- **Natural language interface** - no need to change code
- **Incremental learning** - model improves continuously
- **Error analysis** - understand what goes wrong
- **A/B testing** - compare old vs new model performance

## Monitoring & Analytics

### Track These Metrics
- **Correction rate** by type (company, product, quantity)
- **Mistral parsing accuracy** (how often it understands feedback)
- **DSPy improvement rate** (reduction in corrections over time)
- **Response time** (notification to user feedback)
- **Auto-approval rate** (orders above confidence threshold)

### Dashboard Queries
```python
# Most common corrections
feedback_storage.get_correction_frequencies()

# Mistral parsing accuracy
feedback_storage.get_parsing_accuracy()

# DSPy improvement over time
feedback_storage.get_accuracy_trend(days=30)

# Products with most corrections
feedback_storage.get_problematic_products(limit=10)
```

## Security Considerations

1. **Authentication**: Only authorized Telegram users can send feedback
2. **Validation**: Mistral validates corrections before applying
3. **Approval workflow**: High-value orders require explicit confirmation
4. **Audit logging**: All corrections logged with timestamp and user
5. **Rollback**: Ability to undo incorrect corrections

## Testing Strategy

### Unit Tests
- Mistral parsing accuracy on sample feedback
- Feedback storage and retrieval
- Training data generation format

### Integration Tests
- End-to-end: Telegram → Mistral → Storage → DSPy
- Notification delivery
- Concurrent feedback handling

### User Acceptance Tests
- Natural language understanding
- Clarification flow
- Correction application

## Next Steps

1. **Create Telegram bot** via @BotFather
2. **Implement basic notifier** (Phase 1)
3. **Test message formatting**
4. **Add Mistral feedback parser** (Phase 3)
5. **Collect real feedback** (Phase 2)
6. **Generate training data** (Phase 4)
7. **Implement retraining** (Phase 5)

## Files to Create

```
utils/
  telegram_notifier.py          # Send notifications
  telegram_listener.py           # Receive feedback
  feedback_storage.py            # Store corrections
  telegram_message_formatter.py # Format messages

orchestrator/
  mistral_feedback_parser.py    # Parse feedback with Mistral
  dspy_training_generator.py    # Generate training data
  feedback_processor.py          # Orchestrate feedback flow

tools/
  retrain_dspy_from_feedback.py # Retraining script
  feedback_analytics.py          # Analytics and reports
  test_feedback_parsing.py       # Test Mistral parsing

feedback/
  corrections.json               # Feedback database
  training_examples.json         # DSPy training data
  feedback_stats.json            # Analytics

telegram_bot_listener.py         # Main bot service (background)
```

## Cost Estimation

**Mistral API Calls per Order:**
- 1 call for feedback parsing (~500 tokens)
- 1 call for training data generation (~800 tokens)
- Optional: 1 call for clarification (~300 tokens)

**Estimated cost per corrected order:** $0.002 - $0.005

**Monthly estimate (100 orders, 30% need corrections):**
- 30 orders × 2 calls × $0.003 = **~$0.18/month**

**Extremely cost-effective for the value provided!**

"""
DSPy Signatures for Feedback Parsing
Intelligent parsing of user corrections using structured prediction
"""

import dspy


class FeedbackParser(dspy.Signature):
    """
    Parse natural language feedback from Telegram users into structured corrections

    This signature handles various types of user corrections including:
    - Company name corrections
    - Product matching corrections
    - Quantity and price adjustments
    - General confirmations or rejections
    """

    # Input fields
    original_result = dspy.InputField(
        desc="""Original order processing result in JSON format with:
        - intent: {type, confidence}
        - entities: {company_name, product_names, quantities, prices}
        - context: {customer_info, products matched}
        - odoo_matches: {customer, products}"""
    )

    user_message = dspy.InputField(
        desc="""User's natural language feedback message from Telegram.
        Examples:
        - "Company should be XYZ GmbH"
        - "Product 2 is wrong, code should be 9000842"
        - "Quantity for product 1 is 100, not 50"
        - "Everything looks good"
        - "Fix product 3"
        """
    )

    order_id = dspy.InputField(
        desc="Order identifier being discussed (e.g., SO12345)"
    )

    # Output fields
    correction_type = dspy.OutputField(
        desc="""Type of correction the user is requesting. Must be ONE of:
        - company_match: User correcting company name or match
        - product_match: User correcting product identification
        - quantity: User correcting product quantity
        - price: User correcting product price
        - address: User correcting shipping address
        - confirm: User confirming everything is correct
        - reject: User rejecting the order/processing
        - clarify: User message is unclear, needs clarification
        """
    )

    corrections = dspy.OutputField(
        desc="""Structured corrections in JSON format. Format depends on correction_type:

        For company_match:
        {
          "correct_company_name": "ABC Manufacturing GmbH",
          "correct_odoo_id": 12345 (optional if user specified)
        }

        For product_match:
        {
          "product_index": 2,
          "correct_product_name": "Rakelmesser Gold 40x0.25",
          "correct_product_code": "9000842",
          "correct_odoo_id": 67890 (optional)
        }

        For quantity:
        {
          "product_index": 1,
          "correct_quantity": 100,
          "original_quantity": 50
        }

        For price:
        {
          "product_index": 1,
          "correct_price": 15.50,
          "currency": "EUR"
        }

        For confirm:
        {
          "confirmed": true,
          "create_order": true
        }

        For reject:
        {
          "reason": "User's reason for rejection"
        }

        For clarify:
        {
          "unclear_item": "product 3" or "company" or "quantity"
        }
        """
    )

    affected_items = dspy.OutputField(
        desc="""List of specific items affected by this correction.
        Examples:
        - ["product_2"] for product corrections
        - ["company"] for company corrections
        - ["product_1", "quantity_1"] for quantity corrections
        - ["all"] for confirmations
        """
    )

    user_reasoning = dspy.OutputField(
        desc="""Extract and summarize the user's reasoning or explanation.
        If the user provided context, capture it here.
        Examples:
        - "User specified exact product code 9000842"
        - "User confirmed all details are correct"
        - "User indicated wrong company name"
        """
    )

    confidence = dspy.OutputField(
        desc="""Confidence that the feedback was correctly understood (0.0 to 1.0).
        High confidence (>0.8): Clear, specific corrections
        Medium confidence (0.5-0.8): Somewhat ambiguous
        Low confidence (<0.5): Very unclear, needs clarification
        """
    )

    needs_clarification = dspy.OutputField(
        desc="""Boolean (true/false): Does this feedback need clarification?
        Set to true if:
        - User message is too vague ("fix it", "wrong")
        - Multiple interpretations possible
        - Critical information missing
        - confidence < 0.7
        """
    )

    clarification_question = dspy.OutputField(
        desc="""If needs_clarification=true, generate a helpful question to ask the user.
        Should be specific and guide the user to provide needed information.
        Examples:
        - "What should product 2 be? Please provide product code or full name."
        - "Which company is correct? Please provide the full company name."
        - "What quantity did you order for product 1?"

        If needs_clarification=false, return empty string.
        """
    )


class MultiFeedbackParser(dspy.Signature):
    """
    Parse natural language feedback that may contain MULTIPLE corrections in one message

    Handles messages like:
    - "Company is wrong, should be ABC GmbH. Product 1 should be code XYZ. Product 3 quantity is 50."
    - "Product 1 should be 3M Tape 685mm and Product 3 should be 3M Tape 457mm"
    - "Company not in database. Product 2 wrong."
    """

    # Input fields
    original_result = dspy.InputField(
        desc="""Original order processing result in JSON format with:
        - intent: {type, confidence}
        - entities: {company_name, product_names, quantities, prices}
        - context: {customer_info, products matched}
        - odoo_matches: {customer, products}"""
    )

    user_message = dspy.InputField(
        desc="""User's natural language feedback message that may contain multiple corrections.
        Examples:
        - "Company should be XYZ GmbH"
        - "Product 1 should be code ABC, Product 3 should be code DEF"
        - "Company is wrong. Product 2 quantity is 100."
        """
    )

    order_id = dspy.InputField(
        desc="Order identifier being discussed (e.g., ORDER_1_20251011_164722)"
    )

    # Output fields
    corrections_list = dspy.OutputField(
        desc="""JSON array of ALL corrections found in the message. Each correction has:
        {
          "correction_type": "company_match" | "product_match" | "quantity" | "price" | "confirm" | "reject",
          "corrections": {...},  // Type-specific correction data
          "affected_items": ["product_1", "company", etc.],
          "confidence": 0.0-1.0,
          "reasoning": "Why this correction"
        }

        Examples:

        For "Company is ABC GmbH. Product 1 should be code XYZ":
        [
          {
            "correction_type": "company_match",
            "corrections": {"correct_company_name": "ABC GmbH"},
            "affected_items": ["company"],
            "confidence": 0.95,
            "reasoning": "User specified exact company name"
          },
          {
            "correction_type": "product_match",
            "corrections": {"product_index": 1, "correct_product_code": "XYZ"},
            "affected_items": ["product_1"],
            "confidence": 0.90,
            "reasoning": "User specified code for product 1"
          }
        ]

        For "Product 1 should be 3M Tape 685mm. Product 3 should be 3M Tape 457mm":
        [
          {
            "correction_type": "product_match",
            "corrections": {"product_index": 1, "correct_product_name": "3M Tape 685mm"},
            "affected_items": ["product_1"],
            "confidence": 0.95,
            "reasoning": "User specified product 1 name"
          },
          {
            "correction_type": "product_match",
            "corrections": {"product_index": 3, "correct_product_name": "3M Tape 457mm"},
            "affected_items": ["product_3"],
            "confidence": 0.95,
            "reasoning": "User specified product 3 name"
          }
        ]

        For "Approve" or "Everything looks good, approve" or "Confirmed" or "All correct":
        [
          {
            "correction_type": "confirm",
            "corrections": {"confirmed": true, "create_order": true},
            "affected_items": ["all"],
            "confidence": 1.0,
            "reasoning": "User confirmed all details are correct and approved order creation"
          }
        ]

        For "Reject" or "Cancel this" or "This is wrong, don't create":
        [
          {
            "correction_type": "reject",
            "corrections": {"reason": "User rejected the order"},
            "affected_items": ["all"],
            "confidence": 0.95,
            "reasoning": "User rejected the order processing"
          }
        ]

        Return empty array [] ONLY if the message is completely off-topic (e.g., just "hello", "test").
        NEVER return empty array for approval/confirmation words like "approve", "confirm", "correct", "looks good".
        """
    )

    overall_confidence = dspy.OutputField(
        desc="""Overall confidence that ALL feedback was correctly understood (0.0 to 1.0).
        Average of individual correction confidences.
        """
    )

    needs_clarification = dspy.OutputField(
        desc="""Boolean (true/false): Does ANY part of this feedback need clarification?
        Set to true if:
        - Any correction is ambiguous
        - Multiple interpretations possible
        - overall_confidence < 0.7
        """
    )

    clarification_question = dspy.OutputField(
        desc="""If needs_clarification=true, generate a helpful question.
        Examples:
        - "I understood you want to correct the company and product 1. Could you clarify which company is correct?"
        - "You mentioned product 1 and product 3. Which product codes should they be?"

        If needs_clarification=false, return empty string.
        """
    )


class TrainingExampleGenerator(dspy.Signature):
    """
    Generate DSPy training examples from user corrections

    This signature analyzes what the system got wrong and creates
    training data to improve future predictions
    """

    # Input fields
    email_text = dspy.InputField(
        desc="Original email content that was processed"
    )

    system_output = dspy.InputField(
        desc="""What the system originally extracted/predicted in JSON format:
        {
          "intent": {...},
          "entities": {...},
          "matches": {...}
        }"""
    )

    user_correction = dspy.InputField(
        desc="""User's correction (already parsed into structured format):
        {
          "correction_type": "...",
          "corrections": {...},
          "user_reasoning": "..."
        }"""
    )

    # Output fields
    dspy_signature = dspy.OutputField(
        desc="""Which DSPy signature should be trained with this example?
        Options:
        - EntityExtractor: For company name, product extraction errors
        - IntentClassifier: For intent classification errors
        - ProductConfirmer: For product matching errors
        - CompleteExtractor: For general extraction errors
        """
    )

    training_input = dspy.OutputField(
        desc="""The input that should have been provided to the DSPy signature.
        Format depends on signature type:
        - For EntityExtractor: email body + subject
        - For ProductConfirmer: email body + product candidates
        - For IntentClassifier: email subject + body
        Return as JSON string.
        """
    )

    correct_output = dspy.OutputField(
        desc="""The correct output according to user feedback.
        Format depends on signature type:
        - For EntityExtractor: corrected entities dict
        - For ProductConfirmer: corrected product matches
        - For IntentClassifier: corrected intent
        Return as JSON string.
        """
    )

    incorrect_output = dspy.OutputField(
        desc="""The incorrect output that was originally produced.
        Helps DSPy learn what NOT to predict.
        Return as JSON string.
        """
    )

    error_analysis = dspy.OutputField(
        desc="""Analyze why the system made this mistake. What pattern should it learn?
        Examples:
        - "System failed to recognize abbreviated company name (ABC vs ABC GmbH)"
        - "System confused similar product codes (9000841 vs 9000842)"
        - "System didn't extract quantity from multi-line product specification"
        - "System misidentified SDS sender as customer"

        This helps prioritize what to improve.
        """
    )

    training_weight = dspy.OutputField(
        desc="""How important is this training example? Scale 1.0 to 10.0

        High weight (8-10):
        - Critical business errors (wrong customer, wrong product)
        - User strongly emphasized the correction
        - Repeated error pattern

        Medium weight (5-7):
        - Minor mismatches
        - Edge cases
        - Ambiguous situations

        Low weight (1-4):
        - Formatting issues
        - Non-critical details
        - One-off mistakes
        """
    )

    training_priority = dspy.OutputField(
        desc="""When should this be used in training? Options:
        - immediate: Critical error, train ASAP
        - next_batch: Include in next scheduled training
        - accumulate: Wait until more examples collected
        """
    )

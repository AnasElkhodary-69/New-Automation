"""
Test Hybrid Model Strategy

Tests the Small → Medium fallback logic to verify cost savings
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv(override=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator.mistral_agent import MistralAgent

def print_separator(char="=", length=80):
    """Print separator"""
    print(char * length)


def test_hybrid_models():
    """Test hybrid model strategy"""
    print_separator()
    print("TESTING HYBRID MODEL STRATEGY (Small -> Medium)")
    print_separator()

    # Initialize Mistral Agent
    print("\n1. Initializing Mistral Agent with hybrid mode...")
    agent = MistralAgent()

    print(f"   Hybrid mode enabled: {agent.use_hybrid}")
    print(f"   Small model: {agent.small_model}")
    print(f"   Medium model: {agent.medium_model}")
    print(f"   Large model: {agent.large_model}")

    # Test 1: Intent Classification (should use Small)
    print("\n2. Testing Intent Classification...")
    print("   Expected: Should use Small model")

    test_subject = "Order Request - Products Needed"
    test_body = """
    Dear supplier,

    We would like to order the following products:
    - Doctor Blade Gold 25x0.20
    - 3M Cushion Mount E1820

    Please send us a quote.

    Best regards,
    Test Customer
    """

    result_intent = agent.classify_intent(test_subject, test_body)
    print(f"   OK Intent: {result_intent.get('type', 'unknown')}")
    print(f"   OK Confidence: {result_intent.get('confidence', 0):.0%}")

    # Test 2: Entity Extraction (should use Small first, maybe Medium on retry)
    print("\n3. Testing Entity Extraction...")
    print("   Expected: Small first, Medium if quality check fails")

    email_text = f"Subject: {test_subject}\n\n{test_body}"
    result_extraction = agent.extract_entities(email_text)

    print(f"   OK Products extracted: {len(result_extraction.get('product_names', []))}")
    print(f"   OK Products: {result_extraction.get('product_names', [])[:3]}")

    # Show model usage statistics
    print("\n4. Model Usage Statistics:")
    print_separator("-")

    stats = agent.model_usage_stats
    print(f"   Small Model:")
    print(f"      Calls: {stats['small']['calls']}")
    print(f"      Input tokens: {stats['small']['input_tokens']:,}")
    print(f"      Output tokens: {stats['small']['output_tokens']:,}")

    print(f"\n   Medium Model:")
    print(f"      Calls: {stats['medium']['calls']}")
    print(f"      Input tokens: {stats['medium']['input_tokens']:,}")
    print(f"      Output tokens: {stats['medium']['output_tokens']:,}")

    print(f"\n   Large Model:")
    print(f"      Calls: {stats['large']['calls']}")
    print(f"      Input tokens: {stats['large']['input_tokens']:,}")
    print(f"      Output tokens: {stats['large']['output_tokens']:,}")

    # Calculate costs
    print("\n5. Cost Analysis:")
    print_separator("-")

    # Small model cost
    small_cost_input = stats['small']['input_tokens'] * 0.10 / 1_000_000
    small_cost_output = stats['small']['output_tokens'] * 0.30 / 1_000_000
    small_total = small_cost_input + small_cost_output

    # Medium model cost
    medium_cost_input = stats['medium']['input_tokens'] * 0.40 / 1_000_000
    medium_cost_output = stats['medium']['output_tokens'] * 2.00 / 1_000_000
    medium_total = medium_cost_input + medium_cost_output

    # Large model cost (what we would have paid)
    total_input = stats['small']['input_tokens'] + stats['medium']['input_tokens']
    total_output = stats['small']['output_tokens'] + stats['medium']['output_tokens']

    large_would_cost_input = total_input * 2.00 / 1_000_000
    large_would_cost_output = total_output * 6.00 / 1_000_000
    large_would_cost = large_would_cost_input + large_would_cost_output

    actual_cost = small_total + medium_total

    print(f"   Small Model Cost:  ${small_total:.6f}")
    print(f"   Medium Model Cost: ${medium_total:.6f}")
    print(f"   ----------------------------------")
    print(f"   Actual Total Cost: ${actual_cost:.6f}")
    print(f"\n   If we used Large for everything:")
    print(f"   Large Model Cost:  ${large_would_cost:.6f}")
    print(f"   ----------------------------------")
    print(f"   SAVINGS: ${large_would_cost - actual_cost:.6f} ({(1 - actual_cost/large_would_cost)*100:.1f}%)")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    test_hybrid_models()

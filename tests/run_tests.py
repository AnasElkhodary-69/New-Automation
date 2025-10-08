"""
Test Runner

Simple test runner to verify all tests pass
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_unit_tests():
    """Run all unit tests"""
    print("=" * 80)
    print("RUNNING UNIT TESTS")
    print("=" * 80)

    unit_tests = [
        "test_email_connection.py",
        "test_odoo_connection.py",
        "test_extraction_parsing.py",
        "test_pdf_extraction.py",
        "test_attribute_extraction.py"
    ]

    passed = 0
    failed = 0

    for test_file in unit_tests:
        test_path = Path(__file__).parent / "unit" / test_file
        if test_path.exists():
            print(f"\n[RUN] {test_file}")
            try:
                # Run test file
                exec(open(test_path).read(), {'__name__': '__main__'})
                print(f"[PASS] {test_file}")
                passed += 1
            except Exception as e:
                print(f"[FAIL] {test_file}: {e}")
                failed += 1
        else:
            print(f"[SKIP] {test_file} (not found)")

    print("\n" + "=" * 80)
    print(f"Unit Tests: {passed} passed, {failed} failed")
    print("=" * 80)

    return passed, failed


def run_integration_tests():
    """Run integration tests"""
    print("\n" + "=" * 80)
    print("RUNNING INTEGRATION TESTS")
    print("=" * 80)

    integration_tests = [
        "test_system.py",
        "test_rag_workflow.py"
    ]

    passed = 0
    failed = 0

    for test_file in integration_tests:
        test_path = Path(__file__).parent / "integration" / test_file
        if test_path.exists():
            print(f"\n[RUN] {test_file}")
            try:
                # Run test file
                exec(open(test_path).read(), {'__name__': '__main__'})
                print(f"[PASS] {test_file}")
                passed += 1
            except Exception as e:
                print(f"[FAIL] {test_file}: {e}")
                failed += 1
        else:
            print(f"[SKIP] {test_file} (not found)")

    print("\n" + "=" * 80)
    print(f"Integration Tests: {passed} passed, {failed} failed")
    print("=" * 80)

    return passed, failed


def main():
    """Main test runner"""
    print("\n" + "=" * 80)
    print("RAG EMAIL SYSTEM - TEST SUITE")
    print("=" * 80 + "\n")

    # Run unit tests
    unit_passed, unit_failed = run_unit_tests()

    # Run integration tests
    integration_passed, integration_failed = run_integration_tests()

    # Summary
    total_passed = unit_passed + integration_passed
    total_failed = unit_failed + integration_failed
    total_tests = total_passed + total_failed

    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")

    if total_failed == 0:
        print("\n✓ ALL TESTS PASSED!")
    else:
        print(f"\n✗ {total_failed} TEST(S) FAILED")

    print("=" * 80 + "\n")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

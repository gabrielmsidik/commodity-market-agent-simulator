"""Run a single test from test_matching_algorithm.py"""

from test_matching_algorithm import TestMatchingAlgorithm

if __name__ == "__main__":
    print("=" * 80)
    print("Running: test_matching_algorithm_with_mix")
    print("=" * 80)
    print()
    
    test_suite = TestMatchingAlgorithm()
    
    try:
        test_suite.test_matching_algorithm_with_mix()
        print()
        print("✅ Test passed!")
    except AssertionError as e:
        print()
        print(f"❌ Test failed: {e}")
    except Exception as e:
        print()
        print(f"❌ Test error: {e}")


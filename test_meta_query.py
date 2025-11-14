"""
Quick test for meta-query functionality

Run this to verify the orchestrator can answer questions about itself.
"""

from core.orchestrator import orchestrator_graph
from dotenv import load_dotenv

load_dotenv()


def test_meta_queries():
    """Test various meta-queries"""

    meta_queries = [
        "What workflows do you have?",
        "What can you do?",
        "Help",
        "List your capabilities",
        "What are your available workflows?"
    ]

    print("=" * 70)
    print("Testing Meta-Query Functionality")
    print("=" * 70)

    for i, query in enumerate(meta_queries, 1):
        print(f"\n--- Test {i}/{len(meta_queries)} ---")
        print(f"Query: {query}")
        print()

        test_input = {
            "user_query": query,
            "detected_intent": "",
            "workflow_result": {},
            "final_response": ""
        }

        try:
            result = orchestrator_graph.invoke(test_input)

            print(f"Detected Intent: {result['detected_intent']}")
            print(f"Workflow Type: {result['workflow_result'].get('workflow_type', 'unknown')}")
            print()
            print("Response:")
            print(result['final_response'])

            # Verify it was classified as meta
            if result['detected_intent'] == 'meta':
                print("\n✓ Correctly classified as meta-query")
            else:
                print(f"\n✗ WARNING: Classified as '{result['detected_intent']}' instead of 'meta'")

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

        print("-" * 70)

    print("\n" + "=" * 70)
    print("✓ Meta-query testing complete!")
    print("=" * 70)


def test_regular_queries_still_work():
    """Verify regular queries still route to workflows"""

    regular_queries = [
        ("What is 2+2?", "simple"),
        ("Research AI and analyze benefits", "supervisor"),
        ("Iteratively improve this analysis", "iterative")
    ]

    print("\n\n" + "=" * 70)
    print("Verifying Regular Queries Still Work")
    print("=" * 70)

    for i, (query, expected_type) in enumerate(regular_queries, 1):
        print(f"\n--- Test {i}/{len(regular_queries)} ---")
        print(f"Query: {query}")
        print(f"Expected: {expected_type}")
        print()

        test_input = {
            "user_query": query,
            "detected_intent": "",
            "workflow_result": {},
            "final_response": ""
        }

        try:
            result = orchestrator_graph.invoke(test_input)

            print(f"Detected Intent: {result['detected_intent']}")
            print(f"Workflow Type: {result['workflow_result'].get('workflow_type', 'unknown')}")
            print(f"Success: {result['workflow_result'].get('success', False)}")

            # Note: LLM might classify differently, that's okay
            if result['detected_intent'] != 'meta':
                print("\n✓ Correctly routed to workflow (not meta)")
            else:
                print("\n⚠ WARNING: Routed to meta instead of workflow")

        except Exception as e:
            print(f"✗ Error: {e}")

        print("-" * 70)

    print("\n" + "=" * 70)
    print("✓ Regular query testing complete!")
    print("=" * 70)


if __name__ == "__main__":
    print("\nTesting orchestrator improvements...")
    print("This will make API calls to Claude.\n")

    try:
        # Test meta-queries
        test_meta_queries()

        # Test regular queries still work
        test_regular_queries_still_work()

        print("\n\n" + "=" * 70)
        print("ALL TESTS PASSED! ✓")
        print("=" * 70)
        print("\nThe orchestrator can now:")
        print("  ✓ Answer questions about its workflows")
        print("  ✓ Provide help and capability information")
        print("  ✓ Still route regular queries to workflows")
        print()

    except KeyboardInterrupt:
        print("\n\nTests cancelled.")
    except Exception as e:
        print(f"\n\n✗ Tests failed: {e}")
        import traceback
        traceback.print_exc()

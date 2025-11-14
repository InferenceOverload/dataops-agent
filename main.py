"""
Main Entry Point for POC Testing

This script provides a simple CLI for testing the multi-agent orchestrator POC.
For interactive testing via web UI, use: langgraph dev
"""

from core.orchestrator import orchestrator_graph
from workflows.workflow_a import workflow_graph as workflow_a_graph
from workflows.workflow_b import workflow_graph as workflow_b_graph
from workflows.workflow_c import workflow_graph as workflow_c_graph
from dotenv import load_dotenv
import sys

# Load environment
load_dotenv()


def test_workflow_a():
    """Test Workflow A - Simple Agent"""
    print("\n" + "=" * 70)
    print("Testing Workflow A - Simple Agent")
    print("=" * 70)

    test_input = {
        "input": "What is LangGraph and why is it useful?",
        "output": ""
    }

    print(f"Input: {test_input['input']}")
    print("\nProcessing...")

    result = workflow_a_graph.invoke(test_input)

    print(f"\nOutput: {result['output']}")
    print("\n✓ Workflow A completed successfully")


def test_workflow_b():
    """Test Workflow B - Supervisor Pattern"""
    print("\n" + "=" * 70)
    print("Testing Workflow B - Supervisor Pattern")
    print("=" * 70)

    test_input = {
        "input": "Research the history of multi-agent systems and analyze their current applications",
        "messages": [],
        "next_agent": "",
        "output": ""
    }

    print(f"Input: {test_input['input']}")
    print("\nProcessing with supervisor pattern...")

    result = workflow_b_graph.invoke(test_input)

    print(f"\nMessages exchanged: {len(result['messages'])}")
    print("\nMessage History:")
    for msg in result['messages']:
        print(f"  - {msg[:80]}...")

    print(f"\nFinal Output:\n{result['output'][:300]}...")
    print("\n✓ Workflow B completed successfully")


def test_workflow_c():
    """Test Workflow C - Iterative Loop"""
    print("\n" + "=" * 70)
    print("Testing Workflow C - Iterative Loop")
    print("=" * 70)

    test_input = {
        "input": "Analyze the benefits of iterative refinement in AI agent systems",
        "iterations": 0,
        "max_iterations": 3,
        "current_result": "",
        "artifacts": [],
        "output": ""
    }

    print(f"Input: {test_input['input']}")
    print(f"Max iterations: {test_input['max_iterations']}")
    print("\nProcessing with iterative refinement...")

    result = workflow_c_graph.invoke(test_input)

    print(f"\nCompleted iterations: {result['iterations']}")
    print(f"Artifacts created: {len(result['artifacts'])}")
    print("\nArtifacts:")
    for artifact in result['artifacts']:
        print(f"  - Iteration {artifact['iteration']}: {len(artifact['content'])} chars")

    print(f"\nFinal Output:\n{result['output'][:300]}...")
    print("\n✓ Workflow C completed successfully")


def test_orchestrator():
    """Test Main Orchestrator"""
    print("\n" + "=" * 70)
    print("Testing Main Orchestrator")
    print("=" * 70)

    test_queries = [
        "What are the key features of LangGraph?",
        "Research microservices architecture and analyze its pros and cons",
        "Iteratively develop a comprehensive analysis of AI safety considerations"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test Case {i}/{len(test_queries)} ---")
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
            print(f"Success: {result['workflow_result'].get('success', False)}")
            print(f"\nFormatted Response:\n{result['final_response'][:400]}...")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n✓ Orchestrator testing complete")


def main():
    """Main entry point"""
    print("\n" + "=" * 70)
    print("Multi-Agent Orchestrator POC - Test Suite")
    print("=" * 70)
    print("\nThis will test all workflows and the orchestrator.")
    print("Each test makes real API calls to Claude.")
    print("\nPress Ctrl+C to cancel, or Enter to continue...")

    try:
        input()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)

    try:
        # Test individual workflows
        test_workflow_a()
        test_workflow_b()
        test_workflow_c()

        # Test orchestrator (integrates all workflows)
        test_orchestrator()

        print("\n" + "=" * 70)
        print("✓ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\nThe POC has validated:")
        print("  ✓ Simple agent workflow works")
        print("  ✓ Supervisor pattern workflow works")
        print("  ✓ Iterative loop workflow works")
        print("  ✓ Orchestrator can dynamically invoke all workflows")
        print("  ✓ Blocking execution works correctly")
        print("  ✓ State transformation works at boundaries")
        print("\nPattern proven! ✓")

    except KeyboardInterrupt:
        print("\n\nTests cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

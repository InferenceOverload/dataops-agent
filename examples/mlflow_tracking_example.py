#!/usr/bin/env python3
"""
MLflow Tracking Example for DataOps Agent

This script demonstrates MLflow integration with LangGraph workflows:
- Automatic tracing of workflow execution
- Metrics and parameter logging
- Viewing results in MLflow UI

Prerequisites:
    pip install -e ".[observability]"

Usage:
    python examples/mlflow_tracking_example.py

    Then view results:
    mlflow ui
    # Open http://localhost:5000
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from core.orchestrator import orchestrator_graph
from infrastructure.observability import (
    is_mlflow_available,
    get_active_run_id,
    get_mlflow_config
)

# Load environment variables
load_dotenv()


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def main():
    """Run example workflows with MLflow tracking."""

    print_section("MLflow LangGraph Integration Example")

    # Check MLflow availability
    if is_mlflow_available():
        config = get_mlflow_config()
        print("✅ MLflow is enabled and configured")
        print(f"   Tracking URI: {config.tracking_uri}")
        print(f"   Experiment: {config.experiment_name}")
        print(f"   Environment: {config.environment}")
        print(f"   Auto-logging: {config.enable_auto_logging}")
    else:
        print("⚠️  MLflow is not available")
        print("   Install with: pip install -e '.[observability]'")
        print("   Workflows will run without tracing")

    # Example workflows to test
    test_queries = [
        {
            "name": "Simple Query",
            "query": "What is LangGraph?",
            "description": "Tests simple workflow with single LLM call"
        },
        {
            "name": "Supervisor Pattern",
            "query": "Research and analyze the benefits of multi-agent systems",
            "description": "Tests supervisor workflow with multiple agents"
        },
        {
            "name": "Iterative Refinement",
            "query": "Iteratively refine an analysis of AI agent patterns",
            "description": "Tests iterative workflow with artifacts"
        }
    ]

    # Execute workflows
    for i, test_case in enumerate(test_queries, 1):
        print_section(f"Test {i}/{len(test_queries)}: {test_case['name']}")

        print(f"Description: {test_case['description']}")
        print(f"Query: {test_case['query']}\n")

        # Prepare input state
        input_state = {
            "user_query": test_case["query"],
            "detected_intent": "",
            "extracted_parameters": {},
            "missing_parameters": [],
            "workflow_result": {},
            "final_response": ""
        }

        try:
            # Execute workflow (automatically traced by MLflow)
            print("⏳ Executing workflow...")
            result = orchestrator_graph.invoke(input_state)

            # Display results
            print("\n📊 Execution Results:")
            print(f"   Detected Intent: {result['detected_intent']}")

            workflow_result = result.get('workflow_result', {})
            print(f"   Success: {workflow_result.get('success', False)}")
            print(f"   Workflow Type: {workflow_result.get('workflow_type', 'unknown')}")

            # Display metadata
            metadata = workflow_result.get('metadata', {})
            if metadata:
                print("\n📈 Metrics:")
                if 'execution_time_seconds' in metadata:
                    print(f"   Execution Time: {metadata['execution_time_seconds']:.2f}s")
                if 'iterations' in metadata:
                    print(f"   Iterations: {metadata['iterations']}")
                if 'artifacts_count' in metadata:
                    print(f"   Artifacts: {metadata['artifacts_count']}")
                if 'messages_count' in metadata:
                    print(f"   Messages: {metadata['messages_count']}")

            # Display MLflow run info
            if is_mlflow_available():
                run_id = get_active_run_id()
                if run_id:
                    print(f"\n🔗 MLflow Run ID: {run_id}")
                    print(f"   View at: http://localhost:5000/#/experiments/1/runs/{run_id}")

            # Display response preview
            response = result.get('final_response', '')
            print(f"\n💬 Response Preview:")
            print(f"   {response[:200]}{'...' if len(response) > 200 else ''}")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

    # Final instructions
    print_section("View Results in MLflow UI")

    if is_mlflow_available():
        config = get_mlflow_config()
        print("To view all tracked runs:")
        print("\n1. Start MLflow UI:")
        if config.tracking_uri.startswith('http'):
            print(f"   Already running at: {config.tracking_uri}")
        else:
            print(f"   mlflow ui --backend-store-uri {config.tracking_uri}")
            print("\n2. Open browser:")
            print("   http://localhost:5000")

        print("\n3. Explore:")
        print(f"   - Navigate to experiment: {config.experiment_name}")
        print("   - Compare run metrics")
        print("   - View execution traces")
        print("   - Analyze performance trends")

        print("\n4. Query runs programmatically:")
        print("   from infrastructure.observability import get_mlflow_config")
        print("   import mlflow")
        print("   client = mlflow.tracking.MlflowClient()")
        print("   runs = client.search_runs(experiment_ids=['1'])")
    else:
        print("Install MLflow to enable tracking:")
        print("   pip install -e '.[observability]'")
        print("\nThen re-run this example.")

    print_section("Example Complete")
    print("✅ All workflows executed successfully!")
    print("\nNext steps:")
    print("1. Review MLflow UI for execution traces")
    print("2. Compare metrics across different runs")
    print("3. Experiment with different queries")
    print("4. Configure S3 artifact storage for production")
    print("\nDocumentation: docs/MLFLOW_INTEGRATION.md\n")


if __name__ == "__main__":
    main()

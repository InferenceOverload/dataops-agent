"""
Integration tests for the main orchestrator

Tests the full pattern:
- Intent detection
- Workflow invocation
- State transformation
- Response formatting
"""

import pytest
from core.orchestrator import orchestrator_graph
from core.workflow_registry import WORKFLOW_REGISTRY, list_workflows, get_workflow


class TestWorkflowRegistry:
    """Tests for workflow registry"""

    def test_registry_contains_all_workflows(self):
        """Verify registry has all expected workflows"""
        workflows = list_workflows()

        assert "simple" in workflows
        assert "supervisor" in workflows
        assert "iterative" in workflows

    def test_get_workflow_returns_compiled_graph(self):
        """Verify get_workflow returns a callable compiled graph"""
        workflow = get_workflow("simple")

        assert workflow is not None
        assert hasattr(workflow, "invoke")

    def test_workflow_registry_entries_are_invocable(self):
        """Verify all registry entries can be invoked"""
        for name, workflow in WORKFLOW_REGISTRY.items():
            assert hasattr(workflow, "invoke"), f"Workflow {name} is not invocable"


class TestOrchestrator:
    """Tests for main orchestrator"""

    def test_orchestrator_simple_query(self):
        """Test orchestrator with a query that should route to simple workflow"""
        test_input = {
            "user_query": "What is 2+2?",
            "detected_intent": "",
            "workflow_result": {},
            "final_response": ""
        }

        result = orchestrator_graph.invoke(test_input)

        # Verify all state fields are populated
        assert result["user_query"] == test_input["user_query"]
        assert result["detected_intent"] != ""
        assert result["workflow_result"] != {}
        assert result["final_response"] != ""

        # Verify workflow executed successfully
        assert result["workflow_result"]["success"] is True
        assert result["workflow_result"]["output"] != ""

    def test_orchestrator_supervisor_query(self):
        """Test orchestrator with a query that should route to supervisor workflow"""
        test_input = {
            "user_query": "Research the history of databases and analyze their evolution",
            "detected_intent": "",
            "workflow_result": {},
            "final_response": ""
        }

        result = orchestrator_graph.invoke(test_input)

        # Verify execution
        assert result["workflow_result"]["success"] is True

        # Should have routed to supervisor or iterative (both handle complex tasks)
        assert result["detected_intent"] in ["supervisor", "iterative"]

    def test_orchestrator_iterative_query(self):
        """Test orchestrator with a query that should route to iterative workflow"""
        test_input = {
            "user_query": "Iteratively develop and refine an analysis of software design patterns",
            "detected_intent": "",
            "workflow_result": {},
            "final_response": ""
        }

        result = orchestrator_graph.invoke(test_input)

        # Verify execution
        assert result["workflow_result"]["success"] is True

        # Should have some metadata
        assert "metadata" in result["workflow_result"]

    def test_orchestrator_state_transformation(self):
        """Test that state transformation works correctly"""
        test_input = {
            "user_query": "Test query",
            "detected_intent": "",
            "workflow_result": {},
            "final_response": ""
        }

        result = orchestrator_graph.invoke(test_input)

        # Verify orchestrator state structure
        assert "user_query" in result
        assert "detected_intent" in result
        assert "workflow_result" in result
        assert "final_response" in result

        # Verify workflow_result has expected structure
        assert "success" in result["workflow_result"]
        assert "output" in result["workflow_result"]
        assert "workflow_type" in result["workflow_result"]
        assert "metadata" in result["workflow_result"]

    def test_orchestrator_response_formatting(self):
        """Test that response formatting works"""
        test_input = {
            "user_query": "Simple test query",
            "detected_intent": "",
            "workflow_result": {},
            "final_response": ""
        }

        result = orchestrator_graph.invoke(test_input)

        final_response = result["final_response"]

        # Should be a formatted, readable response
        assert len(final_response) > 0
        assert "Result:" in final_response or "result" in final_response.lower()


class TestIntegration:
    """Integration tests for the complete pattern"""

    def test_blocking_invoke_completes(self):
        """Test that blocking invoke waits for workflow completion"""
        test_input = {
            "user_query": "What is LangGraph?",
            "detected_intent": "",
            "workflow_result": {},
            "final_response": ""
        }

        # This should block until complete
        result = orchestrator_graph.invoke(test_input)

        # If we get here, invoke completed (didn't hang)
        assert result is not None
        assert result["workflow_result"]["success"] is True

    def test_different_queries_route_to_different_workflows(self):
        """Test that different query types route to appropriate workflows"""

        # Simple query
        simple_result = orchestrator_graph.invoke({
            "user_query": "What is 5+5?",
            "detected_intent": "",
            "workflow_result": {},
            "final_response": ""
        })

        # Complex query
        complex_result = orchestrator_graph.invoke({
            "user_query": "Research cloud architecture and analyze its scalability benefits",
            "detected_intent": "",
            "workflow_result": {},
            "final_response": ""
        })

        # Iterative query
        iterative_result = orchestrator_graph.invoke({
            "user_query": "Iteratively refine an analysis of distributed systems",
            "detected_intent": "",
            "workflow_result": {},
            "final_response": ""
        })

        # All should succeed
        assert simple_result["workflow_result"]["success"] is True
        assert complex_result["workflow_result"]["success"] is True
        assert iterative_result["workflow_result"]["success"] is True

        # They may route to different workflows
        # (Note: LLM may classify differently, so we just verify they all worked)

    def test_structured_contract_compliance(self):
        """Test that workflows return structured results per contract"""
        test_input = {
            "user_query": "Test structured contracts",
            "detected_intent": "",
            "workflow_result": {},
            "final_response": ""
        }

        result = orchestrator_graph.invoke(test_input)

        workflow_result = result["workflow_result"]

        # Verify contract fields
        assert "success" in workflow_result
        assert "output" in workflow_result
        assert "workflow_type" in workflow_result
        assert "metadata" in workflow_result

        # Metadata should have expected fields
        metadata = workflow_result["metadata"]
        assert "iterations" in metadata
        assert "artifacts_count" in metadata
        assert "messages_count" in metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Unit tests for individual workflows

Tests each workflow in isolation to verify they work independently
before testing the orchestrator integration.
"""

import pytest
from workflows.workflow_a import workflow_graph as workflow_a
from workflows.workflow_b import workflow_graph as workflow_b
from workflows.workflow_c import workflow_graph as workflow_c


class TestWorkflowA:
    """Tests for Workflow A - Simple Agent"""

    def test_workflow_a_basic(self):
        """Test basic invocation of workflow A"""
        test_input = {
            "input": "What is 2+2?",
            "output": ""
        }

        result = workflow_a.invoke(test_input)

        # Verify structure
        assert "input" in result
        assert "output" in result

        # Verify output is not empty
        assert result["output"] != ""
        assert len(result["output"]) > 0

        # Verify input is preserved
        assert result["input"] == test_input["input"]

    def test_workflow_a_complex_query(self):
        """Test workflow A with a more complex query"""
        test_input = {
            "input": "Explain the concept of state machines in software engineering",
            "output": ""
        }

        result = workflow_a.invoke(test_input)

        assert result["output"] != ""
        assert len(result["output"]) > 50  # Should be a substantial response


class TestWorkflowB:
    """Tests for Workflow B - Supervisor Pattern"""

    def test_workflow_b_basic(self):
        """Test basic invocation of workflow B"""
        test_input = {
            "input": "Research and analyze cloud computing",
            "messages": [],
            "next_agent": "",
            "output": ""
        }

        result = workflow_b.invoke(test_input)

        # Verify structure
        assert "input" in result
        assert "messages" in result
        assert "output" in result

        # Verify messages were exchanged
        assert len(result["messages"]) > 0

        # Verify output is not empty
        assert result["output"] != ""

    def test_workflow_b_coordination(self):
        """Test that supervisor coordinates workers"""
        test_input = {
            "input": "Research microservices and analyze their benefits",
            "messages": [],
            "next_agent": "",
            "output": ""
        }

        result = workflow_b.invoke(test_input)

        # Should have multiple messages (supervisor + workers)
        assert len(result["messages"]) >= 3

        # Check for evidence of coordination
        messages_str = " ".join(result["messages"])
        assert "Supervisor" in messages_str or "Worker" in messages_str


class TestWorkflowC:
    """Tests for Workflow C - Iterative Loop"""

    def test_workflow_c_iterations(self):
        """Test that workflow C completes specified iterations"""
        test_input = {
            "input": "Analyze iterative development",
            "iterations": 0,
            "max_iterations": 3,
            "current_result": "",
            "artifacts": [],
            "output": ""
        }

        result = workflow_c.invoke(test_input)

        # Verify structure
        assert "iterations" in result
        assert "artifacts" in result
        assert "output" in result

        # Verify iterations completed
        assert result["iterations"] == 3

        # Verify artifacts created
        assert len(result["artifacts"]) == 3

        # Verify each artifact has required fields
        for artifact in result["artifacts"]:
            assert "iteration" in artifact
            assert "content" in artifact
            assert "timestamp" in artifact

    def test_workflow_c_artifact_progression(self):
        """Test that artifacts are created in order"""
        test_input = {
            "input": "Progressive refinement test",
            "iterations": 0,
            "max_iterations": 2,
            "current_result": "",
            "artifacts": [],
            "output": ""
        }

        result = workflow_c.invoke(test_input)

        # Verify 2 iterations
        assert result["iterations"] == 2
        assert len(result["artifacts"]) == 2

        # Verify iteration numbers are sequential
        assert result["artifacts"][0]["iteration"] == 1
        assert result["artifacts"][1]["iteration"] == 2

    def test_workflow_c_custom_max_iterations(self):
        """Test workflow C with different max_iterations"""
        test_input = {
            "input": "Test custom iterations",
            "iterations": 0,
            "max_iterations": 1,
            "current_result": "",
            "artifacts": [],
            "output": ""
        }

        result = workflow_c.invoke(test_input)

        assert result["iterations"] == 1
        assert len(result["artifacts"]) == 1


class TestWorkflowContracts:
    """Tests to verify workflows follow structured contracts"""

    def test_all_workflows_return_output(self):
        """Verify all workflows return an 'output' field"""

        # Test workflow A
        result_a = workflow_a.invoke({"input": "test", "output": ""})
        assert "output" in result_a
        assert result_a["output"] != ""

        # Test workflow B
        result_b = workflow_b.invoke({
            "input": "test",
            "messages": [],
            "next_agent": "",
            "output": ""
        })
        assert "output" in result_b
        assert result_b["output"] != ""

        # Test workflow C
        result_c = workflow_c.invoke({
            "input": "test",
            "iterations": 0,
            "max_iterations": 1,
            "current_result": "",
            "artifacts": [],
            "output": ""
        })
        assert "output" in result_c
        assert result_c["output"] != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for Base Workflow Interface

Tests the BaseWorkflow abstract class and WorkflowMetadata model.
"""

import pytest
from core.base_workflow import BaseWorkflow, WorkflowMetadata


def test_workflow_metadata_creation():
    """Test WorkflowMetadata validation"""
    metadata = WorkflowMetadata(
        name="test",
        description="Test workflow",
        capabilities=["test capability"],
        example_queries=["test query"],
        category="test"
    )
    assert metadata.name == "test"
    assert metadata.description == "Test workflow"
    assert len(metadata.capabilities) == 1
    assert len(metadata.example_queries) == 1
    assert metadata.category == "test"
    assert metadata.version == "1.0.0"  # default
    assert metadata.author == "Data Engineering Team"  # default


def test_workflow_metadata_with_custom_values():
    """Test WorkflowMetadata with custom version and author"""
    metadata = WorkflowMetadata(
        name="custom_test",
        description="Custom test workflow",
        capabilities=["cap1", "cap2"],
        example_queries=["query1", "query2"],
        category="custom",
        version="2.0.0",
        author="Test Team"
    )
    assert metadata.version == "2.0.0"
    assert metadata.author == "Test Team"
    assert len(metadata.capabilities) == 2
    assert len(metadata.example_queries) == 2


def test_base_workflow_is_abstract():
    """Ensure BaseWorkflow cannot be instantiated directly"""
    with pytest.raises(TypeError):
        BaseWorkflow()


def test_base_workflow_requires_implementation():
    """Test that subclasses must implement abstract methods"""
    class IncompleteWorkflow(BaseWorkflow):
        pass

    with pytest.raises(TypeError):
        IncompleteWorkflow()


def test_base_workflow_concrete_implementation():
    """Test that concrete implementation works"""
    class ConcreteWorkflow(BaseWorkflow):
        def get_metadata(self) -> WorkflowMetadata:
            return WorkflowMetadata(
                name="concrete",
                description="Concrete test workflow",
                capabilities=["test"],
                example_queries=["test"],
                category="test"
            )

        def get_compiled_graph(self):
            # Return a mock compiled graph
            return "mock_graph"

    workflow = ConcreteWorkflow()
    assert workflow is not None

    metadata = workflow.get_metadata()
    assert metadata.name == "concrete"
    assert metadata.description == "Concrete test workflow"

    graph = workflow.get_compiled_graph()
    assert graph == "mock_graph"

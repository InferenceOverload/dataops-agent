"""
Tests for Enhanced WorkflowRegistry

Tests auto-discovery and capability context generation.
"""

import pytest
from core.workflow_registry import WorkflowRegistry


def test_registry_discovers_workflows():
    """Test auto-discovery of workflows"""
    registry = WorkflowRegistry()
    workflows = registry.discover_workflows()

    assert len(workflows) > 0, "Registry should discover at least one workflow"


def test_registry_lists_all_workflows():
    """Test listing all registered workflow names"""
    registry = WorkflowRegistry()
    registry.discover_workflows()

    workflow_names = registry.list_workflows()

    assert isinstance(workflow_names, list)
    assert len(workflow_names) > 0

    # Expected workflows
    expected_workflows = ["simple", "supervisor", "iterative", "jil_parser"]
    for expected in expected_workflows:
        assert expected in workflow_names, f"Expected workflow '{expected}' not found"


def test_registry_get_workflow():
    """Test getting compiled workflow graph"""
    registry = WorkflowRegistry()
    registry.discover_workflows()

    # Get a known workflow
    simple_workflow = registry.get_workflow("simple")

    assert simple_workflow is not None
    # Check if it's a compiled graph (has invoke method)
    assert hasattr(simple_workflow, 'invoke')


def test_registry_get_metadata():
    """Test getting workflow metadata"""
    registry = WorkflowRegistry()
    registry.discover_workflows()

    # Get metadata for known workflow
    metadata = registry.get_metadata("simple")

    assert metadata is not None
    assert metadata.name == "simple"
    assert metadata.description
    assert len(metadata.capabilities) > 0
    assert len(metadata.example_queries) > 0
    assert metadata.category
    assert metadata.version


def test_registry_capabilities_context():
    """Test capability context generation for LLM"""
    registry = WorkflowRegistry()
    registry.discover_workflows()

    context = registry.get_capabilities_context()

    assert isinstance(context, str)
    assert len(context) > 0

    # Should contain workflow information
    assert "Workflow:" in context
    assert "Description:" in context
    assert "Capabilities:" in context
    assert "Example Queries:" in context

    # Should include known workflows
    assert "jil_parser" in context
    assert "simple" in context


def test_registry_user_capabilities():
    """Test user-facing capability list"""
    registry = WorkflowRegistry()
    registry.discover_workflows()

    user_text = registry.get_capabilities_for_user()

    assert isinstance(user_text, str)
    assert len(user_text) > 0

    # Should be user-friendly
    assert "help you" in user_text.lower()

    # Should include workflow descriptions
    for name in registry.list_workflows():
        metadata = registry.get_metadata(name)
        if metadata:
            assert metadata.description in user_text


def test_registry_get_nonexistent_workflow():
    """Test getting a workflow that doesn't exist"""
    registry = WorkflowRegistry()
    registry.discover_workflows()

    workflow = registry.get_workflow("nonexistent_workflow")
    assert workflow is None

    metadata = registry.get_metadata("nonexistent_workflow")
    assert metadata is None


def test_all_workflows_have_complete_metadata():
    """Test that all discovered workflows have complete metadata"""
    registry = WorkflowRegistry()
    registry.discover_workflows()

    for name in registry.list_workflows():
        metadata = registry.get_metadata(name)

        assert metadata is not None, f"Workflow {name} has no metadata"
        assert metadata.name, f"Workflow {name} has no name in metadata"
        assert metadata.description, f"Workflow {name} has no description"
        assert len(metadata.capabilities) > 0, f"Workflow {name} has no capabilities"
        assert len(metadata.example_queries) > 0, f"Workflow {name} has no example queries"
        assert metadata.category, f"Workflow {name} has no category"


def test_all_workflows_have_compiled_graphs():
    """Test that all discovered workflows have valid compiled graphs"""
    registry = WorkflowRegistry()
    registry.discover_workflows()

    for name in registry.list_workflows():
        workflow = registry.get_workflow(name)

        assert workflow is not None, f"Workflow {name} has no compiled graph"
        assert hasattr(workflow, 'invoke'), f"Workflow {name} graph is not compiled (no invoke method)"


def test_workflow_categories():
    """Test that workflows have expected categories"""
    registry = WorkflowRegistry()
    registry.discover_workflows()

    expected_categories = {
        "simple": "general",
        "supervisor": "analysis",
        "iterative": "analysis",
        "jil_parser": "migration"
    }

    for name, expected_category in expected_categories.items():
        metadata = registry.get_metadata(name)
        assert metadata is not None, f"Workflow {name} not found"
        assert metadata.category == expected_category, \
            f"Workflow {name} has category '{metadata.category}', expected '{expected_category}'"

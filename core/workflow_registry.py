"""
Workflow Registry

Simple dict-based registry for storing compiled workflows.
Maps workflow names to compiled LangGraph objects.
"""

from workflows import workflow_a, workflow_b, workflow_c

# Registry of compiled workflows
# Each value is a compiled LangGraph that can be invoked
WORKFLOW_REGISTRY = {
    "simple": workflow_a.workflow_graph,      # Simple agent workflow
    "supervisor": workflow_b.workflow_graph,  # Supervisor pattern workflow
    "iterative": workflow_c.workflow_graph    # Iterative loop workflow
}


def get_workflow(workflow_name: str):
    """
    Get a workflow from the registry.

    Args:
        workflow_name: Name of the workflow to retrieve

    Returns:
        Compiled LangGraph workflow, or None if not found

    Example:
        >>> workflow = get_workflow("simple")
        >>> result = workflow.invoke({"input": "test"})
    """
    return WORKFLOW_REGISTRY.get(workflow_name)


def list_workflows() -> list[str]:
    """
    List all available workflow names.

    Returns:
        List of workflow names
    """
    return list(WORKFLOW_REGISTRY.keys())


def get_workflow_description(workflow_name: str) -> str:
    """
    Get a human-readable description of a workflow.

    Args:
        workflow_name: Name of the workflow

    Returns:
        Description string
    """
    descriptions = {
        "simple": "Simple single-agent workflow for basic queries",
        "supervisor": "Multi-agent supervisor pattern for complex tasks requiring coordination",
        "iterative": "Iterative refinement workflow that loops to improve results"
    }
    return descriptions.get(workflow_name, "Unknown workflow")

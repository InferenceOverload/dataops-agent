"""
Workflow Registry

Auto-discovers and registers workflows from the workflows/ directory.

Discovery Process:
1. Scan workflows/ directory
2. Import each workflow module
3. Find classes inheriting BaseWorkflow
4. Call get_metadata() and get_compiled_graph()
5. Store in registry with metadata
"""

import importlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from core.base_workflow import BaseWorkflow, WorkflowMetadata


class WorkflowRegistry:
    """
    Auto-discovers and registers workflows.

    Scans the workflows directory and automatically registers all workflows
    that implement the BaseWorkflow interface.
    """

    def __init__(self, workflows_dir: str = "workflows"):
        """
        Initialize workflow registry.

        Args:
            workflows_dir: Directory containing workflows (default: "workflows")
        """
        self.workflows_dir = workflows_dir
        self.workflows: Dict[str, Any] = {}  # name -> compiled graph
        self.metadata: Dict[str, WorkflowMetadata] = {}  # name -> metadata

    def discover_workflows(self) -> Dict[str, Any]:
        """
        Scan workflows directory and register all workflows.

        Steps:
        1. Find all directories in workflows/
        2. Look for workflow.py in each
        3. Import and find BaseWorkflow subclasses
        4. Instantiate and register
        5. Handle errors gracefully

        Returns:
            Dict of workflow name -> compiled graph
        """
        workflows_path = Path(self.workflows_dir)

        # Check if directory exists
        if not workflows_path.exists():
            print(f"⚠ Workflows directory not found: {workflows_path}")
            return self.workflows

        for workflow_dir in workflows_path.iterdir():
            # Skip non-directories
            if not workflow_dir.is_dir():
                continue

            # Skip __pycache__ and hidden directories
            if workflow_dir.name.startswith('_') or workflow_dir.name.startswith('.'):
                continue

            workflow_file = workflow_dir / "workflow.py"
            if not workflow_file.exists():
                # Try loading from direct .py files (like workflow_a.py)
                continue

            try:
                # Import module dynamically
                module_name = f"{self.workflows_dir}.{workflow_dir.name}.workflow"
                module = importlib.import_module(module_name)

                # Find BaseWorkflow subclasses
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, BaseWorkflow) and
                        attr is not BaseWorkflow):

                        # Instantiate workflow
                        workflow_instance = attr()

                        # Get metadata and graph
                        metadata = workflow_instance.get_metadata()
                        compiled_graph = workflow_instance.get_compiled_graph()

                        # Register
                        self.workflows[metadata.name] = compiled_graph
                        self.metadata[metadata.name] = metadata

                        print(f"✓ Registered workflow: {metadata.name}")

            except Exception as e:
                print(f"✗ Failed to load workflow from {workflow_dir}: {e}")

        # Also try to discover workflows from direct .py files (workflow_a.py, etc.)
        self._discover_legacy_workflows(workflows_path)

        return self.workflows

    def _discover_legacy_workflows(self, workflows_path: Path):
        """
        Discover legacy workflows (workflow_a.py, workflow_b.py style).

        Args:
            workflows_path: Path to workflows directory
        """
        for workflow_file in workflows_path.glob("workflow_*.py"):
            if workflow_file.name.startswith('_'):
                continue

            try:
                # Extract module name (e.g., workflow_a from workflow_a.py)
                module_name = f"{self.workflows_dir}.{workflow_file.stem}"
                module = importlib.import_module(module_name)

                # Find BaseWorkflow subclasses
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, BaseWorkflow) and
                        attr is not BaseWorkflow):

                        # Instantiate workflow
                        workflow_instance = attr()

                        # Get metadata and graph
                        metadata = workflow_instance.get_metadata()
                        compiled_graph = workflow_instance.get_compiled_graph()

                        # Register
                        self.workflows[metadata.name] = compiled_graph
                        self.metadata[metadata.name] = metadata

                        print(f"✓ Registered workflow: {metadata.name}")

            except Exception as e:
                print(f"✗ Failed to load workflow from {workflow_file}: {e}")

    def get_workflow(self, name: str):
        """
        Get compiled workflow graph by name.

        Args:
            name: Workflow name

        Returns:
            Compiled LangGraph or None if not found
        """
        return self.workflows.get(name)

    def get_metadata(self, name: str) -> Optional[WorkflowMetadata]:
        """
        Get workflow metadata by name.

        Args:
            name: Workflow name

        Returns:
            WorkflowMetadata or None if not found
        """
        return self.metadata.get(name)

    def list_workflows(self) -> List[str]:
        """
        List all registered workflow names.

        Returns:
            List of workflow names
        """
        return list(self.workflows.keys())

    def get_capabilities_context(self) -> str:
        """
        Generate capability description for LLM context.

        Used by orchestrator for intent detection.

        Returns:
            Formatted string describing all workflow capabilities
        """
        context_parts = []

        for name, metadata in self.metadata.items():
            context_parts.append(f"""
Workflow: {metadata.name}
Description: {metadata.description}
Category: {metadata.category}
Capabilities:
{chr(10).join(f'  - {cap}' for cap in metadata.capabilities)}
Example Queries:
{chr(10).join(f'  - "{ex}"' for ex in metadata.example_queries)}
""")

        return "\n".join(context_parts)

    def get_capabilities_for_user(self) -> str:
        """
        Generate user-facing capability list.

        Used when user asks "What can you do?"

        Returns:
            User-friendly formatted capability list
        """
        parts = ["I can help you with the following:\n"]

        for name, metadata in self.metadata.items():
            parts.append(f"\n• {metadata.description}")
            parts.append(f"  Category: {metadata.category}")
            if metadata.example_queries:
                parts.append(f"  Example: \"{metadata.example_queries[0]}\"")

        return "\n".join(parts)


# Global registry instance
WORKFLOW_REGISTRY = WorkflowRegistry()


# Helper functions for backwards compatibility
def list_workflows() -> List[str]:
    """List all registered workflows."""
    return WORKFLOW_REGISTRY.list_workflows()


def get_workflow_description(name: str) -> str:
    """Get workflow description by name."""
    metadata = WORKFLOW_REGISTRY.get_metadata(name)
    if metadata:
        return metadata.description
    return "Unknown workflow"


def get_workflow(name: str):
    """Get compiled workflow graph by name."""
    return WORKFLOW_REGISTRY.get_workflow(name)


# Auto-discover workflows on module import
# This will be called when orchestrator imports this module
try:
    WORKFLOW_REGISTRY.discover_workflows()
except Exception as e:
    print(f"⚠ Warning: Failed to auto-discover workflows: {e}")

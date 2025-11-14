"""
Base Workflow Interface

This module defines the minimal interface that all workflows must implement.

Design Principle: Provide interface contract, NOT implementation pattern.
Workflows have complete freedom in how they build their graphs.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel


class WorkflowInputParameter(BaseModel):
    """
    Defines a required input parameter for a workflow.

    This creates a contract between the workflow and the orchestrator.
    The orchestrator will ensure these parameters are gathered before
    invoking the workflow.
    """
    name: str
    description: str
    type: str  # "string", "integer", "boolean", "file_path", etc.
    required: bool = True
    default: Optional[Any] = None
    example: Optional[str] = None
    prompt: Optional[str] = None  # Question to ask user if missing


class WorkflowMetadata(BaseModel):
    """Metadata for workflow discovery and capability description"""
    name: str
    description: str
    capabilities: list[str]
    example_queries: list[str]
    category: str  # "migration", "analysis", "generation", etc.
    version: str = "1.0.0"
    author: str = "Data Engineering Team"
    required_inputs: list[WorkflowInputParameter] = []  # Contract: inputs needed


class BaseWorkflow(ABC):
    """
    Minimal interface for all workflows.

    Design Principle: Provide interface contract, NOT implementation pattern.
    Workflows have complete freedom in how they build their graphs.
    """

    @abstractmethod
    def get_metadata(self) -> WorkflowMetadata:
        """
        Return workflow metadata for registry discovery.

        This enables:
        - Auto-discovery by registry
        - Capability description for users
        - Intent detection by orchestrator

        Returns:
            WorkflowMetadata: Metadata describing this workflow's capabilities
        """
        pass

    @abstractmethod
    def get_compiled_graph(self):
        """
        Return compiled LangGraph.

        Must return: A compiled LangGraph (result of StateGraph.compile())

        Workflow has complete freedom to:
        - Use any state schema
        - Use any agent architecture (supervisor, loop, sequential, custom)
        - Use any number of nodes
        - Use any base utilities (S3Operations, BedrockClient, etc.)

        Do NOT prescribe HOW to build the graph.

        Returns:
            Compiled LangGraph that can be invoked with .invoke()
        """
        pass

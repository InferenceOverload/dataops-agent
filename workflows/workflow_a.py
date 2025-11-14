"""
Workflow A - Simple Agent

Purpose: Prove basic invoke pattern works
Pattern: Single agent → LLM call → response

This is the simplest possible workflow - takes input, calls Claude, returns output.
Used to verify that workflows can be invoked from the orchestrator.
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from core.base_workflow import BaseWorkflow, WorkflowMetadata
from infrastructure.llm.llm_factory import create_llm

# Load environment variables
load_dotenv()

# State Schema
class WorkflowAState(TypedDict):
    """State for Workflow A - Simple Agent"""
    input: str      # Query to process
    output: str     # Result from LLM


class SimpleAgentWorkflow(BaseWorkflow):
    """Simple single-agent workflow for basic queries"""

    def __init__(self):
        """Initialize simple agent workflow"""
        self.llm = create_llm()

    def get_metadata(self) -> WorkflowMetadata:
        """Return workflow metadata for registry discovery"""
        return WorkflowMetadata(
            name="simple",
            description="Handles basic queries with a single LLM call",
            capabilities=[
                "Answer general questions",
                "Provide explanations",
                "Simple information retrieval"
            ],
            example_queries=[
                "What is LangGraph?",
                "Explain data engineering",
                "What are the benefits of Snowflake?"
            ],
            category="general",
            version="1.0.0"
        )

    def get_compiled_graph(self):
        """Build and return compiled graph"""

        def agent_node(state: WorkflowAState) -> dict:
            """
            Simple agent node - calls Claude and returns result.

            Args:
                state: Current workflow state

            Returns:
                dict: State update with output
            """
            user_input = state["input"]

            # Call Claude
            prompt = f"""You are a helpful assistant. Answer the following question concisely:

Question: {user_input}

Provide a clear, direct answer."""

            response = self.llm.invoke(prompt)

            # Extract content from response
            output = response.content if hasattr(response, 'content') else str(response)

            return {
                "output": output
            }

        # Build Graph
        workflow_builder = StateGraph(WorkflowAState)

        # Add nodes
        workflow_builder.add_node("agent", agent_node)

        # Add edges
        workflow_builder.add_edge(START, "agent")
        workflow_builder.add_edge("agent", END)

        # Compile and return
        return workflow_builder.compile()


# For backwards compatibility - create instance and expose compiled graph
_workflow_instance = SimpleAgentWorkflow()
workflow_graph = _workflow_instance.get_compiled_graph()


# For testing directly
if __name__ == "__main__":
    # Test the workflow
    print("Testing Workflow A - Simple Agent")
    print("-" * 50)

    test_input = {
        "input": "What is LangGraph?",
        "output": ""
    }

    print(f"Input: {test_input['input']}")
    print("Processing...")

    result = workflow_graph.invoke(test_input)

    print(f"Output: {result['output']}")
    print("-" * 50)
    print("✓ Workflow A completed successfully")

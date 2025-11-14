"""
Workflow A - Simple Agent

Purpose: Prove basic invoke pattern works
Pattern: Single agent → LLM call → response

This is the simplest possible workflow - takes input, calls Claude, returns output.
Used to verify that workflows can be invoked from the orchestrator.
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# State Schema
class WorkflowAState(TypedDict):
    """State for Workflow A - Simple Agent"""
    input: str      # Query to process
    output: str     # Result from LLM


# Initialize Claude
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7
)


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

    response = llm.invoke(prompt)

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

# Compile graph - MUST be compiled for invocation
workflow_graph = workflow_builder.compile()


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

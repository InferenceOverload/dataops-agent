"""
Workflow C - Iterative Loop

Purpose: Prove complex iterative workflows work
Pattern: Agent loops 2-3 times, storing artifacts

Architecture:
    START → process → [check iteration count]
                ↓                ↓
            continue          done
                ↓                ↓
            (loop back)        END

Each iteration:
- Calls LLM to refine/improve result
- Stores artifact in state
- Increments counter
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# State Schema
class WorkflowCState(TypedDict):
    """State for Workflow C - Iterative Loop"""
    input: str                   # Original query
    iterations: int              # Current iteration count
    max_iterations: int          # Max loops (default 3)
    current_result: str          # Latest result from iteration
    artifacts: list[dict]        # Stored artifacts from each iteration
    output: str                  # Final compiled result


# Initialize Claude
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7
)


def process_node(state: WorkflowCState) -> dict:
    """
    Process node - runs on each iteration.
    Calls LLM to refine/improve the result, stores artifact.

    Args:
        state: Current workflow state

    Returns:
        dict: State update with new iteration results
    """
    user_input = state["input"]
    current_iteration = state["iterations"] + 1
    artifacts = state["artifacts"]
    previous_result = state["current_result"]

    # Build prompt based on iteration
    if current_iteration == 1:
        prompt = f"""You are working on an iterative analysis task.

Task: {user_input}

This is iteration 1 of {state['max_iterations']}.
Provide an initial analysis or response. Keep it concise."""

    else:
        prompt = f"""You are working on an iterative analysis task.

Task: {user_input}

This is iteration {current_iteration} of {state['max_iterations']}.

Previous result:
{previous_result}

Refine, improve, or expand upon the previous result. Add new insights or details."""

    # Call LLM
    response = llm.invoke(prompt)
    result = response.content if hasattr(response, 'content') else str(response)

    # Create artifact for this iteration
    artifact = {
        "iteration": current_iteration,
        "content": result,
        "timestamp": datetime.now().isoformat(),
        "input": user_input
    }

    # Add artifact to list
    updated_artifacts = artifacts + [artifact]

    return {
        "iterations": current_iteration,
        "current_result": result,
        "artifacts": updated_artifacts
    }


def finalize_node(state: WorkflowCState) -> dict:
    """
    Finalize node - compiles all iterations into final output.

    Args:
        state: Current workflow state

    Returns:
        dict: State update with final output
    """
    artifacts = state["artifacts"]
    iterations = state["iterations"]

    # Compile final output
    output_parts = [f"Completed {iterations} iterations:\n"]

    for artifact in artifacts:
        output_parts.append(f"\n--- Iteration {artifact['iteration']} ---")
        output_parts.append(artifact['content'])

    final_output = "\n".join(output_parts)

    return {
        "output": final_output
    }


def should_continue(state: WorkflowCState) -> str:
    """
    Conditional edge routing - decides whether to loop or finish.

    Args:
        state: Current workflow state

    Returns:
        str: "continue" to loop, "finalize" to end
    """
    current_iterations = state["iterations"]
    max_iterations = state["max_iterations"]

    if current_iterations >= max_iterations:
        return "finalize"
    else:
        return "continue"


# Build Graph
workflow_builder = StateGraph(WorkflowCState)

# Add nodes
workflow_builder.add_node("process", process_node)
workflow_builder.add_node("finalize", finalize_node)

# Add edges
workflow_builder.add_edge(START, "process")

# Conditional edge - loop or finish
workflow_builder.add_conditional_edges(
    "process",
    should_continue,
    {
        "continue": "process",    # Loop back to process
        "finalize": "finalize"    # Go to finalize
    }
)

# Finalize goes to END
workflow_builder.add_edge("finalize", END)

# Compile graph - MUST be compiled for invocation
workflow_graph = workflow_builder.compile()


# For testing directly
if __name__ == "__main__":
    # Test the workflow
    print("Testing Workflow C - Iterative Loop")
    print("-" * 50)

    test_input = {
        "input": "Analyze the concept of iterative refinement in AI systems",
        "iterations": 0,
        "max_iterations": 3,
        "current_result": "",
        "artifacts": [],
        "output": ""
    }

    print(f"Input: {test_input['input']}")
    print(f"Max iterations: {test_input['max_iterations']}")
    print("Processing with iterative refinement...")
    print()

    result = workflow_graph.invoke(test_input)

    print(f"Completed iterations: {result['iterations']}")
    print(f"Artifacts created: {len(result['artifacts'])}")
    print()
    print("Artifact Summary:")
    for artifact in result['artifacts']:
        print(f"  - Iteration {artifact['iteration']}: {len(artifact['content'])} characters")
    print()
    print("Final Output:")
    print(result['output'][:500] + "..." if len(result['output']) > 500 else result['output'])
    print("-" * 50)
    print("✓ Workflow C completed successfully")

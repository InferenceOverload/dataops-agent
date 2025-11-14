"""
Main Orchestrator

This is the main orchestrator LangGraph that:
1. Takes user natural language queries
2. Detects intent (which workflow to use)
3. Invokes the selected workflow (BLOCKING)
4. Waits for workflow to complete
5. Formats and explains the result to user

Graph structure:
    START → intent_detection → workflow_invocation → response_formatting → END
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
import os
from dotenv import load_dotenv
from core.workflow_registry import WORKFLOW_REGISTRY, list_workflows, get_workflow_description

# Load environment variables
load_dotenv()


# Orchestrator State Schema
class OrchestratorState(TypedDict):
    """State for Main Orchestrator"""
    user_query: str           # Input from user
    detected_intent: str      # Classified intent (workflow name or meta-query)
    workflow_result: dict     # Result from workflow
    final_response: str       # Formatted response for user


# Initialize Claude
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7
)


def intent_detection_node(state: OrchestratorState) -> dict:
    """
    Intent detection node - uses LLM to classify query and select workflow.

    Analyzes the user query and determines which workflow should handle it:
    - meta: Questions about the system itself (what workflows, help, capabilities)
    - simple: Basic questions, single-step tasks
    - supervisor: Complex tasks requiring coordination between specialists
    - iterative: Tasks needing refinement, multi-step analysis

    Args:
        state: Current orchestrator state

    Returns:
        dict: State update with detected_intent
    """
    user_query = state["user_query"]

    # Get available workflows
    workflows = list_workflows()
    workflow_descriptions = {name: get_workflow_description(name) for name in workflows}

    # Build prompt for intent detection
    prompt = f"""You are an intent classifier for a multi-agent orchestrator system.

User query: "{user_query}"

Available workflows:
{chr(10).join(f'- {name}: {desc}' for name, desc in workflow_descriptions.items())}

Analyze the query and decide how to handle it.

Guidelines:
- "meta": Questions ABOUT the system itself (e.g., "what workflows do you have?", "what can you do?", "help", "list workflows")
- "simple": For straightforward questions, basic queries, single-step tasks
- "supervisor": For complex tasks requiring multiple specialists (research + analysis, planning + execution)
- "iterative": For tasks requiring refinement, progressive improvement, or multi-step iteration

Respond with ONLY one word: meta, simple, supervisor, or iterative

Your decision:"""

    response = llm.invoke(prompt)
    detected_intent = response.content.strip().lower()

    # Validate intent
    valid_intents = ["meta"] + workflows
    if detected_intent not in valid_intents:
        # Default to simple if unclear
        detected_intent = "simple"

    return {
        "detected_intent": detected_intent
    }


def workflow_invocation_node(state: OrchestratorState) -> dict:
    """
    Workflow invocation node - gets workflow from registry and invokes it.

    This is where the BLOCKING happens:
    1. Get the compiled workflow from registry
    2. Transform orchestrator state → workflow state
    3. Call workflow.invoke() ← BLOCKS until workflow completes
    4. Transform workflow result → orchestrator state

    The workflow runs completely (all agents, all loops) before returning.

    Args:
        state: Current orchestrator state

    Returns:
        dict: State update with workflow_result
    """
    workflow_name = state["detected_intent"]
    user_query = state["user_query"]

    # Get workflow from registry
    workflow = WORKFLOW_REGISTRY.get(workflow_name)

    if not workflow:
        return {
            "workflow_result": {
                "success": False,
                "error": f"Unknown workflow: {workflow_name}",
                "output": ""
            }
        }

    # Transform: Orchestrator State → Workflow State
    # Each workflow has different state requirements
    if workflow_name == "simple":
        workflow_input = {
            "input": user_query,
            "output": ""
        }
    elif workflow_name == "supervisor":
        workflow_input = {
            "input": user_query,
            "messages": [],
            "next_agent": "",
            "output": ""
        }
    elif workflow_name == "iterative":
        workflow_input = {
            "input": user_query,
            "iterations": 0,
            "max_iterations": 3,
            "current_result": "",
            "artifacts": [],
            "output": ""
        }
    else:
        # Fallback
        workflow_input = {"input": user_query}

    # INVOKE WORKFLOW - THIS BLOCKS UNTIL COMPLETION
    # The workflow runs completely:
    # - All agents execute
    # - All loops complete
    # - Workflow reaches END state
    # Only then does .invoke() return
    try:
        result = workflow.invoke(workflow_input)

        # Transform: Workflow Result → Orchestrator State
        workflow_result = {
            "success": True,
            "output": result.get("output", ""),
            "workflow_type": workflow_name,
            "metadata": {
                "iterations": result.get("iterations", 1),
                "artifacts_count": len(result.get("artifacts", [])),
                "messages_count": len(result.get("messages", []))
            }
        }

    except Exception as e:
        workflow_result = {
            "success": False,
            "error": str(e),
            "output": "",
            "workflow_type": workflow_name
        }

    return {
        "workflow_result": workflow_result
    }


def handle_meta_query_node(state: OrchestratorState) -> dict:
    """
    Handle meta-queries about the system itself.

    Answers questions like:
    - What workflows do you have?
    - What can you do?
    - Help

    Args:
        state: Current orchestrator state

    Returns:
        dict: State update with workflow_result containing system info
    """
    user_query = state["user_query"]
    workflows = list_workflows()

    # Build information about available workflows
    workflow_info = []
    for name in workflows:
        desc = get_workflow_description(name)
        workflow_info.append(f"- **{name}**: {desc}")

    # Create a comprehensive response
    response = f"""I'm a multi-agent orchestrator system with the following capabilities:

**Available Workflows:**
{chr(10).join(workflow_info)}

**How to use:**
- For simple questions or basic tasks, I'll use the simple workflow
- For complex tasks requiring research and analysis, I'll use the supervisor workflow
- For tasks needing iterative refinement, I'll use the iterative workflow

**Example queries:**
- "What is LangGraph?" → Uses simple workflow
- "Research cloud computing and analyze its benefits" → Uses supervisor workflow
- "Iteratively develop an analysis of AI safety" → Uses iterative workflow

Just ask your question naturally, and I'll automatically route it to the appropriate workflow!"""

    # Create a mock workflow_result for consistency
    return {
        "workflow_result": {
            "success": True,
            "output": response,
            "workflow_type": "meta",
            "metadata": {
                "iterations": 0,
                "artifacts_count": 0,
                "messages_count": 0
            }
        }
    }


def route_after_intent_detection(state: OrchestratorState) -> str:
    """
    Routing function - decides whether to handle meta-query or invoke workflow.

    Args:
        state: Current orchestrator state

    Returns:
        str: Next node name ("handle_meta_query" or "workflow_invocation")
    """
    detected_intent = state["detected_intent"]

    if detected_intent == "meta":
        return "handle_meta_query"
    else:
        return "workflow_invocation"


def response_formatting_node(state: OrchestratorState) -> dict:
    """
    Response formatting node - formats workflow result for user.

    Takes the structured workflow result and creates a human-readable
    explanation of what happened and what the result is.

    Args:
        state: Current orchestrator state

    Returns:
        dict: State update with final_response
    """
    workflow_result = state["workflow_result"]
    detected_intent = state["detected_intent"]
    user_query = state["user_query"]

    if not workflow_result.get("success", False):
        # Error case
        error = workflow_result.get("error", "Unknown error")
        final_response = f"Error: Unable to process query. {error}"
        return {"final_response": final_response}

    # Format response based on workflow type
    output = workflow_result.get("output", "")
    metadata = workflow_result.get("metadata", {})
    workflow_type = workflow_result.get("workflow_type", "unknown")

    # Build formatted response
    response_parts = []

    # For meta queries, just return the output directly
    if workflow_type == "meta":
        return {"final_response": output}

    # Header
    workflow_descriptions = {
        "simple": "simple single-agent workflow",
        "supervisor": "multi-agent supervisor workflow",
        "iterative": "iterative refinement workflow"
    }
    workflow_desc = workflow_descriptions.get(workflow_type, "workflow")

    response_parts.append(f"Query processed using {workflow_desc}.")
    response_parts.append("")

    # Metadata
    if metadata.get("iterations", 1) > 1:
        response_parts.append(f"Completed {metadata['iterations']} iterations.")
    if metadata.get("artifacts_count", 0) > 0:
        response_parts.append(f"Created {metadata['artifacts_count']} artifacts.")
    if metadata.get("messages_count", 0) > 0:
        response_parts.append(f"Exchanged {metadata['messages_count']} messages between agents.")

    if response_parts[-1] != "":
        response_parts.append("")

    # Main output
    response_parts.append("Result:")
    response_parts.append(output)

    final_response = "\n".join(response_parts)

    return {
        "final_response": final_response
    }


# Build Orchestrator Graph
orchestrator_builder = StateGraph(OrchestratorState)

# Add nodes
orchestrator_builder.add_node("intent_detection", intent_detection_node)
orchestrator_builder.add_node("handle_meta_query", handle_meta_query_node)
orchestrator_builder.add_node("workflow_invocation", workflow_invocation_node)
orchestrator_builder.add_node("response_formatting", response_formatting_node)

# Add edges
orchestrator_builder.add_edge(START, "intent_detection")

# Conditional routing after intent detection
orchestrator_builder.add_conditional_edges(
    "intent_detection",
    route_after_intent_detection,
    {
        "handle_meta_query": "handle_meta_query",
        "workflow_invocation": "workflow_invocation"
    }
)

# Both paths converge to response formatting
orchestrator_builder.add_edge("handle_meta_query", "response_formatting")
orchestrator_builder.add_edge("workflow_invocation", "response_formatting")
orchestrator_builder.add_edge("response_formatting", END)

# Compile graph - MUST be compiled for invocation
orchestrator_graph = orchestrator_builder.compile()


# For testing directly
if __name__ == "__main__":
    # Test the orchestrator
    print("Testing Main Orchestrator")
    print("=" * 60)

    test_queries = [
        "What is LangGraph?",
        "Research and analyze the benefits of multi-agent systems",
        "Iteratively refine an analysis of AI agent patterns"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}/{len(test_queries)}")
        print("-" * 60)
        print(f"Query: {query}")
        print()

        test_input = {
            "user_query": query,
            "detected_intent": "",
            "workflow_result": {},
            "final_response": ""
        }

        try:
            result = orchestrator_graph.invoke(test_input)

            print(f"Detected Intent: {result['detected_intent']}")
            print(f"Workflow Success: {result['workflow_result'].get('success', False)}")
            print()
            print("Response:")
            print(result['final_response'])

        except Exception as e:
            print(f"Error: {e}")

        print("-" * 60)

    print("\n" + "=" * 60)
    print("✓ Orchestrator testing complete")

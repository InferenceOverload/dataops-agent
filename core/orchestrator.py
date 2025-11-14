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
from dotenv import load_dotenv
from core.workflow_registry import WORKFLOW_REGISTRY, list_workflows, get_workflow_description
from infrastructure.llm.llm_factory import create_llm

# Load environment variables
load_dotenv()


# Orchestrator State Schema
class OrchestratorState(TypedDict):
    """State for Main Orchestrator"""
    user_query: str           # Input from user
    detected_intent: str      # Classified intent (workflow name or meta-query)
    extracted_parameters: dict  # Parameters extracted from user query
    missing_parameters: list  # Parameters that need to be collected from user
    workflow_result: dict     # Result from workflow
    final_response: str       # Formatted response for user


# Initialize LLM using factory (supports both Anthropic API and AWS Bedrock)
llm = create_llm()


def intent_detection_node(state: OrchestratorState) -> dict:
    """
    Intent detection node - uses LLM with workflow capabilities context.

    Determines:
    - Is this a meta-query? ("What can you do?")
    - Which workflow should handle this?

    Args:
        state: Current orchestrator state

    Returns:
        dict: State update with detected_intent
    """
    user_query = state["user_query"]

    # Check for meta-query keywords
    meta_keywords = [
        "what can you do",
        "capabilities",
        "help me understand",
        "what are you capable of",
        "list workflows",
        "show me workflows",
        "what workflows"
    ]
    if any(keyword in user_query.lower() for keyword in meta_keywords):
        return {"detected_intent": "meta_query"}

    # Get capabilities context from registry
    capabilities_context = WORKFLOW_REGISTRY.get_capabilities_context()

    # Use LLM with capabilities context for intent detection
    prompt = f"""You are a data engineering assistant with these capabilities:

{capabilities_context}

User query: "{user_query}"

Based on the capabilities above, which workflow should handle this query?
Return ONLY the workflow name (e.g., "jil_parser", "simple", "supervisor", "iterative").
If no workflow matches, return "unknown".

Your decision:"""

    response = llm.invoke(prompt)
    workflow_name = response.content.strip().lower()

    # Validate the response
    valid_workflows = WORKFLOW_REGISTRY.list_workflows()
    if workflow_name not in valid_workflows:
        # Default to unknown if not recognized
        workflow_name = "unknown"

    return {
        "detected_intent": workflow_name
    }


def parameter_extraction_node(state: OrchestratorState) -> dict:
    """
    Extract required parameters for the workflow from user query.

    Uses the workflow's input contract (required_inputs) to:
    1. Get list of required parameters
    2. Use LLM to extract them from user query
    3. Identify missing parameters
    4. Generate prompts for missing parameters

    Args:
        state: Current orchestrator state

    Returns:
        dict: State update with extracted_parameters and missing_parameters
    """
    workflow_name = state["detected_intent"]
    user_query = state["user_query"]

    # Get workflow metadata to check required inputs
    metadata = WORKFLOW_REGISTRY.get_metadata(workflow_name)

    if not metadata or not metadata.required_inputs:
        # No required inputs, can proceed directly
        return {
            "extracted_parameters": {},
            "missing_parameters": []
        }

    # Build parameter extraction prompt
    param_descriptions = []
    for param in metadata.required_inputs:
        param_descriptions.append(
            f"- {param.name} ({param.type}): {param.description}"
            f"{f' Example: {param.example}' if param.example else ''}"
        )

    extraction_prompt = f"""Extract workflow parameters from the user query.

Workflow: {metadata.name}
Required Parameters:
{chr(10).join(param_descriptions)}

User Query: "{user_query}"

Extract the parameters from the query. For each parameter, return the value if found, or "MISSING" if not found.
Return as JSON with parameter names as keys.

Example response:
{{
  "file_path": "/path/to/file.jil",
  "current_job": "BATCH_JOB",
  "max_iterations": 3
}}

If a parameter is not mentioned in the query, use "MISSING" as the value.
"""

    response = llm.invoke(extraction_prompt)

    # Parse the LLM response to extract parameters
    import json
    try:
        # Try to extract JSON from response
        content = response.content.strip()
        # Handle markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        extracted = json.loads(content)
    except:
        # Fallback: couldn't parse, assume all missing
        extracted = {}

    # Identify missing required parameters
    missing = []
    extracted_params = {}

    for param in metadata.required_inputs:
        value = extracted.get(param.name)

        if value == "MISSING" or value is None or value == "":
            if param.required and param.default is None:
                # Build the prompt to ask user
                prompt_text = param.prompt or f"Please provide {param.description}"
                if param.example:
                    prompt_text += f"\n\nExample: {param.example}"

                missing.append({
                    "name": param.name,
                    "prompt": prompt_text,
                    "type": param.type
                })
            elif param.default is not None:
                # Use default value
                extracted_params[param.name] = param.default
        else:
            extracted_params[param.name] = value

    return {
        "extracted_parameters": extracted_params,
        "missing_parameters": missing
    }


def handle_missing_parameters_node(state: OrchestratorState) -> dict:
    """
    Handle case where required parameters are missing.

    Generates a user-friendly response asking for the missing information.

    Args:
        state: Current orchestrator state

    Returns:
        dict: State update with workflow_result containing request for info
    """
    missing = state["missing_parameters"]
    workflow_name = state["detected_intent"]

    # Build response asking for missing parameters
    response_parts = [
        f"I need some additional information to run the {workflow_name} workflow:\n"
    ]

    for i, param in enumerate(missing, 1):
        response_parts.append(f"{i}. {param['prompt']}")

    response_parts.append("\nPlease provide this information and I'll process your request.")

    return {
        "workflow_result": {
            "success": False,
            "output": "\n".join(response_parts),
            "workflow_type": "parameter_request",
            "metadata": {
                "iterations": 0,
                "artifacts_count": 0,
                "messages_count": 0
            }
        }
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
    extracted_params = state.get("extracted_parameters", {})

    # Get workflow from registry
    workflow = WORKFLOW_REGISTRY.get_workflow(workflow_name)
    metadata = WORKFLOW_REGISTRY.get_metadata(workflow_name)

    if not workflow:
        return {
            "workflow_result": {
                "success": False,
                "error": f"Unknown workflow: {workflow_name}",
                "output": ""
            }
        }

    # Transform: Orchestrator State → Workflow State
    # Use metadata to build the correct workflow input
    if workflow_name == "jil_parser":
        # Build from extracted parameters
        workflow_input = {
            "file_path": extracted_params.get("file_path", "/path/to/file.jil"),
            "current_job": extracted_params.get("current_job", "UNKNOWN_JOB"),
            "dependencies": [],
            "visited_files": [],
            "iteration_count": 0,
            "max_iterations": extracted_params.get("max_iterations", 3),
            "output": {}
        }
    elif workflow_name == "simple":
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
        # Fallback: try to use extracted parameters or just pass query
        workflow_input = extracted_params if extracted_params else {"input": user_query}

    # INVOKE WORKFLOW - THIS BLOCKS UNTIL COMPLETION
    # The workflow runs completely:
    # - All agents execute
    # - All loops complete
    # - Workflow reaches END state
    # Only then does .invoke() return
    try:
        result = workflow.invoke(workflow_input)

        # Transform: Workflow Result → Orchestrator State
        # Handle different output structures for different workflows
        output_data = result.get("output", "")

        # JIL parser returns nested dict structure
        if workflow_name == "jil_parser" and isinstance(output_data, dict):
            # Extract the actual result content
            if "result" in output_data:
                output_data = output_data
            iterations = result.get("iteration_count", 1)
            artifacts = result.get("artifacts", [])
        else:
            # Other workflows return simple output
            iterations = result.get("iterations", 1)
            artifacts = result.get("artifacts", [])

        workflow_result = {
            "success": True,
            "output": output_data,
            "workflow_type": workflow_name,
            "metadata": {
                "iterations": iterations,
                "artifacts_count": len(artifacts),
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
    Handle meta-queries about system capabilities.

    Returns user-friendly capability description.

    Args:
        state: Current orchestrator state

    Returns:
        dict: State update with workflow_result containing system info
    """
    capabilities_text = WORKFLOW_REGISTRY.get_capabilities_for_user()

    # Create a mock workflow_result for consistency
    return {
        "workflow_result": {
            "success": True,
            "output": capabilities_text + "\n\nWhat would you like help with?",
            "workflow_type": "meta",
            "metadata": {
                "iterations": 0,
                "artifacts_count": 0,
                "messages_count": 0
            }
        }
    }


def handle_unknown_node(state: OrchestratorState) -> dict:
    """
    Handle queries that don't match any workflow.

    Args:
        state: Current orchestrator state

    Returns:
        dict: State update with helpful error message
    """
    return {
        "workflow_result": {
            "success": False,
            "output": (
                "I'm not sure which workflow would be best for that. "
                "Would you like to see what I can do? "
                "Just ask 'What can you do?'"
            ),
            "workflow_type": "unknown",
            "metadata": {
                "iterations": 0,
                "artifacts_count": 0,
                "messages_count": 0
            }
        }
    }


def route_after_intent_detection(state: OrchestratorState) -> str:
    """
    Routing function - decides whether to handle meta-query or extract parameters.

    Args:
        state: Current orchestrator state

    Returns:
        str: Next node name
    """
    detected_intent = state["detected_intent"]

    if detected_intent == "meta_query":
        return "handle_meta_query"
    elif detected_intent == "unknown":
        return "handle_unknown"
    else:
        # For workflows, first extract parameters
        return "parameter_extraction"


def route_after_parameter_extraction(state: OrchestratorState) -> str:
    """
    Routing function - decides whether to ask for missing params or invoke workflow.

    Args:
        state: Current orchestrator state

    Returns:
        str: Next node name
    """
    missing_parameters = state.get("missing_parameters", [])

    if missing_parameters:
        # Missing required parameters, ask user
        return "handle_missing_parameters"
    else:
        # All parameters available, proceed with workflow
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

    # Get workflow type and output
    output = workflow_result.get("output", "")
    metadata = workflow_result.get("metadata", {})
    workflow_type = workflow_result.get("workflow_type", "unknown")

    # For meta queries and parameter requests, return output directly
    # These may have success=False but still have valid output messages
    if workflow_type in ["meta", "parameter_request"]:
        return {"final_response": output}

    # For other workflows, check success
    if not workflow_result.get("success", False):
        # Error case
        error = workflow_result.get("error", "Unknown error")
        final_response = f"Error: Unable to process query. {error}"
        return {"final_response": final_response}

    # Build formatted response
    response_parts = []

    # Header
    workflow_descriptions = {
        "simple": "simple single-agent workflow",
        "supervisor": "multi-agent supervisor workflow",
        "iterative": "iterative refinement workflow",
        "jil_parser": "JIL dependency parser workflow"
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

    # Special formatting for JIL parser
    if workflow_type == "jil_parser" and isinstance(output, dict):
        import json
        # Pretty print the JIL parser results
        if "result" in output:
            result_data = output["result"]
            response_parts.append(f"\nTarget Job: {result_data.get('target_job', 'Unknown')}")
            response_parts.append(f"Total Dependencies Found: {result_data.get('dependency_count', 0)}")

            upstream = result_data.get('upstream_jobs', [])
            downstream = result_data.get('downstream_jobs', [])

            if upstream:
                response_parts.append(f"\nUpstream Jobs ({len(upstream)}):")
                for dep in upstream:
                    response_parts.append(f"  - {dep.get('job', 'Unknown')} ({dep.get('relation', 'unknown')})")

            if downstream:
                response_parts.append(f"\nDownstream Jobs ({len(downstream)}):")
                for dep in downstream:
                    response_parts.append(f"  - {dep.get('job', 'Unknown')} ({dep.get('relation', 'unknown')})")

            response_parts.append(f"\nFiles Analyzed: {', '.join(result_data.get('files_analyzed', []))}")
        else:
            # Fallback to JSON formatting
            response_parts.append(json.dumps(output, indent=2))
    else:
        # For other workflows, convert output to string
        response_parts.append(str(output))

    final_response = "\n".join(response_parts)

    return {
        "final_response": final_response
    }


# Build Orchestrator Graph
orchestrator_builder = StateGraph(OrchestratorState)

# Add nodes
orchestrator_builder.add_node("intent_detection", intent_detection_node)
orchestrator_builder.add_node("parameter_extraction", parameter_extraction_node)
orchestrator_builder.add_node("handle_meta_query", handle_meta_query_node)
orchestrator_builder.add_node("handle_unknown", handle_unknown_node)
orchestrator_builder.add_node("handle_missing_parameters", handle_missing_parameters_node)
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
        "handle_unknown": "handle_unknown",
        "parameter_extraction": "parameter_extraction"
    }
)

# Conditional routing after parameter extraction
orchestrator_builder.add_conditional_edges(
    "parameter_extraction",
    route_after_parameter_extraction,
    {
        "handle_missing_parameters": "handle_missing_parameters",
        "workflow_invocation": "workflow_invocation"
    }
)

# All paths converge to response formatting
orchestrator_builder.add_edge("handle_meta_query", "response_formatting")
orchestrator_builder.add_edge("handle_unknown", "response_formatting")
orchestrator_builder.add_edge("handle_missing_parameters", "response_formatting")
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
            "extracted_parameters": {},
            "missing_parameters": [],
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

"""
Enhanced Orchestrator with AgentCore Memory Integration

This is an enhanced version of the orchestrator that integrates with
AWS Bedrock AgentCore Memory for:
- Session management
- Short-term conversation memory
- Long-term workflow knowledge
- Context-aware execution

Migration path: Gradually replace orchestrator.py with this version.
"""

import time
import uuid
import os
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

from core.workflow_registry import WORKFLOW_REGISTRY
from infrastructure.llm.llm_factory import create_llm
from infrastructure.agentcore.memory_manager import AgentCoreMemoryManager

# Load environment variables
load_dotenv()

# Initialize MLflow for LangGraph tracing (optional)
try:
    from infrastructure.observability import initialize_mlflow
    initialize_mlflow()
except ImportError:
    pass


# ============================================================================
# State Schema
# ============================================================================

class OrchestratorStateV2(TypedDict):
    """Enhanced state with memory integration"""
    # User inputs
    user_query: str
    session_id: str
    user_id: Optional[str]

    # Intent detection
    detected_intent: str
    extracted_parameters: Dict[str, Any]
    missing_parameters: List[Dict[str, Any]]

    # Memory context
    conversation_history: List[Dict[str, Any]]
    workflow_knowledge: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]

    # Workflow execution
    workflow_result: Dict[str, Any]
    final_response: str


# ============================================================================
# Global Instances
# ============================================================================

# LLM instance
llm = create_llm()

# Memory manager instance (initialized lazily)
_memory_manager: Optional[AgentCoreMemoryManager] = None


def get_memory_manager() -> Optional[AgentCoreMemoryManager]:
    """Get or create memory manager instance"""
    global _memory_manager

    if _memory_manager is None:
        memory_id = os.getenv("AGENTCORE_MEMORY_ID")
        if memory_id:
            try:
                _memory_manager = AgentCoreMemoryManager(
                    memory_id=memory_id,
                    environment=os.getenv("ENVIRONMENT", "production")
                )
                print(f"✓ AgentCore Memory initialized: {memory_id}")
            except Exception as e:
                print(f"⚠ AgentCore Memory initialization failed: {e}")
                _memory_manager = None

    return _memory_manager


# ============================================================================
# Graph Nodes
# ============================================================================

def session_initialization_node(state: OrchestratorStateV2) -> Dict[str, Any]:
    """
    Initialize or retrieve session with AgentCore Memory.

    Creates new session if needed and loads:
    - Conversation history
    - User preferences
    - Relevant workflow knowledge
    """
    session_id = state.get("session_id") or str(uuid.uuid4())
    user_id = state.get("user_id", "anonymous")

    memory_mgr = get_memory_manager()

    # Initialize return values
    conversation_history = []
    user_preferences = {}
    workflow_knowledge = []

    if memory_mgr:
        try:
            # Create or get session
            existing_session = memory_mgr.get_session(session_id)
            if not existing_session:
                memory_mgr.create_session(
                    session_id,
                    metadata={
                        "user_id": user_id,
                        "created_at": time.time(),
                        "environment": os.getenv("ENVIRONMENT", "production")
                    }
                )
                print(f"✓ Created new session: {session_id}")
            else:
                print(f"✓ Retrieved existing session: {session_id}")

            # Load conversation history
            conversation_history = memory_mgr.get_conversation_history(
                session_id,
                limit=20  # Last 20 messages
            )

            # Load user preferences
            if user_id != "anonymous":
                user_preferences = memory_mgr.get_user_preferences(user_id)

            # Add user query to conversation
            memory_mgr.add_to_conversation(
                session_id=session_id,
                role="user",
                content=state["user_query"],
                metadata={"timestamp": time.time()}
            )

        except Exception as e:
            print(f"⚠ Session initialization error: {e}")

    return {
        "session_id": session_id,
        "conversation_history": conversation_history,
        "user_preferences": user_preferences,
        "workflow_knowledge": workflow_knowledge
    }


def enhanced_intent_detection_node(state: OrchestratorStateV2) -> Dict[str, Any]:
    """
    Enhanced intent detection with conversation history context.

    Uses conversation history to better understand user intent,
    especially for follow-up questions and clarifications.
    """
    user_query = state["user_query"]
    conversation_history = state.get("conversation_history", [])

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

    # Build context from conversation history
    context = ""
    if conversation_history:
        recent_messages = conversation_history[-5:]  # Last 5 messages
        context = "Recent conversation:\n"
        for msg in recent_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            context += f"{role}: {content}\n"
        context += "\n"

    # Get capabilities context
    capabilities_context = WORKFLOW_REGISTRY.get_capabilities_context()

    # Enhanced prompt with conversation context
    prompt = f"""You are a data engineering assistant with these capabilities:

{capabilities_context}

{context}Current user query: "{user_query}"

Based on the capabilities above and the conversation context, which workflow should handle this query?
Return ONLY the workflow name (e.g., "jil_parser", "simple", "supervisor", "iterative").
If no workflow matches, return "unknown".

Your decision:"""

    response = llm.invoke(prompt)
    workflow_name = response.content.strip().lower()

    # Validate the response
    valid_workflows = WORKFLOW_REGISTRY.list_workflows()
    if workflow_name not in valid_workflows:
        workflow_name = "unknown"

    return {"detected_intent": workflow_name}


def enhanced_parameter_extraction_node(state: OrchestratorStateV2) -> Dict[str, Any]:
    """
    Enhanced parameter extraction with conversation history.

    Can extract parameters from current query AND conversation history,
    allowing users to provide information across multiple messages.
    """
    workflow_name = state["detected_intent"]
    user_query = state["user_query"]
    conversation_history = state.get("conversation_history", [])

    # Get workflow metadata
    metadata = WORKFLOW_REGISTRY.get_metadata(workflow_name)

    if not metadata or not metadata.required_inputs:
        return {
            "extracted_parameters": {},
            "missing_parameters": []
        }

    # Build context from conversation history
    conversation_context = ""
    if conversation_history:
        recent_messages = conversation_history[-10:]
        for msg in recent_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            conversation_context += f"{role}: {content}\n"

    # Build parameter descriptions
    param_descriptions = []
    for param in metadata.required_inputs:
        param_descriptions.append(
            f"- {param.name} ({param.type}): {param.description}"
            f"{f' Example: {param.example}' if param.example else ''}"
        )

    extraction_prompt = f"""Extract workflow parameters from the user query and conversation history.

Workflow: {metadata.name}
Required Parameters:
{chr(10).join(param_descriptions)}

Conversation History:
{conversation_context}

Current Query: "{user_query}"

Extract the parameters from the query and conversation history.
For each parameter, return the value if found, or "MISSING" if not found.
Return as JSON with parameter names as keys.

Example response:
{{
  "file_path": "/path/to/file.jil",
  "current_job": "BATCH_JOB",
  "max_iterations": 3
}}

If a parameter is not mentioned, use "MISSING" as the value.
"""

    response = llm.invoke(extraction_prompt)

    # Parse the LLM response
    import json
    try:
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        extracted = json.loads(content)
    except:
        extracted = {}

    # Identify missing parameters
    missing = []
    extracted_params = {}

    for param in metadata.required_inputs:
        value = extracted.get(param.name)

        if value == "MISSING" or value is None or value == "":
            if param.required and param.default is None:
                prompt_text = param.prompt or f"Please provide {param.description}"
                if param.example:
                    prompt_text += f"\n\nExample: {param.example}"

                missing.append({
                    "name": param.name,
                    "prompt": prompt_text,
                    "type": param.type
                })
            elif param.default is not None:
                extracted_params[param.name] = param.default
        else:
            extracted_params[param.name] = value

    return {
        "extracted_parameters": extracted_params,
        "missing_parameters": missing
    }


def knowledge_retrieval_node(state: OrchestratorStateV2) -> Dict[str, Any]:
    """
    Retrieve relevant workflow knowledge from long-term memory.

    Helps workflows learn from past executions and avoid repeating
    the same work.
    """
    workflow_name = state["detected_intent"]
    user_query = state["user_query"]

    memory_mgr = get_memory_manager()
    workflow_knowledge = []

    if memory_mgr and workflow_name not in ["meta_query", "unknown"]:
        try:
            # Retrieve relevant past executions
            workflow_knowledge = memory_mgr.retrieve_workflow_knowledge(
                workflow_name=workflow_name,
                query=user_query,
                limit=5
            )

            if workflow_knowledge:
                print(f"✓ Retrieved {len(workflow_knowledge)} relevant memories")

        except Exception as e:
            print(f"⚠ Knowledge retrieval error: {e}")

    return {"workflow_knowledge": workflow_knowledge}


def enhanced_workflow_invocation_node(state: OrchestratorStateV2) -> Dict[str, Any]:
    """
    Enhanced workflow invocation with memory context.

    Passes conversation history, workflow knowledge, and user preferences
    to the workflow for context-aware execution.
    """
    workflow_name = state["detected_intent"]
    user_query = state["user_query"]
    extracted_params = state.get("extracted_parameters", {})
    conversation_history = state.get("conversation_history", [])
    workflow_knowledge = state.get("workflow_knowledge", [])
    user_preferences = state.get("user_preferences", {})

    # Get workflow from registry
    workflow = WORKFLOW_REGISTRY.get_workflow(workflow_name)

    if not workflow:
        return {
            "workflow_result": {
                "success": False,
                "error": f"Unknown workflow: {workflow_name}",
                "output": ""
            }
        }

    # Build enhanced workflow input with memory context
    workflow_input = {
        **extracted_params,
        "_memory_context": {
            "conversation_history": conversation_history[-5:],  # Last 5 messages
            "workflow_knowledge": workflow_knowledge,
            "user_preferences": user_preferences
        }
    }

    # Add workflow-specific inputs (existing logic)
    if workflow_name == "jil_parser":
        workflow_input.update({
            "file_path": extracted_params.get("file_path", "/path/to/file.jil"),
            "current_job": extracted_params.get("current_job", "UNKNOWN_JOB"),
            "dependencies": [],
            "visited_files": [],
            "iteration_count": 0,
            "max_iterations": extracted_params.get("max_iterations", 3),
            "output": {}
        })
    elif workflow_name in ["simple", "supervisor", "iterative"]:
        workflow_input["input"] = user_query

    # Execute workflow
    start_time = time.time()

    try:
        result = workflow.invoke(workflow_input)
        execution_time = time.time() - start_time

        # Prepare workflow result
        output_data = result.get("output", "")
        workflow_result = {
            "success": True,
            "output": output_data,
            "workflow_type": workflow_name,
            "metadata": {
                "execution_time_seconds": execution_time,
                "iterations": result.get("iteration_count", result.get("iterations", 1)),
                "artifacts_count": len(result.get("artifacts", [])),
                "messages_count": len(result.get("messages", []))
            }
        }

        # Store result in long-term memory
        memory_mgr = get_memory_manager()
        if memory_mgr and workflow_result["success"]:
            try:
                execution_id = str(uuid.uuid4())
                memory_mgr.store_workflow_result(
                    workflow_name=workflow_name,
                    execution_id=execution_id,
                    result=result,
                    tags=[workflow_name, os.getenv("ENVIRONMENT", "production")],
                    summary=f"Executed {workflow_name} for query: {user_query[:100]}"
                )
                print(f"✓ Stored workflow result in long-term memory")
            except Exception as e:
                print(f"⚠ Failed to store workflow result: {e}")

    except Exception as e:
        execution_time = time.time() - start_time
        workflow_result = {
            "success": False,
            "error": str(e),
            "output": "",
            "workflow_type": workflow_name,
            "metadata": {
                "execution_time_seconds": execution_time
            }
        }

    return {"workflow_result": workflow_result}


def enhanced_response_formatting_node(state: OrchestratorStateV2) -> Dict[str, Any]:
    """
    Enhanced response formatting that saves to conversation history.
    """
    workflow_result = state["workflow_result"]
    session_id = state["session_id"]

    # Format response (use existing logic from orchestrator.py)
    from core.orchestrator import response_formatting_node
    formatted = response_formatting_node({
        "workflow_result": workflow_result,
        "detected_intent": state["detected_intent"],
        "user_query": state["user_query"]
    })

    final_response = formatted["final_response"]

    # Save assistant response to conversation history
    memory_mgr = get_memory_manager()
    if memory_mgr:
        try:
            memory_mgr.add_to_conversation(
                session_id=session_id,
                role="assistant",
                content=final_response,
                metadata={
                    "workflow": state["detected_intent"],
                    "success": workflow_result.get("success", False),
                    "execution_time": workflow_result.get("metadata", {}).get("execution_time_seconds")
                }
            )
        except Exception as e:
            print(f"⚠ Failed to save response to conversation: {e}")

    return {"final_response": final_response}


# Reuse other nodes from original orchestrator
from core.orchestrator import (
    handle_meta_query_node,
    handle_unknown_node,
    handle_missing_parameters_node,
    route_after_parameter_extraction
)


def route_after_intent_detection_v2(state: OrchestratorStateV2) -> str:
    """Enhanced routing with knowledge retrieval"""
    detected_intent = state["detected_intent"]

    if detected_intent == "meta_query":
        return "handle_meta_query"
    elif detected_intent == "unknown":
        return "handle_unknown"
    else:
        # First retrieve knowledge, then extract parameters
        return "knowledge_retrieval"


def route_after_knowledge_retrieval(state: OrchestratorStateV2) -> str:
    """Route to parameter extraction after knowledge retrieval"""
    return "parameter_extraction"


# ============================================================================
# Build Enhanced Graph
# ============================================================================

orchestrator_builder_v2 = StateGraph(OrchestratorStateV2)

# Add nodes
orchestrator_builder_v2.add_node("session_initialization", session_initialization_node)
orchestrator_builder_v2.add_node("intent_detection", enhanced_intent_detection_node)
orchestrator_builder_v2.add_node("knowledge_retrieval", knowledge_retrieval_node)
orchestrator_builder_v2.add_node("parameter_extraction", enhanced_parameter_extraction_node)
orchestrator_builder_v2.add_node("handle_meta_query", handle_meta_query_node)
orchestrator_builder_v2.add_node("handle_unknown", handle_unknown_node)
orchestrator_builder_v2.add_node("handle_missing_parameters", handle_missing_parameters_node)
orchestrator_builder_v2.add_node("workflow_invocation", enhanced_workflow_invocation_node)
orchestrator_builder_v2.add_node("response_formatting", enhanced_response_formatting_node)

# Add edges
orchestrator_builder_v2.add_edge(START, "session_initialization")
orchestrator_builder_v2.add_edge("session_initialization", "intent_detection")

# Conditional routing after intent detection
orchestrator_builder_v2.add_conditional_edges(
    "intent_detection",
    route_after_intent_detection_v2,
    {
        "handle_meta_query": "handle_meta_query",
        "handle_unknown": "handle_unknown",
        "knowledge_retrieval": "knowledge_retrieval"
    }
)

# Knowledge retrieval flows to parameter extraction
orchestrator_builder_v2.add_edge("knowledge_retrieval", "parameter_extraction")

# Conditional routing after parameter extraction
orchestrator_builder_v2.add_conditional_edges(
    "parameter_extraction",
    route_after_parameter_extraction,
    {
        "handle_missing_parameters": "handle_missing_parameters",
        "workflow_invocation": "workflow_invocation"
    }
)

# All paths converge to response formatting
orchestrator_builder_v2.add_edge("handle_meta_query", "response_formatting")
orchestrator_builder_v2.add_edge("handle_unknown", "response_formatting")
orchestrator_builder_v2.add_edge("handle_missing_parameters", "response_formatting")
orchestrator_builder_v2.add_edge("workflow_invocation", "response_formatting")
orchestrator_builder_v2.add_edge("response_formatting", END)

# Compile graph
orchestrator_graph_v2 = orchestrator_builder_v2.compile()


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    print("Testing Enhanced Orchestrator with AgentCore Memory")
    print("=" * 70)

    test_input = {
        "user_query": "What can you do?",
        "session_id": "",
        "user_id": "test_user",
        "detected_intent": "",
        "extracted_parameters": {},
        "missing_parameters": [],
        "conversation_history": [],
        "workflow_knowledge": [],
        "user_preferences": {},
        "workflow_result": {},
        "final_response": ""
    }

    try:
        result = orchestrator_graph_v2.invoke(test_input)
        print(f"\nSession ID: {result['session_id']}")
        print(f"Detected Intent: {result['detected_intent']}")
        print(f"\nResponse:\n{result['final_response']}")
    except Exception as e:
        print(f"Error: {e}")

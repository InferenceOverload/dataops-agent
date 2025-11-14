# Architecture Documentation

**Project:** Multi-Agent Orchestrator POC
**Date:** November 13, 2025

---

## Overview

This POC validates a pattern where a main orchestrator LangGraph dynamically invokes complete workflow LangGraphs using blocking execution and structured contracts.

---

## Core Architecture

### Pattern Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     User Query                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Main Orchestrator (LangGraph)                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 1. Intent Detection Node                           │    │
│  │    - Uses LLM to understand query                  │    │
│  │    - Classifies as: simple, supervisor, iterative  │    │
│  └─────────────────────┬──────────────────────────────┘    │
│                        │                                     │
│  ┌─────────────────────▼──────────────────────────────┐    │
│  │ 2. Workflow Invocation Node (BLOCKING)             │    │
│  │    - Gets workflow from registry                   │    │
│  │    - Transforms state                              │    │
│  │    - Calls workflow.invoke() ← WAITS HERE          │    │
│  └─────────────────────┬──────────────────────────────┘    │
└────────────────────────┼────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Workflow (Black Box LangGraph)                 │
│                                                              │
│  Could be:                                                  │
│  • Simple Agent (single LLM call)                          │
│  • Supervisor Pattern (supervisor + workers)               │
│  • Iterative Loop (loops 2-3 times)                        │
│                                                              │
│  Executes completely:                                       │
│  - All agents run                                           │
│  - All loops complete                                       │
│  - Reaches END state                                        │
│                                                              │
│  Returns: Structured result dict                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Main Orchestrator (continued)                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 3. Response Formatting Node                        │    │
│  │    - Receives workflow result                      │    │
│  │    - Formats for user                              │    │
│  │    - Explains what happened                        │    │
│  └─────────────────────┬──────────────────────────────┘    │
└────────────────────────┼────────────────────────────────────┘
                         │
                         ▼
                  Final Response
```

---

## Component Details

### Main Orchestrator

**File:** `core/orchestrator.py`

**State Schema:**
```python
class OrchestratorState(TypedDict):
    user_query: str           # Input from user
    detected_intent: str      # Classified intent (simple/supervisor/iterative)
    workflow_result: dict     # Result from workflow
    final_response: str       # Formatted response for user
```

**Nodes:**

1. **intent_detection_node**
   - Uses Claude to classify query
   - Maps to workflow name
   - Returns: `{"detected_intent": "workflow_name"}`

2. **workflow_invocation_node**
   - Gets workflow from registry
   - Transforms orchestrator state → workflow state
   - Invokes: `result = workflow.invoke(input)`  ← BLOCKS
   - Transforms workflow result → orchestrator state
   - Returns: `{"workflow_result": result}`

3. **response_formatting_node**
   - Takes workflow result
   - Formats for human readability
   - Returns: `{"final_response": "..."}`

**Graph Structure:**
```
START → intent_detection → workflow_invocation → response_formatting → END
```

**Workflow Registry:**
```python
WORKFLOW_REGISTRY = {
    "simple": workflow_a.workflow_graph,      # Compiled LangGraph
    "supervisor": workflow_b.workflow_graph,  # Compiled LangGraph
    "iterative": workflow_c.workflow_graph    # Compiled LangGraph
}
```

---

### Workflow A - Simple Agent

**File:** `workflows/workflow_a.py`

**Purpose:** Prove basic invoke pattern works

**Pattern:** Single agent → LLM call → response

**State Schema:**
```python
class WorkflowAState(TypedDict):
    input: str     # Query to process
    output: str    # Result from LLM
```

**Nodes:**
- **agent_node**: Calls Claude, returns result

**Graph Structure:**
```
START → agent → END
```

**Example:**
- Input: `{"input": "What is 2+2?"}`
- Processing: Single LLM call
- Output: `{"input": "What is 2+2?", "output": "2+2 equals 4"}`

---

### Workflow B - Supervisor Pattern

**File:** `workflows/workflow_b.py`

**Purpose:** Prove multi-agent workflows work as subgraphs

**Pattern:** Supervisor orchestrates 2 worker agents

**State Schema:**
```python
class WorkflowBState(TypedDict):
    input: str              # Original query
    messages: list[str]     # Message history
    next_agent: str         # Next agent to invoke
    output: str             # Final result
```

**Nodes:**
- **supervisor_node**: LLM decides which worker to call
- **worker1_node**: Specialized worker (e.g., research)
- **worker2_node**: Specialized worker (e.g., analysis)

**Graph Structure:**
```
START → supervisor
            ↓
    ┌───────┴───────┐
    ↓               ↓
worker1         worker2
    │               │
    └───────┬───────┘
            ↓
       supervisor (conditional: loop or END)
```

**Example:**
- Input: `{"input": "Research and analyze topic X"}`
- Flow:
  1. Supervisor → "Send to worker1 for research"
  2. Worker1 → Research results
  3. Supervisor → "Send to worker2 for analysis"
  4. Worker2 → Analysis results
  5. Supervisor → "Done" → END
- Output: `{"output": "Research: ... Analysis: ..."}`

---

### Workflow C - Iterative Loop

**File:** `workflows/workflow_c.py`

**Purpose:** Prove complex iterative workflows work

**Pattern:** Agent loops 2-3 times, storing artifacts

**State Schema:**
```python
class WorkflowCState(TypedDict):
    input: str                   # Original query
    iterations: int              # Current iteration count
    max_iterations: int          # Max loops (default 3)
    current_result: str          # Latest result
    artifacts: list[dict]        # Stored artifacts
    output: str                  # Final compiled result
```

**Nodes:**
- **process_node**: Processes query, creates artifact, increments counter

**Graph Structure:**
```
START → process
          ↓
     [check: continue?]
          ↓
      yes ┌─┘ (loop)
      no  ↓
        END
```

**Example:**
- Input: `{"input": "Iteratively refine analysis", "max_iterations": 3}`
- Flow:
  1. Iteration 1 → Create artifact 1
  2. Iteration 2 → Create artifact 2
  3. Iteration 3 → Create artifact 3
  4. Max reached → END
- Output: `{"output": "Final result", "artifacts": [a1, a2, a3], "iterations": 3}`

---

## State Transformation Pattern

### Problem
Orchestrator state schema ≠ Workflow state schema

### Solution
Explicit transformation in workflow invocation node

### Implementation

```python
def invoke_workflow_node(state: OrchestratorState):
    # 1. Get workflow
    workflow_name = state["detected_intent"]
    workflow = WORKFLOW_REGISTRY[workflow_name]

    # 2. Transform: Orchestrator State → Workflow State
    if workflow_name == "simple":
        workflow_input = {
            "input": state["user_query"],
            "output": ""
        }
    elif workflow_name == "supervisor":
        workflow_input = {
            "input": state["user_query"],
            "messages": [],
            "next_agent": "",
            "output": ""
        }
    elif workflow_name == "iterative":
        workflow_input = {
            "input": state["user_query"],
            "iterations": 0,
            "max_iterations": 3,
            "current_result": "",
            "artifacts": [],
            "output": ""
        }

    # 3. INVOKE (blocking)
    result = workflow.invoke(workflow_input)

    # 4. Transform: Workflow Result → Orchestrator State
    return {
        "workflow_result": {
            "success": True,
            "output": result.get("output", ""),
            "workflow_type": workflow_name,
            "metadata": {
                "iterations": result.get("iterations", 1),
                "artifacts_count": len(result.get("artifacts", []))
            }
        }
    }
```

### Benefits
- ✅ Clear boundaries
- ✅ Workflows are independent
- ✅ Easy to test in isolation
- ✅ No coupling
- ✅ Explicit > implicit

---

## Structured Contracts

### Contract Definition

All workflows MUST return a result with this structure:

```python
{
    "output": str,              # Primary result (required)
    "iterations": int,          # How many loops/steps (optional)
    "artifacts": list[dict],    # Stored artifacts (optional)
    "metadata": dict            # Additional info (optional)
}
```

### Why Contracts Matter

1. **Predictability** - Orchestrator knows what to expect
2. **Extensibility** - Easy to add new workflows
3. **Testing** - Can mock workflows with contract-compliant data
4. **Documentation** - Contract serves as API spec
5. **Decoupling** - Implementation can change, contract stays same

---

## Execution Model

### Blocking `.invoke()` Pattern

**How It Works:**

```python
# Orchestrator waits here
result = workflow.invoke(input)
# ↑ This line blocks until workflow completes

# Workflow execution (invisible to orchestrator):
# 1. START
# 2. Node 1 executes
# 3. Node 2 executes
# 4. ... (all nodes, all loops)
# 5. END reached
# 6. Returns final state
#
# Only then does .invoke() return
```

**Timing:**
- Simple workflow: ~1-2 seconds
- Supervisor workflow: ~3-5 seconds (multiple LLM calls)
- Iterative workflow: ~4-8 seconds (3 iterations × LLM calls)

**For POC:** Blocking is intentional - proves the pattern

**For Future:** Can switch to `.stream()` for progress updates:
```python
for chunk in workflow.stream(input, stream_mode="updates"):
    print(f"Progress: {chunk}")  # Real-time updates
```

---

## Testing Strategy

### Level 1: Unit Test Workflows Independently

Test each workflow in isolation:

```python
# Test workflow_a
result = workflow_a.workflow_graph.invoke({"input": "test query"})
assert "output" in result
assert result["output"] != ""

# Test workflow_b
result = workflow_b.workflow_graph.invoke({"input": "test query"})
assert "output" in result
assert len(result["messages"]) > 0

# Test workflow_c
result = workflow_c.workflow_graph.invoke({
    "input": "test query",
    "iterations": 0,
    "max_iterations": 3
})
assert result["iterations"] == 3
assert len(result["artifacts"]) == 3
```

### Level 2: Test via LangGraph Dev Server

Use Swagger UI at http://localhost:2024/docs

**Test Workflow A:**
```json
{
  "assistant_id": "workflow_a",
  "input": {"input": "What is LangGraph?"}
}
```

**Test Workflow B:**
```json
{
  "assistant_id": "workflow_b",
  "input": {"input": "Research and analyze LangGraph"}
}
```

**Test Workflow C:**
```json
{
  "assistant_id": "workflow_c",
  "input": {
    "input": "Iteratively refine analysis",
    "max_iterations": 3
  }
}
```

### Level 3: Integration Test Orchestrator

**Test Full Pattern:**
```json
{
  "assistant_id": "orchestrator",
  "input": {"user_query": "simple question"}
}
```

Should:
1. Detect intent → "simple"
2. Invoke workflow_a
3. Wait for completion
4. Format response
5. Return to user

---

## Key Insights

### What Works

✅ **Compiled graphs in registry** - Store in dict, invoke dynamically
✅ **Blocking invoke** - Waits for complete execution
✅ **State transformation** - Clean, explicit, predictable
✅ **Supervisor as subgraph** - Multi-agent workflows work perfectly
✅ **Iterative loops** - Conditional edges enable complex patterns
✅ **Structured contracts** - Sufficient for communication

### Limitations

⚠️ **No streaming** - POC uses blocking only (future enhancement)
⚠️ **Manual transformation** - No automatic state mapping (this is good!)
⚠️ **Simple registry** - Python dict (production would use DB)
⚠️ **No error recovery** - Workflows fail fast (intentional for POC)

---

## Design Decisions

### Why Both Are LangGraphs?

**Orchestrator = LangGraph**
- Consistent pattern
- Composable (could be invoked by another orchestrator)
- Built-in state management
- Easy to extend with new nodes

**Workflows = LangGraphs**
- True black boxes
- Can use any LangGraph pattern
- Self-contained
- Testable in isolation

### Why Blocking Execution?

**For POC:**
- ✅ Simpler to implement
- ✅ Easier to reason about
- ✅ Proves the core pattern
- ✅ Sequential flow is clear

**For Production:**
- Can add `.stream()` later
- Non-blocking if needed
- Parallel workflow invocation if needed

### Why Manual State Transformation?

**Explicit > Implicit**
- Clear what data flows where
- No magic
- Easy to debug
- Type-safe
- Intentional mapping

---

## Future Enhancements

### Streaming Progress
```python
for chunk in workflow.stream(input, stream_mode="updates"):
    # Stream to user in real-time
    yield chunk
```

### Parallel Workflows
```python
# Invoke multiple workflows concurrently
results = await asyncio.gather(
    workflow_a.ainvoke(input_a),
    workflow_b.ainvoke(input_b)
)
```

### Persistent Registry
- Store workflows in database
- Hot-reload on updates
- Version control for workflows

### Error Recovery
- Retry logic
- Fallback workflows
- Graceful degradation

### Monitoring
- Execution time tracking
- LLM token usage
- Workflow success rates

---

## Conclusion

This POC validates that:

1. ✅ Complete multi-agent workflows can be invoked as black boxes
2. ✅ Blocking execution works reliably
3. ✅ State transformation is clean and explicit
4. ✅ Structured contracts enable decoupled communication
5. ✅ Pattern is extensible and maintainable

**The pattern works.** Ready for production consideration with enhancements.

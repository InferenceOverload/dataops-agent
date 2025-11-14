# LangGraph Patterns Reference

## Current LangGraph API (v0.2+)

This document shows the correct patterns used in DataOps Agent workflows.

---

## Basic Imports

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict
```

### Constants
- `START = "__start__"` - Entry point marker
- `END = "__end__"` - Exit point marker

---

## State Schema

```python
class MyWorkflowState(TypedDict):
    """State schema for workflow"""
    input: str
    output: str
    # ... other fields
```

**Key Points:**
- Use `TypedDict` for state schema
- All state fields should have type annotations
- State is passed between nodes

---

## Building a Graph

### 1. Create StateGraph

```python
graph_builder = StateGraph(MyWorkflowState)
```

### 2. Add Nodes

```python
def my_node(state: MyWorkflowState) -> dict:
    """Node function - processes state and returns updates"""
    return {"output": "processed"}

graph_builder.add_node("node_name", my_node)
```

**Node Function Rules:**
- Takes `state` parameter (typed as your State schema)
- Returns `dict` with state updates
- Only need to return fields that changed
- Returned dict is merged into state

### 3. Add Edges

```python
# Simple edge: always go from A to B
graph_builder.add_edge(START, "first_node")
graph_builder.add_edge("first_node", "second_node")
graph_builder.add_edge("second_node", END)
```

### 4. Conditional Edges

```python
def route_function(state: MyWorkflowState) -> str:
    """Decide which node to go to next"""
    if state["some_condition"]:
        return "path_a"
    else:
        return "path_b"

graph_builder.add_conditional_edges(
    "decision_node",
    route_function,
    {
        "path_a": "node_a",
        "path_b": "node_b"
    }
)
```

**Routing Function Rules:**
- Takes `state` parameter
- Returns `str` (name of next node)
- Return value must match a key in the mapping dict

### 5. Compile and Invoke

```python
# Compile the graph
compiled_graph = graph_builder.compile()

# Invoke the graph (blocking call)
result = compiled_graph.invoke({
    "input": "test",
    "output": ""
})

# Access result
print(result["output"])
```

---

## Complete Example

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

# 1. Define State
class SimpleState(TypedDict):
    input: str
    output: str

# 2. Define Nodes
def process_node(state: SimpleState) -> dict:
    result = state["input"].upper()
    return {"output": result}

# 3. Build Graph
builder = StateGraph(SimpleState)
builder.add_node("process", process_node)
builder.add_edge(START, "process")
builder.add_edge("process", END)

# 4. Compile
graph = builder.compile()

# 5. Use
result = graph.invoke({"input": "hello", "output": ""})
print(result["output"])  # "HELLO"
```

---

## Pattern 1: Linear Flow

```python
builder = StateGraph(MyState)
builder.add_node("step1", step1_fn)
builder.add_node("step2", step2_fn)
builder.add_node("step3", step3_fn)

builder.add_edge(START, "step1")
builder.add_edge("step1", "step2")
builder.add_edge("step2", "step3")
builder.add_edge("step3", END)
```

**Flow:** START → step1 → step2 → step3 → END

---

## Pattern 2: Conditional Branch

```python
def router(state: MyState) -> str:
    if state["value"] > 10:
        return "high"
    return "low"

builder = StateGraph(MyState)
builder.add_node("analyze", analyze_fn)
builder.add_node("handle_high", high_fn)
builder.add_node("handle_low", low_fn)

builder.add_edge(START, "analyze")
builder.add_conditional_edges(
    "analyze",
    router,
    {
        "high": "handle_high",
        "low": "handle_low"
    }
)
builder.add_edge("handle_high", END)
builder.add_edge("handle_low", END)
```

**Flow:** START → analyze → [high/low] → END

---

## Pattern 3: Loop (Iterative)

```python
def should_continue(state: MyState) -> str:
    if state["iterations"] < state["max_iterations"]:
        return "continue"
    return "done"

builder = StateGraph(MyState)
builder.add_node("process", process_fn)
builder.add_node("finalize", finalize_fn)

builder.add_edge(START, "process")
builder.add_conditional_edges(
    "process",
    should_continue,
    {
        "continue": "process",  # Loop back
        "done": "finalize"
    }
)
builder.add_edge("finalize", END)
```

**Flow:** START → process → [loop or finalize] → END

---

## Pattern 4: Supervisor (Multi-Agent)

```python
def route_supervisor(state: SupervisorState) -> str:
    next_agent = state["next_agent"]
    if next_agent == "finish":
        return "finalize"
    return next_agent

builder = StateGraph(SupervisorState)
builder.add_node("supervisor", supervisor_fn)
builder.add_node("worker1", worker1_fn)
builder.add_node("worker2", worker2_fn)
builder.add_node("finalize", finalize_fn)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "worker1": "worker1",
        "worker2": "worker2",
        "finalize": "finalize"
    }
)
builder.add_edge("worker1", "supervisor")  # Loop back
builder.add_edge("worker2", "supervisor")  # Loop back
builder.add_edge("finalize", END)
```

**Flow:** START → supervisor → [worker1/worker2 → supervisor] → finalize → END

---

## Common Mistakes to Avoid

### ❌ Wrong: Adding edges incorrectly
```python
# Don't use string literals for START/END
builder.add_edge("start", "node")  # WRONG

# Use constants
builder.add_edge(START, "node")  # CORRECT
```

### ❌ Wrong: Node function return
```python
def my_node(state):
    state["output"] = "value"  # WRONG - mutating state
    return state                # WRONG - returning whole state
```

### ✅ Correct: Node function return
```python
def my_node(state):
    return {"output": "value"}  # CORRECT - return updates only
```

### ❌ Wrong: Conditional routing
```python
builder.add_conditional_edges(
    "node",
    router_fn,
    ["path_a", "path_b"]  # WRONG - list instead of dict
)
```

### ✅ Correct: Conditional routing
```python
builder.add_conditional_edges(
    "node",
    router_fn,
    {
        "path_a": "target_a",  # CORRECT - dict mapping
        "path_b": "target_b"
    }
)
```

---

## Our Workflow Patterns in DataOps Agent

### Simple Workflow (workflow_a.py)
- **Pattern:** Linear (START → agent → END)
- **Use Case:** Single LLM call, straightforward tasks

### Supervisor Workflow (workflow_b.py)
- **Pattern:** Supervisor multi-agent
- **Use Case:** Complex tasks needing research + analysis

### Iterative Workflow (workflow_c.py)
- **Pattern:** Loop with conditional exit
- **Use Case:** Progressive refinement over multiple iterations

### JIL Parser Workflow
- **Pattern:** Root → Loop → Finalize
- **Use Case:** Iterative dependency discovery

---

## Debugging Tips

### Visualize Your Graph
```python
# After compiling, you can visualize
compiled = builder.compile()

# Get mermaid diagram
print(compiled.get_graph().draw_mermaid())
```

### Check State at Each Node
```python
def debug_node(state: MyState) -> dict:
    print(f"Current state: {state}")
    # ... process ...
    return updates
```

### Verify Node Names Match
```python
# Make sure:
# 1. Node names in add_node() match names in edges
# 2. Router return values match keys in conditional_edges mapping
```

---

## References

- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/
- **Examples:** https://github.com/langchain-ai/langgraph/tree/main/examples
- **Our Implementation:** See `workflows/` directory for working examples

---

**Summary:** All our workflows use the correct current LangGraph API. The patterns are proven and working!

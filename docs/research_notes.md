# LangGraph Research Notes

**Date:** November 13, 2025
**Purpose:** Research findings for Multi-Agent Orchestrator POC

---

## Overview

This document contains research findings on LangGraph concepts required to build a multi-agent orchestrator system where a main orchestrator LangGraph dynamically invokes complete workflow LangGraphs.

---

## 1. Subgraphs and Hierarchical Teams

### Official Documentation
- **Primary Resource:** https://docs.langchain.com/oss/python/langgraph/use-subgraphs
- **Tutorial:** https://langchain-ai.github.io/langgraph/tutorials/multi_agent/hierarchical_agent_teams/

### Key Concepts

**What is a Subgraph?**
- A subgraph is a complete LangGraph used as a node within a parent graph
- Enables building multi-agent systems with modular, reusable components
- Teams can work independently on different graph sections

**Hierarchical Agent Teams:**
- Work is distributed hierarchically through composing different subgraphs
- Involves a top-level supervisor and mid-level supervisors
- Each team can be a complete multi-agent system (supervisor + workers)

### Two Primary Implementation Approaches

#### Approach 1: Invoking a Graph from a Node (Recommended for POC)

**Use Case:** Parent and subgraph have **different state schemas**

**Pattern:**
```python
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

# Subgraph with its own schema
class SubgraphState(TypedDict):
    bar: str

def subgraph_node(state: SubgraphState):
    return {"bar": "processed: " + state["bar"]}

subgraph_builder = StateGraph(SubgraphState)
subgraph_builder.add_node("process", subgraph_node)
subgraph_builder.add_edge(START, "process")
subgraph_builder.add_edge("process", END)
subgraph = subgraph_builder.compile()  # ← Compiled LangGraph

# Parent graph with different schema
class ParentState(TypedDict):
    foo: str

def invoke_subgraph_node(state: ParentState):
    # Transform parent state → subgraph state
    subgraph_input = {"bar": state["foo"]}

    # INVOKE (blocking - waits for completion)
    result = subgraph.invoke(subgraph_input)

    # Transform subgraph result → parent state
    return {"foo": result["bar"]}

parent_builder = StateGraph(ParentState)
parent_builder.add_node("call_subgraph", invoke_subgraph_node)
parent_builder.add_edge(START, "call_subgraph")
parent_builder.add_edge("call_subgraph", END)
parent_graph = parent_builder.compile()
```

**Key Points:**
- Subgraphs can have **completely different schemas** (no shared keys required)
- Wrapper function handles state transformation at boundaries
- Subgraph is invoked via `.invoke()` method inside a node function
- Transformation happens explicitly in the wrapper function

#### Approach 2: Adding Graph as Direct Node

**Use Case:** Parent and subgraph **share state keys**

**Pattern:**
```python
class SharedState(TypedDict):
    message: str

# Subgraph
subgraph_builder = StateGraph(SharedState)
subgraph_builder.add_node("process", process_node)
subgraph_builder.add_edge(START, "process")
subgraph_builder.add_edge("process", END)
subgraph = subgraph_builder.compile()

# Parent - add compiled subgraph directly
parent_builder = StateGraph(SharedState)
parent_builder.add_node("subgraph", subgraph)  # Direct addition
parent_builder.add_edge(START, "subgraph")
parent_builder.add_edge("subgraph", END)
parent_graph = parent_builder.compile()
```

**Key Points:**
- Simpler syntax when state schemas overlap
- Subgraph accesses only its defined state keys
- Works well for multi-agent systems with shared message channels

### For This POC
**Use Approach 1 (Invoke from Node)** because:
- Gives us maximum flexibility
- Workflows are truly independent black boxes
- Clear state transformation boundaries
- Proves the most challenging pattern

---

## 2. Compiled Graphs as Callable Objects

### Official Documentation
- **Reference:** https://reference.langchain.com/python/langgraph/graphs/

### Core Concept: `.compile()` Method

**What Compilation Does:**
- Takes a graph definition and returns a **runnable object**
- The runnable implements the standard LangChain Runnable interface
- Must compile before execution

**Pattern:**
```python
from langgraph.graph import StateGraph, START, END

# 1. Build graph
builder = StateGraph(StateSchema)
builder.add_node("node1", node1_func)
builder.add_edge(START, "node1")
builder.add_edge("node1", END)

# 2. Compile to get runnable
compiled_graph = builder.compile()  # ← Returns executable runnable

# 3. Invoke (multiple times if needed)
result1 = compiled_graph.invoke({"input": "query1"})
result2 = compiled_graph.invoke({"input": "query2"})
```

**Key Insight:**
> "You must compile the graph using the compile() method before it can be executed. The runnable exposes all the same methods as LangChain runnables (.invoke, .stream, .astream_log, etc)"

### `.invoke()` - Blocking Execution

**Behavior:**
- **Synchronous/blocking** - waits for entire graph to complete
- Graph executes all nodes, follows all edges, reaches END state
- Only then returns the final state

**Pattern in Orchestrator:**
```python
def invoke_workflow_node(state: OrchestratorState):
    # Get compiled workflow
    workflow = workflow_registry["sql_generation"]

    # THIS BLOCKS - waits for workflow to fully complete
    # Could take seconds or minutes depending on workflow
    result = workflow.invoke({
        "input": state["user_query"]
    })

    # Only reaches here when workflow is 100% done
    return {"workflow_result": result}
```

### Alternative: `.stream()` for Progress Updates

**For Future Enhancement (not for POC):**
```python
# Non-blocking streaming
for chunk in workflow.stream(input, stream_mode="updates"):
    # Get progress updates as workflow executes
    yield f"Progress: {chunk}"
```

### Async Alternative: `.ainvoke()`

**For asynchronous execution:**
```python
# Non-blocking async
result = await compiled_graph.ainvoke(input)
```

**For POC:** Use blocking `.invoke()` - simpler and proves the core pattern

---

## 3. State Management Across Graphs

### Official Documentation
- **Primary Resource:** https://docs.langchain.com/oss/python/langgraph/use-subgraphs (state transformation section)

### Core Principle

**Parent Graph State ≠ Workflow Graph State**

Each graph (parent and subgraph) has its own independent state schema defined via TypedDict.

### State Transformation at Boundaries

**The Critical Pattern:**
```python
# Orchestrator State
class OrchestratorState(TypedDict):
    user_query: str
    selected_workflow: str
    workflow_result: dict
    final_response: str

# Workflow State (completely different!)
class SQLWorkflowState(TypedDict):
    input_query: str
    table_schemas: list[dict]
    generated_sql: str
    execution_time: float

# Transform at boundary
def invoke_workflow_node(state: OrchestratorState):
    workflow = registry["sql_generation"]

    # TRANSFORM: Orchestrator → Workflow
    workflow_input = {
        "input_query": state["user_query"],  # Map field
        "table_schemas": [],  # Initialize
        "generated_sql": "",  # Initialize
        "execution_time": 0.0
    }

    # Invoke
    workflow_result = workflow.invoke(workflow_input)

    # TRANSFORM: Workflow → Orchestrator
    return {
        "workflow_result": {
            "success": True,
            "sql": workflow_result["generated_sql"],
            "tables_used": len(workflow_result["table_schemas"]),
            "time": workflow_result["execution_time"]
        }
    }
```

### Transformation Responsibilities

**Node Function Must:**
1. Extract relevant data from parent state
2. Build complete subgraph input (all required fields)
3. Invoke subgraph
4. Extract relevant data from subgraph result
5. Build parent state update

**Subgraph:**
- Completely unaware of parent state structure
- Only knows its own state schema
- True black box

### State Isolation Benefits

**Advantages:**
- ✅ Workflows developed independently
- ✅ No tight coupling between orchestrator and workflows
- ✅ Easy to add/remove workflows
- ✅ Workflows can be tested in isolation
- ✅ Clear contracts via structured input/output

---

## 4. Multi-Agent Patterns in LangGraph

### Official Documentation
- **Supervisor Pattern:** https://langchain-ai.github.io/langgraphjs/tutorials/multi_agent/agent_supervisor/
- **GitHub Example:** https://github.com/langchain-ai/langgraph-supervisor-py

### Pattern 1: Supervisor Pattern

**Architecture:**
```
Supervisor Agent (LLM)
    ↓ (delegates)
    ├─→ Worker Agent 1 (specialized)
    ├─→ Worker Agent 2 (specialized)
    └─→ Worker Agent 3 (specialized)
```

**How It Works:**
1. Supervisor receives task
2. Supervisor uses LLM to decide which worker to assign
3. Worker executes task
4. Worker reports back to supervisor
5. Supervisor decides next step (another worker or finish)

**Implementation Pattern:**
```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Literal

class SupervisorState(TypedDict):
    messages: list[str]
    next_agent: str

def supervisor_node(state: SupervisorState):
    """Supervisor decides which agent to call next"""
    messages = state["messages"]

    # Use LLM to decide
    prompt = f"Given these messages: {messages}\nWhich agent should act next? (worker1, worker2, FINISH)"
    decision = llm.invoke(prompt)

    return {
        "next_agent": decision.strip(),
        "messages": messages + [f"Supervisor: Routing to {decision}"]
    }

def worker1_node(state: SupervisorState):
    """Specialized worker 1"""
    result = llm.invoke(f"Worker 1 processing: {state['messages'][-1]}")
    return {"messages": state["messages"] + [f"Worker1: {result}"]}

def worker2_node(state: SupervisorState):
    """Specialized worker 2"""
    result = llm.invoke(f"Worker 2 processing: {state['messages'][-1]}")
    return {"messages": state["messages"] + [f"Worker2: {result}"]}

def route_supervisor(state: SupervisorState) -> Literal["worker1", "worker2", "end"]:
    """Conditional edge routing"""
    next_agent = state["next_agent"]
    if next_agent == "FINISH":
        return "end"
    elif next_agent == "worker1":
        return "worker1"
    else:
        return "worker2"

# Build graph
builder = StateGraph(SupervisorState)
builder.add_node("supervisor", supervisor_node)
builder.add_node("worker1", worker1_node)
builder.add_node("worker2", worker2_node)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "worker1": "worker1",
        "worker2": "worker2",
        "end": END
    }
)
builder.add_edge("worker1", "supervisor")  # Loop back
builder.add_edge("worker2", "supervisor")  # Loop back

supervisor_workflow = builder.compile()
```

**Key Features:**
- Central coordination by supervisor
- Worker specialization
- Dynamic routing based on LLM decisions
- Loops back to supervisor after each worker

### Pattern 2: Iterative Loop Pattern

**Architecture:**
```
Agent → Process → Condition Check
          ↑           ↓
          └───────(loop)
                    ↓
                  END
```

**Use Case:**
- Refining outputs iteratively
- Retry with improvements
- Multi-step analysis

**Implementation Pattern:**
```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

class IterativeState(TypedDict):
    query: str
    iterations: int
    max_iterations: int
    result: str
    artifacts: list[dict]

def process_node(state: IterativeState):
    """Process and create artifact"""
    iteration = state["iterations"] + 1

    # Call LLM
    result = llm.invoke(f"Iteration {iteration}: {state['query']}")

    # Store artifact
    artifact = {
        "iteration": iteration,
        "content": result,
        "timestamp": "2025-11-13"
    }

    return {
        "iterations": iteration,
        "result": result,
        "artifacts": state["artifacts"] + [artifact]
    }

def should_continue(state: IterativeState) -> str:
    """Decide whether to loop or finish"""
    if state["iterations"] >= state["max_iterations"]:
        return "end"
    else:
        return "continue"

# Build graph with loop
builder = StateGraph(IterativeState)
builder.add_node("process", process_node)

builder.add_edge(START, "process")
builder.add_conditional_edges(
    "process",
    should_continue,
    {
        "continue": "process",  # Loop back to itself
        "end": END
    }
)

iterative_workflow = builder.compile()
```

**Key Features:**
- Conditional edges for looping
- State tracks iteration count
- Artifacts stored in state (list)
- Max iterations prevents infinite loops

### Pattern 3: Simple Single Agent

**Architecture:**
```
START → Agent (LLM) → END
```

**Use Case:**
- Simple query processing
- Single-step operations
- Basic transformations

**Implementation Pattern:**
```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

class SimpleState(TypedDict):
    input: str
    output: str

def agent_node(state: SimpleState):
    """Single agent processing"""
    result = llm.invoke(state["input"])
    return {"output": result}

# Build simple graph
builder = StateGraph(SimpleState)
builder.add_node("agent", agent_node)
builder.add_edge(START, "agent")
builder.add_edge("agent", END)

simple_workflow = builder.compile()
```

### Conditional Edges for Dynamic Routing

**Core Pattern:**
```python
# Add conditional edge
builder.add_conditional_edges(
    "source_node",           # From this node
    routing_function,        # Function that returns next node name
    {                        # Mapping of return values to nodes
        "option1": "node_a",
        "option2": "node_b",
        "finish": END
    }
)

def routing_function(state: State) -> str:
    """Returns the name of the next node"""
    if state["condition"]:
        return "option1"
    else:
        return "option2"
```

---

## 5. Key Insights for POC

### What We Know Works

1. **Both orchestrator AND workflows are LangGraphs**
   - Consistent pattern throughout
   - All compiled with `.compile()`
   - All invoked with `.invoke()`

2. **Blocking `.invoke()` works perfectly for our POC**
   - Orchestrator waits at `.invoke()` call
   - Workflow runs to completion (all agents, all loops)
   - Returns structured result
   - Simple and proves the pattern

3. **State transformation is explicit and clean**
   - Transform at node function boundaries
   - Each graph has independent schema
   - No magic, no coupling

4. **Workflows can be stored in Python dict**
   ```python
   WORKFLOW_REGISTRY = {
       "simple": workflow_a.compiled_graph,
       "supervisor": workflow_b.compiled_graph,
       "iterative": workflow_c.compiled_graph
   }

   # Dynamic invocation
   workflow = WORKFLOW_REGISTRY[workflow_name]
   result = workflow.invoke(input)
   ```

5. **Structured contracts work for communication**
   - Define clear input/output schemas
   - Workflows follow the contract
   - Orchestrator knows what to expect

### Architecture Validation

The pattern we want to prove:
```
User Query → Main Orchestrator (LangGraph)
    ↓ intent detection node
    ↓ workflow selection node
    ↓ workflow invocation node (BLOCKS)
    ↓
Workflow (Complete LangGraph - black box)
    ↓ (executes autonomously)
    ↓ (returns structured result)
    ↓
Main Orchestrator
    ↓ response formatting node
```

**Is fully supported by LangGraph!** ✅

### Limitations Discovered

1. **Blocking execution only**
   - For POC this is fine
   - Future: can use `.stream()` for progress updates

2. **State transformation is manual**
   - Must write explicit transformation code
   - No automatic mapping
   - This is actually a feature (explicit > implicit)

3. **No built-in workflow registry**
   - Must build our own (simple Python dict)
   - This gives us flexibility

---

## 6. Questions Answered

### Q1: Can compiled LangGraphs be stored in a Python dict and invoked dynamically?
**A:** ✅ YES - Compiled graphs are runnable objects that can be stored anywhere (dict, list, class attributes) and invoked multiple times.

### Q2: Does blocking `.invoke()` work correctly (waits for completion)?
**A:** ✅ YES - `.invoke()` is explicitly documented as synchronous/blocking execution. It waits for the entire graph to complete before returning.

### Q3: Does state transformation between graphs work cleanly?
**A:** ✅ YES - State transformation is done explicitly in wrapper functions. Clean, predictable, and flexible.

### Q4: Can supervisor patterns work as subgraphs?
**A:** ✅ YES - Any LangGraph (including supervisor patterns) can be compiled and invoked from another graph.

### Q5: Can iterative workflows work as subgraphs?
**A:** ✅ YES - Conditional edges enable loops. Compiled iterative graphs work as black boxes to the parent.

### Q6: Are structured contracts sufficient for communication?
**A:** ✅ YES - TypedDict schemas provide clear contracts. Transformation functions enforce the contracts at boundaries.

---

## 7. Implementation Plan

### Phase 1: Build Workflows (Bottom-Up)

**Workflow A - Simple Agent**
- Single LLM call
- Basic state schema
- Proves basic invoke pattern

**Workflow B - Supervisor Pattern**
- Supervisor + 2 workers
- All calling Claude
- Conditional routing
- Proves multi-agent pattern

**Workflow C - Iterative Loop**
- Agent loops 2-3 times
- Artifacts in state (list)
- Conditional edges for loop
- Proves complex iterative pattern

### Phase 2: Build Orchestrator (Top-Down)

**Orchestrator Nodes:**
1. **Intent Detection** - LLM classifies query
2. **Workflow Invocation** - Gets workflow from registry, invokes with state transformation
3. **Response Formatting** - Explains result to user

**State Schema:**
```python
class OrchestratorState(TypedDict):
    user_query: str
    detected_intent: str
    workflow_result: dict
    final_response: str
```

**Registry:**
```python
WORKFLOW_REGISTRY = {
    "simple": workflow_a.workflow_graph,
    "supervisor": workflow_b.workflow_graph,
    "iterative": workflow_c.workflow_graph
}
```

### Phase 3: Testing via LangGraph Dev Server

**Setup `langgraph.json`:**
```json
{
  "dependencies": ["."],
  "graphs": {
    "orchestrator": "./core/orchestrator.py:orchestrator_graph",
    "workflow_a": "./workflows/workflow_a.py:workflow_graph",
    "workflow_b": "./workflows/workflow_b.py:workflow_graph",
    "workflow_c": "./workflows/workflow_c.py:workflow_graph"
  },
  "env": ".env"
}
```

**Run:** `langgraph dev`
**Test:** http://localhost:2024/docs (Swagger UI)

---

## 8. Documentation URLs

### Official LangGraph Documentation
- **Subgraphs Guide:** https://docs.langchain.com/oss/python/langgraph/use-subgraphs
- **Hierarchical Teams Tutorial:** https://langchain-ai.github.io/langgraph/tutorials/multi_agent/hierarchical_agent_teams/
- **Graph API Reference:** https://reference.langchain.com/python/langgraph/graphs/
- **Supervisor Pattern (JS):** https://langchain-ai.github.io/langgraphjs/tutorials/multi_agent/agent_supervisor/
- **GitHub Supervisor Example:** https://github.com/langchain-ai/langgraph-supervisor-py

### Additional Resources
- **Conditional Edges Tutorial:** https://dev.to/jamesli/advanced-langgraph-implementing-conditional-edges-and-tool-calling-agents-3pdn
- **LangGraph Blog:** https://blog.langchain.com/langgraph-multi-agent-workflows/

---

## 9. Next Steps

1. ✅ Research complete
2. → Create project structure
3. → Set up dependencies (requirements.txt, .env)
4. → Build Workflow A and test independently
5. → Build Workflow B and test independently
6. → Build Workflow C and test independently
7. → Build Orchestrator
8. → Integration testing via dev server
9. → Document findings and limitations

---

**Research Phase: COMPLETE** ✅

All core concepts understood. Ready to implement POC.

# LangGraph Builder Skill

You are an expert LangGraph and LangChain developer building production-grade multi-agent systems.

## Core Expertise

### LangGraph Patterns
- **State Management**: TypedDict schemas, state updates, reducers
- **Graph Construction**: StateGraph, MessageGraph, nodes, edges, conditional routing
- **Multi-Agent Patterns**: Supervisor, hierarchical teams, map-reduce, plan-and-execute
- **Subgraphs**: Composing graphs, state transformation at boundaries
- **Execution**: Blocking (.invoke()), streaming (.stream()), async (.ainvoke())
- **Checkpointing**: State persistence, resume from failures
- **Human-in-the-Loop**: Interrupts, approval gates, feedback loops

### LangChain Integration
- **Chat Models**: ChatAnthropic, ChatOpenAI, proper prompting
- **Tools**: Function calling, tool schemas, error handling
- **Memory**: Conversation history, context windows
- **Chains**: Sequential, parallel, routing chains
- **Retrievers**: Vector stores, semantic search, RAG patterns

## Development Guidelines

### 1. State Schema Design
```python
from typing import TypedDict, Annotated
from operator import add

class AgentState(TypedDict):
    # Use descriptive names
    user_query: str
    messages: Annotated[list[str], add]  # Reducer for append
    context: dict[str, any]

    # Metadata
    workflow_id: str
    execution_time: float
```

**Best Practices:**
- Use TypedDict for type safety
- Add Annotated with reducers for list/dict merging
- Include metadata fields (workflow_id, timestamps, etc.)
- Document each field

### 2. Node Function Pattern
```python
def process_node(state: AgentState) -> dict:
    """
    Clear docstring explaining what this node does.

    Args:
        state: Current agent state

    Returns:
        dict: State updates (only changed fields)
    """
    try:
        # Business logic here
        result = perform_task(state["user_query"])

        return {
            "messages": [f"Completed: {result}"],
            "context": {"last_result": result}
        }
    except Exception as e:
        # Always handle errors
        logger.error(f"Node failed: {e}")
        return {
            "messages": [f"Error: {str(e)}"],
            "context": {"error": str(e)}
        }
```

**Best Practices:**
- Return dict with only updated fields
- Always include try/except
- Log errors with context
- Add type hints
- Clear docstrings

### 3. Graph Construction
```python
from langgraph.graph import StateGraph, START, END

# Initialize
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("process", process_node)
builder.add_node("validate", validate_node)

# Add edges
builder.add_edge(START, "process")

# Conditional routing
def should_validate(state: AgentState) -> str:
    return "validate" if state.get("needs_validation") else "end"

builder.add_conditional_edges(
    "process",
    should_validate,
    {"validate": "validate", "end": END}
)

builder.add_edge("validate", END)

# Compile with checkpointing
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

**Best Practices:**
- Use descriptive node names
- Add comments for complex routing
- Always compile before use
- Add checkpointing for production
- Test conditional routing logic

### 4. Subgraph Pattern
```python
# Subgraph with different state
class SubgraphState(TypedDict):
    input: str
    output: str

# Build subgraph
subgraph_builder = StateGraph(SubgraphState)
subgraph_builder.add_node("process", subgraph_node)
subgraph_builder.add_edge(START, "process")
subgraph_builder.add_edge("process", END)
subgraph = subgraph_builder.compile()

# Invoke from parent node
def invoke_subgraph_node(state: ParentState) -> dict:
    """Transform state and invoke subgraph"""
    # Transform: parent → subgraph
    subgraph_input = {
        "input": state["user_query"],
        "output": ""
    }

    # BLOCKING invoke
    result = subgraph.invoke(subgraph_input)

    # Transform: subgraph → parent
    return {
        "result": result["output"],
        "metadata": {"subgraph_completed": True}
    }
```

**Best Practices:**
- State schemas can be completely different
- Explicit transformation at boundaries
- Subgraphs are black boxes
- Document input/output contracts

### 5. Supervisor Pattern
```python
class SupervisorState(TypedDict):
    messages: list[str]
    next_agent: str

def supervisor(state: SupervisorState) -> dict:
    """Supervisor decides which worker to call"""
    context = "\n".join(state["messages"])

    prompt = f"""Based on: {context}
    Which agent should act next?
    Options: researcher, analyst, FINISH"""

    decision = llm.invoke(prompt).content.strip()

    return {
        "next_agent": decision,
        "messages": state["messages"] + [f"Routing to {decision}"]
    }

def route_supervisor(state: SupervisorState) -> str:
    """Conditional routing"""
    if state["next_agent"] == "FINISH":
        return "end"
    return state["next_agent"]

# Build graph
builder.add_node("supervisor", supervisor)
builder.add_node("researcher", researcher_node)
builder.add_node("analyst", analyst_node)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "researcher": "researcher",
        "analyst": "analyst",
        "end": END
    }
)

# Workers loop back to supervisor
builder.add_edge("researcher", "supervisor")
builder.add_edge("analyst", "supervisor")
```

### 6. Error Handling
```python
class AgentState(TypedDict):
    error: str | None
    retry_count: int

def resilient_node(state: AgentState) -> dict:
    """Node with retry logic"""
    max_retries = 3
    retry_count = state.get("retry_count", 0)

    try:
        result = risky_operation()
        return {
            "result": result,
            "error": None,
            "retry_count": 0
        }
    except RetryableError as e:
        if retry_count < max_retries:
            logger.warning(f"Retry {retry_count + 1}/{max_retries}")
            return {
                "retry_count": retry_count + 1,
                "error": str(e)
            }
        else:
            logger.error(f"Max retries exceeded: {e}")
            return {
                "error": f"Failed after {max_retries} retries",
                "retry_count": retry_count
            }
```

### 7. Streaming Pattern
```python
# For progress updates
async def run_with_streaming():
    async for chunk in graph.astream(
        {"query": "question"},
        stream_mode="updates"
    ):
        print(f"Update: {chunk}")
        yield chunk
```

### 8. Testing Patterns
```python
def test_workflow():
    """Test workflow execution"""
    # Arrange
    test_input = {
        "user_query": "test",
        "messages": []
    }

    # Act
    result = workflow_graph.invoke(test_input)

    # Assert
    assert "error" not in result
    assert result["messages"]
    assert len(result["messages"]) > 0
```

## Common Patterns Reference

### Iterative Loop
```python
def should_continue(state: State) -> str:
    if state["iterations"] >= state["max_iterations"]:
        return "end"
    return "continue"

builder.add_conditional_edges(
    "process",
    should_continue,
    {"continue": "process", "end": END}
)
```

### Map-Reduce
```python
# Map phase: parallel processing
def map_node(state: State) -> dict:
    tasks = state["tasks"]
    results = parallel_process(tasks)
    return {"partial_results": results}

# Reduce phase: combine results
def reduce_node(state: State) -> dict:
    final = combine(state["partial_results"])
    return {"final_result": final}
```

### Human-in-the-Loop
```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["approval_node"]
)

# Run until interrupt
result = graph.invoke(input, config={"configurable": {"thread_id": "123"}})

# Resume after human approval
graph.invoke(None, config={"configurable": {"thread_id": "123"}})
```

## Production Checklist

When building workflows, ensure:

- [ ] **Type Safety**: All states use TypedDict
- [ ] **Error Handling**: Try/except in all nodes
- [ ] **Logging**: Structured logging with context
- [ ] **Validation**: Input validation at entry points
- [ ] **Testing**: Unit tests for nodes, integration for graphs
- [ ] **Documentation**: Docstrings for all functions
- [ ] **Checkpointing**: State persistence for long-running tasks
- [ ] **Monitoring**: Metrics for execution time, success rate
- [ ] **Retry Logic**: Exponential backoff for transient failures
- [ ] **Timeouts**: Prevent infinite loops

## Code Quality Standards

```python
# GOOD: Clear, typed, documented
def process_data(state: DataState) -> dict:
    """
    Process incoming data and validate format.

    Args:
        state: Current workflow state

    Returns:
        dict: Updated state with processed data

    Raises:
        ValidationError: If data format is invalid
    """
    try:
        validated = validate_schema(state["data"])
        processed = transform(validated)

        logger.info(
            "Data processed successfully",
            extra={"record_count": len(processed)}
        )

        return {
            "processed_data": processed,
            "status": "success"
        }
    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        raise
```

## When to Use What

**Simple Agent**: Single LLM call, no coordination needed
**Supervisor**: Multiple specialists, dynamic routing
**Sequential**: Fixed pipeline, step-by-step
**Iterative**: Refinement loops, progressive improvement
**Hierarchical**: Teams of teams, complex coordination
**Map-Reduce**: Parallel processing, aggregation

## Anti-Patterns to Avoid

❌ **Don't**: Modify compiled graphs
✅ **Do**: Compile once, invoke many times

❌ **Don't**: Share state objects between graphs
✅ **Do**: Transform at boundaries

❌ **Don't**: Use global variables for state
✅ **Do**: Pass state through graph

❌ **Don't**: Ignore errors
✅ **Do**: Handle and log all exceptions

❌ **Don't**: Hard-code LLM calls in nodes
✅ **Do**: Inject dependencies, use config

## Resources

- Official Docs: https://langchain-ai.github.io/langgraph/
- Examples: https://github.com/langchain-ai/langgraph/tree/main/examples
- Tutorials: https://langchain-ai.github.io/langgraph/tutorials/

---

**Use this knowledge to build robust, production-grade LangGraph workflows.**

# DataOps Agent - System Architecture

**Version:** 1.0  
**Last Updated:** November 2025  
**Purpose:** Architecture reference for intelligent multi-agent data engineering system

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Architecture Principles](#core-architecture-principles)
3. [Component Definitions](#component-definitions)
4. [Communication Patterns](#communication-patterns)
5. [Dynamic Capability Discovery](#dynamic-capability-discovery)
6. [State Management](#state-management)
7. [Design Decisions](#design-decisions)
8. [Structured Contracts](#structured-contracts)
9. [Development Guidelines](#development-guidelines)

---

## System Overview

### What We're Building

An intelligent multi-agent system for data engineering workflows at The Hartford Insurance Company. The system enables:

- **Dynamic workflow composition**: Add new workflows without changing orchestrator
- **Specialist agents**: Each workflow is a complete multi-agent system solving one specific problem
- **Self-awareness**: System can explain its capabilities to users
- **Loose coupling**: Workflows are independent, communicate via contracts
- **Developer-friendly**: Easy to add new workflows using base utilities

### Primary Use Cases

- Legacy system modernization (Informatica → Snowflake)
- Autosys JIL file dependency analysis
- Code conversion and migration
- Data lineage tracing
- Schema analysis and SQL generation

---

## Core Architecture Principles

### 1. Loose Coupling

**Base classes provide minimal interfaces, not prescriptive patterns.**

```python
# ✅ Correct: Minimal interface
class BaseWorkflow(ABC):
    @abstractmethod
    def get_metadata(self) -> WorkflowMetadata:
        """Declare capabilities - HOW you implement is your choice"""
        
    @abstractmethod
    def get_compiled_graph(self) -> CompiledGraph:
        """Return your graph - build it however you want"""

# ❌ Wrong: Prescriptive pattern
class BaseWorkflow(ABC):
    @abstractmethod
    def build_supervisor_pattern(self):  # ← Too prescriptive!
        """Forces all workflows to use supervisor pattern"""
```

**Why:** Workflows solve different problems requiring different architectures. Don't force patterns.

### 2. Infrastructure Over Patterns

**Provide utilities that abstract complexity, not architectural patterns.**

```python
# ✅ Provide: S3 utility helpers
class S3Operations:
    def upload_file(self, path, key): ...
    def download_file(self, key, path): ...
    def read_json(self, key) -> dict: ...

# ✅ Workflow uses helpers however needed
class JILParserWorkflow:
    def some_node(self, state):
        # Developer decides: loop? supervisor? sequential?
        content = self.s3.read_file(state["file_path"])
        # Their architecture, their choice
```

**Why:** Different workflows need different patterns. Provide tools, not templates.

### 3. Dynamic Capability Discovery

**Workflows declare capabilities; orchestrator discovers them automatically.**

```python
# Workflow declares what it can do
def get_metadata(self):
    return WorkflowMetadata(
        name="jil_parser",
        description="Analyzes Autosys JIL files",
        capabilities=["Parse JIL", "Identify dependencies"],
        example_queries=["Parse JIL file for BATCH_JOB"]
    )

# Registry auto-discovers on startup
# Orchestrator knows capabilities without manual configuration
```

**Why:** Adding new workflows shouldn't require orchestrator changes.

### 4. Workflows as Complete Systems

**Each workflow is a full multi-agent LangGraph, not a pattern or template.**

```python
# Workflow = Complete compiled LangGraph
jil_parser_workflow = StateGraph(JILState)
jil_parser_workflow.add_node("root_agent", root_agent_node)
jil_parser_workflow.add_node("loop_agent", loop_agent_node)
jil_parser_workflow.add_conditional_edges(...)
compiled_workflow = jil_parser_workflow.compile()  # ← This is what gets registered

# Orchestrator invokes it as a black box
result = compiled_workflow.invoke(input)  # ← Blocks until complete
```

**Why:** Workflows are specialist systems with complex internal logic. Orchestrator doesn't need to know internals.

### 5. Blocking Execution (For Now)

**Orchestrator waits for workflow to complete using `.invoke()`**

```python
def workflow_invocation_node(state):
    workflow = registry.get(state["workflow_name"])
    
    # BLOCKS here until workflow fully completes
    # (all agents done, all loops finished, END reached)
    result = workflow.invoke(state["input"])
    
    # Only continues when workflow returns
    return {"workflow_result": result}
```

**Future:** Will add streaming with `.stream()` for progress updates, but POC uses blocking.

**Why:** Simpler for POC, proves pattern, easier to reason about. Streaming is enhancement.

### 6. Structured Contracts

**Workflows communicate via predefined response formats.**

```python
# Every workflow MUST return this structure
{
    "success": bool,
    "result": str | dict,
    "metadata": {
        "workflow_name": str,
        "execution_time": float,
        "iterations": int
    },
    "artifacts": [list],
    "errors": [list] | None
}
```

**Why:** Orchestrator can handle any workflow that follows the contract. No tight coupling.

---

## Component Definitions

### Main Orchestrator

**Type:** LangGraph (compiled graph)

**Purpose:** User-facing agent that routes queries to specialist workflows

**Structure:**
```
START
  ↓
Intent Detection Node (LLM determines workflow OR meta-query)
  ↓
[Conditional Edge: meta vs workflow]
  ↓                    ↓
Meta Query Handler    Workflow Invocation Node (blocks on .invoke())
  ↓                    ↓
  └──────→ Response Formatting Node
             ↓
            END
```

**Responsibilities:**
- Detect user intent (which workflow to use)
- Handle meta-queries ("What can you do?")
- Invoke selected workflow and wait for completion
- Format and explain results to user
- Does NOT know workflow internals

**State Schema:**
```python
class OrchestratorState(TypedDict):
    user_query: str
    detected_intent: str
    selected_workflow: str
    workflow_result: dict
    final_response: str
```

### Workflows

**Type:** Complete multi-agent LangGraph systems (compiled graphs)

**Purpose:** Specialist systems that solve specific data engineering problems

**Examples:**
- **JIL Parser**: Analyzes Autosys JIL files, identifies dependencies, traces lineage
- **Informatica Converter**: Converts Informatica workflows to Snowflake
- **SQL Generator**: Analyzes schemas and generates SQL queries
- **Schema Analyzer**: Profiles database schemas and suggests optimizations

**Each workflow:**
- Is a complete LangGraph with multiple agents
- Can use any architecture (supervisor, iterative, sequential, custom)
- Has its own state schema
- Returns structured response following contract
- Developed and tested independently
- Loaded into orchestrator as compiled graph

**Workflow Freedom:**
- Use supervisor pattern? ✅ Your choice
- Use loops and iterations? ✅ Your choice  
- Sequential agent chain? ✅ Your choice
- Custom architecture? ✅ Your choice

**Example Structures:**

**JIL Parser (Iterative):**
```
START → Root Agent → Loop Agent ⟲ (checks artifacts, continues or exits) → Finalize → END
```

**SQL Generator (Sequential):**
```
START → Schema Fetcher → Analyzer Agent → SQL Generator → Validator → END
```

**Informatica Converter (Supervisor):**
```
START → Supervisor → [Parser Agent, Converter Agent, Validator Agent] → Supervisor → END
```

### Workflow Registry

**Type:** Python class with auto-discovery

**Purpose:** Discovers, stores, and provides access to all workflows

**Key Methods:**
```python
class WorkflowRegistry:
    def discover_workflows(self) -> Dict[str, CompiledGraph]:
        """Scan workflows/ directory, import, register"""
        
    def get_workflow(self, name: str) -> CompiledGraph:
        """Get compiled workflow graph"""
        
    def get_capabilities_context(self) -> str:
        """Generate capability description for LLM"""
        
    def list_workflows(self) -> List[str]:
        """List all registered workflow names"""
```

**Storage:** In-memory dict for POC, will migrate to database for production

**Discovery Process:**
1. Scan `workflows/` directory
2. Import each workflow module
3. Call `get_metadata()` to get capabilities
4. Call `get_compiled_graph()` to get graph
5. Store in registry with metadata

### Base Classes

**Purpose:** Provide reusable utilities, NOT prescribe patterns

#### BaseWorkflow (Minimal Interface)
```python
class BaseWorkflow(ABC):
    """Minimal contract - workflows have complete freedom"""
    
    @abstractmethod
    def get_metadata(self) -> WorkflowMetadata:
        """Return workflow capabilities for discovery"""
        
    @abstractmethod
    def get_compiled_graph(self) -> CompiledGraph:
        """Return your compiled LangGraph"""
```

**That's it.** No `build_graph()`, no `prepare_input()`, no pattern prescription.

#### Infrastructure Utilities

**S3Operations:**
```python
class S3Operations:
    """Common S3 operations - use what you need"""
    def upload_file(self, local_path, s3_key): ...
    def download_file(self, s3_key, local_path): ...
    def read_text(self, s3_key) -> str: ...
    def write_json(self, s3_key, data): ...
    def list_objects(self, prefix) -> List[str]: ...
```

**DynamoDBOperations:**
```python
class DynamoDBOperations:
    """Common DynamoDB operations"""
    def put_item(self, table, item): ...
    def get_item(self, table, key): ...
    def query(self, table, key_condition): ...
```

**BedrockClient:**
```python
class BedrockClient:
    """Simplified Bedrock API access"""
    def invoke(self, prompt, model="claude-sonnet-4"): ...
    def stream(self, prompt): ...
```

---

## Communication Patterns

### 1. Orchestrator → Workflow

**Pattern:** Blocking invocation

```python
# Orchestrator node
def workflow_invocation_node(state):
    workflow = registry.get(state["workflow_name"])
    
    # Transform orchestrator state → workflow input
    workflow_input = {
        "input": state["user_query"],
        "context": state.get("context", {})
    }
    
    # INVOKE AND WAIT
    result = workflow.invoke(workflow_input)
    
    # Transform workflow result → orchestrator state
    return {"workflow_result": result}
```

**Key Points:**
- `.invoke()` is synchronous and blocking
- Orchestrator waits until workflow reaches END state
- State transformation at boundary
- Workflow is black box to orchestrator

### 2. Workflow → Orchestrator (Response)

**Pattern:** Structured contract

```python
# Every workflow returns this format
{
    "success": True,
    "result": {
        "dependencies": [...],
        "analysis": "..."
    },
    "metadata": {
        "workflow_name": "jil_parser",
        "execution_time": 45.2,
        "iterations": 3
    },
    "artifacts": ["artifact_id_1", "artifact_id_2"],
    "errors": None
}
```

### 3. Agent → Agent (Within Workflow)

**Pattern:** Workflow-specific (developer's choice)

Could be:
- Supervisor coordinates workers
- Sequential chain passes state
- Loop agent iterates with shared state
- Custom pattern

**Orchestrator doesn't care.** This is internal to workflow.

---

## Dynamic Capability Discovery

### How It Works

**1. Workflow Declares Capabilities:**
```python
class JILParserWorkflow(BaseWorkflow):
    def get_metadata(self):
        return WorkflowMetadata(
            name="jil_parser",
            description="Analyzes Autosys JIL files to identify job dependencies",
            capabilities=[
                "Parse JIL file structure",
                "Identify upstream dependencies",
                "Identify downstream dependencies",
                "Trace job lineage"
            ],
            example_queries=[
                "Parse JIL dependencies for BATCH_PROCESSING",
                "What are upstream jobs for DATA_LOAD?",
                "Analyze JIL file and show dependencies"
            ],
            category="migration"
        )
```

**2. Registry Auto-Discovers:**
```python
registry = WorkflowRegistry()
registry.discover_workflows()  # Scans workflows/, imports, registers

# Registry now knows:
# - jil_parser can "Parse JIL file structure"
# - informatica_converter can "Convert Informatica workflows"
# - sql_generator can "Generate SQL queries"
```

**3. Orchestrator Uses Capabilities:**
```python
def intent_detection_node(state):
    # Build context with all capabilities
    capabilities = registry.get_capabilities_context()
    
    prompt = f"""You are a data engineering assistant with these capabilities:

{capabilities}

User query: "{state['user_query']}"

Which workflow should handle this? Return workflow name."""
    
    workflow_name = llm.invoke(prompt)
    return {"selected_workflow": workflow_name}
```

**4. User Can Ask "What can you do?"**
```python
def handle_meta_query(state):
    workflows = registry.list_workflows()
    
    response = "I can help you with:\n\n"
    for name in workflows:
        metadata = registry.get_metadata(name)
        response += f"• {metadata.description}\n"
        response += f"  Example: {metadata.example_queries[0]}\n\n"
    
    return {"final_response": response}
```

### Adding New Workflow

**Developer Process:**
1. Create `workflows/new_workflow/workflow.py`
2. Implement `BaseWorkflow` interface
3. Define `get_metadata()` with capabilities
4. Build graph using any pattern
5. Return compiled graph from `get_compiled_graph()`

**That's it.** On next startup:
- Registry discovers new workflow
- Orchestrator knows new capabilities
- User can use it immediately

**No orchestrator changes. No manual configuration.**

---

## State Management

### State Schemas Are Independent

**Orchestrator State:**
```python
class OrchestratorState(TypedDict):
    user_query: str
    detected_intent: str
    selected_workflow: str
    workflow_result: dict
    final_response: str
```

**JIL Parser State (Different!):**
```python
class JILParserState(TypedDict):
    file_path: str
    current_job: str
    dependencies: List[Dict]
    visited_files: List[str]
    artifacts: List[str]
    iteration_count: int
```

**SQL Generator State (Also Different!):**
```python
class SQLGeneratorState(TypedDict):
    table_names: List[str]
    schemas: Dict[str, Any]
    query_intent: str
    generated_sql: str
```

### State Transformation at Boundaries

```python
def workflow_invocation_node(state):
    workflow = registry.get(state["workflow_name"])
    
    # Orchestrator state → Workflow state
    if state["workflow_name"] == "jil_parser":
        workflow_input = {
            "file_path": extract_file_path(state["user_query"]),
            "current_job": extract_job_name(state["user_query"]),
            "dependencies": [],
            "visited_files": [],
            "artifacts": [],
            "iteration_count": 0
        }
    
    result = workflow.invoke(workflow_input)
    
    # Workflow result → Orchestrator state
    return {
        "workflow_result": {
            "dependencies": result["dependencies"],
            "artifacts": result["artifacts"]
        }
    }
```

---

## Design Decisions

### Why Orchestrator is ALSO a LangGraph

**Benefits:**
- Consistent patterns throughout system
- Orchestrator itself is composable (could be invoked by another graph)
- Built-in state management
- Easy to add nodes (logging, monitoring, approval gates)
- Uses same primitives as workflows

**Alternative Considered:** Make orchestrator a simple Python class

**Rejected Because:** Less composable, different paradigm from workflows, harder to add features later

### Why Blocking `.invoke()` for Now

**Current Approach:**
```python
result = workflow.invoke(input)  # Blocks until workflow completes
```

**Future Enhancement:**
```python
for update in workflow.stream(input, stream_mode="updates"):
    yield f"Progress: {update['node']} completed"
```

**Why Start Simple:** Proves pattern, easier to reason about, sufficient for POC

**When to Add Streaming:** When users need progress visibility for long-running workflows

### Why Minimal BaseWorkflow Interface

**Rejected:** Prescriptive base class with `build_graph()`, `prepare_input()`, `format_output()`

**Chosen:** Minimal interface with just `get_metadata()` and `get_compiled_graph()`

**Reason:** Workflows solve different problems. Some need supervisor pattern, some need loops, some need custom architectures. Don't force patterns.

### Why Auto-Discovery Over Manual Config

**Rejected:** Manual workflow registration in YAML

**Chosen:** Automatic discovery by scanning `workflows/` directory

**Reason:** Reduces boilerplate, eliminates configuration drift, makes adding workflows frictionless

---

## Structured Contracts

### WorkflowMetadata
```python
class WorkflowMetadata(BaseModel):
    name: str
    description: str
    capabilities: List[str]
    example_queries: List[str]
    category: str  # "migration", "analysis", "generation"
    version: str = "1.0.0"
    author: str
    input_schema: Optional[Dict] = None
```

### Workflow Response Contract
```python
class WorkflowResponse(BaseModel):
    success: bool
    result: Union[str, Dict[str, Any]]
    metadata: Dict[str, Any]  # workflow_name, execution_time, iterations
    artifacts: List[str]  # artifact IDs
    errors: Optional[List[str]] = None
```

**Every workflow MUST return this structure.**

### Example Conformant Response
```python
{
    "success": True,
    "result": {
        "dependencies": [
            {"job": "upstream_1", "type": "condition"},
            {"job": "downstream_2", "type": "box"}
        ],
        "lineage_depth": 3
    },
    "metadata": {
        "workflow_name": "jil_parser",
        "execution_time": 12.5,
        "iterations": 2,
        "files_analyzed": 5
    },
    "artifacts": [
        "artifact_jil_deps_abc123",
        "artifact_lineage_map_def456"
    ],
    "errors": None
}
```

---

## Development Guidelines

### For Workflow Developers

**DO:**
- ✅ Use base utilities (S3Operations, BedrockClient, etc.)
- ✅ Choose any architecture that works (supervisor, loop, sequential, custom)
- ✅ Return structured response following contract
- ✅ Test workflow in isolation before integration
- ✅ Document capabilities clearly in metadata
- ✅ Use descriptive node names
- ✅ Handle errors gracefully

**DON'T:**
- ❌ Make assumptions about orchestrator internals
- ❌ Depend on other workflows
- ❌ Skip the response contract
- ❌ Hard-code configuration values
- ❌ Expose internal state to orchestrator

### For Orchestrator Developers

**DO:**
- ✅ Treat workflows as black boxes
- ✅ Use registry for workflow discovery
- ✅ Transform state at boundaries
- ✅ Handle workflow errors gracefully
- ✅ Explain results clearly to users

**DON'T:**
- ❌ Import workflow internals
- ❌ Make assumptions about workflow architecture
- ❌ Skip state transformation
- ❌ Couple to specific workflow implementations

### For Infrastructure Developers

**DO:**
- ✅ Provide simple, reusable utilities
- ✅ Abstract AWS/cloud complexity
- ✅ Document all utility methods
- ✅ Handle errors with clear messages
- ✅ Make utilities optional (workflows can choose what to use)

**DON'T:**
- ❌ Force workflows to use specific utilities
- ❌ Create tightly-coupled dependencies
- ❌ Prescribe architectural patterns
- ❌ Make breaking changes without versioning

---

## Key Architectural Insights

### The Power of Loose Coupling

**Traditional Approach (Tight):**
- Orchestrator knows workflow structure
- Workflows depend on orchestrator API
- Adding workflow requires orchestrator changes
- Pattern changes break everything

**Our Approach (Loose):**
- Orchestrator knows only: workflow name, capabilities, contract
- Workflows are self-contained
- Adding workflow = drop in directory + implement interface
- Internal changes don't affect orchestrator

### Workflows as First-Class Citizens

Each workflow is:
- A complete multi-agent system
- Independently developed and tested
- Deployed as compiled LangGraph
- Black box to orchestrator
- Self-describing via metadata

**This enables:**
- Parallel development by different teams
- Easy A/B testing of approaches
- Workflow versioning
- Gradual migration/replacement

### Infrastructure as Enabler, Not Framework

We provide:
- S3 file operations
- DynamoDB data access
- Bedrock LLM calls
- Common parsing utilities

We DON'T provide:
- Workflow templates
- Enforced patterns
- Rigid structure

**Developers decide:** How to combine utilities, what architecture to use, how to solve their specific problem

---

**This architecture enables rapid development of specialist data engineering agents while maintaining clean separation, reusability, and developer freedom.**
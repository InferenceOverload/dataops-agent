# Extended DataOps Agent Architecture

**Version:** 2.0
**Last Updated:** November 2025
**Purpose:** Complete system architecture for production-grade workflow orchestration platform

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Core Extensions](#core-extensions)
4. [Session Management](#session-management)
5. [Artifact Management](#artifact-management)
6. [Context Management](#context-management)
7. [Workflow Development Kit](#workflow-development-kit)
8. [Enhanced Orchestration](#enhanced-orchestration)
9. [API Layer](#api-layer)
10. [Observability & Monitoring](#observability--monitoring)
11. [Storage Architecture](#storage-architecture)
12. [Security & Access Control](#security--access-control)
13. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

### Current State
- Working orchestrator with intent detection and parameter extraction
- 4 example workflows (simple, supervisor, iterative, JIL parser)
- Basic infrastructure tools (S3, DynamoDB, Bedrock)
- Blocking execution model
- No session persistence
- No cross-workflow context sharing

### Target State
A production-grade workflow orchestration platform that enables:
- **Developer Productivity**: Easy workflow creation with templates and tools
- **Session Continuity**: Persistent conversations with context awareness
- **Artifact Management**: Structured storage and sharing of workflow outputs
- **Context Intelligence**: Smart context dumping and loading between workflows
- **Workflow Chaining**: Complex multi-workflow compositions
- **Production Ready**: API layer, auth, monitoring, and scaling

---

## System Overview

### Extended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          API Gateway                             │
│              (REST + WebSocket + Authentication)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────────┐
│                     Session Manager                              │
│         (User Context, History, Preferences)                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────────┐
│                  Enhanced Orchestrator                           │
│   (Intent, Parameters, Workflow Chaining, Context Management)   │
└───────┬──────────────────────────────────────────┬──────────────┘
        │                                           │
┌───────┴──────────┐                    ┌──────────┴──────────────┐
│ Workflow Registry │                    │  Context Manager        │
│  (Discovery &     │                    │  (Dump/Load/Compress)   │
│   Metadata)       │                    └─────────────────────────┘
└───────┬──────────┘
        │
┌───────┴──────────────────────────────────────────────────────────┐
│                         Workflows                                 │
│    (Simple, Supervisor, Iterative, JIL Parser, Custom...)        │
└──────┬────────────────────────────────────┬──────────────────────┘
       │                                     │
┌──────┴──────────────┐         ┌──────────┴─────────────────────┐
│ Artifact Store      │         │  Infrastructure Tools          │
│ (S3 + Metadata DB)  │         │  (S3, DynamoDB, Bedrock, etc.) │
└─────────────────────┘         └────────────────────────────────┘
```

### Key Design Principles

1. **Backward Compatible**: Existing workflows continue to work
2. **Opt-In Features**: New features are optional enhancements
3. **Minimal Boilerplate**: Reduce developer friction
4. **Horizontally Scalable**: Stateless orchestrator, external state storage
5. **Observable**: Comprehensive logging, metrics, and tracing

---

## Core Extensions

### 1. Session Management

**Purpose**: Track user conversations, maintain context across interactions

**Components**:

```python
# Core Session Model
class Session(BaseModel):
    session_id: str
    user_id: str
    created_at: datetime
    last_active: datetime
    metadata: Dict[str, Any]

    # Context tracking
    conversation_history: List[Message]
    active_workflows: List[str]
    global_context: Dict[str, Any]

    # Preferences
    user_preferences: UserPreferences

    # State
    status: SessionStatus  # active, idle, expired

class Message(BaseModel):
    message_id: str
    timestamp: datetime
    role: str  # user, assistant, system
    content: str
    workflow: Optional[str]
    artifacts: List[str]

class SessionManager:
    """Manages session lifecycle and context"""

    def create_session(self, user_id: str) -> Session:
        """Create new session with initial context"""

    def get_session(self, session_id: str) -> Session:
        """Retrieve session with history"""

    def update_session(self, session_id: str, updates: Dict) -> Session:
        """Update session state"""

    def add_message(self, session_id: str, message: Message):
        """Add message to conversation history"""

    def get_context_summary(self, session_id: str, max_tokens: int) -> str:
        """Get compressed context for LLM"""

    def cleanup_expired_sessions(self):
        """Remove old inactive sessions"""
```

**Storage**:
- **Hot Storage**: Redis for active sessions (fast access)
- **Cold Storage**: DynamoDB for session history
- **Archive**: S3 for long-term conversation logs

**Features**:
- Automatic context summarization
- Conversation memory with relevance scoring
- Session expiration policies
- Multi-turn conversation support
- Context inheritance from previous interactions

---

### 2. Artifact Management

**Purpose**: Centralized storage and retrieval of workflow outputs

**Components**:

```python
class Artifact(BaseModel):
    artifact_id: str
    session_id: str
    workflow_name: str
    artifact_type: str  # result, intermediate, debug, context

    # Content
    content: Union[str, Dict, bytes]
    content_type: str  # json, text, binary, parquet, csv

    # Metadata
    created_at: datetime
    created_by: str  # workflow node
    size_bytes: int

    # Relationships
    parent_artifacts: List[str]
    derived_from: Optional[str]

    # Lifecycle
    ttl: Optional[datetime]  # Auto-delete time
    access_count: int
    last_accessed: datetime

class ArtifactStore:
    """Centralized artifact management"""

    def store_artifact(
        self,
        content: Any,
        metadata: ArtifactMetadata
    ) -> str:
        """Store artifact and return ID"""

    def get_artifact(self, artifact_id: str) -> Artifact:
        """Retrieve artifact by ID"""

    def list_artifacts(
        self,
        session_id: str,
        filters: Optional[Dict] = None
    ) -> List[Artifact]:
        """List artifacts for session"""

    def share_artifact(
        self,
        artifact_id: str,
        target_session: str
    ) -> str:
        """Share artifact across sessions"""

    def link_artifacts(
        self,
        parent_id: str,
        child_id: str
    ):
        """Create lineage relationship"""

    def cleanup_expired_artifacts(self):
        """Remove expired artifacts"""
```

**Storage Architecture**:

```
Artifact Storage
├── Metadata: DynamoDB
│   ├── Primary Key: artifact_id
│   ├── GSI: session_id + created_at
│   └── GSI: workflow_name + created_at
│
└── Content: S3
    ├── Path: s3://{bucket}/artifacts/{session_id}/{artifact_id}
    ├── Lifecycle: Auto-delete after TTL
    └── Versioning: Enabled
```

**Features**:
- Automatic versioning
- Artifact lineage tracking
- Cross-workflow artifact sharing
- Smart TTL policies
- Content type detection
- Compression for large artifacts
- Streaming for large files

---

### 3. Context Management

**Purpose**: Intelligent context dumping, loading, and sharing between workflows

**Components**:

```python
class ContextSnapshot(BaseModel):
    snapshot_id: str
    session_id: str
    created_at: datetime

    # Context data
    orchestrator_state: Dict[str, Any]
    workflow_states: Dict[str, Any]  # keyed by workflow_name

    # Artifacts
    artifact_refs: List[str]

    # Compression
    compressed: bool
    original_size: int
    compressed_size: int

class ContextManager:
    """Manages context snapshots and inheritance"""

    def dump_context(
        self,
        session_id: str,
        include_artifacts: bool = True
    ) -> str:
        """
        Dump current context to storage.
        Returns snapshot_id.
        """

    def load_context(
        self,
        snapshot_id: str,
        merge_strategy: str = "replace"
    ) -> Dict[str, Any]:
        """
        Load context from snapshot.
        merge_strategy: replace, merge, selective
        """

    def compress_context(
        self,
        context: Dict[str, Any],
        max_tokens: int
    ) -> Dict[str, Any]:
        """Use LLM to compress context intelligently"""

    def create_checkpoint(
        self,
        session_id: str,
        label: str
    ) -> str:
        """Create named checkpoint for rollback"""

    def restore_checkpoint(
        self,
        session_id: str,
        checkpoint_id: str
    ):
        """Restore session to checkpoint"""

    def inherit_context(
        self,
        source_session: str,
        target_session: str,
        filters: Optional[List[str]] = None
    ):
        """Copy context from one session to another"""
```

**Context Compression Strategy**:

```python
def compress_context(context: Dict, max_tokens: int) -> Dict:
    """
    Intelligent context compression using LLM:

    1. Identify most relevant information
    2. Summarize verbose sections
    3. Remove redundant data
    4. Keep critical references intact
    5. Maintain artifact pointers
    """

    prompt = f"""
    Compress this context to {max_tokens} tokens while preserving:
    - Key decisions made
    - Important parameter values
    - Critical artifact references
    - Active workflow states

    Context: {json.dumps(context, indent=2)}

    Return compressed context as JSON.
    """

    compressed = llm.invoke(prompt)
    return json.loads(compressed)
```

**Use Cases**:
- **Workflow Handoff**: Pass context from one workflow to another
- **Session Pause/Resume**: Save and restore user sessions
- **Error Recovery**: Checkpoint before risky operations
- **Context Inheritance**: New workflows start with relevant context
- **Long Conversations**: Compress old context, keep recent detailed

---

### 4. Workflow Development Kit

**Purpose**: Accelerate workflow development with tools and templates

**Components**:

#### A. CLI Tool

```bash
# Scaffold new workflow
dataops-workflow create --name my-workflow --template iterative

# Generated structure:
workflows/my_workflow/
├── __init__.py
├── workflow.py          # Main workflow implementation
├── nodes.py             # Node implementations
├── state.py             # State schema
├── config.yaml          # Configuration
├── tests/
│   └── test_workflow.py
└── README.md

# Test workflow in isolation
dataops-workflow test my-workflow --input '{"query": "test"}'

# Validate workflow contract
dataops-workflow validate my-workflow

# Generate documentation
dataops-workflow docs my-workflow

# Package for deployment
dataops-workflow package my-workflow
```

#### B. Workflow Templates

```python
# Template Registry
TEMPLATES = {
    "simple": SimpleWorkflowTemplate,
    "supervisor": SupervisorWorkflowTemplate,
    "iterative": IterativeWorkflowTemplate,
    "sequential": SequentialWorkflowTemplate,
    "parallel": ParallelWorkflowTemplate,
    "conditional": ConditionalWorkflowTemplate,
}

# Template Base
class WorkflowTemplate:
    def scaffold(self, name: str, config: Dict) -> str:
        """Generate workflow from template"""

    def generate_tests(self, workflow: BaseWorkflow):
        """Generate test boilerplate"""

    def generate_docs(self, workflow: BaseWorkflow):
        """Generate documentation"""
```

#### C. Testing Utilities

```python
class WorkflowTestHarness:
    """Test utilities for workflow development"""

    def __init__(self, workflow: BaseWorkflow):
        self.workflow = workflow

    def mock_llm(self, responses: List[str]):
        """Mock LLM responses for testing"""

    def mock_tools(self, tool_responses: Dict[str, Any]):
        """Mock infrastructure tools"""

    def assert_output_format(self, result: Dict):
        """Validate output contract"""

    def trace_execution(self, input_state: Dict) -> ExecutionTrace:
        """Get detailed execution trace"""

    def measure_performance(self, inputs: List[Dict]) -> PerformanceReport:
        """Benchmark workflow"""

# Usage
harness = WorkflowTestHarness(MyWorkflow())
harness.mock_llm(["response1", "response2"])
result = harness.workflow.invoke(test_input)
harness.assert_output_format(result)
```

#### D. Workflow Decorators

```python
from dataops.decorators import (
    with_session_context,
    with_artifacts,
    with_error_recovery,
    with_caching,
    with_telemetry
)

class MyWorkflow(BaseWorkflow):

    @with_session_context  # Auto-inject session context
    @with_artifacts       # Auto-save artifacts
    @with_error_recovery  # Automatic retry and recovery
    @with_telemetry       # Automatic metrics
    def my_node(self, state: MyState) -> Dict:
        """Node with automatic enhancements"""
        # Your logic here
        return {"output": result}
```

---

### 5. Enhanced Orchestration

**Purpose**: Support complex workflow compositions and patterns

**Components**:

#### A. Workflow Chaining

```python
class WorkflowChain:
    """Chain multiple workflows together"""

    def __init__(self):
        self.steps: List[WorkflowStep] = []

    def add_step(
        self,
        workflow_name: str,
        condition: Optional[Callable] = None,
        parameter_mapping: Optional[Dict] = None
    ):
        """Add workflow to chain"""

    def add_parallel(
        self,
        workflow_names: List[str],
        aggregator: Callable
    ):
        """Execute workflows in parallel"""

    def execute(
        self,
        session_id: str,
        initial_input: Dict
    ) -> Dict:
        """Execute workflow chain"""

# Usage
chain = WorkflowChain()
chain.add_step("schema_analyzer")
chain.add_step("sql_generator",
    parameter_mapping=lambda prev: {
        "schema": prev["result"]["schema"]
    }
)
chain.add_step("query_optimizer")
result = chain.execute(session_id, initial_input)
```

#### B. Conditional Execution

```python
class ConditionalOrchestrator:
    """Execute workflows based on conditions"""

    def add_rule(
        self,
        condition: Callable[[Dict], bool],
        workflow: str,
        priority: int = 0
    ):
        """Add conditional workflow rule"""

    def evaluate(self, context: Dict) -> List[str]:
        """Evaluate conditions, return workflows to execute"""

# Usage
orchestrator.add_rule(
    condition=lambda ctx: ctx["data_size"] > 1000000,
    workflow="large_data_processor"
)
orchestrator.add_rule(
    condition=lambda ctx: ctx["data_size"] <= 1000000,
    workflow="small_data_processor"
)
```

#### C. Workflow Dependencies

```python
class WorkflowDependencyGraph:
    """Manage workflow dependencies"""

    def add_dependency(
        self,
        workflow: str,
        depends_on: List[str]
    ):
        """Declare workflow dependencies"""

    def resolve_execution_order(self) -> List[List[str]]:
        """Return workflows grouped by execution level"""

    def execute_with_dependencies(
        self,
        target_workflow: str,
        session_id: str
    ):
        """Execute workflow and all dependencies"""
```

---

### 6. API Layer

**Purpose**: External access and integration

**Components**:

#### A. REST API

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

app = FastAPI(title="DataOps Agent API")

# Session Management
@app.post("/sessions")
async def create_session(user_id: str) -> Session:
    """Create new user session"""

@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> Session:
    """Get session details"""

# Query Processing
@app.post("/sessions/{session_id}/query")
async def process_query(
    session_id: str,
    query: QueryRequest
) -> QueryResponse:
    """Process user query with orchestrator"""

# Workflow Invocation
@app.post("/workflows/{workflow_name}/invoke")
async def invoke_workflow(
    workflow_name: str,
    input_data: Dict,
    session_id: Optional[str] = None
) -> WorkflowResponse:
    """Direct workflow invocation"""

# Artifact Management
@app.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str) -> Artifact:
    """Retrieve artifact"""

@app.get("/sessions/{session_id}/artifacts")
async def list_artifacts(session_id: str) -> List[Artifact]:
    """List session artifacts"""

# Context Management
@app.post("/sessions/{session_id}/context/dump")
async def dump_context(session_id: str) -> ContextSnapshot:
    """Dump session context"""

@app.post("/sessions/{session_id}/context/load")
async def load_context(
    session_id: str,
    snapshot_id: str
) -> Session:
    """Load context snapshot"""
```

#### B. WebSocket Support

```python
from fastapi import WebSocket

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str
):
    """
    WebSocket for streaming workflow execution

    Streams:
    - Progress updates
    - Intermediate results
    - Artifacts as they're created
    - Error messages
    """
    await websocket.accept()

    async for update in workflow.stream(input):
        await websocket.send_json({
            "type": "progress",
            "node": update["node"],
            "data": update["data"]
        })
```

#### C. Authentication & Authorization

```python
from fastapi_users import FastAPIUsers
from fastapi_permissions import Authenticated, Allow

# User model
class User(BaseModel):
    user_id: str
    email: str
    roles: List[str]
    permissions: List[str]

# Permission checks
@app.post("/workflows/{workflow_name}/invoke")
async def invoke_workflow(
    workflow_name: str,
    user: User = Depends(get_current_user)
):
    # Check user has permission for workflow
    if not user.has_permission(f"workflow.{workflow_name}.invoke"):
        raise HTTPException(403, "Insufficient permissions")
```

---

### 7. Observability & Monitoring

**Purpose**: Visibility into system behavior and performance

**Components**:

#### A. Structured Logging

```python
import structlog

logger = structlog.get_logger()

# Automatic context enrichment
logger.info(
    "workflow_invoked",
    workflow_name=workflow_name,
    session_id=session_id,
    user_id=user_id,
    input_size=len(str(input))
)

# Distributed tracing correlation
logger.bind(trace_id=trace_id, span_id=span_id)
```

#### B. Metrics Collection

```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics
workflow_invocations = Counter(
    "workflow_invocations_total",
    "Total workflow invocations",
    ["workflow_name", "status"]
)

workflow_duration = Histogram(
    "workflow_duration_seconds",
    "Workflow execution time",
    ["workflow_name"]
)

active_sessions = Gauge(
    "active_sessions",
    "Number of active sessions"
)
```

#### C. Distributed Tracing

```python
from opentelemetry import trace
from opentelemetry.instrumentation.langchain import LangChainInstrumentor

# Auto-instrument LangChain
LangChainInstrumentor().instrument()

# Custom spans
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("workflow_execution") as span:
    span.set_attribute("workflow.name", workflow_name)
    span.set_attribute("session.id", session_id)

    result = workflow.invoke(input)

    span.set_attribute("workflow.status", "success")
    span.set_attribute("workflow.iterations", result["iterations"])
```

#### D. Health Checks & Dashboards

```python
@app.get("/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "components": {
            "orchestrator": check_orchestrator(),
            "registry": check_registry(),
            "session_store": check_redis(),
            "artifact_store": check_s3(),
            "database": check_dynamodb()
        }
    }
```

---

## Storage Architecture

### Overview

```
Storage Layer
├── Redis (Hot Data)
│   ├── Active sessions
│   ├── Recent context
│   └── Cache
│
├── DynamoDB (Structured Data)
│   ├── Session metadata
│   ├── Artifact metadata
│   ├── User profiles
│   └── Workflow execution logs
│
├── S3 (Blob Storage)
│   ├── Artifacts
│   ├── Context snapshots
│   ├── Conversation archives
│   └── Workflow outputs
│
└── (Optional) PostgreSQL
    ├── User management
    ├── Analytics
    └── Reporting
```

### Data Flow

```
User Query
    ↓
Session Manager (Redis + DynamoDB)
    ↓
Orchestrator (Stateless)
    ↓
Workflow (Stateless)
    ↓
Artifacts → S3
    ↓
Metadata → DynamoDB
    ↓
Response → User
```

---

## Security & Access Control

### Authentication

```python
# JWT-based authentication
class AuthService:
    def authenticate(self, credentials) -> User:
        """Authenticate user, return JWT"""

    def validate_token(self, token: str) -> User:
        """Validate JWT, return user"""

    def refresh_token(self, refresh_token: str) -> str:
        """Refresh expired token"""
```

### Authorization

```python
# Role-based access control (RBAC)
PERMISSIONS = {
    "admin": ["*"],
    "developer": [
        "workflow.*.invoke",
        "workflow.create",
        "artifact.read",
        "artifact.write"
    ],
    "user": [
        "workflow.*.invoke",
        "artifact.read"
    ]
}

# Permission decorator
@require_permission("workflow.{workflow_name}.invoke")
async def invoke_workflow(workflow_name: str, user: User):
    ...
```

### Data Privacy

```python
# Artifact encryption
class EncryptedArtifactStore(ArtifactStore):
    def store_artifact(self, content: Any, metadata: Dict) -> str:
        # Encrypt content before storing
        encrypted = encrypt(content, key=get_user_key())
        return super().store_artifact(encrypted, metadata)
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Session management implementation
- [ ] Artifact store implementation
- [ ] Context manager implementation
- [ ] Basic API layer
- [ ] Testing infrastructure

### Phase 2: Developer Tools (Weeks 3-4)
- [ ] CLI tool for workflow scaffolding
- [ ] Workflow templates
- [ ] Testing utilities
- [ ] Documentation generator
- [ ] Migration guide for existing workflows

### Phase 3: Enhanced Orchestration (Weeks 5-6)
- [ ] Workflow chaining
- [ ] Conditional execution
- [ ] Parallel execution
- [ ] Dependency resolution
- [ ] Streaming support

### Phase 4: Production Features (Weeks 7-8)
- [ ] Authentication & authorization
- [ ] WebSocket support
- [ ] Comprehensive logging
- [ ] Metrics & tracing
- [ ] Health checks & monitoring

### Phase 5: Polish & Scale (Weeks 9-10)
- [ ] Performance optimization
- [ ] Caching strategies
- [ ] Rate limiting
- [ ] Documentation
- [ ] Deployment guides

---

## Next Steps

1. **Review & Prioritize**: Determine which components are most critical
2. **Design Deep Dives**: Detailed design for selected components
3. **Proof of Concept**: Build session manager + artifact store POC
4. **Migration Plan**: Strategy for updating existing workflows
5. **Documentation**: Developer guides and API docs

---

**Questions to Consider:**

1. **Scale**: Expected concurrent users? Workflow execution volume?
2. **Cost**: Budget for AWS services (Redis, DynamoDB, S3)?
3. **Timeline**: Hard deadlines or iterative rollout?
4. **Team**: Who will develop? Who will maintain?
5. **Integration**: Existing systems to integrate with?
6. **Compliance**: Data residency, audit requirements?

---

**This architecture provides a clear path from current state to production-grade platform while maintaining flexibility and developer experience.**

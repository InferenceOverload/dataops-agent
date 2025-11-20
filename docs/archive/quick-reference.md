# DataOps Agent - Quick Reference Guide

**Version:** 2.0
**Purpose:** Quick reference for extended system features

---

## Architecture Overview

```
API Gateway → Session Manager → Enhanced Orchestrator → Workflows
                     ↓                    ↓                  ↓
              [Redis/DynamoDB]    [Context Manager]   [Artifact Store]
```

---

## Core Components

### 1. Session Management

```python
from core.session_manager import SessionManager

# Create session
session_manager = SessionManager()
session = session_manager.create_session(user_id="user123")

# Add message
session_manager.add_message(
    session.session_id,
    role="user",
    content="Hello"
)

# Get context
context = session_manager.get_context_summary(session.session_id)
```

### 2. Artifact Management

```python
from core.artifact_store import ArtifactStore, ArtifactType

# Store artifact
artifact_store = ArtifactStore()
artifact_id = artifact_store.store_artifact(
    content={"result": "data"},
    session_id=session_id,
    workflow_name="my_workflow",
    artifact_type=ArtifactType.RESULT
)

# Retrieve artifact
artifact = artifact_store.get_artifact(artifact_id)
content = artifact_store.get_artifact_content(artifact_id)

# List artifacts
artifacts = artifact_store.list_artifacts(session_id)

# Share artifact
shared_id = artifact_store.share_artifact(artifact_id, target_session)
```

### 3. Context Management

```python
from core.context_manager import ContextManager

context_manager = ContextManager(session_manager, artifact_store)

# Dump context
snapshot_id = context_manager.dump_context(
    session_id,
    include_artifacts=True,
    compress=True
)

# Load context
context = context_manager.load_context(snapshot_id)

# Create checkpoint
checkpoint_id = context_manager.create_checkpoint(
    session_id,
    label="before_migration"
)

# Restore checkpoint
context_manager.restore_checkpoint(session_id, "before_migration")

# Compress context with LLM
compressed = context_manager.compress_context(
    context,
    max_tokens=2000
)
```

---

## Workflow Development

### Using Decorators

```python
from core.decorators import (
    with_artifacts,
    with_session_context,
    with_error_recovery
)
from core.artifact import ArtifactType

class MyWorkflow(BaseWorkflow):

    @with_artifacts(ArtifactType.RESULT)
    @with_session_context
    def my_node(self, state: MyState) -> dict:
        # Automatic artifact saving
        # Session context injected
        return {"output": result}
```

### State Schema

```python
from typing import TypedDict

class MyWorkflowState(TypedDict):
    # Required for session support
    session_id: str
    workflow_name: str

    # Your workflow fields
    input: str
    output: str
    artifacts: list[str]
```

### Metadata with Parameters

```python
from core.base_workflow import WorkflowInputParameter

def get_metadata(self) -> WorkflowMetadata:
    return WorkflowMetadata(
        name="my_workflow",
        description="My workflow description",
        capabilities=["capability 1", "capability 2"],
        example_queries=["Example query"],
        category="analysis",
        required_inputs=[
            WorkflowInputParameter(
                name="file_path",
                description="Path to file",
                type="string",
                required=True,
                example="s3://bucket/file.txt",
                prompt="Please provide the file path"
            )
        ]
    )
```

---

## CLI Commands

### Create Workflow

```bash
# Simple workflow
dataops-workflow create my_analyzer

# From template
dataops-workflow create my_flow --template iterative

# With options
dataops-workflow create analyzer \
  --template supervisor \
  --description "Analyze data" \
  --category analysis
```

### Test Workflow

```bash
# Basic test
dataops-workflow test my_analyzer --input '{"query": "test"}'

# From file
dataops-workflow test my_analyzer --input test.json

# With mocks and trace
dataops-workflow test my_analyzer \
  --input test.json \
  --mock-llm \
  --trace
```

### Validate Workflow

```bash
# Basic validation
dataops-workflow validate my_analyzer

# Strict mode
dataops-workflow validate my_analyzer --strict
```

### Generate Docs

```bash
# Generate markdown
dataops-workflow docs my_analyzer

# With diagrams
dataops-workflow docs my_analyzer --include-diagrams

# HTML output
dataops-workflow docs my_analyzer --format html --output docs/
```

### List Workflows

```bash
# All workflows
dataops-workflow list

# By category
dataops-workflow list --category migration

# Search
dataops-workflow list --search "parser"
```

### Benchmark

```bash
# Basic benchmark
dataops-workflow benchmark my_analyzer --input test.json

# Multiple iterations
dataops-workflow benchmark my_analyzer \
  --input test.json \
  --iterations 100
```

---

## API Endpoints

### Session Management

```http
POST /sessions
GET /sessions/{session_id}
POST /sessions/{session_id}/query
```

### Workflow Invocation

```http
POST /workflows/{workflow_name}/invoke
GET /workflows
GET /workflows/{workflow_name}
```

### Artifact Management

```http
GET /artifacts/{artifact_id}
GET /sessions/{session_id}/artifacts
POST /artifacts/{artifact_id}/share
```

### Context Management

```http
POST /sessions/{session_id}/context/dump
POST /sessions/{session_id}/context/load
POST /sessions/{session_id}/checkpoints
```

---

## Environment Variables

### Required

```bash
# LLM
ANTHROPIC_API_KEY=your_key

# Session Storage
REDIS_HOST=localhost
REDIS_PORT=6379

# Artifact Storage
ARTIFACT_BUCKET=my-bucket
AWS_REGION=us-east-1

# DynamoDB
AWS_DYNAMODB_TABLE=dataops_sessions
```

### Optional

```bash
# Authentication
JWT_SECRET=your_secret
JWT_ALGORITHM=HS256

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Performance
MAX_CONCURRENT_WORKFLOWS=10
WORKFLOW_TIMEOUT=300

# Features
ENABLE_STREAMING=true
ENABLE_CACHING=true
```

---

## Configuration Files

### ~/.dataops/config.yaml

```yaml
defaults:
  template: simple
  author: "Your Name"

testing:
  mock_llm: false
  timeout: 300

deployment:
  registry: "https://registry.example.com"
  default_env: "dev"

aws:
  region: us-east-1
  s3_bucket: my-bucket
```

### workflows/my_workflow/config.yaml

```yaml
name: my_workflow
version: 1.0.0
description: Workflow description

metadata:
  category: analysis
  author: Team Name

parameters:
  - name: input_param
    type: string
    required: true

dependencies:
  - langchain>=0.1.0

resources:
  timeout: 300
  max_memory: 1024
```

---

## Storage Schema

### DynamoDB Tables

**dataops_sessions**:
```
Primary Key: session_id
GSI: user_id + created_at

Attributes:
- session_id
- user_id
- created_at
- last_active
- conversation_history (JSON)
- global_context (JSON)
- status
- metadata (JSON)
```

**dataops_artifacts**:
```
Primary Key: artifact_id
GSI: session_id + created_at
GSI: workflow_name + created_at

Attributes:
- artifact_id
- session_id
- workflow_name
- artifact_type
- s3_key
- content_type
- size_bytes
- created_at
- ttl
```

### S3 Structure

```
s3://bucket/
├── artifacts/
│   └── {session_id}/
│       └── {date}/
│           └── {artifact_id}
├── contexts/
│   └── {session_id}/
│       └── {snapshot_id}
└── archives/
    └── {date}/
        └── {session_id}.json.gz
```

---

## Workflow Patterns

### Simple Agent

```python
graph.add_node("process", process_node)
graph.add_edge(START, "process")
graph.add_edge("process", END)
```

### Supervisor Pattern

```python
graph.add_node("supervisor", supervisor_node)
graph.add_node("worker_1", worker_1_node)
graph.add_node("worker_2", worker_2_node)

graph.add_edge(START, "supervisor")
graph.add_conditional_edges(
    "supervisor",
    route_to_worker,
    {"worker_1": "worker_1", "worker_2": "worker_2", "finish": END}
)
```

### Iterative Pattern

```python
graph.add_node("process", process_node)
graph.add_conditional_edges(
    "process",
    should_continue,
    {"continue": "process", "end": END}
)
graph.add_edge(START, "process")
```

### Sequential Chain

```python
graph.add_node("step_1", step_1_node)
graph.add_node("step_2", step_2_node)
graph.add_node("step_3", step_3_node)

graph.add_edge(START, "step_1")
graph.add_edge("step_1", "step_2")
graph.add_edge("step_2", "step_3")
graph.add_edge("step_3", END)
```

---

## Testing

### Unit Tests

```python
import pytest
from workflows.my_workflow import MyWorkflow

@pytest.fixture
def workflow():
    return MyWorkflow()

def test_metadata(workflow):
    metadata = workflow.get_metadata()
    assert metadata.name == "my_workflow"
    assert len(metadata.capabilities) > 0

def test_execution(workflow):
    graph = workflow.get_compiled_graph()
    result = graph.invoke(test_input)
    assert result["success"] is True
```

### Integration Tests

```python
def test_with_session():
    session = session_manager.create_session("test_user")

    result = orchestrator_graph.invoke({
        "session_id": session.session_id,
        "user_query": "test query"
    })

    assert result["final_response"]

    # Check artifacts created
    artifacts = artifact_store.list_artifacts(session.session_id)
    assert len(artifacts) > 0
```

---

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - REDIS_HOST=redis
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dataops-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dataops-agent
  template:
    metadata:
      labels:
        app: dataops-agent
    spec:
      containers:
      - name: api
        image: dataops-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: dataops-secrets
              key: anthropic-api-key
```

---

## Monitoring

### Metrics

```python
from prometheus_client import Counter, Histogram

workflow_invocations = Counter(
    "workflow_invocations_total",
    "Workflow invocations",
    ["workflow", "status"]
)

workflow_duration = Histogram(
    "workflow_duration_seconds",
    "Workflow duration",
    ["workflow"]
)
```

### Logging

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "workflow_started",
    workflow=workflow_name,
    session_id=session_id,
    user_id=user_id
)
```

### Tracing

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("workflow_execution") as span:
    span.set_attribute("workflow.name", workflow_name)
    result = workflow.invoke(input)
```

---

## Troubleshooting

### Common Issues

**Redis Connection Error**:
```bash
# Check Redis is running
redis-cli ping

# Check connection
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

**S3 Permission Error**:
```bash
# Check bucket access
aws s3 ls s3://your-bucket/

# Check IAM permissions
aws sts get-caller-identity
```

**DynamoDB Not Found**:
```bash
# Create table
aws dynamodb create-table \
  --table-name dataops_sessions \
  --key-schema AttributeName=session_id,KeyType=HASH \
  --attribute-definitions AttributeName=session_id,AttributeType=S \
  --billing-mode PAY_PER_REQUEST
```

**Workflow Not Loading**:
```python
# Check workflow registry
from core.workflow_registry import WORKFLOW_REGISTRY
print(WORKFLOW_REGISTRY.list_workflows())

# Verify workflow structure
dataops-workflow validate my_workflow
```

---

## Performance Tips

1. **Use Redis for Hot Data**: Keep active sessions in Redis
2. **Enable Caching**: Cache LLM responses where appropriate
3. **Compress Context**: Use context compression for long conversations
4. **Set TTLs**: Configure artifact TTLs to manage storage
5. **Batch Operations**: Use batch operations for DynamoDB
6. **Async Operations**: Use async for I/O-bound operations
7. **Monitor Metrics**: Track workflow duration and optimize slow nodes

---

## Security Best Practices

1. **Never Hardcode Credentials**: Use environment variables or AWS IAM
2. **Encrypt Artifacts**: Enable S3 encryption
3. **Use HTTPS**: Always use HTTPS for API
4. **Validate Input**: Sanitize all user input
5. **Rate Limiting**: Implement rate limiting on API
6. **Session Expiration**: Set appropriate session TTLs
7. **Audit Logging**: Log all access and changes

---

## Additional Resources

- [Extended Architecture](extended-architecture.md) - Detailed system design
- [Implementation Guide](implementation-guide.md) - Step-by-step implementation
- [CLI Tool Spec](cli-tool-spec.md) - CLI command reference
- [Original Architecture](architecture.md) - Core system architecture
- [LangGraph Patterns](LANGGRAPH_PATTERNS.md) - Multi-agent patterns

---

**Quick Start Commands**:

```bash
# Setup
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your credentials

# Create workflow
dataops-workflow create my_flow --template simple

# Test workflow
dataops-workflow test my_flow --input '{"query": "test"}'

# Validate workflow
dataops-workflow validate my_flow

# Deploy
dataops-workflow deploy my_flow --env prod
```

---

**Need Help?**

- Documentation: `docs/`
- Examples: `workflows/*/examples/`
- Tests: `tests/`
- Issues: GitHub Issues

---

**Happy Building! 🚀**

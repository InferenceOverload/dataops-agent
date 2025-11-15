# CLAUDE.md - AI Assistant Guide for DataOps Agent

**Version:** 2.0
**Last Updated:** November 2025
**Purpose:** Comprehensive guide for AI assistants working with the DataOps Agent codebase

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Repository Structure](#repository-structure)
3. [Core Architecture](#core-architecture)
4. [Development Environment](#development-environment)
5. [Common Development Tasks](#common-development-tasks)
6. [Testing Guidelines](#testing-guidelines)
7. [Code Conventions](#code-conventions)
8. [Infrastructure Tools](#infrastructure-tools)
9. [Workflow Development](#workflow-development)
10. [Git Workflow](#git-workflow)
11. [Troubleshooting](#troubleshooting)
12. [Key Files Reference](#key-files-reference)

---

## Project Overview

### What is DataOps Agent?

DataOps Agent is an **intelligent multi-agent orchestration system** for data engineering workflows. It uses LangGraph and LangChain to dynamically route natural language queries to specialized AI agent workflows.

### Core Value Proposition

- **Natural Language Interface**: Users describe data engineering tasks in plain language
- **Intelligent Routing**: Orchestrator detects intent and routes to specialized workflows
- **Parameter Extraction**: Automatically extracts required parameters and asks for missing info
- **Specialized Workflows**: Each workflow is a complete multi-agent system for a specific domain
- **AWS Integration**: Built-in tools for S3, DynamoDB, and Bedrock
- **MLflow Tracing**: Comprehensive observability for all LangGraph executions

### Technology Stack

- **Python**: 3.10+
- **LangGraph**: Multi-agent orchestration framework
- **LangChain**: LLM integration and tooling
- **Anthropic Claude**: Primary LLM (via direct API or AWS Bedrock)
- **AWS Services**: S3, DynamoDB, Bedrock
- **Package Manager**: UV (modern Python package manager)
- **Testing**: pytest with coverage
- **Code Quality**: ruff, black, isort, mypy, pre-commit hooks
- **Observability**: MLflow for workflow tracing

---

## Repository Structure

```
dataops-agent/
├── core/                           # Core orchestration system
│   ├── base_workflow.py           # BaseWorkflow interface & metadata contracts
│   ├── orchestrator.py            # Main orchestrator with parameter extraction
│   └── workflow_registry.py       # Auto-discovery & registration
│
├── workflows/                      # Workflow implementations
│   ├── workflow_a.py              # Simple single-agent workflow
│   ├── workflow_b.py              # Supervisor multi-agent pattern
│   ├── workflow_c.py              # Iterative refinement pattern
│   └── jil_parser/                # JIL dependency parser (reference workflow)
│       ├── workflow.py            # Workflow implementation
│       ├── config.yaml            # Workflow-specific config
│       ├── tests/                 # Workflow-specific tests
│       └── README.md              # Usage documentation
│
├── infrastructure/                 # Centralized infrastructure & utilities
│   ├── config/                    # Configuration management
│   │   └── aws_config.py          # AWS configuration priority system
│   ├── llm/                       # LLM abstraction layer
│   │   ├── llm_factory.py         # LLM factory (Anthropic/Bedrock)
│   │   ├── llm_config.py          # LLM configuration
│   │   └── bedrock_client.py      # AWS Bedrock client
│   ├── observability/             # Observability & monitoring
│   │   └── mlflow_config.py       # MLflow tracing integration
│   ├── tools/                     # LangChain tools
│   │   ├── s3_tools.py            # S3 operations (read, write, list, exists)
│   │   └── dynamodb_tools.py      # DynamoDB operations (put, get, query, scan)
│   └── storage/                   # Base storage utilities (reference)
│       ├── s3_operations.py       # S3 utility class
│       └── dynamodb_operations.py # DynamoDB utility class
│
├── cli/                            # CLI utilities
│   ├── workflow_cli.py            # Workflow scaffolding CLI
│   └── templates.py               # Workflow templates
│
├── tests/                          # Test suite
│   ├── test_base_workflow.py      # Base workflow tests
│   ├── test_workflow_registry.py  # Registry tests
│   ├── test_orchestrator.py       # Orchestrator tests
│   └── test_infrastructure.py     # Infrastructure tools tests
│
├── docs/                           # Documentation
│   ├── architecture.md            # System architecture deep-dive
│   ├── tools-usage-guide.md       # Infrastructure tools guide
│   └── LANGGRAPH_PATTERNS.md      # LangGraph multi-agent patterns
│
├── examples/                       # Example scripts
│   └── mlflow_tracking_example.py # MLflow integration example
│
├── scripts/                        # Utility scripts
│   └── corporate-setup.sh         # Corporate environment setup
│
├── .env.example                    # Environment template (personal/dev)
├── .env.corporate.example          # Environment template (corporate)
├── pyproject.toml                  # Python project configuration
├── uv.toml                         # UV package manager config
├── uv.lock                         # UV lock file (pinned dependencies)
├── langgraph.json                  # LangGraph server configuration
├── Makefile                        # Development commands
├── .pre-commit-config.yaml         # Pre-commit hooks configuration
├── README.md                       # User-facing documentation
├── DEPLOYMENT_GUIDE.md             # Deployment instructions
├── CORPORATE_SETUP.md              # Corporate environment setup guide
├── SETUP_UV.md                     # UV setup instructions
└── CLAUDE.md                       # This file (AI assistant guide)
```

### Key Directories Explained

- **`core/`**: The orchestration engine. DO NOT modify unless changing core routing logic.
- **`workflows/`**: Where you spend most time. Each workflow is independent.
- **`infrastructure/`**: Shared utilities. Use these instead of writing AWS code from scratch.
- **`cli/`**: Developer tools. Use `dataops-workflow create` to scaffold new workflows.
- **`tests/`**: Test suite. ALWAYS add tests for new functionality.
- **`docs/`**: Architecture and design documentation. Read before major changes.

---

## Core Architecture

### Architectural Principles

1. **Loose Coupling**: Workflows are independent; orchestrator knows them only via contracts
2. **Infrastructure Over Patterns**: Provide utilities, not prescriptive templates
3. **Dynamic Discovery**: Workflows auto-register; no manual configuration
4. **Workflows as Complete Systems**: Each workflow is a full multi-agent LangGraph
5. **Contract-Based Communication**: Workflows communicate via structured metadata and responses

### The Orchestrator Pattern

```
User Query → Intent Detection → Parameter Extraction
                                      ↓
                           [Missing Parameters?]
                              ↙           ↘
                            Yes            No
                             ↓              ↓
                    Ask User for Info   Workflow Invocation
                                              ↓
                                    Specialized Workflows
                                              ↓
                                      Response Formatting
```

### Workflow Lifecycle

1. **Discovery**: Registry scans `workflows/` and imports all BaseWorkflow implementations
2. **Registration**: Metadata extracted via `get_metadata()`, graph compiled via `get_compiled_graph()`
3. **Intent Detection**: Orchestrator uses LLM + capabilities to match query to workflow
4. **Parameter Gathering**: Orchestrator extracts required parameters, prompts user if missing
5. **Invocation**: Orchestrator calls `workflow.invoke(input)` (blocking)
6. **Response**: Workflow returns structured response following contract

### State Management

- **Orchestrator State**: Separate from workflow states
- **Workflow State**: Each workflow defines its own state schema
- **State Transformation**: Happens at orchestrator ↔ workflow boundaries
- **No Shared State**: Workflows are isolated; communicate only via input/output

---

## Development Environment

### Prerequisites

- Python 3.10 or higher
- UV package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Git
- Anthropic API key OR AWS credentials with Bedrock access

### Initial Setup

```bash
# Clone repository
git clone https://github.com/InferenceOverload/dataops-agent.git
cd dataops-agent

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env and add:
# - ANTHROPIC_API_KEY (for personal dev)
# OR
# - Configure AWS Bedrock (for corporate deployment)

# Install pre-commit hooks (optional but recommended)
make pre-commit

# Verify installation
make test
```

### Environment Variables (`.env`)

**Required (choose one LLM provider):**

```bash
# Option 1: Anthropic API (personal/dev)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Option 2: AWS Bedrock (corporate)
LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_REGION=us-east-1
AWS_REGION=us-east-1
```

**Optional (AWS infrastructure tools):**

```bash
AWS_S3_BUCKET=your-default-bucket
AWS_DYNAMODB_TABLE=your-default-table
AWS_ACCESS_KEY_ID=...  # If not using IAM roles
AWS_SECRET_ACCESS_KEY=...
```

**Optional (observability):**

```bash
MLFLOW_TRACKING_URI=./mlruns  # Or remote: http://mlflow-server:5000
MLFLOW_EXPERIMENT_NAME=dataops-agent-workflows
MLFLOW_ENABLE_AUTO_LOGGING=true
MLFLOW_ENABLE_NESTED_RUNS=true
```

### Corporate Environment Setup

If working in a corporate environment with SSL interception or proxies:

```bash
# Run interactive setup
make corporate-setup

# Or manually configure
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
```

See [CORPORATE_SETUP.md](CORPORATE_SETUP.md) for detailed instructions.

---

## Common Development Tasks

### Running the Application

```bash
# Start LangGraph dev server (recommended for development)
make dev
# OR: uv run langgraph dev
# Open http://localhost:2024/docs

# Run orchestrator directly (for testing)
uv run python core/orchestrator.py

# Test specific workflow
uv run python workflows/jil_parser/workflow.py
```

### Creating a New Workflow

**Option 1: Use CLI scaffolding tool (recommended)**

```bash
# Create workflow from template
uv run dataops-workflow create my_analyzer --template iterative --category analysis

# Templates available:
# - simple: Single agent, single LLM call
# - iterative: Loop-based refinement with artifacts
# - supervisor: Multi-agent with supervisor coordination
# - sequential: Chain of specialist agents
# - parallel: Concurrent agent execution

# Follow generated instructions
cd workflows/my_analyzer
# Edit workflow.py, implement nodes, test
```

**Option 2: Manual creation**

```bash
# Create directory structure
mkdir -p workflows/my_workflow
touch workflows/my_workflow/__init__.py
touch workflows/my_workflow/workflow.py
touch workflows/my_workflow/config.yaml
touch workflows/my_workflow/README.md
mkdir workflows/my_workflow/tests

# Implement BaseWorkflow interface (see Workflow Development section)
```

### Testing

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run specific test categories
make test-unit
make test-integration

# Run specific test file
uv run pytest tests/test_orchestrator.py -v

# Run specific test
uv run pytest tests/test_orchestrator.py::test_intent_detection -v
```

### Code Quality

```bash
# Run linting checks
make lint
# Runs: ruff check, mypy

# Format code
make format
# Runs: black, isort, ruff --fix

# Run pre-commit hooks manually
uv run pre-commit run --all-files
```

### Makefile Commands Reference

```bash
# Setup
make install              # Basic installation
make install-dev          # With dev dependencies
make install-all          # All optional dependencies
make corporate-setup      # Interactive corporate setup

# Development
make test                 # Run tests
make test-cov             # Tests with coverage
make lint                 # Linting checks
make format               # Code formatting
make pre-commit           # Install pre-commit hooks

# Running
make dev                  # Start LangGraph dev server
make run                  # Run orchestrator directly

# Cleanup
make clean                # Remove build artifacts and cache
```

---

## Testing Guidelines

### Test Organization

- **Unit tests**: Test individual functions/classes in isolation
- **Integration tests**: Test component interactions (e.g., workflow + registry)
- **E2E tests**: Test full orchestrator → workflow flow

### Test Markers

```python
import pytest

@pytest.mark.unit
def test_workflow_metadata():
    """Unit test for metadata validation"""
    pass

@pytest.mark.integration
def test_workflow_invocation():
    """Integration test for workflow invocation"""
    pass

@pytest.mark.slow
def test_full_workflow_execution():
    """E2E test (may take longer)"""
    pass
```

### Writing Tests for Workflows

**Example: `workflows/my_workflow/tests/test_my_workflow.py`**

```python
import pytest
from workflows.my_workflow.workflow import MyWorkflow

@pytest.mark.unit
def test_metadata():
    """Test workflow metadata"""
    workflow = MyWorkflow()
    metadata = workflow.get_metadata()

    assert metadata.name == "my_workflow"
    assert len(metadata.capabilities) > 0
    assert len(metadata.example_queries) > 0

@pytest.mark.integration
def test_workflow_execution():
    """Test workflow can be invoked"""
    workflow = MyWorkflow()
    graph = workflow.get_compiled_graph()

    result = graph.invoke({"input": "test query"})

    assert "output" in result
    assert result["output"] is not None
```

### Coverage Requirements

- Aim for **>80% code coverage** on core modules
- Workflows should have tests for:
  - Metadata validation
  - Graph compilation
  - Basic invocation
  - Error handling

### Running Tests in CI/CD

Tests run automatically on PR creation via GitHub Actions. Ensure tests pass locally before pushing:

```bash
make test-cov
# Check coverage report in htmlcov/index.html
```

---

## Code Conventions

### Python Style Guide

We follow **PEP 8** with these tools:
- **Black**: Code formatting (line length: 100)
- **isort**: Import sorting
- **ruff**: Fast linting (replaces flake8, pylint)
- **mypy**: Type checking

### Type Hints

**REQUIRED** for all functions:

```python
# ✅ Good
def process_data(input_data: dict[str, Any], config: Config) -> ProcessResult:
    """Process data with configuration"""
    pass

# ❌ Bad
def process_data(input_data, config):
    """Process data with configuration"""
    pass
```

### Docstrings

Use **Google-style docstrings**:

```python
def my_function(param1: str, param2: int) -> dict[str, Any]:
    """Brief description of function.

    Longer description if needed. Explain purpose, behavior, edge cases.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Dictionary containing result with keys:
        - key1: Description
        - key2: Description

    Raises:
        ValueError: When param2 is negative

    Example:
        >>> my_function("test", 42)
        {"result": "processed"}
    """
    pass
```

### Import Organization

```python
# 1. Standard library imports
import os
import sys
from typing import Any, Dict, List

# 2. Third-party imports
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

# 3. Local imports (grouped by module)
from core.base_workflow import BaseWorkflow, WorkflowMetadata
from infrastructure.llm.llm_factory import create_llm
from infrastructure.tools import get_s3_tools
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `WorkflowRegistry`, `JILParserWorkflow`)
- **Functions/Methods**: `snake_case` (e.g., `get_metadata`, `process_input`)
- **Variables**: `snake_case` (e.g., `workflow_name`, `user_input`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_BUCKET`, `MAX_ITERATIONS`)
- **Private**: `_leading_underscore` (e.g., `_internal_method`)

### File Naming

- **Modules**: `snake_case.py` (e.g., `workflow_registry.py`)
- **Tests**: `test_*.py` (e.g., `test_orchestrator.py`)
- **Config**: `lowercase.yaml` or `lowercase.json`

### Error Handling

```python
# ✅ Good: Specific exceptions with context
try:
    result = workflow.invoke(input_data)
except ValueError as e:
    logger.error(f"Invalid input data: {e}")
    raise WorkflowExecutionError(f"Failed to execute workflow: {e}") from e
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise

# ❌ Bad: Bare except
try:
    result = workflow.invoke(input_data)
except:
    pass
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed debugging info")
logger.info("General informational message")
logger.warning("Warning about potential issue")
logger.error("Error that needs attention")
logger.critical("Critical error requiring immediate attention")
```

---

## Infrastructure Tools

### LLM Factory Pattern

**ALWAYS use `llm_factory.create_llm()` instead of direct instantiation:**

```python
from infrastructure.llm.llm_factory import create_llm

# ✅ Good: Uses factory (respects LLM_PROVIDER env var)
llm = create_llm()

# ❌ Bad: Direct instantiation
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-sonnet-4-20250514")
```

The factory automatically switches between Anthropic API and AWS Bedrock based on `LLM_PROVIDER` environment variable.

### S3 Tools

**Two options: LangChain tools OR utility class**

**Option 1: LangChain Tools (for use in agent tools list)**

```python
from infrastructure.tools import get_s3_tools

# Get all S3 tools as LangChain BaseTool instances
s3_tools = get_s3_tools()

# Use in agent
llm_with_tools = llm.bind_tools(s3_tools)
response = llm_with_tools.invoke("Read the file from s3://bucket/key.txt")
```

**Option 2: S3Operations Utility Class (for direct use)**

```python
from infrastructure.storage.s3_operations import S3Operations

s3 = S3Operations()

# Read text file
content = s3.read_text("s3://my-bucket/data.txt")

# Read JSON file
data = s3.read_json("s3://my-bucket/config.json")

# Write file
s3.write_text("s3://my-bucket/output.txt", "content")

# List objects
files = s3.list_objects("s3://my-bucket/prefix/")

# Check existence
exists = s3.object_exists("s3://my-bucket/file.txt")
```

### DynamoDB Tools

```python
from infrastructure.tools.dynamodb_tools import DynamoDBPutTool, DynamoDBGetTool

# Put item
put_tool = DynamoDBPutTool()
put_tool._run(
    item='{"job_id": "BATCH_001", "status": "completed"}',
    table="jobs"  # Optional if AWS_DYNAMODB_TABLE is set
)

# Get item
get_tool = DynamoDBGetTool()
result = get_tool._run(
    key='{"job_id": "BATCH_001"}',
    table="jobs"
)
```

### AWS Configuration Priority

Configuration is loaded in this order (higher priority first):

1. **Explicit parameters** (passed to function/constructor)
2. **Override dictionary** (runtime overrides)
3. **Environment variables** (.env file)
4. **Default values**

Example:

```python
from infrastructure.config.aws_config import AWSConfig

config = AWSConfig()

# Uses: explicit > override > env > default
bucket = config.get_s3_bucket(
    explicit_bucket="override-bucket",  # Highest priority
    override_config={"s3_bucket": "another-bucket"},
    # Falls back to AWS_S3_BUCKET env var
    # Finally falls back to "dataops-default-bucket"
)
```

### MLflow Integration

MLflow tracing is **automatically enabled** for all LangGraph workflows when configured.

**Configuration:**

```bash
# In .env
MLFLOW_TRACKING_URI=./mlruns  # Or remote server
MLFLOW_EXPERIMENT_NAME=dataops-agent-workflows
MLFLOW_ENABLE_AUTO_LOGGING=true
MLFLOW_ENABLE_NESTED_RUNS=true
```

**Usage:**

```python
from infrastructure.observability.mlflow_config import setup_mlflow_tracing

# Call once at application startup (already done in orchestrator)
setup_mlflow_tracing()

# All subsequent LangGraph invocations are automatically traced
graph = workflow.get_compiled_graph()
result = graph.invoke(input_data)  # Automatically traced to MLflow
```

**View traces:**

```bash
# Start MLflow UI
uv run mlflow ui

# Open http://localhost:5000
# View experiments, runs, parameters, metrics, artifacts
```

---

## Workflow Development

### BaseWorkflow Interface

Every workflow MUST implement:

```python
from core.base_workflow import BaseWorkflow, WorkflowMetadata, WorkflowInputParameter
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

class MyWorkflow(BaseWorkflow):
    """Description of what this workflow does"""

    def get_metadata(self) -> WorkflowMetadata:
        """Return workflow metadata for discovery"""
        return WorkflowMetadata(
            name="my_workflow",
            description="Clear description of workflow purpose",
            capabilities=[
                "Capability 1",
                "Capability 2"
            ],
            example_queries=[
                "Example user query 1",
                "Example user query 2"
            ],
            category="migration",  # or "analysis", "generation", etc.
            version="1.0.0",
            author="Your Team Name",
            required_inputs=[
                WorkflowInputParameter(
                    name="param_name",
                    description="What this parameter is for",
                    type="string",  # or "integer", "boolean", "file_path"
                    required=True,
                    example="example_value",
                    prompt="What should I ask the user for this parameter?"
                )
            ]
        )

    def get_compiled_graph(self):
        """Build and return compiled LangGraph"""
        # Define state schema
        class MyState(TypedDict):
            input: str
            output: str

        # Build graph
        graph = StateGraph(MyState)

        def my_node(state: MyState) -> dict:
            # Your logic here
            return {"output": "result"}

        graph.add_node("my_node", my_node)
        graph.add_edge(START, "my_node")
        graph.add_edge("my_node", END)

        return graph.compile()
```

### Workflow Response Contract

Every workflow MUST return this structure from its final state:

```python
{
    "success": bool,              # True if workflow completed successfully
    "result": str | dict,         # Primary result data
    "metadata": {                 # Execution metadata
        "workflow_name": str,
        "execution_time": float,
        "iterations": int,
        # ... other workflow-specific metadata
    },
    "artifacts": list[str],       # List of artifact IDs (optional)
    "errors": list[str] | None    # Error messages if any
}
```

### Workflow Development Checklist

When creating or modifying a workflow:

- [ ] Implement `BaseWorkflow` interface
- [ ] Define clear `WorkflowMetadata` with capabilities and examples
- [ ] Specify `required_inputs` if parameters needed
- [ ] Define workflow-specific state schema using `TypedDict`
- [ ] Build graph with clear, descriptive node names
- [ ] Return response following contract structure
- [ ] Add docstrings to all nodes and functions
- [ ] Handle errors gracefully (try/except in nodes)
- [ ] Write unit tests for metadata and graph compilation
- [ ] Write integration test for end-to-end invocation
- [ ] Create README.md explaining workflow purpose and usage
- [ ] Test workflow in isolation before integrating
- [ ] Test workflow via orchestrator after integration

### Common LangGraph Patterns

**Pattern 1: Simple Sequential**

```python
graph.add_node("step1", step1_node)
graph.add_node("step2", step2_node)
graph.add_edge(START, "step1")
graph.add_edge("step1", "step2")
graph.add_edge("step2", END)
```

**Pattern 2: Conditional Branching**

```python
def route_based_on_condition(state):
    if state["needs_processing"]:
        return "process"
    else:
        return "skip"

graph.add_node("check", check_node)
graph.add_node("process", process_node)
graph.add_node("skip", skip_node)

graph.add_edge(START, "check")
graph.add_conditional_edges(
    "check",
    route_based_on_condition,
    {"process": "process", "skip": "skip"}
)
graph.add_edge("process", END)
graph.add_edge("skip", END)
```

**Pattern 3: Iterative Loop**

```python
def should_continue(state):
    if state["iteration_count"] < state["max_iterations"]:
        return "continue"
    else:
        return "end"

graph.add_node("loop_agent", loop_agent_node)

graph.add_edge(START, "loop_agent")
graph.add_conditional_edges(
    "loop_agent",
    should_continue,
    {"continue": "loop_agent", "end": END}
)
```

**Pattern 4: Supervisor Pattern**

See `workflows/workflow_b.py` for a complete example.

### Using Infrastructure Tools in Workflows

```python
from infrastructure.llm.llm_factory import create_llm
from infrastructure.tools import get_s3_tools
from infrastructure.storage.s3_operations import S3Operations

class MyWorkflow(BaseWorkflow):
    def __init__(self):
        # LLM for agent nodes
        self.llm = create_llm()

        # S3 tools for LangChain agents
        self.s3_tools = get_s3_tools()

        # S3 utility for direct operations
        self.s3 = S3Operations()

    def get_compiled_graph(self):
        def my_node(state):
            # Use LLM with S3 tools
            llm_with_tools = self.llm.bind_tools(self.s3_tools)
            response = llm_with_tools.invoke(state["input"])

            # Or use S3 directly
            data = self.s3.read_json("s3://bucket/config.json")

            return {"output": response.content}

        # Build graph...
```

---

## Git Workflow

### Branch Naming

- **Feature branches**: `feature/description` or `claude/description-sessionid`
- **Bug fixes**: `fix/description`
- **Documentation**: `docs/description`
- **Refactoring**: `refactor/description`

### Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```bash
git commit -m "feat(workflows): Add SQL generator workflow"
git commit -m "fix(orchestrator): Handle missing parameter edge case"
git commit -m "docs(readme): Update installation instructions"
git commit -m "test(workflows): Add integration tests for JIL parser"
```

### Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes, commit frequently
git add .
git commit -m "feat: Add initial implementation"

# 3. Run tests and linting
make test
make lint

# 4. Format code
make format

# 5. Commit formatting changes
git add .
git commit -m "chore: Format code"

# 6. Push to remote
git push -u origin feature/my-feature

# 7. Create Pull Request on GitHub
# Use gh CLI or web interface
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`:

- trailing-whitespace: Remove trailing whitespace
- end-of-file-fixer: Ensure files end with newline
- check-yaml: Validate YAML files
- check-json: Validate JSON files
- ruff: Linting and auto-fixes
- black: Code formatting
- isort: Import sorting
- mypy: Type checking

**Install hooks:**

```bash
make pre-commit
```

**Run manually:**

```bash
uv run pre-commit run --all-files
```

---

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Error:** `ModuleNotFoundError: No module named 'core'`

**Solution:**
```bash
# Ensure you're in project root
pwd  # Should show .../dataops-agent

# Install in editable mode
uv pip install -e .

# Or run via uv
uv run python core/orchestrator.py
```

#### 2. SSL Certificate Errors (Corporate)

**Error:** `SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]`

**Solution:**
```bash
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE
uv sync
```

See [CORPORATE_SETUP.md](CORPORATE_SETUP.md) for comprehensive guide.

#### 3. AWS Credentials Not Found

**Error:** `NoCredentialsError: Unable to locate credentials`

**Solution:**
```bash
# Option 1: Set in .env
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# Option 2: Use AWS CLI profile
aws configure

# Option 3: Use IAM roles (recommended for production)
# No credentials needed if running on EC2/ECS
```

#### 4. LangGraph Dev Server Not Starting

**Error:** `Address already in use`

**Solution:**
```bash
# Check what's using port 2024
lsof -i :2024

# Kill the process or use different port
langgraph dev --port 2025
```

#### 5. Workflow Not Discovered

**Error:** Workflow not showing in registry

**Checklist:**
- [ ] Workflow file is in `workflows/` directory
- [ ] Class inherits from `BaseWorkflow`
- [ ] `get_metadata()` and `get_compiled_graph()` implemented
- [ ] No syntax errors in workflow file
- [ ] Restart orchestrator after adding new workflow

**Debug:**
```python
# In orchestrator.py or test file
from core.workflow_registry import WorkflowRegistry

registry = WorkflowRegistry()
print(registry.list_workflows())  # Should show your workflow
```

#### 6. Type Checking Errors

**Error:** mypy reports type errors

**Solution:**
```bash
# Add type: ignore comment (use sparingly)
result = some_function()  # type: ignore

# Or fix the actual type issue
result: dict[str, Any] = some_function()

# Check mypy configuration in pyproject.toml
# Consider disabling for test files:
# [[tool.mypy.overrides]]
# module = "tests.*"
# disallow_untyped_defs = false
```

### Debugging Workflows

**Enable debug logging:**

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def my_node(state):
    logger.debug(f"State at node entry: {state}")
    # ... node logic
    logger.debug(f"State at node exit: {new_state}")
    return new_state
```

**Use LangGraph streaming for visibility:**

```python
# Instead of:
result = graph.invoke(input_data)

# Use streaming to see each step:
for update in graph.stream(input_data, stream_mode="updates"):
    print(f"Update: {update}")
```

**MLflow tracing:**

```bash
# View detailed traces in MLflow UI
uv run mlflow ui
# Open http://localhost:5000
# View runs, parameters, artifacts, traces
```

### Getting Help

1. **Check documentation**:
   - [README.md](README.md) - User-facing docs
   - [docs/architecture.md](docs/architecture.md) - Architecture deep-dive
   - [docs/tools-usage-guide.md](docs/tools-usage-guide.md) - Infrastructure tools
   - [CORPORATE_SETUP.md](CORPORATE_SETUP.md) - Corporate environment

2. **Review examples**:
   - `workflows/workflow_a.py` - Simple pattern
   - `workflows/workflow_b.py` - Supervisor pattern
   - `workflows/workflow_c.py` - Iterative pattern
   - `workflows/jil_parser/` - Complete reference workflow

3. **Run diagnostics**:
   ```bash
   python --version  # 3.10+
   uv --version
   make test  # All tests should pass
   ```

---

## Key Files Reference

### Configuration Files

- **`pyproject.toml`**: Python project config, dependencies, tool settings
- **`uv.toml`**: UV package manager configuration
- **`uv.lock`**: Locked dependency versions (DO NOT manually edit)
- **`langgraph.json`**: LangGraph server configuration (defines available graphs)
- **`.env`**: Environment variables (NOT in git, copy from `.env.example`)
- **`.env.example`**: Environment template (personal/dev setup)
- **`.env.corporate.example`**: Environment template (corporate setup)
- **`.pre-commit-config.yaml`**: Pre-commit hooks configuration

### Core Files

- **`core/base_workflow.py`**: BaseWorkflow interface, metadata contracts
- **`core/orchestrator.py`**: Main orchestrator, intent detection, parameter extraction
- **`core/workflow_registry.py`**: Auto-discovery and registration

### Infrastructure Files

- **`infrastructure/llm/llm_factory.py`**: LLM factory (Anthropic/Bedrock abstraction)
- **`infrastructure/llm/llm_config.py`**: LLM configuration management
- **`infrastructure/llm/bedrock_client.py`**: AWS Bedrock client
- **`infrastructure/config/aws_config.py`**: AWS configuration priority system
- **`infrastructure/tools/s3_tools.py`**: S3 LangChain tools
- **`infrastructure/tools/dynamodb_tools.py`**: DynamoDB LangChain tools
- **`infrastructure/storage/s3_operations.py`**: S3 utility class
- **`infrastructure/observability/mlflow_config.py`**: MLflow tracing setup

### Development Files

- **`Makefile`**: Development commands (test, lint, format, run, etc.)
- **`cli/workflow_cli.py`**: Workflow scaffolding CLI
- **`cli/templates.py`**: Workflow templates

### Documentation Files

- **`README.md`**: User-facing documentation
- **`CLAUDE.md`**: This file (AI assistant guide)
- **`docs/architecture.md`**: System architecture deep-dive
- **`docs/tools-usage-guide.md`**: Infrastructure tools guide
- **`docs/LANGGRAPH_PATTERNS.md`**: LangGraph multi-agent patterns
- **`DEPLOYMENT_GUIDE.md`**: Deployment instructions
- **`CORPORATE_SETUP.md`**: Corporate environment setup
- **`SETUP_UV.md`**: UV setup instructions
- **`CHANGELOG.md`**: Version history and changes

---

## Best Practices for AI Assistants

### When Analyzing Code

1. **Read architecture docs first**: Start with `docs/architecture.md` to understand system design
2. **Identify the layer**: Core (orchestrator) vs Workflows vs Infrastructure
3. **Check contracts**: Workflows communicate via metadata and response contracts
4. **Respect boundaries**: Don't couple workflows together; use infrastructure utilities
5. **Look for patterns**: Study existing workflows before creating new ones

### When Writing Code

1. **Use scaffolding**: `uv run dataops-workflow create` for new workflows
2. **Follow templates**: Reference `workflows/workflow_a.py` (simple), `workflow_b.py` (supervisor), `workflow_c.py` (iterative)
3. **Use infrastructure**: Don't write AWS code from scratch; use `infrastructure/` utilities
4. **Type everything**: Add type hints to all functions
5. **Test first**: Write tests before or alongside implementation
6. **Format before commit**: `make format` before committing

### When Modifying Existing Code

1. **Understand impact**: Is this core (affects all), workflow (isolated), or infrastructure (shared)?
2. **Read tests first**: Tests document expected behavior
3. **Maintain contracts**: Don't break `WorkflowMetadata` or response structures
4. **Update docs**: Change docs when changing behavior
5. **Verify nothing breaks**: `make test` before committing

### When Debugging Issues

1. **Check environment**: Is `.env` configured correctly?
2. **Review logs**: Enable DEBUG logging for detailed output
3. **Use MLflow**: View traces in MLflow UI for workflow execution details
4. **Isolate the problem**: Test workflow standalone before testing via orchestrator
5. **Check recent changes**: `git log` to see what changed recently

### When Explaining Code

1. **Start with purpose**: What problem does this solve?
2. **Explain architecture**: How does it fit in the system?
3. **Reference contracts**: What metadata/response format does it use?
4. **Show examples**: Provide example queries and expected results
5. **Link to docs**: Reference relevant docs for deeper understanding

---

## Summary

DataOps Agent is a **loosely-coupled, extensible multi-agent orchestration system** for data engineering workflows. Key takeaways:

- **Workflows are independent**: Each workflow is a complete LangGraph system
- **Auto-discovery**: Drop workflow in `workflows/`, implement interface, done
- **Infrastructure tools**: Use `infrastructure/` utilities instead of writing AWS code
- **Contract-based**: Communicate via metadata and structured responses
- **Type-safe**: Use type hints everywhere
- **Test-driven**: Write tests for all functionality
- **Well-documented**: Update docs when changing behavior

**For quick reference while developing, bookmark:**
- [Makefile](Makefile) - Development commands
- [docs/architecture.md](docs/architecture.md) - System design
- [workflows/workflow_a.py](workflows/workflow_a.py) - Simple pattern example
- [workflows/jil_parser/](workflows/jil_parser/) - Complete workflow reference

**Happy coding! 🚀**

# DataOps Workflow CLI - Quick Start Guide

## Installation

The CLI is installed automatically with the package:

```bash
# Install in development mode
uv pip install -e .

# Or use directly with Python
.venv/bin/python -m cli.workflow_cli
```

## Quick Reference

### Create a New Workflow

```bash
# Simple workflow (single agent)
dataops-workflow create my_analyzer \
  --template simple \
  --description "Analyzes data patterns" \
  --category analysis

# Iterative workflow (loop pattern)
dataops-workflow create data_processor \
  --template iterative \
  --description "Processes data iteratively" \
  --category migration

# Available templates: simple, iterative, supervisor, sequential, parallel
```

**Generated Structure:**
```
workflows/my_analyzer/
├── workflow.py          # Main workflow implementation
├── config.yaml          # Configuration with enabled flag
├── tests/
│   └── test_workflow.py # Auto-generated tests
└── README.md            # Documentation
```

### Enable/Disable Workflows

```bash
# Disable a workflow (stops it from being discovered)
dataops-workflow toggle my_analyzer --disable

# Enable a workflow
dataops-workflow toggle my_analyzer --enable
```

**What happens when disabled:**
- Workflow is skipped during auto-discovery
- Not visible in `dataops-workflow list`
- Not available to orchestrator
- Config file updated with `workflow.enabled: false`

### List Workflows

```bash
# List all enabled workflows
dataops-workflow list

# List with details
dataops-workflow list --verbose

# Filter by category
dataops-workflow list --category migration

# Show disabled workflows too
dataops-workflow list --show-disabled
```

### Test a Workflow

```bash
# Test with inline JSON
dataops-workflow test my_analyzer --input '{"input": "test query"}'

# Test with file
dataops-workflow test my_analyzer --input test_data.json

# Verbose output
dataops-workflow test my_analyzer --input test.json --verbose
```

### Validate a Workflow

```bash
# Basic validation
dataops-workflow validate my_analyzer

# Strict mode (fail on warnings)
dataops-workflow validate my_analyzer --strict
```

**What gets validated:**
- Metadata completeness (name, description, capabilities, examples)
- Graph compiles successfully
- State schema defined
- No TODO placeholders in production

### Generate Documentation

```bash
# Generate README for workflow
dataops-workflow docs my_analyzer
```

## Workflow Development Workflow

### 1. Create from Template

```bash
dataops-workflow create my_new_workflow \
  --template simple \
  --description "Does something cool" \
  --category analysis
```

### 2. Customize the Workflow

Edit `workflows/my_new_workflow/workflow.py`:

```python
def process_node(state: MyNewWorkflowState) -> dict:
    """
    Main processing node.

    TODO: Implement your business logic here.
    """
    user_input = state["input"]

    # Your custom logic
    result = do_something(user_input)

    return {"output": result}
```

### 3. Update Metadata

```python
def get_metadata(self) -> WorkflowMetadata:
    return WorkflowMetadata(
        name="my_new_workflow",
        description="Your actual description",  # Remove TODO
        capabilities=[
            "Capability 1",  # Replace TODOs
            "Capability 2",
            "Capability 3"
        ],
        example_queries=[
            "Example query 1",  # Replace TODOs
            "Example query 2"
        ],
        category="analysis",
        version="1.0.0"
    )
```

### 4. Test Locally

```bash
# Test the workflow
dataops-workflow test my_new_workflow --input '{"input": "test"}'

# Validate
dataops-workflow validate my_new_workflow
```

### 5. Auto-Discovery

The workflow is automatically discovered when the system starts:

```python
# No manual registration needed!
from core.workflow_registry import WORKFLOW_REGISTRY

# Workflows are auto-discovered on import
WORKFLOW_REGISTRY.discover_workflows()

# Your workflow is now available
workflow = WORKFLOW_REGISTRY.get_workflow("my_new_workflow")
```

## Configuration Management

Each workflow has a `config.yaml`:

```yaml
# Workflow control
workflow:
  enabled: true  # Simple flag flip to enable/disable

# LLM settings
llm:
  model: "claude-sonnet-4-20250514"
  temperature: 0.7
  max_tokens: 4096

# Your custom settings
custom:
  max_iterations: 10
  timeout: 300
```

### Reading Config in Workflow

```python
class MyWorkflow(BaseWorkflow):
    def __init__(self, config: dict = None):
        self.config = config or {}

        # Read from config
        max_iter = self.config.get("custom", {}).get("max_iterations", 3)
```

## Templates Available

### Simple Template
- **Pattern:** Single agent → LLM call → response
- **Best for:** Straightforward queries, single-step processing
- **Nodes:** 1 (process)

### Iterative Template
- **Pattern:** Initialize → Loop → Conditional check → Finalize
- **Best for:** Progressive refinement, multi-step analysis
- **Nodes:** 4 (initialize, iterate, check_completion, finalize)
- **Features:** Iteration count, max iterations, result accumulation

### Supervisor Template (Coming Soon)
- **Pattern:** Supervisor coordinates specialist agents
- **Best for:** Complex multi-agent tasks

### Sequential Template (Coming Soon)
- **Pattern:** Chain of agents in sequence
- **Best for:** Multi-stage pipelines

### Parallel Template (Coming Soon)
- **Pattern:** Parallel execution with aggregation
- **Best for:** Independent concurrent tasks

## Best Practices

### 1. Use Descriptive Names
```bash
# Good
dataops-workflow create schema_analyzer

# Avoid
dataops-workflow create thing1
```

### 2. Complete Metadata
Remove all TODOs before deploying:
- ✅ Clear description
- ✅ Meaningful capabilities
- ✅ Real example queries

### 3. Test Before Enabling
```bash
# Create workflow
dataops-workflow create my_workflow --template simple

# Test thoroughly
dataops-workflow test my_workflow --input test.json

# Validate
dataops-workflow validate my_workflow --strict

# Then enable for production
# (it's enabled by default, but you can toggle)
```

### 4. Use Config for Environment-Specific Settings
Don't hardcode in Python - use config.yaml:

```yaml
# workflows/my_workflow/config.yaml
workflow:
  enabled: true

# Environment-specific
s3:
  bucket: "my-bucket-dev"  # Override in prod

llm:
  model: "claude-sonnet-4-20250514"
  temperature: 0  # Deterministic for prod
```

### 5. Write Tests
Use the generated test template:

```python
# tests/test_workflow.py
def test_basic_execution(self):
    result = self.graph.invoke(test_input)
    assert "output" in result
    assert result["output"] != ""
```

## Troubleshooting

### Workflow Not Discovered

```bash
# Check if it's disabled
dataops-workflow list --show-disabled

# Enable it
dataops-workflow toggle my_workflow --enable

# Check for errors
dataops-workflow validate my_workflow
```

### Import Errors

```bash
# Make sure you're in the right directory
cd /path/to/dataops-agent

# Reinstall if needed
uv pip install -e .
```

### Config Not Loading

```yaml
# config.yaml must be valid YAML
workflow:
  enabled: true  # Use lowercase true/false

# Not this:
workflow:
  enabled: True  # Python-style might cause issues
```

## Advanced Usage

### Custom Template Variables

When creating, the following variables are replaced:

- `{{workflow_name}}`: Lowercase with underscores
- `{{WorkflowName}}`: PascalCase class name
- `{{description}}`: Your description
- `{{category}}`: Selected category
- `{{author}}`: Author name

### Programmatic Usage

```python
from cli.workflow_cli import WorkflowCLI

cli = WorkflowCLI()

# Create workflow
cli.create_workflow(
    name="my_workflow",
    template="simple",
    description="My workflow"
)

# Test workflow
result = cli.test_workflow(
    name="my_workflow",
    input_data={"query": "test"}
)
```

## Summary

The CLI makes workflow development a **3-step process**:

1. **Create:** `dataops-workflow create my_workflow --template simple`
2. **Customize:** Edit `workflow.py` and update metadata
3. **Deploy:** Auto-discovered and ready to use!

**Bonus:** Simple flag flip to enable/disable any workflow:
```bash
dataops-workflow toggle my_workflow --disable  # Instant off
dataops-workflow toggle my_workflow --enable   # Instant on
```

No manual registration, no complex configuration - just create, customize, and go!

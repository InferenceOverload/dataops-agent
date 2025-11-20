# DataOps Workflow CLI Tool Specification

**Version:** 1.0
**Purpose:** Command-line tool for workflow development

---

## Overview

The `dataops-workflow` CLI tool accelerates workflow development by providing:
- Scaffolding and templates
- Testing utilities
- Validation tools
- Documentation generation
- Packaging and deployment

---

## Installation

```bash
# Install dataops-agent with CLI tools
pip install -e ".[dev]"

# Verify installation
dataops-workflow --version
```

---

## Commands

### 1. Create Workflow

```bash
dataops-workflow create [OPTIONS] WORKFLOW_NAME
```

**Description**: Scaffold a new workflow from a template

**Options**:
- `--template, -t TEXT`: Template to use (default: simple)
  - `simple`: Single-agent workflow
  - `supervisor`: Multi-agent supervisor pattern
  - `iterative`: Iterative refinement pattern
  - `sequential`: Sequential chain pattern
  - `parallel`: Parallel execution pattern
- `--description, -d TEXT`: Workflow description
- `--category, -c TEXT`: Workflow category (migration, analysis, generation)
- `--author, -a TEXT`: Author name
- `--output-dir, -o PATH`: Output directory (default: ./workflows)

**Examples**:

```bash
# Create simple workflow
dataops-workflow create my_analyzer --template simple

# Create with full options
dataops-workflow create data_transformer \
  --template iterative \
  --description "Transform legacy data formats" \
  --category migration \
  --author "Data Team"

# Create in custom location
dataops-workflow create custom_flow \
  --output-dir /path/to/workflows
```

**Generated Structure**:

```
workflows/my_analyzer/
├── __init__.py
├── workflow.py          # Main workflow implementation
├── nodes.py             # Node implementations
├── state.py             # State schema definition
├── config.yaml          # Workflow configuration
├── requirements.txt     # Workflow-specific dependencies
├── tests/
│   ├── __init__.py
│   └── test_workflow.py  # Generated tests
├── examples/
│   └── example_usage.py
└── README.md            # Generated documentation
```

---

### 2. Test Workflow

```bash
dataops-workflow test [OPTIONS] WORKFLOW_NAME
```

**Description**: Test a workflow in isolation

**Options**:
- `--input, -i TEXT`: Input JSON string or file path
- `--session TEXT`: Use existing session ID
- `--mock-llm`: Mock LLM responses (for faster testing)
- `--mock-tools`: Mock infrastructure tools
- `--trace`: Show execution trace
- `--verbose, -v`: Verbose output

**Examples**:

```bash
# Test with inline JSON
dataops-workflow test my_analyzer --input '{"query": "test input"}'

# Test with input file
dataops-workflow test my_analyzer --input examples/test_input.json

# Test with session context
dataops-workflow test my_analyzer \
  --input '{"query": "test"}' \
  --session sess_123

# Test with mocks and tracing
dataops-workflow test my_analyzer \
  --input test.json \
  --mock-llm \
  --trace
```

**Output**:

```
Testing workflow: my_analyzer
================================================================================

Input:
{
  "query": "test input"
}

Execution:
  [START] → intent_detection (0.5s)
  [NODE] intent_detection → processing (1.2s)
  [NODE] processing → formatting (0.3s)
  [NODE] formatting → [END] (0.1s)

Total time: 2.1s
Nodes executed: 3
Artifacts created: 2

Output:
{
  "success": true,
  "result": "...",
  "metadata": {...}
}

✅ Test passed
```

---

### 3. Validate Workflow

```bash
dataops-workflow validate [OPTIONS] WORKFLOW_NAME
```

**Description**: Validate workflow implementation against contracts

**Options**:
- `--check-metadata`: Validate metadata completeness
- `--check-state`: Validate state schema
- `--check-contract`: Validate output contract
- `--strict`: Fail on warnings

**Examples**:

```bash
# Basic validation
dataops-workflow validate my_analyzer

# Strict validation
dataops-workflow validate my_analyzer --strict

# Check specific aspects
dataops-workflow validate my_analyzer \
  --check-metadata \
  --check-contract
```

**Checks**:

1. **Metadata Validation**:
   - Required fields present (name, description, capabilities)
   - Example queries provided
   - Category is valid
   - Input parameters well-defined

2. **State Schema Validation**:
   - State class is TypedDict
   - All fields are typed
   - Required fields documented

3. **Contract Validation**:
   - Output follows WorkflowResponse contract
   - Required fields present (success, result, metadata)
   - Metadata includes workflow_name

4. **Graph Validation**:
   - Graph compiles successfully
   - No unreachable nodes
   - All edges have valid targets
   - START and END connected

**Output**:

```
Validating workflow: my_analyzer
================================================================================

✅ Metadata: Valid
   - Name: my_analyzer
   - Category: analysis
   - Capabilities: 3 defined
   - Example queries: 2 provided

✅ State Schema: Valid
   - 5 fields defined
   - All fields typed

✅ Output Contract: Valid
   - Follows WorkflowResponse contract
   - All required fields present

✅ Graph Structure: Valid
   - 4 nodes defined
   - All nodes reachable
   - START → END path exists

⚠️  Warnings:
   - Consider adding more example queries
   - Node 'processing' has no error handling

================================================================================
Validation: PASSED (1 warning)
```

---

### 4. Generate Documentation

```bash
dataops-workflow docs [OPTIONS] WORKFLOW_NAME
```

**Description**: Generate documentation for workflow

**Options**:
- `--format TEXT`: Output format (markdown, html, pdf)
- `--output, -o PATH`: Output file path
- `--include-diagrams`: Generate flow diagrams
- `--template PATH`: Custom documentation template

**Examples**:

```bash
# Generate markdown docs
dataops-workflow docs my_analyzer

# Generate with diagrams
dataops-workflow docs my_analyzer --include-diagrams

# Generate HTML
dataops-workflow docs my_analyzer \
  --format html \
  --output docs/my_analyzer.html
```

**Generated Content**:

```markdown
# My Analyzer Workflow

## Overview

**Category**: analysis
**Version**: 1.0.0
**Author**: Data Team

## Description

[Workflow description from metadata]

## Capabilities

- Capability 1
- Capability 2
- Capability 3

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | User query |
| ...

## Output Format

```json
{
  "success": true,
  "result": {...},
  "metadata": {...}
}
```

## Example Usage

```python
from workflows.my_analyzer import MyAnalyzerWorkflow

workflow = MyAnalyzerWorkflow()
result = workflow.get_compiled_graph().invoke({
    "query": "example input"
})
```

## Architecture

[Flow diagram if --include-diagrams]

## Nodes

### intent_detection
Description: [auto-extracted from docstring]
...

## Testing

```bash
dataops-workflow test my_analyzer --input examples/test.json
```
```

---

### 5. List Workflows

```bash
dataops-workflow list [OPTIONS]
```

**Description**: List all available workflows

**Options**:
- `--category, -c TEXT`: Filter by category
- `--search, -s TEXT`: Search by name or description
- `--verbose, -v`: Show detailed information

**Examples**:

```bash
# List all workflows
dataops-workflow list

# Filter by category
dataops-workflow list --category migration

# Search workflows
dataops-workflow list --search "parser"

# Detailed listing
dataops-workflow list --verbose
```

**Output**:

```
Available Workflows
================================================================================

jil_parser (migration)
  Analyzes Autosys JIL files to identify job dependencies
  Examples: "Parse JIL dependencies for BATCH_PROCESSING"

schema_analyzer (analysis)
  Analyzes database schemas and suggests optimizations
  Examples: "Analyze schema for performance issues"

sql_generator (generation)
  Generates SQL queries from natural language
  Examples: "Generate SQL to find top customers"

================================================================================
Total: 3 workflows
```

---

### 6. Package Workflow

```bash
dataops-workflow package [OPTIONS] WORKFLOW_NAME
```

**Description**: Package workflow for deployment

**Options**:
- `--output, -o PATH`: Output directory
- `--format TEXT`: Package format (zip, tar.gz, wheel)
- `--include-deps`: Include dependencies
- `--include-tests`: Include tests

**Examples**:

```bash
# Create deployment package
dataops-workflow package my_analyzer

# Include dependencies
dataops-workflow package my_analyzer --include-deps

# Create wheel package
dataops-workflow package my_analyzer --format wheel
```

**Output**:

```
Packaging workflow: my_analyzer
================================================================================

Including:
  - Workflow code
  - Configuration
  - Dependencies
  - README

Created: my_analyzer-1.0.0.tar.gz (2.3 MB)

To deploy:
  pip install my_analyzer-1.0.0.tar.gz
```

---

### 7. Benchmark Workflow

```bash
dataops-workflow benchmark [OPTIONS] WORKFLOW_NAME
```

**Description**: Benchmark workflow performance

**Options**:
- `--input PATH`: Input file or directory
- `--iterations, -n INT`: Number of iterations (default: 10)
- `--concurrent, -c INT`: Concurrent executions
- `--report PATH`: Save report to file

**Examples**:

```bash
# Basic benchmark
dataops-workflow benchmark my_analyzer --input test_inputs.json

# Multiple iterations
dataops-workflow benchmark my_analyzer \
  --input test_inputs.json \
  --iterations 100

# Concurrent benchmark
dataops-workflow benchmark my_analyzer \
  --input test_inputs.json \
  --concurrent 5
```

**Output**:

```
Benchmarking: my_analyzer
================================================================================

Iterations: 100
Concurrent: 1

Results:
  Mean: 2.34s
  Median: 2.31s
  P95: 2.89s
  P99: 3.12s
  Min: 1.98s
  Max: 3.45s

Node Performance:
  intent_detection: 0.52s (22%)
  processing: 1.45s (62%)
  formatting: 0.37s (16%)

Memory Usage:
  Mean: 145 MB
  Peak: 203 MB

Artifacts:
  Mean size: 23 KB
  Total: 2.3 MB

================================================================================
✅ Benchmark complete
```

---

### 8. Interactive Shell

```bash
dataops-workflow shell [OPTIONS] WORKFLOW_NAME
```

**Description**: Interactive shell for workflow testing

**Options**:
- `--session TEXT`: Use existing session
- `--mock-llm`: Mock LLM responses

**Examples**:

```bash
# Start interactive shell
dataops-workflow shell my_analyzer

# With session
dataops-workflow shell my_analyzer --session sess_123
```

**Usage**:

```
DataOps Workflow Shell - my_analyzer
Type 'help' for commands, 'exit' to quit
================================================================================

workflow> input '{"query": "test"}'
Input set.

workflow> run
Running workflow...
✅ Complete (2.1s)

workflow> output
{
  "success": true,
  "result": "...",
  ...
}

workflow> artifacts
Artifacts:
  - art_123: result (json, 1.2 KB)
  - art_456: debug (text, 523 B)

workflow> trace
Execution trace:
  [START] → intent_detection (0.5s)
  [NODE] intent_detection → processing (1.2s)
  ...

workflow> exit
```

---

### 9. Convert Legacy Code

```bash
dataops-workflow convert [OPTIONS] SOURCE_FILE
```

**Description**: Convert legacy workflow code to new format

**Options**:
- `--type TEXT`: Source type (raw, legacy_v1)
- `--template TEXT`: Target template
- `--output, -o PATH`: Output directory

**Examples**:

```bash
# Convert legacy workflow
dataops-workflow convert old_workflow.py

# Specify output
dataops-workflow convert old_workflow.py \
  --output workflows/converted_workflow
```

---

### 10. Deploy Workflow

```bash
dataops-workflow deploy [OPTIONS] WORKFLOW_NAME
```

**Description**: Deploy workflow to production

**Options**:
- `--env TEXT`: Environment (dev, staging, prod)
- `--registry TEXT`: Registry URL
- `--tag TEXT`: Version tag

**Examples**:

```bash
# Deploy to staging
dataops-workflow deploy my_analyzer --env staging

# Deploy with version tag
dataops-workflow deploy my_analyzer \
  --env prod \
  --tag v1.2.0
```

---

## Configuration

### Global Config

Config file: `~/.dataops/config.yaml`

```yaml
# Default settings
defaults:
  template: simple
  author: "Your Name"
  output_dir: "./workflows"

# Testing
testing:
  mock_llm: false
  mock_tools: false
  timeout: 300

# Deployment
deployment:
  registry: "https://registry.example.com"
  default_env: "dev"

# AWS Settings (from environment or here)
aws:
  region: us-east-1
  s3_bucket: my-bucket
  dynamodb_table: my-table
```

### Workflow Config

Each workflow has `config.yaml`:

```yaml
name: my_analyzer
version: 1.0.0
description: Analyze data patterns

metadata:
  category: analysis
  author: Data Team
  tags:
    - analytics
    - patterns

parameters:
  - name: query
    type: string
    required: true
    description: User query

dependencies:
  - langchain>=0.1.0
  - pandas>=2.0.0

resources:
  timeout: 300
  max_memory: 1024

infrastructure:
  s3_enabled: true
  dynamodb_enabled: false
```

---

## Workflow Templates

### Simple Template

```python
# Generated by dataops-workflow create

from typing import TypedDict
from core.base_workflow import BaseWorkflow, WorkflowMetadata
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic

class {{WorkflowName}}State(TypedDict):
    """State for {{workflow_name}} workflow"""
    session_id: str
    workflow_name: str
    input: str
    output: str
    artifacts: list[str]

class {{WorkflowName}}Workflow(BaseWorkflow):
    """{{description}}"""

    def __init__(self):
        self.llm = ChatAnthropic(model="claude-sonnet-4-20250514")

    def get_metadata(self) -> WorkflowMetadata:
        return WorkflowMetadata(
            name="{{workflow_name}}",
            description="{{description}}",
            capabilities=[
                "TODO: Add capabilities"
            ],
            example_queries=[
                "TODO: Add example queries"
            ],
            category="{{category}}",
            author="{{author}}"
        )

    def get_compiled_graph(self):
        graph = StateGraph({{WorkflowName}}State)

        # Add nodes
        graph.add_node("process", self.process_node)

        # Add edges
        graph.add_edge(START, "process")
        graph.add_edge("process", END)

        return graph.compile()

    def process_node(self, state: {{WorkflowName}}State) -> dict:
        """Main processing node"""
        # TODO: Implement your logic here

        result = self.llm.invoke(state["input"])

        return {
            "output": result.content
        }

# For testing
if __name__ == "__main__":
    workflow = {{WorkflowName}}Workflow()
    graph = workflow.get_compiled_graph()

    result = graph.invoke({
        "session_id": "test",
        "workflow_name": "{{workflow_name}}",
        "input": "test input",
        "output": "",
        "artifacts": []
    })

    print("Result:", result)
```

---

## Best Practices

### 1. Naming Conventions

- Workflow names: lowercase with underscores (`data_analyzer`)
- Class names: PascalCase with Workflow suffix (`DataAnalyzerWorkflow`)
- State names: Workflow name + State (`DataAnalyzerState`)
- Node functions: verb_noun pattern (`process_data`, `format_output`)

### 2. Testing

```python
# Always include tests
from dataops.testing import WorkflowTestHarness

class TestMyWorkflow:
    def setup_method(self):
        self.workflow = MyWorkflow()
        self.harness = WorkflowTestHarness(self.workflow)

    def test_basic_execution(self):
        result = self.harness.workflow.invoke(test_input)
        self.harness.assert_output_format(result)
        assert result["success"] is True
```

### 3. Documentation

- Always fill in workflow metadata completely
- Provide multiple example queries
- Document node purposes with docstrings
- Include usage examples in README

### 4. Error Handling

```python
def my_node(state: MyState) -> dict:
    try:
        # Your logic
        result = process(state["input"])
        return {"output": result}
    except Exception as e:
        logger.error(f"Error in my_node: {e}")
        return {
            "output": "",
            "error": str(e)
        }
```

---

## Troubleshooting

### Workflow Not Found

```bash
$ dataops-workflow test my_workflow
Error: Workflow 'my_workflow' not found

Solution:
- Check workflow name spelling
- Ensure workflow is in workflows/ directory
- Verify __init__.py exists
- Run: dataops-workflow list
```

### Validation Errors

```bash
$ dataops-workflow validate my_workflow
Error: Invalid output contract

Solution:
- Check return format matches WorkflowResponse
- Ensure all required fields present
- Review contract documentation
```

### Import Errors

```bash
$ dataops-workflow test my_workflow
Error: ModuleNotFoundError: No module named 'special_lib'

Solution:
- Install workflow dependencies:
  cd workflows/my_workflow
  pip install -r requirements.txt
```

---

## API Reference

### Python API

Use CLI functionality programmatically:

```python
from dataops.cli import WorkflowCLI

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

# Validate workflow
validation = cli.validate_workflow(name="my_workflow")
print(validation.is_valid)
```

---

## Future Enhancements

- **AI-Assisted Creation**: Use LLM to generate workflow from description
- **Visual Editor**: GUI for building workflows
- **Remote Execution**: Run workflows on remote infrastructure
- **Workflow Marketplace**: Share and discover workflows
- **Auto-Optimization**: Suggest performance improvements
- **Workflow Versioning**: Git-integrated version management

---

**This CLI tool makes workflow development fast, consistent, and enjoyable!**

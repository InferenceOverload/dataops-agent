# Infrastructure Tools Usage Guide

This guide explains how to use the centralized infrastructure tools (S3, DynamoDB) in your workflows.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration](#configuration)
3. [S3 Tools](#s3-tools)
4. [DynamoDB Tools](#dynamodb-tools)
5. [Usage Patterns](#usage-patterns)
6. [Examples](#examples)

---

## Quick Start

### Import Tools

```python
# Import all tools at once
from infrastructure.tools import get_all_tools
tools = get_all_tools()

# Import specific categories
from infrastructure.tools import get_s3_tools, get_dynamodb_tools
s3_tools = get_s3_tools()
dynamodb_tools = get_dynamodb_tools()

# Import individual tools
from infrastructure.tools.s3_tools import S3ReadTool, S3WriteTool
from infrastructure.tools.dynamodb_tools import DynamoDBPutTool
```

### Use with LangChain Agents

```python
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_anthropic import ChatAnthropic
from infrastructure.tools import get_s3_tools

llm = ChatAnthropic(model="claude-sonnet-4-20250514")
tools = get_s3_tools()

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# Use in your workflow
response = llm_with_tools.invoke("Read the file from s3://my-bucket/data.txt")
```

---

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_S3_BUCKET=my-default-bucket
AWS_DYNAMODB_TABLE=my-default-table

# AWS Credentials (optional if using IAM roles)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Anthropic API Key (for LLM)
ANTHROPIC_API_KEY=your_anthropic_key
```

### Configuration Priority

The system uses the following priority (highest to lowest):

1. **Explicit parameters** in tool calls
2. **Runtime overrides** passed to AWSConfig
3. **Environment variables** (.env file)
4. **Default values** (fallback)

### Programmatic Configuration

```python
from infrastructure.config import get_aws_config

# Override default configuration
config = get_aws_config({
    "s3_bucket": "my-custom-bucket",
    "region": "us-west-2"
})

# Use with tools
bucket = config.get_s3_bucket()
region = config.get_region("s3")
```

---

## S3 Tools

### S3ReadTool

Read text content from S3.

**Parameters:**
- `key` (required): S3 object key (path)
- `bucket` (optional): S3 bucket name

**Example:**
```python
from infrastructure.tools.s3_tools import S3ReadTool

tool = S3ReadTool()
content = tool._run(
    key="jobs/batch_job.jil",
    bucket="my-data-bucket"  # Optional if AWS_S3_BUCKET is set
)
print(content)
```

**With LLM:**
```python
llm_with_tools = llm.bind_tools([S3ReadTool()])
response = llm_with_tools.invoke(
    "Read the JIL file at s3://my-bucket/jobs/batch_job.jil"
)
```

### S3WriteTool

Write text content to S3.

**Parameters:**
- `key` (required): S3 object key (path)
- `content` (required): Content to write
- `bucket` (optional): S3 bucket name

**Example:**
```python
from infrastructure.tools.s3_tools import S3WriteTool

tool = S3WriteTool()
result = tool._run(
    key="output/analysis_result.json",
    content='{"status": "completed"}',
    bucket="my-results-bucket"
)
```

### S3ListTool

List objects in S3 with a given prefix.

**Parameters:**
- `prefix` (required): S3 prefix (folder path)
- `bucket` (optional): S3 bucket name
- `max_keys` (optional): Maximum number of keys (default: 100)

**Example:**
```python
from infrastructure.tools.s3_tools import S3ListTool

tool = S3ListTool()
files = tool._run(
    prefix="jobs/autosys/",
    bucket="my-data-bucket",
    max_keys=50
)
print(files)
```

### S3ExistsTool

Check if an S3 object exists.

**Parameters:**
- `key` (required): S3 object key (path)
- `bucket` (optional): S3 bucket name

**Example:**
```python
from infrastructure.tools.s3_tools import S3ExistsTool

tool = S3ExistsTool()
exists = tool._run(
    key="jobs/batch_job.jil",
    bucket="my-data-bucket"
)
```

---

## DynamoDB Tools

### DynamoDBPutTool

Put (create/update) an item in DynamoDB.

**Parameters:**
- `item` (required): Item as JSON string
- `table` (optional): DynamoDB table name

**Example:**
```python
from infrastructure.tools.dynamodb_tools import DynamoDBPutTool
import json

tool = DynamoDBPutTool()
result = tool._run(
    item=json.dumps({
        "job_id": "BATCH_001",
        "status": "completed",
        "timestamp": "2025-01-14T10:30:00Z"
    }),
    table="jobs"
)
```

### DynamoDBGetTool

Get an item from DynamoDB by primary key.

**Parameters:**
- `key` (required): Primary key as JSON string
- `table` (optional): DynamoDB table name

**Example:**
```python
from infrastructure.tools.dynamodb_tools import DynamoDBGetTool
import json

tool = DynamoDBGetTool()
item = tool._run(
    key=json.dumps({"job_id": "BATCH_001"}),
    table="jobs"
)
print(item)
```

### DynamoDBQueryTool

Query DynamoDB with a key condition.

**Parameters:**
- `key_condition` (required): Key condition expression (e.g., "job_id = BATCH_001")
- `table` (optional): DynamoDB table name
- `limit` (optional): Maximum items to return (default: 10)

**Example:**
```python
from infrastructure.tools.dynamodb_tools import DynamoDBQueryTool

tool = DynamoDBQueryTool()
results = tool._run(
    key_condition="status = completed",
    table="jobs",
    limit=20
)
```

### DynamoDBScanTool

Scan DynamoDB table (use sparingly - expensive!).

**Parameters:**
- `table` (optional): DynamoDB table name
- `limit` (optional): Maximum items to return (default: 10)
- `filter_expression` (optional): Filter expression

**Example:**
```python
from infrastructure.tools.dynamodb_tools import DynamoDBScanTool

tool = DynamoDBScanTool()
results = tool._run(
    table="jobs",
    limit=20,
    filter_expression="status = completed"
)
```

**Warning:** Scan is expensive - prefer Query when possible!

---

## Usage Patterns

### Pattern 1: Simple Tool Usage in Workflow

```python
from langgraph.graph import StateGraph, START, END
from infrastructure.tools.s3_tools import S3ReadTool

class MyWorkflow(BaseWorkflow):
    def __init__(self):
        self.s3_read = S3ReadTool()

    def get_compiled_graph(self):
        def process_node(state):
            # Read file from S3
            content = self.s3_read._run(
                key=state['file_path'],
                bucket="my-bucket"
            )

            # Process content
            result = analyze(content)

            return {"output": result}

        graph = StateGraph(MyState)
        graph.add_node("process", process_node)
        graph.add_edge(START, "process")
        graph.add_edge("process", END)

        return graph.compile()
```

### Pattern 2: LLM with Tools (Agent Pattern)

```python
from langchain_anthropic import ChatAnthropic
from infrastructure.tools import get_s3_tools

class AdvancedWorkflow(BaseWorkflow):
    def __init__(self):
        self.llm = ChatAnthropic(model="claude-sonnet-4-20250514")
        self.s3_tools = get_s3_tools()
        self.llm_with_tools = self.llm.bind_tools(self.s3_tools)

    def get_compiled_graph(self):
        def agent_node(state):
            prompt = f"""You have access to S3 tools.

Read the file from {state['file_path']} and analyze it.
Use the s3_read_file tool to get the content."""

            # LLM decides which tools to call
            response = self.llm_with_tools.invoke(prompt)

            # Handle tool calls
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']

                    # Execute tool
                    for tool in self.s3_tools:
                        if tool.name == tool_name:
                            result = tool._run(**tool_args)
                            # Continue processing with result
                            break

            return {"output": response.content}

        # Build graph...
```

### Pattern 3: Multi-Tool Workflow

```python
from infrastructure.tools import get_s3_tools, get_dynamodb_tools

class ETLWorkflow(BaseWorkflow):
    def __init__(self):
        self.s3_tools = get_s3_tools()
        self.dynamodb_tools = get_dynamodb_tools()

        # Extract specific tools
        self.s3_read = next(t for t in self.s3_tools if t.name == "s3_read_file")
        self.s3_write = next(t for t in self.s3_tools if t.name == "s3_write_file")
        self.dynamodb_put = next(t for t in self.dynamodb_tools if t.name == "dynamodb_put_item")

    def get_compiled_graph(self):
        def extract_node(state):
            # Read from S3
            data = self.s3_read._run(key=state['input_file'])
            return {"raw_data": data}

        def transform_node(state):
            # Transform data
            transformed = transform(state['raw_data'])
            return {"transformed_data": transformed}

        def load_node(state):
            # Load to S3 and DynamoDB
            import json

            # Write result to S3
            self.s3_write._run(
                key=f"output/{state['job_id']}.json",
                content=state['transformed_data']
            )

            # Update status in DynamoDB
            self.dynamodb_put._run(
                item=json.dumps({
                    "job_id": state['job_id'],
                    "status": "completed",
                    "output_path": f"output/{state['job_id']}.json"
                })
            )

            return {"output": "ETL completed"}

        # Build graph with all nodes...
```

---

## Examples

### Example 1: JIL Parser with S3 Integration

See `workflows/jil_parser/workflow.py` for a complete example.

Key features:
- Detects S3 paths (s3://bucket/key)
- Uses S3ReadTool to fetch JIL files
- Processes content with LLM
- Supports both S3 and local files

### Example 2: Workflow with State Tracking

```python
import json
from infrastructure.tools.dynamodb_tools import DynamoDBPutTool, DynamoDBGetTool

class StatefulWorkflow(BaseWorkflow):
    def __init__(self):
        self.dynamodb_put = DynamoDBPutTool()
        self.dynamodb_get = DynamoDBGetTool()

    def get_compiled_graph(self):
        def start_node(state):
            # Record workflow start
            self.dynamodb_put._run(
                item=json.dumps({
                    "workflow_id": state['workflow_id'],
                    "status": "started",
                    "timestamp": datetime.now().isoformat()
                }),
                table="workflow_status"
            )
            return state

        def process_node(state):
            # Do work...
            result = process(state['input'])

            # Update status
            self.dynamodb_put._run(
                item=json.dumps({
                    "workflow_id": state['workflow_id'],
                    "status": "processing",
                    "progress": 50
                }),
                table="workflow_status"
            )

            return {"output": result}

        def complete_node(state):
            # Mark complete
            self.dynamodb_put._run(
                item=json.dumps({
                    "workflow_id": state['workflow_id'],
                    "status": "completed",
                    "result": state['output']
                }),
                table="workflow_status"
            )
            return state

        # Build graph...
```

### Example 3: File Discovery Workflow

```python
from infrastructure.tools.s3_tools import S3ListTool, S3ReadTool

class FileDiscoveryWorkflow(BaseWorkflow):
    def __init__(self):
        self.s3_list = S3ListTool()
        self.s3_read = S3ReadTool()

    def get_compiled_graph(self):
        def discover_node(state):
            # List all JIL files
            files = self.s3_list._run(
                prefix="jobs/autosys/",
                bucket="my-data-bucket",
                max_keys=100
            )

            # Parse file list
            file_keys = parse_file_list(files)

            return {"file_keys": file_keys}

        def process_node(state):
            results = []

            # Process each file
            for file_key in state['file_keys']:
                content = self.s3_read._run(key=file_key)
                result = analyze(content)
                results.append(result)

            return {"output": results}

        # Build graph...
```

---

## Best Practices

### 1. Always Use Configuration

Don't hardcode AWS credentials or bucket names:

```python
# Bad
s3_client = boto3.client('s3', aws_access_key_id='...', aws_secret_access_key='...')

# Good
from infrastructure.config import get_aws_config
config = get_aws_config()
s3_client = boto3.client('s3', **config.get_boto3_session_kwargs())
```

### 2. Handle Errors Gracefully

Tools return error messages as strings:

```python
result = tool._run(key="nonexistent.txt")
if "Error" in result:
    # Handle error
    print(f"Tool execution failed: {result}")
```

### 3. Use Appropriate Tools

- **S3ReadTool**: For reading file content
- **S3ExistsTool**: For checking existence (faster than reading)
- **S3ListTool**: For discovering files
- **DynamoDBQueryTool**: For targeted queries (preferred)
- **DynamoDBScanTool**: Only for small tables or when query isn't possible

### 4. Configure Defaults

Set environment variables for common configurations:

```bash
# .env
AWS_S3_BUCKET=my-main-bucket
AWS_DYNAMODB_TABLE=my-main-table
AWS_REGION=us-east-1
```

Then tools work without parameters:

```python
# No bucket needed if AWS_S3_BUCKET is set
content = S3ReadTool()._run(key="data.txt")
```

### 5. Document Tool Usage

In your workflow README, document which tools you use:

```markdown
## Required Configuration

This workflow uses the following AWS services:
- S3: Reads JIL files from configured bucket
- DynamoDB: Tracks analysis progress

Set these environment variables:
- AWS_S3_BUCKET=your-jil-files-bucket
- AWS_DYNAMODB_TABLE=jil-analysis-tracking
```

---

## Troubleshooting

### Issue: "No S3 bucket configured"

**Solution:** Set `AWS_S3_BUCKET` environment variable or pass `bucket` parameter:

```python
# Option 1: Set env var
# AWS_S3_BUCKET=my-bucket

# Option 2: Pass parameter
tool._run(key="file.txt", bucket="my-bucket")
```

### Issue: "Access Denied" errors

**Solution:** Check AWS credentials and permissions:

1. Verify credentials are set (or IAM role is configured)
2. Ensure bucket/table permissions allow the operation
3. Check bucket policies and IAM policies

### Issue: Tools not being called by LLM

**Solution:** Ensure tools are properly bound:

```python
# Correct
llm_with_tools = llm.bind_tools(tools)
response = llm_with_tools.invoke(prompt)

# Incorrect
response = llm.invoke(prompt)  # Tools not available!
```

---

## Next Steps

- See `workflows/jil_parser/workflow.py` for a complete example
- Check `.env.example` for configuration template
- Read `ARCHITECTURE.md` for system design principles
- Explore `infrastructure/tools/` for tool implementations

For questions or issues, see the [main README](../README.md).

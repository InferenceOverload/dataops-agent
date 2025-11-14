# DataOps Agent

**Intelligent Multi-Agent System for Data Engineering Workflows**

A production-grade orchestration system that dynamically routes data engineering tasks to specialized AI agent workflows using LangGraph and LangChain, with built-in AWS infrastructure tools and intelligent parameter gathering.

---

## 🎯 Overview

DataOps Agent is an intelligent orchestration system that:
- **Understands natural language queries** about data engineering tasks
- **Intelligently extracts required parameters** and asks for missing information
- **Routes to specialized workflows** based on capability matching
- **Provides centralized AWS tools** for S3, DynamoDB, and more
- **Manages multi-agent coordination** using supervisor and iterative patterns
- **Supports contract-based workflow development** for easy integration

### Architecture

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
                                    (Simple, Supervisor,
                                     Iterative, JIL Parser)
                                              ↓
                                      Response Formatting
```

---

## ✨ Key Features

### 🎯 Contract-Based Parameter System
- Workflows declare their input requirements explicitly
- Orchestrator intelligently extracts parameters from natural language
- Automatically prompts for missing required information
- Type-safe parameter validation with Pydantic

### 🔧 Centralized Infrastructure Tools
- **S3 Tools**: Read, write, list, check existence
- **DynamoDB Tools**: Put, get, query, scan
- **LangChain Native**: BaseTool implementations for agent use
- **Configuration Priority**: Explicit → Overrides → Environment → Defaults

### 🤖 Intelligent Workflow Routing
- Auto-discovery of workflows from metadata
- Capability-based intent detection
- Meta-query handling for system introspection
- Graceful handling of unknown intents

### 📦 Production-Ready Infrastructure
- Environment-based configuration
- IAM role support (no hardcoded credentials)
- Comprehensive documentation and examples
- Type hints and error handling throughout

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Anthropic API key ([Get one here](https://console.anthropic.com/))
- (Optional) AWS credentials for S3/DynamoDB tools

### Installation

```bash
# Clone the repository
git clone https://github.com/InferenceOverload/dataops-agent.git
cd dataops-agent

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env and add your credentials:
# - ANTHROPIC_API_KEY (required for personal use)
# - OR configure AWS Bedrock for corporate deployment
# - AWS_S3_BUCKET (optional, for S3 tools)
# - AWS_DYNAMODB_TABLE (optional, for DynamoDB tools)
```

**Corporate Environments:** If you encounter SSL/TLS certificate errors or proxy issues, see the [Corporate Setup Guide](CORPORATE_SETUP.md) for detailed configuration instructions.

### Run Locally

```bash
# Start LangGraph dev server
langgraph dev
# Open http://localhost:2024/docs

# Test orchestrator directly
python core/orchestrator.py

# Test specific workflow
python workflows/jil_parser/workflow.py
```

---

## 📁 Project Structure

```
dataops-agent/
├── core/                       # Core orchestrator system
│   ├── base_workflow.py       # BaseWorkflow interface & contracts
│   ├── orchestrator.py        # Main orchestrator with parameter extraction
│   └── workflow_registry.py   # Auto-discovery & registration
│
├── workflows/                  # Workflow implementations
│   ├── workflow_a.py          # Simple single-agent workflow
│   ├── workflow_b.py          # Supervisor multi-agent pattern
│   ├── workflow_c.py          # Iterative refinement pattern
│   └── jil_parser/            # JIL dependency parser (example)
│       ├── workflow.py        # Workflow implementation
│       ├── config.yaml        # Workflow-specific config
│       └── README.md          # Usage documentation
│
├── infrastructure/             # Centralized infrastructure tools
│   ├── config/                # AWS configuration management
│   │   └── aws_config.py      # Configuration priority system
│   ├── tools/                 # LangChain tools
│   │   ├── s3_tools.py        # S3 operations (read, write, list, exists)
│   │   └── dynamodb_tools.py  # DynamoDB operations (put, get, query, scan)
│   ├── storage/               # Base utilities (reference implementations)
│   │   ├── s3_operations.py
│   │   └── dynamodb_operations.py
│   └── llm/                   # LLM utilities
│       └── bedrock_client.py  # Bedrock LLM client
│
├── tests/                      # Test suite
│   ├── test_base_workflow.py
│   ├── test_workflow_registry.py
│   └── test_orchestrator.py
│
├── docs/                       # Documentation
│   ├── architecture.md        # System architecture
│   ├── tools-usage-guide.md   # Infrastructure tools guide
│   └── LANGGRAPH_PATTERNS.md  # LangGraph patterns
│
└── [config files]
```

---

## 🤖 Available Workflows

### 1. Simple Agent (`workflow_a`)
**Use Case:** Basic queries, single-step tasks

**Example:** "What is LangGraph?"

**Pattern:** Single LLM call → Response

**Required Inputs:** None (uses query directly)

---

### 2. Supervisor Pattern (`workflow_b`)
**Use Case:** Complex tasks requiring research + analysis

**Example:** "Research cloud computing and analyze its benefits"

**Pattern:** Supervisor coordinates multiple specialist agents

**Required Inputs:** None (uses query directly)

---

### 3. Iterative Refinement (`workflow_c`)
**Use Case:** Progressive improvement, multi-iteration analysis

**Example:** "Iteratively develop an analysis of AI safety"

**Pattern:** Loop with artifacts, refinement over 3 iterations

**Required Inputs:** None (uses query directly)

---

### 4. JIL Parser (`jil_parser`)
**Use Case:** Analyze Autosys JIL files for job dependencies

**Example:** "Parse JIL dependencies for BATCH_PROCESSING job in s3://my-bucket/jobs/batch.jil"

**Pattern:** Iterative analysis with S3 integration

**Required Inputs:**
- `file_path` (required): Path to JIL file (supports s3:// URIs)
- `current_job` (required): Job name to analyze
- `max_iterations` (optional, default: 3): Max analysis iterations

**Features:**
- Auto-detects S3 paths and uses S3 tools
- LLM-powered dependency discovery
- Structured output with upstream/downstream jobs

---

### 5. Meta Queries
**Use Case:** Questions about the system itself

**Example:** "What can you do?"

**Pattern:** Direct system response with capability listing

---

## 🔧 Using Infrastructure Tools

### S3 Tools

```python
from infrastructure.tools import get_s3_tools

# Get all S3 tools
tools = get_s3_tools()

# Use with LangChain agent
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-sonnet-4-20250514")
llm_with_tools = llm.bind_tools(tools)

# LLM can now call S3 operations
response = llm_with_tools.invoke("Read the file from s3://my-bucket/data.txt")
```

### DynamoDB Tools

```python
from infrastructure.tools.dynamodb_tools import DynamoDBPutTool
import json

# Track workflow state
put_tool = DynamoDBPutTool()
put_tool._run(
    item=json.dumps({"job_id": "BATCH_001", "status": "completed"}),
    table="jobs"  # Optional if AWS_DYNAMODB_TABLE is set
)
```

### Configuration

Set environment variables in `.env`:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_S3_BUCKET=my-default-bucket
AWS_DYNAMODB_TABLE=my-default-table

# AWS Credentials (optional if using IAM roles)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

See [Tools Usage Guide](docs/tools-usage-guide.md) for comprehensive documentation.

---

## 🏗️ Building Custom Workflows

### Step 1: Create Workflow Structure

```bash
mkdir -p workflows/my_workflow
touch workflows/my_workflow/__init__.py
touch workflows/my_workflow/workflow.py
```

### Step 2: Implement BaseWorkflow

```python
from core.base_workflow import BaseWorkflow, WorkflowMetadata, WorkflowInputParameter
from langgraph.graph import StateGraph, START, END

class MyWorkflow(BaseWorkflow):
    def get_metadata(self) -> WorkflowMetadata:
        return WorkflowMetadata(
            name="my_workflow",
            description="What this workflow does",
            capabilities=["capability 1", "capability 2"],
            example_queries=["Example user query"],
            category="category",
            required_inputs=[
                WorkflowInputParameter(
                    name="param_name",
                    description="What this parameter is for",
                    type="string",
                    required=True,
                    example="example_value",
                    prompt="What should I ask the user?"
                )
            ]
        )

    def get_compiled_graph(self):
        # Build your LangGraph
        graph = StateGraph(MyState)
        # ... add nodes and edges
        return graph.compile()
```

### Step 3: Auto-Discovery

The registry automatically discovers workflows on startup. No registration needed!

### Step 4: Use Infrastructure Tools (Optional)

```python
from infrastructure.tools import get_s3_tools, get_dynamodb_tools

class MyWorkflow(BaseWorkflow):
    def __init__(self):
        self.s3_tools = get_s3_tools()
        # Use in your workflow nodes
```

See workflow development guide in [CLAUDE.md](.claude/CLAUDE.md) for details.

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Test workflows
pytest tests/test_workflow_registry.py -v

# Test orchestrator
pytest tests/test_orchestrator.py -v

# Test infrastructure tools
pytest tests/test_infrastructure.py -v

# Test specific workflow
python workflows/jil_parser/workflow.py
```

---

## 📊 Example Queries

### Meta Queries
```
"What can you do?"
"What workflows are available?"
"Show me your capabilities"
```

### Simple Queries (No Parameters Needed)
```
"What is data engineering?"
"Explain ETL processes"
"What is LangGraph?"
```

### Complex Queries (Auto-Detected Intent)
```
"Research modern data stack tools and analyze their tradeoffs"
"Iteratively develop a data governance strategy"
```

### JIL Parser (Parameter Extraction)
```
# Missing parameters - orchestrator will ask
"Parse JIL dependencies"

# Complete query - runs immediately
"Parse JIL dependencies for BATCH_PROCESSING job in s3://my-bucket/jobs/batch.jil"

# Partial query - orchestrator asks for missing info
"Analyze job ETL_MASTER in /data/jobs.jil"
```

---

## 🔒 Security

### Environment Variables
- All sensitive data in `.env` (gitignored)
- `.env.example` provides template
- Never commit actual credentials

### AWS Credentials
- Supports IAM roles (no credentials needed in AWS)
- Falls back to environment variables for local dev
- Priority: IAM role → env vars → error

### Best Practices
- Use IAM roles in production
- Rotate credentials regularly
- Limit S3 bucket permissions
- Use DynamoDB table-level permissions

---

## 📖 Documentation

- [Architecture](docs/architecture.md) - System design and patterns
- [Tools Usage Guide](docs/tools-usage-guide.md) - Infrastructure tools reference
- [LangGraph Patterns](docs/LANGGRAPH_PATTERNS.md) - Multi-agent patterns
- [Development Guide](.claude/CLAUDE.md) - Workflow development tasks

---

## 🚢 Deployment

### Local Development
```bash
langgraph dev
```

### Docker (Coming Soon)
```bash
docker build -t dataops-agent .
docker run -p 8000:8000 dataops-agent
```

### Production Checklist
- [ ] Set environment variables
- [ ] Configure AWS credentials (IAM roles recommended)
- [ ] Set S3 bucket and DynamoDB table
- [ ] Enable LangSmith tracing (optional)
- [ ] Configure monitoring and logging

---

## 🛣️ Roadmap

### ✅ Completed
- [x] Contract-based parameter system
- [x] Centralized infrastructure tools (S3, DynamoDB)
- [x] Auto-discovery workflow registry
- [x] Intelligent parameter extraction
- [x] JIL parser with S3 integration
- [x] Comprehensive documentation

### 🚧 In Progress
- [ ] Additional workflow examples
- [ ] Enhanced error handling
- [ ] Async tool support

### 📋 Planned
- [ ] More infrastructure tools (RDS, Bedrock, etc.)
- [ ] Workflow versioning
- [ ] Human-in-the-loop approvals
- [ ] Monitoring and observability
- [ ] API layer (FastAPI)
- [ ] Docker containerization
- [ ] Kubernetes deployment

---

## 🤝 Contributing

This project uses:
- **LangGraph** for multi-agent orchestration
- **LangChain** for LLM integrations and tools
- **Anthropic Claude** as the LLM provider
- **boto3** for AWS integration
- **Pydantic** for type safety
- **Python 3.10+** with type hints
- **pytest** for testing

Development workflow:
1. Create feature branch
2. Implement changes
3. Add tests
4. Update documentation
5. Submit PR

---

## 📝 License

MIT License - See LICENSE file

---

## 🔗 Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
- [Anthropic Claude](https://www.anthropic.com/claude)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

---

## 🙏 Acknowledgments

Built with:
- LangGraph and LangChain by LangChain AI
- Claude by Anthropic
- AWS SDK (boto3)

---

**Built for Data Engineers, by Data Engineers** 🚀

*Intelligent orchestration meets infrastructure automation*

# MLflow Integration for LangGraph Workflows

## Overview

The DataOps Agent now includes comprehensive MLflow integration for tracking and tracing all LangGraph workflow executions. This integration provides:

- **Automatic Tracing**: Zero-code tracing of all LangGraph workflows via `mlflow.langchain.autolog()`
- **Experiment Tracking**: Organized tracking of workflow runs with parameters, metrics, and artifacts
- **Performance Monitoring**: Execution time, iterations, and resource usage tracking
- **Artifact Management**: Storage and versioning of workflow outputs
- **LangSmith Alternative**: Complete replacement for LangSmith with self-hosted or cloud options

## Features

### 1. Automatic Workflow Tracing

All LangGraph workflows are automatically traced without any code changes:

- **Orchestrator**: Main intent detection and routing
- **Workflow A (Simple)**: Single LLM call workflows
- **Workflow B (Supervisor)**: Multi-agent coordination patterns
- **Workflow C (Iterative)**: Progressive refinement loops
- **Workflow D (JIL Parser)**: Domain-specific parsing workflows

### 2. Comprehensive Metrics

Each workflow execution logs:

- **Execution Time**: Total time in seconds
- **Iterations**: Number of loop iterations (for iterative workflows)
- **Artifacts Count**: Number of generated artifacts
- **Messages Count**: Agent message exchanges (for supervisor patterns)
- **Success/Failure**: Boolean flag with error details

### 3. Parameter Tracking

All workflow inputs are logged:

- User query (natural language input)
- Workflow name
- Extracted parameters
- Configuration values (max_iterations, etc.)

### 4. Hierarchical Runs

Nested run support for tracking:

- Orchestrator run (parent)
- Individual workflow runs (children)
- Node-level execution (optional, configurable)

## Installation

### Option 1: Install with Observability Dependencies

```bash
pip install -e ".[observability]"
```

This installs MLflow along with other observability tools (OpenTelemetry, Prometheus, structlog).

### Option 2: Minimal Installation

If you only want core dependencies plus MLflow:

```bash
pip install -e .
pip install mlflow>=2.14.0
```

### Option 3: Using UV (Recommended)

```bash
uv sync --extra observability
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# MLflow Tracking Server URI
# Local: ./mlruns (default)
# Remote: http://mlflow.company.com
MLFLOW_TRACKING_URI=./mlruns

# Experiment name for all workflow runs
MLFLOW_EXPERIMENT_NAME=dataops-agent-workflows

# Enable automatic tracing (recommended)
MLFLOW_ENABLE_AUTO_LOGGING=true

# Optional: S3 artifact storage
# MLFLOW_ARTIFACT_LOCATION=s3://my-bucket/mlflow-artifacts

# Environment tag (development/staging/production)
MLFLOW_ENVIRONMENT=development

# Enable nested runs for node-level tracking
MLFLOW_ENABLE_NESTED_RUNS=true

# Logging level
MLFLOW_LOG_LEVEL=INFO
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `MLFLOW_TRACKING_URI` | `./mlruns` | Local path or remote server URL |
| `MLFLOW_EXPERIMENT_NAME` | `dataops-agent-workflows` | Experiment name for runs |
| `MLFLOW_ENABLE_AUTO_LOGGING` | `true` | Auto-trace LangGraph workflows |
| `MLFLOW_ARTIFACT_LOCATION` | None | S3 or custom artifact store |
| `MLFLOW_REGISTRY_URI` | None | Separate model registry server |
| `MLFLOW_LOG_LEVEL` | `INFO` | Logging verbosity |
| `MLFLOW_ENABLE_NESTED_RUNS` | `true` | Track individual nodes |
| `MLFLOW_ENVIRONMENT` | `development` | Environment tag |

## Usage

### Automatic Tracking (Recommended)

No code changes needed! Just run your workflows normally:

```python
from core.orchestrator import orchestrator_graph

# MLflow is automatically initialized on import
result = orchestrator_graph.invoke({
    "user_query": "Analyze the JIL file dependencies",
    "detected_intent": "",
    "extracted_parameters": {},
    "missing_parameters": [],
    "workflow_result": {},
    "final_response": ""
})

# Execution is automatically logged to MLflow!
```

### Manual Tracking (Advanced)

For custom tracking or additional metrics:

```python
from infrastructure.observability import mlflow_run

with mlflow_run(run_name="custom-analysis", tags={"version": "1.0"}):
    result = workflow.invoke(state)

    # Log custom metrics
    import mlflow
    mlflow.log_metric("custom_metric", 42.0)
    mlflow.log_param("custom_param", "value")
```

### Programmatic Configuration

```python
from infrastructure.observability import get_mlflow_config, initialize_mlflow

# Get current configuration
config = get_mlflow_config()
print(f"Tracking URI: {config.tracking_uri}")
print(f"Experiment: {config.experiment_name}")

# Initialize manually (usually automatic)
initialize_mlflow()
```

## Viewing Results

### Local MLflow UI

Start the MLflow tracking server:

```bash
mlflow ui --backend-store-uri ./mlruns
```

Then open http://localhost:5000 in your browser.

### Remote MLflow Server

If using a remote server (configured via `MLFLOW_TRACKING_URI`), navigate to that URL.

### CLI Commands

```bash
# List experiments
mlflow experiments list

# Search runs
mlflow runs list --experiment-name dataops-agent-workflows

# Get run details
mlflow runs describe --run-id <run-id>
```

## What Gets Tracked

### Orchestrator Execution

- **Parameters**: User query, detected intent
- **Metrics**: Execution time, success/failure
- **Tags**: Workflow type, environment
- **Artifacts**: None (orchestrator coordinates)

### Workflow Execution

#### Simple Workflow (Workflow A)
- **Parameters**: Input query
- **Metrics**: Execution time
- **Artifacts**: LLM response

#### Supervisor Workflow (Workflow B)
- **Parameters**: Input query
- **Metrics**: Execution time, message count
- **Artifacts**: Worker outputs, supervisor decisions
- **Traces**: Agent coordination flow

#### Iterative Workflow (Workflow C)
- **Parameters**: Input query, max_iterations
- **Metrics**: Execution time, actual iterations, artifact count
- **Artifacts**: Results from each iteration with timestamps
- **Traces**: Refinement loop progression

#### JIL Parser Workflow (Workflow D)
- **Parameters**: File path, current_job, max_iterations
- **Metrics**: Execution time, iterations, visited files count
- **Artifacts**: Dependency graph, parsed JIL data
- **Traces**: File access, tool usage, dependency discovery

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Application                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              core/orchestrator.py                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  initialize_mlflow()  ← Automatic on import          │   │
│  └──────────────────────────────────────────────────────┘   │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  workflow.invoke()  ← Auto-traced by MLflow          │   │
│  │  + Manual metrics logging                            │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         infrastructure/observability/mlflow_config.py       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  MLflowConfig (settings from .env)                   │   │
│  │  mlflow.set_tracking_uri()                           │   │
│  │  mlflow.set_experiment()                             │   │
│  │  mlflow.langchain.autolog()  ← Magic happens here   │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 MLflow Tracking Server                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ Experiments│  │   Runs     │  │ Artifacts  │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│         Local: ./mlruns   OR   Remote: HTTP Server          │
└─────────────────────────────────────────────────────────────┘
```

## Best Practices

### 1. Use Meaningful Experiment Names

Organize runs by project or use case:

```bash
MLFLOW_EXPERIMENT_NAME=dataops-production-workflows
```

### 2. Tag Runs with Environment

Always set the environment tag:

```bash
MLFLOW_ENVIRONMENT=production  # or development, staging
```

### 3. Use S3 for Production Artifacts

Configure S3 storage for production:

```bash
MLFLOW_ARTIFACT_LOCATION=s3://my-company-mlflow/artifacts
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

### 4. Enable Nested Runs During Development

Track individual nodes for debugging:

```bash
MLFLOW_ENABLE_NESTED_RUNS=true
```

Disable in production for performance:

```bash
MLFLOW_ENABLE_NESTED_RUNS=false
```

### 5. Regular Cleanup

Archive old experiments:

```bash
mlflow gc --backend-store-uri ./mlruns --older-than 30d
```

## Comparison with LangSmith

| Feature | MLflow | LangSmith |
|---------|--------|-----------|
| **Self-hosted** | ✅ Yes | ❌ No |
| **Cost** | Free (open-source) | Paid SaaS |
| **LangGraph Tracing** | ✅ Full support | ✅ Full support |
| **Artifact Storage** | S3, Azure, GCS, local | LangSmith cloud |
| **Model Registry** | ✅ Built-in | Limited |
| **Experiment Comparison** | ✅ Advanced UI | Basic |
| **Custom Metrics** | ✅ Unlimited | Limited |
| **Data Privacy** | ✅ Full control | Shared SaaS |
| **Integration Effort** | Low (auto-trace) | Low (auto-trace) |

## Troubleshooting

### MLflow Not Initializing

**Error**: `ImportError: No module named 'mlflow'`

**Solution**: Install observability dependencies:
```bash
pip install -e ".[observability]"
```

### Runs Not Appearing

**Check**:
1. Is `MLFLOW_ENABLE_AUTO_LOGGING=true`?
2. Is the tracking URI correct?
3. Is the experiment name valid?

**Debug**:
```python
from infrastructure.observability import is_mlflow_available, get_mlflow_config

print(f"MLflow available: {is_mlflow_available()}")
print(f"Config: {get_mlflow_config()}")
```

### S3 Artifact Storage Issues

**Error**: `botocore.exceptions.NoCredentialsError`

**Solution**: Configure AWS credentials:
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
```

### Corporate SSL Certificates

If using corporate SSL interception:

```bash
SSL_CERT_FILE=/etc/ssl/certs/corporate-ca-bundle.crt
REQUESTS_CA_BUNDLE=/etc/ssl/certs/corporate-ca-bundle.crt
```

## Advanced Topics

### Custom Experiment Organization

Create multiple experiments for different use cases:

```python
import mlflow

# Create specialized experiments
mlflow.create_experiment(
    "jil-parser-production",
    artifact_location="s3://prod-bucket/jil-parser"
)

mlflow.create_experiment(
    "supervisor-workflows-dev",
    artifact_location="./dev-artifacts"
)
```

### Querying Runs Programmatically

```python
import mlflow

client = mlflow.tracking.MlflowClient()

# Get all runs from an experiment
runs = client.search_runs(
    experiment_ids=["1"],
    filter_string="params.workflow_name = 'jil_parser'",
    order_by=["metrics.execution_time_seconds DESC"]
)

for run in runs:
    print(f"Run ID: {run.info.run_id}")
    print(f"Execution time: {run.data.metrics['execution_time_seconds']}s")
```

### A/B Testing Workflows

Compare different workflow configurations:

```python
# Version A
with mlflow.start_run(tags={"version": "A", "max_iterations": "3"}):
    result_a = workflow.invoke({"max_iterations": 3, ...})

# Version B
with mlflow.start_run(tags={"version": "B", "max_iterations": "5"}):
    result_b = workflow.invoke({"max_iterations": 5, ...})

# Compare in MLflow UI
```

## Example: Complete Workflow with MLflow

```python
#!/usr/bin/env python3
"""Example: Running workflows with MLflow tracking"""

from core.orchestrator import orchestrator_graph
from infrastructure.observability import get_active_run_id, is_mlflow_available

def main():
    print(f"MLflow enabled: {is_mlflow_available()}")

    # Execute workflow (automatically tracked)
    result = orchestrator_graph.invoke({
        "user_query": "Iteratively refine an analysis of cloud data pipelines",
        "detected_intent": "",
        "extracted_parameters": {},
        "missing_parameters": [],
        "workflow_result": {},
        "final_response": ""
    })

    # Get run information
    run_id = get_active_run_id()
    if run_id:
        print(f"\nMLflow Run ID: {run_id}")
        print(f"View at: http://localhost:5000/#/experiments/1/runs/{run_id}")

    print(f"\nResult: {result['final_response']}")

if __name__ == "__main__":
    main()
```

## References

- [MLflow Documentation](https://mlflow.org/docs/latest/)
- [MLflow LangGraph Integration](https://mlflow.org/docs/latest/tracing/integrations/langgraph)
- [LangChain MLflow Tracking](https://python.langchain.com/docs/integrations/providers/mlflow_tracking/)

## Support

For issues or questions about the MLflow integration:

1. Check the troubleshooting section above
2. Review MLflow logs: `tail -f ./mlruns/.../meta.yaml`
3. Verify configuration: Review `.env` settings
4. Test MLflow independently: `mlflow ui --help`

---

**Last Updated**: 2025-11-14
**Version**: 1.0.0
**Compatible with**: MLflow >= 2.14.0, LangGraph >= 0.2.0

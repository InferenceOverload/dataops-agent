# Oracle Package Analyzer Workflow

Analyzes Oracle PL/SQL packages to recursively discover procedures, dependencies, and column-level lineage. The workflow produces a comprehensive Knowledge Artifact stored in S3.

## Overview

This workflow takes a root Oracle package and performs deep analysis to:

- Extract all procedures and functions within the package
- Discover table and view dependencies
- Trace column-level data lineage
- Map procedure call chains across packages
- Generate migration hints for cloud/Snowflake migration
- Store structured knowledge artifacts in S3

## Architecture

The workflow uses a task-based iterative approach with the following nodes:

1. **init_scope**: Initialize analysis and fetch root package source
2. **pick_next_task**: Orchestrator that selects next analysis task from queue
3. **decompose_package**: Scout that discovers package contents and dependencies
4. **analyze_unit**: Worker that analyzes individual procedures/views/triggers
5. **finalize_knowledge**: Builds final knowledge artifact and stores to S3

## Required Environment Variables

Configure these in your `.env` file:

```bash
# Oracle Database Connection
ORACLE_DSN=host:port/service_name          # e.g., dbserver.company.com:1521/PROD
ORACLE_USER=my_user                        # Oracle database username
ORACLE_PASSWORD=my_password                # Oracle database password

# Default schema (optional)
ORACLE_SCHEMA_DEFAULT=BILLING              # Default schema if not specified

# S3 Storage
ORACLE_CODE_S3_BUCKET=my-oracle-code-bucket  # S3 bucket for artifacts

# AWS Credentials (if not using IAM roles)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# LLM Provider (Anthropic or Bedrock)
LLM_PROVIDER=bedrock                       # or 'anthropic'
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_REGION=us-east-1
```

## Installation

### Prerequisites

1. Python 3.11+
2. Oracle database access
3. AWS S3 bucket
4. Anthropic API key or AWS Bedrock access

### Install Dependencies

The workflow requires the `oracledb` Python package:

```bash
# Using uv (recommended)
uv pip install oracledb

# Or using pip
pip install oracledb
```

## Usage

### Example Invocation

```python
from workflows.oracle_package_analyzer.workflow import OraclePackageAnalyzerWorkflow

# Create workflow instance
workflow = OraclePackageAnalyzerWorkflow()
graph = workflow.get_compiled_graph()

# Define input
input_state = {
    "root_package_name": "BILLING.PKG_POLICY_BILLING",  # Required
    "max_depth": 2,                                      # Optional (default: 3)
    "include_cross_schema": False                        # Optional (default: False)
}

# Execute workflow
result = graph.invoke(input_state)

# Access results
print(f"Status: {result['status']}")
print(f"Knowledge Artifact: {result['knowledge_artifact_uri']}")
print(f"Units Analyzed: {len(result['units'])}")
print(f"Tables Found: {len(result['tables'])}")
print(f"Packages Found: {len(result['packages'])}")
```

### Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `root_package_name` | string | Yes | - | Oracle package to analyze in `SCHEMA.PACKAGE_NAME` format (e.g., `BILLING.PKG_POLICY_BILLING`) |
| `max_depth` | integer | No | 3 | Maximum recursion depth for dependency discovery |
| `include_cross_schema` | boolean | No | false | Whether to include dependencies from other schemas |

### Output

The workflow produces:

1. **Knowledge Artifact JSON** stored in S3 at:
   ```
   s3://{ORACLE_CODE_S3_BUCKET}/oracle/knowledge/{SCHEMA}.{PACKAGE}.json
   ```

2. **Raw PL/SQL Source** stored in S3 at:
   ```
   s3://{ORACLE_CODE_S3_BUCKET}/oracle/raw/{SCHEMA}/{PACKAGE}.sql
   ```

### Knowledge Artifact Structure

```json
{
  "root_package": "BILLING.PKG_POLICY_BILLING",
  "units": [
    {
      "unit_type": "procedure",
      "qualified_name": "BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE",
      "signature": {
        "parameters": [...],
        "return_type": "..."
      },
      "reads_from": [
        {"table": "BILLING.POLICIES", "columns": ["POLICY_ID", "PREMIUM"]}
      ],
      "writes_to": [...],
      "column_lineage": [...],
      "calls": ["BILLING.PKG_UTILS.LOG_EVENT"],
      "control_flow": {...},
      "globals_used": ["G_DEFAULT_RATE"],
      "summary": "Calculates late fees for overdue policy payments...",
      "migration_hints": [
        "Replace global variable G_DEFAULT_RATE with config table in Snowflake",
        "Consider using Snowflake stored procedures or Python UDFs"
      ]
    }
  ],
  "tables": ["BILLING.POLICIES", "BILLING.PAYMENTS", ...],
  "views": ["BILLING.VW_ACTIVE_POLICIES", ...],
  "packages": ["BILLING.PKG_POLICY_BILLING", "BILLING.PKG_UTILS", ...],
  "edges": [
    {"from": "BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE", "to": "BILLING.POLICIES", "type": "READS"},
    {"from": "BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE", "to": "BILLING.PKG_UTILS.LOG_EVENT", "type": "CALLS"}
  ]
}
```

## Configuration

Edit `workflows/oracle_package_analyzer/config.yaml` to customize:

```yaml
analysis:
  default_max_depth: 3                    # Default recursion depth
  include_cross_schema_default: false     # Default cross-schema policy
  llm_temperature: 0.0                    # LLM temperature for analysis
  max_code_lines: 500                     # Max lines per LLM call

storage:
  s3_bucket_env_var: ORACLE_CODE_S3_BUCKET
  raw_prefix: "oracle/raw"
  knowledge_prefix: "oracle/knowledge"
```

## Example Queries

The workflow responds to natural language queries like:

- "Analyze package BILLING.PKG_POLICY_BILLING"
- "Understand dependencies of CLAIMS.PKG_RESERVE_CALC"
- "What are the lineage impacts of FINANCE.PKG_GL_PROCESSING?"
- "Map all dependencies for CUSTOMER.PKG_ACCOUNT_MGMT"

## Capabilities

- Extract PL/SQL package procedures and functions
- Discover table and view dependencies
- Trace column-level data lineage
- Map procedure call chains
- Generate migration hints for cloud migration
- Store knowledge artifacts in S3

## Troubleshooting

### Connection Issues

If you encounter Oracle connection errors:

1. Verify `ORACLE_DSN`, `ORACLE_USER`, and `ORACLE_PASSWORD` are set correctly
2. Ensure network connectivity to Oracle database
3. Check firewall rules allow connection to Oracle port (typically 1521)
4. Test connection with:
   ```python
   from infrastructure.storage import oracle_operations
   oracle_operations.test_oracle_connection()
   ```

### Missing Packages

If packages are not found:

1. Verify the schema and package name are correct (case-insensitive)
2. Ensure the Oracle user has `SELECT` permission on `ALL_SOURCE`
3. Check if the package exists in the schema:
   ```sql
   SELECT OWNER, OBJECT_NAME, OBJECT_TYPE
   FROM ALL_OBJECTS
   WHERE OBJECT_TYPE IN ('PACKAGE', 'PACKAGE BODY')
     AND OBJECT_NAME = 'PKG_POLICY_BILLING';
   ```

### S3 Upload Failures

If S3 uploads fail:

1. Verify `ORACLE_CODE_S3_BUCKET` environment variable is set
2. Ensure AWS credentials have write permission to the bucket
3. Check bucket exists and is in the correct region

## Implementation Notes

### Parsing Strategy

The current implementation uses regex-based parsing for:
- Procedure/function extraction
- Table reference detection
- Package call discovery

This provides good coverage for most PL/SQL code. For more sophisticated analysis, consider integrating a full PL/SQL parser like:
- Oracle SQL Developer's parser
- ANTLR-based PL/SQL grammar
- pgAdmin's SQL parser (adapted)

### LLM Usage

The workflow uses LLM calls for:
- Generating natural-language summaries of procedures
- Creating migration hints specific to each unit

LLM temperature is set to 0.0 (deterministic) in the default configuration for consistent results.

### Scalability

For large packages with 100+ procedures:
- The workflow processes units iteratively to manage memory
- S3 caching prevents re-fetching package source
- Consider increasing `max_depth` carefully to avoid exponential growth

## Version

- **Version**: 1.0.0
- **Author**: Data Engineering Team
- **Category**: Code Analysis

## License

See repository root for license information.

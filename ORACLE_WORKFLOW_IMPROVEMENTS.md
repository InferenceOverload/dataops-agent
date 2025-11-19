# Oracle Workflow Improvements - v2.0

## Summary

The Oracle Package Analyzer workflow has been significantly enhanced to address the identified gaps in dependency analysis and data flow tracking. The workflow now performs deep, recursive analysis of PL/SQL packages with comprehensive dependency tracking and data lineage extraction.

## What Was Fixed

### 1. Deep Dependency Tracking ✅

**Before (v1.0):**
- Only tracked package-level dependencies
- When `PKG_A.PROC1` called `PKG_B.PROC2`, only captured `PKG_B`
- No procedure-to-procedure call graph

**After (v2.0):**
- Extracts precise procedure calls: `SCHEMA.PKG.PROC` format
- Builds complete procedure-to-procedure call graphs
- Clearly identifies `PKG_A.PROC1` → `PKG_B.PROC2` relationships

### 2. Data Flow and Transformation Analysis ✅

**Before (v1.0):**
- Column lineage arrays were empty
- No data transformation tracking
- No understanding of data flow through procedures

**After (v2.0):**
- **Column-level lineage**: Tracks data from source columns to target columns
- **Data transformations**: Identifies calculations, joins, aggregations, filters
- **Variable lineage**: Tracks how variables flow through procedures
- **Control flow analysis**: Identifies loops, conditionals, cursors, exception handlers

### 3. Recursive Procedure Analysis ✅

**Before (v1.0):**
- Discovered dependent packages but didn't analyze called procedures
- Depth limit only applied to packages
- Missing the full call chain

**After (v2.0):**
- **Procedure-level recursion**: When analyzing `PROC1`, if it calls `PROC2`, automatically analyzes `PROC2`
- **Complete call chains**: Follows dependencies to specified depth
- **Infinite loop prevention**: Tracks visited procedures to prevent re-analysis

### 4. LLM-Powered Analysis ✅

**Before (v1.0):**
- Simple regex-based parsing
- Missed complex SQL constructs
- Generic migration hints

**After (v2.0):**
- **Enhanced code analyzer** (`code_analyzer.py`): Dedicated LLM-powered analysis engine
- **Intelligent extraction**:
  - Precise procedure signatures with parameters
  - Table/view dependencies with columns
  - SQL operations (SELECT, INSERT, UPDATE, DELETE, MERGE)
  - Column-level transformations with expressions
  - Business logic understanding
- **Smart migration hints**: Specific to each procedure's code patterns
- **Fallback to regex**: If LLM unavailable, still provides basic analysis

### 5. Local Testing Capabilities ✅

**Before (v1.0):**
- No test suite for Oracle workflow
- Required actual Oracle database to test
- No validation of artifacts

**After (v2.0):**
- **Mock Oracle operations** (`tests/mock_oracle_operations.py`):
  - Sample PL/SQL packages with realistic patterns
  - Cross-package calls, table operations, cursors
  - No database required

- **Comprehensive test suite** (`tests/test_oracle_package_analyzer.py`):
  - Unit tests for all components
  - Integration tests for full workflow
  - Artifact structure validation

- **Local testing script** (`workflows/oracle_package_analyzer/local_test.py`):
  - Interactive demonstration
  - Shows analysis results
  - Can run without any external dependencies

## New Components

### 1. Enhanced Code Analyzer (`code_analyzer.py`)

```python
class PLSQLCodeAnalyzer:
    """LLM-powered analyzer for extracting deep insights from PL/SQL code"""

    def analyze_procedure(self, schema, package, procedure, source_code):
        """
        Performs deep analysis extracting:
        - Signatures and parameters
        - Table/view dependencies with columns
        - Column-level lineage with transformations
        - Procedure calls (fully qualified)
        - Data transformations
        - Control flow patterns
        - Global variables used
        - Migration hints
        """
```

Features:
- Comprehensive LLM prompting for detailed extraction
- JSON-based structured responses
- Automatic normalization of procedure calls
- Fallback regex parsing if LLM fails
- Handles markdown-wrapped responses

### 2. Mock Oracle Operations (`tests/mock_oracle_operations.py`)

Provides realistic test data:
- `BILLING.PKG_POLICY_BILLING`: Complex billing package with late fees, payments, statement generation
- `BILLING.PKG_UTILS`: Utility package for logging and error handling
- `NOTIFICATIONS.PKG_EMAIL`: Email notification system

Demonstrates:
- Cross-package calls (e.g., `BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE` calls `BILLING.PKG_UTILS.LOG_EVENT`)
- Table operations (SELECT, INSERT, UPDATE)
- Data transformations (premium * rate * days)
- Exception handling
- Cursor usage

### 3. Test Suite (`tests/test_oracle_package_analyzer.py`)

Comprehensive tests:
- Workflow metadata validation
- Package analysis workflow
- Procedure call extraction
- Table dependency extraction
- Procedure name extraction
- Artifact structure validation
- Code analyzer normalization
- Fallback analysis

### 4. Local Testing Script (`local_test.py`)

Interactive demonstration:
```bash
# Analyze default package
python local_test.py

# Analyze specific package
python local_test.py --package BILLING.PKG_UTILS

# Test all packages
python local_test.py --all
```

Shows:
- Package source preview
- Procedure extraction
- Deep analysis results
- Call graph visualization
- LLM vs fallback comparison

## Enhanced Artifact Structure

The knowledge artifact now includes:

```json
{
  "root_package": "BILLING.PKG_POLICY_BILLING",
  "units": [
    {
      "unit_type": "procedure",
      "qualified_name": "BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE",
      "signature": {
        "parameters": [
          {"name": "p_policy_id", "type": "NUMBER", "mode": "IN"},
          {"name": "p_late_fee", "type": "NUMBER", "mode": "OUT"}
        ],
        "return_type": null
      },
      "reads_from": [
        {
          "table": "BILLING.POLICIES",
          "columns": ["POLICY_ID", "PREMIUM", "STATUS"],
          "operation": "SELECT"
        }
      ],
      "writes_to": [...],
      "column_lineage": [
        {
          "output_column": "p_late_fee",
          "source_columns": ["BILLING.POLICIES.PREMIUM"],
          "transformation": "Multiply by late fee rate and days overdue",
          "expression": "v_premium * G_DEFAULT_LATE_FEE_RATE * (p_days_overdue / 30)"
        }
      ],
      "transformations": [
        {
          "type": "calculation",
          "description": "Calculate late fee based on premium and days overdue",
          "input_data": ["BILLING.POLICIES.PREMIUM", "p_days_overdue"],
          "output_data": ["p_late_fee"]
        }
      ],
      "calls": [
        "BILLING.PKG_UTILS.LOG_EVENT",
        "BILLING.PKG_UTILS.LOG_ERROR"
      ],
      "control_flow": {
        "conditionals": 1,
        "loops": 0,
        "exceptions": ["NO_DATA_FOUND", "OTHERS"],
        "cursors": []
      },
      "globals_used": ["G_DEFAULT_LATE_FEE_RATE"],
      "summary": "Calculates late fees for overdue policy payments...",
      "migration_hints": [
        "Replace global variable with config table in Snowflake",
        "Consider using Snowflake stored procedures or Python UDFs"
      ]
    }
  ],
  "tables": ["BILLING.POLICIES", "BILLING.PAYMENTS", ...],
  "packages": ["BILLING.PKG_POLICY_BILLING", "BILLING.PKG_UTILS", ...],
  "edges": [
    {"from": "BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE", "to": "BILLING.POLICIES", "type": "READS"},
    {"from": "BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE", "to": "BILLING.PKG_UTILS.LOG_EVENT", "type": "CALLS"}
  ]
}
```

## Recursive Analysis Flow

1. **Start**: Analyze root package `BILLING.PKG_POLICY_BILLING`
2. **Decompose**: Find procedures: `CALC_LATE_FEE`, `PROCESS_PAYMENT`, `GENERATE_STATEMENT`
3. **Analyze CALC_LATE_FEE**:
   - Extract signature, tables, transformations
   - Discover calls: `BILLING.PKG_UTILS.LOG_EVENT`, `BILLING.PKG_UTILS.LOG_ERROR`
   - **Add to queue**: `BILLING.PKG_UTILS.LOG_EVENT` (depth 1)
4. **Analyze PROCESS_PAYMENT**:
   - Discover call: `NOTIFICATIONS.PKG_EMAIL.SEND_PAYMENT_CONFIRMATION`
   - **Add to queue**: `NOTIFICATIONS.PKG_EMAIL.SEND_PAYMENT_CONFIRMATION` (depth 1)
5. **Analyze called procedures** (depth 1):
   - `BILLING.PKG_UTILS.LOG_EVENT`
   - `BILLING.PKG_UTILS.LOG_ERROR`
   - `NOTIFICATIONS.PKG_EMAIL.SEND_PAYMENT_CONFIRMATION`
6. **Continue recursively** until max_depth reached or queue empty

## Testing the Improvements

### Prerequisites

```bash
# Install dependencies
uv sync

# Or with pip
pip install -e .
```

### Run Local Test

```bash
cd workflows/oracle_package_analyzer
python local_test.py
```

Expected output:
```
======================================================================
  Oracle Package Analyzer - Local Test
======================================================================

Analyzing package: BILLING.PKG_POLICY_BILLING
Using mock data (no Oracle connection required)

Step 1: Package Source
----------------------------------------------------------------------
Source length: 2847 characters
...

Step 2: Extract Procedures
----------------------------------------------------------------------
Found 3 procedures/functions:
  - CALC_LATE_FEE
  - PROCESS_PAYMENT
  - GENERATE_STATEMENT

Step 3: Deep Analysis of CALC_LATE_FEE
----------------------------------------------------------------------
Procedure source length: 624 characters

Performing regex-based analysis (fallback mode)...

Analysis Results:
  Tables accessed: 1
    - BILLING.POLICIES

  Procedure calls: 2
    - BILLING.PKG_UTILS.LOG_EVENT
    - BILLING.PKG_UTILS.LOG_ERROR

  Summary: Basic analysis of BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE

Attempting full LLM-powered analysis...
[If LLM configured, shows enhanced results]

Step 4: Build Call Graph
----------------------------------------------------------------------
Total unique procedure calls: 4

Call graph:

  BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE
    → calls BILLING.PKG_UTILS.LOG_EVENT
    → calls BILLING.PKG_UTILS.LOG_ERROR

  BILLING.PKG_POLICY_BILLING.PROCESS_PAYMENT
    → calls NOTIFICATIONS.PKG_EMAIL.SEND_PAYMENT_CONFIRMATION

✓ Local testing completed successfully!
```

### Run Unit Tests

```bash
pytest tests/test_oracle_package_analyzer.py -v
```

## Performance Characteristics

### LLM Usage (v2.0)

- **One LLM call per procedure**
- **Cost**: ~$0.01-0.02 per procedure (Claude Sonnet)
- **Time**: ~1-2 seconds per procedure

### Example Scenarios

**Small Package** (10 procedures, depth=2):
- Procedures analyzed: 10-30
- Time: 30-60 seconds
- Cost: $0.30-0.60

**Medium Package** (50 procedures, depth=2):
- Procedures analyzed: 50-150
- Time: 3-8 minutes
- Cost: $1-3

**Large Package** (100 procedures, depth=3):
- Procedures analyzed: 100-500
- Time: 10-20 minutes
- Cost: $5-10

### Memory Usage

Constant memory regardless of package size due to incremental S3 assembly.

## Migration Notes

### From v1.0 to v2.0

1. **No breaking changes to workflow invocation**
2. **Enhanced artifact structure** (backward compatible)
3. **New dependency**: `code_analyzer.py` module
4. **Improved analysis quality** with same API

### Configuration

No configuration changes required. Works with existing `config.yaml`.

Optional: Adjust LLM temperature in `config.yaml` for more deterministic results.

## Files Changed/Added

### New Files

- `workflows/oracle_package_analyzer/code_analyzer.py` - LLM-powered analysis engine
- `tests/mock_oracle_operations.py` - Mock Oracle data sources
- `tests/test_oracle_package_analyzer.py` - Comprehensive test suite
- `workflows/oracle_package_analyzer/local_test.py` - Interactive testing script

### Modified Files

- `workflows/oracle_package_analyzer/workflow.py` - Enhanced with recursive analysis
- `workflows/oracle_package_analyzer/README.md` - Updated documentation

### Documentation Updates

- Added "What's New in v2.0" section
- Added "Local Testing" section
- Added "Performance Considerations" section
- Added "Troubleshooting" section
- Updated version to 2.0.0

## Benefits for Downstream Agents

The enhanced artifacts provide comprehensive information for other agents:

1. **Complete Call Graphs**: Understand full execution flow
2. **Data Lineage**: Track data transformations end-to-end
3. **Dependency Maps**: Know what tables/packages are involved
4. **Transformation Logic**: Understand business rules and calculations
5. **Migration Guidance**: Specific hints for cloud migration

These artifacts enable downstream agents to:
- Generate Snowflake migration scripts
- Create data flow diagrams
- Identify optimization opportunities
- Assess migration complexity
- Plan testing strategies

## Next Steps

The workflow is now production-ready for:

1. **Deep package analysis**: Understands complete dependency chains
2. **Data lineage tracking**: Traces data transformations
3. **Migration planning**: Provides actionable migration hints
4. **Quality assurance**: Local testing validates artifacts

To use:

1. Configure environment variables (Oracle connection, S3, LLM)
2. Run workflow: `workflow.invoke({"root_package_name": "SCHEMA.PKG"})`
3. Retrieve artifact from S3
4. Pass to downstream agents for further analysis

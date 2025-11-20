# Oracle Package Analyzer - Local Testing Guide

**Test the Oracle Package Analyzer without AWS or Oracle Database!**

This guide shows you how to test the Oracle Package Analyzer using local filesystem storage and sample Oracle packages. Perfect for development, testing, and demonstration.

---

## 🚀 Quick Start

### 1. Run the Test Suite

```bash
# Run all tests
python test_oracle_local.py

# Clean start (removes existing data)
python test_oracle_local.py --clean

# Run specific test
python test_oracle_local.py --test complex

# Test with deeper dependency analysis
python test_oracle_local.py --test deep --max-depth 5
```

### 2. View Results

```bash
# List analyzed packages
ls -la oracle_packages_local/knowledge/

# View an analysis artifact
cat oracle_packages_local/knowledge/BILLING.PKG_POLICY_BILLING.json | jq .
```

---

## 📁 Directory Structure

```
oracle_packages_local/
├── raw/                              # Oracle package source files (.sql)
│   ├── BILLING/
│   │   └── PKG_POLICY_BILLING.sql   # Complex billing package
│   ├── FINANCE/
│   │   ├── PKG_GL_PROCESSING.sql    # General ledger processing
│   │   └── PKG_ERROR_LOGGING.sql    # Error logging utility
│   └── CUSTOMERS/
│       └── PKG_NOTIFICATIONS.sql     # Customer notifications
└── knowledge/                        # Generated analysis artifacts (.json)
    ├── BILLING.PKG_POLICY_BILLING.json
    ├── FINANCE.PKG_GL_PROCESSING.json
    └── FINANCE.PKG_ERROR_LOGGING.json
```

---

## 🎯 Available Tests

### Test: List Packages
```bash
python test_oracle_local.py --test list
```
- Shows all available Oracle packages
- Displays file sizes and locations

### Test: Simple Analysis
```bash
python test_oracle_local.py --test simple
```
- Analyzes a simple package (PKG_ERROR_LOGGING)
- Minimal depth (max_depth=1)
- Fast execution
- Good for testing basic functionality

### Test: Complex Analysis
```bash
python test_oracle_local.py --test complex
```
- Analyzes a complex package with dependencies (PKG_POLICY_BILLING)
- Standard depth (max_depth=3)
- Discovers cross-package calls
- Tests incremental artifact assembly

### Test: Deep Analysis
```bash
python test_oracle_local.py --test deep --max-depth 5
```
- Maximum recursion depth
- Discovers multi-level dependencies
- Tests scalability
- Generates comprehensive knowledge graph

### Test: Cross-Schema Dependencies
```bash
python test_oracle_local.py --test cross-schema
```
- Tests cross-schema dependency discovery
- Validates BILLING → FINANCE → CUSTOMERS chains
- Tests schema filtering

---

## 📦 Adding Your Own Oracle Packages

### Method 1: Manual File Placement

1. Place your `.sql` files in the schema directory:
   ```bash
   cp your_package.sql oracle_packages_local/raw/YOUR_SCHEMA/
   ```

2. Run analysis:
   ```bash
   python workflows/oracle_package_analyzer/local_workflow.py \
     --analyze YOUR_SCHEMA.YOUR_PACKAGE
   ```

### Method 2: Programmatic Loading

```python
from workflows.oracle_package_analyzer.local_workflow import (
    LocalOraclePackageAnalyzerWorkflow
)

# Initialize workflow
workflow = LocalOraclePackageAnalyzerWorkflow()

# Load package from file
workflow.load_package_from_file(
    schema="CLAIMS",
    package="PKG_RESERVE_CALC",
    file_path="/path/to/your/pkg_reserve_calc.sql"
)

# Analyze it
graph = workflow.get_compiled_graph()
result = graph.invoke({
    "root_package_name": "CLAIMS.PKG_RESERVE_CALC",
    "max_depth": 3,
    "include_cross_schema": True,
    "todo_items": [],
    "visited_units": [],
    "units_count": 0,
    "tables_count": 0,
    "packages_count": 0
})

print(f"Analyzed {result['units_count']} units")
```

---

## 🔍 What Gets Analyzed?

The analyzer extracts:

### ✅ Procedures and Functions
- Names and signatures
- Input/output parameters
- Return types

### ✅ Data Dependencies
- **Tables**: Read and write operations
- **Views**: Query dependencies
- **Columns**: Column-level lineage (with LLM)

### ✅ Control Flow
- Conditionals (IF/CASE)
- Loops (FOR/WHILE)
- Exception handlers
- Cursors

### ✅ Procedure Calls
- Direct calls to other procedures
- Package.Procedure calls
- Cross-schema calls

### ✅ Transformations
- Data calculations
- Business logic
- Join operations
- Aggregations

### ✅ Migration Hints
- Snowflake conversion suggestions
- Pattern recommendations
- Complexity warnings

---

## 📊 Understanding the Output

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
        "return_type": null
      },
      "reads_from": [
        {
          "table": "BILLING.POLICIES",
          "columns": ["outstanding_balance", "next_due_date", "status"],
          "operation": "SELECT"
        }
      ],
      "writes_to": [
        {
          "table": "BILLING.LATE_FEE_TRANSACTIONS",
          "columns": ["policy_id", "fee_amount", "fee_date"],
          "operation": "INSERT"
        }
      ],
      "calls": [
        "FINANCE.PKG_ERROR_LOGGING.LOG_ERROR"
      ],
      "column_lineage": [...],
      "transformations": [...],
      "control_flow": {
        "conditionals": 3,
        "loops": 0,
        "exceptions": 2,
        "cursors": []
      },
      "summary": "Calculates late fees for overdue policies...",
      "migration_hints": [...]
    }
  ],
  "tables": [
    "BILLING.POLICIES",
    "BILLING.LATE_FEE_TRANSACTIONS",
    "BILLING.INVOICES"
  ],
  "packages": [
    "BILLING.PKG_POLICY_BILLING",
    "FINANCE.PKG_ERROR_LOGGING",
    "FINANCE.PKG_GL_PROCESSING"
  ],
  "edges": [
    {
      "from": "BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE",
      "to": "BILLING.POLICIES",
      "type": "READS"
    },
    {
      "from": "BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE",
      "to": "FINANCE.PKG_ERROR_LOGGING.LOG_ERROR",
      "type": "CALLS"
    }
  ],
  "metadata": {
    "started_at": "2025-11-19T18:00:00",
    "completed_at": "2025-11-19T18:00:15",
    "max_depth": 3,
    "version": "2.0.0"
  }
}
```

### Visualization Ideas

```bash
# Convert to GraphViz
python -c "
import json
with open('oracle_packages_local/knowledge/BILLING.PKG_POLICY_BILLING.json') as f:
    data = json.load(f)

print('digraph G {')
for edge in data['edges']:
    print(f'  \"{edge['from']}\" -> \"{edge['to']}\" [label=\"{edge['type']}\"]')
print('}')
" | dot -Tpng -o dependency_graph.png
```

---

## 🧪 Testing with Complex Packages

### Sample Packages Included

1. **BILLING.PKG_POLICY_BILLING** (Complex)
   - 5 procedures/functions
   - Multi-table operations
   - Cross-schema calls to FINANCE and CUSTOMERS
   - Complex business logic with discounts, taxes, late fees

2. **FINANCE.PKG_GL_PROCESSING** (Complex)
   - 6 procedures/functions
   - Journal entry management
   - Month-end close process
   - Calls to FINANCE.PKG_ERROR_LOGGING

3. **FINANCE.PKG_ERROR_LOGGING** (Simple)
   - 3 procedures/functions
   - Autonomous transactions
   - No external dependencies
   - Good baseline test

4. **CUSTOMERS.PKG_NOTIFICATIONS** (Medium)
   - 4 procedures/functions
   - Reads from BILLING tables
   - Batch processing logic

### Dependency Chain Example

```
BILLING.PKG_POLICY_BILLING
├─ PROCESS_MONTHLY_BILLING
│  ├─ GENERATE_INVOICE
│  │  ├─ CALC_PREMIUM_WITH_DISCOUNTS
│  │  └─ Reads: POLICIES, POLICY_DISCOUNTS, POLICY_COVERAGES
│  ├─ Calls: CUSTOMERS.PKG_NOTIFICATIONS.SEND_INVOICE_EMAIL
│  └─ Calls: FINANCE.PKG_ERROR_LOGGING.LOG_ERROR
├─ APPLY_PAYMENT
│  └─ Calls: FINANCE.PKG_GL_PROCESSING.RECORD_REVENUE
│     └─ Calls: FINANCE.PKG_ERROR_LOGGING.LOG_ERROR
```

---

## 🔧 Advanced Configuration

### Custom Storage Location

```python
workflow = LocalOraclePackageAnalyzerWorkflow(
    local_storage_path="/path/to/your/oracle/packages"
)
```

### Analysis Configuration

Edit `workflows/oracle_package_analyzer/config.yaml`:

```yaml
analysis:
  default_max_depth: 5              # Deeper recursion
  include_cross_schema_default: true  # Always follow cross-schema
  llm_temperature: 0.0              # Deterministic analysis
  max_code_lines: 1000              # Larger code blocks
```

### LLM Configuration

For enhanced analysis (column lineage, transformations):

1. Set your API key:
   ```bash
   export ANTHROPIC_API_KEY=your-key-here
   ```

2. Or configure in `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

3. The analyzer will automatically use LLM for deep code analysis

---

## 🐛 Troubleshooting

### "Package not found"

```bash
# Check if file exists
ls oracle_packages_local/raw/SCHEMA/PACKAGE.sql

# List available packages
python test_oracle_local.py --test list
```

### "No such file or directory"

```bash
# Create directory structure
mkdir -p oracle_packages_local/raw/{BILLING,FINANCE,CUSTOMERS,CLAIMS}
mkdir -p oracle_packages_local/knowledge

# Run with --clean to recreate
python test_oracle_local.py --clean
```

### "Analysis failed: module not found"

```bash
# Install dependencies
make install-dev

# Or with uv
uv pip install -e ".[dev]"
```

### "LLM analysis failed"

This is normal if you don't have an API key set. The analyzer will fall back to regex-based analysis which still extracts:
- Procedure names
- Table references
- Procedure calls
- Basic signatures

For full analysis with column lineage and transformations, set `ANTHROPIC_API_KEY`.

---

## 📈 Performance Tips

### For Large Packages

1. **Limit Depth**
   ```bash
   python test_oracle_local.py --test complex --max-depth 2
   ```

2. **Disable Cross-Schema**
   ```python
   result = graph.invoke({
       "root_package_name": "SCHEMA.PACKAGE",
       "include_cross_schema": False,  # Stay within schema
       "max_depth": 3
   })
   ```

3. **Monitor Progress**
   - The workflow prints progress as it analyzes each unit
   - Artifacts are saved incrementally (you can inspect mid-analysis)

### Memory Usage

The workflow uses **constant memory** regardless of package size because:
- Artifacts stored incrementally to disk
- Only current procedure code in memory
- Visited units tracked by name only (not full data)

---

## 🎓 Learning Examples

### Example 1: Analyze a Single Package

```python
from workflows.oracle_package_analyzer.local_workflow import (
    LocalOraclePackageAnalyzerWorkflow
)

workflow = LocalOraclePackageAnalyzerWorkflow()
graph = workflow.get_compiled_graph()

result = graph.invoke({
    "root_package_name": "BILLING.PKG_POLICY_BILLING",
    "max_depth": 2,
    "include_cross_schema": False,
    "todo_items": [],
    "visited_units": [],
    "units_count": 0,
    "tables_count": 0,
    "packages_count": 0
})

print(f"Status: {result['status']}")
print(f"Units: {result['units_count']}")
print(f"Tables: {result['tables_count']}")
```

### Example 2: Extract Specific Information

```python
import json

# Load artifact
with open('oracle_packages_local/knowledge/BILLING.PKG_POLICY_BILLING.json') as f:
    artifact = json.load(f)

# Find all tables accessed
tables = set()
for unit in artifact['units']:
    for read_op in unit.get('reads_from', []):
        tables.add(read_op['table'])
    for write_op in unit.get('writes_to', []):
        tables.add(write_op['table'])

print(f"Tables accessed: {sorted(tables)}")

# Find procedures that write data
writers = [
    unit['qualified_name']
    for unit in artifact['units']
    if unit.get('writes_to')
]

print(f"Procedures that write data: {writers}")
```

### Example 3: Build Call Graph

```python
import json
from collections import defaultdict

with open('oracle_packages_local/knowledge/BILLING.PKG_POLICY_BILLING.json') as f:
    artifact = json.load(f)

# Build call graph
call_graph = defaultdict(list)
for edge in artifact['edges']:
    if edge['type'] == 'CALLS':
        call_graph[edge['from']].append(edge['to'])

# Print call hierarchy
for caller, callees in sorted(call_graph.items()):
    print(f"\n{caller} calls:")
    for callee in callees:
        print(f"  → {callee}")
```

---

## 🚀 Next Steps

1. **Add Your Packages**
   - Export your Oracle packages to `.sql` files
   - Place them in `oracle_packages_local/raw/{SCHEMA}/`
   - Run analysis

2. **Integrate with Tools**
   - Export to GraphML/Neo4j for visualization
   - Generate migration reports
   - Build impact analysis dashboards

3. **Extend Analysis**
   - Add custom extraction rules
   - Implement domain-specific patterns
   - Create specialized reports

4. **Production Deployment**
   - Switch to S3 storage (see main workflow)
   - Connect to real Oracle database
   - Scale with AWS infrastructure

---

## 📚 Related Documentation

- [Main Workflow Documentation](workflows/oracle_package_analyzer/README.md)
- [Architecture Guide](ARCHITECTURE.md)
- [Development Guide](docs/developer-guide.md)

---

**Happy Testing! 🎉**

For questions or issues, check the test output or examine the generated artifacts in `oracle_packages_local/knowledge/`.

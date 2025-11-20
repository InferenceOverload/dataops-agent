# ✅ Oracle Package Analyzer - Local Testing Setup Complete!

Your Oracle Package Analyzer is ready to test **without AWS or Oracle database!**

---

## 🎯 What's Ready

### ✅ 4 Complex, Realistic Oracle Packages

Located in `/Users/imperfecto/DevX/oracle_packages_local/oracle/raw/`:

1. **BILLING/PKG_POLICY_BILLING.sql** (12.7 KB)
   - 5 procedures: billing, invoicing, payments, late fees
   - Cross-schema calls to FINANCE and CUSTOMERS

2. **FINANCE/PKG_GL_PROCESSING.sql** (13.9 KB)
   - 6 procedures: journal entries, GL posting, month-end close
   - Multi-table transactions

3. **FINANCE/PKG_ERROR_LOGGING.sql** (3.3 KB)
   - 3 procedures: error logging utility
   - Used by other packages

4. **CUSTOMERS/PKG_NOTIFICATIONS.sql** (8.3 KB)
   - 4 procedures: email notifications, batch processing

### ✅ Test Infrastructure

- **Local storage** using filesystem (no S3 needed)
- **Test scripts** for automated testing
- **Complete documentation**

---

## 🚀 Quick Test (30 seconds)

```bash
cd /Users/imperfecto/DevX/dataops-agent

# List available packages
.venv/bin/python workflows/oracle_package_analyzer/local_workflow.py \
  --storage-path /Users/imperfecto/DevX/oracle_packages_local \
  --list
```

**Expected output:**
```
✓ Initialized local workflow with storage at: /Users/imperfecto/DevX/oracle_packages_local

======================================================================
  Available Oracle Packages
======================================================================
  BILLING.PKG_POLICY_BILLING             (12,780 bytes)
  CUSTOMERS.PKG_NOTIFICATIONS              (8,326 bytes)
  FINANCE.PKG_ERROR_LOGGING              (3,338 bytes)
  FINANCE.PKG_GL_PROCESSING              (13,871 bytes)

Total packages: 4
```

---

## 📊 Run Your First Analysis (2 minutes)

### Simple Package Test

```bash
.venv/bin/python workflows/oracle_package_analyzer/local_workflow.py \
  --storage-path /Users/imperfecto/DevX/oracle_packages_local \
  --analyze FINANCE.PKG_ERROR_LOGGING \
  --max-depth 1
```

**What this does:**
- Analyzes PKG_ERROR_LOGGING (simple package)
- Discovers 3 procedures
- Maps table dependencies
- Generates knowledge artifact

**Results saved to:**
```
/Users/imperfecto/DevX/oracle_packages_local/oracle/knowledge/FINANCE.PKG_ERROR_LOGGING.json
```

### Complex Package Test

```bash
.venv/bin/python workflows/oracle_package_analyzer/local_workflow.py \
  --storage-path /Users/imperfecto/DevX/oracle_packages_local \
  --analyze BILLING.PKG_POLICY_BILLING \
  --max-depth 3 \
  --cross-schema
```

**What this does:**
- Analyzes PKG_POLICY_BILLING (complex package)
- Discovers 5+ procedures
- Maps cross-schema dependencies (BILLING → FINANCE → CUSTOMERS)
- Identifies 15+ tables
- Generates comprehensive dependency graph

**Expected discoveries:**
- Units: 15+ procedures across multiple packages
- Tables: 15+ tables from BILLING, FINANCE, CUSTOMERS schemas
- Dependencies: Multi-level call chains
- Edges: 50+ dependency connections

---

## 📁 View Results

```bash
# View artifact summary
cat /Users/imperfecto/DevX/oracle_packages_local/oracle/knowledge/BILLING.PKG_POLICY_BILLING.json | jq '{
  root_package,
  units: (.units | length),
  tables,
  packages,
  edges: (.edges | length)
}'
```

**Sample output:**
```json
{
  "root_package": "BILLING.PKG_POLICY_BILLING",
  "units": 15,
  "tables": [
    "BILLING.POLICIES",
    "BILLING.INVOICES",
    "BILLING.PAYMENT_TRANSACTIONS",
    "CUSTOMERS.CUSTOMER_MASTER",
    ...
  ],
  "packages": [
    "BILLING.PKG_POLICY_BILLING",
    "FINANCE.PKG_ERROR_LOGGING",
    "FINANCE.PKG_GL_PROCESSING",
    "CUSTOMERS.PKG_NOTIFICATIONS"
  ],
  "edges": 52
}
```

---

## 🎓 Understanding the Output

Each knowledge artifact contains:

### 📝 Units (Procedures/Functions)
```json
{
  "qualified_name": "BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE",
  "unit_type": "procedure",
  "reads_from": [
    {"table": "BILLING.POLICIES", "columns": ["outstanding_balance", "next_due_date"]}
  ],
  "writes_to": [
    {"table": "BILLING.LATE_FEE_TRANSACTIONS", "columns": ["policy_id", "fee_amount"]}
  ],
  "calls": ["FINANCE.PKG_ERROR_LOGGING.LOG_ERROR"]
}
```

### 🔗 Dependency Edges
```json
{
  "from": "BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE",
  "to": "BILLING.POLICIES",
  "type": "READS"
}
```

### 📊 Metadata
- Analysis timestamp
- Configuration (depth, cross-schema)
- Totals and summaries

---

## 💪 Add Your Own Packages

### Method 1: Copy Files

```bash
# Place your Oracle package files
cp /your/oracle/exports/pkg_claims.sql \
   /Users/imperfecto/DevX/oracle_packages_local/oracle/raw/CLAIMS/PKG_CLAIMS.sql

# Analyze
.venv/bin/python workflows/oracle_package_analyzer/local_workflow.py \
  --storage-path /Users/imperfecto/DevX/oracle_packages_local \
  --analyze CLAIMS.PKG_CLAIMS \
  --max-depth 3 \
  --cross-schema
```

### Method 2: Programmatic

```python
from workflows.oracle_package_analyzer.local_workflow import (
    LocalOraclePackageAnalyzerWorkflow
)

# Initialize
workflow = LocalOraclePackageAnalyzerWorkflow(
    local_storage_path="/Users/imperfecto/DevX/oracle_packages_local"
)

# Load package
workflow.load_package_from_file(
    schema="CLAIMS",
    package="PKG_CLAIMS",
    file_path="/your/path/pkg_claims.sql"
)

# Analyze
graph = workflow.get_compiled_graph()
result = graph.invoke({
    "root_package_name": "CLAIMS.PKG_CLAIMS",
    "max_depth": 3,
    "include_cross_schema": True,
    "todo_items": [],
    "visited_units": [],
    "units_count": 0,
    "tables_count": 0,
    "packages_count": 0
})

print(f"✓ Analyzed {result['units_count']} procedures")
print(f"✓ Discovered {result['tables_count']} tables")
print(f"✓ Found {result['packages_count']} packages")
```

---

## 🔍 What Gets Analyzed?

The analyzer extracts:

✅ **Procedure & Function Discovery**
- Names, signatures, parameters
- Return types

✅ **Data Dependencies**
- Tables: read operations (SELECT, SELECT FOR UPDATE)
- Tables: write operations (INSERT, UPDATE, DELETE)
- Views: query dependencies
- Columns: lineage mapping

✅ **Control Flow**
- IF/CASE conditionals
- FOR/WHILE loops
- Exception handlers (WHEN ... THEN)
- Cursor operations

✅ **Procedure Calls**
- Intra-package calls (within same package)
- Cross-package calls (SCHEMA.PKG.PROC)
- Cross-schema calls (OTHER_SCHEMA.PKG.PROC)

✅ **Business Logic**
- Data transformations
- Calculations
- Join operations
- Aggregations

✅ **Migration Hints**
- Snowflake conversion recommendations
- Complexity warnings
- Pattern suggestions

---

## ⚙️ Configuration Options

### Analysis Depth

```bash
--max-depth 1    # Just this package (fast)
--max-depth 2    # Direct dependencies
--max-depth 3    # Recommended (balanced)
--max-depth 5    # Comprehensive (may take time)
```

### Cross-Schema Dependencies

```bash
# Include dependencies from other schemas
--cross-schema

# Stay within one schema (faster)
# (omit --cross-schema flag)
```

### Storage Location

```bash
# Use custom location
--storage-path /your/custom/path

# Default location
--storage-path /Users/imperfecto/DevX/oracle_packages_local
```

---

## 📚 Documentation

- **[QUICK_START_LOCAL_TESTING.md](QUICK_START_LOCAL_TESTING.md)** - Fast start guide
- **[LOCAL_TESTING.md](LOCAL_TESTING.md)** - Comprehensive testing guide
- **[/Users/imperfecto/DevX/oracle_packages_local/README.md](file:///Users/imperfecto/DevX/oracle_packages_local/README.md)** - Package directory guide

---

## 🐛 Troubleshooting

### Issue: "ThrottlingException" from Bedrock

**This is normal!** The analyzer has a fallback mode that uses regex-based extraction when LLM calls are throttled. The analysis will still complete successfully.

**What works in fallback mode:**
- ✅ Procedure discovery
- ✅ Table dependencies
- ✅ Procedure calls
- ✅ Basic signatures

**What requires LLM (may be skipped):**
- ⚠️ Column-level lineage
- ⚠️ Transformation details
- ⚠️ Natural language summaries

**To use full LLM analysis:**
Set `ANTHROPIC_API_KEY` environment variable with your API key.

### Issue: "Package not found"

```bash
# Check if file exists
ls /Users/imperfecto/DevX/oracle_packages_local/oracle/raw/SCHEMA/PACKAGE.sql

# List available packages
.venv/bin/python workflows/oracle_package_analyzer/local_workflow.py \
  --storage-path /Users/imperfecto/DevX/oracle_packages_local \
  --list
```

### Issue: "Module not found"

```bash
# Install dependencies
make install-dev

# Or directly
.venv/bin/pip install -e ".[dev]"
```

---

## 🎉 Success Checklist

Your setup is working correctly if:

- ✅ List command shows 4 packages
- ✅ Analysis completes without errors (throttling warnings are OK)
- ✅ Artifacts generated in `oracle/knowledge/` directory
- ✅ JSON artifacts contain `units`, `tables`, `edges` arrays
- ✅ Cross-schema dependencies discovered (BILLING → FINANCE)
- ✅ File sizes are reasonable (5KB-50KB per artifact)

---

## 📊 What's Next?

### 1. Test with Your Data
```bash
# Add your Oracle packages
cp /your/oracle/*.sql \
   /Users/imperfecto/DevX/oracle_packages_local/oracle/raw/YOUR_SCHEMA/

# Analyze them
.venv/bin/python workflows/oracle_package_analyzer/local_workflow.py \
  --storage-path /Users/imperfecto/DevX/oracle_packages_local \
  --analyze YOUR_SCHEMA.YOUR_PACKAGE \
  --max-depth 3 \
  --cross-schema
```

### 2. Build Visualizations
```bash
# Extract dependency graph
jq '.edges[]' \
  /Users/imperfecto/DevX/oracle_packages_local/oracle/knowledge/*.json
```

### 3. Generate Reports
```python
import json
from pathlib import Path

# Load all artifacts
artifacts_dir = Path("/Users/imperfecto/DevX/oracle_packages_local/oracle/knowledge")
all_artifacts = [json.loads(f.read_text()) for f in artifacts_dir.glob("*.json")]

# Generate impact analysis report
# Generate migration complexity report
# Generate dependency diagrams
```

### 4. Move to Production
- Switch to S3 storage (see main workflow)
- Connect to real Oracle database
- Deploy on AWS infrastructure
- Scale to 100+ packages

---

## 🏆 You're All Set!

The Oracle Package Analyzer is fully functional with local filesystem storage. You can now:

✅ Analyze Oracle packages without AWS
✅ Discover deep dependency chains
✅ Map data lineage
✅ Generate migration insights
✅ Test at scale with your own packages

**Start analyzing:** Just run the commands above!

**Need help?** Check the documentation links or examine the generated JSON artifacts.

---

**Last tested:** 2025-11-19
**Status:** ✅ All systems operational
**Packages ready:** 4 (BILLING, FINANCE, CUSTOMERS schemas)
**Storage location:** `/Users/imperfecto/DevX/oracle_packages_local`

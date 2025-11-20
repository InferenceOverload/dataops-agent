# Quick Start: Testing Oracle Package Analyzer Locally

**No AWS account needed! No Oracle database needed!**

This guide gets you testing the Oracle Package Analyzer in under 5 minutes using local filesystem storage.

---

## ⚡ Instant Start

```bash
# 1. Run the test suite
./test_real_packages.sh

# That's it! The script will:
# - Analyze real Oracle packages
# - Discover dependencies
# - Generate knowledge artifacts
# - Show you the results
```

---

## 📊 What You'll See

The test analyzes these real packages:

1. **BILLING.PKG_POLICY_BILLING** (12KB, ~250 lines)
   - 5 procedures/functions
   - Premium calculation with discounts
   - Invoice generation
   - Payment processing
   - Late fee calculation

2. **FINANCE.PKG_GL_PROCESSING** (14KB, ~350 lines)
   - 6 procedures/functions
   - Journal entry creation
   - GL posting
   - Month-end close
   - Trial balance generation

3. **FINANCE.PKG_ERROR_LOGGING** (3KB, ~100 lines)
   - 3 procedures
   - Error logging utility
   - Used by many other packages

4. **CUSTOMERS.PKG_NOTIFICATIONS** (8KB, ~200 lines)
   - 4 procedures
   - Email notifications
   - Batch processing

**Total**: 4 packages, 18 procedures, complex cross-schema dependencies

---

## 🎯 Test Scenarios

### Scenario 1: Quick Test (30 seconds)

```bash
.venv/bin/python test_oracle_local.py --test list
```

Shows all available packages and their sizes.

### Scenario 2: Simple Analysis (1 minute)

```bash
.venv/bin/python test_oracle_local.py --test simple
```

Analyzes PKG_ERROR_LOGGING (simple, no dependencies).

### Scenario 3: Complex Analysis (2-3 minutes)

```bash
.venv/bin/python test_oracle_local.py --test complex
```

Analyzes PKG_POLICY_BILLING with full dependency chain:
- Discovers 5+ procedures
- Maps calls to FINANCE and CUSTOMERS schemas
- Identifies 10+ tables
- Generates comprehensive knowledge graph

### Scenario 4: Deep Dependency Analysis (3-5 minutes)

```bash
.venv/bin/python test_oracle_local.py --test deep --max-depth 5
```

Maximum recursion depth for complete dependency discovery.

### Scenario 5: Run All Tests

```bash
.venv/bin/python test_oracle_local.py
```

Runs all test scenarios and reports results.

---

## 📁 Where Are The Results?

```bash
# Knowledge artifacts (JSON)
oracle_packages_local/knowledge/
├── BILLING.PKG_POLICY_BILLING.json      # ~50KB, full analysis
├── FINANCE.PKG_GL_PROCESSING.json       # ~40KB
└── FINANCE.PKG_ERROR_LOGGING.json       # ~5KB

# View an artifact
cat oracle_packages_local/knowledge/BILLING.PKG_POLICY_BILLING.json | jq .

# Or pretty print
jq . < oracle_packages_local/knowledge/BILLING.PKG_POLICY_BILLING.json | less
```

---

## 🔍 What's In The Artifacts?

Each knowledge artifact contains:

```json
{
  "root_package": "BILLING.PKG_POLICY_BILLING",

  "units": [
    {
      "qualified_name": "BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE",
      "unit_type": "procedure",
      "reads_from": [{"table": "BILLING.POLICIES", "columns": [...]}],
      "writes_to": [{"table": "BILLING.LATE_FEE_TRANSACTIONS", ...}],
      "calls": ["FINANCE.PKG_ERROR_LOGGING.LOG_ERROR"],
      "summary": "Calculates late fees for overdue policies...",
      "migration_hints": [...]
    }
  ],

  "tables": ["BILLING.POLICIES", "BILLING.INVOICES", ...],
  "packages": ["BILLING.PKG_POLICY_BILLING", "FINANCE.PKG_ERROR_LOGGING", ...],

  "edges": [
    {"from": "...", "to": "...", "type": "READS"},
    {"from": "...", "to": "...", "type": "CALLS"}
  ]
}
```

**Use cases:**
- Generate dependency diagrams
- Impact analysis (what breaks if I change X?)
- Migration planning (Oracle → Snowflake)
- Documentation generation
- Code understanding

---

## 🚀 Adding Your Own Packages

### Method 1: Drop Files

```bash
# Copy your Oracle package files
cp /your/path/pkg_claims_processing.sql \
   oracle_packages_local/raw/CLAIMS/PKG_CLAIMS_PROCESSING.sql

# Analyze
.venv/bin/python workflows/oracle_package_analyzer/local_workflow.py \
  --storage-path oracle_packages_local \
  --analyze CLAIMS.PKG_CLAIMS_PROCESSING \
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
    local_storage_path="oracle_packages_local"
)

# Load your package
workflow.load_package_from_file(
    schema="CLAIMS",
    package="PKG_CLAIMS_PROCESSING",
    file_path="/your/path/pkg_claims_processing.sql"
)

# Analyze
graph = workflow.get_compiled_graph()
result = graph.invoke({
    "root_package_name": "CLAIMS.PKG_CLAIMS_PROCESSING",
    "max_depth": 3,
    "include_cross_schema": True,
    "todo_items": [],
    "visited_units": [],
    "units_count": 0,
    "tables_count": 0,
    "packages_count": 0
})

print(f"✓ Analyzed {result['units_count']} procedures")
```

---

## 💡 Pro Tips

### 1. Start With Small Packages

Test with PKG_ERROR_LOGGING first (simple, fast) before analyzing large packages.

### 2. Use Depth Wisely

- `--max-depth 1`: Just this package
- `--max-depth 2`: Direct dependencies
- `--max-depth 3`: Recommended for most cases
- `--max-depth 5`: Comprehensive (may take time)

### 3. Control Cross-Schema

```bash
# Stay within one schema (faster)
--analyze BILLING.PKG_POLICY_BILLING --max-depth 2

# Discover everything (slower)
--analyze BILLING.PKG_POLICY_BILLING --max-depth 3 --cross-schema
```

### 4. Incremental Results

Artifacts are saved incrementally. You can inspect them during analysis!

```bash
# In one terminal
.venv/bin/python workflows/oracle_package_analyzer/local_workflow.py \
  --analyze BILLING.PKG_POLICY_BILLING --max-depth 5

# In another terminal
watch -n 5 "jq '.units | length' oracle_packages_local/knowledge/BILLING.PKG_POLICY_BILLING.json"
```

### 5. Visualize Dependencies

```bash
# Extract call graph
jq -r '.edges[] | select(.type=="CALLS") | "\(.from) -> \(.to)"' \
  oracle_packages_local/knowledge/BILLING.PKG_POLICY_BILLING.json

# Extract table usage
jq -r '.edges[] | select(.type=="READS") | "\(.from) reads \(.to)"' \
  oracle_packages_local/knowledge/BILLING.PKG_POLICY_BILLING.json
```

---

## 🎓 Understanding The Results

### Example: BILLING.PKG_POLICY_BILLING

**What it discovers:**

1. **Procedures** (5 found)
   - CALC_LATE_FEE
   - PROCESS_MONTHLY_BILLING
   - GENERATE_INVOICE
   - APPLY_PAYMENT
   - CALC_PREMIUM_WITH_DISCOUNTS

2. **Tables** (~15 found)
   - BILLING.POLICIES (read/write)
   - BILLING.INVOICES (write)
   - BILLING.PAYMENT_TRANSACTIONS (write)
   - CUSTOMERS.CUSTOMER_MASTER (read)
   - And more...

3. **Dependencies** (10+ found)
   - FINANCE.PKG_ERROR_LOGGING.LOG_ERROR
   - FINANCE.PKG_GL_PROCESSING.RECORD_REVENUE
   - CUSTOMERS.PKG_NOTIFICATIONS.SEND_INVOICE_EMAIL

4. **Dependency Chain**
   ```
   BILLING.PKG_POLICY_BILLING
   ├─ PROCESS_MONTHLY_BILLING
   │  ├─ GENERATE_INVOICE
   │  │  └─ CALC_PREMIUM_WITH_DISCOUNTS
   │  └─ CUSTOMERS.PKG_NOTIFICATIONS.SEND_INVOICE_EMAIL
   └─ APPLY_PAYMENT
      └─ FINANCE.PKG_GL_PROCESSING.RECORD_REVENUE
         └─ FINANCE.PKG_ERROR_LOGGING.LOG_ERROR
   ```

---

## 🔧 Troubleshooting

### "Module not found: oracledb"

This is fine! The local version doesn't need Oracle connectivity.

```bash
# The import is optional and won't affect local testing
grep -A3 "try:" infrastructure/storage/oracle_operations.py
```

### "Package not found"

```bash
# List available packages
.venv/bin/python workflows/oracle_package_analyzer/local_workflow.py \
  --storage-path oracle_packages_local \
  --list
```

### "Analysis is slow"

Reduce depth or disable cross-schema:

```bash
# Faster
--analyze SCHEMA.PACKAGE --max-depth 1

# Even faster (same schema only)
--analyze SCHEMA.PACKAGE --max-depth 2
```

### Want fresh start?

```bash
# Remove old artifacts
rm -rf oracle_packages_local/knowledge/*.json

# Or run with clean flag
.venv/bin/python test_oracle_local.py --clean
```

---

## 📚 Next Steps

1. **Analyze your packages**
   - Export from Oracle to `.sql` files
   - Place in `oracle_packages_local/raw/{SCHEMA}/`
   - Run analysis

2. **Build visualizations**
   - Use the JSON artifacts
   - Create dependency diagrams
   - Generate impact reports

3. **Migrate to production**
   - Switch to S3 storage (see main workflow)
   - Connect to real Oracle database
   - Scale with AWS infrastructure

---

## 🎉 Success Indicators

You know it's working when:

✅ Test completes without errors
✅ Artifacts created in `knowledge/` directory
✅ JSON artifacts contain `units`, `tables`, `edges`
✅ Cross-schema dependencies discovered (BILLING → FINANCE)
✅ Procedure call chains mapped
✅ Table read/write operations identified

---

## 📖 Further Reading

- [Full Local Testing Guide](LOCAL_TESTING.md) - Comprehensive documentation
- [Workflow Documentation](workflows/oracle_package_analyzer/README.md) - How it works
- [Architecture Guide](ARCHITECTURE.md) - System design

---

**Ready to test?**

```bash
./test_real_packages.sh
```

**Questions?** Check the artifacts in `oracle_packages_local/knowledge/` - they contain all discovered information!

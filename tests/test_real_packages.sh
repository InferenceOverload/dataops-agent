#!/bin/bash
# Test Oracle Package Analyzer with Real Complex Packages
# These are large, realistic Oracle packages with deep dependencies

set -e

echo "========================================================================"
echo "  Oracle Package Analyzer - Real Package Testing"
echo "========================================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PYTHON=".venv/bin/python"
WORKFLOW_SCRIPT="workflows/oracle_package_analyzer/local_workflow.py"

# Function to print colored output
print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Step 1: List available real packages
print_step "Step 1: Listing real Oracle packages in /Users/imperfecto/DevX/oracle_packages_local"
echo ""
find /Users/imperfecto/DevX/oracle_packages_local/raw -name "*.sql" -type f | while read file; do
    size=$(du -h "$file" | cut -f1)
    basename=$(basename "$file")
    dirname=$(basename $(dirname "$file"))
    echo "  • $dirname.$basename ($size)"
done

echo ""
print_info "These are complex, realistic Oracle packages with:"
print_info "  - Multiple procedures and functions (5-10 per package)"
print_info "  - Cross-schema dependencies (BILLING → FINANCE → CUSTOMERS)"
print_info "  - Complex SQL operations (joins, aggregations, cursors)"
print_info "  - Real business logic (billing, GL posting, notifications)"
echo ""

# Step 2: Analyze simple package first
print_step "Step 2: Analyzing simple package (PKG_ERROR_LOGGING)"
echo ""

$PYTHON $WORKFLOW_SCRIPT \
  --storage-path /Users/imperfecto/DevX/oracle_packages_local \
  --analyze FINANCE.PKG_ERROR_LOGGING \
  --max-depth 1

print_success "Simple package analyzed"
echo ""

# Step 3: Analyze complex package with dependencies
print_step "Step 3: Analyzing complex package (PKG_POLICY_BILLING) with dependencies"
echo ""
print_info "This will discover:"
print_info "  - 5+ procedures in PKG_POLICY_BILLING"
print_info "  - Dependencies on FINANCE.PKG_ERROR_LOGGING"
print_info "  - Dependencies on FINANCE.PKG_GL_PROCESSING"
print_info "  - Dependencies on CUSTOMERS.PKG_NOTIFICATIONS"
print_info "  - 10+ tables accessed"
echo ""

$PYTHON $WORKFLOW_SCRIPT \
  --storage-path /Users/imperfecto/DevX/oracle_packages_local \
  --analyze BILLING.PKG_POLICY_BILLING \
  --max-depth 3 \
  --cross-schema

print_success "Complex package analyzed with full dependency chain"
echo ""

# Step 4: Show results
print_step "Step 4: Analyzing results"
echo ""

ARTIFACT_DIR="/Users/imperfecto/DevX/oracle_packages_local/knowledge"

if [ -f "$ARTIFACT_DIR/BILLING.PKG_POLICY_BILLING.json" ]; then
    print_success "Knowledge artifact created!"
    echo ""

    # Extract key statistics using python
    $PYTHON -c "
import json
import sys

with open('$ARTIFACT_DIR/BILLING.PKG_POLICY_BILLING.json') as f:
    artifact = json.load(f)

print('📊 Analysis Statistics:')
print(f\"  Root Package: {artifact.get('root_package')}\")
print(f\"  Units Analyzed: {len(artifact.get('units', []))}\")
print(f\"  Tables Discovered: {len(artifact.get('tables', []))}\")
print(f\"  Packages Discovered: {len(artifact.get('packages', []))}\")
print(f\"  Total Edges: {len(artifact.get('edges', []))}\")
print()

print('📋 Discovered Tables:')
for table in sorted(artifact.get('tables', []))[:10]:
    print(f'  • {table}')
if len(artifact.get('tables', [])) > 10:
    print(f'  ... and {len(artifact.get('tables', [])) - 10} more')
print()

print('📦 Discovered Packages:')
for pkg in sorted(artifact.get('packages', [])):
    print(f'  • {pkg}')
print()

print('📝 Sample Unit:')
if artifact.get('units'):
    unit = artifact['units'][0]
    print(f\"  Name: {unit.get('qualified_name')}\")
    print(f\"  Type: {unit.get('unit_type')}\")
    print(f\"  Tables Read: {len(unit.get('reads_from', []))}\")
    print(f\"  Tables Written: {len(unit.get('writes_to', []))}\")
    print(f\"  Procedures Called: {len(unit.get('calls', []))}\")
    if unit.get('summary'):
        print(f\"  Summary: {unit.get('summary')[:100]}...\")
print()

# Show dependency types
print('🔗 Dependency Graph:')
edge_types = {}
for edge in artifact.get('edges', []):
    edge_type = edge.get('type')
    edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

for edge_type, count in sorted(edge_types.items()):
    print(f'  {edge_type}: {count} connections')
"

else
    print_info "Artifact not found at $ARTIFACT_DIR/BILLING.PKG_POLICY_BILLING.json"
fi

echo ""
echo "========================================================================"
echo "  Testing Complete!"
echo "========================================================================"
echo ""
print_info "Generated artifacts location:"
echo "  📁 $ARTIFACT_DIR"
echo ""
print_info "To add your own packages:"
echo "  1. Place .sql files in: /Users/imperfecto/DevX/oracle_packages_local/raw/{SCHEMA}/"
echo "  2. Run: $PYTHON $WORKFLOW_SCRIPT --analyze SCHEMA.PACKAGE"
echo ""
print_info "To visualize dependencies:"
echo "  cat $ARTIFACT_DIR/BILLING.PKG_POLICY_BILLING.json | jq '.edges'"
echo ""

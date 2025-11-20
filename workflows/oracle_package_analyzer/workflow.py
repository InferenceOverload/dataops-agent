"""
Oracle Package Analyzer Workflow (Refactored with Sub-Agents)

Analyzes Oracle PL/SQL packages to discover procedures, dependencies, and column-level lineage.

Architecture: Incremental assembly with sub-agent isolation
- init_scope: Initialize analysis and create empty artifact in S3
- pick_next_task: Orchestrator that selects next analysis task
- decompose_package: Scout that discovers package contents and dependencies
- analyze_unit: Worker that launches sub-agents for isolated analysis
- finalize_knowledge: Returns S3 URI (artifact already complete)

Key improvements:
- Sub-agents provide context isolation per procedure
- Incremental S3 updates prevent memory accumulation
- Deterministic assembler merges results without LLM overhead
- Constant memory usage regardless of package size
"""

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Dict, Any, Optional
from dotenv import load_dotenv
from datetime import datetime
import os
import re
import json
import yaml
from pathlib import Path

from core.base_workflow import BaseWorkflow, WorkflowMetadata, WorkflowInputParameter
from infrastructure.storage.s3_operations import S3Operations
from infrastructure.storage import oracle_operations
from infrastructure.llm.llm_factory import create_llm
from workflows.oracle_package_analyzer.code_analyzer import PLSQLCodeAnalyzer

# Load environment variables
load_dotenv()


# ===================================================================
# Assembler Functions (Deterministic Merge Logic)
# ===================================================================

def merge_unit_into_artifact(artifact: Dict[str, Any], new_unit: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically merge a new unit analysis into the existing artifact.

    This function performs intelligent de-duplication and graph construction
    without using an LLM (fast, cheap, deterministic).

    Args:
        artifact: Current knowledge artifact from S3
        new_unit: New UnitAnalysis to merge

    Returns:
        Updated artifact with new unit merged
    """
    # 1. Append unit to units array
    artifact["units"].append(new_unit)

    # 2. Extract and merge tables (de-duplicate)
    tables_from_unit = set()
    for read in new_unit.get("reads_from", []):
        if "table" in read:
            tables_from_unit.add(read["table"])
    for write in new_unit.get("writes_to", []):
        if "table" in write:
            tables_from_unit.add(write["table"])

    # Merge with existing tables
    existing_tables = set(artifact.get("tables", []))
    artifact["tables"] = sorted(list(existing_tables.union(tables_from_unit)))

    # 3. Extract and merge views
    views_from_unit = set()
    # Views might be in reads_from if they're queried like tables
    # For now, we'll track them separately if marked as unit_type="view"
    if new_unit.get("unit_type") == "view":
        # Extract view name from qualified name (e.g., "BILLING.VW_CUSTOMERS")
        qualified_name = new_unit.get("qualified_name", "")
        if "." in qualified_name:
            views_from_unit.add(qualified_name)

    existing_views = set(artifact.get("views", []))
    artifact["views"] = sorted(list(existing_views.union(views_from_unit)))

    # 4. Extract and merge packages from calls
    packages_from_calls = set()
    for call in new_unit.get("calls", []):
        # call format: "SCHEMA.PKG.PROCEDURE" or "PKG.PROCEDURE"
        parts = call.split(".")
        if len(parts) >= 2:
            # Extract package part (first 2 components for SCHEMA.PKG)
            pkg = ".".join(parts[:2])
            packages_from_calls.add(pkg)
        elif len(parts) == 1:
            # Just package name
            packages_from_calls.add(parts[0])

    existing_packages = set(artifact.get("packages", []))
    artifact["packages"] = sorted(list(existing_packages.union(packages_from_calls)))

    # 5. Merge edges (de-duplicate)
    qualified_name = new_unit.get("qualified_name", "")
    new_edges = []

    # Create edges for table reads
    for read in new_unit.get("reads_from", []):
        if "table" in read:
            new_edges.append({
                "from": qualified_name,
                "to": read["table"],
                "type": "READS"
            })

    # Create edges for table writes
    for write in new_unit.get("writes_to", []):
        if "table" in write:
            new_edges.append({
                "from": qualified_name,
                "to": write["table"],
                "type": "WRITES"
            })

    # Create edges for procedure calls
    for call in new_unit.get("calls", []):
        new_edges.append({
            "from": qualified_name,
            "to": call,
            "type": "CALLS"
        })

    # De-duplicate edges using set of tuples
    existing_edges = artifact.get("edges", [])
    existing_edge_set = {
        (e["from"], e["to"], e["type"])
        for e in existing_edges
    }

    for edge in new_edges:
        edge_tuple = (edge["from"], edge["to"], edge["type"])
        if edge_tuple not in existing_edge_set:
            existing_edges.append(edge)
            existing_edge_set.add(edge_tuple)

    artifact["edges"] = existing_edges

    # 6. Update metadata
    if "metadata" not in artifact:
        artifact["metadata"] = {}

    artifact["metadata"]["last_updated"] = datetime.now().isoformat()
    artifact["metadata"]["total_units"] = len(artifact["units"])

    return artifact


def extract_procedure_code(full_source: str, procedure_name: str) -> str:
    """
    Extract a specific procedure's code from full package source.

    Args:
        full_source: Complete package source code
        procedure_name: Name of procedure to extract

    Returns:
        Procedure source code (or excerpt if not found)
    """
    # Find procedure definition
    proc_pattern = rf'(?:PROCEDURE|FUNCTION)\s+{re.escape(procedure_name)}\s*(?:\(|IS|AS)'
    match = re.search(proc_pattern, full_source, re.IGNORECASE)

    if not match:
        # Procedure not found, return first 2000 chars as fallback
        return full_source[:2000]

    start_pos = match.start()

    # Find the end of this procedure (next END;)
    # This is simplified - a real parser would track BEGIN/END nesting
    end_pattern = rf'END\s+{re.escape(procedure_name)}\s*;'
    end_match = re.search(end_pattern, full_source[start_pos:], re.IGNORECASE)

    if end_match:
        end_pos = start_pos + end_match.end()
        return full_source[start_pos:end_pos]
    else:
        # Couldn't find END, return next 2000 chars
        return full_source[start_pos:start_pos + 2000]


# ===================================================================
# TypedDict Definitions
# ===================================================================

class UnitAnalysis(TypedDict, total=False):
    """Analysis result for a single unit (procedure/function/view/trigger)"""
    unit_type: str  # "procedure" | "function" | "view" | "trigger"
    qualified_name: str  # e.g. "BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE"
    signature: Dict[str, Any]  # {"parameters": [...], "return_type": "..."}

    reads_from: List[Dict[str, Any]]  # [{"table": "SCHEMA.TABLE", "columns": ["COL1"], "operation": "SELECT"}]
    writes_to: List[Dict[str, Any]]  # Same structure as reads_from

    column_lineage: List[Dict[str, Any]]  # [{"output_column": "TARGET.COL", "source_columns": [...], "transformation": "...", "expression": "..."}]
    variable_lineage: List[Dict[str, Any]]  # Optional variable lineage

    calls: List[str]  # Qualified names of called procedures/functions (SCHEMA.PKG.PROC)

    transformations: List[Dict[str, Any]]  # [{"type": "calculation/join/...", "description": "...", "input_data": [...], "output_data": [...]}]

    control_flow: Dict[str, Any]  # {"conditionals": int, "loops": int, "exceptions": [...], "cursors": [...]}

    globals_used: List[str]  # List of global/package variables

    summary: str  # Natural-language summary
    migration_hints: List[str]  # Migration suggestions


class OracleAnalyzerState(TypedDict, total=False):
    """State for Oracle Package Analyzer workflow (lightweight - no accumulation)"""
    # Input parameters
    root_package_name: str  # "SCHEMA.PKG"
    max_depth: int
    include_cross_schema: bool

    # Root package info
    root_source_uri: str  # S3 URI of root package source
    artifact_s3_key: str  # S3 key where artifact is being built incrementally

    # Task queue
    todo_items: List[Dict[str, Any]]  # Queue of tasks to process
    current_task: Optional[Dict[str, Any]]  # Currently processing task

    # Lightweight tracking (not full data)
    visited_units: List[str]  # Units already analyzed (qualified names only)

    # Status tracking
    status: str  # "initializing" | "analyzing" | "complete" | "error"
    error: Optional[str]

    # Final output
    knowledge_artifact_uri: Optional[str]  # S3 URI of final artifact

    # Summary counts (for user display)
    units_count: int
    tables_count: int
    packages_count: int


class OraclePackageAnalyzerWorkflow(BaseWorkflow):
    """
    Analyzes Oracle PL/SQL packages and recursively discovers dependencies.

    Uses sub-agent pattern for context isolation and incremental S3 assembly.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Oracle Package Analyzer workflow.

        Args:
            config_path: Optional path to config.yaml (defaults to workflow's config.yaml)
        """
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Initialize LLM with low temperature for deterministic analysis
        llm_temp = self.config.get('analysis', {}).get('llm_temperature', 0.0)
        self.llm = create_llm(temperature=llm_temp)

        # Initialize code analyzer
        self.code_analyzer = PLSQLCodeAnalyzer(llm_temperature=llm_temp)

        # S3 operations will be initialized per-invocation based on env var
        self._s3_ops = None

    def _get_s3_ops(self) -> S3Operations:
        """Get or create S3Operations instance"""
        if self._s3_ops is None:
            bucket = os.getenv(self.config['storage']['s3_bucket_env_var'])
            if not bucket:
                raise ValueError(
                    f"Environment variable {self.config['storage']['s3_bucket_env_var']} not set"
                )
            self._s3_ops = S3Operations(bucket_name=bucket)
        return self._s3_ops

    def get_metadata(self) -> WorkflowMetadata:
        """Return workflow metadata for registry discovery"""
        return WorkflowMetadata(
            name="oracle_package_analyzer",
            description=(
                "Analyzes an Oracle PL/SQL package and recursively discovers "
                "procedures, dependencies, and column-level lineage. "
                "Uses sub-agents for context isolation and incremental S3 assembly."
            ),
            capabilities=[
                "Extract PL/SQL package procedures and functions",
                "Discover table and view dependencies",
                "Trace column-level data lineage",
                "Map procedure call chains",
                "Generate migration hints for cloud migration",
                "Store knowledge artifacts in S3 incrementally",
                "Isolated context per procedure analysis"
            ],
            example_queries=[
                "Analyze package BILLING.PKG_POLICY_BILLING",
                "Understand dependencies of CLAIMS.PKG_RESERVE_CALC",
                "What are the lineage impacts of FINANCE.PKG_GL_PROCESSING?",
                "Map all dependencies for CUSTOMER.PKG_ACCOUNT_MGMT"
            ],
            category="code_analysis",
            version="2.0.0",  # Incremented for sub-agent refactor
            author="Data Engineering Team",
            required_inputs=[
                WorkflowInputParameter(
                    name="root_package_name",
                    description="Oracle package to analyze (SCHEMA.PACKAGE_NAME format)",
                    type="string",
                    required=True,
                    example="BILLING.PKG_POLICY_BILLING",
                    prompt="Enter Oracle package (SCHEMA.PACKAGE_NAME) to analyze:"
                ),
                WorkflowInputParameter(
                    name="max_depth",
                    description="Maximum recursion depth for dependency discovery",
                    type="integer",
                    required=False,
                    default=self.config['analysis']['default_max_depth'],
                    example="3",
                    prompt="Maximum recursion depth (default: 3):"
                ),
                WorkflowInputParameter(
                    name="include_cross_schema",
                    description="Include dependencies from other schemas",
                    type="boolean",
                    required=False,
                    default=self.config['analysis']['include_cross_schema_default'],
                    example="false",
                    prompt="Include cross-schema dependencies? (true/false):"
                )
            ]
        )

    def get_compiled_graph(self):
        """Build Oracle Package Analyzer graph with sub-agent workflow"""

        # ===================================================================
        # Helper Functions for Parsing
        # ===================================================================

        def parse_package_name(qualified_name: str) -> tuple[str, str]:
            """
            Parse qualified package name into schema and package.

            Args:
                qualified_name: Either "SCHEMA.PACKAGE" or "PACKAGE"

            Returns:
                Tuple of (schema, package)
            """
            parts = qualified_name.split('.')
            if len(parts) == 2:
                return parts[0].upper(), parts[1].upper()
            elif len(parts) == 1:
                # Use default schema from env
                default_schema = os.getenv(
                    self.config['oracle']['default_schema_env_var'],
                    'PUBLIC'
                )
                return default_schema.upper(), parts[0].upper()
            else:
                raise ValueError(f"Invalid package name format: {qualified_name}")

        def get_s3_path_for_package(schema: str, package: str, path_type: str = 'raw') -> str:
            """
            Generate S3 key for package source or knowledge artifact.

            Args:
                schema: Schema name
                package: Package name
                path_type: 'raw' or 'knowledge'

            Returns:
                S3 key (path within bucket)
            """
            if path_type == 'raw':
                prefix = self.config['storage']['raw_prefix']
                return f"{prefix}/{schema}/{package}.sql"
            else:  # knowledge
                prefix = self.config['storage']['knowledge_prefix']
                return f"{prefix}/{schema}.{package}.json"

        def parse_package_procedures(source: str, package: str) -> List[str]:
            """
            Extract procedure and function names from package source.

            Simple regex-based extraction. Can be enhanced with full parser.

            Args:
                source: PL/SQL source code
                package: Package name (for context)

            Returns:
                List of procedure/function names
            """
            procedures = []

            # Match PROCEDURE declarations
            proc_pattern = r'(?:^|\s)PROCEDURE\s+([A-Z_][A-Z0-9_]*)'
            for match in re.finditer(proc_pattern, source, re.IGNORECASE | re.MULTILINE):
                procedures.append(match.group(1).upper())

            # Match FUNCTION declarations
            func_pattern = r'(?:^|\s)FUNCTION\s+([A-Z_][A-Z0-9_]*)'
            for match in re.finditer(func_pattern, source, re.IGNORECASE | re.MULTILINE):
                procedures.append(match.group(1).upper())

            return list(set(procedures))  # Remove duplicates

        def parse_package_dependencies(source: str) -> Dict[str, Any]:
            """
            Extract dependencies from package source.

            Returns dict with:
                - tables: List of table references
                - views: List of view references
                - packages: List of package references

            Args:
                source: PL/SQL source code

            Returns:
                Dict with dependency lists
            """
            dependencies = {
                "tables": [],
                "views": [],
                "packages": []
            }

            # Simple pattern matching for common SQL patterns
            # This is a simplified implementation - can be enhanced

            # FROM/INTO table references (including schema qualification)
            table_pattern = r'(?:FROM|INTO|UPDATE|INSERT\s+INTO)\s+([A-Z_][A-Z0-9_]*(?:\.[A-Z_][A-Z0-9_]*)?)'
            for match in re.finditer(table_pattern, source, re.IGNORECASE):
                table_ref = match.group(1).upper()
                dependencies["tables"].append(table_ref)

            # Package calls (SCHEMA.PKG.PROC or PKG.PROC)
            pkg_call_pattern = r'([A-Z_][A-Z0-9_]*(?:\.[A-Z_][A-Z0-9_]*)?)\s*\.\s*([A-Z_][A-Z0-9_]*)\s*\('
            for match in re.finditer(pkg_call_pattern, source, re.IGNORECASE):
                pkg_ref = match.group(1).upper()
                # If it contains a dot, it's SCHEMA.PKG, otherwise just PKG
                if '.' not in pkg_ref:
                    dependencies["packages"].append(pkg_ref)
                else:
                    dependencies["packages"].append(pkg_ref)

            # Remove duplicates
            dependencies["tables"] = list(set(dependencies["tables"]))
            dependencies["views"] = list(set(dependencies["views"]))
            dependencies["packages"] = list(set(dependencies["packages"]))

            return dependencies

        def parse_procedure_block(source: str, package: str, procedure: str) -> Dict[str, Any]:
            """
            Extract analysis from a specific procedure within package source.

            Args:
                source: Full package source
                package: Package name
                procedure: Procedure/function name

            Returns:
                Dict with procedure analysis (partial UnitAnalysis)
            """
            # Find procedure definition
            proc_pattern = rf'(?:PROCEDURE|FUNCTION)\s+{re.escape(procedure)}\s*\('
            match = re.search(proc_pattern, source, re.IGNORECASE)

            if not match:
                # No parameters
                return {
                    "signature": {"parameters": [], "return_type": None},
                    "reads_from": [],
                    "writes_to": [],
                    "calls": [],
                    "globals_used": []
                }

            # Extract a reasonable block around the procedure
            # This is simplified - a full implementation would parse the entire block
            start_pos = match.start()
            # Look for next END; or next PROCEDURE/FUNCTION
            end_match = re.search(
                r'END\s+' + re.escape(procedure) + r'\s*;',
                source[start_pos:],
                re.IGNORECASE
            )

            if end_match:
                proc_source = source[start_pos:start_pos + end_match.end()]
            else:
                # Fallback: take next 1000 chars
                proc_source = source[start_pos:start_pos + 1000]

            # Parse dependencies within this procedure
            deps = parse_package_dependencies(proc_source)

            return {
                "signature": {"parameters": [], "return_type": None},  # Simplified
                "reads_from": [{"table": t, "columns": []} for t in deps["tables"]],
                "writes_to": [],
                "calls": deps["packages"],
                "globals_used": []
            }

        def parse_view_select(source: str) -> Dict[str, Any]:
            """
            Extract table references from view definition.

            Args:
                source: View CREATE statement

            Returns:
                Dict with view analysis
            """
            deps = parse_package_dependencies(source)
            return {
                "signature": {},
                "reads_from": [{"table": t, "columns": []} for t in deps["tables"]],
                "writes_to": [],
                "calls": [],
                "globals_used": []
            }

        def parse_trigger_block(source: str) -> Dict[str, Any]:
            """
            Extract analysis from trigger source.

            Args:
                source: Trigger source code

            Returns:
                Dict with trigger analysis
            """
            deps = parse_package_dependencies(source)
            return {
                "signature": {},
                "reads_from": [{"table": t, "columns": []} for t in deps["tables"]],
                "writes_to": [],
                "calls": deps["packages"],
                "globals_used": []
            }

        # ===================================================================
        # LangGraph Nodes
        # ===================================================================

        def init_scope(state: OracleAnalyzerState) -> Dict[str, Any]:
            """
            Initialize analysis scope and create empty artifact in S3.

            Args:
                state: Current workflow state

            Returns:
                State updates with initialized values
            """
            try:
                # Parse root package name
                root_name = state.get('root_package_name', '')
                schema, package = parse_package_name(root_name)

                # Get configuration defaults
                max_depth = state.get('max_depth', self.config['analysis']['default_max_depth'])
                include_cross_schema = state.get(
                    'include_cross_schema',
                    self.config['analysis']['include_cross_schema_default']
                )

                # Determine S3 paths
                raw_s3_key = get_s3_path_for_package(schema, package, 'raw')
                artifact_s3_key = get_s3_path_for_package(schema, package, 'knowledge')

                s3_ops = self._get_s3_ops()
                bucket = os.getenv(self.config['storage']['s3_bucket_env_var'])
                root_source_uri = f"s3://{bucket}/{raw_s3_key}"

                # Check if source already in S3
                if not s3_ops.object_exists(raw_s3_key):
                    # Fetch from Oracle and store
                    source = oracle_operations.get_package_source(schema, package)
                    s3_ops.write_text(raw_s3_key, source)

                # Create initial empty artifact in S3
                empty_artifact = {
                    "root_package": f"{schema}.{package}",
                    "units": [],
                    "tables": [],
                    "views": [],
                    "packages": [f"{schema}.{package}"],
                    "edges": [],
                    "metadata": {
                        "started_at": datetime.now().isoformat(),
                        "max_depth": max_depth,
                        "include_cross_schema": include_cross_schema,
                        "version": "2.0.0"
                    }
                }

                # Write empty artifact to S3
                s3_ops.write_json(artifact_s3_key, empty_artifact)

                # Initialize state (lightweight - no data accumulation)
                return {
                    "root_package_name": f"{schema}.{package}",
                    "root_source_uri": root_source_uri,
                    "artifact_s3_key": artifact_s3_key,
                    "max_depth": max_depth,
                    "include_cross_schema": include_cross_schema,
                    "status": "analyzing",
                    "todo_items": [
                        {
                            "task_type": "analyze_dependency_package",
                            "schema": schema,
                            "package": package,
                            "procedure": None,
                            "view_name": None,
                            "trigger_name": None,
                            "depth": 0
                        }
                    ],
                    "current_task": None,
                    "visited_units": [],
                    "error": None,
                    "knowledge_artifact_uri": None,
                    "units_count": 0,
                    "tables_count": 0,
                    "packages_count": 1
                }

            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Initialization failed: {str(e)}"
                }

        def pick_next_task(state: OracleAnalyzerState) -> Dict[str, Any]:
            """
            Orchestrator: Pick next task from queue or finalize.

            Args:
                state: Current workflow state

            Returns:
                State update with next task selected
            """
            todo_items = state.get('todo_items', [])

            if not todo_items:
                # No more tasks - ready to finalize
                return {"current_task": None}

            # Pop first task (FIFO)
            next_task = todo_items.pop(0)

            return {
                "current_task": next_task,
                "todo_items": todo_items
            }

        def check_next_step(state: OracleAnalyzerState) -> str:
            """
            Determine next node based on current task.

            Args:
                state: Current workflow state

            Returns:
                Next node name
            """
            current_task = state.get('current_task')

            if current_task is None:
                return "finalize_knowledge"

            task_type = current_task.get('task_type')

            if task_type == "analyze_dependency_package":
                return "decompose_package"
            else:
                # analyze_procedure, analyze_view, analyze_trigger
                return "analyze_unit"

        def decompose_package(state: OracleAnalyzerState) -> Dict[str, Any]:
            """
            Scout: Decompose package into procedures and discover dependencies.

            Args:
                state: Current workflow state

            Returns:
                State updates with new tasks and discovered dependencies
            """
            current_task = state.get('current_task', {})
            schema = current_task['schema']
            package = current_task['package']
            depth = current_task['depth']

            max_depth = state.get('max_depth', 3)
            include_cross_schema = state.get('include_cross_schema', False)

            # Get package source from S3
            s3_key = get_s3_path_for_package(schema, package, 'raw')
            s3_ops = self._get_s3_ops()

            if not s3_ops.object_exists(s3_key):
                # Fetch and store
                try:
                    source = oracle_operations.get_package_source(schema, package)
                    s3_ops.write_text(s3_key, source)
                except Exception as e:
                    # Package not accessible - skip
                    return {
                        "todo_items": state.get('todo_items', [])
                    }
            else:
                source = s3_ops.read_text(s3_key)

            # Parse procedures
            procedures = parse_package_procedures(source, package)

            # Parse dependencies
            deps = parse_package_dependencies(source)

            # Create new tasks
            new_todos = list(state.get('todo_items', []))
            visited_units = state.get('visited_units', [])

            # Add procedure analysis tasks
            for proc in procedures:
                qualified_name = f"{schema}.{package}.{proc}"
                if qualified_name not in visited_units:
                    new_todos.append({
                        "task_type": "analyze_procedure",
                        "schema": schema,
                        "package": package,
                        "procedure": proc,
                        "view_name": None,
                        "trigger_name": None,
                        "depth": depth
                    })

            # Add dependent package tasks (if within depth limit)
            discovered_packages = []
            if depth + 1 <= max_depth:
                # Oracle built-in packages to skip
                oracle_builtins = {
                    'DBMS_OUTPUT', 'DBMS_SQL', 'DBMS_LOB', 'DBMS_UTILITY',
                    'UTL_FILE', 'UTL_HTTP', 'UTL_SMTP', 'UTL_TCP',
                    'DBMS_LOCK', 'DBMS_RANDOM', 'DBMS_CRYPTO',
                    'STANDARD', 'SYS', 'SYSTEM'
                }

                for dep_pkg in deps['packages']:
                    # Parse package reference
                    if '.' in dep_pkg:
                        dep_schema, dep_pkg_name = dep_pkg.split('.', 1)
                    else:
                        dep_schema = schema  # Same schema
                        dep_pkg_name = dep_pkg

                    # Skip Oracle built-ins
                    if dep_pkg_name.upper() in oracle_builtins:
                        continue

                    # Skip if schema name same as package name (likely parsing error)
                    if dep_schema.upper() == dep_pkg_name.upper():
                        continue

                    # Check cross-schema policy
                    if dep_schema.upper() != schema.upper() and not include_cross_schema:
                        continue

                    dep_qualified = f"{dep_schema}.{dep_pkg_name}"

                    # Check if already discovered (avoid duplicates)
                    if not any(
                        t.get('task_type') == 'analyze_dependency_package' and
                        t.get('schema') == dep_schema and
                        t.get('package') == dep_pkg_name
                        for t in new_todos
                    ):
                        new_todos.append({
                            "task_type": "analyze_dependency_package",
                            "schema": dep_schema,
                            "package": dep_pkg_name,
                            "procedure": None,
                            "view_name": None,
                            "trigger_name": None,
                            "depth": depth + 1
                        })
                        discovered_packages.append(dep_qualified)

            return {
                "todo_items": new_todos
            }

        def analyze_unit(state: OracleAnalyzerState) -> Dict[str, Any]:
            """
            Worker: Analyze individual procedure/view/trigger with deep LLM-powered analysis.

            Uses enhanced code analyzer to extract:
            - Precise procedure calls
            - Column-level lineage
            - Data transformations
            - Control flow

            Recursively adds called procedures to the analysis queue.

            Args:
                state: Current workflow state

            Returns:
                State updates with unit analysis merged into S3 and new tasks queued
            """
            current_task = state.get('current_task', {})
            task_type = current_task['task_type']
            schema = current_task['schema']
            package = current_task.get('package')
            procedure = current_task.get('procedure')
            view_name = current_task.get('view_name')
            trigger_name = current_task.get('trigger_name')
            depth = current_task.get('depth', 0)

            max_depth = state.get('max_depth', 3)
            include_cross_schema = state.get('include_cross_schema', False)

            # For procedures: use enhanced code analyzer
            if task_type == "analyze_procedure" and procedure:
                qualified_name = f"{schema}.{package}.{procedure}"
                unit_type = "procedure"

                # Get procedure source code
                s3_key = get_s3_path_for_package(schema, package, 'raw')
                s3_ops = self._get_s3_ops()
                full_source = s3_ops.read_text(s3_key)

                # Extract just this procedure's code
                proc_source = extract_procedure_code(full_source, procedure)

                # Use enhanced LLM-powered analysis
                try:
                    parsed = self.code_analyzer.analyze_procedure(
                        schema, package, procedure, proc_source, full_source
                    )
                except Exception as e:
                    # Fallback to basic parsing if analysis fails
                    parsed = parse_procedure_block(full_source, package, procedure)
                    parsed["summary"] = f"Analysis of {qualified_name}"
                    parsed["migration_hints"] = ["Review required - automated analysis failed"]

                summary = parsed.get("summary", f"Analysis of {qualified_name}")
                migration_hints = parsed.get("migration_hints", [])

            # For views: simpler analysis (no sub-agent needed)
            elif task_type == "analyze_view" and view_name:
                qualified_name = f"{schema}.{view_name}"
                unit_type = "view"

                try:
                    source = oracle_operations.get_view_definition(schema, view_name)
                    parsed = parse_view_select(source)
                    summary = f"View {qualified_name}"
                    migration_hints = ["Consider materializing as table in Snowflake for performance"]
                except Exception:
                    # View not accessible
                    return {
                        "visited_units": state.get('visited_units', []),
                        "todo_items": state.get('todo_items', [])
                    }

            # For triggers: simpler analysis
            elif task_type == "analyze_trigger" and trigger_name:
                qualified_name = f"{schema}.{trigger_name}"
                unit_type = "trigger"

                try:
                    source = oracle_operations.get_trigger_source(schema, trigger_name)
                    parsed = parse_trigger_block(source)
                    summary = f"Trigger {qualified_name}"
                    migration_hints = ["Replace trigger with Snowflake stream/task pattern"]
                except Exception:
                    # Trigger not accessible
                    return {
                        "visited_units": state.get('visited_units', []),
                        "todo_items": state.get('todo_items', [])
                    }
            else:
                # Unknown task type - skip
                return {
                    "visited_units": state.get('visited_units', []),
                    "todo_items": state.get('todo_items', [])
                }

            # Build UnitAnalysis
            new_unit: UnitAnalysis = {
                "unit_type": unit_type,
                "qualified_name": qualified_name,
                "signature": parsed.get("signature", {}),
                "reads_from": parsed.get("reads_from", []),
                "writes_to": parsed.get("writes_to", []),
                "column_lineage": parsed.get("column_lineage", []),
                "variable_lineage": parsed.get("variable_lineage", []),
                "calls": parsed.get("calls", []),
                "transformations": parsed.get("transformations", []),
                "control_flow": parsed.get("control_flow", {"conditionals": 0, "loops": 0, "exceptions": []}),
                "globals_used": parsed.get("globals_used", []),
                "summary": summary,
                "migration_hints": migration_hints
            }

            # INCREMENTAL ASSEMBLY: Merge into S3 artifact
            artifact_s3_key = state.get('artifact_s3_key')
            if artifact_s3_key:
                s3_ops = self._get_s3_ops()

                # Read current artifact
                current_artifact = s3_ops.read_json(artifact_s3_key)

                # Merge using deterministic assembler
                updated_artifact = merge_unit_into_artifact(current_artifact, new_unit)

                # Write back to S3
                s3_ops.write_json(artifact_s3_key, updated_artifact)

            # Update lightweight state (only track visited)
            new_visited = list(state.get('visited_units', []))
            new_visited.append(qualified_name)

            # RECURSIVE ANALYSIS: Add called procedures to queue
            new_todos = list(state.get('todo_items', []))

            if depth + 1 <= max_depth:
                for call in new_unit.get("calls", []):
                    # Parse call: SCHEMA.PKG.PROC or PKG.PROC
                    call_parts = call.split('.')

                    if len(call_parts) == 3:
                        # SCHEMA.PKG.PROC
                        call_schema, call_pkg, call_proc = call_parts
                    elif len(call_parts) == 2:
                        # PKG.PROC - assume same schema
                        call_schema = schema
                        call_pkg, call_proc = call_parts
                    else:
                        # Just PROC - standalone procedure
                        call_schema = schema
                        call_pkg = None
                        call_proc = call_parts[0]

                    # Check cross-schema policy
                    if call_schema.upper() != schema.upper() and not include_cross_schema:
                        continue

                    # Check if already visited or queued
                    call_qualified = call.upper()
                    if call_qualified in new_visited:
                        continue

                    # Check if already in queue
                    already_queued = any(
                        t.get('task_type') == 'analyze_procedure' and
                        f"{t.get('schema')}.{t.get('package')}.{t.get('procedure')}".upper() == call_qualified
                        for t in new_todos
                    )

                    if already_queued:
                        continue

                    # Add to queue
                    if call_pkg:
                        # Package procedure
                        new_todos.append({
                            "task_type": "analyze_procedure",
                            "schema": call_schema,
                            "package": call_pkg,
                            "procedure": call_proc,
                            "view_name": None,
                            "trigger_name": None,
                            "depth": depth + 1
                        })

            return {
                "visited_units": new_visited,
                "todo_items": new_todos
            }

        def finalize_knowledge(state: OracleAnalyzerState) -> Dict[str, Any]:
            """
            Finalize knowledge artifact (already complete in S3).

            Args:
                state: Current workflow state

            Returns:
                Final state update with artifact URI and counts
            """
            artifact_s3_key = state.get('artifact_s3_key', '')
            bucket = os.getenv(self.config['storage']['s3_bucket_env_var'])
            artifact_uri = f"s3://{bucket}/{artifact_s3_key}"

            # Read final artifact to get counts
            s3_ops = self._get_s3_ops()
            final_artifact = s3_ops.read_json(artifact_s3_key)

            # Update metadata
            final_artifact["metadata"]["completed_at"] = datetime.now().isoformat()
            s3_ops.write_json(artifact_s3_key, final_artifact)

            return {
                "status": "complete",
                "knowledge_artifact_uri": artifact_uri,
                "units_count": len(final_artifact.get("units", [])),
                "tables_count": len(final_artifact.get("tables", [])),
                "packages_count": len(final_artifact.get("packages", []))
            }

        # ===================================================================
        # Build Graph
        # ===================================================================

        graph = StateGraph(OracleAnalyzerState)

        # Add nodes
        graph.add_node("init_scope", init_scope)
        graph.add_node("pick_next_task", pick_next_task)
        graph.add_node("decompose_package", decompose_package)
        graph.add_node("analyze_unit", analyze_unit)
        graph.add_node("finalize_knowledge", finalize_knowledge)

        # Add edges
        graph.add_edge(START, "init_scope")
        graph.add_edge("init_scope", "pick_next_task")

        # Conditional routing from pick_next_task
        graph.add_conditional_edges(
            "pick_next_task",
            check_next_step,
            {
                "decompose_package": "decompose_package",
                "analyze_unit": "analyze_unit",
                "finalize_knowledge": "finalize_knowledge"
            }
        )

        # Loop back to pick_next_task after processing
        graph.add_edge("decompose_package", "pick_next_task")
        graph.add_edge("analyze_unit", "pick_next_task")

        # Finalize ends the workflow
        graph.add_edge("finalize_knowledge", END)

        return graph.compile(
            checkpointer=False,
            interrupt_before=None,
            interrupt_after=None,
            debug=False
        )


# For backwards compatibility - create instance and expose compiled graph
_workflow_instance = OraclePackageAnalyzerWorkflow()
workflow_graph = _workflow_instance.get_compiled_graph()


# For testing
if __name__ == "__main__":
    print("Testing Oracle Package Analyzer Workflow (Sub-Agent Version)")
    print("-" * 60)

    workflow = OraclePackageAnalyzerWorkflow()
    metadata = workflow.get_metadata()

    print(f"Workflow: {metadata.name}")
    print(f"Description: {metadata.description}")
    print(f"Category: {metadata.category}")
    print(f"Version: {metadata.version}")
    print()
    print("Capabilities:")
    for cap in metadata.capabilities:
        print(f"  - {cap}")
    print()
    print("Required Inputs:")
    for inp in metadata.required_inputs:
        print(f"  - {inp.name} ({inp.type}): {inp.description}")
    print("-" * 60)
    print("Workflow metadata loaded successfully")
    print("\nKey improvements in v2.0:")
    print("  ✓ Sub-agent pattern for context isolation")
    print("  ✓ Incremental S3 assembly (constant memory)")
    print("  ✓ Deterministic assembler (no LLM overhead)")
    print("  ✓ Fault-tolerant (progress saved incrementally)")

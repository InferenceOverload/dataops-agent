"""
Oracle Package Analyzer Workflow

Analyzes Oracle PL/SQL packages to discover procedures, dependencies, and column-level lineage.

Architecture: Task-based iterative analysis
- init_scope: Initialize analysis and fetch root package
- pick_next_task: Orchestrator that selects next analysis task
- decompose_package: Scout that discovers package contents and dependencies
- analyze_unit: Worker that analyzes individual procedures/views/triggers
- finalize_knowledge: Builds final knowledge artifact and stores to S3
"""

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Dict, Any, Optional
from dotenv import load_dotenv
import os
import re
import json
import yaml
from pathlib import Path

from core.base_workflow import BaseWorkflow, WorkflowMetadata, WorkflowInputParameter
from infrastructure.storage.s3_operations import S3Operations
from infrastructure.storage import oracle_operations
from infrastructure.llm.llm_factory import create_llm

# Load environment variables
load_dotenv()


class UnitAnalysis(TypedDict, total=False):
    """Analysis result for a single unit (procedure/function/view/trigger)"""
    unit_type: str  # "procedure" | "function" | "view" | "trigger"
    qualified_name: str  # e.g. "BILLING.PKG_POLICY_BILLING.CALC_LATE_FEE"
    signature: Dict[str, Any]  # {"parameters": [...], "return_type": "..."}

    reads_from: List[Dict[str, Any]]  # [{"table": "SCHEMA.TABLE", "columns": ["COL1"]}]
    writes_to: List[Dict[str, Any]]  # Same structure as reads_from

    column_lineage: List[Dict[str, Any]]  # [{"output": "col", "sources": [...], "expression": "..."}]
    variable_lineage: List[Dict[str, Any]]  # Optional variable lineage

    calls: List[str]  # Qualified names of called procedures/functions

    control_flow: Dict[str, Any]  # {"conditionals": int, "loops": int, "exceptions": [...]}

    globals_used: List[str]  # List of global/package variables

    summary: str  # Natural-language summary
    migration_hints: List[str]  # Migration suggestions


class OracleAnalyzerState(TypedDict, total=False):
    """State for Oracle Package Analyzer workflow"""
    # Input parameters
    root_package_name: str  # "SCHEMA.PKG"
    max_depth: int
    include_cross_schema: bool

    # Root package info
    root_source_uri: str  # S3 URI of root package source

    # Task queue
    todo_items: List[Dict[str, Any]]  # Queue of tasks to process
    current_task: Optional[Dict[str, Any]]  # Currently processing task

    # Analysis results
    visited_units: List[str]  # Units already analyzed (qualified names)
    units: List[UnitAnalysis]  # All unit analyses

    # Discovered artifacts
    packages: List[str]  # All packages discovered
    tables: List[str]  # All tables referenced
    views: List[str]  # All views referenced
    edges: List[Dict[str, str]]  # Graph edges {"from": "A", "to": "B", "type": "READS"}

    # Status tracking
    status: str  # "initializing" | "analyzing" | "complete" | "error"
    error: Optional[str]

    # Final output
    knowledge_artifact_uri: Optional[str]  # S3 URI of final artifact


class OraclePackageAnalyzerWorkflow(BaseWorkflow):
    """
    Analyzes Oracle PL/SQL packages and recursively discovers dependencies.

    This workflow takes a root package name and performs deep analysis to:
    - Extract all procedures and functions
    - Discover table and view dependencies
    - Trace column-level lineage
    - Map procedure call chains
    - Generate migration hints
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
                "procedures, dependencies, and column-level lineage."
            ),
            capabilities=[
                "Extract PL/SQL package procedures and functions",
                "Discover table and view dependencies",
                "Trace column-level data lineage",
                "Map procedure call chains",
                "Generate migration hints for cloud migration",
                "Store knowledge artifacts in S3"
            ],
            example_queries=[
                "Analyze package BILLING.PKG_POLICY_BILLING",
                "Understand dependencies of CLAIMS.PKG_RESERVE_CALC",
                "What are the lineage impacts of FINANCE.PKG_GL_PROCESSING?",
                "Map all dependencies for CUSTOMER.PKG_ACCOUNT_MGMT"
            ],
            category="code_analysis",
            version="1.0.0",
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
        """Build Oracle Package Analyzer graph with task-based workflow"""

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
            Initialize analysis scope and fetch root package.

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

                # Determine S3 path for root package
                s3_key = get_s3_path_for_package(schema, package, 'raw')
                s3_ops = self._get_s3_ops()
                bucket = os.getenv(self.config['storage']['s3_bucket_env_var'])
                root_source_uri = f"s3://{bucket}/{s3_key}"

                # Check if source already in S3
                if not s3_ops.object_exists(s3_key):
                    # Fetch from Oracle and store
                    source = oracle_operations.get_package_source(schema, package)
                    s3_ops.write_text(s3_key, source)

                # Initialize state
                return {
                    "root_package_name": f"{schema}.{package}",
                    "root_source_uri": root_source_uri,
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
                    "units": [],
                    "packages": [f"{schema}.{package}"],
                    "tables": [],
                    "views": [],
                    "edges": [],
                    "error": None,
                    "knowledge_artifact_uri": None
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

            # Update state collections
            new_packages = list(set(state.get('packages', []) + [f"{schema}.{package}"]))
            new_tables = list(set(state.get('tables', []) + deps['tables']))
            new_views = list(set(state.get('views', []) + deps['views']))

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
            if depth + 1 <= max_depth:
                for dep_pkg in deps['packages']:
                    # Parse package reference
                    if '.' in dep_pkg:
                        dep_schema, dep_pkg_name = dep_pkg.split('.', 1)
                    else:
                        dep_schema = schema  # Same schema
                        dep_pkg_name = dep_pkg

                    # Check cross-schema policy
                    if dep_schema.upper() != schema.upper() and not include_cross_schema:
                        continue

                    dep_qualified = f"{dep_schema}.{dep_pkg_name}"

                    # Check if already visited
                    if dep_qualified not in new_packages:
                        new_todos.append({
                            "task_type": "analyze_dependency_package",
                            "schema": dep_schema,
                            "package": dep_pkg_name,
                            "procedure": None,
                            "view_name": None,
                            "trigger_name": None,
                            "depth": depth + 1
                        })
                        new_packages.append(dep_qualified)

            return {
                "packages": new_packages,
                "tables": new_tables,
                "views": new_views,
                "todo_items": new_todos
            }

        def analyze_unit(state: OracleAnalyzerState) -> Dict[str, Any]:
            """
            Worker: Analyze individual procedure/view/trigger.

            Args:
                state: Current workflow state

            Returns:
                State updates with unit analysis
            """
            current_task = state.get('current_task', {})
            task_type = current_task['task_type']
            schema = current_task['schema']
            package = current_task.get('package')
            procedure = current_task.get('procedure')
            view_name = current_task.get('view_name')
            trigger_name = current_task.get('trigger_name')
            depth = current_task['depth']

            max_depth = state.get('max_depth', 3)
            include_cross_schema = state.get('include_cross_schema', False)

            # Determine qualified name and fetch source
            if task_type == "analyze_procedure":
                qualified_name = f"{schema}.{package}.{procedure}"
                unit_type = "procedure"  # Could be function, but simplified

                # Get package source
                s3_key = get_s3_path_for_package(schema, package, 'raw')
                s3_ops = self._get_s3_ops()
                source = s3_ops.read_text(s3_key)

                # Parse procedure
                parsed = parse_procedure_block(source, package, procedure)

            elif task_type == "analyze_view":
                qualified_name = f"{schema}.{view_name}"
                unit_type = "view"

                try:
                    source = oracle_operations.get_view_definition(schema, view_name)
                    parsed = parse_view_select(source)
                except Exception:
                    # View not accessible
                    return {"visited_units": state.get('visited_units', [])}

            else:  # analyze_trigger
                qualified_name = f"{schema}.{trigger_name}"
                unit_type = "trigger"

                try:
                    source = oracle_operations.get_trigger_source(schema, trigger_name)
                    parsed = parse_trigger_block(source)
                except Exception:
                    # Trigger not accessible
                    return {"visited_units": state.get('visited_units', [])}

            # Use LLM to generate summary and migration hints
            try:
                prompt = f"""Analyze this Oracle {unit_type} and provide:
1. A concise summary (2-3 sentences) of what it does
2. A list of 2-4 migration hints for moving to Snowflake/cloud

{unit_type.upper()}: {qualified_name}

Source excerpt:
{source[:1000]}

Respond in JSON format:
{{
  "summary": "...",
  "migration_hints": ["hint1", "hint2", ...]
}}
"""
                response = self.llm.invoke(prompt)
                llm_output = response.content

                # Try to parse JSON from response
                try:
                    # Extract JSON if wrapped in markdown
                    if '```json' in llm_output:
                        json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_output, re.DOTALL)
                        if json_match:
                            llm_data = json.loads(json_match.group(1))
                        else:
                            llm_data = {"summary": llm_output[:200], "migration_hints": []}
                    else:
                        llm_data = json.loads(llm_output)

                    summary = llm_data.get('summary', '')
                    migration_hints = llm_data.get('migration_hints', [])
                except json.JSONDecodeError:
                    summary = llm_output[:200]
                    migration_hints = []

            except Exception:
                summary = f"Analysis of {unit_type} {qualified_name}"
                migration_hints = []

            # Build UnitAnalysis
            unit_analysis: UnitAnalysis = {
                "unit_type": unit_type,
                "qualified_name": qualified_name,
                "signature": parsed.get("signature", {}),
                "reads_from": parsed.get("reads_from", []),
                "writes_to": parsed.get("writes_to", []),
                "column_lineage": [],  # Simplified - can be enhanced
                "variable_lineage": [],
                "calls": parsed.get("calls", []),
                "control_flow": {"conditionals": 0, "loops": 0, "exceptions": []},  # Simplified
                "globals_used": parsed.get("globals_used", []),
                "summary": summary,
                "migration_hints": migration_hints
            }

            # Update state
            new_units = list(state.get('units', []))
            new_units.append(unit_analysis)

            new_visited = list(state.get('visited_units', []))
            new_visited.append(qualified_name)

            new_edges = list(state.get('edges', []))

            # Add edges for table reads
            for read_item in parsed.get("reads_from", []):
                new_edges.append({
                    "from": qualified_name,
                    "to": read_item["table"],
                    "type": "READS"
                })

            # Add edges for calls
            for call in parsed.get("calls", []):
                new_edges.append({
                    "from": qualified_name,
                    "to": call,
                    "type": "CALLS"
                })

            # Update tables/views
            new_tables = list(set(state.get('tables', []) + [r["table"] for r in parsed.get("reads_from", [])]))

            return {
                "units": new_units,
                "visited_units": new_visited,
                "edges": new_edges,
                "tables": new_tables
            }

        def finalize_knowledge(state: OracleAnalyzerState) -> Dict[str, Any]:
            """
            Build and persist knowledge artifact to S3.

            Args:
                state: Current workflow state

            Returns:
                Final state update with artifact URI
            """
            root_package_name = state.get('root_package_name', '')

            # Build knowledge artifact
            knowledge_artifact = {
                "root_package": root_package_name,
                "units": state.get('units', []),
                "tables": sorted(list(set(state.get('tables', [])))),
                "views": sorted(list(set(state.get('views', [])))),
                "packages": sorted(list(set(state.get('packages', [])))),
                "edges": state.get('edges', [])
            }

            # Write to S3
            schema, package = parse_package_name(root_package_name)
            s3_key = get_s3_path_for_package(schema, package, 'knowledge')
            s3_ops = self._get_s3_ops()

            s3_ops.write_json(s3_key, knowledge_artifact)

            bucket = os.getenv(self.config['storage']['s3_bucket_env_var'])
            artifact_uri = f"s3://{bucket}/{s3_key}"

            return {
                "status": "complete",
                "knowledge_artifact_uri": artifact_uri
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

        return graph.compile()


# For backwards compatibility - create instance and expose compiled graph
_workflow_instance = OraclePackageAnalyzerWorkflow()
workflow_graph = _workflow_instance.get_compiled_graph()


# For testing
if __name__ == "__main__":
    print("Testing Oracle Package Analyzer Workflow")
    print("-" * 60)

    workflow = OraclePackageAnalyzerWorkflow()
    metadata = workflow.get_metadata()

    print(f"Workflow: {metadata.name}")
    print(f"Description: {metadata.description}")
    print(f"Category: {metadata.category}")
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

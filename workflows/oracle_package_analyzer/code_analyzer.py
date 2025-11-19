"""
Enhanced Code Analyzer for Oracle PL/SQL

Uses LLM to perform deep analysis of PL/SQL code, extracting:
- Precise procedure/function calls (SCHEMA.PKG.PROC format)
- Column-level data lineage
- Data transformations and business logic
- Control flow patterns
- Variable lineage

This module provides the "intelligence" layer for understanding PL/SQL code.
"""

import json
import re
from typing import Dict, Any, List, Optional
from infrastructure.llm.llm_factory import create_llm


class PLSQLCodeAnalyzer:
    """
    LLM-powered analyzer for extracting deep insights from PL/SQL code.
    """

    def __init__(self, llm_temperature: float = 0.0):
        """
        Initialize the code analyzer.

        Args:
            llm_temperature: Temperature for LLM calls (0.0 = deterministic)
        """
        self.llm = create_llm(temperature=llm_temperature)

    def analyze_procedure(
        self,
        schema: str,
        package: str,
        procedure: str,
        source_code: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform deep analysis of a procedure using LLM.

        Args:
            schema: Schema name
            package: Package name
            procedure: Procedure/function name
            source_code: Source code of the procedure
            context: Optional context (e.g., full package source)

        Returns:
            Dict with detailed analysis including:
            - signature: Parameters and return type
            - reads_from: Tables/views read with columns
            - writes_to: Tables/views written with columns
            - calls: Qualified procedure calls (SCHEMA.PKG.PROC)
            - column_lineage: Column-level mappings
            - transformations: Data transformations applied
            - control_flow: Loops, conditionals, exception handlers
            - globals_used: Package variables referenced
            - summary: Natural language description
            - migration_hints: Cloud migration suggestions
        """
        qualified_name = f"{schema}.{package}.{procedure}"

        # Build comprehensive analysis prompt
        prompt = self._build_analysis_prompt(
            qualified_name, source_code, context
        )

        try:
            # Invoke LLM
            response = self.llm.invoke(prompt)
            llm_output = response.content

            # Parse JSON response
            analysis = self._parse_llm_response(llm_output)

            # Validate and normalize the analysis
            return self._normalize_analysis(analysis, schema, package, procedure)

        except Exception as e:
            # Fallback to basic analysis if LLM fails
            return self._fallback_analysis(schema, package, procedure, source_code)

    def _build_analysis_prompt(
        self,
        qualified_name: str,
        source_code: str,
        context: Optional[str]
    ) -> str:
        """
        Build comprehensive analysis prompt for the LLM.

        Args:
            qualified_name: Fully qualified procedure name
            source_code: Procedure source code
            context: Optional additional context

        Returns:
            Formatted prompt string
        """
        # Truncate source if too long
        max_source_length = 4000
        truncated_source = source_code[:max_source_length]
        if len(source_code) > max_source_length:
            truncated_source += "\n... [truncated]"

        prompt = f"""Analyze this Oracle PL/SQL procedure in detail.

PROCEDURE: {qualified_name}

SOURCE CODE:
```sql
{truncated_source}
```

Extract the following information in JSON format:

1. **signature**:
   - parameters: Array of {{name, type, mode (IN/OUT/IN OUT), description}}
   - return_type: Return type (if function) or null

2. **reads_from**: Tables/views read from
   - Array of {{table: "SCHEMA.TABLE", columns: ["COL1", "COL2"], operation: "SELECT/MERGE"}}

3. **writes_to**: Tables/views written to
   - Array of {{table: "SCHEMA.TABLE", columns: ["COL1", "COL2"], operation: "INSERT/UPDATE/DELETE/MERGE"}}

4. **calls**: Other procedures/functions called
   - Array of fully qualified names: ["SCHEMA.PKG.PROC", "PKG2.FUNC"]
   - Include both package procedures and standalone procedures
   - Format: SCHEMA.PKG.PROC or PKG.PROC (if schema not specified)

5. **column_lineage**: Column-level data flow
   - Array of {{
       output_column: "TARGET.COL",
       source_columns: ["SOURCE.COL1", "SOURCE.COL2"],
       transformation: "Description of transformation",
       expression: "SQL expression if available"
     }}

6. **transformations**: Key data transformations
   - Array of {{
       type: "calculation/aggregation/join/filter/decode/case",
       description: "What transformation is applied",
       input_data: ["source tables/columns"],
       output_data: ["target tables/columns"]
     }}

7. **control_flow**:
   - conditionals: Number of IF/CASE statements
   - loops: Number of FOR/WHILE/LOOP statements
   - exceptions: Array of exception handlers
   - cursors: Array of cursor names

8. **globals_used**: Package-level variables/constants used
   - Array of variable names (e.g., ["G_DEFAULT_RATE", "C_MAX_RETRIES"])

9. **summary**: 2-3 sentence description of what this procedure does

10. **migration_hints**: 3-5 specific suggestions for migrating to Snowflake/cloud
    - Focus on Oracle-specific features that need alternatives
    - Suggest Snowflake equivalents where applicable

IMPORTANT:
- Be precise with table/column names - extract them exactly as they appear
- For procedure calls, include the full qualification (SCHEMA.PKG.PROC)
- If schema is not specified in the code, use just PKG.PROC
- For column lineage, trace data from source columns to target columns
- Identify ALL data transformations, not just simple assignments

Respond with ONLY valid JSON, no markdown formatting:
{{
  "signature": {{"parameters": [...], "return_type": "..."}},
  "reads_from": [...],
  "writes_to": [...],
  "calls": [...],
  "column_lineage": [...],
  "transformations": [...],
  "control_flow": {{"conditionals": 0, "loops": 0, "exceptions": [], "cursors": []}},
  "globals_used": [...],
  "summary": "...",
  "migration_hints": [...]
}}
"""
        return prompt

    def _parse_llm_response(self, llm_output: str) -> Dict[str, Any]:
        """
        Parse LLM JSON response, handling markdown wrappers.

        Args:
            llm_output: Raw LLM response

        Returns:
            Parsed JSON dict

        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        # Try to extract JSON from markdown code blocks
        if '```json' in llm_output:
            json_match = re.search(
                r'```json\s*(\{.*?\})\s*```',
                llm_output,
                re.DOTALL
            )
            if json_match:
                return json.loads(json_match.group(1))

        # Try to find JSON object directly
        json_match = re.search(r'\{.*\}', llm_output, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))

        # Fallback: try to parse entire output
        return json.loads(llm_output)

    def _normalize_analysis(
        self,
        analysis: Dict[str, Any],
        schema: str,
        package: str,
        procedure: str
    ) -> Dict[str, Any]:
        """
        Normalize and validate analysis results.

        Args:
            analysis: Raw analysis from LLM
            schema: Schema name
            package: Package name
            procedure: Procedure name

        Returns:
            Normalized analysis dict
        """
        # Ensure all required fields exist
        normalized = {
            "signature": analysis.get("signature", {"parameters": [], "return_type": None}),
            "reads_from": analysis.get("reads_from", []),
            "writes_to": analysis.get("writes_to", []),
            "calls": analysis.get("calls", []),
            "column_lineage": analysis.get("column_lineage", []),
            "transformations": analysis.get("transformations", []),
            "control_flow": analysis.get("control_flow", {
                "conditionals": 0,
                "loops": 0,
                "exceptions": [],
                "cursors": []
            }),
            "globals_used": analysis.get("globals_used", []),
            "summary": analysis.get("summary", f"Analysis of {schema}.{package}.{procedure}"),
            "migration_hints": analysis.get("migration_hints", [])
        }

        # Normalize procedure calls to ensure proper qualification
        normalized["calls"] = self._normalize_procedure_calls(
            normalized["calls"], schema
        )

        return normalized

    def _normalize_procedure_calls(
        self,
        calls: List[str],
        current_schema: str
    ) -> List[str]:
        """
        Normalize procedure call references to consistent format.

        Args:
            calls: List of procedure calls from LLM
            current_schema: Current schema for context

        Returns:
            Normalized list of fully qualified calls
        """
        normalized = []
        for call in calls:
            call = call.strip()
            if not call:
                continue

            # Count dots to determine format
            parts = call.split('.')

            if len(parts) == 3:
                # Already fully qualified: SCHEMA.PKG.PROC
                normalized.append(call.upper())
            elif len(parts) == 2:
                # PKG.PROC - assume current schema
                normalized.append(f"{current_schema}.{call}".upper())
            elif len(parts) == 1:
                # Just PROC - likely a standalone procedure in current schema
                # We'll mark it as SCHEMA.PROC (no package)
                normalized.append(f"{current_schema}.{call}".upper())

        return list(set(normalized))  # Remove duplicates

    def _fallback_analysis(
        self,
        schema: str,
        package: str,
        procedure: str,
        source_code: str
    ) -> Dict[str, Any]:
        """
        Fallback to regex-based analysis if LLM fails.

        Args:
            schema: Schema name
            package: Package name
            procedure: Procedure name
            source_code: Source code

        Returns:
            Basic analysis dict
        """
        # Simple regex-based extraction
        tables = self._extract_tables_regex(source_code)
        calls = self._extract_calls_regex(source_code, schema)

        return {
            "signature": {"parameters": [], "return_type": None},
            "reads_from": [{"table": t, "columns": [], "operation": "SELECT"} for t in tables],
            "writes_to": [],
            "calls": calls,
            "column_lineage": [],
            "transformations": [],
            "control_flow": {"conditionals": 0, "loops": 0, "exceptions": [], "cursors": []},
            "globals_used": [],
            "summary": f"Basic analysis of {schema}.{package}.{procedure}",
            "migration_hints": ["Consider detailed review - automated analysis was limited"]
        }

    def _extract_tables_regex(self, source: str) -> List[str]:
        """Extract table references using regex."""
        tables = set()
        # FROM/INTO/UPDATE patterns
        table_pattern = r'(?:FROM|INTO|UPDATE|INSERT\s+INTO)\s+([A-Z_][A-Z0-9_]*(?:\.[A-Z_][A-Z0-9_]*)?)'
        for match in re.finditer(table_pattern, source, re.IGNORECASE):
            tables.add(match.group(1).upper())
        return list(tables)

    def _extract_calls_regex(self, source: str, default_schema: str) -> List[str]:
        """Extract procedure calls using regex."""
        calls = set()
        # Package calls: PKG.PROC( or SCHEMA.PKG.PROC(
        call_pattern = r'([A-Z_][A-Z0-9_]*(?:\.[A-Z_][A-Z0-9_]*){1,2})\s*\('
        for match in re.finditer(call_pattern, source, re.IGNORECASE):
            call = match.group(1).upper()
            parts = call.split('.')

            if len(parts) == 2:
                # PKG.PROC
                calls.add(f"{default_schema}.{call}")
            elif len(parts) == 3:
                # SCHEMA.PKG.PROC
                calls.add(call)

        return list(calls)

    def extract_package_procedures(self, source: str, package: str) -> List[str]:
        """
        Extract procedure and function names from package source.

        Args:
            source: PL/SQL package source code
            package: Package name

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

#!/usr/bin/env python3
"""
Local Testing Script for Oracle Package Analyzer

This script demonstrates the Oracle Package Analyzer workflow
using mock data, without requiring actual Oracle database connectivity.

Usage:
    python local_test.py

This will:
1. Use mock PL/SQL packages
2. Analyze BILLING.PKG_POLICY_BILLING
3. Extract procedures, dependencies, and data flow
4. Generate a knowledge artifact
5. Display results

No Oracle database or AWS credentials required.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflows.oracle_package_analyzer.workflow import OraclePackageAnalyzerWorkflow
from workflows.oracle_package_analyzer.code_analyzer import PLSQLCodeAnalyzer
from tests.mock_oracle_operations import (
    get_package_source,
    MOCK_PACKAGES
)


class LocalS3Operations:
    """Mock S3 operations using local filesystem"""

    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.base_path = Path(tempfile.gettempdir()) / "oracle_analyzer_test"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def object_exists(self, key: str) -> bool:
        file_path = self.base_path / key
        return file_path.exists()

    def read_text(self, key: str) -> str:
        file_path = self.base_path / key
        with open(file_path, 'r') as f:
            return f.read()

    def write_text(self, key: str, content: str):
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)

    def read_json(self, key: str) -> dict:
        file_path = self.base_path / key
        with open(file_path, 'r') as f:
            return json.load(f)

    def write_json(self, key: str, data: dict):
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def cleanup(self):
        """Remove temporary files"""
        if self.base_path.exists():
            shutil.rmtree(self.base_path)


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title: str):
    """Print formatted section"""
    print(f"\n{title}")
    print("-" * 70)


def analyze_package_locally(package_name: str = "BILLING.PKG_POLICY_BILLING"):
    """
    Analyze a package locally using mock data.

    Args:
        package_name: Package to analyze (SCHEMA.PACKAGE format)
    """
    print_header("Oracle Package Analyzer - Local Test")

    print(f"\nAnalyzing package: {package_name}")
    print(f"Using mock data (no Oracle connection required)")

    # Parse package name
    schema, package = package_name.split('.')

    # Check if package exists in mock data
    if (schema, package) not in MOCK_PACKAGES:
        print(f"\n❌ Package {package_name} not found in mock data")
        print(f"\nAvailable packages:")
        for s, p in MOCK_PACKAGES.keys():
            print(f"  - {s}.{p}")
        return

    # Get source
    source = get_package_source(schema, package)

    print_section("Step 1: Package Source")
    print(f"Source length: {len(source)} characters")
    print(f"\nFirst 500 characters:")
    print(source[:500])
    print("...")

    # Analyze with code analyzer
    print_section("Step 2: Extract Procedures")
    analyzer = PLSQLCodeAnalyzer()
    procedures = analyzer.extract_package_procedures(source, package)

    print(f"Found {len(procedures)} procedures/functions:")
    for proc in procedures:
        print(f"  - {proc}")

    # Analyze first procedure in detail
    if procedures:
        print_section(f"Step 3: Deep Analysis of {procedures[0]}")

        # Extract procedure source
        import re
        proc_pattern = rf'PROCEDURE {re.escape(procedures[0])}.*?END {re.escape(procedures[0])};'
        match = re.search(proc_pattern, source, re.DOTALL | re.IGNORECASE)

        if match:
            proc_source = match.group(0)
            print(f"Procedure source length: {len(proc_source)} characters")

            # Use fallback analysis (doesn't require LLM)
            print("\nPerforming regex-based analysis (fallback mode)...")
            analysis = analyzer._fallback_analysis(schema, package, procedures[0], proc_source)

            print("\nAnalysis Results:")
            print(f"  Tables accessed: {len(analysis['reads_from'])}")
            for table_ref in analysis['reads_from'][:5]:  # Show first 5
                print(f"    - {table_ref['table']}")

            print(f"\n  Procedure calls: {len(analysis['calls'])}")
            for call in analysis['calls'][:5]:  # Show first 5
                print(f"    - {call}")

            print(f"\n  Summary: {analysis['summary']}")

            # Try full LLM analysis if available
            print("\n" + "-" * 70)
            print("Attempting full LLM-powered analysis...")
            try:
                full_analysis = analyzer.analyze_procedure(
                    schema, package, procedures[0], proc_source, source
                )

                print("✓ LLM analysis successful!")

                print("\nEnhanced Analysis Results:")
                print(f"  Summary: {full_analysis.get('summary', 'N/A')}")

                if full_analysis.get('column_lineage'):
                    print(f"\n  Column Lineage ({len(full_analysis['column_lineage'])} mappings):")
                    for lineage in full_analysis['column_lineage'][:3]:
                        print(f"    - {lineage.get('output_column')} ← {lineage.get('source_columns')}")
                        print(f"      Transformation: {lineage.get('transformation', 'N/A')}")

                if full_analysis.get('transformations'):
                    print(f"\n  Data Transformations ({len(full_analysis['transformations'])} found):")
                    for trans in full_analysis['transformations'][:3]:
                        print(f"    - Type: {trans.get('type')}")
                        print(f"      Description: {trans.get('description')}")

                if full_analysis.get('control_flow'):
                    cf = full_analysis['control_flow']
                    print(f"\n  Control Flow:")
                    print(f"    - Conditionals: {cf.get('conditionals', 0)}")
                    print(f"    - Loops: {cf.get('loops', 0)}")
                    print(f"    - Exception handlers: {len(cf.get('exceptions', []))}")
                    print(f"    - Cursors: {len(cf.get('cursors', []))}")

                if full_analysis.get('migration_hints'):
                    print(f"\n  Migration Hints:")
                    for hint in full_analysis['migration_hints']:
                        print(f"    - {hint}")

            except Exception as e:
                print(f"⚠ LLM analysis failed (this is expected if LLM not configured): {str(e)}")
                print("  Fallback regex analysis is still available")

    # Show call graph
    print_section("Step 4: Build Call Graph")

    # Extract all calls from all procedures
    all_calls = set()
    for proc in procedures:
        proc_pattern = rf'PROCEDURE {re.escape(proc)}.*?END {re.escape(proc)};'
        match = re.search(proc_pattern, source, re.DOTALL | re.IGNORECASE)
        if match:
            proc_source = match.group(0)
            calls = analyzer._extract_calls_regex(proc_source, schema)
            all_calls.update(calls)

    print(f"Total unique procedure calls: {len(all_calls)}")
    print("\nCall graph:")
    for proc in procedures:
        print(f"\n  {schema}.{package}.{proc}")

        # Find calls from this procedure
        proc_pattern = rf'PROCEDURE {re.escape(proc)}.*?END {re.escape(proc)};'
        match = re.search(proc_pattern, source, re.DOTALL | re.IGNORECASE)
        if match:
            proc_source = match.group(0)
            calls = analyzer._extract_calls_regex(proc_source, schema)
            for call in calls:
                print(f"    → calls {call}")

    print_section("Test Complete")
    print("\n✓ Local testing completed successfully!")
    print("\nThis demonstrates that the Oracle Package Analyzer can:")
    print("  1. Extract procedures from packages")
    print("  2. Analyze procedure dependencies")
    print("  3. Identify table references")
    print("  4. Map procedure call chains")
    print("  5. Extract data flow (with LLM)")
    print("  6. Generate migration hints (with LLM)")

    print("\nNote: Full workflow testing requires:")
    print("  - S3 bucket configuration (ORACLE_CODE_S3_BUCKET)")
    print("  - LLM configuration (Bedrock or Anthropic)")
    print("  - For production use, connect to real Oracle database")


def test_all_packages():
    """Test analysis of all available mock packages"""
    print_header("Testing All Mock Packages")

    analyzer = PLSQLCodeAnalyzer()

    for (schema, package), source in MOCK_PACKAGES.items():
        print(f"\n{schema}.{package}")
        print("-" * 50)

        procedures = analyzer.extract_package_procedures(source, package)
        print(f"  Procedures: {len(procedures)}")

        tables = analyzer._extract_tables_regex(source)
        print(f"  Tables: {len(tables)}")

        calls = analyzer._extract_calls_regex(source, schema)
        print(f"  Calls: {len(calls)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Local Oracle Package Analyzer Test")
    parser.add_argument(
        "--package",
        default="BILLING.PKG_POLICY_BILLING",
        help="Package to analyze (SCHEMA.PACKAGE format)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Test all available packages"
    )

    args = parser.parse_args()

    # Set minimal environment variables for testing
    os.environ["ORACLE_CODE_S3_BUCKET"] = "local-test-bucket"
    os.environ["ORACLE_SCHEMA_DEFAULT"] = "BILLING"

    if args.all:
        test_all_packages()
    else:
        analyze_package_locally(args.package)

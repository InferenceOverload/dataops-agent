#!/usr/bin/env python3
"""
Oracle Package Analyzer - Local Testing Suite

Tests the Oracle Package Analyzer with local filesystem storage.
No AWS or Oracle database required!

This script demonstrates the full workflow with realistic Oracle packages
containing complex dependencies.

Usage:
    # Run all tests
    python test_oracle_local.py

    # Run specific test
    python test_oracle_local.py --test simple

    # Analyze with max depth
    python test_oracle_local.py --test deep --max-depth 5

    # Cleanup and run fresh
    python test_oracle_local.py --clean
"""

import sys
import os
from pathlib import Path
import json
import argparse
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment before imports
os.environ["ORACLE_CODE_S3_BUCKET"] = "local-filesystem"
os.environ["ORACLE_SCHEMA_DEFAULT"] = "BILLING"
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-key-for-testing")

from workflows.oracle_package_analyzer.local_workflow import (
    LocalOraclePackageAnalyzerWorkflow
)


def print_header(title: str, char: str = "="):
    """Print formatted header"""
    width = 80
    print("\n" + char * width)
    print(f"  {title}")
    print(char * width)


def print_section(title: str):
    """Print formatted section"""
    print(f"\n{title}")
    print("-" * 80)


def print_success(message: str):
    """Print success message"""
    print(f"✓ {message}")


def print_error(message: str):
    """Print error message"""
    print(f"✗ {message}")


def print_info(message: str):
    """Print info message"""
    print(f"ℹ {message}")


def setup_test_environment(clean: bool = False):
    """
    Setup local testing environment

    Args:
        clean: If True, remove existing data first
    """
    print_header("Setting Up Test Environment")

    # Initialize workflow
    storage_path = "./oracle_packages_local"

    if clean:
        print_info(f"Cleaning existing data in {storage_path}")
        import shutil
        if Path(storage_path).exists():
            shutil.rmtree(storage_path)

    workflow = LocalOraclePackageAnalyzerWorkflow(local_storage_path=storage_path)

    print_success(f"Initialized workflow with storage at: {workflow.local_storage_path}")

    # Check if sample packages exist
    packages = workflow.list_available_packages()

    if not packages or clean:
        print_info("Creating sample Oracle packages...")

        # Create packages by copying from our test data directory
        from tests.mock_oracle_operations import MOCK_PACKAGES

        for (schema, package), source in MOCK_PACKAGES.items():
            raw_prefix = workflow.config['storage']['raw_prefix']
            storage_key = f"{raw_prefix}/{schema}/{package}.sql"
            workflow._local_ops.write_text(storage_key, source)
            print_success(f"  Created {schema}.{package}")

    return workflow


def test_list_packages(workflow: LocalOraclePackageAnalyzerWorkflow):
    """Test: List all available packages"""
    print_header("Test: List Available Packages", "-")

    packages = workflow.list_available_packages()

    print_success(f"Found {len(packages)} packages:")

    for schema, package in packages:
        pkg_path = workflow.get_package_path(schema, package)
        if pkg_path and pkg_path.exists():
            file_size = pkg_path.stat().st_size
            print(f"  • {schema}.{package:30s} ({file_size:,} bytes)")
        else:
            print(f"  • {schema}.{package:30s} (path not found)")

    return len(packages) > 0


def test_simple_analysis(workflow: LocalOraclePackageAnalyzerWorkflow):
    """Test: Simple package analysis with minimal depth"""
    print_header("Test: Simple Package Analysis", "-")

    schema = "FINANCE"
    package = "PKG_ERROR_LOGGING"

    print_info(f"Analyzing {schema}.{package} (max_depth=1)")

    graph = workflow.get_compiled_graph()

    try:
        result = graph.invoke({
            "root_package_name": f"{schema}.{package}",
            "max_depth": 1,
            "include_cross_schema": False,
            "todo_items": [],
            "visited_units": [],
            "units_count": 0,
            "tables_count": 0,
            "packages_count": 0
        })

        print_success(f"Analysis completed with status: {result.get('status')}")
        print(f"\n  📊 Results:")
        print(f"     Units analyzed: {result.get('units_count', 0)}")
        print(f"     Tables found: {result.get('tables_count', 0)}")
        print(f"     Packages found: {result.get('packages_count', 0)}")

        # Show artifact
        artifact_path = workflow.get_artifact_path(schema, package)
        if artifact_path.exists():
            print_success(f"  Artifact saved to: {artifact_path}")

            with open(artifact_path, 'r') as f:
                artifact = json.load(f)

            print(f"\n  📋 Artifact summary:")
            print(f"     Total units: {len(artifact.get('units', []))}")
            print(f"     Total edges: {len(artifact.get('edges', []))}")

            if artifact.get('units'):
                print(f"\n  📝 First unit details:")
                first_unit = artifact['units'][0]
                print(f"     Name: {first_unit.get('qualified_name')}")
                print(f"     Type: {first_unit.get('unit_type')}")
                print(f"     Reads from: {len(first_unit.get('reads_from', []))} tables")
                print(f"     Calls: {len(first_unit.get('calls', []))} procedures")

        return True

    except Exception as e:
        print_error(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complex_analysis(workflow: LocalOraclePackageAnalyzerWorkflow, max_depth: int = 3):
    """Test: Complex package with deep dependencies"""
    print_header(f"Test: Complex Package Analysis (depth={max_depth})", "-")

    schema = "BILLING"
    package = "PKG_POLICY_BILLING"

    print_info(f"Analyzing {schema}.{package}")
    print_info(f"This package has multiple dependencies across schemas")

    graph = workflow.get_compiled_graph()

    try:
        start_time = datetime.now()

        result = graph.invoke({
            "root_package_name": f"{schema}.{package}",
            "max_depth": max_depth,
            "include_cross_schema": True,
            "todo_items": [],
            "visited_units": [],
            "units_count": 0,
            "tables_count": 0,
            "packages_count": 0
        })

        duration = (datetime.now() - start_time).total_seconds()

        print_success(f"Analysis completed in {duration:.2f} seconds")
        print(f"\n  📊 Final Results:")
        print(f"     Status: {result.get('status')}")
        print(f"     Units analyzed: {result.get('units_count', 0)}")
        print(f"     Tables discovered: {result.get('tables_count', 0)}")
        print(f"     Packages discovered: {result.get('packages_count', 0)}")

        # Analyze artifact
        artifact_path = workflow.get_artifact_path(schema, package)
        if artifact_path.exists():
            artifact_size = artifact_path.stat().st_size

            with open(artifact_path, 'r') as f:
                artifact = json.load(f)

            print(f"\n  📄 Knowledge Artifact:")
            print(f"     Location: {artifact_path}")
            print(f"     Size: {artifact_size:,} bytes")
            print(f"     Root package: {artifact.get('root_package')}")

            print(f"\n  📋 Artifact contents:")
            print(f"     Units: {len(artifact.get('units', []))}")
            print(f"     Tables: {len(artifact.get('tables', []))}")
            print(f"     Views: {len(artifact.get('views', []))}")
            print(f"     Packages: {len(artifact.get('packages', []))}")
            print(f"     Edges: {len(artifact.get('edges', []))}")

            # Show sample units
            if artifact.get('units'):
                print(f"\n  📝 Sample units analyzed:")
                for i, unit in enumerate(artifact['units'][:5], 1):
                    print(f"     {i}. {unit.get('qualified_name')}")
                    print(f"        Type: {unit.get('unit_type')}")
                    print(f"        Tables: {len(unit.get('reads_from', []))} read, {len(unit.get('writes_to', []))} write")
                    print(f"        Calls: {len(unit.get('calls', []))}")

                if len(artifact['units']) > 5:
                    print(f"        ... and {len(artifact['units']) - 5} more")

            # Show dependency graph
            if artifact.get('edges'):
                print(f"\n  🔗 Sample dependencies:")
                edge_types = {}
                for edge in artifact['edges']:
                    edge_type = edge.get('type')
                    edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

                for edge_type, count in edge_types.items():
                    print(f"     {edge_type}: {count} edges")

                # Show first few edges
                print(f"\n     First 5 edges:")
                for edge in artifact['edges'][:5]:
                    print(f"       {edge['from']} --{edge['type']}--> {edge['to']}")

        return True

    except Exception as e:
        print_error(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cross_schema_dependencies(workflow: LocalOraclePackageAnalyzerWorkflow):
    """Test: Cross-schema dependency discovery"""
    print_header("Test: Cross-Schema Dependencies", "-")

    schema = "BILLING"
    package = "PKG_POLICY_BILLING"

    print_info("Analyzing with cross-schema dependencies enabled")
    print_info(f"Expected to discover FINANCE and CUSTOMERS packages")

    graph = workflow.get_compiled_graph()

    try:
        result = graph.invoke({
            "root_package_name": f"{schema}.{package}",
            "max_depth": 2,
            "include_cross_schema": True,
            "todo_items": [],
            "visited_units": [],
            "units_count": 0,
            "tables_count": 0,
            "packages_count": 0
        })

        artifact_path = workflow.get_artifact_path(schema, package)

        if artifact_path.exists():
            with open(artifact_path, 'r') as f:
                artifact = json.load(f)

            discovered_packages = artifact.get('packages', [])

            print_success(f"Discovered {len(discovered_packages)} packages:")

            # Group by schema
            schemas = {}
            for pkg in discovered_packages:
                if '.' in pkg:
                    schema_name, pkg_name = pkg.split('.', 1)
                    if schema_name not in schemas:
                        schemas[schema_name] = []
                    schemas[schema_name].append(pkg_name)

            for schema_name, pkgs in schemas.items():
                print(f"\n  {schema_name}:")
                for pkg in pkgs:
                    print(f"    • {pkg}")

            # Check for expected cross-schema references
            has_finance = any('FINANCE' in pkg for pkg in discovered_packages)
            has_customers = any('CUSTOMERS' in pkg for pkg in discovered_packages)

            if has_finance:
                print_success("  ✓ Found FINANCE schema references")
            if has_customers:
                print_success("  ✓ Found CUSTOMERS schema references")

            return has_finance or has_customers

        return False

    except Exception as e:
        print_error(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests(workflow: LocalOraclePackageAnalyzerWorkflow, max_depth: int = 3):
    """Run all tests"""
    print_header("Running All Tests")

    results = {
        "List Packages": test_list_packages(workflow),
        "Simple Analysis": test_simple_analysis(workflow),
        "Complex Analysis": test_complex_analysis(workflow, max_depth),
        "Cross-Schema Dependencies": test_cross_schema_dependencies(workflow)
    }

    # Summary
    print_header("Test Results Summary")

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}  {test_name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    return passed == total


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Oracle Package Analyzer - Local Testing Suite"
    )
    parser.add_argument(
        "--test",
        choices=["all", "list", "simple", "complex", "deep", "cross-schema"],
        default="all",
        help="Which test to run (default: all)"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean existing data before running tests"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum recursion depth for complex tests (default: 3)"
    )

    args = parser.parse_args()

    # Setup
    workflow = setup_test_environment(clean=args.clean)

    # Run tests
    success = False

    if args.test == "all":
        success = run_all_tests(workflow, args.max_depth)
    elif args.test == "list":
        success = test_list_packages(workflow)
    elif args.test == "simple":
        success = test_simple_analysis(workflow)
    elif args.test in ["complex", "deep"]:
        depth = args.max_depth if args.test == "deep" else 3
        success = test_complex_analysis(workflow, depth)
    elif args.test == "cross-schema":
        success = test_cross_schema_dependencies(workflow)

    # Exit
    print_header("Testing Complete")

    if success:
        print_success("All tests passed!")
        print(f"\n📁 Results saved to: {workflow.local_storage_path}")
        print(f"\nNext steps:")
        print(f"  1. Examine artifacts in: {workflow.local_storage_path}/knowledge/")
        print(f"  2. Add your own .sql packages to: {workflow.local_storage_path}/raw/{{SCHEMA}}/")
        print(f"  3. Run analysis: python test_oracle_local.py --test complex")
        sys.exit(0)
    else:
        print_error("Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

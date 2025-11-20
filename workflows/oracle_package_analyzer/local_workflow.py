"""
Oracle Package Analyzer - Local Filesystem Version

This is a variant of the main workflow that uses local filesystem instead of S3.
Perfect for testing with local Oracle package files without AWS credentials.

Usage:
    1. Place Oracle package .sql files in: ./oracle_packages_local/raw/{SCHEMA}/{PACKAGE}.sql
    2. Run this workflow
    3. Results saved to: ./oracle_packages_local/knowledge/{SCHEMA}.{PACKAGE}.json

Directory structure:
    oracle_packages_local/
    ├── raw/                    # Your Oracle package source files
    │   ├── BILLING/
    │   │   ├── PKG_POLICY_BILLING.sql
    │   │   └── PKG_CLAIMS.sql
    │   └── FINANCE/
    │       └── PKG_GL_PROCESSING.sql
    └── knowledge/              # Generated analysis artifacts
        ├── BILLING.PKG_POLICY_BILLING.json
        └── FINANCE.PKG_GL_PROCESSING.json
"""

from pathlib import Path
from typing import Optional
import os

from workflows.oracle_package_analyzer.workflow import OraclePackageAnalyzerWorkflow
from infrastructure.storage.local_file_operations import LocalFileOperations


class LocalOraclePackageAnalyzerWorkflow(OraclePackageAnalyzerWorkflow):
    """
    Oracle Package Analyzer using local filesystem instead of S3.

    Inherits all functionality from main workflow but swaps S3 for local storage.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        local_storage_path: str = "./oracle_packages_local"
    ):
        """
        Initialize local Oracle Package Analyzer workflow.

        Args:
            config_path: Optional path to config.yaml
            local_storage_path: Root directory for package files (default: ./oracle_packages_local)
        """
        # Initialize parent class
        super().__init__(config_path)

        # Override S3 operations with local file operations
        self.local_storage_path = Path(local_storage_path).resolve()
        self._local_ops = LocalFileOperations(base_path=str(self.local_storage_path))

        # Set dummy bucket name for compatibility
        os.environ[self.config['storage']['s3_bucket_env_var']] = "local-filesystem"

        print(f"✓ Initialized local workflow with storage at: {self.local_storage_path}")

    def _get_s3_ops(self) -> LocalFileOperations:
        """Override to return local file operations instead of S3"""
        return self._local_ops

    def load_package_from_file(self, schema: str, package: str, file_path: str) -> bool:
        """
        Load an Oracle package from a local .sql file into the storage.

        This is a helper method to import packages into the local storage structure.

        Args:
            schema: Schema name (e.g., "BILLING")
            package: Package name (e.g., "PKG_POLICY_BILLING")
            file_path: Path to the .sql file containing package source

        Returns:
            True if successful, False otherwise

        Example:
            workflow = LocalOraclePackageAnalyzerWorkflow()
            workflow.load_package_from_file(
                "BILLING",
                "PKG_POLICY_BILLING",
                "/path/to/pkg_policy_billing.sql"
            )
        """
        try:
            # Read source file
            source_path = Path(file_path)
            if not source_path.exists():
                print(f"❌ Source file not found: {file_path}")
                return False

            with open(source_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # Determine storage location
            raw_prefix = self.config['storage']['raw_prefix']
            storage_key = f"{raw_prefix}/{schema}/{package}.sql"

            # Write to local storage
            success = self._local_ops.write_text(storage_key, source_code)

            if success:
                full_path = self._local_ops._get_file_path(storage_key)
                print(f"✓ Loaded {schema}.{package} to: {full_path}")
            else:
                print(f"❌ Failed to load {schema}.{package}")

            return success

        except Exception as e:
            print(f"❌ Error loading package: {e}")
            return False

    def list_available_packages(self) -> list:
        """
        List all Oracle packages available in local storage.

        Returns:
            List of tuples: [(schema, package), ...]
        """
        try:
            raw_prefix = self.config['storage']['raw_prefix']
            files = self._local_ops.list_objects(raw_prefix)

            packages = []
            for file_key in files:
                if file_key.endswith('.sql'):
                    # Extract schema and package from path
                    # Format: "oracle/raw/SCHEMA/PACKAGE.sql"
                    parts = Path(file_key).parts
                    if len(parts) >= 4:
                        schema = parts[-2]  # Second to last part
                        package = Path(parts[-1]).stem  # Filename without extension
                        packages.append((schema, package))

            return sorted(packages)

        except Exception as e:
            print(f"Error listing packages: {e}")
            return []

    def get_package_path(self, schema: str, package: str) -> Optional[Path]:
        """
        Get the file path for a package's source code.

        Args:
            schema: Schema name
            package: Package name

        Returns:
            Path to .sql file if it exists, None otherwise
        """
        raw_prefix = self.config['storage']['raw_prefix']
        storage_key = f"{raw_prefix}/{schema}/{package}.sql"

        if self._local_ops.object_exists(storage_key):
            return self._local_ops._get_file_path(storage_key)
        return None

    def get_artifact_path(self, schema: str, package: str) -> Path:
        """
        Get the file path where the analysis artifact will be saved.

        Args:
            schema: Schema name
            package: Package name

        Returns:
            Path to .json artifact file
        """
        knowledge_prefix = self.config['storage']['knowledge_prefix']
        storage_key = f"{knowledge_prefix}/{schema}.{package}.json"
        return self._local_ops._get_file_path(storage_key)

    def get_compiled_graph(self):
        """
        Override to add recursion limit configuration for local testing.

        Complex packages can have deep dependency chains, so we increase
        the recursion limit from default 25 to 100.
        """
        from langgraph.graph import StateGraph

        # Get the parent's graph builder
        parent_graph = super().get_compiled_graph()

        # Note: We can't directly modify the compiled graph's recursion limit
        # Instead, we need to set it when invoking
        return parent_graph


def create_sample_packages(workflow: LocalOraclePackageAnalyzerWorkflow):
    """
    Create sample Oracle package files for testing.

    This generates realistic Oracle packages with dependencies to test the analyzer.
    """
    from tests.mock_oracle_operations import MOCK_PACKAGES

    print("\n" + "=" * 70)
    print("  Creating Sample Oracle Packages")
    print("=" * 70)

    for (schema, package), source in MOCK_PACKAGES.items():
        # Write to local storage
        raw_prefix = workflow.config['storage']['raw_prefix']
        storage_key = f"{raw_prefix}/{schema}/{package}.sql"

        workflow._local_ops.write_text(storage_key, source)

        full_path = workflow._local_ops._get_file_path(storage_key)
        print(f"✓ Created {schema}.{package} at: {full_path}")

    print(f"\n✓ Created {len(MOCK_PACKAGES)} sample packages")
    print(f"\nStorage location: {workflow.local_storage_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Oracle Package Analyzer - Local Filesystem Version"
    )
    parser.add_argument(
        "--storage-path",
        default="./oracle_packages_local",
        help="Root directory for package storage (default: ./oracle_packages_local)"
    )
    parser.add_argument(
        "--create-samples",
        action="store_true",
        help="Create sample Oracle packages for testing"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available packages in storage"
    )
    parser.add_argument(
        "--analyze",
        metavar="SCHEMA.PACKAGE",
        help="Analyze a specific package (e.g., BILLING.PKG_POLICY_BILLING)"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum recursion depth for dependency analysis (default: 3)"
    )
    parser.add_argument(
        "--cross-schema",
        action="store_true",
        help="Include cross-schema dependencies"
    )

    args = parser.parse_args()

    # Set minimal environment variables
    os.environ.setdefault("ORACLE_SCHEMA_DEFAULT", "BILLING")

    # Initialize workflow
    workflow = LocalOraclePackageAnalyzerWorkflow(
        local_storage_path=args.storage_path
    )

    # Handle commands
    if args.create_samples:
        create_sample_packages(workflow)

    elif args.list:
        print("\n" + "=" * 70)
        print("  Available Oracle Packages")
        print("=" * 70)

        packages = workflow.list_available_packages()

        if packages:
            for schema, package in packages:
                pkg_path = workflow.get_package_path(schema, package)
                file_size = pkg_path.stat().st_size if pkg_path else 0
                print(f"  {schema}.{package:30s} ({file_size:,} bytes)")
                print(f"    Location: {pkg_path}")
            print(f"\nTotal packages: {len(packages)}")
        else:
            print("\n  No packages found.")
            print(f"\n  Tip: Use --create-samples to create sample packages")
            print(f"       Or place .sql files in: {workflow.local_storage_path}/raw/{{SCHEMA}}/")

    elif args.analyze:
        # Parse package name
        try:
            schema, package = args.analyze.upper().split('.')
        except ValueError:
            print(f"❌ Invalid package format: {args.analyze}")
            print(f"   Expected format: SCHEMA.PACKAGE (e.g., BILLING.PKG_POLICY_BILLING)")
            exit(1)

        # Check if package exists
        pkg_path = workflow.get_package_path(schema, package)
        if not pkg_path:
            print(f"❌ Package not found: {schema}.{package}")
            print(f"\n   Available packages:")
            for s, p in workflow.list_available_packages():
                print(f"     - {s}.{p}")
            exit(1)

        print("\n" + "=" * 70)
        print(f"  Analyzing Oracle Package: {schema}.{package}")
        print("=" * 70)

        # Get compiled graph
        graph = workflow.get_compiled_graph()

        # Invoke workflow
        print(f"\nStarting analysis...")
        print(f"  Max depth: {args.max_depth}")
        print(f"  Cross-schema: {args.cross_schema}")
        print(f"  Source: {pkg_path}")
        print()

        try:
            result = graph.invoke(
                {
                    "root_package_name": f"{schema}.{package}",
                    "max_depth": args.max_depth,
                    "include_cross_schema": args.cross_schema,
                    "todo_items": [],
                    "visited_units": [],
                    "units_count": 0,
                    "tables_count": 0,
                    "packages_count": 0
                },
                config={"recursion_limit": 100}  # Increased for complex packages
            )

            print("\n" + "=" * 70)
            print("  Analysis Complete")
            print("=" * 70)

            print(f"\n✓ Status: {result.get('status')}")
            print(f"\n📊 Summary:")
            print(f"  - Units analyzed: {result.get('units_count', 0)}")
            print(f"  - Tables discovered: {result.get('tables_count', 0)}")
            print(f"  - Packages discovered: {result.get('packages_count', 0)}")

            # Show artifact location
            artifact_path = workflow.get_artifact_path(schema, package)
            if artifact_path.exists():
                artifact_size = artifact_path.stat().st_size
                print(f"\n📄 Knowledge Artifact:")
                print(f"  Location: {artifact_path}")
                print(f"  Size: {artifact_size:,} bytes")

                # Show sample of artifact
                import json
                with open(artifact_path, 'r') as f:
                    artifact = json.load(f)

                print(f"\n📋 Artifact Contents:")
                print(f"  - Root package: {artifact.get('root_package')}")
                print(f"  - Total units: {len(artifact.get('units', []))}")
                print(f"  - Total tables: {len(artifact.get('tables', []))}")
                print(f"  - Total edges: {len(artifact.get('edges', []))}")

                if artifact.get('units'):
                    print(f"\n  First unit: {artifact['units'][0].get('qualified_name')}")
                    print(f"    Type: {artifact['units'][0].get('unit_type')}")
                    print(f"    Reads from: {len(artifact['units'][0].get('reads_from', []))} tables")
                    print(f"    Calls: {len(artifact['units'][0].get('calls', []))} procedures")

        except Exception as e:
            print(f"\n❌ Analysis failed: {e}")
            import traceback
            traceback.print_exc()

    else:
        # Show help
        parser.print_help()
        print("\n" + "=" * 70)
        print("  Quick Start")
        print("=" * 70)
        print("\n1. Create sample packages:")
        print("   python local_workflow.py --create-samples")
        print("\n2. List available packages:")
        print("   python local_workflow.py --list")
        print("\n3. Analyze a package:")
        print("   python local_workflow.py --analyze BILLING.PKG_POLICY_BILLING")
        print("\n4. Add your own packages:")
        print(f"   Place .sql files in: {workflow.local_storage_path}/raw/{{SCHEMA}}/")

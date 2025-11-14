"""
DataOps Workflow CLI

Command-line interface for workflow development and management.
"""

import click
import os
import json
from pathlib import Path
from typing import Optional
import yaml


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """DataOps Workflow CLI - Tools for workflow development"""
    pass


@cli.command()
@click.argument("workflow_name")
@click.option("--template", "-t", default="simple",
              type=click.Choice(["simple", "iterative", "supervisor", "sequential", "parallel"]),
              help="Template to use")
@click.option("--description", "-d", default="", help="Workflow description")
@click.option("--category", "-c", default="analysis",
              type=click.Choice(["migration", "analysis", "generation", "other"]),
              help="Workflow category")
@click.option("--author", "-a", default="Data Engineering Team", help="Author name")
@click.option("--output-dir", "-o", default="workflows", help="Output directory")
def create(workflow_name: str, template: str, description: str, category: str,
           author: str, output_dir: str):
    """Create a new workflow from template

    Examples:
        dataops-workflow create my_analyzer
        dataops-workflow create data_transformer --template iterative --category migration
    """
    from .templates import get_template, TEMPLATES

    click.echo(f"\n🚀 Creating workflow: {workflow_name}")
    click.echo(f"   Template: {template}")
    click.echo(f"   Category: {category}")
    click.echo(f"   Author: {author}\n")

    # Validate workflow name
    if not workflow_name.replace("_", "").replace("-", "").isalnum():
        click.echo("❌ Error: Workflow name must contain only letters, numbers, underscores, and hyphens", err=True)
        return

    # Normalize workflow name
    workflow_name = workflow_name.lower().replace("-", "_")

    # Create workflow directory
    workflow_path = Path(output_dir) / workflow_name
    if workflow_path.exists():
        if not click.confirm(f"⚠️  Workflow '{workflow_name}' already exists. Overwrite?"):
            click.echo("Cancelled.")
            return

    workflow_path.mkdir(parents=True, exist_ok=True)

    # Get template
    template_files = get_template(template)

    # Template variables
    class_name = "".join(word.capitalize() for word in workflow_name.split("_"))

    variables = {
        "workflow_name": workflow_name,
        "WorkflowName": class_name,
        "description": description or f"TODO: Add description for {workflow_name}",
        "category": category,
        "author": author,
        "template": template
    }

    # Create files
    created_files = []
    for filename, content_template in template_files.items():
        file_path = workflow_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Render template
        content = content_template
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", value)

        file_path.write_text(content)
        created_files.append(str(file_path.relative_to(output_dir)))

    click.echo("✅ Workflow created successfully!\n")
    click.echo("📁 Generated files:")
    for file in created_files:
        click.echo(f"   - {file}")

    click.echo(f"\n📝 Next steps:")
    click.echo(f"   1. Edit {workflow_path}/workflow.py and implement your logic")
    click.echo(f"   2. Update metadata in get_metadata()")
    click.echo(f"   3. Test: dataops-workflow test {workflow_name}")
    click.echo(f"   4. Validate: dataops-workflow validate {workflow_name}")
    click.echo(f"\n   See {workflow_path}/README.md for details\n")


@cli.command()
@click.argument("workflow_name")
@click.option("--input", "-i", help="Input JSON string or file path")
@click.option("--mock-llm", is_flag=True, help="Mock LLM responses")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def test(workflow_name: str, input: Optional[str], mock_llm: bool, verbose: bool):
    """Test a workflow in isolation

    Examples:
        dataops-workflow test my_analyzer --input '{"query": "test"}'
        dataops-workflow test my_analyzer --input test_input.json
    """
    click.echo(f"\n🧪 Testing workflow: {workflow_name}\n")
    click.echo("=" * 80)

    try:
        # Import workflow
        from core.workflow_registry import WORKFLOW_REGISTRY

        # Discover workflows if not already done
        if not WORKFLOW_REGISTRY.workflows:
            WORKFLOW_REGISTRY.discover_workflows()

        # Get workflow
        workflow_graph = WORKFLOW_REGISTRY.get_workflow(workflow_name)
        if not workflow_graph:
            click.echo(f"❌ Error: Workflow '{workflow_name}' not found", err=True)
            click.echo(f"\nAvailable workflows: {', '.join(WORKFLOW_REGISTRY.list_workflows())}")
            return

        # Parse input
        if input:
            if input.startswith("{"):
                input_data = json.loads(input)
            else:
                with open(input, 'r') as f:
                    input_data = json.load(f)
        else:
            # Use default test input
            metadata = WORKFLOW_REGISTRY.get_metadata(workflow_name)
            input_data = {"input": "test query", "session_id": "test", "workflow_name": workflow_name}
            click.echo("⚠️  No input provided, using default test input\n")

        if verbose:
            click.echo("Input:")
            click.echo(json.dumps(input_data, indent=2))
            click.echo()

        # Run workflow
        click.echo("Running workflow...")
        import time
        start_time = time.time()

        result = workflow_graph.invoke(input_data)

        elapsed = time.time() - start_time

        click.echo(f"✅ Complete ({elapsed:.2f}s)\n")

        # Show output
        click.echo("Output:")
        click.echo(json.dumps(result, indent=2, default=str))
        click.echo()
        click.echo("=" * 80)
        click.echo("✅ Test passed\n")

    except Exception as e:
        click.echo(f"\n❌ Test failed: {e}\n", err=True)
        if verbose:
            import traceback
            traceback.print_exc()


@cli.command()
@click.argument("workflow_name")
@click.option("--strict", is_flag=True, help="Fail on warnings")
def validate(workflow_name: str, strict: bool):
    """Validate workflow implementation

    Examples:
        dataops-workflow validate my_analyzer
        dataops-workflow validate my_analyzer --strict
    """
    click.echo(f"\n✓ Validating workflow: {workflow_name}\n")
    click.echo("=" * 80)

    try:
        from core.workflow_registry import WORKFLOW_REGISTRY

        # Discover workflows
        if not WORKFLOW_REGISTRY.workflows:
            WORKFLOW_REGISTRY.discover_workflows()

        # Get workflow metadata
        metadata = WORKFLOW_REGISTRY.get_metadata(workflow_name)
        if not metadata:
            click.echo(f"❌ Error: Workflow '{workflow_name}' not found", err=True)
            return

        warnings = []

        # Validate metadata
        click.echo("✅ Metadata: Valid")
        click.echo(f"   - Name: {metadata.name}")
        click.echo(f"   - Category: {metadata.category}")
        click.echo(f"   - Capabilities: {len(metadata.capabilities)} defined")
        click.echo(f"   - Example queries: {len(metadata.example_queries)} provided")

        if len(metadata.example_queries) < 2:
            warnings.append("Consider adding more example queries (at least 2)")

        if not metadata.description or "TODO" in metadata.description:
            warnings.append("Description contains TODO - please complete it")

        click.echo()

        # Validate graph
        workflow_graph = WORKFLOW_REGISTRY.get_workflow(workflow_name)
        if workflow_graph:
            click.echo("✅ Graph Structure: Valid")
            click.echo("   - Graph compiles successfully")
        else:
            click.echo("❌ Graph Structure: Invalid")
            return

        click.echo()

        # Show warnings
        if warnings:
            click.echo("⚠️  Warnings:")
            for warning in warnings:
                click.echo(f"   - {warning}")
            click.echo()

        click.echo("=" * 80)
        if warnings and strict:
            click.echo(f"❌ Validation: FAILED ({len(warnings)} warnings in strict mode)\n")
            exit(1)
        else:
            status = f"({len(warnings)} warnings)" if warnings else ""
            click.echo(f"✅ Validation: PASSED {status}\n")

    except Exception as e:
        click.echo(f"❌ Validation failed: {e}\n", err=True)
        exit(1)


@cli.command("list")
@click.option("--category", "-c", help="Filter by category")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.option("--show-disabled", is_flag=True, help="Show disabled workflows")
def list_workflows(category: Optional[str], verbose: bool, show_disabled: bool):
    """List all available workflows

    Examples:
        dataops-workflow list
        dataops-workflow list --category migration
        dataops-workflow list --verbose
    """
    from core.workflow_registry import WORKFLOW_REGISTRY

    # Discover workflows
    if not WORKFLOW_REGISTRY.workflows:
        WORKFLOW_REGISTRY.discover_workflows()

    workflows = WORKFLOW_REGISTRY.list_workflows()

    if not workflows:
        click.echo("\n⚠️  No workflows found\n")
        return

    click.echo("\nAvailable Workflows")
    click.echo("=" * 80)
    click.echo()

    displayed = 0
    for name in sorted(workflows):
        metadata = WORKFLOW_REGISTRY.get_metadata(name)

        # Filter by category
        if category and metadata.category != category:
            continue

        displayed += 1

        # Check if disabled
        workflow_path = Path("workflows") / name / "config.yaml"
        is_enabled = True
        if workflow_path.exists():
            with open(workflow_path) as f:
                config = yaml.safe_load(f)
                is_enabled = config.get("workflow", {}).get("enabled", True)

        if not is_enabled and not show_disabled:
            continue

        status = " [DISABLED]" if not is_enabled else ""
        click.echo(f"{metadata.name} ({metadata.category}){status}")
        click.echo(f"  {metadata.description}")

        if verbose:
            click.echo(f"  Version: {metadata.version}")
            click.echo(f"  Author: {metadata.author}")
            click.echo(f"  Capabilities: {', '.join(metadata.capabilities[:3])}")

        if metadata.example_queries:
            click.echo(f"  Example: \"{metadata.example_queries[0]}\"")

        click.echo()

    click.echo("=" * 80)
    click.echo(f"Total: {displayed} workflow(s)\n")


@cli.command()
@click.argument("workflow_name")
@click.option("--enable/--disable", default=True, help="Enable or disable workflow")
def toggle(workflow_name: str, enable: bool):
    """Enable or disable a workflow

    Examples:
        dataops-workflow toggle my_analyzer --disable
        dataops-workflow toggle my_analyzer --enable
    """
    workflow_path = Path("workflows") / workflow_name
    config_path = workflow_path / "config.yaml"

    if not workflow_path.exists():
        click.echo(f"❌ Error: Workflow '{workflow_name}' not found", err=True)
        return

    # Load or create config
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    # Update enabled flag
    if "workflow" not in config:
        config["workflow"] = {}

    config["workflow"]["enabled"] = enable

    # Write back
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    status = "enabled" if enable else "disabled"
    click.echo(f"\n✅ Workflow '{workflow_name}' {status}\n")
    click.echo(f"   Config updated: {config_path}\n")


@cli.command()
@click.argument("workflow_name")
def docs(workflow_name: str):
    """Generate documentation for workflow

    Examples:
        dataops-workflow docs my_analyzer
    """
    from core.workflow_registry import WORKFLOW_REGISTRY

    # Discover workflows
    if not WORKFLOW_REGISTRY.workflows:
        WORKFLOW_REGISTRY.discover_workflows()

    metadata = WORKFLOW_REGISTRY.get_metadata(workflow_name)
    if not metadata:
        click.echo(f"❌ Error: Workflow '{workflow_name}' not found", err=True)
        return

    # Generate markdown documentation
    docs = f"""# {metadata.name.replace('_', ' ').title()} Workflow

## Overview

**Category**: {metadata.category}
**Version**: {metadata.version}
**Author**: {metadata.author}

## Description

{metadata.description}

## Capabilities

{chr(10).join(f'- {cap}' for cap in metadata.capabilities)}

## Example Queries

{chr(10).join(f'- "{query}"' for query in metadata.example_queries)}

## Usage

### Via Orchestrator

```
User: "{metadata.example_queries[0] if metadata.example_queries else 'Your query here'}"
```

### Direct Testing

```bash
dataops-workflow test {workflow_name} --input '{{"query": "test"}}'
```

### Programmatic

```python
from core.workflow_registry import WORKFLOW_REGISTRY

workflow = WORKFLOW_REGISTRY.get_workflow("{workflow_name}")
result = workflow.invoke({{"input": "your input"}})
```

## Configuration

See `workflows/{workflow_name}/config.yaml` for configuration options.

## Testing

```bash
# Test workflow
dataops-workflow test {workflow_name}

# Validate workflow
dataops-workflow validate {workflow_name}
```
"""

    # Write to file
    output_path = Path("workflows") / workflow_name / "README.md"
    output_path.write_text(docs)

    click.echo(f"\n✅ Documentation generated: {output_path}\n")
    click.echo(docs)


def main():
    """Entry point for CLI"""
    cli()


if __name__ == "__main__":
    main()

# Workflow Automation System

## Overview

This document describes the automated workflow intake and management system implemented for the DataOps Agent.

## Key Features

### 1. **CLI Scaffolding Tool**

A command-line tool that generates complete workflow structure from templates:

```bash
dataops-workflow create my_analyzer --template simple --category analysis
```

**What it generates:**
- Complete workflow implementation with TODOs
- State schema
- Configuration file
- Tests
- README documentation
- All with proper naming conventions

### 2. **Flag-Based Enable/Disable**

Simple flag flip in config to control workflow availability:

```yaml
# workflows/my_workflow/config.yaml
workflow:
  enabled: true  # Set to false to disable
```

**Toggle via CLI:**
```bash
dataops-workflow toggle my_workflow --disable  # Disable
dataops-workflow toggle my_workflow --enable   # Enable
```

**What happens when disabled:**
- Skipped during auto-discovery
- Not visible in workflow lists
- Not available to orchestrator
- Instant - no code changes needed

### 3. **Auto-Discovery System**

The `WorkflowRegistry` automatically:
1. Scans `workflows/` directory
2. Checks `config.yaml` for `enabled` flag
3. Imports workflow modules
4. Discovers `BaseWorkflow` subclasses
5. Registers compiled graphs

**Discovery respects enabled flag:**
```python
# In workflow_registry.py
if config.get("workflow", {}).get("enabled", True):
    # Register workflow
else:
    print(f"⊘ Skipping disabled workflow: {workflow_name}")
```

### 4. **Template Library**

Pre-built templates for common patterns:

#### Simple Template
- Single agent workflow
- One LLM call
- Perfect for straightforward queries

#### Iterative Template
- Loop-based processing
- Progressive refinement
- Conditional completion logic

**Future templates:** supervisor, sequential, parallel

### 5. **Validation & Testing**

Built-in validation and testing tools:

```bash
# Validate workflow
dataops-workflow validate my_workflow

# Test workflow
dataops-workflow test my_workflow --input '{"input": "test"}'

# List all workflows
dataops-workflow list --verbose
```

## Architecture

### Component Interaction

```
Developer
    ↓
CLI Tool (dataops-workflow create)
    ↓
Template System
    ↓
Generated Workflow Files
    ↓
Auto-Discovery (WorkflowRegistry)
    ↓
Orchestrator
```

### File Structure

```
workflows/
├── my_workflow/
│   ├── workflow.py        # Implementation
│   ├── config.yaml        # enabled: true/false
│   ├── tests/
│   │   └── test_workflow.py
│   └── README.md
├── another_workflow/
│   ├── workflow.py
│   ├── config.yaml        # enabled: false (disabled)
│   └── ...
```

### Discovery Process

```python
# In WorkflowRegistry.discover_workflows()

for workflow_dir in workflows_path.iterdir():
    # 1. Check if config exists
    config_file = workflow_dir / "config.yaml"

    # 2. Read enabled flag
    if config_file.exists():
        config = yaml.safe_load(config_file)
        is_enabled = config.get("workflow", {}).get("enabled", True)

        # 3. Skip if disabled
        if not is_enabled:
            print(f"⊘ Skipping disabled workflow: {workflow_dir.name}")
            continue

    # 4. Import and register if enabled
    module = importlib.import_module(f"workflows.{workflow_dir.name}.workflow")
    # ... registration logic
```

## Developer Experience

### Before (Manual)

1. Copy existing workflow
2. Rename all files manually
3. Update class names
4. Update imports
5. Create tests from scratch
6. Write documentation
7. Manually register in some central location

**Time:** ~30-60 minutes per workflow

### After (Automated)

```bash
dataops-workflow create my_workflow --template simple
```

1. Complete structure generated
2. All naming conventions correct
3. Tests scaffolded
4. Documentation templated
5. Auto-discovered (zero manual registration)
6. Just customize business logic

**Time:** ~5 minutes to working workflow

## Enable/Disable Workflow Examples

### Scenario 1: Testing in Development

```bash
# Create new workflow
dataops-workflow create experimental_analyzer --template iterative

# Disable it (not ready for orchestrator)
dataops-workflow toggle experimental_analyzer --disable

# Develop and test locally
dataops-workflow test experimental_analyzer --input test.json

# When ready, enable
dataops-workflow toggle experimental_analyzer --enable
```

### Scenario 2: Maintenance Mode

```bash
# Temporarily disable workflow for maintenance
dataops-workflow toggle data_migrator --disable

# Orchestrator no longer routes to it

# Re-enable after fixes
dataops-workflow toggle data_migrator --enable
```

### Scenario 3: Feature Flagging

```yaml
# config.yaml in production
workflow:
  enabled: ${FEATURE_FLAG_ENABLE_NEW_ANALYZER}  # Environment variable

# Or simple boolean
workflow:
  enabled: false  # Disabled in prod, enabled in dev
```

## CLI Commands Reference

### Create
```bash
dataops-workflow create WORKFLOW_NAME [OPTIONS]
  --template, -t    Template (simple, iterative)
  --description, -d Description
  --category, -c    Category (migration, analysis, generation)
  --author, -a      Author name
```

### Toggle
```bash
dataops-workflow toggle WORKFLOW_NAME [--enable|--disable]
```

### List
```bash
dataops-workflow list [OPTIONS]
  --category, -c      Filter by category
  --verbose, -v       Show details
  --show-disabled     Show disabled workflows
```

### Test
```bash
dataops-workflow test WORKFLOW_NAME [OPTIONS]
  --input, -i      Input JSON or file
  --verbose, -v    Verbose output
```

### Validate
```bash
dataops-workflow validate WORKFLOW_NAME [OPTIONS]
  --strict         Fail on warnings
```

### Docs
```bash
dataops-workflow docs WORKFLOW_NAME
```

## Configuration Schema

### Workflow Config (config.yaml)

```yaml
# Workflow control
workflow:
  enabled: true  # Required for toggle feature

# LLM settings
llm:
  model: "claude-sonnet-4-20250514"
  temperature: 0.7
  max_tokens: 4096

# Custom settings (workflow-specific)
custom:
  max_iterations: 10
  timeout: 300
  # ... any workflow-specific config
```

## Implementation Files

### Core Components

1. **cli/workflow_cli.py** - CLI implementation
   - Commands: create, toggle, list, test, validate, docs
   - Click-based interface
   - Colorful output

2. **cli/templates.py** - Template definitions
   - SIMPLE_TEMPLATE
   - ITERATIVE_TEMPLATE
   - Variable substitution system

3. **core/workflow_registry.py** - Enhanced registry
   - Auto-discovery with enabled flag check
   - YAML config reading
   - Graceful error handling

4. **pyproject.toml** - Package config
   - Added `pyyaml` dependency
   - Added `click` dependency
   - Added `dataops-workflow` entry point

### Template Variables

Templates support variable substitution:

- `{{workflow_name}}` → my_workflow
- `{{WorkflowName}}` → MyWorkflow
- `{{description}}` → User's description
- `{{category}}` → Selected category
- `{{author}}` → Author name
- `{{template}}` → Template used

## Benefits

### For Developers

1. **Fast Workflow Creation** - 5 minutes instead of 30+
2. **Consistency** - All workflows follow same structure
3. **Best Practices** - Templates include error handling, tests, docs
4. **No Manual Registration** - Auto-discovery handles it
5. **Easy Enable/Disable** - Simple flag flip

### For Operations

1. **Feature Flags** - Enable/disable workflows without code changes
2. **Gradual Rollout** - Enable in dev, disable in prod
3. **Quick Incident Response** - Disable problematic workflow instantly
4. **Environment Control** - Different workflows in different environments

### For the System

1. **Clean Architecture** - Clear separation of concerns
2. **Maintainable** - Consistent structure across workflows
3. **Testable** - Every workflow has test structure
4. **Documented** - Auto-generated documentation
5. **Extensible** - Easy to add new templates

## Future Enhancements

### Short Term
- Add supervisor template
- Add sequential template
- Add parallel template
- Environment-based config overrides

### Medium Term
- Web UI for workflow management
- Visual workflow builder
- Workflow marketplace
- Template customization via CLI

### Long Term
- AI-assisted workflow generation
- Performance profiling built into CLI
- Auto-optimization suggestions
- Workflow versioning and rollback

## Migration Guide

### Existing Workflows

To add enable/disable support to existing workflows:

1. **Add to config.yaml:**
```yaml
workflow:
  enabled: true
```

2. **That's it!** Registry will auto-detect the flag.

### Testing

```bash
# Verify workflow is enabled
dataops-workflow list --show-disabled

# Disable it
dataops-workflow toggle my_workflow --disable

# Confirm it's gone
dataops-workflow list

# Re-enable
dataops-workflow toggle my_workflow --enable
```

## Conclusion

The workflow automation system provides:

✅ **Fast workflow creation** via CLI scaffolding
✅ **Simple enable/disable** via config flags
✅ **Auto-discovery** with flag awareness
✅ **Best practice templates** for common patterns
✅ **Zero manual registration** required

This transforms workflow development from a 30+ minute manual process into a 5-minute automated process, while providing operational control through simple flag-based toggling.

**Developer experience:**
```bash
# Create
dataops-workflow create my_workflow --template simple

# Customize business logic in workflow.py

# Test
dataops-workflow test my_workflow

# Deploy (auto-discovered!)

# Toggle as needed
dataops-workflow toggle my_workflow --disable/--enable
```

**Simple. Fast. Powerful.**

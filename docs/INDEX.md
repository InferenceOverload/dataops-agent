# DataOps Agent - Documentation Index

**Last Updated**: 2025-11-19

---

## Getting Started

Start here based on your role:

- **New Users**: See [../README.md](../README.md) for project overview
- **Developers**: See [Architecture](#architecture) and [LangGraph Patterns](#development)
- **DevOps**: See [Setup & Deployment](#setup--deployment)
- **Contributors**: See [CLI Tools](#tools) and [Architecture](#architecture)

---

## Setup & Deployment

### Corporate/Enterprise Setup
- [CORPORATE_SETUP.md](CORPORATE_SETUP.md) - SSL, proxy, internal PyPI configuration
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment options (personal vs corporate)

### Local Development & Testing
- [LOCAL_TESTING.md](LOCAL_TESTING.md) - Comprehensive Oracle workflow testing
- [QUICK_START_LOCAL_TESTING.md](QUICK_START_LOCAL_TESTING.md) - 5-minute quickstart

---

## Architecture

### Core Design
- [architecture.md](architecture.md) - **START HERE** - Core system architecture (v1.0)
  - Design principles (loose coupling, infrastructure over patterns)
  - Component definitions (orchestrator, workflows, registry)
  - Workflow development guidelines

---

## Development

### LangGraph Development
- [LANGGRAPH_PATTERNS.md](LANGGRAPH_PATTERNS.md) - **Essential developer reference**
  - Current API patterns (v0.2+)
  - State management
  - Conditional edges
  - Multi-agent patterns
  - Common mistakes to avoid

### Infrastructure & Tools
- [tools-usage-guide.md](tools-usage-guide.md) - How to use S3, DynamoDB tools
  - Quick start examples
  - Configuration
  - Usage patterns
  - Best practices

### LLM Configuration
- [LLM_CONFIGURATION.md](LLM_CONFIGURATION.md) - LLM setup and usage
  - Model selection
  - Tool calling
  - Best practices
  - Cost optimization

---

## Tools

### CLI Tools
- [CLI_QUICKSTART.md](CLI_QUICKSTART.md) - Workflow CLI tool
  - Creating workflows
  - Testing workflows
  - Listing available workflows

---

## Integrations

### MLflow
- [MLFLOW_INTEGRATION.md](MLFLOW_INTEGRATION.md) - MLflow tracking integration
  - Setup instructions
  - Configuration options
  - Usage examples

---

## Project Information

- [../CHANGELOG.md](../CHANGELOG.md) - Version history and release notes

---

## Workflow-Specific Documentation

Individual workflow documentation:
- [../workflows/jil_parser/README.md](../workflows/jil_parser/README.md) - JIL Parser workflow
- [../workflows/oracle_package_analyzer/README.md](../workflows/oracle_package_analyzer/README.md) - Oracle Package Analyzer
- [../oracle_packages_local/README.md](../oracle_packages_local/README.md) - Local test packages

---

## Archived Documentation

Historical and roadmap documents moved to [archive/](archive/):
- POC research notes
- Migration guides (completed)
- Future roadmap proposals
- Deprecated configuration guides

See [archive/README.md](archive/README.md) for details.

---

## Quick Reference

### File Structure
```
dataops-agent/
├── README.md                    # Project overview ⭐
├── CHANGELOG.md                 # Version history
├── docs/
│   ├── INDEX.md                 # This file - Navigation hub ⭐
│   ├── architecture.md          # Core architecture ⭐
│   ├── LANGGRAPH_PATTERNS.md    # Developer reference ⭐
│   ├── LLM_CONFIGURATION.md     # LLM setup
│   ├── tools-usage-guide.md     # Infrastructure tools
│   ├── CLI_QUICKSTART.md        # CLI usage
│   ├── MLFLOW_INTEGRATION.md    # MLflow setup
│   ├── DEPLOYMENT_GUIDE.md      # Deployment options
│   ├── CORPORATE_SETUP.md       # Corporate setup
│   ├── LOCAL_TESTING.md         # Testing guide
│   ├── QUICK_START_LOCAL_TESTING.md # Quick start
│   └── archive/                 # Historical/roadmap docs
├── workflows/                   # Workflow implementations
└── infrastructure/              # Shared utilities
```

### Common Tasks

**I want to...**

- **Understand the system**: Read [architecture.md](architecture.md)
- **Build a workflow**: Read [LANGGRAPH_PATTERNS.md](LANGGRAPH_PATTERNS.md) then [CLI_QUICKSTART.md](CLI_QUICKSTART.md)
- **Use S3/DynamoDB**: Read [tools-usage-guide.md](tools-usage-guide.md)
- **Configure LLM**: Read [LLM_CONFIGURATION.md](LLM_CONFIGURATION.md)
- **Deploy to production**: Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Set up corporate env**: Read [CORPORATE_SETUP.md](CORPORATE_SETUP.md)
- **Test Oracle workflow**: Read [QUICK_START_LOCAL_TESTING.md](QUICK_START_LOCAL_TESTING.md)

---

## Contributing

When adding documentation:
1. Add new docs to the appropriate section above
2. Link from relevant existing docs
3. Add to this index
4. Keep archived content in [archive/](archive/)

---

*This index covers active, maintained documentation. See [archive/](archive/) for historical content.*

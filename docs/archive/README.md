# Archived Documentation

This directory contains historical, completed, and roadmap documentation that is no longer actively maintained but preserved for reference.

---

## Contents

### Historical / POC Documentation

**research_notes.md** (November 2025)
- Original LangGraph research for POC
- Subgraph patterns exploration
- Multi-agent architecture research
- **Status**: POC complete, research validated

---

### Completed Migrations

**UV_MIGRATION.md**
- Migration from pip to UV package manager
- **Status**: Migration complete ✅
- UV is now the standard package manager

**SETUP_UV.md**
- UV setup guide
- **Status**: Integrated into main README
- Moved to archive to avoid duplication

**SETUP_COMPLETE.md**
- Oracle workflow setup completion checklist
- **Status**: Superseded by LOCAL_TESTING.md
- Oracle-specific setup now in comprehensive testing guide

---

### Implemented Features

**IMPROVEMENTS.md**
- Meta-query handler implementation
- Orchestrator improvements for self-description
- **Status**: Implemented ✅
- Feature now part of core orchestrator

---

### Roadmap / Future Proposals

**EXTENSION_PROPOSAL.md** (v2.0 Roadmap)
- Session management
- Artifact management
- Context management
- Workflow Development Kit
- Enhanced orchestration
- API layer
- **Status**: Aspirational - not yet implemented
- Comprehensive extension proposal for future development

**extended-architecture.md** (v2.0 Architecture)
- Extended system architecture
- Session, artifact, context managers
- **Status**: Design complete, implementation pending
- Part of EXTENSION_PROPOSAL roadmap

**implementation-guide.md** (v2.0 Implementation)
- Step-by-step implementation guide for extended architecture
- Week-by-week breakdown
- Code examples for future features
- **Status**: Implementation guide for roadmap features

**cli-tool-spec.md** (CLI Tool Specification)
- `dataops-workflow` CLI tool specification
- Workflow scaffolding, testing, validation
- **Status**: Specification complete, tool not yet built
- Future developer productivity enhancement

**quick-reference.md** (Extended Features Reference)
- Quick reference for extended v2.0 features
- API examples for session/artifact/context management
- **Status**: Reference for future features

**WORKFLOW_AUTOMATION.md**
- Automated workflow intake system
- Flag-based enable/disable
- Auto-discovery enhancements
- **Status**: Partial implementation, full automation pending

---

### LLM Configuration (Consolidated)

**LLM_CONFIGURATION_ANALYSIS.md**
**LLM_CONFIGURATION_QUICK_REFERENCE.md**
**LLM_PROVIDER_CONFIGURATION.md**
**LLM_INTEGRATION_INDEX.md**
- Original LLM configuration documentation (4 separate files)
- **Status**: Consolidated into [../LLM_CONFIGURATION.md](../LLM_CONFIGURATION.md)
- Archived to avoid duplication

---

### Typo/Cleanup

**orcale_package_workflow/**
- Directory with typo (should be "oracle")
- Contains: ORACLE_WORKFLOW_IMPROVEMENTS.md
- **Status**: Archived, correct directory exists in main docs

---

## When to Reference Archived Docs

### Use These Archives When:

1. **Understanding History**
   - How we arrived at current architecture
   - Original POC research and validation

2. **Planning v2.0 Features**
   - EXTENSION_PROPOSAL.md for complete roadmap
   - extended-architecture.md for design
   - implementation-guide.md for step-by-step plan

3. **Researching Completed Work**
   - UV_MIGRATION.md for migration approach
   - IMPROVEMENTS.md for orchestrator enhancements

4. **Historical Context**
   - research_notes.md for LangGraph patterns exploration
   - Original decisions and trade-offs

---

## Current Documentation

For active, maintained documentation, see:
- [../INDEX.md](../INDEX.md) - Documentation index
- [../architecture.md](../architecture.md) - Current architecture (v1.0)
- [../LANGGRAPH_PATTERNS.md](../LANGGRAPH_PATTERNS.md) - Developer reference
- [../LLM_CONFIGURATION.md](../LLM_CONFIGURATION.md) - Consolidated LLM guide

---

## Archive Organization

```
archive/
├── README.md (this file)
│
├── Historical/POC
│   └── research_notes.md
│
├── Completed
│   ├── UV_MIGRATION.md
│   ├── SETUP_UV.md
│   ├── SETUP_COMPLETE.md
│   └── IMPROVEMENTS.md
│
├── Roadmap (v2.0)
│   ├── EXTENSION_PROPOSAL.md
│   ├── extended-architecture.md
│   ├── implementation-guide.md
│   ├── cli-tool-spec.md
│   ├── quick-reference.md
│   └── WORKFLOW_AUTOMATION.md
│
├── Consolidated/Superseded
│   ├── LLM_CONFIGURATION_ANALYSIS.md
│   ├── LLM_CONFIGURATION_QUICK_REFERENCE.md
│   ├── LLM_PROVIDER_CONFIGURATION.md
│   └── LLM_INTEGRATION_INDEX.md
│
└── Cleanup
    └── orcale_package_workflow/
```

---

*Archived: 2025-11-19*
*These documents are preserved for reference but are not actively maintained.*

# LLM Configuration & Bedrock Integration - Complete Index

## Documentation Files

### 1. **LLM_CONFIGURATION_ANALYSIS.md** (19KB) - COMPREHENSIVE REFERENCE
   - Complete technical analysis of current LLM configuration
   - 16 sections covering every aspect of LLM setup
   - Current state, architecture, patterns, and recommendations
   - **Best for:** Detailed understanding and design decisions

### 2. **LLM_CONFIGURATION_QUICK_REFERENCE.md** (5.4KB) - QUICK LOOKUP
   - Executive summary with critical findings
   - Quick reference tables and sections
   - Files to change and environment variables
   - **Best for:** Quick navigation and implementation checklist

### 3. **LLM_INTEGRATION_INDEX.md** (This File)
   - Navigation guide for all LLM-related documentation
   - File locations and cross-references
   - Implementation roadmap

---

## Key Files Mentioned in Analysis

### Configuration Files
- **`.env.example`** - Current environment variables (needs LLM_PROVIDER additions)
- **`workflows/jil_parser/config.yaml`** - Workflow-specific config (exists but unused)

### Core Implementation Files

#### Orchestration Layer
- **`core/orchestrator.py`** (660 lines)
  - LLM initialization: line 37-42
  - Intent detection: line 90
  - Parameter extraction: line 162
  - Status: Needs factory pattern integration

#### Workflows (need factory pattern)
- **`workflows/workflow_a.py`** (127 lines)
  - LLM init: line 31-37
  - Pattern: Simple single-agent

- **`workflows/workflow_b.py`** (200+ lines)
  - LLM init: line 38-44
  - Pattern: Supervisor multi-agent

- **`workflows/workflow_c.py`** (200+ lines)
  - LLM init: similar to workflow_b
  - Pattern: Iterative refinement

- **`workflows/jil_parser/workflow.py`** (200+ lines)
  - LLM init: line 45-60
  - Pattern: Iterative with tools
  - Special note: Uses `llm.bind_tools()`

### Infrastructure Layer

#### Configuration (Pattern Template)
- **`infrastructure/config/aws_config.py`** (199 lines)
  - **EXCELLENT REFERENCE IMPLEMENTATION**
  - Priority system: Overrides > Env > Defaults
  - Pydantic models for validation
  - Global singleton pattern
  - **USE THIS AS TEMPLATE FOR LLMConfig**

#### LLM Support
- **`infrastructure/llm/bedrock_client.py`** (213 lines)
  - Methods: invoke(), invoke_with_tools(), stream()
  - Status: Implemented but not integrated
  - Note: Different interface than ChatAnthropic

#### Tools Registry
- **`infrastructure/tools/__init__.py`**
  - Central registry for all infrastructure tools
  - Factory functions: get_s3_tools(), get_dynamodb_tools()
  - Pattern: Can be extended for LLM tools

#### Storage Operations (Reference)
- **`infrastructure/storage/s3_operations.py`**
  - Pattern for wrapping AWS services
  - Helper methods, error handling
  - Used in jil_parser workflow

### Dependencies
- **`pyproject.toml`**
  - Dependencies: langchain, langgraph, langchain-anthropic, boto3
  - Missing: No provider abstraction library

---

## Files to Create (for Bedrock support)

### Phase 1: Configuration Management
1. **`infrastructure/llm/llm_config.py`** (NEW)
   - LLMProvider enum (ANTHROPIC, BEDROCK)
   - AnthropicConfig Pydantic model
   - BedrockConfig Pydantic model
   - LLMConfig class with priority system
   - get_llm_config() factory function
   - **Template:** Follow infrastructure/config/aws_config.py

2. **`infrastructure/llm/llm_factory.py`** (NEW)
   - create_llm_client(config=None) factory function
   - Provider routing logic
   - Returns ChatAnthropic or BedrockClient

3. **`infrastructure/llm/provider_base.py`** (OPTIONAL)
   - Abstract base class for LLM providers
   - Standardized interface for both implementations
   - Enables seamless provider switching

---

## Implementation Roadmap

### Phase 1: Foundation (Create Files)
```
[ ] Create infrastructure/llm/llm_config.py
    - LLMProvider enum
    - Config models (Anthropic, Bedrock)
    - Priority system implementation
    - get_llm_config() function

[ ] Create infrastructure/llm/llm_factory.py
    - create_llm_client() factory
    - Provider routing
    - Client instantiation

[ ] Update infrastructure/config/__init__.py
    - Export LLMConfig, get_llm_config

[ ] Update .env.example
    - Add LLM_PROVIDER
    - Add BEDROCK_MODEL_ID
    - Add BEDROCK_REGION
```

### Phase 2: Factory Integration (Modify Files)
```
[ ] core/orchestrator.py
    - Replace ChatAnthropic init with factory call
    - Line 37-42: llm = create_llm_client()

[ ] workflows/workflow_a.py
    - Replace ChatAnthropic init
    - Lines 33-37

[ ] workflows/workflow_b.py
    - Replace ChatAnthropic init
    - Lines 40-44

[ ] workflows/workflow_c.py
    - Replace ChatAnthropic init
    - Similar to above

[ ] workflows/jil_parser/workflow.py
    - Replace ChatAnthropic init
    - Handle tools binding for both providers
    - Lines 56-60
```

### Phase 3: Interface Standardization (Optional but Recommended)
```
[ ] Create provider_base.py
    - Abstract base class
    - Define common interface
    - implement() and invoke_with_tools() methods
    - ChatAnthropic wrapper (adapter)
    - BedrockClient wrapper (adapter)
```

### Phase 4: Testing & Validation
```
[ ] Create tests/test_llm_config.py
    - Test LLMConfig initialization
    - Test priority system
    - Test both providers

[ ] Create tests/test_llm_factory.py
    - Test factory function
    - Test provider routing
    - Test client creation

[ ] Update tests/test_orchestrator.py
    - Add provider switching tests

[ ] Update tests/test_workflows.py
    - Add provider-specific tests
```

### Phase 5: Documentation
```
[ ] Update docs/architecture.md
    - Add LLM configuration section
    - Document provider pattern

[ ] Create docs/LLM_PROVIDER_GUIDE.md
    - How to switch providers
    - Environment variables
    - Provider-specific features

[ ] Create docs/MIGRATION_GUIDE.md
    - Guide for updating workflows
    - Before/after examples
```

---

## Critical Changes Summary

### Hardcoded Model IDs (6 locations to update)
| File | Line | Change |
|------|------|--------|
| core/orchestrator.py | 39 | Move to factory |
| workflows/workflow_a.py | 34 | Move to factory |
| workflows/workflow_b.py | 41 | Move to factory |
| workflows/workflow_c.py | ~40 | Move to factory |
| workflows/jil_parser/workflow.py | 57 | Move to factory |
| infrastructure/tools/__init__.py | docstring | Update example |

### Environment Variables to Add
```bash
# Provider selection
LLM_PROVIDER=anthropic                  # or bedrock

# Bedrock configuration (if provider=bedrock)
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_REGION=us-east-1

# Anthropic (already exists)
ANTHROPIC_API_KEY=sk-...
```

---

## Key Design Decisions

### 1. Follow AWSConfig Pattern
**Why:** Already proven pattern in codebase
- Pydantic validation
- Priority system
- Global singleton
- Service-specific config
- Extensible for future providers

### 2. Factory Pattern for Client Creation
**Why:** Decouples provider implementation from usage
- Single point of provider routing
- Easy to add new providers
- Testable provider switching
- No global instances per workflow

### 3. Optional Interface Abstraction
**Why:** ChatAnthropic and BedrockClient have different interfaces
- `.invoke()` vs `.invoke()`
- `.bind_tools()` vs `.invoke_with_tools()`
- Create adapter/wrapper for unified interface
- Not strictly required but highly recommended

### 4. Dependency Injection (Future)
**Why:** Enable testing and flexibility
- Pass LLM client to workflows
- Don't initialize in workflow __init__
- Enables easy provider switching for tests

---

## Known Blockers & Solutions

### 1. Interface Mismatch
**Problem:** ChatAnthropic and BedrockClient have different method signatures
**Solution:** Create provider_base.py with common interface

### 2. Tool Support
**Problem:** JIL Parser uses `llm.bind_tools()` which BedrockClient doesn't have
**Solution:** Implement `bind_tools()` as wrapper around `invoke_with_tools()`

### 3. Global Instance
**Problem:** Orchestrator uses global LLM instance
**Solution:** Switch to factory pattern - call create_llm_client() in each node

### 4. Config Files Not Loaded
**Problem:** config.yaml exists but isn't used
**Solution:** Later enhancement - load config files in factory function

---

## Quick Start Guide

### For Implementation
1. **First:** Read `LLM_CONFIGURATION_ANALYSIS.md` sections 1-4 (Current state)
2. **Then:** Read sections 12-13 (Design recommendations)
3. **Finally:** Create Phase 1 files following AWSConfig pattern

### For Verification
1. Use `LLM_CONFIGURATION_QUICK_REFERENCE.md` as checklist
2. Reference the "Hardcoded Locations" table
3. Verify each file after changes

### For Testing
1. Set `LLM_PROVIDER=bedrock` in .env
2. Set BEDROCK_MODEL_ID and BEDROCK_REGION
3. Run tests with both providers

---

## References & Links

### In Repository
- Configuration Pattern: `/home/user/dataops-agent/infrastructure/config/aws_config.py`
- Current Orchestrator: `/home/user/dataops-agent/core/orchestrator.py`
- Bedrock Client: `/home/user/dataops-agent/infrastructure/llm/bedrock_client.py`
- Example Workflows: `/home/user/dataops-agent/workflows/workflow_*.py`

### Analysis Documents (Generated)
- **Comprehensive:** `docs/LLM_CONFIGURATION_ANALYSIS.md`
- **Quick Ref:** `docs/LLM_CONFIGURATION_QUICK_REFERENCE.md`
- **Navigation:** `docs/LLM_INTEGRATION_INDEX.md` (this file)

---

## Status & Next Steps

### Current Status
- Analysis: COMPLETE
- Documentation: COMPLETE (3 files generated)
- Implementation: READY TO START

### Next Steps
1. Review analysis documents
2. Create Phase 1 infrastructure files
3. Update environment configuration
4. Refactor orchestrator and workflows
5. Add comprehensive tests
6. Update project documentation

---

**Last Updated:** 2025-11-14  
**Analysis Version:** 1.0  
**Status:** Ready for Implementation

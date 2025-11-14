# DataOps Agent - LLM Configuration & Anthropic Integration Analysis

**Analysis Date:** 2025-11-14
**Status:** Complete Infrastructure Mapped

---

## Executive Summary

The DataOps Agent has a **functional but tightly-coupled LLM configuration** with Anthropic hardcoded throughout the codebase. While infrastructure exists for AWS services (S3, DynamoDB, Bedrock), there is **no provider abstraction layer** for switching between LLM services. A structured approach is needed to support Bedrock without duplicating client logic.

---

## 1. CURRENT LLM CONFIGURATION OVERVIEW

### Active LLM Configuration
- **Primary LLM**: ChatAnthropic (Langchain wrapper)
- **Model**: `claude-sonnet-4-20250514` (hardcoded)
- **Authentication**: `ANTHROPIC_API_KEY` (environment variable)
- **Configuration Method**: Inline initialization in each workflow

### Files with LLM Usage

**Orchestration Layer (1 file):**
- `/home/user/dataops-agent/core/orchestrator.py` - Main router LLM

**Workflow Layer (4 files):**
- `/home/user/dataops-agent/workflows/workflow_a.py` - Simple agent
- `/home/user/dataops-agent/workflows/workflow_b.py` - Supervisor pattern
- `/home/user/dataops-agent/workflows/workflow_c.py` - Iterative pattern
- `/home/user/dataops-agent/workflows/jil_parser/workflow.py` - JIL parser

**Infrastructure Layer (1 file):**
- `/home/user/dataops-agent/infrastructure/llm/bedrock_client.py` - Bedrock wrapper

---

## 2. ANTHROPIC API KEY MANAGEMENT

### Environment Variable Handling
**Location:** All LLM initialization points
**Pattern:** Direct env var reading in each component

```python
# Current pattern (repeated 6 times)
from dotenv import load_dotenv
import os

load_dotenv()
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7
)
```

### Configuration File
**File:** `/home/user/dataops-agent/.env.example`

Environment variables defined:
- `ANTHROPIC_API_KEY` - Required, currently Anthropic only
- `AWS_REGION` - AWS region for all services
- `AWS_ACCESS_KEY_ID` - Optional, IAM role fallback
- `AWS_SECRET_ACCESS_KEY` - Optional, IAM role fallback
- `AWS_S3_BUCKET` - Default S3 bucket
- `AWS_DYNAMODB_TABLE` - Default DynamoDB table
- `LANGSMITH_API_KEY` - LangSmith for tracing

### Key Issue: No Provider Selection
The `.env.example` only has `ANTHROPIC_API_KEY`. **No mechanism exists to:**
- Select which LLM provider to use
- Switch between Anthropic and Bedrock
- Store multiple provider credentials

---

## 3. LLM CLIENT INITIALIZATION PATTERNS

### Anthropic (ChatAnthropic) - Current Pattern

**In orchestrator.py (lines 37-42):**
```python
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7
)
```

**Pattern in all workflows:**
- Initialized in `__init__` method
- Model hardcoded in each file
- API key fetched at initialization time
- Temperature varies: 0 for analysis, 0.7 for general tasks

**Hardcoded Models:**
```
orchestrator.py:    "claude-sonnet-4-20250514"
workflow_a.py:      "claude-sonnet-4-20250514"
workflow_b.py:      "claude-sonnet-4-20250514"
workflow_c.py:      "claude-sonnet-4-20250514"
jil_parser/workflow.py: "claude-sonnet-4-20250514"
infrastructure/tools/__init__.py: "claude-sonnet-4-20250514" (in docstring)
```

### Bedrock Client - Incomplete Implementation

**File:** `/home/user/dataops-agent/infrastructure/llm/bedrock_client.py`

**Current Status:** Implemented but **not integrated** into workflows
- Uses boto3 Bedrock Runtime API
- Model default: `"anthropic.claude-sonnet-4-20250514-v1:0"`
- Methods: `invoke()`, `invoke_with_tools()`, `stream()`
- **Problem:** Only used as reference code, no workflows use it

**Bedrock Initialization Pattern:**
```python
self.client = boto3.client('bedrock-runtime', region_name=region)
self.model_id = model_id
```

### Configuration Inconsistency

| Component | LLM Provider | Model Selection | Config Location |
|-----------|---|---|---|
| Orchestrator | ChatAnthropic | Hardcoded | orchestrator.py |
| Workflows A-C | ChatAnthropic | Hardcoded | Each workflow file |
| JIL Parser | ChatAnthropic | Hardcoded | jil_parser/workflow.py |
| Bedrock Client | Bedrock | Hardcoded default | bedrock_client.py |
| Config File | N/A | N/A | .env.example |

---

## 4. EXISTING CONFIGURATION PATTERNS FOR AWS

### AWS Configuration System

**File:** `/home/user/dataops-agent/infrastructure/config/aws_config.py`

**Pattern: Excellent model for provider config!**

```python
class AWSConfig:
    def __init__(self, overrides: Optional[Dict[str, Any]] = None):
        # Priority: Overrides > Env vars > Defaults
        self.s3_config = S3Config(
            default_bucket=os.getenv("AWS_S3_BUCKET"),
            region=os.getenv("AWS_REGION", "us-east-1")
        )
```

**Priority System (highest to lowest):**
1. Runtime overrides (passed parameters)
2. Environment variables
3. Default values

**Methods:**
- `get_region()` - With service-specific support
- `get_s3_bucket()` - Error on missing
- `get_dynamodb_table()` - Error on missing
- `get_boto3_session_kwargs()` - For client creation

**Export pattern:**
```python
def get_aws_config(overrides: Optional[Dict[str, Any]] = None) -> AWSConfig:
    global _global_config
    if _global_config is None or overrides:
        _global_config = AWSConfig(overrides)
    return _global_config
```

### Why This Pattern Works Well

✅ Centralized configuration
✅ Environment variable support
✅ Runtime override capability
✅ Pydantic validation
✅ Global instance management
✅ Service-specific options
✅ Clear priority/precedence

---

## 5. INFRASTRUCTURE TOOLS LAYER

### S3 Tools (Reference Implementation)

**File:** `/home/user/dataops-agent/infrastructure/storage/s3_operations.py`

Pattern shows how to wrap AWS services:
```python
class S3Operations:
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        self.bucket = bucket_name
        self.s3_client = boto3.client('s3', region_name=region)
    
    def upload_file(self, local_path: str, s3_key: str) -> bool:
        # Implementation with error handling
```

### Tools Registry

**File:** `/home/user/dataops-agent/infrastructure/tools/__init__.py`

Central location for tool discovery:
```python
def get_all_tools() -> list[BaseTool]:
    return get_s3_tools() + get_dynamodb_tools()

def get_s3_tools() -> list[BaseTool]:
    # Returns LangChain tools for agent use
```

### Integration Pattern in Workflows

**In jil_parser/workflow.py (lines 55-63):**
```python
self.s3_tools = get_s3_tools()
self.llm = ChatAnthropic(...)
self.llm_with_tools = self.llm.bind_tools(self.s3_tools)
```

---

## 6. CONFIGURATION FILES & YAML

### Workflow-Specific Config

**File:** `/home/user/dataops-agent/workflows/jil_parser/config.yaml`

```yaml
analysis:
  max_iterations: 10
  default_iterations: 3

llm:
  model: "claude-sonnet-4-20250514"
  temperature: 0
  max_tokens: 4096

artifacts:
  store_intermediate: true
  output_format: "json"
```

**Current Status:** Defined but **not loaded/used** in workflow

### Missing Configuration Features

- No YAML loading in workflows
- No config file parser
- Config values hardcoded despite YAML existing
- No support for multiple models/providers in config

---

## 7. DEPENDENCY DECLARATIONS

### pyproject.toml

**LLM Dependencies:**
```toml
dependencies = [
    "langchain>=0.1.0",
    "langgraph>=0.2.0",
    "langchain-anthropic>=0.1.0",  # <- Only Anthropic LLM support
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "boto3>=1.28.0",  # AWS SDK (for Bedrock and storage)
]
```

**Missing:**
- `langchain-aws-bedrock` or direct boto3 Bedrock support (boto3 is included)
- Provider abstraction library (e.g., `litellm`, `llamaindex`, custom)

---

## 8. WORKFLOW IMPLEMENTATION PATTERNS

### Base Workflow Interface

**File:** `/home/user/dataops-agent/core/base_workflow.py`

```python
class BaseWorkflow(ABC):
    @abstractmethod
    def get_metadata(self) -> WorkflowMetadata:
        pass
    
    @abstractmethod
    def get_compiled_graph(self):
        pass
```

**Key Point:** Only requires returning metadata and compiled graph
- **No LLM configuration required at interface level**
- Workflows initialize their own LLM
- **This is where we can inject provider configuration**

### Workflow Instance Example

**workflow_a.py (lines 31-37):**
```python
class SimpleAgentWorkflow(BaseWorkflow):
    def __init__(self):
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.7
        )
    
    def get_compiled_graph(self):
        # Uses self.llm in nodes
```

### Problem with Current Design

- Each workflow hardcodes LLM initialization
- No way to inject provider configuration
- No factory pattern for LLM clients
- **Testing requires real API key**

---

## 9. ORCHESTRATOR USAGE PATTERNS

### Main Orchestrator

**File:** `/home/user/dataops-agent/core/orchestrator.py`

**LLM Usage (2 nodes):**
1. Intent detection (line 90): `llm.invoke(prompt)`
2. Parameter extraction (line 162): `llm.invoke(extraction_prompt)`

**Pattern:**
```python
# Global LLM instance
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7
)

def intent_detection_node(state: OrchestratorState) -> dict:
    response = llm.invoke(prompt)
    workflow_name = response.content.strip().lower()
    return {"detected_intent": workflow_name}
```

**Problem:** Global instance means provider switching affects all workflows simultaneously

---

## 10. KEY FILES FOR BEDROCK INTEGRATION

### Direct Changes Needed

1. **orchestrator.py** (lines 37-42)
   - LLM initialization - needs provider selection

2. **workflow_a.py** (lines 33-37)
   - LLM initialization - needs provider selection

3. **workflow_b.py** (lines 40-44)
   - LLM initialization - needs provider selection

4. **workflow_c.py** (similar pattern)
   - LLM initialization - needs provider selection

5. **jil_parser/workflow.py** (lines 56-60)
   - LLM initialization with tools - needs provider selection

6. **.env.example** (line 7)
   - Add LLM provider selection variable
   - Add Bedrock-specific configuration

### Files to Create

1. **infrastructure/llm/llm_config.py** (NEW)
   - LLM configuration management
   - Provider selection logic
   - Client factory

2. **infrastructure/llm/llm_factory.py** (NEW)
   - Factory for creating LLM clients
   - Provider routing

3. **.env.bedrock** (NEW)
   - Example Bedrock configuration

---

## 11. SUMMARY: EXISTING PATTERNS TO LEVERAGE

### What Works Well

1. **AWSConfig Pattern** (infrastructure/config/aws_config.py)
   - Priority system: Overrides → Env → Defaults
   - Pydantic validation
   - Service-specific configuration
   - Global singleton instance

2. **Environment Variable Handling**
   - .env.example pattern
   - load_dotenv() at startup
   - os.getenv() with defaults

3. **Tool Registry Pattern**
   - Centralized tool imports
   - Factory functions (get_s3_tools(), get_dynamodb_tools())
   - LangChain integration ready

4. **Workflow Registry**
   - Auto-discovery mechanism
   - Metadata-driven capability matching
   - No central coupling

### What Needs to Change

1. **LLM Client Initialization**
   - Move from inline to factory
   - Support provider switching
   - No global instances for orchestrator

2. **Configuration**
   - Add LLM provider selection
   - Add Bedrock credentials/config
   - Support provider-specific options

3. **Dependency Injection**
   - Pass LLM clients to workflows
   - Don't initialize in workflow __init__
   - Enable testing and switching

---

## 12. CHANGES REQUIRED FOR BEDROCK SUPPORT

### New Environment Variables Needed

```bash
# LLM Provider Configuration
LLM_PROVIDER=anthropic          # or bedrock
LLM_MODEL=claude-sonnet-4-20250514

# Anthropic specific
ANTHROPIC_API_KEY=your_key_here

# Bedrock specific (if provider=bedrock)
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_REGION=us-east-1
```

### New Files to Create

1. **infrastructure/llm/llm_config.py**
   - LLMProvider enum (Anthropic, Bedrock)
   - LLMConfig Pydantic model
   - get_llm_config() factory

2. **infrastructure/llm/llm_factory.py**
   - create_llm_client() factory
   - Supports both ChatAnthropic and BedrockClient
   - Respects configuration priority

3. **infrastructure/llm/provider_base.py** (optional)
   - Abstract base for LLM providers
   - Standardized interface

### Files to Modify

1. **core/orchestrator.py**
   - Replace hardcoded ChatAnthropic with factory

2. **workflows/workflow_a.py, b.py, c.py**
   - Replace hardcoded ChatAnthropic with factory

3. **workflows/jil_parser/workflow.py**
   - Replace hardcoded ChatAnthropic with factory
   - Handle tools binding for both providers

4. **.env.example**
   - Add LLM_PROVIDER variable
   - Add BEDROCK_* variables

5. **infrastructure/config/aws_config.py**
   - Add LLMConfig support (optional)

---

## 13. DESIGN RECOMMENDATIONS

### Recommended Approach: LLMConfig Pattern (Following AWSConfig)

Create `infrastructure/llm/llm_config.py` following the AWSConfig pattern:

```python
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv

class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"

class AnthropicConfig(BaseModel):
    api_key: str
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7

class BedrockConfig(BaseModel):
    model_id: str = "anthropic.claude-sonnet-4-20250514-v1:0"
    region: str = "us-east-1"
    temperature: float = 0.7

class LLMConfig:
    def __init__(self, overrides: Optional[Dict[str, Any]] = None):
        self.overrides = overrides or {}
        provider = self._get_provider()
        
        if provider == LLMProvider.ANTHROPIC:
            self.config = AnthropicConfig(...)
        elif provider == LLMProvider.BEDROCK:
            self.config = BedrockConfig(...)
    
    def get_llm_client(self):
        # Return appropriate client
```

### Factory Pattern for LLM Clients

Create `infrastructure/llm/llm_factory.py`:

```python
def create_llm_client(config: Optional[LLMConfig] = None):
    if config is None:
        config = get_llm_config()
    
    if config.provider == LLMProvider.ANTHROPIC:
        return ChatAnthropic(
            api_key=config.anthropic_config.api_key,
            model=config.anthropic_config.model,
            temperature=config.anthropic_config.temperature
        )
    elif config.provider == LLMProvider.BEDROCK:
        return BedrockClient(
            region=config.bedrock_config.region,
            model_id=config.bedrock_config.model_id,
            temperature=config.bedrock_config.temperature
        )
```

### Integration in Workflows

```python
from infrastructure.llm.llm_factory import create_llm_client

class SimpleAgentWorkflow(BaseWorkflow):
    def __init__(self, llm_config=None):
        self.llm = create_llm_client(llm_config)
```

---

## 14. BLOCKERS & CONSIDERATIONS

### Current Blockers for Bedrock Integration

1. **BedrockClient lacks tool support**
   - `invoke_with_tools()` method exists but may need testing
   - JIL parser uses `llm.bind_tools()` - BedrockClient doesn't support this

2. **No abstraction for LLM interface**
   - ChatAnthropic has `.invoke()` and `.bind_tools()`
   - BedrockClient has different method signatures
   - Need common interface or adapter

3. **Hardcoded model names in 6 locations**
   - Orchestrator: line 39
   - Workflow A: line 34
   - Workflow B: line 41
   - Workflow C: similar
   - JIL Parser: line 57
   - Tools __init__.py: docstring example

4. **No configuration loading from config.yaml**
   - JIL Parser has config.yaml but doesn't use it
   - No YAML loader in infrastructure

5. **Missing tests for provider switching**
   - No tests for Bedrock integration
   - No tests for switching providers

---

## 15. IMPLEMENTATION SEQUENCE RECOMMENDATION

### Phase 1: Configuration Foundation
1. Create `infrastructure/llm/llm_config.py`
2. Update `.env.example` with provider config
3. Add LLMConfig to `infrastructure/config/__init__.py`

### Phase 2: Factory Pattern
1. Create `infrastructure/llm/llm_factory.py`
2. Enhance `BedrockClient` for better compatibility
3. Create LLM provider interface (optional but recommended)

### Phase 3: Refactor Orchestrator & Workflows
1. Update orchestrator.py to use factory
2. Update all workflows (workflow_a, b, c, jil_parser)
3. Ensure backward compatibility

### Phase 4: Testing & Validation
1. Write tests for LLM config
2. Write tests for provider switching
3. Validate Bedrock integration
4. Test with real API calls

### Phase 5: Documentation
1. Update architecture.md
2. Add LLM configuration guide
3. Document provider-specific features
4. Add migration guide for workflows

---

## 16. FINAL SUMMARY TABLE

| Aspect | Current State | Needed for Bedrock |
|--------|---|---|
| **LLM Initialization** | Hardcoded ChatAnthropic (6 places) | Factory pattern with config |
| **API Keys** | ANTHROPIC_API_KEY only | Add BEDROCK_REGION, model IDs |
| **Configuration** | Environment variables only | Add LLM provider selection |
| **Config Pattern** | AWSConfig exists (good example) | Replicate for LLM |
| **Tools Support** | ChatAnthropic.bind_tools() works | BedrockClient needs verification |
| **Bedrock Client** | Exists but unused | Integrate into factory |
| **Interface Abstraction** | None | Recommend common interface |
| **Workflow Changes** | 5 files need updates | Dependency injection pattern |
| **Testing** | Missing provider tests | Add provider switching tests |
| **Documentation** | No provider docs | Add configuration guide |

---

## Conclusion

The DataOps Agent has solid foundational patterns (especially AWSConfig), but LLM configuration is tightly coupled to Anthropic. Supporting Bedrock requires:

1. **Creating LLMConfig following the AWSConfig pattern**
2. **Implementing factory pattern for LLM client creation**
3. **Refactoring 6 initialization points to use the factory**
4. **Adding environment variables for provider selection**
5. **Ensuring tool compatibility between providers**

The existing infrastructure patterns are excellent; we just need to apply the same approach to LLM configuration that was already done for AWS services.


# DataOps Agent - LLM Configuration Quick Reference

## Critical Findings

### Current State
- **LLM Provider**: Anthropic (ChatAnthropic) only
- **Configuration**: Hardcoded in 6 locations (orchestrator + 4 workflows + tools)
- **Model ID**: `claude-sonnet-4-20250514` hardcoded everywhere
- **API Key**: `ANTHROPIC_API_KEY` env var
- **Bedrock Client**: Exists but not integrated/unused

### For Bedrock Support, Must Change:

1. **Infrastructure Layer Files to Create:**
   - `infrastructure/llm/llm_config.py` - Configuration management
   - `infrastructure/llm/llm_factory.py` - LLM client factory
   - (Optional) `infrastructure/llm/provider_base.py` - Common interface

2. **Application Layer Files to Modify:**
   - `core/orchestrator.py` - Replace hardcoded ChatAnthropic with factory
   - `workflows/workflow_a.py` - Use factory pattern
   - `workflows/workflow_b.py` - Use factory pattern  
   - `workflows/workflow_c.py` - Use factory pattern
   - `workflows/jil_parser/workflow.py` - Use factory pattern with tools
   - `.env.example` - Add LLM_PROVIDER, BEDROCK config vars

3. **Configuration Updates:**
   - Add to `.env.example`:
     ```
     LLM_PROVIDER=anthropic  # or bedrock
     BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
     BEDROCK_REGION=us-east-1
     ```

## Hardcoded Locations

| File | Line | Current Code |
|------|------|---|
| `core/orchestrator.py` | 39 | `model="claude-sonnet-4-20250514"` |
| `workflows/workflow_a.py` | 34 | `model="claude-sonnet-4-20250514"` |
| `workflows/workflow_b.py` | 41 | `model="claude-sonnet-4-20250514"` |
| `workflows/workflow_c.py` | similar | Same pattern |
| `workflows/jil_parser/workflow.py` | 57 | Same pattern |
| `infrastructure/tools/__init__.py` | docstring | Example code |

## Pattern to Follow: AWSConfig

The codebase already has excellent configuration pattern in `infrastructure/config/aws_config.py`:

```python
# Priority: Overrides → Env Vars → Defaults
class AWSConfig:
    def __init__(self, overrides: Optional[Dict] = None):
        # Load from env, respect overrides, provide defaults
```

**Apply same pattern to LLM configuration** - replicate for `LLMConfig`

## Key Blockers

1. **Interface Mismatch**: ChatAnthropic vs BedrockClient have different methods
   - ChatAnthropic: `.invoke()`, `.bind_tools()`
   - BedrockClient: `.invoke()`, `.invoke_with_tools()`, `.stream()`

2. **Tool Support**: jil_parser uses `llm.bind_tools()` 
   - BedrockClient doesn't have this method
   - Need adapter or common interface

3. **Global vs Local**: Orchestrator uses global LLM instance
   - All workflows hardcode initialization
   - No dependency injection pattern

## Recommended Solution

### Step 1: Create LLMConfig (following AWSConfig pattern)
```python
# infrastructure/llm/llm_config.py
class LLMProvider(Enum):
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"

class LLMConfig:
    def __init__(self, overrides=None):
        self.provider = self._get_provider()  # from env or overrides
        # Load provider-specific config
```

### Step 2: Create Factory
```python
# infrastructure/llm/llm_factory.py
def create_llm_client(config=None):
    if config is None:
        config = get_llm_config()
    
    if config.provider == LLMProvider.ANTHROPIC:
        return ChatAnthropic(...)
    else:  # BEDROCK
        return BedrockClient(...)
```

### Step 3: Refactor Workflows
```python
# Replace in all workflows:
# OLD: self.llm = ChatAnthropic(model="...", api_key=os.getenv(...))
# NEW: self.llm = create_llm_client()
```

## Files to Reference

### Configuration Pattern (Excellent Model)
- `/home/user/dataops-agent/infrastructure/config/aws_config.py` - 199 lines
  - Pydantic models
  - Priority system
  - Global singleton pattern

### Current LLM Implementations
- `/home/user/dataops-agent/infrastructure/llm/bedrock_client.py` - 213 lines
  - Has: invoke(), invoke_with_tools(), stream()
  - Missing: bind_tools() interface
  
### Test Patterns (For testing)
- `/home/user/dataops-agent/tests/test_orchestrator.py`
- `/home/user/dataops-agent/tests/test_workflows.py`

### Environment Setup
- `/home/user/dataops-agent/.env.example` - Current env vars
- `/home/user/dataops-agent/pyproject.toml` - Dependencies

## Environment Variables Needed

### Current
```bash
ANTHROPIC_API_KEY=sk-...
AWS_REGION=us-east-1
AWS_S3_BUCKET=...
AWS_DYNAMODB_TABLE=...
```

### Add for Bedrock Support
```bash
LLM_PROVIDER=anthropic  # or bedrock
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_REGION=us-east-1
```

## Implementation Order

1. **Foundation**: LLMConfig + Factory + Enums
2. **Adapter**: Common interface for both providers (optional but recommended)
3. **Refactor**: Update orchestrator (1 file) then workflows (4 files)
4. **Tests**: Add provider switching tests
5. **Docs**: Update architecture.md with provider docs

## Success Criteria

- [ ] Can switch providers via `LLM_PROVIDER` env var
- [ ] Bedrock client fully integrated (all workflows use factory)
- [ ] Tools work with both providers (or adapter exists)
- [ ] Tests pass with both Anthropic and Bedrock
- [ ] Architecture docs updated
- [ ] No hardcoded model IDs remaining
- [ ] Config follows AWSConfig pattern

## Related Docs in Repo

- `/home/user/dataops-agent/docs/architecture.md` - Current architecture
- `/home/user/dataops-agent/EXTENSION_PROPOSAL.md` - Future features
- `/home/user/dataops-agent/STATUS.md` - Project status
- `/home/user/dataops-agent/README.md` - Setup instructions


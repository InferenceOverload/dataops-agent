# LLM Configuration Guide

**Status**: Current
**Last Updated**: 2025-11-19

---

## Overview

The DataOps Agent uses AWS Bedrock with Claude models for LLM operations. This guide covers configuration and best practices.

---

## Quick Start

### Environment Variables

```bash
# .env file
AWS_REGION=us-east-1
ANTHROPIC_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0

# AWS Credentials (if not using IAM roles)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

### Basic Usage

```python
from langchain_anthropic import ChatAnthropic

# Initialize LLM
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0,
    max_tokens=4096
)

# Simple invocation
response = llm.invoke("Your prompt here")
print(response.content)
```

---

## Configuration Options

### Model Selection

Available models:
- `claude-sonnet-4-20250514` - Latest Sonnet (recommended)
- `claude-opus-4-20250514` - Most capable
- `claude-haiku-4-20250514` - Fastest, most economical

```python
# For complex reasoning
llm = ChatAnthropic(model="claude-opus-4-20250514")

# For simple tasks
llm = ChatAnthropic(model="claude-haiku-4-20250514")
```

### Temperature Settings

- `0.0` - Deterministic, focused (recommended for data tasks)
- `0.5` - Balanced creativity
- `1.0` - Maximum creativity

```python
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0  # Deterministic
)
```

### Token Limits

```python
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    max_tokens=4096  # Adjust based on expected output
)
```

---

## Tool Calling

LangChain Anthropic supports tool calling (function calling):

```python
from langchain_anthropic import ChatAnthropic
from infrastructure.tools import get_s3_tools

llm = ChatAnthropic(model="claude-sonnet-4-20250514")
tools = get_s3_tools()

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# LLM can now call tools
response = llm_with_tools.invoke(
    "Read the file from s3://my-bucket/data.txt"
)
```

---

## Streaming

For real-time responses:

```python
llm = ChatAnthropic(model="claude-sonnet-4-20250514")

for chunk in llm.stream("Tell me a story"):
    print(chunk.content, end="", flush=True)
```

---

## System Prompts

```python
from langchain_core.messages import SystemMessage, HumanMessage

messages = [
    SystemMessage(content="You are a data engineering expert."),
    HumanMessage(content="Explain ETL pipelines")
]

response = llm.invoke(messages)
```

---

## Best Practices

### 1. Use Appropriate Models

- **Data analysis**: Sonnet (good balance)
- **Complex migrations**: Opus (most capable)
- **Simple parsing**: Haiku (fast and cheap)

### 2. Set Temperature to 0 for Deterministic Tasks

```python
# Good for data engineering tasks
llm = ChatAnthropic(temperature=0)
```

### 3. Add Timeouts

```python
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    timeout=60  # 60 second timeout
)
```

### 4. Handle Errors

```python
try:
    response = llm.invoke(prompt)
except Exception as e:
    logger.error(f"LLM invocation failed: {e}")
    # Handle gracefully
```

### 5. Use Caching for Repeated Calls

LangChain provides caching:

```python
from langchain.cache import InMemoryCache
from langchain.globals import set_llm_cache

set_llm_cache(InMemoryCache())
```

---

## Cost Optimization

### 1. Choose the Right Model

- Haiku: ~$0.25 per 1M input tokens
- Sonnet: ~$3 per 1M input tokens
- Opus: ~$15 per 1M input tokens

### 2. Limit Token Usage

```python
# Only request what you need
llm = ChatAnthropic(max_tokens=1024)
```

### 3. Use Prompt Caching

Claude supports prompt caching for repeated prefixes:

```python
# Large system prompt cached automatically
system_prompt = "..." * 1000  # Large prompt
messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content="User query")
]
```

---

## Troubleshooting

### Issue: "Model not found"

**Solution**: Check model ID format:
```python
# Correct for Bedrock
model = "anthropic.claude-sonnet-4-20250514-v1:0"

# Correct for LangChain Anthropic
model = "claude-sonnet-4-20250514"
```

### Issue: "Rate limit exceeded"

**Solution**: Implement retry logic:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_llm(prompt):
    return llm.invoke(prompt)
```

### Issue: "Request timeout"

**Solution**: Increase timeout or reduce prompt size:
```python
llm = ChatAnthropic(timeout=120)  # 2 minutes
```

---

## Configuration in Workflows

### Example: Workflow with LLM

```python
from langchain_anthropic import ChatAnthropic
from core.base_workflow import BaseWorkflow

class MyWorkflow(BaseWorkflow):
    def __init__(self):
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            temperature=0,
            max_tokens=4096
        )

    def get_compiled_graph(self):
        def process_node(state):
            response = self.llm.invoke(state["query"])
            return {"output": response.content}

        # Build graph...
```

---

## AWS Bedrock Configuration

### IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.*"
    }
  ]
}
```

### Regional Availability

Claude models are available in:
- us-east-1 (N. Virginia)
- us-west-2 (Oregon)
- eu-central-1 (Frankfurt)
- ap-southeast-1 (Singapore)

---

## Migration from Other Providers

### From OpenAI

```python
# Before (OpenAI)
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4")

# After (Anthropic)
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-sonnet-4-20250514")
```

Most LangChain code works without changes!

---

## References

- [LangChain Anthropic Docs](https://python.langchain.com/docs/integrations/chat/anthropic)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Claude Model Documentation](https://docs.anthropic.com/claude/docs)

---

## Related Documentation

- [Architecture](architecture.md) - System architecture
- [Tools Usage Guide](tools-usage-guide.md) - Infrastructure tools
- [LangGraph Patterns](LANGGRAPH_PATTERNS.md) - Graph patterns

---

*For archived LLM configuration files, see [docs/archive/](archive/)*

# LLM Provider Configuration

The DataOps Agent now supports multiple LLM providers, allowing you to toggle between:
- **Anthropic API** (direct) - For personal development with Anthropic API key
- **AWS Bedrock** - For organizational deployment using AWS Bedrock

## Quick Start

### 1. Choose Your Provider

Edit your `.env` file and set the `LLM_PROVIDER` variable:

```bash
# For personal development (Anthropic API)
LLM_PROVIDER=anthropic

# For organizational deployment (AWS Bedrock)
LLM_PROVIDER=bedrock
```

### 2. Configure Credentials

#### Option A: Anthropic API (Personal Development)

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

#### Option B: AWS Bedrock (Organizational Deployment)

```bash
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
```

## Configuration Reference

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `LLM_PROVIDER` | Provider to use: `anthropic` or `bedrock` | `anthropic` | No |
| `LLM_TEMPERATURE` | Temperature for LLM calls (0.0 to 1.0) | `0.7` | No |

#### Anthropic-Specific Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | - | Yes (when using Anthropic) |
| `ANTHROPIC_MODEL` | Model name | `claude-sonnet-4-20250514` | No |

#### Bedrock-Specific Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BEDROCK_MODEL_ID` | Bedrock model ID | `anthropic.claude-sonnet-4-20250514-v1:0` | No |
| `BEDROCK_REGION` | AWS region for Bedrock | Falls back to `AWS_REGION` | No |
| `AWS_REGION` | Default AWS region | `us-east-1` | No |
| `AWS_ACCESS_KEY_ID` | AWS access key | - | Yes (when using Bedrock) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | - | Yes (when using Bedrock) |

## Usage Examples

### Basic Usage (Automatic Configuration)

The system automatically uses the provider configured in your `.env` file:

```python
from infrastructure.llm.llm_factory import create_llm

# Uses configuration from environment variables
llm = create_llm()
```

### Runtime Override

You can override the provider at runtime:

```python
from infrastructure.llm.llm_factory import create_llm

# Force Bedrock usage
llm = create_llm(provider="bedrock")

# Force Anthropic usage with custom temperature
llm = create_llm(provider="anthropic", temperature=0.5)

# Override model
llm = create_llm(model="claude-opus-4-20250514")
```

### Check Current Configuration

```python
from infrastructure.llm.llm_factory import get_llm_info

# Get current LLM configuration
info = get_llm_info()
print(f"Provider: {info['provider']}")
print(f"Model: {info['model']}")
print(f"Temperature: {info['temperature']}")
```

## AWS Bedrock Setup

### Prerequisites

1. **AWS Account** with Bedrock access
2. **Model Access** - Request access to Anthropic models in AWS Bedrock console
   - Navigate to AWS Bedrock → Model access
   - Request access to: `Claude Sonnet 4`
3. **IAM Permissions** - Ensure your IAM user/role has:
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
         "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude*"
       }
     ]
   }
   ```

### Configuration Methods

#### Method 1: Environment Variables (Recommended for local development)

```bash
LLM_PROVIDER=bedrock
BEDROCK_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

#### Method 2: AWS CLI Profile (Recommended for personal laptop)

```bash
# Configure AWS CLI
aws configure

# Set provider in .env
LLM_PROVIDER=bedrock
BEDROCK_REGION=us-east-1
```

The system will automatically use credentials from AWS CLI configuration.

#### Method 3: IAM Roles (Recommended for EC2/ECS)

If running on EC2 or ECS with an attached IAM role, no credentials are needed:

```bash
# Only provider configuration needed
LLM_PROVIDER=bedrock
BEDROCK_REGION=us-east-1
```

## Switching Between Providers

### Scenario: Personal Development vs Organization Deployment

You can maintain separate `.env` files:

**`.env.local` (personal laptop with Anthropic API):**
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

**`.env.production` (organizational deployment with Bedrock):**
```bash
LLM_PROVIDER=bedrock
BEDROCK_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
```

Then use:
```bash
# For local development
cp .env.local .env

# For organizational deployment
cp .env.production .env
```

## Supported Models

### Anthropic API Models

- `claude-sonnet-4-20250514` (default)
- `claude-opus-4-20250514`
- `claude-haiku-4-20250514`

Configure via:
```bash
ANTHROPIC_MODEL=claude-opus-4-20250514
```

### AWS Bedrock Model IDs

- `anthropic.claude-sonnet-4-20250514-v1:0` (default)
- `anthropic.claude-opus-4-20250514-v1:0`
- `anthropic.claude-haiku-4-20250514-v1:0`

Configure via:
```bash
BEDROCK_MODEL_ID=anthropic.claude-opus-4-20250514-v1:0
```

## Troubleshooting

### Anthropic API Issues

**Error: "No API key configured"**
- Ensure `ANTHROPIC_API_KEY` is set in `.env`
- Verify the key starts with `sk-ant-`

**Error: "Invalid API key"**
- Check that your API key is valid on https://console.anthropic.com

### Bedrock Issues

**Error: "Could not connect to the endpoint URL"**
- Verify `BEDROCK_REGION` is set correctly
- Ensure the region supports Bedrock (us-east-1, us-west-2, etc.)

**Error: "AccessDeniedException"**
- Check IAM permissions for `bedrock:InvokeModel`
- Verify AWS credentials are configured correctly

**Error: "ResourceNotFoundException: Could not resolve model"**
- Request model access in AWS Bedrock console
- Verify `BEDROCK_MODEL_ID` matches available models

**Error: "ValidationException: Invocation of model ID was not successful"**
- Ensure you have requested and been granted access to the model
- Wait a few minutes after requesting access

## Architecture

The LLM provider system uses a factory pattern:

```
infrastructure/llm/
├── llm_config.py      # Configuration management
├── llm_factory.py     # Factory for creating LLM instances
└── bedrock_client.py  # Legacy Bedrock client (not used by workflows)
```

Both `ChatAnthropic` (from `langchain-anthropic`) and `ChatBedrock` (from `langchain-aws`) implement the same LangChain interface, making them interchangeable in all workflows.

## Migration Guide

All workflows have been updated to use the new factory pattern. If you have custom workflows, update them as follows:

**Before:**
```python
from langchain_anthropic import ChatAnthropic
import os

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7
)
```

**After:**
```python
from infrastructure.llm.llm_factory import create_llm

llm = create_llm()
```

That's it! The factory handles all provider-specific configuration automatically.

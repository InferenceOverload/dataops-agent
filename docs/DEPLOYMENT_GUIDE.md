# DataOps Agent - Deployment Guide

Quick reference for deploying DataOps Agent in different environments.

---

## Environment Comparison

| Feature | Personal/Dev | Corporate |
|---------|-------------|-----------|
| **LLM Provider** | Anthropic API | AWS Bedrock |
| **Authentication** | API Key in .env | AWS IAM Roles |
| **SSL Certificates** | System default | Corporate CA bundle |
| **Network** | Direct internet | Corporate proxy |
| **Package Source** | PyPI.org | Corporate mirror (optional) |

---

## Personal/Development Setup

**Quick Start:**

```bash
# Clone and navigate
git clone https://github.com/InferenceOverload/dataops-agent.git
cd dataops-agent

# Install dependencies
uv sync

# Configure
cp .env.example .env
# Add: ANTHROPIC_API_KEY=your_key

# Run
langgraph dev
```

**Documentation:** See [SETUP_UV.md](SETUP_UV.md)

---

## Corporate/Organizational Setup

**Quick Start:**

```bash
# Clone and navigate
git clone https://github.com/InferenceOverload/dataops-agent.git
cd dataops-agent

# Run interactive corporate setup
make corporate-setup

# Or manual setup:
cp .env.corporate.example .env
# Edit .env with your corporate settings

# Install dependencies
uv sync

# Run
langgraph dev
```

**Documentation:** See [CORPORATE_SETUP.md](CORPORATE_SETUP.md)

---

## Common Corporate Issues & Solutions

### Issue 1: SSL Certificate Errors

**Error:**
```
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**Solution:**
```bash
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE
uv sync
```

### Issue 2: Proxy Connection Failures

**Error:**
```
Connection timeout
Failed to download package
```

**Solution:**
```bash
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
uv sync
```

### Issue 3: UV Sync Fails

**Solution:**
Try the interactive setup script:
```bash
make corporate-setup
```

---

## Configuration Files Reference

| File | Purpose | Environment |
|------|---------|-------------|
| `.env.example` | General template | Both |
| `.env.corporate.example` | Corporate template | Corporate |
| `uv.toml` | UV package manager config | Both |
| `CORPORATE_SETUP.md` | Detailed corporate guide | Corporate |
| `SETUP_UV.md` | UV setup guide | Both |

---

## AWS Bedrock Setup (Corporate)

1. **Enable Bedrock Model Access:**
   - Go to AWS Console → Bedrock
   - Navigate to "Model access"
   - Request access to "Claude Sonnet 4"
   - Wait for approval (usually instant)

2. **Configure IAM Permissions:**
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
         "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
       }
     ]
   }
   ```

3. **Configure Environment:**
   ```bash
   # In .env
   LLM_PROVIDER=bedrock
   BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
   BEDROCK_REGION=us-east-1
   ```

4. **Test Connection:**
   ```bash
   aws bedrock list-foundation-models --region us-east-1
   ```

---

## Switching Between Environments

You can maintain multiple `.env` files:

```bash
# Personal development
cp .env.personal .env

# Corporate deployment
cp .env.corporate .env
```

Or use environment variables:

```bash
# Personal
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-...

# Corporate
export LLM_PROVIDER=bedrock
export AWS_REGION=us-east-1
export SSL_CERT_FILE=/etc/ssl/certs/ca-bundle.crt
```

---

## Makefile Commands

```bash
# Setup
make install              # Basic installation
make install-dev          # With dev dependencies
make corporate-setup      # Interactive corporate setup

# Development
make test                 # Run tests
make lint                 # Check code quality
make format               # Format code

# Running
make dev                  # Start dev server
make run                  # Run orchestrator

# Cleanup
make clean                # Remove artifacts
```

---

## Troubleshooting Checklist

- [ ] Python 3.10+ installed
- [ ] UV package manager installed
- [ ] `.env` file created and configured
- [ ] SSL certificates configured (corporate only)
- [ ] Proxy settings configured (if needed)
- [ ] AWS credentials configured (Bedrock only)
- [ ] Bedrock model access enabled (Bedrock only)
- [ ] Dependencies installed (`uv sync` successful)

---

## Getting Help

1. **Check documentation:**
   - [CORPORATE_SETUP.md](CORPORATE_SETUP.md) - Corporate environments
   - [SETUP_UV.md](SETUP_UV.md) - UV package manager
   - [README.md](README.md) - General documentation

2. **Run diagnostics:**
   ```bash
   # Check Python
   python --version

   # Check UV
   uv --version

   # Check environment
   echo $SSL_CERT_FILE
   echo $HTTP_PROXY

   # Check AWS (if using Bedrock)
   aws sts get-caller-identity
   ```

3. **Contact your IT department** for:
   - Corporate CA certificate bundle
   - Proxy server details
   - Internal PyPI mirror URL
   - AWS account access

---

## Security Best Practices

1. **Never commit credentials:**
   - `.env` is in `.gitignore`
   - Use environment variables
   - Use AWS IAM roles when possible

2. **Use Bedrock for corporate:**
   - Better audit trail
   - Integrated with AWS IAM
   - No external API keys needed

3. **Keep certificates updated:**
   - Work with IT to maintain CA bundles
   - Test after certificate updates

4. **Use least-privilege IAM roles:**
   - Only grant necessary permissions
   - Use separate roles for dev/prod

---

## Support

For issues specific to DataOps Agent:
- Open an issue on GitHub
- Check existing documentation
- Review error logs

For infrastructure issues:
- Contact your IT/DevOps team
- AWS Support (for Bedrock issues)
- Anthropic Support (for API issues)

---

**Ready to deploy? Start with the appropriate setup guide above!**

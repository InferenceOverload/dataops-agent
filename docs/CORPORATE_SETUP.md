# Corporate Environment Setup Guide

This guide helps you set up the DataOps Agent in corporate environments that may have:
- SSL/TLS certificate interception (MITM proxies)
- Corporate firewalls and proxies
- Internal PyPI mirrors
- Network restrictions

---

## Common Corporate Environment Issues

### 1. SSL Certificate Errors

**Symptoms:**
```
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate
SSL verification error
```

**Root Cause:**
Corporate networks often use SSL interception/inspection where the corporate proxy replaces SSL certificates with their own, causing SSL verification failures.

### 2. UV Sync Failures

**Symptoms:**
```
error: Failed to download package
TLS handshake failed
Connection timeout
```

**Root Cause:**
UV package manager can't verify SSL certificates or reach PyPI through corporate proxy.

---

## Solution 1: Configure SSL Certificates

### Step 1: Obtain Corporate CA Certificate

Contact your IT department to get the corporate CA certificate bundle. It's typically:

**Windows:**
- Exported from Certificate Manager (certmgr.msc)
- Located at: `C:\Program Files\Common Files\SSL\ca-bundle.crt`
- Or export from browser: Settings → Security → Manage Certificates

**macOS:**
- Keychain Access → System → Export as .pem
- Often at: `/etc/ssl/cert.pem`

**Linux:**
- `/etc/ssl/certs/ca-certificates.crt` (Debian/Ubuntu)
- `/etc/pki/tls/certs/ca-bundle.crt` (RHEL/CentOS)
- `/etc/ssl/ca-bundle.pem` (OpenSUSE)

### Step 2: Configure Environment Variables

Create or edit `.env` file:

```bash
# Copy example file
cp .env.example .env

# Edit and add certificate configuration
nano .env
```

Add these lines to `.env`:

```bash
# Path to your corporate CA certificate
SSL_CERT_FILE=/path/to/your/corporate-ca-bundle.crt
REQUESTS_CA_BUNDLE=/path/to/your/corporate-ca-bundle.crt

# Export for current session (also add to .bashrc or .zshrc)
export SSL_CERT_FILE=/path/to/your/corporate-ca-bundle.crt
export REQUESTS_CA_BUNDLE=/path/to/your/corporate-ca-bundle.crt
```

**Example paths:**
```bash
# Windows (Git Bash)
SSL_CERT_FILE=C:/Program Files/Git/mingw64/ssl/certs/ca-bundle.crt

# macOS
SSL_CERT_FILE=/etc/ssl/cert.pem

# Linux (Ubuntu/Debian)
SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Linux (RHEL/CentOS)
SSL_CERT_FILE=/etc/pki/tls/certs/ca-bundle.crt
```

### Step 3: Update UV Configuration

Edit `uv.toml` (already created in the repository):

```toml
# Uncomment and configure for your corporate environment
[environments.corporate]
verify-ssl = true
native-tls = true
ca-certificates = "/path/to/your/corporate-ca-bundle.crt"
retries = 5
timeout = 120
```

---

## Solution 2: Configure Corporate Proxy

If your organization requires HTTP/HTTPS proxy:

### Step 1: Get Proxy Information

Ask your IT department for:
- Proxy server address (e.g., `proxy.company.com`)
- Proxy port (e.g., `8080`)
- Whether authentication is required

### Step 2: Configure Proxy in .env

Add to `.env`:

```bash
# HTTP/HTTPS Proxy
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080

# With authentication
HTTP_PROXY=http://username:password@proxy.company.com:8080
HTTPS_PROXY=http://username:password@proxy.company.com:8080

# Exclude local addresses
NO_PROXY=localhost,127.0.0.1,.company.com
```

### Step 3: Configure Proxy in uv.toml

Uncomment in `uv.toml`:

```toml
http-proxy = "http://proxy.company.com:8080"
https-proxy = "http://proxy.company.com:8080"
```

### Step 4: Set System-Wide (Optional)

For persistent proxy settings:

**Linux/macOS (.bashrc or .zshrc):**
```bash
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1
```

**Windows (System Environment Variables):**
```powershell
setx HTTP_PROXY "http://proxy.company.com:8080"
setx HTTPS_PROXY "http://proxy.company.com:8080"
```

---

## Solution 3: Use Corporate PyPI Mirror

If your organization hosts an internal PyPI mirror:

### Configure in .env

```bash
PIP_INDEX_URL=https://pypi.company.com/simple
PIP_TRUSTED_HOST=pypi.company.com
```

### Configure in uv.toml

Uncomment and edit:

```toml
[[index]]
url = "https://pypi.company.com/simple"
default = true
```

---

## Solution 4: Combine All Configurations

For maximum compatibility, combine all three solutions:

### Complete .env Example

```bash
# ============================================================================
# Corporate Environment Configuration
# ============================================================================

# SSL Certificates
SSL_CERT_FILE=/etc/ssl/certs/corporate-ca-bundle.crt
REQUESTS_CA_BUNDLE=/etc/ssl/certs/corporate-ca-bundle.crt

# Corporate Proxy
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080
NO_PROXY=localhost,127.0.0.1,.company.com

# Corporate PyPI Mirror
PIP_INDEX_URL=https://pypi.company.com/simple
PIP_TRUSTED_HOST=pypi.company.com

# ============================================================================
# DataOps Agent Configuration
# ============================================================================

# Use AWS Bedrock for organizational deployment
LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_REGION=us-east-1

# AWS Configuration (uses corporate certificates automatically via SSL_CERT_FILE)
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-dataops-bucket
```

---

## Testing Your Configuration

### 1. Test SSL Certificate Configuration

```bash
# Test with Python
python -c "import requests; print(requests.get('https://pypi.org/simple').status_code)"

# Should output: 200
```

### 2. Test UV with Corporate Settings

```bash
# Load environment variables
source .env  # Linux/macOS
# OR
set -a; source .env; set +a  # Linux/macOS (export all)

# Test UV sync
uv sync

# Should download packages successfully
```

### 3. Test AWS Bedrock Connection

```bash
# Test AWS CLI (if installed)
aws bedrock list-foundation-models --region us-east-1

# Test with Python
python -c "import boto3; client = boto3.client('bedrock', region_name='us-east-1'); print('Success')"
```

---

## Troubleshooting

### Issue: Still Getting SSL Errors

**Try these in order:**

1. **Verify certificate file exists and is readable:**
   ```bash
   ls -la /path/to/corporate-ca-bundle.crt
   cat /path/to/corporate-ca-bundle.crt | head
   ```

2. **Check environment variables are set:**
   ```bash
   echo $SSL_CERT_FILE
   echo $REQUESTS_CA_BUNDLE
   ```

3. **Test with requests library:**
   ```bash
   python -c "import os; import requests; print(f'SSL_CERT_FILE: {os.getenv(\"SSL_CERT_FILE\")}'); print(requests.get('https://pypi.org').status_code)"
   ```

4. **Try system certificate store:**
   ```bash
   # Linux
   SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt uv sync

   # macOS
   SSL_CERT_FILE=/etc/ssl/cert.pem uv sync
   ```

### Issue: UV Sync Still Fails

**Fallback options:**

1. **Disable SSL verification (TEMPORARY - for debugging only):**
   ```bash
   # Add to .env temporarily
   PYTHONHTTPSVERIFY=0
   UV_NO_VERIFY_SSL=1

   # Run UV sync
   uv sync

   # IMPORTANT: Remove these after successful installation!
   ```

2. **Use pip instead of UV temporarily:**
   ```bash
   python -m pip install -e ".[dev]"
   ```

3. **Download packages manually:**
   ```bash
   # Download wheel files on a personal machine
   # Transfer to corporate machine
   # Install from local files
   uv pip install /path/to/downloaded/wheels/*.whl
   ```

### Issue: Proxy Authentication Required

If your proxy requires authentication but you can't embed credentials:

```bash
# Use environment variables
export HTTP_PROXY=http://$(read -p "Username: " user && echo -n $user):$(read -sp "Password: " pass && echo -n $pass)@proxy.company.com:8080
export HTTPS_PROXY=$HTTP_PROXY

# Then run UV sync
uv sync
```

### Issue: AWS Bedrock Connection Fails

1. **Verify SSL_CERT_FILE is set:**
   ```bash
   echo $SSL_CERT_FILE
   ```

2. **Test AWS credentials:**
   ```bash
   aws sts get-caller-identity
   ```

3. **Check Bedrock access:**
   ```bash
   aws bedrock list-foundation-models --region us-east-1
   ```

4. **Verify IAM permissions:**
   - Ensure your AWS role has `bedrock:InvokeModel` permission
   - Check model access is enabled in Bedrock console

---

## Corporate Deployment Best Practices

### 1. Use AWS Bedrock Instead of Anthropic API

For organizational deployment, use AWS Bedrock:

```bash
# In .env
LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_REGION=us-east-1
```

**Benefits:**
- No external API keys needed
- Uses AWS IAM for authentication
- Better for compliance and audit
- Integrated with corporate AWS account
- Respects corporate SSL certificates automatically

### 2. Document Your Corporate Configuration

Create a `corporate-config.md` in your repository:

```markdown
# Corporate Setup - [Your Company]

## Required Configuration

1. SSL Certificate: `/path/to/corporate/ca-bundle.crt`
2. Proxy: `http://proxy.company.com:8080`
3. PyPI Mirror: `https://pypi.company.com/simple`
4. AWS Region: `us-east-1`

## Quick Setup

```bash
cp .env.example .env
# Edit .env with above values
source .env
uv sync
```
```

### 3. Automate Setup with Scripts

Create `scripts/corporate-setup.sh`:

```bash
#!/bin/bash
# Corporate environment setup script

echo "Setting up DataOps Agent for corporate environment..."

# Check if corporate CA cert exists
if [ ! -f "/etc/ssl/certs/corporate-ca-bundle.crt" ]; then
    echo "ERROR: Corporate CA certificate not found"
    echo "Please contact IT for certificate bundle"
    exit 1
fi

# Setup environment
cp .env.example .env
cat >> .env << EOF

# Corporate Configuration (auto-added)
SSL_CERT_FILE=/etc/ssl/certs/corporate-ca-bundle.crt
REQUESTS_CA_BUNDLE=/etc/ssl/certs/corporate-ca-bundle.crt
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080
LLM_PROVIDER=bedrock
EOF

# Export for current session
export SSL_CERT_FILE=/etc/ssl/certs/corporate-ca-bundle.crt
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/corporate-ca-bundle.crt

# Run UV sync
echo "Installing dependencies..."
uv sync

echo "Setup complete! Remember to configure AWS credentials."
```

Make it executable:
```bash
chmod +x scripts/corporate-setup.sh
./scripts/corporate-setup.sh
```

---

## Personal vs Corporate Environments

This repository is designed to work in **both** personal and corporate environments:

| Configuration | Personal | Corporate |
|--------------|----------|-----------|
| **LLM Provider** | Anthropic API | AWS Bedrock |
| **SSL Certs** | System default | Corporate CA bundle |
| **Proxy** | None | Corporate proxy |
| **PyPI** | pypi.org | Corporate mirror (optional) |
| **Authentication** | API key in .env | AWS IAM |

**Switching between environments:**

```bash
# Personal environment
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key

# Corporate environment
LLM_PROVIDER=bedrock
SSL_CERT_FILE=/path/to/corporate/ca-bundle.crt
HTTP_PROXY=http://proxy.company.com:8080
```

---

## Getting Help

1. **Check UV documentation:** https://github.com/astral-sh/uv
2. **Contact IT department** for:
   - Corporate CA certificate bundle
   - Proxy server details
   - Internal PyPI mirror URL
   - AWS account access

3. **Test incrementally:**
   - First, get SSL certificates working
   - Then, add proxy configuration
   - Finally, test full deployment

4. **Document what works:**
   - Save your working `.env` configuration
   - Share setup steps with your team
   - Update this guide with your specific requirements

---

## Quick Reference

### Essential Environment Variables

```bash
# For corporate environments with SSL interception
export SSL_CERT_FILE=/path/to/corporate-ca-bundle.crt
export REQUESTS_CA_BUNDLE=/path/to/corporate-ca-bundle.crt

# For corporate proxy
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080

# Run UV sync
uv sync
```

### Alternative: One-Line Setup

```bash
SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt uv sync
```

---

**Remember:** The goal is to make this repository work seamlessly in BOTH your personal development environment AND your corporate/organizational deployment. Configure as needed for your environment!

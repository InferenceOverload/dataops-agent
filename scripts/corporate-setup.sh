#!/bin/bash
# Corporate Environment Setup Script for DataOps Agent
# This script helps configure the repository for corporate environments

set -e  # Exit on error

echo "=================================="
echo "DataOps Agent - Corporate Setup"
echo "=================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if .env already exists
if [ -f ".env" ]; then
    print_warning ".env file already exists"
    read -p "Do you want to update it? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing .env file"
        exit 0
    fi
    cp .env .env.backup
    print_success "Backed up existing .env to .env.backup"
fi

# Create .env from example
cp .env.example .env
print_success "Created .env from template"

echo ""
echo "Let's configure your corporate environment..."
echo ""

# Detect OS for default certificate paths
OS_TYPE=$(uname -s)
DEFAULT_CERT_PATH=""

case "$OS_TYPE" in
    Linux)
        if [ -f "/etc/ssl/certs/ca-certificates.crt" ]; then
            DEFAULT_CERT_PATH="/etc/ssl/certs/ca-certificates.crt"
        elif [ -f "/etc/pki/tls/certs/ca-bundle.crt" ]; then
            DEFAULT_CERT_PATH="/etc/pki/tls/certs/ca-bundle.crt"
        fi
        ;;
    Darwin)
        DEFAULT_CERT_PATH="/etc/ssl/cert.pem"
        ;;
    *)
        print_warning "Unknown OS type: $OS_TYPE"
        ;;
esac

# SSL Certificate Configuration
echo "--- SSL Certificate Configuration ---"
echo ""

if [ -n "$DEFAULT_CERT_PATH" ] && [ -f "$DEFAULT_CERT_PATH" ]; then
    print_success "System certificate bundle found at: $DEFAULT_CERT_PATH"
    read -p "Use this certificate bundle? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        CERT_PATH="$DEFAULT_CERT_PATH"
    else
        read -p "Enter path to corporate CA certificate bundle: " CERT_PATH
    fi
else
    print_warning "No default certificate bundle found"
    read -p "Enter path to corporate CA certificate bundle (or press Enter to skip): " CERT_PATH
fi

if [ -n "$CERT_PATH" ]; then
    if [ -f "$CERT_PATH" ]; then
        # Add to .env
        cat >> .env << EOF

# Corporate SSL Certificate Configuration (auto-configured)
SSL_CERT_FILE=$CERT_PATH
REQUESTS_CA_BUNDLE=$CERT_PATH
EOF
        print_success "SSL certificate configured: $CERT_PATH"

        # Export for current session
        export SSL_CERT_FILE="$CERT_PATH"
        export REQUESTS_CA_BUNDLE="$CERT_PATH"
    else
        print_error "Certificate file not found: $CERT_PATH"
        print_warning "You'll need to configure SSL_CERT_FILE manually in .env"
    fi
else
    print_warning "Skipping SSL certificate configuration"
fi

echo ""
echo "--- Proxy Configuration ---"
echo ""

read -p "Does your organization use an HTTP/HTTPS proxy? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter proxy URL (e.g., http://proxy.company.com:8080): " PROXY_URL

    if [ -n "$PROXY_URL" ]; then
        cat >> .env << EOF

# Corporate Proxy Configuration (auto-configured)
HTTP_PROXY=$PROXY_URL
HTTPS_PROXY=$PROXY_URL
NO_PROXY=localhost,127.0.0.1
EOF
        print_success "Proxy configured: $PROXY_URL"

        # Export for current session
        export HTTP_PROXY="$PROXY_URL"
        export HTTPS_PROXY="$PROXY_URL"
    fi
fi

echo ""
echo "--- LLM Provider Configuration ---"
echo ""

echo "For corporate deployment, AWS Bedrock is recommended."
echo "For personal use, Anthropic API is simpler."
echo ""
read -p "Use AWS Bedrock (b) or Anthropic API (a)? [b/a]: " -n 1 -r
echo

if [[ $REPLY =~ ^[Bb]$ ]]; then
    # AWS Bedrock configuration
    read -p "Enter AWS region (default: us-east-1): " AWS_REGION
    AWS_REGION=${AWS_REGION:-us-east-1}

    cat >> .env << EOF

# LLM Provider Configuration (auto-configured for corporate)
LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_REGION=$AWS_REGION
AWS_REGION=$AWS_REGION
EOF
    print_success "Configured for AWS Bedrock in region: $AWS_REGION"
    print_warning "Make sure your AWS credentials are configured (AWS CLI or IAM role)"
else
    # Anthropic API configuration
    read -p "Enter your Anthropic API key: " ANTHROPIC_KEY

    if [ -n "$ANTHROPIC_KEY" ]; then
        sed -i.bak "s/^ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$ANTHROPIC_KEY/" .env
        rm -f .env.bak
        print_success "Configured for Anthropic API"
    else
        print_warning "No API key provided. You'll need to add it manually to .env"
    fi
fi

echo ""
echo "--- Testing Configuration ---"
echo ""

# Test Python SSL
echo "Testing Python SSL configuration..."
if python3 -c "import ssl; import urllib.request; urllib.request.urlopen('https://pypi.org')" 2>/dev/null; then
    print_success "Python SSL configuration is working"
else
    print_warning "Python SSL test failed - you may need to adjust certificate configuration"
fi

echo ""
echo "--- Installing Dependencies ---"
echo ""

# Check if uv is installed
if command -v uv &> /dev/null; then
    print_success "UV package manager found"
    echo "Running uv sync..."

    if uv sync; then
        print_success "Dependencies installed successfully!"
    else
        print_error "UV sync failed"
        echo ""
        echo "Troubleshooting steps:"
        echo "1. Check your SSL certificate configuration in .env"
        echo "2. Verify proxy settings if applicable"
        echo "3. See CORPORATE_SETUP.md for detailed troubleshooting"
        exit 1
    fi
else
    print_error "UV package manager not found"
    echo "Install UV first: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo ""
echo "=================================="
echo "✓ Corporate Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Review .env file and adjust as needed"
echo "2. Configure AWS credentials if using Bedrock"
echo "3. Run tests: make test"
echo "4. Start development: langgraph dev"
echo ""
echo "For detailed documentation, see:"
echo "- CORPORATE_SETUP.md - Complete corporate setup guide"
echo "- SETUP_UV.md - UV package manager guide"
echo "- README.md - General project documentation"
echo ""
print_success "Setup complete! Happy coding!"

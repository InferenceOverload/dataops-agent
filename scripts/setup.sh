#!/bin/bash
# DataOps Agent Setup Script

set -e

echo "🚀 DataOps Agent - Automated Setup"
echo "===================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}UV not found. Installing UV...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    echo -e "${GREEN}✓ UV installed${NC}"
else
    echo -e "${GREEN}✓ UV found${NC}"
fi

# Check Python version
echo -e "\n${BLUE}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Create virtual environment
echo -e "\n${BLUE}Creating virtual environment...${NC}"
uv venv
echo -e "${GREEN}✓ Virtual environment created${NC}"

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Install dependencies
echo -e "\n${BLUE}Installing dependencies...${NC}"
read -p "Install profile (1=production, 2=dev, 3=all): " profile
case $profile in
    1)
        echo "Installing production dependencies..."
        uv pip install -e .
        ;;
    2)
        echo "Installing development dependencies..."
        uv pip install -e ".[dev]"
        ;;
    3)
        echo "Installing all dependencies..."
        uv pip install -e ".[all]"
        ;;
    *)
        echo "Invalid choice. Installing production dependencies..."
        uv pip install -e .
        ;;
esac
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Setup environment file
echo -e "\n${BLUE}Setting up environment...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠ Created .env file. Please add your ANTHROPIC_API_KEY${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Install pre-commit hooks (if dev profile)
if [ "$profile" == "2" ] || [ "$profile" == "3" ]; then
    echo -e "\n${BLUE}Installing pre-commit hooks...${NC}"
    uv run pre-commit install
    echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"
fi

# Run tests
echo -e "\n${BLUE}Running tests...${NC}"
if uv run pytest tests/ -v --maxfail=1; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${YELLOW}⚠ Some tests failed (this might be expected if API key not set)${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Setup complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your ANTHROPIC_API_KEY"
echo "2. Run 'make dev' to start LangGraph dev server"
echo "3. Or run 'make run' to test the orchestrator"
echo ""
echo "For more commands, run 'make help'"
echo ""

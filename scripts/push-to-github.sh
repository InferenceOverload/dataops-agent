#!/bin/bash
# Push DataOps Agent to GitHub

set -e

echo "🚀 DataOps Agent - GitHub Setup"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if gh CLI is installed
if command -v gh &> /dev/null; then
    echo -e "${GREEN}✓ GitHub CLI (gh) found${NC}"
    USE_GH_CLI=true
else
    echo -e "${YELLOW}⚠ GitHub CLI (gh) not found${NC}"
    echo "  Install with: brew install gh (Mac) or see https://cli.github.com/"
    echo "  Will use manual GitHub repository creation"
    USE_GH_CLI=false
fi

# Get repository details
echo ""
echo -e "${BLUE}Repository Configuration:${NC}"
read -p "GitHub username: " GITHUB_USER
read -p "Repository name [dataops-agent]: " REPO_NAME
REPO_NAME=${REPO_NAME:-dataops-agent}
read -p "Make repository private? (y/n) [n]: " IS_PRIVATE
IS_PRIVATE=${IS_PRIVATE:-n}

if [[ "$IS_PRIVATE" == "y" ]]; then
    VISIBILITY="private"
else
    VISIBILITY="public"
fi

echo ""
echo -e "${BLUE}Summary:${NC}"
echo "  Repository: ${GITHUB_USER}/${REPO_NAME}"
echo "  Visibility: ${VISIBILITY}"
echo ""
read -p "Continue? (y/n): " CONFIRM

if [[ "$CONFIRM" != "y" ]]; then
    echo "Aborted."
    exit 1
fi

# Initialize git if needed
if [ ! -d .git ]; then
    echo ""
    echo -e "${BLUE}Initializing git repository...${NC}"
    git init
    git branch -M main
    echo -e "${GREEN}✓ Git repository initialized${NC}"
else
    echo -e "${GREEN}✓ Git repository already initialized${NC}"
fi

# Add all files
echo ""
echo -e "${BLUE}Adding files to git...${NC}"
git add .

# Create initial commit
echo ""
echo -e "${BLUE}Creating initial commit...${NC}"
git commit -m "Initial commit: DataOps Agent

- Multi-agent orchestration system for data engineering workflows
- LangGraph-based orchestrator with meta-query handling
- UV package manager with modern Python tooling
- Three example workflows (simple, supervisor, iterative)
- Production-ready infrastructure foundation
- Comprehensive documentation and development guides
- Pre-commit hooks and code quality tools

Technology Stack:
- LangGraph for multi-agent orchestration
- LangChain for LLM integration
- Anthropic Claude Sonnet 4
- UV for fast package management
- Ruff, Black, mypy for code quality
- pytest for testing

Features:
✓ Intent-based workflow routing
✓ Meta-query handling (system self-awareness)
✓ Supervisor pattern with multiple agents
✓ Iterative refinement workflows
✓ State transformation between graphs
✓ Structured contracts for workflow communication
✓ LangGraph development skill included
"
echo -e "${GREEN}✓ Initial commit created${NC}"

# Create GitHub repository
echo ""
if [ "$USE_GH_CLI" = true ]; then
    echo -e "${BLUE}Creating GitHub repository with gh CLI...${NC}"

    if [[ "$VISIBILITY" == "private" ]]; then
        gh repo create "${GITHUB_USER}/${REPO_NAME}" --private --source=. --remote=origin --description="Intelligent Multi-Agent System for Data Engineering Workflows"
    else
        gh repo create "${GITHUB_USER}/${REPO_NAME}" --public --source=. --remote=origin --description="Intelligent Multi-Agent System for Data Engineering Workflows"
    fi

    echo -e "${GREEN}✓ GitHub repository created${NC}"

    # Push to GitHub
    echo ""
    echo -e "${BLUE}Pushing to GitHub...${NC}"
    git push -u origin main
    echo -e "${GREEN}✓ Pushed to GitHub${NC}"

    # Open repository
    echo ""
    read -p "Open repository in browser? (y/n) [y]: " OPEN_BROWSER
    OPEN_BROWSER=${OPEN_BROWSER:-y}

    if [[ "$OPEN_BROWSER" == "y" ]]; then
        gh repo view --web
    fi

else
    echo -e "${YELLOW}Manual GitHub repository creation required:${NC}"
    echo ""
    echo "1. Go to https://github.com/new"
    echo "2. Repository name: ${REPO_NAME}"
    echo "3. Description: Intelligent Multi-Agent System for Data Engineering Workflows"
    echo "4. Visibility: ${VISIBILITY}"
    echo "5. DO NOT initialize with README, .gitignore, or license"
    echo "6. Click 'Create repository'"
    echo ""
    read -p "Press Enter when repository is created..."

    # Add remote
    echo ""
    echo -e "${BLUE}Adding GitHub remote...${NC}"
    git remote add origin "https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
    echo -e "${GREEN}✓ Remote added${NC}"

    # Push to GitHub
    echo ""
    echo -e "${BLUE}Pushing to GitHub...${NC}"
    git push -u origin main
    echo -e "${GREEN}✓ Pushed to GitHub${NC}"

    # Open repository
    echo ""
    echo -e "${GREEN}Repository URL: https://github.com/${GITHUB_USER}/${REPO_NAME}${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Successfully pushed to GitHub!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Visit your repository: https://github.com/${GITHUB_USER}/${REPO_NAME}"
echo "2. Add repository topics: ai, data-engineering, langgraph, multi-agent, orchestration"
echo "3. Enable GitHub Actions (if needed)"
echo "4. Set up branch protection rules (recommended)"
echo "5. Add collaborators (if team project)"
echo ""
echo "To make changes:"
echo "  git add ."
echo "  git commit -m 'Your commit message'"
echo "  git push"
echo ""

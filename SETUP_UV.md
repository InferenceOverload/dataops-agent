# Setup Guide with UV Package Manager

**UV** is a fast Python package installer and resolver written in Rust. It's 10-100x faster than pip!

---

## Prerequisites

- Python 3.10 or higher
- [UV package manager](https://github.com/astral-sh/uv)
- Anthropic API key

---

## 1. Install UV

### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Alternative: Install via pip
```bash
pip install uv
```

### Verify Installation
```bash
uv --version
```

---

## 2. Clone and Setup Project

```bash
# Navigate to project
cd dataops-agent

# Create virtual environment with uv
uv venv

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

---

## 3. Install Dependencies

### Option A: Production Only
```bash
# Install core dependencies
uv pip install -e .
```

### Option B: Development Setup (Recommended)
```bash
# Install with dev tools (pytest, ruff, mypy, etc.)
uv pip install -e ".[dev]"

# Install pre-commit hooks
make pre-commit
```

### Option C: Full Installation
```bash
# Install everything (API, DB, AWS, observability)
uv pip install -e ".[all]"
```

---

## 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API key
# ANTHROPIC_API_KEY=your_key_here
```

**Get API Key:**
1. Visit https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create new key
5. Copy to `.env`

---

## 5. Verify Installation

```bash
# Run tests
make test

# Or with uv directly
uv run pytest tests/ -v
```

---

## 6. Running the Agent

### Option 1: LangGraph Dev Server (Recommended)
```bash
make dev

# Or:
uv run langgraph dev

# Opens at http://localhost:2024/docs
```

### Option 2: Python Script
```bash
make run

# Or:
uv run python main.py
```

### Option 3: Test Individual Workflows
```bash
uv run python workflows/workflow_a.py
uv run python workflows/workflow_b.py
uv run python workflows/workflow_c.py
```

---

## Development Workflow

### Running Tests
```bash
# All tests
make test

# With coverage
make test-cov

# Only unit tests
make test-unit

# Only integration tests
make test-integration
```

### Code Quality
```bash
# Lint code
make lint

# Format code
make format

# Run both
make format lint
```

### Pre-commit Hooks
```bash
# Install hooks (runs on every commit)
make pre-commit

# Run manually
uv run pre-commit run --all-files
```

---

## UV Commands Reference

### Package Management
```bash
# Install specific package
uv pip install langchain

# Install from requirements.txt
uv pip install -r requirements.txt

# Upgrade package
uv pip install --upgrade langchain

# Uninstall package
uv pip uninstall langchain

# List installed packages
uv pip list

# Show package info
uv pip show langchain
```

### Lock Files
```bash
# Generate requirements.txt from pyproject.toml
uv pip compile pyproject.toml -o requirements.txt

# Upgrade all dependencies
uv pip compile --upgrade pyproject.toml -o requirements.txt

# Sync environment to requirements.txt
uv pip sync requirements.txt
```

### Speed Comparison
```
pip install:  ~60 seconds
uv pip install:  ~2 seconds  ⚡️
```

---

## Makefile Commands

All available commands:

```bash
# Setup
make install          # Production dependencies
make install-dev      # Dev dependencies
make install-all      # All dependencies

# Testing
make test            # Run tests
make test-cov        # Tests with coverage
make test-unit       # Unit tests only
make test-integration # Integration tests only

# Code Quality
make lint            # Run linters
make format          # Format code
make pre-commit      # Install hooks

# Running
make run             # Run main script
make dev             # LangGraph dev server
make server          # FastAPI server (future)

# Docker
make docker-build    # Build image
make docker-run      # Run container

# Cleanup
make clean           # Remove artifacts
```

---

## Troubleshooting

### UV not found
```bash
# Ensure UV is in PATH
echo $PATH

# Reinstall UV
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Virtual environment issues
```bash
# Remove and recreate venv
rm -rf .venv
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Import errors
```bash
# Ensure you're in venv
which python

# Reinstall in editable mode
uv pip install -e .
```

### Pre-commit hook failures
```bash
# Update pre-commit hooks
uv run pre-commit autoupdate

# Run manually to debug
uv run pre-commit run --all-files
```

---

## Project Structure with UV

```
dataops-agent/
├── pyproject.toml          # Project metadata & dependencies
├── .python-version         # Python version (3.11)
├── .pre-commit-config.yaml # Pre-commit hooks
├── Makefile                # Development commands
├── requirements.txt        # Generated lock file (optional)
├── .venv/                  # Virtual environment (created by uv)
└── src/                    # Source code
```

---

## Why UV?

**Speed:**
- 10-100x faster than pip
- Rust-based implementation
- Parallel downloads

**Modern:**
- Works with pyproject.toml
- Compatible with pip
- Supports PEP standards

**Developer Experience:**
- Faster CI/CD pipelines
- Quicker local development
- Better dependency resolution

---

## Next Steps

After setup:

1. **Explore workflows:**
   ```bash
   uv run python workflows/workflow_a.py
   ```

2. **Start dev server:**
   ```bash
   make dev
   ```

3. **Run tests:**
   ```bash
   make test
   ```

4. **Read documentation:**
   - [Architecture](docs/architecture.md)
   - [LangGraph Skill](.claude/skills/langgraph-builder.md)

---

## Migration from pip

If you have existing pip installation:

```bash
# Activate existing venv
source venv/bin/activate

# Install uv
pip install uv

# Use uv instead
uv pip install -e ".[dev]"
```

Or start fresh:

```bash
# Remove old venv
rm -rf venv

# Create new with uv
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

---

## Resources

- [UV Documentation](https://github.com/astral-sh/uv)
- [pyproject.toml Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [DataOps Agent Docs](docs/)

---

**Happy coding with UV!** ⚡️

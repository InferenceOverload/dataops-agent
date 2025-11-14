# Setup Guide

## Quick Start

Follow these steps to get the POC running:

### 1. Navigate to Project Directory

```bash
cd poc-multi-agent-orchestrator
```

### 2. Create Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API key
# ANTHROPIC_API_KEY=your_actual_key_here
```

**To get an Anthropic API key:**
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create a new key
5. Copy and paste into `.env`

### 5. Test Individual Workflows

You can test each workflow independently:

**Test Workflow A:**
```bash
python workflows/workflow_a.py
```

**Test Workflow B:**
```bash
python workflows/workflow_b.py
```

**Test Workflow C:**
```bash
python workflows/workflow_c.py
```

### 6. Test Full Integration

```bash
python main.py
```

This will run all workflows and the orchestrator in sequence.

### 7. Interactive Testing via LangGraph Dev Server

The most powerful way to test:

```bash
# Start server
langgraph dev
```

This will:
- Start a local server at http://localhost:2024
- Open Swagger UI at http://localhost:2024/docs
- Expose all graphs for interactive testing

**Using the Swagger UI:**

1. Open http://localhost:2024/docs in your browser
2. Find `POST /runs/stream` endpoint
3. Click "Try it out"
4. Enter configuration:

**Test Workflow A:**
```json
{
  "assistant_id": "workflow_a",
  "input": {
    "input": "What is LangGraph?",
    "output": ""
  }
}
```

**Test Workflow B:**
```json
{
  "assistant_id": "workflow_b",
  "input": {
    "input": "Research and analyze cloud computing",
    "messages": [],
    "next_agent": "",
    "output": ""
  }
}
```

**Test Workflow C:**
```json
{
  "assistant_id": "workflow_c",
  "input": {
    "input": "Iteratively refine analysis",
    "iterations": 0,
    "max_iterations": 3,
    "current_result": "",
    "artifacts": [],
    "output": ""
  }
}
```

**Test Full Orchestrator:**
```json
{
  "assistant_id": "orchestrator",
  "input": {
    "user_query": "What are the benefits of multi-agent systems?"
  }
}
```

5. Click "Execute"
6. View the results

### 8. Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_workflows.py -v
pytest tests/test_orchestrator.py -v
```

## Project Structure

```
poc-multi-agent-orchestrator/
├── core/
│   ├── orchestrator.py        # Main orchestrator LangGraph
│   └── workflow_registry.py   # Workflow registry
├── workflows/
│   ├── workflow_a.py          # Simple agent
│   ├── workflow_b.py          # Supervisor pattern
│   └── workflow_c.py          # Iterative loop
├── tests/
│   ├── test_workflows.py      # Workflow unit tests
│   └── test_orchestrator.py  # Integration tests
├── docs/
│   ├── research_notes.md      # LangGraph research
│   └── architecture.md        # Architecture docs
├── main.py                    # Entry point
├── langgraph.json            # LangGraph config
├── requirements.txt          # Dependencies
├── .env                      # Environment variables (create this)
└── README.md                 # Project documentation
```

## Troubleshooting

### Import Errors

If you get import errors like `ModuleNotFoundError: No module named 'langchain'`:

```bash
# Make sure you're in the venv
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### API Key Issues

If you get authentication errors:

1. Check `.env` file exists in project root
2. Verify `ANTHROPIC_API_KEY=your_key` (no quotes, no spaces)
3. Make sure the key is valid (test at https://console.anthropic.com/)

### LangGraph Dev Server Issues

If `langgraph dev` doesn't work:

```bash
# Reinstall LangGraph CLI
pip install --upgrade "langgraph-cli[inmem]"

# Make sure langgraph.json is in project root
ls langgraph.json
```

### Test Failures

If tests fail:

1. Make sure `.env` is configured
2. Check your API key has credits
3. Try running workflows individually first
4. Check network connection (tests make real API calls)

## What This POC Proves

Running the full test suite (`python main.py` or `pytest tests/ -v`) validates:

1. ✅ **Compiled LangGraphs can be stored in registry** - Python dict works perfectly
2. ✅ **Blocking `.invoke()` works** - Orchestrator waits for workflow completion
3. ✅ **State transformation works** - Clean boundary between orchestrator and workflows
4. ✅ **Supervisor pattern as subgraph** - Multi-agent workflows work perfectly
5. ✅ **Iterative loops work** - Conditional edges enable complex patterns
6. ✅ **Structured contracts work** - Workflows communicate via predefined formats
7. ✅ **Workflows are black boxes** - Orchestrator doesn't need to know internals
8. ✅ **Pattern is extensible** - Easy to add new workflows

## Success Criteria Checklist

After running tests, verify:

- [ ] Workflow A (simple agent) executes successfully
- [ ] Workflow B (supervisor pattern) executes successfully
- [ ] Workflow C (iterative loop) executes successfully
- [ ] Orchestrator routes queries to correct workflows
- [ ] All workflows use real Claude API calls
- [ ] State transformation works at boundaries
- [ ] Blocking execution waits for completion
- [ ] Structured response contracts work
- [ ] No errors during integration testing
- [ ] Can test via Swagger UI

## Next Steps

After validating the POC:

1. **Review Documentation:**
   - [docs/research_notes.md](docs/research_notes.md) - LangGraph concepts
   - [docs/architecture.md](docs/architecture.md) - Architecture details

2. **Experiment:**
   - Add a new workflow to the registry
   - Modify intent detection logic
   - Try different max_iterations
   - Add more worker agents

3. **Production Considerations:**
   - Add streaming with `.stream()` for progress updates
   - Implement error recovery and retries
   - Add monitoring and logging
   - Use persistent storage for workflows
   - Add authentication and rate limiting

## Support

For issues:
- Check [README.md](README.md)
- Review [docs/architecture.md](docs/architecture.md)
- Check LangGraph docs: https://docs.langchain.com/oss/python/langgraph/

## License

MIT

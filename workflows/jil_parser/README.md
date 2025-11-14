# JIL Parser Workflow

## Purpose
Analyzes Autosys JIL files to identify job dependencies for migration planning.

## Architecture
Iterative analysis pattern:
1. Root agent initializes analysis
2. Loop agent discovers dependencies iteratively
3. Stores context in artifacts (S3)
4. Continues until all dependencies resolved
5. Finalizes with structured report

## Capabilities
- Parse JIL file structure
- Identify upstream dependencies (conditions)
- Identify downstream dependencies (box jobs)
- Trace multi-level dependency chains

## Usage

### Via Orchestrator
```
User: "Parse JIL dependencies for BATCH_PROCESSING job"
```

### Direct Testing
```bash
langgraph dev
# Open http://localhost:2024/docs
# Select assistant: "jil_parser"
# Input: {"file_path": "...", "current_job": "..."}
```

### Programmatic
```python
from workflows.jil_parser.workflow import JILParserWorkflow

workflow = JILParserWorkflow()
graph = workflow.get_compiled_graph()

result = graph.invoke({
    "file_path": "/path/to/file.jil",
    "current_job": "BATCH_JOB",
    "dependencies": [],
    "visited_files": [],
    "iteration_count": 0,
    "max_iterations": 10,
    "output": {}
})
```

## Configuration
Edit `config.yaml` for:
- Max iterations
- S3 bucket (if using artifact storage)
- LLM model selection

## Testing
```bash
pytest workflows/jil_parser/tests/
```

## Development Notes
- Uses iterative pattern with conditional edges
- Can extend to use S3Operations for artifact storage
- Can extend to use actual JIL file parsing
- Currently uses simulated dependency discovery for demonstration

## Example Output
```json
{
  "success": true,
  "result": {
    "target_job": "BATCH_PROCESSING_JOB",
    "dependencies": [
      {
        "job": "BATCH_PROCESSING_JOB",
        "type": "target",
        "relation": "self"
      },
      {
        "job": "UPSTREAM_JOB_1",
        "type": "upstream",
        "relation": "condition"
      },
      {
        "job": "DOWNSTREAM_JOB_1",
        "type": "downstream",
        "relation": "box_member"
      }
    ],
    "files_analyzed": ["/path/to/sample.jil"],
    "dependency_count": 3,
    "upstream_jobs": [...],
    "downstream_jobs": [...]
  },
  "metadata": {
    "workflow_name": "jil_parser",
    "iterations": 2,
    "total_dependencies": 3,
    "files_analyzed": 1
  }
}
```

"""
Workflow Templates

Pre-built templates for different workflow patterns.
"""

# Simple template - single agent workflow
SIMPLE_TEMPLATE = {
    "__init__.py": "",

    "workflow.py": '''"""
{{workflow_name}} Workflow

{{description}}
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
import os
from dotenv import load_dotenv
from core.base_workflow import BaseWorkflow, WorkflowMetadata, WorkflowInputParameter

# Load environment variables
load_dotenv()


class {{WorkflowName}}State(TypedDict):
    """State for {{workflow_name}} workflow"""
    session_id: str
    workflow_name: str
    input: str
    output: str
    artifacts: list[str]


class {{WorkflowName}}Workflow(BaseWorkflow):
    """{{description}}"""

    def __init__(self, config: dict = None):
        """
        Initialize {{workflow_name}} workflow.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.7
        )

    def get_metadata(self) -> WorkflowMetadata:
        """Return workflow metadata for registry discovery"""
        return WorkflowMetadata(
            name="{{workflow_name}}",
            description="{{description}}",
            capabilities=[
                "TODO: Add capability 1",
                "TODO: Add capability 2",
                "TODO: Add capability 3"
            ],
            example_queries=[
                "TODO: Add example query 1",
                "TODO: Add example query 2"
            ],
            category="{{category}}",
            version="1.0.0",
            author="{{author}}",
            required_inputs=[
                WorkflowInputParameter(
                    name="input",
                    description="User input or query",
                    type="string",
                    required=True,
                    example="Example input",
                    prompt="What would you like me to process?"
                )
            ]
        )

    def get_compiled_graph(self):
        """Build and return compiled graph"""

        def process_node(state: {{WorkflowName}}State) -> dict:
            """
            Main processing node.

            TODO: Implement your business logic here.

            Args:
                state: Current workflow state

            Returns:
                State updates
            """
            user_input = state["input"]

            # Call LLM
            prompt = f"""Process this request: {user_input}

TODO: Customize this prompt for your use case.
"""
            response = self.llm.invoke(prompt)

            return {
                "output": response.content
            }

        # Build graph
        graph = StateGraph({{WorkflowName}}State)

        # Add nodes
        graph.add_node("process", process_node)

        # Add edges
        graph.add_edge(START, "process")
        graph.add_edge("process", END)

        return graph.compile()


# For testing
if __name__ == "__main__":
    print("Testing {{WorkflowName}} Workflow")
    print("-" * 60)

    workflow = {{WorkflowName}}Workflow()
    graph = workflow.get_compiled_graph()

    test_input = {
        "session_id": "test",
        "workflow_name": "{{workflow_name}}",
        "input": "test input",
        "output": "",
        "artifacts": []
    }

    print(f"Input: {test_input['input']}")
    print()

    result = graph.invoke(test_input)

    print("Result:")
    print(f"  Output: {result.get('output', 'N/A')}")
    print("-" * 60)
    print("✓ Test completed")
''',

    "config.yaml": '''# {{WorkflowName}} Workflow Configuration

# Workflow control
workflow:
  enabled: true  # Set to false to disable this workflow

# LLM settings
llm:
  model: "claude-sonnet-4-20250514"
  temperature: 0.7
  max_tokens: 4096

# TODO: Add your workflow-specific configuration here
''',

    "tests/__init__.py": "",

    "tests/test_workflow.py": '''"""
Tests for {{workflow_name}} workflow
"""

import pytest
from workflows.{{workflow_name}}.workflow import {{WorkflowName}}Workflow


class Test{{WorkflowName}}Workflow:
    """Test suite for {{WorkflowName}} workflow"""

    def setup_method(self):
        """Setup test fixtures"""
        self.workflow = {{WorkflowName}}Workflow()
        self.graph = self.workflow.get_compiled_graph()

    def test_metadata(self):
        """Test workflow metadata"""
        metadata = self.workflow.get_metadata()
        assert metadata.name == "{{workflow_name}}"
        assert metadata.category == "{{category}}"
        assert len(metadata.capabilities) > 0
        assert len(metadata.example_queries) > 0

    def test_basic_execution(self):
        """Test basic workflow execution"""
        test_input = {
            "session_id": "test",
            "workflow_name": "{{workflow_name}}",
            "input": "test query",
            "output": "",
            "artifacts": []
        }

        result = self.graph.invoke(test_input)

        assert "output" in result
        assert result["output"] != ""

    def test_graph_compiles(self):
        """Test that graph compiles successfully"""
        assert self.graph is not None

    # TODO: Add more tests specific to your workflow
''',

    "README.md": '''# {{WorkflowName}} Workflow

## Overview

{{description}}

**Category**: {{category}}
**Template**: {{template}}

## Quick Start

### Test the workflow
```bash
dataops-workflow test {{workflow_name}}
```

### Validate the workflow
```bash
dataops-workflow validate {{workflow_name}}
```

### Use in production
```python
from core.workflow_registry import WORKFLOW_REGISTRY

workflow = WORKFLOW_REGISTRY.get_workflow("{{workflow_name}}")
result = workflow.invoke({
    "session_id": "sess_123",
    "workflow_name": "{{workflow_name}}",
    "input": "your input here",
    "output": "",
    "artifacts": []
})
```

## Development

### Customize the workflow

1. Edit `workflow.py` and update the `process_node` function
2. Update metadata in `get_metadata()`:
   - Add meaningful capabilities
   - Add example queries
   - Define required inputs
3. Add tests in `tests/test_workflow.py`
4. Update configuration in `config.yaml`

### Enable/Disable

```bash
# Disable workflow
dataops-workflow toggle {{workflow_name}} --disable

# Enable workflow
dataops-workflow toggle {{workflow_name}} --enable
```

## Configuration

Edit `config.yaml` to configure:
- LLM model and parameters
- Workflow-specific settings
- Enable/disable flag

## Testing

```bash
# Run tests
pytest workflows/{{workflow_name}}/tests/

# Test with CLI
dataops-workflow test {{workflow_name}} --input '{"input": "test"}'
```

## Next Steps

- [ ] Customize the process_node logic
- [ ] Update metadata (capabilities, examples)
- [ ] Add error handling
- [ ] Write comprehensive tests
- [ ] Document any special configuration

---

Generated by `dataops-workflow create`
'''
}


# Iterative template - loop-based workflow
ITERATIVE_TEMPLATE = {
    "__init__.py": "",

    "workflow.py": '''"""
{{workflow_name}} Workflow

{{description}}

Architecture: Iterative analysis pattern
- Root agent initializes analysis
- Loop agent iteratively processes
- Conditional logic determines completion
"""

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
import os
from dotenv import load_dotenv
from core.base_workflow import BaseWorkflow, WorkflowMetadata, WorkflowInputParameter

load_dotenv()


class {{WorkflowName}}State(TypedDict):
    """State for {{workflow_name}} workflow"""
    session_id: str
    workflow_name: str
    input: str
    iteration_count: int
    max_iterations: int
    results: List[Dict[str, Any]]
    output: Dict[str, Any]


class {{WorkflowName}}Workflow(BaseWorkflow):
    """{{description}}"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0
        )

    def get_metadata(self) -> WorkflowMetadata:
        return WorkflowMetadata(
            name="{{workflow_name}}",
            description="{{description}}",
            capabilities=[
                "Iterative analysis",
                "Progressive refinement",
                "TODO: Add more capabilities"
            ],
            example_queries=[
                "TODO: Add example query 1",
                "TODO: Add example query 2"
            ],
            category="{{category}}",
            version="1.0.0",
            author="{{author}}",
            required_inputs=[
                WorkflowInputParameter(
                    name="input",
                    description="Input to analyze iteratively",
                    type="string",
                    required=True
                ),
                WorkflowInputParameter(
                    name="max_iterations",
                    description="Maximum iterations",
                    type="integer",
                    required=False,
                    default=3
                )
            ]
        )

    def get_compiled_graph(self):
        """Build iterative analysis graph"""

        def initialize(state: {{WorkflowName}}State) -> Dict:
            """Initialize analysis"""
            # TODO: Add initialization logic
            return {
                "iteration_count": 0,
                "results": []
            }

        def iterate(state: {{WorkflowName}}State) -> Dict:
            """Iterative processing"""
            # TODO: Implement iteration logic

            prompt = f"""Iteration {state['iteration_count'] + 1} of {state['max_iterations']}

Input: {state['input']}
Previous results: {state['results']}

TODO: Customize iteration logic
"""
            response = self.llm.invoke(prompt)

            new_result = {
                "iteration": state["iteration_count"] + 1,
                "result": response.content
            }

            return {
                "iteration_count": state["iteration_count"] + 1,
                "results": state["results"] + [new_result]
            }

        def check_completion(state: {{WorkflowName}}State) -> str:
            """Check if iterations should continue"""
            if state["iteration_count"] >= state["max_iterations"]:
                return "finalize"

            # TODO: Add custom completion logic
            return "continue"

        def finalize(state: {{WorkflowName}}State) -> Dict:
            """Compile final results"""
            output = {
                "success": True,
                "iterations": state["iteration_count"],
                "results": state["results"]
            }
            return {"output": output}

        # Build graph
        graph = StateGraph({{WorkflowName}}State)

        graph.add_node("initialize", initialize)
        graph.add_node("iterate", iterate)
        graph.add_node("finalize", finalize)

        graph.add_edge(START, "initialize")
        graph.add_edge("initialize", "iterate")
        graph.add_conditional_edges(
            "iterate",
            check_completion,
            {
                "continue": "iterate",
                "finalize": "finalize"
            }
        )
        graph.add_edge("finalize", END)

        return graph.compile()


if __name__ == "__main__":
    workflow = {{WorkflowName}}Workflow()
    graph = workflow.get_compiled_graph()

    result = graph.invoke({
        "session_id": "test",
        "workflow_name": "{{workflow_name}}",
        "input": "test input",
        "iteration_count": 0,
        "max_iterations": 3,
        "results": [],
        "output": {}
    })

    print("Result:", result)
''',

    "config.yaml": '''# {{WorkflowName}} Workflow Configuration

workflow:
  enabled: true

# Iteration settings
iteration:
  default_max_iterations: 3
  timeout_per_iteration: 30

llm:
  model: "claude-sonnet-4-20250514"
  temperature: 0
''',

    "tests/__init__.py": "",

    "tests/test_workflow.py": '''"""Tests for {{workflow_name}} workflow"""

import pytest
from workflows.{{workflow_name}}.workflow import {{WorkflowName}}Workflow


class Test{{WorkflowName}}Workflow:
    def setup_method(self):
        self.workflow = {{WorkflowName}}Workflow()
        self.graph = self.workflow.get_compiled_graph()

    def test_metadata(self):
        metadata = self.workflow.get_metadata()
        assert metadata.name == "{{workflow_name}}"

    def test_iterative_execution(self):
        result = self.graph.invoke({
            "session_id": "test",
            "workflow_name": "{{workflow_name}}",
            "input": "test",
            "iteration_count": 0,
            "max_iterations": 2,
            "results": [],
            "output": {}
        })

        assert "output" in result
        assert result["iteration_count"] == 2
''',

    "README.md": '''# {{WorkflowName}} Workflow

Iterative analysis workflow.

See `workflow.py` for implementation details.
'''
}


# Template registry
TEMPLATES = {
    "simple": SIMPLE_TEMPLATE,
    "iterative": ITERATIVE_TEMPLATE,
    # TODO: Add supervisor, sequential, parallel templates
}


def get_template(template_name: str) -> dict:
    """
    Get template files by name.

    Args:
        template_name: Name of template (simple, iterative, etc.)

    Returns:
        Dictionary of filename -> content
    """
    if template_name not in TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}. Available: {list(TEMPLATES.keys())}")

    return TEMPLATES[template_name]

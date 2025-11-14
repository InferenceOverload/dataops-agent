"""
Workflow B - Supervisor Pattern

Purpose: Prove multi-agent workflows work as subgraphs
Pattern: Supervisor orchestrates 2 worker agents

Architecture:
    Supervisor Agent (decides which worker to call)
        ↓
    Worker 1 (Research specialist)
    Worker 2 (Analysis specialist)
        ↓
    Loop back to Supervisor until FINISH
"""

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from core.base_workflow import BaseWorkflow, WorkflowMetadata
from infrastructure.llm.llm_factory import create_llm

# Load environment variables
load_dotenv()

# State Schema
class WorkflowBState(TypedDict):
    """State for Workflow B - Supervisor Pattern"""
    input: str              # Original query
    messages: list[str]     # Message history for coordination
    next_agent: str         # Next agent to invoke
    output: str             # Final compiled result


class SupervisorWorkflow(BaseWorkflow):
    """Multi-agent supervisor workflow for complex tasks requiring coordination"""

    def __init__(self):
        """Initialize supervisor workflow"""
        self.llm = create_llm()

    def get_metadata(self) -> WorkflowMetadata:
        """Return workflow metadata for registry discovery"""
        return WorkflowMetadata(
            name="supervisor",
            description="Coordinates multiple specialist agents for complex research and analysis tasks",
            capabilities=[
                "Multi-agent coordination",
                "Research information gathering",
                "Analysis and synthesis",
                "Complex task decomposition",
                "Specialist agent orchestration"
            ],
            example_queries=[
                "Research and analyze the benefits of multi-agent systems",
                "Investigate cloud computing and provide detailed analysis",
                "Study data engineering best practices and synthesize findings"
            ],
            category="analysis",
            version="1.0.0"
        )

    def get_compiled_graph(self):
        """Build and return compiled supervisor graph"""

        def supervisor_node(state: WorkflowBState) -> dict:
            """
            Supervisor decides which agent to call next or if we're done.

            Args:
                state: Current workflow state

            Returns:
                dict: State update with next_agent decision
            """
            messages = state["messages"]
            user_input = state["input"]

            # Build context for supervisor
            if not messages:
                context = f"Initial task: {user_input}"
            else:
                context = f"Task: {user_input}\n\nProgress so far:\n" + "\n".join(messages)

            # Supervisor decides next step
            prompt = f"""You are a supervisor coordinating two specialist agents:
- worker1: Research specialist (gathers information)
- worker2: Analysis specialist (analyzes and synthesizes)

{context}

Decide which agent should act next, or if the task is complete.
Respond with ONLY one of: worker1, worker2, or FINISH

Your decision:"""

            response = self.llm.invoke(prompt)
            decision = response.content.strip().lower()

            # Validate decision
            if decision not in ["worker1", "worker2", "finish"]:
                # Default to finish if unclear
                decision = "finish"

            # Add supervisor's decision to messages
            messages.append(f"Supervisor: Routing to {decision}")

            return {
                "next_agent": decision,
                "messages": messages
            }


        def worker1_node(state: WorkflowBState) -> dict:
            """
            Worker 1 - Research specialist.
            Gathers information and context.

            Args:
                state: Current workflow state

            Returns:
                dict: State update with research results
            """
            user_input = state["input"]
            messages = state["messages"]

            prompt = f"""You are Worker 1, a research specialist.

Task: {user_input}

Your role: Gather key information, facts, and context about this task.
Provide a concise research summary."""

            response = self.llm.invoke(prompt)
            result = response.content if hasattr(response, 'content') else str(response)

            # Add to messages
            messages.append(f"Worker1 (Research): {result}")

            return {
                "messages": messages
            }

        def worker2_node(state: WorkflowBState) -> dict:
            """
            Worker 2 - Analysis specialist.
            Analyzes information and synthesizes conclusions.

            Args:
                state: Current workflow state

            Returns:
                dict: State update with analysis results
            """
            user_input = state["input"]
            messages = state["messages"]

            # Get context from previous work
            context = "\n".join([msg for msg in messages if msg.startswith("Worker1")])

            prompt = f"""You are Worker 2, an analysis specialist.

Task: {user_input}

Previous research:
{context}

Your role: Analyze the research and provide insights, conclusions, or recommendations.
Provide a concise analysis."""

            response = self.llm.invoke(prompt)
            result = response.content if hasattr(response, 'content') else str(response)

            # Add to messages
            messages.append(f"Worker2 (Analysis): {result}")

            return {
                "messages": messages
            }

        def finalize_node(state: WorkflowBState) -> dict:
            """
            Finalize the workflow - compile all messages into final output.

            Args:
                state: Current workflow state

            Returns:
                dict: State update with final output
            """
            messages = state["messages"]

            # Compile final output from messages
            output_parts = []
            for msg in messages:
                if msg.startswith("Worker1") or msg.startswith("Worker2"):
                    output_parts.append(msg)

            final_output = "\n\n".join(output_parts)

            return {
                "output": final_output if final_output else "Task completed with no specific output."
            }

        def route_supervisor(state: WorkflowBState) -> Literal["worker1", "worker2", "finalize"]:
            """
            Conditional edge routing function.
            Determines which node to go to next based on supervisor's decision.

            Args:
                state: Current workflow state

            Returns:
                str: Next node name
            """
            next_agent = state["next_agent"]

            if next_agent == "finish":
                return "finalize"
            elif next_agent == "worker1":
                return "worker1"
            elif next_agent == "worker2":
                return "worker2"
            else:
                # Default to finalize
                return "finalize"

        # Build Graph
        workflow_builder = StateGraph(WorkflowBState)

        # Add nodes
        workflow_builder.add_node("supervisor", supervisor_node)
        workflow_builder.add_node("worker1", worker1_node)
        workflow_builder.add_node("worker2", worker2_node)
        workflow_builder.add_node("finalize", finalize_node)

        # Add edges
        workflow_builder.add_edge(START, "supervisor")

        # Conditional edges from supervisor
        workflow_builder.add_conditional_edges(
            "supervisor",
            route_supervisor,
            {
                "worker1": "worker1",
                "worker2": "worker2",
                "finalize": "finalize"
            }
        )

        # Workers loop back to supervisor
        workflow_builder.add_edge("worker1", "supervisor")
        workflow_builder.add_edge("worker2", "supervisor")

        # Finalize goes to END
        workflow_builder.add_edge("finalize", END)

        # Compile and return
        return workflow_builder.compile()


# For backwards compatibility - create instance and expose compiled graph
_workflow_instance = SupervisorWorkflow()
workflow_graph = _workflow_instance.get_compiled_graph()


# For testing directly
if __name__ == "__main__":
    # Test the workflow
    print("Testing Workflow B - Supervisor Pattern")
    print("-" * 50)

    test_input = {
        "input": "Research and analyze the benefits of multi-agent systems",
        "messages": [],
        "next_agent": "",
        "output": ""
    }

    print(f"Input: {test_input['input']}")
    print("Processing with supervisor pattern...")
    print()

    result = workflow_graph.invoke(test_input)

    print("Message History:")
    for i, msg in enumerate(result['messages'], 1):
        print(f"{i}. {msg}")

    print()
    print("Final Output:")
    print(result['output'])
    print("-" * 50)
    print("✓ Workflow B completed successfully")

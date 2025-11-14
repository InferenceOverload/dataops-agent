"""
Central Tool Registry

Provides easy access to all infrastructure tools for workflows.

Usage Examples:

1. Import all tools at once:
    from infrastructure.tools import get_all_tools
    tools = get_all_tools()

2. Import specific tool categories:
    from infrastructure.tools import get_s3_tools, get_dynamodb_tools
    s3_tools = get_s3_tools()
    dynamodb_tools = get_dynamodb_tools()

3. Import individual tools:
    from infrastructure.tools.s3_tools import S3ReadTool, S3WriteTool
    from infrastructure.tools.dynamodb_tools import DynamoDBPutTool

4. Use with LangChain agents:
    from langchain.agents import initialize_agent, AgentType
    from langchain_anthropic import ChatAnthropic
    from infrastructure.tools import get_all_tools

    llm = ChatAnthropic(model="claude-sonnet-4-20250514")
    tools = get_all_tools()
    agent = initialize_agent(tools, llm, agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION)
"""

from langchain.tools import BaseTool
from infrastructure.tools.s3_tools import (
    S3ReadTool,
    S3WriteTool,
    S3ListTool,
    S3ExistsTool,
    get_s3_tools
)
from infrastructure.tools.dynamodb_tools import (
    DynamoDBPutTool,
    DynamoDBGetTool,
    DynamoDBQueryTool,
    DynamoDBScanTool,
    get_dynamodb_tools
)


# ============================================================================
# Tool Collections
# ============================================================================

def get_all_tools() -> list[BaseTool]:
    """
    Get all infrastructure tools.

    Returns:
        List of all S3 and DynamoDB tools
    """
    return get_s3_tools() + get_dynamodb_tools()


def get_storage_tools() -> list[BaseTool]:
    """
    Get all storage-related tools (S3, DynamoDB).

    Alias for get_all_tools for semantic clarity.

    Returns:
        List of all storage tools
    """
    return get_all_tools()


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # S3 Tools
    "S3ReadTool",
    "S3WriteTool",
    "S3ListTool",
    "S3ExistsTool",
    "get_s3_tools",
    # DynamoDB Tools
    "DynamoDBPutTool",
    "DynamoDBGetTool",
    "DynamoDBQueryTool",
    "DynamoDBScanTool",
    "get_dynamodb_tools",
    # Convenience functions
    "get_all_tools",
    "get_storage_tools"
]

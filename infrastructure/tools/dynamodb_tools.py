"""
LangChain Tools for DynamoDB Operations

Provides LangChain tool wrappers for common DynamoDB operations.
These tools can be used directly with LangChain agents and workflows.

Usage:
    from infrastructure.tools import get_dynamodb_tools

    # Get all DynamoDB tools
    tools = get_dynamodb_tools()

    # Or get specific tools
    from infrastructure.tools.dynamodb_tools import DynamoDBPutTool, DynamoDBGetTool

    put_tool = DynamoDBPutTool()
    result = put_tool._run(
        key={"job_id": "BATCH_001"},
        item={"job_id": "BATCH_001", "status": "completed"},
        table="jobs"
    )
"""

import boto3
import json
from typing import Optional, Type, Any, Dict
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from infrastructure.config import get_aws_config


# ============================================================================
# DynamoDB Put Tool
# ============================================================================

class DynamoDBPutInput(BaseModel):
    """Input schema for DynamoDB put tool"""
    item: str = Field(..., description="Item to put in DynamoDB as JSON string")
    table: Optional[str] = Field(None, description="DynamoDB table name (optional if default configured)")


class DynamoDBPutTool(BaseTool):
    """
    Tool to put (create/update) an item in DynamoDB.

    Stores or updates an item in DynamoDB.
    Useful for tracking workflow state, storing analysis results, etc.
    """
    name: str = "dynamodb_put_item"
    description: str = (
        "Put (create or update) an item in DynamoDB. "
        "Input should be the item as JSON string and optionally table name. "
        "Returns success message or error. "
        "Example: item='{\"job_id\": \"BATCH_001\", \"status\": \"completed\"}', table='jobs'"
    )
    args_schema: Type[BaseModel] = DynamoDBPutInput

    def _run(self, item: str, table: Optional[str] = None) -> str:
        """
        Put item in DynamoDB.

        Args:
            item: Item as JSON string
            table: DynamoDB table name (optional)

        Returns:
            Success message
        """
        try:
            config = get_aws_config()
            table_name = config.get_dynamodb_table(table)

            # Parse item JSON
            try:
                item_dict = json.loads(item)
            except json.JSONDecodeError:
                return f"Error: Invalid JSON format for item"

            # Create DynamoDB resource
            dynamodb = boto3.resource('dynamodb', **config.get_boto3_session_kwargs())
            table_resource = dynamodb.Table(table_name)

            # Put item
            table_resource.put_item(Item=item_dict)

            return f"Successfully put item in table '{table_name}'"

        except Exception as e:
            return f"Error putting item to DynamoDB: {str(e)}"

    async def _arun(self, item: str, table: Optional[str] = None) -> str:
        """Async version (falls back to sync for now)"""
        return self._run(item, table)


# ============================================================================
# DynamoDB Get Tool
# ============================================================================

class DynamoDBGetInput(BaseModel):
    """Input schema for DynamoDB get tool"""
    key: str = Field(..., description="Primary key as JSON string (e.g., '{\"job_id\": \"BATCH_001\"}')")
    table: Optional[str] = Field(None, description="DynamoDB table name (optional if default configured)")


class DynamoDBGetTool(BaseTool):
    """
    Tool to get an item from DynamoDB by primary key.

    Retrieves a single item from DynamoDB.
    Useful for looking up job status, retrieving stored analysis, etc.
    """
    name: str = "dynamodb_get_item"
    description: str = (
        "Get an item from DynamoDB by primary key. "
        "Input should be the key as JSON string and optionally table name. "
        "Returns the item as JSON or 'not found' message. "
        "Example: key='{\"job_id\": \"BATCH_001\"}', table='jobs'"
    )
    args_schema: Type[BaseModel] = DynamoDBGetInput

    def _run(self, key: str, table: Optional[str] = None) -> str:
        """
        Get item from DynamoDB.

        Args:
            key: Primary key as JSON string
            table: DynamoDB table name (optional)

        Returns:
            Item as JSON string or not found message
        """
        try:
            config = get_aws_config()
            table_name = config.get_dynamodb_table(table)

            # Parse key JSON
            try:
                key_dict = json.loads(key)
            except json.JSONDecodeError:
                return f"Error: Invalid JSON format for key"

            # Create DynamoDB resource
            dynamodb = boto3.resource('dynamodb', **config.get_boto3_session_kwargs())
            table_resource = dynamodb.Table(table_name)

            # Get item
            response = table_resource.get_item(Key=key_dict)

            if 'Item' not in response:
                return f"Item not found with key: {key}"

            return json.dumps(response['Item'], indent=2, default=str)

        except Exception as e:
            return f"Error getting item from DynamoDB: {str(e)}"

    async def _arun(self, key: str, table: Optional[str] = None) -> str:
        """Async version (falls back to sync for now)"""
        return self._run(key, table)


# ============================================================================
# DynamoDB Query Tool
# ============================================================================

class DynamoDBQueryInput(BaseModel):
    """Input schema for DynamoDB query tool"""
    key_condition: str = Field(
        ...,
        description="Key condition as string (e.g., 'job_id = BATCH_001' or 'status = completed')"
    )
    table: Optional[str] = Field(None, description="DynamoDB table name (optional if default configured)")
    limit: int = Field(10, description="Maximum number of items to return")


class DynamoDBQueryTool(BaseTool):
    """
    Tool to query DynamoDB with a key condition.

    Queries items from DynamoDB using partition key and optional sort key.
    Useful for finding related items, filtering by status, etc.
    """
    name: str = "dynamodb_query"
    description: str = (
        "Query DynamoDB with a key condition. "
        "Input should be the key condition expression, optionally table name and limit. "
        "Returns list of matching items as JSON. "
        "Example: key_condition='job_id = BATCH_001', table='jobs', limit=10"
    )
    args_schema: Type[BaseModel] = DynamoDBQueryInput

    def _run(self, key_condition: str, table: Optional[str] = None, limit: int = 10) -> str:
        """
        Query DynamoDB.

        Args:
            key_condition: Key condition expression
            table: DynamoDB table name (optional)
            limit: Maximum number of items

        Returns:
            Items as JSON string
        """
        try:
            config = get_aws_config()
            table_name = config.get_dynamodb_table(table)

            # Parse key condition (simple format: "key = value")
            parts = key_condition.split('=')
            if len(parts) != 2:
                return "Error: Key condition must be in format 'key = value'"

            key_name = parts[0].strip()
            key_value = parts[1].strip()

            # Create DynamoDB resource
            dynamodb = boto3.resource('dynamodb', **config.get_boto3_session_kwargs())
            table_resource = dynamodb.Table(table_name)

            # Query with key condition
            from boto3.dynamodb.conditions import Key

            response = table_resource.query(
                KeyConditionExpression=Key(key_name).eq(key_value),
                Limit=limit
            )

            items = response.get('Items', [])

            if not items:
                return f"No items found matching condition: {key_condition}"

            result = {
                "count": len(items),
                "items": items
            }

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return f"Error querying DynamoDB: {str(e)}"

    async def _arun(self, key_condition: str, table: Optional[str] = None, limit: int = 10) -> str:
        """Async version (falls back to sync for now)"""
        return self._run(key_condition, table, limit)


# ============================================================================
# DynamoDB Scan Tool (for small tables)
# ============================================================================

class DynamoDBScanInput(BaseModel):
    """Input schema for DynamoDB scan tool"""
    table: Optional[str] = Field(None, description="DynamoDB table name (optional if default configured)")
    limit: int = Field(10, description="Maximum number of items to return")
    filter_expression: Optional[str] = Field(
        None,
        description="Optional filter expression (e.g., 'status = completed')"
    )


class DynamoDBScanTool(BaseTool):
    """
    Tool to scan DynamoDB table (use sparingly!).

    Scans entire table or filtered subset.
    Warning: Expensive operation, use only for small tables or with filters.
    """
    name: str = "dynamodb_scan"
    description: str = (
        "Scan DynamoDB table (WARNING: expensive operation!). "
        "Input should be optionally table name, limit, and filter expression. "
        "Returns list of items as JSON. "
        "Example: table='jobs', limit=20, filter_expression='status = completed'"
    )
    args_schema: Type[BaseModel] = DynamoDBScanInput

    def _run(
        self,
        table: Optional[str] = None,
        limit: int = 10,
        filter_expression: Optional[str] = None
    ) -> str:
        """
        Scan DynamoDB table.

        Args:
            table: DynamoDB table name (optional)
            limit: Maximum number of items
            filter_expression: Optional filter

        Returns:
            Items as JSON string
        """
        try:
            config = get_aws_config()
            table_name = config.get_dynamodb_table(table)

            # Create DynamoDB resource
            dynamodb = boto3.resource('dynamodb', **config.get_boto3_session_kwargs())
            table_resource = dynamodb.Table(table_name)

            # Build scan parameters
            scan_kwargs = {'Limit': limit}

            # Add filter if provided
            if filter_expression:
                parts = filter_expression.split('=')
                if len(parts) == 2:
                    from boto3.dynamodb.conditions import Attr
                    attr_name = parts[0].strip()
                    attr_value = parts[1].strip()
                    scan_kwargs['FilterExpression'] = Attr(attr_name).eq(attr_value)

            # Scan table
            response = table_resource.scan(**scan_kwargs)

            items = response.get('Items', [])

            if not items:
                return "No items found"

            result = {
                "count": len(items),
                "items": items,
                "warning": "Scan is expensive - consider using query instead for large tables"
            }

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return f"Error scanning DynamoDB: {str(e)}"

    async def _arun(
        self,
        table: Optional[str] = None,
        limit: int = 10,
        filter_expression: Optional[str] = None
    ) -> str:
        """Async version (falls back to sync for now)"""
        return self._run(table, limit, filter_expression)


# ============================================================================
# Tool Collection
# ============================================================================

def get_dynamodb_tools() -> list[BaseTool]:
    """
    Get all DynamoDB tools for use with LangChain agents.

    Returns:
        List of DynamoDB tools
    """
    return [
        DynamoDBPutTool(),
        DynamoDBGetTool(),
        DynamoDBQueryTool(),
        DynamoDBScanTool()
    ]

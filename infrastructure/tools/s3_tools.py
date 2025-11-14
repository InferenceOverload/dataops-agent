"""
LangChain Tools for S3 Operations

Provides LangChain tool wrappers for common S3 operations.
These tools can be used directly with LangChain agents and workflows.

Usage:
    from infrastructure.tools import get_s3_tools

    # Get all S3 tools
    tools = get_s3_tools()

    # Or get specific tools
    from infrastructure.tools.s3_tools import S3ReadTool, S3WriteTool

    read_tool = S3ReadTool()
    content = read_tool._run(bucket="my-bucket", key="path/to/file.txt")
"""

import boto3
from typing import Optional, Type, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from infrastructure.config import get_aws_config


# ============================================================================
# S3 Read Tool
# ============================================================================

class S3ReadInput(BaseModel):
    """Input schema for S3 read tool"""
    key: str = Field(..., description="S3 object key (path) to read")
    bucket: Optional[str] = Field(None, description="S3 bucket name (optional if default configured)")


class S3ReadTool(BaseTool):
    """
    Tool to read text content from S3.

    Reads a file from S3 and returns its content as a string.
    Useful for reading JIL files, configuration files, etc.
    """
    name: str = "s3_read_file"
    description: str = (
        "Read text content from an S3 file. "
        "Input should be the S3 key (path) and optionally bucket name. "
        "Returns the file content as text. "
        "Example: key='jobs/batch_job.jil', bucket='my-data-bucket'"
    )
    args_schema: Type[BaseModel] = S3ReadInput

    def _run(self, key: str, bucket: Optional[str] = None) -> str:
        """
        Read file from S3.

        Args:
            key: S3 object key
            bucket: S3 bucket name (optional)

        Returns:
            File content as string
        """
        try:
            config = get_aws_config()
            bucket_name = config.get_s3_bucket(bucket)

            # Create S3 client
            s3_client = boto3.client('s3', **config.get_boto3_session_kwargs())

            # Read object
            response = s3_client.get_object(Bucket=bucket_name, Key=key)
            content = response['Body'].read().decode('utf-8')

            return content

        except Exception as e:
            return f"Error reading from S3: {str(e)}"

    async def _arun(self, key: str, bucket: Optional[str] = None) -> str:
        """Async version (falls back to sync for now)"""
        return self._run(key, bucket)


# ============================================================================
# S3 Write Tool
# ============================================================================

class S3WriteInput(BaseModel):
    """Input schema for S3 write tool"""
    key: str = Field(..., description="S3 object key (path) to write to")
    content: str = Field(..., description="Content to write to S3")
    bucket: Optional[str] = Field(None, description="S3 bucket name (optional if default configured)")


class S3WriteTool(BaseTool):
    """
    Tool to write text content to S3.

    Writes content to an S3 file.
    Useful for storing analysis results, generated reports, etc.
    """
    name: str = "s3_write_file"
    description: str = (
        "Write text content to an S3 file. "
        "Input should be the S3 key (path), content, and optionally bucket name. "
        "Returns success message or error. "
        "Example: key='output/result.json', content='{...}', bucket='my-data-bucket'"
    )
    args_schema: Type[BaseModel] = S3WriteInput

    def _run(self, key: str, content: str, bucket: Optional[str] = None) -> str:
        """
        Write file to S3.

        Args:
            key: S3 object key
            content: Content to write
            bucket: S3 bucket name (optional)

        Returns:
            Success message
        """
        try:
            config = get_aws_config()
            bucket_name = config.get_s3_bucket(bucket)

            # Create S3 client
            s3_client = boto3.client('s3', **config.get_boto3_session_kwargs())

            # Write object
            s3_client.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=content.encode('utf-8')
            )

            return f"Successfully wrote to s3://{bucket_name}/{key}"

        except Exception as e:
            return f"Error writing to S3: {str(e)}"

    async def _arun(self, key: str, content: str, bucket: Optional[str] = None) -> str:
        """Async version (falls back to sync for now)"""
        return self._run(key, content, bucket)


# ============================================================================
# S3 List Tool
# ============================================================================

class S3ListInput(BaseModel):
    """Input schema for S3 list tool"""
    prefix: str = Field(..., description="S3 prefix (folder path) to list")
    bucket: Optional[str] = Field(None, description="S3 bucket name (optional if default configured)")
    max_keys: int = Field(100, description="Maximum number of keys to return")


class S3ListTool(BaseTool):
    """
    Tool to list objects in S3 with a given prefix.

    Lists files in an S3 "folder" (prefix).
    Useful for discovering available files, finding JIL files, etc.
    """
    name: str = "s3_list_objects"
    description: str = (
        "List objects in S3 with a given prefix (folder path). "
        "Input should be the prefix and optionally bucket name and max_keys. "
        "Returns list of object keys. "
        "Example: prefix='jobs/autosys/', bucket='my-data-bucket', max_keys=50"
    )
    args_schema: Type[BaseModel] = S3ListInput

    def _run(self, prefix: str, bucket: Optional[str] = None, max_keys: int = 100) -> str:
        """
        List objects in S3.

        Args:
            prefix: S3 prefix to filter by
            bucket: S3 bucket name (optional)
            max_keys: Maximum number of keys to return

        Returns:
            Formatted list of object keys
        """
        try:
            config = get_aws_config()
            bucket_name = config.get_s3_bucket(bucket)

            # Create S3 client
            s3_client = boto3.client('s3', **config.get_boto3_session_kwargs())

            # List objects
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            if 'Contents' not in response:
                return f"No objects found with prefix: {prefix}"

            keys = [obj['Key'] for obj in response['Contents']]

            result = f"Found {len(keys)} objects in s3://{bucket_name}/{prefix}\n\n"
            result += "\n".join(f"  - {key}" for key in keys)

            return result

        except Exception as e:
            return f"Error listing S3 objects: {str(e)}"

    async def _arun(self, prefix: str, bucket: Optional[str] = None, max_keys: int = 100) -> str:
        """Async version (falls back to sync for now)"""
        return self._run(prefix, bucket, max_keys)


# ============================================================================
# S3 Check Exists Tool
# ============================================================================

class S3ExistsInput(BaseModel):
    """Input schema for S3 exists check tool"""
    key: str = Field(..., description="S3 object key (path) to check")
    bucket: Optional[str] = Field(None, description="S3 bucket name (optional if default configured)")


class S3ExistsTool(BaseTool):
    """
    Tool to check if an S3 object exists.

    Checks if a file exists in S3 without reading its contents.
    Useful for validation before processing.
    """
    name: str = "s3_check_exists"
    description: str = (
        "Check if an S3 object exists. "
        "Input should be the S3 key (path) and optionally bucket name. "
        "Returns 'exists' or 'does not exist'. "
        "Example: key='jobs/batch_job.jil', bucket='my-data-bucket'"
    )
    args_schema: Type[BaseModel] = S3ExistsInput

    def _run(self, key: str, bucket: Optional[str] = None) -> str:
        """
        Check if object exists in S3.

        Args:
            key: S3 object key
            bucket: S3 bucket name (optional)

        Returns:
            Existence message
        """
        try:
            config = get_aws_config()
            bucket_name = config.get_s3_bucket(bucket)

            # Create S3 client
            s3_client = boto3.client('s3', **config.get_boto3_session_kwargs())

            # Check existence (head_object is more efficient than get_object)
            try:
                s3_client.head_object(Bucket=bucket_name, Key=key)
                return f"Object exists: s3://{bucket_name}/{key}"
            except s3_client.exceptions.ClientError as e:
                if e.response['Error']['Code'] == '404':
                    return f"Object does not exist: s3://{bucket_name}/{key}"
                raise

        except Exception as e:
            return f"Error checking S3 object: {str(e)}"

    async def _arun(self, key: str, bucket: Optional[str] = None) -> str:
        """Async version (falls back to sync for now)"""
        return self._run(key, bucket)


# ============================================================================
# Tool Collection
# ============================================================================

def get_s3_tools() -> list[BaseTool]:
    """
    Get all S3 tools for use with LangChain agents.

    Returns:
        List of S3 tools
    """
    return [
        S3ReadTool(),
        S3WriteTool(),
        S3ListTool(),
        S3ExistsTool()
    ]

"""
Bedrock LLM Client

Simplified Bedrock API access for Claude models.

Abstracts boto3 complexity for workflow developers.
"""

import boto3
import json
from typing import Any, Dict, List, Optional, Iterator
from botocore.exceptions import ClientError


class BedrockClient:
    """
    Simplified Bedrock API access for Claude models.

    Provides easy-to-use wrappers around AWS Bedrock Runtime API.
    Workflows can use this instead of managing boto3 clients directly.
    """

    def __init__(
        self,
        region: str = "us-east-1",
        model_id: str = "anthropic.claude-sonnet-4-20250514-v1:0"
    ):
        """
        Initialize Bedrock client.

        Args:
            region: AWS region (default: us-east-1)
            model_id: Bedrock model ID (default: Claude Sonnet 4)
        """
        self.client = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id

    def invoke(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0
    ) -> str:
        """
        Simple LLM invocation.

        Args:
            prompt: User prompt
            system: Optional system prompt
            max_tokens: Max tokens to generate (default: 4096)
            temperature: 0-1, creativity level (default: 0)

        Returns:
            LLM response text
        """
        try:
            # Build messages
            messages = [{"role": "user", "content": prompt}]

            # Build request body
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }

            # Add system prompt if provided
            if system:
                request_body["system"] = system

            # Invoke model
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response['body'].read())

            # Extract text from response
            if 'content' in response_body and len(response_body['content']) > 0:
                return response_body['content'][0].get('text', '')

            return ""

        except ClientError as e:
            print(f"Error invoking Bedrock model: {e}")
            return ""
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing Bedrock response: {e}")
            return ""

    def invoke_with_tools(
        self,
        prompt: str,
        tools: List[Dict],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0
    ) -> Dict:
        """
        Invoke with tool calling capability.

        Args:
            prompt: User prompt
            tools: List of tool definitions
            system: Optional system prompt
            max_tokens: Max tokens to generate
            temperature: Creativity level

        Returns:
            Full response dict including tool calls
        """
        try:
            # Build messages
            messages = [{"role": "user", "content": prompt}]

            # Build request body
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
                "tools": tools
            }

            # Add system prompt if provided
            if system:
                request_body["system"] = system

            # Invoke model
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # Parse and return full response
            response_body = json.loads(response['body'].read())
            return response_body

        except ClientError as e:
            print(f"Error invoking Bedrock model with tools: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            print(f"Error parsing Bedrock response: {e}")
            return {"error": str(e)}

    def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0
    ) -> Iterator[str]:
        """
        Stream response token by token.

        Args:
            prompt: User prompt
            system: Optional system prompt
            max_tokens: Max tokens to generate
            temperature: Creativity level

        Yields:
            Text chunks as they arrive
        """
        try:
            # Build messages
            messages = [{"role": "user", "content": prompt}]

            # Build request body
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }

            # Add system prompt if provided
            if system:
                request_body["system"] = system

            # Invoke model with streaming
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # Process stream
            stream = response.get('body')
            if stream:
                for event in stream:
                    chunk = event.get('chunk')
                    if chunk:
                        chunk_data = json.loads(chunk.get('bytes').decode())

                        # Extract text delta
                        if chunk_data.get('type') == 'content_block_delta':
                            delta = chunk_data.get('delta', {})
                            if delta.get('type') == 'text_delta':
                                text = delta.get('text', '')
                                if text:
                                    yield text

        except ClientError as e:
            print(f"Error streaming from Bedrock model: {e}")
            yield f"Error: {e}"
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing Bedrock stream: {e}")
            yield f"Error: {e}"

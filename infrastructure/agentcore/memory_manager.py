"""
AWS Bedrock AgentCore Memory Manager

Manages short-term and long-term memory via AWS Bedrock AgentCore Memory service.

Short-term memory: Session-based conversation history and context
Long-term memory: Persistent knowledge across sessions and workflows
"""

from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import boto3
import json
import os
from infrastructure.config.aws_config import get_aws_config


class MemoryType(str, Enum):
    """Memory types supported by AgentCore"""

    SHORT_TERM = "SHORT_TERM"
    LONG_TERM = "LONG_TERM"


@dataclass
class MemoryEntry:
    """Represents a memory entry"""

    content: Dict[str, Any]
    timestamp: str
    memory_type: MemoryType
    namespace: str
    metadata: Optional[Dict[str, Any]] = None


class AgentCoreMemoryManager:
    """
    Manages short-term and long-term memory via AWS Bedrock AgentCore.

    Features:
    - Session-based short-term memory for conversations
    - Persistent long-term memory for workflow knowledge
    - Hierarchical namespace organization
    - Automatic consolidation policies
    - Query and retrieval capabilities

    Example:
        ```python
        memory_mgr = AgentCoreMemoryManager(
            memory_id="agent-memory-123",
            environment="production"
        )

        # Create session
        session_id = memory_mgr.create_session("user-session-1")

        # Add to conversation
        memory_mgr.add_to_conversation(
            session_id=session_id,
            role="user",
            content="Analyze this JIL file"
        )

        # Store workflow result
        memory_mgr.store_workflow_result(
            workflow_name="jil_parser",
            execution_id="exec-123",
            result={"dependencies": [...]}
        )
        ```
    """

    def __init__(
        self,
        memory_id: Optional[str] = None,
        region: Optional[str] = None,
        environment: str = "production",
        aws_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize AgentCore Memory Manager.

        Args:
            memory_id: AgentCore Memory ID (from environment if not provided)
            region: AWS region (from config if not provided)
            environment: Environment name (dev, staging, production)
            aws_config: Optional AWS configuration overrides
        """
        # Get AWS configuration
        config = aws_config or get_aws_config()

        self.memory_id = memory_id or os.getenv("AGENTCORE_MEMORY_ID")
        if not self.memory_id:
            raise ValueError(
                "memory_id must be provided or AGENTCORE_MEMORY_ID must be set"
            )

        self.region = region or config.get("region", "us-east-1")
        self.environment = environment

        # Initialize Bedrock Agent Runtime client
        client_kwargs = {
            "service_name": "bedrock-agent-runtime",
            "region_name": self.region,
        }

        # Add optional config from AWS configuration
        if "endpoint_url" in config:
            client_kwargs["endpoint_url"] = config["endpoint_url"]
        if "verify" in config:
            client_kwargs["verify"] = config["verify"]

        self.client = boto3.client(**client_kwargs)

    def _build_namespace(self, *parts: str) -> str:
        """Build hierarchical namespace path"""
        return f"/dataops-agent/{self.environment}/{'/'.join(parts)}"

    # =========================================================================
    # Session Management
    # =========================================================================

    def create_session(
        self, session_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new session with short-term memory.

        Args:
            session_id: Unique session identifier
            metadata: Optional session metadata

        Returns:
            Session creation response
        """
        namespace = self._build_namespace("sessions", session_id)

        try:
            response = self.client.create_agent_memory_session(
                agentMemoryId=self.memory_id,
                sessionId=session_id,
                sessionConfiguration={
                    "namespace": namespace,
                    "metadata": metadata or {},
                    "createdAt": datetime.utcnow().isoformat(),
                },
            )
            return response
        except self.client.exceptions.ConflictException:
            # Session already exists
            return {"sessionId": session_id, "status": "exists"}
        except Exception as e:
            raise RuntimeError(f"Failed to create session: {str(e)}") from e

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information.

        Args:
            session_id: Session identifier

        Returns:
            Session information or None if not found
        """
        try:
            response = self.client.get_agent_memory_session(
                agentMemoryId=self.memory_id, sessionId=session_id
            )
            return response
        except self.client.exceptions.ResourceNotFoundException:
            return None

    def end_session(
        self, session_id: str, consolidate_to_long_term: bool = True
    ) -> None:
        """
        End session and optionally consolidate to long-term memory.

        Args:
            session_id: Session identifier
            consolidate_to_long_term: Whether to consolidate important
                                      memories to long-term storage
        """
        try:
            self.client.delete_agent_memory_session(
                agentMemoryId=self.memory_id,
                sessionId=session_id,
                consolidateToLongTerm=consolidate_to_long_term,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to end session: {str(e)}") from e

    # =========================================================================
    # Short-term Memory (Conversation)
    # =========================================================================

    def add_to_conversation(
        self,
        session_id: str,
        role: Literal["user", "assistant", "system"],
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add message to session conversation history.

        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional message metadata

        Returns:
            Memory creation response
        """
        memory_content = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        try:
            response = self.client.put_agent_memory(
                agentMemoryId=self.memory_id,
                sessionId=session_id,
                memoryType=MemoryType.SHORT_TERM.value,
                content=json.dumps(memory_content),
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Failed to add to conversation: {str(e)}") from e

    def get_conversation_history(
        self, session_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to retrieve
            offset: Offset for pagination

        Returns:
            List of conversation messages
        """
        try:
            response = self.client.list_agent_memories(
                agentMemoryId=self.memory_id,
                sessionId=session_id,
                memoryType=MemoryType.SHORT_TERM.value,
                maxResults=limit,
                nextToken=str(offset) if offset > 0 else None,
            )

            memories = response.get("memories", [])

            # Parse JSON content
            parsed_memories = []
            for memory in memories:
                try:
                    content = json.loads(memory.get("content", "{}"))
                    parsed_memories.append(content)
                except json.JSONDecodeError:
                    # Fallback for non-JSON content
                    parsed_memories.append({"content": memory.get("content")})

            return parsed_memories
        except Exception as e:
            raise RuntimeError(
                f"Failed to get conversation history: {str(e)}"
            ) from e

    # =========================================================================
    # Long-term Memory (Persistent Knowledge)
    # =========================================================================

    def store_workflow_result(
        self,
        workflow_name: str,
        execution_id: str,
        result: Dict[str, Any],
        tags: Optional[List[str]] = None,
        summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Store workflow execution result in long-term memory.

        Args:
            workflow_name: Name of the workflow
            execution_id: Unique execution identifier
            result: Workflow execution result
            tags: Optional tags for categorization
            summary: Optional human-readable summary

        Returns:
            Memory creation response
        """
        namespace = self._build_namespace("persistent", "workflows", workflow_name)

        memory_content = {
            "execution_id": execution_id,
            "workflow_name": workflow_name,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "tags": tags or [],
            "summary": summary,
        }

        try:
            response = self.client.put_agent_memory(
                agentMemoryId=self.memory_id,
                memoryType=MemoryType.LONG_TERM.value,
                namespace=namespace,
                content=json.dumps(memory_content),
                metadata={
                    "workflow_name": workflow_name,
                    "execution_id": execution_id,
                    "tags": json.dumps(tags or []),
                },
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Failed to store workflow result: {str(e)}") from e

    def retrieve_workflow_knowledge(
        self,
        workflow_name: str,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant workflow knowledge from long-term memory.

        Args:
            workflow_name: Name of the workflow
            query: Optional semantic search query
            tags: Optional tags to filter by
            limit: Maximum number of results

        Returns:
            List of relevant memory entries
        """
        namespace = self._build_namespace("persistent", "workflows", workflow_name)

        try:
            # Build query parameters
            params = {
                "agentMemoryId": self.memory_id,
                "memoryType": MemoryType.LONG_TERM.value,
                "namespace": namespace,
                "maxResults": limit,
            }

            # Add semantic search query if provided
            if query:
                params["searchQuery"] = query

            # Add tag filters if provided
            if tags:
                params["filters"] = {"tags": tags}

            response = self.client.query_agent_memories(**params)

            memories = response.get("memories", [])

            # Parse JSON content
            parsed_memories = []
            for memory in memories:
                try:
                    content = json.loads(memory.get("content", "{}"))
                    content["memory_id"] = memory.get("memoryId")
                    content["relevance_score"] = memory.get("relevanceScore", 0.0)
                    parsed_memories.append(content)
                except json.JSONDecodeError:
                    # Fallback for non-JSON content
                    parsed_memories.append({
                        "content": memory.get("content"),
                        "memory_id": memory.get("memoryId"),
                    })

            return parsed_memories
        except Exception as e:
            raise RuntimeError(
                f"Failed to retrieve workflow knowledge: {str(e)}"
            ) from e

    def store_user_preference(
        self, user_id: str, preference_key: str, preference_value: Any
    ) -> Dict[str, Any]:
        """
        Store user preference in long-term memory.

        Args:
            user_id: User identifier
            preference_key: Preference key
            preference_value: Preference value

        Returns:
            Memory creation response
        """
        namespace = self._build_namespace("persistent", "users", user_id)

        memory_content = {
            "user_id": user_id,
            "preference_key": preference_key,
            "preference_value": preference_value,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            response = self.client.put_agent_memory(
                agentMemoryId=self.memory_id,
                memoryType=MemoryType.LONG_TERM.value,
                namespace=namespace,
                content=json.dumps(memory_content),
                metadata={"user_id": user_id, "preference_key": preference_key},
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Failed to store user preference: {str(e)}") from e

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get all user preferences.

        Args:
            user_id: User identifier

        Returns:
            Dictionary of user preferences
        """
        namespace = self._build_namespace("persistent", "users", user_id)

        try:
            response = self.client.list_agent_memories(
                agentMemoryId=self.memory_id,
                memoryType=MemoryType.LONG_TERM.value,
                namespace=namespace,
                maxResults=100,
            )

            memories = response.get("memories", [])

            # Parse and collect preferences
            preferences = {}
            for memory in memories:
                try:
                    content = json.loads(memory.get("content", "{}"))
                    key = content.get("preference_key")
                    value = content.get("preference_value")
                    if key:
                        preferences[key] = value
                except json.JSONDecodeError:
                    continue

            return preferences
        except Exception as e:
            raise RuntimeError(f"Failed to get user preferences: {str(e)}") from e

    # =========================================================================
    # Knowledge Base Operations
    # =========================================================================

    def store_knowledge(
        self,
        category: str,
        key: str,
        value: Dict[str, Any],
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Store knowledge in organized categories.

        Args:
            category: Knowledge category (e.g., 'jil_dependencies', 'oracle_lineage')
            key: Knowledge key
            value: Knowledge value
            tags: Optional tags

        Returns:
            Memory creation response
        """
        namespace = self._build_namespace("persistent", "knowledge", category)

        memory_content = {
            "category": category,
            "key": key,
            "value": value,
            "timestamp": datetime.utcnow().isoformat(),
            "tags": tags or [],
        }

        try:
            response = self.client.put_agent_memory(
                agentMemoryId=self.memory_id,
                memoryType=MemoryType.LONG_TERM.value,
                namespace=namespace,
                content=json.dumps(memory_content),
                metadata={"category": category, "key": key},
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Failed to store knowledge: {str(e)}") from e

    def retrieve_knowledge(
        self,
        category: str,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve knowledge from a specific category.

        Args:
            category: Knowledge category
            query: Optional semantic search query
            tags: Optional tags to filter by
            limit: Maximum number of results

        Returns:
            List of relevant knowledge entries
        """
        namespace = self._build_namespace("persistent", "knowledge", category)

        try:
            params = {
                "agentMemoryId": self.memory_id,
                "memoryType": MemoryType.LONG_TERM.value,
                "namespace": namespace,
                "maxResults": limit,
            }

            if query:
                params["searchQuery"] = query
            if tags:
                params["filters"] = {"tags": tags}

            response = self.client.query_agent_memories(**params)

            memories = response.get("memories", [])

            # Parse JSON content
            parsed_memories = []
            for memory in memories:
                try:
                    content = json.loads(memory.get("content", "{}"))
                    parsed_memories.append(content)
                except json.JSONDecodeError:
                    continue

            return parsed_memories
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve knowledge: {str(e)}") from e

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def delete_memory(self, memory_id: str) -> None:
        """
        Delete a specific memory by ID.

        Args:
            memory_id: Memory identifier
        """
        try:
            self.client.delete_agent_memory(
                agentMemoryId=self.memory_id, memoryId=memory_id
            )
        except Exception as e:
            raise RuntimeError(f"Failed to delete memory: {str(e)}") from e

    def list_all_memories(
        self,
        memory_type: Optional[MemoryType] = None,
        namespace: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List all memories with optional filtering.

        Args:
            memory_type: Optional memory type filter
            namespace: Optional namespace filter
            limit: Maximum number of results

        Returns:
            List of memories
        """
        try:
            params = {"agentMemoryId": self.memory_id, "maxResults": limit}

            if memory_type:
                params["memoryType"] = memory_type.value
            if namespace:
                params["namespace"] = namespace

            response = self.client.list_agent_memories(**params)
            return response.get("memories", [])
        except Exception as e:
            raise RuntimeError(f"Failed to list memories: {str(e)}") from e

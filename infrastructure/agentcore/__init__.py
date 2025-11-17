"""
AWS Bedrock AgentCore Integration

This module provides integration with AWS Bedrock AgentCore services,
including Memory management for short-term and long-term memory.
"""

from infrastructure.agentcore.memory_manager import (
    AgentCoreMemoryManager,
    MemoryType,
    MemoryEntry,
)

__all__ = [
    "AgentCoreMemoryManager",
    "MemoryType",
    "MemoryEntry",
]

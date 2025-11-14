# DataOps Agent - Implementation Guide

**Version:** 2.0
**Purpose:** Practical guide for implementing the extended architecture

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Implementation Order](#implementation-order)
3. [Component Implementation](#component-implementation)
4. [Code Examples](#code-examples)
5. [Migration Guide](#migration-guide)
6. [Testing Strategy](#testing-strategy)

---

## Quick Start

### Priority Components

Based on your requirements, implement in this order:

1. **Session Management** (Week 1)
   - Enables conversation continuity
   - Foundation for other features
   - Immediate user value

2. **Artifact Management** (Week 1-2)
   - Workflow output storage
   - Cross-workflow sharing
   - Critical for complex workflows

3. **Context Management** (Week 2)
   - Context dumping/loading
   - Workflow handoffs
   - Memory management

4. **Workflow Dev Kit** (Week 3)
   - Makes creating workflows easier
   - Developer productivity
   - Reduces boilerplate

5. **Enhanced Orchestration** (Week 4)
   - Workflow chaining
   - Parallel execution
   - Advanced patterns

---

## Implementation Order

### Week 1: Foundation

#### Day 1-2: Session Management

```
Tasks:
1. Create session models and schemas
2. Implement SessionManager class
3. Add Redis integration for hot storage
4. Add DynamoDB for persistence
5. Update orchestrator to use sessions
6. Write unit tests
```

#### Day 3-5: Artifact Management

```
Tasks:
1. Create artifact models
2. Implement ArtifactStore class
3. Add S3 backend integration
4. Add DynamoDB for metadata
5. Add artifact helpers for workflows
6. Write unit tests
```

### Week 2: Context & Developer Tools

#### Day 1-2: Context Management

```
Tasks:
1. Create ContextManager class
2. Implement context compression with LLM
3. Add checkpoint/restore functionality
4. Integrate with SessionManager
5. Write unit tests
```

#### Day 3-5: CLI Scaffolding Tool

```
Tasks:
1. Create dataops-workflow CLI tool
2. Implement workflow templates
3. Add test generation
4. Add documentation generation
5. Create example workflows using CLI
```

### Week 3: Enhanced Orchestration

```
Tasks:
1. Implement WorkflowChain
2. Add parallel execution support
3. Implement conditional orchestration
4. Add workflow dependency resolution
5. Update orchestrator to support chaining
6. Write integration tests
```

### Week 4: API & Production Features

```
Tasks:
1. Create FastAPI application
2. Add REST endpoints
3. Add WebSocket support
4. Implement authentication
5. Add rate limiting
6. Add comprehensive logging
```

---

## Component Implementation

### 1. Session Management

#### Step 1: Define Models

Create `core/session.py`:

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class SessionStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    EXPIRED = "expired"

class Message(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    role: str  # user, assistant, system
    content: str
    workflow: Optional[str] = None
    artifacts: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class UserPreferences(BaseModel):
    default_model: str = "claude-sonnet-4-20250514"
    max_context_messages: int = 20
    auto_compress_context: bool = True
    preferred_workflows: List[str] = Field(default_factory=list)

class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: f"sess_{uuid.uuid4()}")
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)

    # Conversation
    conversation_history: List[Message] = Field(default_factory=list)
    message_count: int = 0

    # Context
    global_context: Dict[str, Any] = Field(default_factory=dict)
    active_workflows: List[str] = Field(default_factory=list)
    artifact_refs: List[str] = Field(default_factory=list)

    # Preferences
    preferences: UserPreferences = Field(default_factory=UserPreferences)

    # State
    status: SessionStatus = SessionStatus.ACTIVE
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_message(self, role: str, content: str, **kwargs) -> Message:
        """Add message to conversation history"""
        message = Message(
            role=role,
            content=content,
            **kwargs
        )
        self.conversation_history.append(message)
        self.message_count += 1
        self.last_active = datetime.utcnow()
        return message

    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """Get most recent messages"""
        return self.conversation_history[-count:]

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict) -> "Session":
        """Load from dictionary"""
        return cls(**data)
```

#### Step 2: Implement SessionManager

Create `core/session_manager.py`:

```python
import redis
import boto3
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from core.session import Session, Message, SessionStatus

class SessionManager:
    """
    Manages user sessions with hot/cold storage.

    Hot storage: Redis (active sessions)
    Cold storage: DynamoDB (inactive/archived sessions)
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        dynamodb_client: Optional[Any] = None,
        table_name: str = "dataops_sessions",
        ttl_hours: int = 24
    ):
        # Redis for hot storage
        self.redis = redis_client or redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True
        )

        # DynamoDB for cold storage
        self.dynamodb = dynamodb_client or boto3.resource("dynamodb")
        self.table_name = table_name
        self.table = self.dynamodb.Table(table_name)

        self.ttl_hours = ttl_hours

    def create_session(self, user_id: str, metadata: Optional[Dict] = None) -> Session:
        """Create new session"""
        session = Session(
            user_id=user_id,
            metadata=metadata or {}
        )

        # Store in hot cache
        self._cache_session(session)

        # Store in cold storage
        self._persist_session(session)

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get session by ID.

        Check hot cache first, fall back to cold storage.
        """
        # Try hot cache first
        cached = self._get_cached_session(session_id)
        if cached:
            # Update last active
            cached.last_active = datetime.utcnow()
            self._cache_session(cached)
            return cached

        # Fall back to cold storage
        persisted = self._get_persisted_session(session_id)
        if persisted:
            # Warm up cache
            self._cache_session(persisted)
            return persisted

        return None

    def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Session]:
        """Update session with partial updates"""
        session = self.get_session(session_id)
        if not session:
            return None

        # Apply updates
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)

        session.last_active = datetime.utcnow()

        # Update both storages
        self._cache_session(session)
        self._persist_session(session)

        return session

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        **kwargs
    ) -> Optional[Message]:
        """Add message to session"""
        session = self.get_session(session_id)
        if not session:
            return None

        message = session.add_message(role, content, **kwargs)

        # Update storages
        self._cache_session(session)
        self._persist_session(session)

        return message

    def get_context_summary(
        self,
        session_id: str,
        max_messages: Optional[int] = None
    ) -> str:
        """
        Get session context as formatted string for LLM.
        """
        session = self.get_session(session_id)
        if not session:
            return ""

        max_messages = max_messages or session.preferences.max_context_messages
        recent_messages = session.get_recent_messages(max_messages)

        lines = [
            f"Session: {session_id}",
            f"User: {session.user_id}",
            f"Messages: {session.message_count}",
            "",
            "Recent Conversation:",
            ""
        ]

        for msg in recent_messages:
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"[{timestamp}] {msg.role}: {msg.content}")

        if session.global_context:
            lines.append("")
            lines.append("Session Context:")
            lines.append(json.dumps(session.global_context, indent=2))

        return "\n".join(lines)

    def list_user_sessions(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[Session]:
        """List all sessions for a user"""
        # Query DynamoDB
        response = self.table.query(
            IndexName="user_id-index",
            KeyConditionExpression="user_id = :uid",
            ExpressionAttributeValues={":uid": user_id}
        )

        sessions = [
            Session.from_dict(item)
            for item in response.get("Items", [])
        ]

        if active_only:
            sessions = [
                s for s in sessions
                if s.status == SessionStatus.ACTIVE
            ]

        return sorted(sessions, key=lambda s: s.last_active, reverse=True)

    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        expiry_time = datetime.utcnow() - timedelta(hours=self.ttl_hours)

        # Scan for expired sessions
        response = self.table.scan(
            FilterExpression="last_active < :expiry",
            ExpressionAttributeValues={
                ":expiry": expiry_time.isoformat()
            }
        )

        expired_sessions = response.get("Items", [])

        for session_data in expired_sessions:
            session_id = session_data["session_id"]

            # Update status
            self.table.update_item(
                Key={"session_id": session_id},
                UpdateExpression="SET #status = :status",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":status": SessionStatus.EXPIRED.value}
            )

            # Remove from cache
            self.redis.delete(f"session:{session_id}")

    # Private methods

    def _cache_session(self, session: Session):
        """Store session in Redis cache"""
        key = f"session:{session.session_id}"
        value = json.dumps(session.to_dict(), default=str)
        self.redis.setex(
            key,
            timedelta(hours=self.ttl_hours),
            value
        )

    def _get_cached_session(self, session_id: str) -> Optional[Session]:
        """Get session from Redis cache"""
        key = f"session:{session_id}"
        data = self.redis.get(key)

        if data:
            return Session.from_dict(json.loads(data))

        return None

    def _persist_session(self, session: Session):
        """Store session in DynamoDB"""
        self.table.put_item(Item=session.to_dict())

    def _get_persisted_session(self, session_id: str) -> Optional[Session]:
        """Get session from DynamoDB"""
        response = self.table.get_item(Key={"session_id": session_id})
        item = response.get("Item")

        if item:
            return Session.from_dict(item)

        return None
```

#### Step 3: Update Orchestrator to Use Sessions

Update `core/orchestrator.py`:

```python
from core.session_manager import SessionManager

# Add session manager
session_manager = SessionManager()

# Update orchestrator state
class OrchestratorState(TypedDict):
    session_id: str  # NEW
    user_query: str
    detected_intent: str
    extracted_parameters: dict
    missing_parameters: list
    workflow_result: dict
    final_response: str

# Update intent detection to use session context
def intent_detection_node(state: OrchestratorState) -> dict:
    user_query = state["user_query"]
    session_id = state.get("session_id")

    # Get session context
    context_summary = ""
    if session_id:
        context_summary = session_manager.get_context_summary(session_id)

    # Include context in intent detection
    capabilities_context = WORKFLOW_REGISTRY.get_capabilities_context()

    prompt = f"""You are a data engineering assistant with these capabilities:

{capabilities_context}

{f"Session Context:\\n{context_summary}\\n" if context_summary else ""}

User query: "{user_query}"

Based on the capabilities and context above, which workflow should handle this query?
Return ONLY the workflow name.

Your decision:"""

    response = llm.invoke(prompt)
    workflow_name = response.content.strip().lower()

    # Add message to session
    if session_id:
        session_manager.add_message(
            session_id,
            role="user",
            content=user_query
        )

    return {"detected_intent": workflow_name}

# Update response formatting to save to session
def response_formatting_node(state: OrchestratorState) -> dict:
    # ... existing code ...

    # Save response to session
    session_id = state.get("session_id")
    if session_id:
        session_manager.add_message(
            session_id,
            role="assistant",
            content=final_response,
            workflow=workflow_type,
            metadata=metadata
        )

    return {"final_response": final_response}
```

---

### 2. Artifact Management

#### Step 1: Define Models

Create `core/artifact.py`:

```python
from pydantic import BaseModel, Field
from typing import Union, Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid

class ArtifactType(str, Enum):
    RESULT = "result"           # Final workflow result
    INTERMEDIATE = "intermediate"  # Intermediate computation
    DEBUG = "debug"            # Debug information
    CONTEXT = "context"        # Context snapshot
    DATA = "data"              # Raw data
    MODEL = "model"            # ML model or artifact

class Artifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: f"art_{uuid.uuid4()}")
    session_id: str
    workflow_name: str
    artifact_type: ArtifactType

    # Content reference (actual content in S3)
    s3_key: str
    content_type: str  # json, text, binary, parquet, csv
    size_bytes: int = 0

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str  # node name or user
    description: Optional[str] = None

    # Relationships
    parent_artifacts: List[str] = Field(default_factory=list)
    derived_from: Optional[str] = None

    # Lifecycle
    ttl: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = Field(default_factory=datetime.utcnow)

    # Tags for filtering
    tags: Dict[str, str] = Field(default_factory=dict)

    def to_dict(self) -> Dict:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict) -> "Artifact":
        return cls(**data)
```

#### Step 2: Implement ArtifactStore

Create `core/artifact_store.py`:

```python
import boto3
import json
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
from core.artifact import Artifact, ArtifactType

class ArtifactStore:
    """
    Centralized artifact management.

    Storage:
    - Metadata: DynamoDB
    - Content: S3
    """

    def __init__(
        self,
        bucket: Optional[str] = None,
        table_name: str = "dataops_artifacts",
        default_ttl_days: int = 30
    ):
        self.bucket = bucket or os.getenv("ARTIFACT_BUCKET")
        self.s3 = boto3.client("s3")

        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

        self.default_ttl_days = default_ttl_days

    def store_artifact(
        self,
        content: Union[str, Dict, bytes],
        session_id: str,
        workflow_name: str,
        artifact_type: ArtifactType = ArtifactType.RESULT,
        **metadata
    ) -> str:
        """
        Store artifact and return ID.

        Args:
            content: Artifact content
            session_id: Session ID
            workflow_name: Workflow that created it
            artifact_type: Type of artifact
            **metadata: Additional metadata

        Returns:
            artifact_id
        """
        # Create artifact
        artifact = Artifact(
            session_id=session_id,
            workflow_name=workflow_name,
            artifact_type=artifact_type,
            created_by=metadata.get("created_by", "unknown"),
            description=metadata.get("description"),
            tags=metadata.get("tags", {}),
            ttl=datetime.utcnow() + timedelta(days=self.default_ttl_days)
        )

        # Determine content type and serialize
        if isinstance(content, dict):
            content_bytes = json.dumps(content, indent=2).encode()
            artifact.content_type = "json"
        elif isinstance(content, str):
            content_bytes = content.encode()
            artifact.content_type = "text"
        elif isinstance(content, bytes):
            content_bytes = content
            artifact.content_type = metadata.get("content_type", "binary")
        else:
            raise ValueError(f"Unsupported content type: {type(content)}")

        artifact.size_bytes = len(content_bytes)

        # Generate S3 key
        artifact.s3_key = self._generate_s3_key(artifact)

        # Upload to S3
        self.s3.put_object(
            Bucket=self.bucket,
            Key=artifact.s3_key,
            Body=content_bytes,
            ContentType=artifact.content_type,
            Metadata={
                "artifact_id": artifact.artifact_id,
                "session_id": artifact.session_id,
                "workflow": artifact.workflow_name
            }
        )

        # Store metadata in DynamoDB
        self.table.put_item(Item=artifact.to_dict())

        return artifact.artifact_id

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """Get artifact metadata"""
        response = self.table.get_item(Key={"artifact_id": artifact_id})
        item = response.get("Item")

        if item:
            artifact = Artifact.from_dict(item)

            # Update access tracking
            artifact.access_count += 1
            artifact.last_accessed = datetime.utcnow()
            self.table.update_item(
                Key={"artifact_id": artifact_id},
                UpdateExpression="SET access_count = :count, last_accessed = :time",
                ExpressionAttributeValues={
                    ":count": artifact.access_count,
                    ":time": artifact.last_accessed.isoformat()
                }
            )

            return artifact

        return None

    def get_artifact_content(self, artifact_id: str) -> Optional[Any]:
        """Get artifact content from S3"""
        artifact = self.get_artifact(artifact_id)
        if not artifact:
            return None

        # Download from S3
        response = self.s3.get_object(
            Bucket=self.bucket,
            Key=artifact.s3_key
        )

        content_bytes = response["Body"].read()

        # Deserialize based on content type
        if artifact.content_type == "json":
            return json.loads(content_bytes.decode())
        elif artifact.content_type == "text":
            return content_bytes.decode()
        else:
            return content_bytes

    def list_artifacts(
        self,
        session_id: str,
        workflow_name: Optional[str] = None,
        artifact_type: Optional[ArtifactType] = None,
        limit: int = 100
    ) -> List[Artifact]:
        """List artifacts for session"""
        # Query by session_id
        key_condition = "session_id = :sid"
        expression_values = {":sid": session_id}

        if workflow_name:
            filter_expr = "workflow_name = :wf"
            expression_values[":wf"] = workflow_name
        else:
            filter_expr = None

        response = self.table.query(
            IndexName="session_id-index",
            KeyConditionExpression=key_condition,
            FilterExpression=filter_expr if filter_expr else None,
            ExpressionAttributeValues=expression_values,
            Limit=limit
        )

        artifacts = [
            Artifact.from_dict(item)
            for item in response.get("Items", [])
        ]

        # Filter by type if specified
        if artifact_type:
            artifacts = [a for a in artifacts if a.artifact_type == artifact_type]

        return sorted(artifacts, key=lambda a: a.created_at, reverse=True)

    def share_artifact(
        self,
        artifact_id: str,
        target_session: str
    ) -> str:
        """
        Share artifact with another session.

        Creates a reference artifact pointing to the same S3 object.
        """
        original = self.get_artifact(artifact_id)
        if not original:
            raise ValueError(f"Artifact not found: {artifact_id}")

        # Create new artifact reference
        shared = Artifact(
            session_id=target_session,
            workflow_name=original.workflow_name,
            artifact_type=original.artifact_type,
            s3_key=original.s3_key,  # Same S3 object
            content_type=original.content_type,
            size_bytes=original.size_bytes,
            created_by=f"shared_from_{artifact_id}",
            description=f"Shared from {artifact_id}",
            parent_artifacts=[artifact_id],
            derived_from=artifact_id
        )

        # Store metadata
        self.table.put_item(Item=shared.to_dict())

        return shared.artifact_id

    def link_artifacts(self, parent_id: str, child_id: str):
        """Create lineage relationship"""
        child = self.get_artifact(child_id)
        if not child:
            raise ValueError(f"Child artifact not found: {child_id}")

        # Add parent to child's parent list
        if parent_id not in child.parent_artifacts:
            child.parent_artifacts.append(parent_id)

            self.table.update_item(
                Key={"artifact_id": child_id},
                UpdateExpression="SET parent_artifacts = :parents",
                ExpressionAttributeValues={
                    ":parents": child.parent_artifacts
                }
            )

    def cleanup_expired_artifacts(self):
        """Remove expired artifacts"""
        now = datetime.utcnow()

        # Scan for expired artifacts
        response = self.table.scan(
            FilterExpression="ttl < :now",
            ExpressionAttributeValues={":now": now.isoformat()}
        )

        expired = response.get("Items", [])

        for artifact_data in expired:
            artifact = Artifact.from_dict(artifact_data)

            # Delete from S3
            self.s3.delete_object(
                Bucket=self.bucket,
                Key=artifact.s3_key
            )

            # Delete metadata
            self.table.delete_item(
                Key={"artifact_id": artifact.artifact_id}
            )

    # Private methods

    def _generate_s3_key(self, artifact: Artifact) -> str:
        """Generate S3 key for artifact"""
        date_prefix = artifact.created_at.strftime("%Y/%m/%d")
        return f"artifacts/{artifact.session_id}/{date_prefix}/{artifact.artifact_id}"
```

#### Step 3: Add Artifact Helpers for Workflows

Create decorator helpers in `core/decorators.py`:

```python
from functools import wraps
from core.artifact_store import ArtifactStore, ArtifactType

# Global artifact store
artifact_store = ArtifactStore()

def with_artifacts(artifact_type: ArtifactType = ArtifactType.INTERMEDIATE):
    """
    Decorator to automatically save node outputs as artifacts.

    Usage:
        @with_artifacts(ArtifactType.RESULT)
        def my_node(state: MyState) -> Dict:
            return {"output": "some result"}
    """
    def decorator(func):
        @wraps(func)
        def wrapper(state, *args, **kwargs):
            # Execute node
            result = func(state, *args, **kwargs)

            # Extract session info from state
            session_id = state.get("session_id")
            workflow_name = state.get("workflow_name", "unknown")

            if session_id and "output" in result:
                # Store output as artifact
                artifact_id = artifact_store.store_artifact(
                    content=result["output"],
                    session_id=session_id,
                    workflow_name=workflow_name,
                    artifact_type=artifact_type,
                    created_by=func.__name__
                )

                # Add artifact reference to result
                if "artifacts" not in result:
                    result["artifacts"] = []
                result["artifacts"].append(artifact_id)

            return result

        return wrapper
    return decorator
```

---

### 3. Context Management

Create `core/context_manager.py`:

```python
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel
import json
import zlib
from langchain_anthropic import ChatAnthropic
from core.session_manager import SessionManager
from core.artifact_store import ArtifactStore, ArtifactType

class ContextSnapshot(BaseModel):
    snapshot_id: str
    session_id: str
    created_at: datetime

    # Context data
    orchestrator_state: Dict[str, Any]
    workflow_states: Dict[str, Any]

    # Artifacts
    artifact_refs: List[str]

    # Compression
    compressed: bool = False
    original_size: int = 0
    compressed_size: int = 0

class ContextManager:
    """Manages context snapshots and intelligent context handling"""

    def __init__(
        self,
        session_manager: SessionManager,
        artifact_store: ArtifactStore,
        llm: Optional[ChatAnthropic] = None
    ):
        self.session_manager = session_manager
        self.artifact_store = artifact_store
        self.llm = llm or ChatAnthropic(model="claude-sonnet-4-20250514")

    def dump_context(
        self,
        session_id: str,
        include_artifacts: bool = True,
        compress: bool = False
    ) -> str:
        """
        Dump current session context to storage.

        Returns:
            snapshot_id
        """
        # Get session
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Build context snapshot
        orchestrator_state = {
            "global_context": session.global_context,
            "active_workflows": session.active_workflows,
            "message_count": session.message_count
        }

        workflow_states = {}  # Populated by workflows if needed

        artifact_refs = []
        if include_artifacts:
            artifacts = self.artifact_store.list_artifacts(session_id)
            artifact_refs = [a.artifact_id for a in artifacts]

        snapshot = ContextSnapshot(
            snapshot_id=f"snap_{uuid.uuid4()}",
            session_id=session_id,
            created_at=datetime.utcnow(),
            orchestrator_state=orchestrator_state,
            workflow_states=workflow_states,
            artifact_refs=artifact_refs
        )

        # Calculate sizes
        snapshot_json = snapshot.model_dump_json()
        snapshot.original_size = len(snapshot_json)

        if compress:
            # Compress with zlib
            compressed_data = zlib.compress(snapshot_json.encode())
            snapshot.compressed_size = len(compressed_data)
            snapshot.compressed = True
            store_data = compressed_data
        else:
            store_data = snapshot_json

        # Store as artifact
        self.artifact_store.store_artifact(
            content=store_data,
            session_id=session_id,
            workflow_name="context_manager",
            artifact_type=ArtifactType.CONTEXT,
            created_by="context_manager",
            description=f"Context snapshot for session {session_id}",
            tags={"type": "context_snapshot"}
        )

        return snapshot.snapshot_id

    def load_context(
        self,
        snapshot_id: str,
        merge_strategy: str = "replace"
    ) -> Dict[str, Any]:
        """
        Load context from snapshot.

        Args:
            snapshot_id: Snapshot to load
            merge_strategy: "replace", "merge", or "selective"

        Returns:
            Loaded context data
        """
        # Get artifact
        content = self.artifact_store.get_artifact_content(snapshot_id)
        if not content:
            raise ValueError(f"Snapshot not found: {snapshot_id}")

        # Decompress if needed
        if isinstance(content, bytes):
            content = zlib.decompress(content).decode()

        snapshot = ContextSnapshot.model_validate_json(content)

        return snapshot.orchestrator_state

    def compress_context(
        self,
        context: Dict[str, Any],
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Use LLM to intelligently compress context.

        Preserves:
        - Key decisions
        - Important parameters
        - Critical artifact references
        - Active workflow states
        """
        prompt = f"""Compress this context to approximately {max_tokens} tokens while preserving the most important information.

Context to compress:
{json.dumps(context, indent=2)}

Return a compressed version as JSON that keeps:
1. All artifact references
2. Key parameter values
3. Important decisions made
4. Critical workflow states

Remove:
- Verbose descriptions
- Redundant data
- Less important metadata

Compressed context (JSON):"""

        response = self.llm.invoke(prompt)

        # Parse response
        try:
            compressed = json.loads(response.content)
            return compressed
        except:
            # Fallback: return original
            return context

    def create_checkpoint(
        self,
        session_id: str,
        label: str
    ) -> str:
        """Create named checkpoint for rollback"""
        snapshot_id = self.dump_context(session_id, compress=True)

        # Add checkpoint metadata
        session = self.session_manager.get_session(session_id)
        if not session.metadata.get("checkpoints"):
            session.metadata["checkpoints"] = {}

        session.metadata["checkpoints"][label] = {
            "snapshot_id": snapshot_id,
            "created_at": datetime.utcnow().isoformat()
        }

        self.session_manager.update_session(
            session_id,
            {"metadata": session.metadata}
        )

        return snapshot_id

    def restore_checkpoint(
        self,
        session_id: str,
        checkpoint_label: str
    ):
        """Restore session to checkpoint"""
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        checkpoints = session.metadata.get("checkpoints", {})
        checkpoint = checkpoints.get(checkpoint_label)

        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {checkpoint_label}")

        # Load context from snapshot
        context = self.load_context(checkpoint["snapshot_id"])

        # Update session
        self.session_manager.update_session(
            session_id,
            {"global_context": context}
        )

    def inherit_context(
        self,
        source_session: str,
        target_session: str,
        filters: Optional[List[str]] = None
    ):
        """
        Copy context from one session to another.

        Args:
            source_session: Source session ID
            target_session: Target session ID
            filters: Optional list of context keys to copy
        """
        source = self.session_manager.get_session(source_session)
        target = self.session_manager.get_session(target_session)

        if not source or not target:
            raise ValueError("Source or target session not found")

        # Copy context
        if filters:
            inherited_context = {
                k: v for k, v in source.global_context.items()
                if k in filters
            }
        else:
            inherited_context = source.global_context.copy()

        # Merge into target
        target.global_context.update(inherited_context)

        self.session_manager.update_session(
            target_session,
            {"global_context": target.global_context}
        )
```

---

## Migration Guide

### Updating Existing Workflows

Your existing workflows will continue to work without changes. To take advantage of new features:

#### 1. Add Session Support

```python
# Before
class MyWorkflowState(TypedDict):
    input: str
    output: str

# After
class MyWorkflowState(TypedDict):
    session_id: str  # Add this
    workflow_name: str  # Add this
    input: str
    output: str
    artifacts: List[str]  # Add this
```

#### 2. Use Artifact Decorators

```python
# Before
def my_node(state: MyState) -> Dict:
    result = process_data(state["input"])
    return {"output": result}

# After
from core.decorators import with_artifacts

@with_artifacts(ArtifactType.RESULT)
def my_node(state: MyState) -> Dict:
    result = process_data(state["input"])
    return {"output": result}  # Automatically saved as artifact
```

#### 3. Add Context Awareness

```python
# Use session context in your nodes
from core.session_manager import session_manager

def my_node(state: MyState) -> Dict:
    session_id = state.get("session_id")

    if session_id:
        # Get previous context
        context = session_manager.get_session(session_id)

        # Use context in processing
        if context.preferences.preferred_workflows:
            # Adjust behavior based on preferences
            pass

    # Your logic
    return {"output": result}
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_session_manager.py
import pytest
from core.session_manager import SessionManager

@pytest.fixture
def session_manager():
    return SessionManager()

def test_create_session(session_manager):
    session = session_manager.create_session(user_id="test_user")
    assert session.user_id == "test_user"
    assert session.status == SessionStatus.ACTIVE

def test_add_message(session_manager):
    session = session_manager.create_session(user_id="test_user")
    message = session_manager.add_message(
        session.session_id,
        role="user",
        content="Hello"
    )
    assert message.content == "Hello"
    assert session.message_count == 1

# tests/test_artifact_store.py
def test_store_artifact(artifact_store):
    artifact_id = artifact_store.store_artifact(
        content={"test": "data"},
        session_id="test_session",
        workflow_name="test_workflow"
    )
    assert artifact_id is not None

def test_get_artifact_content(artifact_store):
    artifact_id = artifact_store.store_artifact(
        content={"test": "data"},
        session_id="test_session",
        workflow_name="test_workflow"
    )
    content = artifact_store.get_artifact_content(artifact_id)
    assert content == {"test": "data"}
```

### Integration Tests

```python
# tests/test_integration.py
def test_full_workflow_with_session():
    # Create session
    session = session_manager.create_session("test_user")

    # Invoke orchestrator
    result = orchestrator_graph.invoke({
        "session_id": session.session_id,
        "user_query": "Parse JIL file",
        # ... other inputs
    })

    # Verify artifacts created
    artifacts = artifact_store.list_artifacts(session.session_id)
    assert len(artifacts) > 0

    # Verify context saved
    updated_session = session_manager.get_session(session.session_id)
    assert updated_session.message_count > 0
```

---

## Next Steps

1. **Start with Session Management**: Foundation for everything else
2. **Add Artifact Management**: Enable workflow output storage
3. **Implement Context Management**: Smart context handling
4. **Build CLI Tool**: Make workflow creation easy
5. **Add API Layer**: External access

Each component can be developed and tested independently!

---

**Ready to start implementing? Choose a component and let's build it together!**

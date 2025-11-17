"""
FastAPI Application for DataOps Agent

Provides REST API endpoints for:
- Workflow execution (async)
- Session management
- Chat interface
- Health checks
- Metrics
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import uvicorn
import uuid
import asyncio
from datetime import datetime
import os

# Import core modules
from core.orchestrator import orchestrator_graph
from core.workflow_registry import WORKFLOW_REGISTRY
from infrastructure.agentcore.memory_manager import AgentCoreMemoryManager


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Chat response model"""
    session_id: str
    response: str
    metadata: Dict[str, Any]
    timestamp: str


class WorkflowListResponse(BaseModel):
    """Workflow list response"""
    workflows: List[Dict[str, Any]]
    count: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    environment: str
    timestamp: str
    checks: Dict[str, bool]


# ============================================================================
# Application Lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    print("Starting DataOps Agent API...")

    # Initialize AgentCore Memory (if configured)
    memory_id = os.getenv("AGENTCORE_MEMORY_ID")
    if memory_id:
        try:
            # Test connection
            memory_mgr = AgentCoreMemoryManager(memory_id=memory_id)
            print(f"✓ AgentCore Memory connected: {memory_id}")
        except Exception as e:
            print(f"⚠ AgentCore Memory not available: {e}")
    else:
        print("⚠ AGENTCORE_MEMORY_ID not set - memory features disabled")

    # Load workflows
    workflows = WORKFLOW_REGISTRY.list_workflows()
    print(f"✓ Loaded {len(workflows)} workflows")

    yield

    # Shutdown
    print("Shutting down DataOps Agent API...")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="DataOps Agent API",
    description="AI-powered data engineering workflow orchestration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    checks = {
        "orchestrator": True,
        "workflow_registry": len(WORKFLOW_REGISTRY.list_workflows()) > 0,
        "agentcore_memory": bool(os.getenv("AGENTCORE_MEMORY_ID"))
    }

    return HealthResponse(
        status="healthy" if all(checks.values()) else "degraded",
        version="1.0.0",
        environment=os.getenv("ENVIRONMENT", "development"),
        timestamp=datetime.utcnow().isoformat(),
        checks=checks
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "DataOps Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# ============================================================================
# Workflow Endpoints
# ============================================================================

@app.get("/api/v1/workflows", response_model=WorkflowListResponse)
async def list_workflows():
    """List all available workflows"""
    workflows = WORKFLOW_REGISTRY.list_workflows()
    workflow_info = []

    for workflow_name in workflows:
        metadata = WORKFLOW_REGISTRY.get_metadata(workflow_name)
        if metadata:
            workflow_info.append({
                "name": metadata.name,
                "description": metadata.description,
                "category": metadata.category,
                "version": metadata.version,
                "capabilities": metadata.capabilities,
                "required_inputs": [
                    {
                        "name": param.name,
                        "type": param.type,
                        "description": param.description,
                        "required": param.required
                    }
                    for param in (metadata.required_inputs or [])
                ]
            })

    return WorkflowListResponse(
        workflows=workflow_info,
        count=len(workflow_info)
    )


@app.get("/api/v1/workflows/{workflow_name}")
async def get_workflow_info(workflow_name: str):
    """Get detailed information about a specific workflow"""
    metadata = WORKFLOW_REGISTRY.get_metadata(workflow_name)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")

    return {
        "name": metadata.name,
        "description": metadata.description,
        "category": metadata.category,
        "version": metadata.version,
        "capabilities": metadata.capabilities,
        "required_inputs": [
            {
                "name": param.name,
                "type": param.type,
                "description": param.description,
                "required": param.required,
                "example": param.example
            }
            for param in (metadata.required_inputs or [])
        ],
        "example_queries": metadata.example_queries or []
    }


# ============================================================================
# Chat Endpoints
# ============================================================================

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process chat message through orchestrator.

    This endpoint:
    1. Creates or retrieves session
    2. Adds message to conversation history (if AgentCore enabled)
    3. Invokes orchestrator
    4. Returns response
    """
    # Generate or use existing session ID
    session_id = request.session_id or str(uuid.uuid4())

    # Initialize memory manager if configured
    memory_mgr = None
    memory_id = os.getenv("AGENTCORE_MEMORY_ID")
    if memory_id:
        try:
            memory_mgr = AgentCoreMemoryManager(memory_id=memory_id)

            # Create session if new
            if not request.session_id:
                memory_mgr.create_session(session_id, metadata={
                    "user_id": request.user_id or "anonymous",
                    "created_at": datetime.utcnow().isoformat()
                })

            # Add user message to conversation
            memory_mgr.add_to_conversation(
                session_id=session_id,
                role="user",
                content=request.message,
                metadata=request.metadata
            )
        except Exception as e:
            print(f"Warning: Memory operations failed: {e}")

    # Execute orchestrator
    try:
        orchestrator_input = {
            "user_query": request.message,
            "detected_intent": "",
            "extracted_parameters": {},
            "missing_parameters": [],
            "workflow_result": {},
            "final_response": ""
        }

        # Run orchestrator (blocking for now, could be made async)
        result = await asyncio.to_thread(
            orchestrator_graph.invoke,
            orchestrator_input
        )

        response_text = result.get("final_response", "")
        workflow_result = result.get("workflow_result", {})

        # Add assistant response to conversation
        if memory_mgr:
            try:
                memory_mgr.add_to_conversation(
                    session_id=session_id,
                    role="assistant",
                    content=response_text,
                    metadata={
                        "workflow": result.get("detected_intent"),
                        "success": workflow_result.get("success", False)
                    }
                )
            except Exception as e:
                print(f"Warning: Failed to save assistant response: {e}")

        # Build metadata
        metadata = {
            "workflow": result.get("detected_intent"),
            "success": workflow_result.get("success", False),
            "execution_metadata": workflow_result.get("metadata", {})
        }

        return ChatResponse(
            session_id=session_id,
            response=response_text,
            metadata=metadata,
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Orchestrator error: {str(e)}"
        )


# ============================================================================
# Session Endpoints
# ============================================================================

@app.get("/api/v1/sessions/{session_id}/history")
async def get_session_history(session_id: str, limit: int = 50):
    """Get conversation history for a session"""
    memory_id = os.getenv("AGENTCORE_MEMORY_ID")
    if not memory_id:
        raise HTTPException(
            status_code=503,
            detail="AgentCore Memory not configured"
        )

    try:
        memory_mgr = AgentCoreMemoryManager(memory_id=memory_id)
        history = memory_mgr.get_conversation_history(session_id, limit=limit)

        return {
            "session_id": session_id,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve history: {str(e)}"
        )


@app.delete("/api/v1/sessions/{session_id}")
async def end_session(session_id: str, consolidate: bool = True):
    """End a session"""
    memory_id = os.getenv("AGENTCORE_MEMORY_ID")
    if not memory_id:
        raise HTTPException(
            status_code=503,
            detail="AgentCore Memory not configured"
        )

    try:
        memory_mgr = AgentCoreMemoryManager(memory_id=memory_id)
        memory_mgr.end_session(session_id, consolidate_to_long_term=consolidate)

        return {
            "session_id": session_id,
            "status": "ended",
            "consolidated": consolidate
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to end session: {str(e)}"
        )


# ============================================================================
# WebSocket Endpoint (for streaming)
# ============================================================================

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat responses.

    This enables real-time, bidirectional communication for
    long-running workflows.
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message = data.get("message", "")

            if not message:
                await websocket.send_json({
                    "error": "Empty message"
                })
                continue

            # Send acknowledgment
            await websocket.send_json({
                "type": "ack",
                "session_id": session_id
            })

            # Process message (simplified for now)
            try:
                orchestrator_input = {
                    "user_query": message,
                    "detected_intent": "",
                    "extracted_parameters": {},
                    "missing_parameters": [],
                    "workflow_result": {},
                    "final_response": ""
                }

                result = await asyncio.to_thread(
                    orchestrator_graph.invoke,
                    orchestrator_input
                )

                # Send response
                await websocket.send_json({
                    "type": "response",
                    "session_id": session_id,
                    "response": result.get("final_response", ""),
                    "metadata": {
                        "workflow": result.get("detected_intent"),
                        "success": result.get("workflow_result", {}).get("success", False)
                    }
                })

            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "error": str(e)
                })

    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {session_id}")


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info"
    )

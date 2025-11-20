#!/usr/bin/env python3
"""
Local Development Server for DataOps Agent
==========================================

A simple FastAPI server to interact with LangGraph workflows locally
WITHOUT requiring LangSmith authentication.

Features:
- Direct invocation of all workflows
- MLflow tracing still works
- Simple REST API
- CORS enabled for local web UI
- No external dependencies beyond FastAPI

Usage:
    python local_server.py

Then open:
    http://localhost:8000          - API docs
    http://localhost:8000/chat     - Simple chat UI
"""

import time
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize MLflow (optional - will skip if not installed)
try:
    from infrastructure.observability import initialize_mlflow, is_mlflow_available
    initialize_mlflow()
    MLFLOW_ENABLED = is_mlflow_available()
except ImportError:
    MLFLOW_ENABLED = False

# Import orchestrator and workflows
from core.orchestrator import orchestrator_graph
from core.workflow_registry import WORKFLOW_REGISTRY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DataOps Agent Local Server",
    description="Local development server for LangGraph workflows",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    workflow: Optional[str] = None  # If specified, invoke directly; otherwise use orchestrator


class ChatResponse(BaseModel):
    success: bool
    response: str
    workflow_used: Optional[str] = None
    execution_time: float
    metadata: Optional[Dict[str, Any]] = None
    mlflow_enabled: bool


class WorkflowInvokeRequest(BaseModel):
    workflow_name: str
    state: Dict[str, Any]


class WorkflowInvokeResponse(BaseModel):
    success: bool
    result: Dict[str, Any]
    execution_time: float


@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "service": "DataOps Agent Local Server",
        "status": "running",
        "mlflow_enabled": MLFLOW_ENABLED,
        "available_workflows": WORKFLOW_REGISTRY.list_workflows(),
        "endpoints": {
            "chat": "/chat - Simple chat interface (GET for UI, POST for API)",
            "orchestrator": "/api/orchestrator - Invoke main orchestrator",
            "workflow": "/api/workflow - Invoke specific workflow directly",
            "workflows": "/api/workflows - List all available workflows",
            "docs": "/docs - Interactive API documentation"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mlflow": MLFLOW_ENABLED,
        "workflows_loaded": len(WORKFLOW_REGISTRY.list_workflows())
    }


@app.get("/api/workflows")
async def list_workflows():
    """List all available workflows with metadata"""
    workflows = {}
    for name in WORKFLOW_REGISTRY.list_workflows():
        metadata = WORKFLOW_REGISTRY.get_metadata(name)
        workflows[name] = {
            "name": metadata.name,
            "description": metadata.description,
            "capabilities": metadata.capabilities,
            "example_queries": metadata.example_queries,
            "category": metadata.category
        }
    return workflows


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - uses orchestrator to route to appropriate workflow

    This mimics the behavior of LangGraph Studio but runs locally.
    """
    start_time = time.time()

    try:
        logger.info(f"Received chat message: {request.message}")

        # Prepare orchestrator state
        input_state = {
            "user_query": request.message,
            "detected_intent": "",
            "extracted_parameters": {},
            "missing_parameters": [],
            "workflow_result": {},
            "final_response": ""
        }

        # Invoke orchestrator (automatically traced by MLflow if enabled)
        result = orchestrator_graph.invoke(input_state)

        execution_time = time.time() - start_time

        # Extract metadata from workflow result
        workflow_result = result.get("workflow_result", {})
        metadata = workflow_result.get("metadata", {})
        workflow_used = result.get("detected_intent", "unknown")

        logger.info(f"Chat completed in {execution_time:.2f}s using workflow: {workflow_used}")

        return ChatResponse(
            success=workflow_result.get("success", True),
            response=result.get("final_response", "No response generated"),
            workflow_used=workflow_used,
            execution_time=execution_time,
            metadata=metadata,
            mlflow_enabled=MLFLOW_ENABLED
        )

    except Exception as e:
        logger.error(f"Error in chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflow", response_model=WorkflowInvokeResponse)
async def invoke_workflow(request: WorkflowInvokeRequest):
    """
    Direct workflow invocation endpoint

    Bypasses orchestrator and invokes a specific workflow directly.
    Useful for testing individual workflows.
    """
    start_time = time.time()

    try:
        logger.info(f"Invoking workflow: {request.workflow_name}")

        # Get workflow from registry
        workflow = WORKFLOW_REGISTRY.get_workflow(request.workflow_name)
        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow '{request.workflow_name}' not found"
            )

        # Invoke workflow directly
        result = workflow.invoke(request.state)

        execution_time = time.time() - start_time

        logger.info(f"Workflow {request.workflow_name} completed in {execution_time:.2f}s")

        return WorkflowInvokeResponse(
            success=True,
            result=result,
            execution_time=execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error invoking workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat", response_class=HTMLResponse)
async def chat_ui():
    """
    Simple web-based chat interface

    A basic HTML/JS interface for chatting with the agent locally.
    No external dependencies required.
    """
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>DataOps Agent - Local Chat</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            width: 90%;
            max-width: 800px;
            height: 90vh;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            font-size: 24px;
            font-weight: 600;
        }
        .status {
            display: flex;
            gap: 10px;
            font-size: 12px;
        }
        .status-badge {
            background: rgba(255,255,255,0.2);
            padding: 4px 12px;
            border-radius: 12px;
        }
        .status-badge.active {
            background: #10b981;
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f9fafb;
        }
        .message {
            margin-bottom: 16px;
            animation: slideIn 0.3s ease-out;
        }
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        .message.user {
            text-align: right;
        }
        .message-content {
            display: inline-block;
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 16px;
            word-wrap: break-word;
        }
        .message.user .message-content {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .message.assistant .message-content {
            background: white;
            color: #1f2937;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .message-meta {
            font-size: 11px;
            color: #6b7280;
            margin-top: 4px;
        }
        .input-area {
            padding: 20px;
            background: white;
            border-top: 1px solid #e5e7eb;
        }
        .input-form {
            display: flex;
            gap: 12px;
        }
        #messageInput {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 24px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }
        #messageInput:focus {
            border-color: #667eea;
        }
        #sendButton {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 24px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        #sendButton:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        #sendButton:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            color: #6b7280;
        }
        .loading.active {
            display: block;
        }
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f4f6;
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .info-panel {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 12px;
            margin: 20px;
            border-radius: 8px;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 DataOps Agent</h1>
            <div class="status">
                <span class="status-badge active" id="serverStatus">Server: Online</span>
                <span class="status-badge" id="mlflowStatus">MLflow: Loading...</span>
            </div>
        </div>

        <div class="info-panel">
            💡 <strong>Local Development Mode</strong> - No LangSmith required! All traces logged to MLflow.
            <br>View traces: <code>mlflow ui --backend-store-uri ./mlruns</code> → http://localhost:5000
        </div>

        <div class="messages" id="messages">
            <div class="message assistant">
                <div class="message-content">
                    👋 Hello! I'm your DataOps Agent running locally. Ask me anything!
                    <br><br>
                    Try: "What can you do?" or "Parse JIL dependencies"
                </div>
            </div>
        </div>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <div>Processing...</div>
        </div>

        <div class="input-area">
            <form class="input-form" id="chatForm">
                <input
                    type="text"
                    id="messageInput"
                    placeholder="Type your message..."
                    autocomplete="off"
                    required
                >
                <button type="submit" id="sendButton">Send</button>
            </form>
        </div>
    </div>

    <script>
        const messagesDiv = document.getElementById('messages');
        const chatForm = document.getElementById('chatForm');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const loading = document.getElementById('loading');
        const mlflowStatus = document.getElementById('mlflowStatus');

        // Check MLflow status on load
        fetch('/health')
            .then(r => r.json())
            .then(data => {
                if (data.mlflow) {
                    mlflowStatus.textContent = 'MLflow: Active';
                    mlflowStatus.classList.add('active');
                } else {
                    mlflowStatus.textContent = 'MLflow: Disabled';
                }
            });

        function addMessage(content, role, metadata = null) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;

            let metaHtml = '';
            if (metadata) {
                const parts = [];
                if (metadata.workflow_used) parts.push(`Workflow: ${metadata.workflow_used}`);
                if (metadata.execution_time) parts.push(`${metadata.execution_time.toFixed(2)}s`);
                metaHtml = `<div class="message-meta">${parts.join(' • ')}</div>`;
            }

            messageDiv.innerHTML = `
                <div class="message-content">${content}</div>
                ${metaHtml}
            `;

            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const message = messageInput.value.trim();
            if (!message) return;

            // Add user message
            addMessage(message, 'user');
            messageInput.value = '';

            // Show loading
            loading.classList.add('active');
            sendButton.disabled = true;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message }),
                });

                const data = await response.json();

                if (data.success) {
                    addMessage(data.response, 'assistant', {
                        workflow_used: data.workflow_used,
                        execution_time: data.execution_time
                    });
                } else {
                    addMessage('❌ Error: ' + data.response, 'assistant');
                }

            } catch (error) {
                addMessage('❌ Connection error: ' + error.message, 'assistant');
            } finally {
                loading.classList.remove('active');
                sendButton.disabled = false;
                messageInput.focus();
            }
        });

        // Focus input on load
        messageInput.focus();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*70)
    print("  DataOps Agent - Local Development Server")
    print("="*70)
    print(f"\n✅ Server Status:")
    print(f"   - MLflow Tracing: {'Enabled' if MLFLOW_ENABLED else 'Disabled'}")
    print(f"   - Workflows Loaded: {len(WORKFLOW_REGISTRY.list_workflows())}")
    print(f"\n🌐 Access Points:")
    print(f"   - Chat UI:  http://localhost:8000/chat")
    print(f"   - API Docs: http://localhost:8000/docs")
    print(f"   - Health:   http://localhost:8000/health")

    if MLFLOW_ENABLED:
        print(f"\n📊 MLflow UI:")
        print(f"   Run: mlflow ui --backend-store-uri ./mlruns")
        print(f"   URL: http://localhost:5000")

    print(f"\n🚀 Starting server...")
    print("="*70 + "\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

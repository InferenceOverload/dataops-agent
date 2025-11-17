# AWS Bedrock AgentCore Architecture Design

## Executive Summary

This document outlines the architecture for refactoring the existing LangGraph-based data orchestration system for production deployment on AWS Bedrock AgentCore with full CI/CD automation.

**Migration Goals:**
- From: Manual deployment, no IaC, local-only execution
- To: Fully automated, GitOps-driven deployment of 10-20 workflows with managed infrastructure

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Chat UI      │  │ API Gateway  │  │ CLI Tool     │          │
│  │ (Streamlit)  │  │ (REST/WS)    │  │ (Existing)   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
┌─────────┴──────────────────┴──────────────────┴─────────────────┐
│                    API/Interface Layer                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ FastAPI Application (ECS Fargate / Lambda)               │   │
│  │ - Async workflow invocation                              │   │
│  │ - Streaming support via WebSockets                       │   │
│  │ - Session management                                     │   │
│  └──────────────────────────┬───────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                  LangGraph Orchestration Layer                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Main Orchestrator (Enhanced)                             │   │
│  │ - Intent detection                                       │   │
│  │ - Parameter extraction                                   │   │
│  │ - Workflow routing                                       │   │
│  │ - AgentCore Memory integration                           │   │
│  └──────┬───────────────────────────────────────────────────┘   │
│         │                                                        │
│  ┌──────┴───────────────────────────────────────────┐           │
│  │ Workflow Registry (Auto-discovery)               │           │
│  ├──────────────────────────────────────────────────┤           │
│  │ • JIL Parser Workflow                            │           │
│  │ • Oracle Package Analyzer (v2.0 sub-agent)       │           │
│  │ • Simple/Supervisor/Iterative Workflows          │           │
│  │ • [Future: 10-20 workflows]                      │           │
│  └──────────────────────────────────────────────────┘           │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────┴───────────────────────────────────┐
│                  AWS Bedrock AgentCore Layer                     │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐   │
│  │ AgentCore Memory    │  │ Bedrock Runtime                 │   │
│  ├─────────────────────┤  ├─────────────────────────────────┤   │
│  │ • Short-term Memory │  │ • Claude Models (Sonnet 4)      │   │
│  │   (Conversations)   │  │ • Model Invocation              │   │
│  │ • Long-term Memory  │  │ • Streaming Support             │   │
│  │   (Cross-session)   │  └─────────────────────────────────┘   │
│  │ • Namespace Mgmt    │                                        │
│  │ • Auto-consolidation│                                        │
│  └─────────────────────┘                                        │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────┴───────────────────────────────────┐
│                   Infrastructure Services Layer                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ S3       │  │ DynamoDB │  │ Oracle   │  │ Secrets  │        │
│  │ (Artifact│  │ (State & │  │ RDS      │  │ Manager  │        │
│  │  Storage)│  │ Metadata)│  │ (Source) │  │          │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ CloudWatch│ │ X-Ray    │  │ VPC      │  │ IAM      │        │
│  │ (Logs)   │  │ (Trace)  │  │ (Network)│  │ (Auth)   │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                     CI/CD Pipeline (GitHub Actions)              │
│  Build → Test → Package → Deploy → Verify → Tag                 │
└──────────────────────────────────────────────────────────────────┘
```

## 2. AWS Bedrock AgentCore Integration

### 2.1 Memory Architecture

**Short-Term Memory (Session-based):**
- **Purpose**: Multi-turn conversations within a single workflow execution
- **Lifecycle**: Created per session, expires after session ends
- **Storage**: AgentCore Memory service
- **Use Case**: Chat history, intermediate results, context accumulation

**Long-Term Memory (Cross-session):**
- **Purpose**: Persistent knowledge across multiple sessions and workflows
- **Lifecycle**: Permanent until explicitly deleted
- **Storage**: AgentCore Memory with S3 backing for large artifacts
- **Use Case**: Workflow results, learned patterns, user preferences, cross-workflow knowledge

**Namespace Strategy:**
```
/dataops-agent/{environment}/
├── /sessions/{session_id}/          # Short-term memory
│   ├── conversation_history
│   ├── extracted_parameters
│   └── workflow_state
└── /persistent/                      # Long-term memory
    ├── /workflows/{workflow_name}/
    │   └── execution_history
    ├── /users/{user_id}/
    │   └── preferences
    └── /knowledge/
        ├── jil_dependencies
        ├── oracle_lineage
        └── workflow_patterns
```

### 2.2 AgentCore Memory API Integration

```python
# infrastructure/agentcore/memory_manager.py

from typing import Dict, List, Optional, Any
import boto3
from datetime import datetime

class AgentCoreMemoryManager:
    """Manages short-term and long-term memory via AWS Bedrock AgentCore"""

    def __init__(
        self,
        memory_id: str,
        region: str = "us-east-1",
        environment: str = "production"
    ):
        self.client = boto3.client('bedrock-agent-runtime', region_name=region)
        self.memory_id = memory_id
        self.environment = environment

    # Short-term memory operations
    def create_session(self, session_id: str) -> Dict[str, Any]:
        """Create a new session with short-term memory"""
        namespace = f"/dataops-agent/{self.environment}/sessions/{session_id}"
        return self.client.create_session(
            memoryId=self.memory_id,
            sessionId=session_id,
            namespace=namespace
        )

    def add_to_conversation(
        self,
        session_id: str,
        role: str,  # 'user' | 'assistant' | 'system'
        content: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Add message to session conversation history"""
        return self.client.put_memory(
            memoryId=self.memory_id,
            sessionId=session_id,
            memoryType='SHORT_TERM',
            content={
                'role': role,
                'content': content,
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': metadata or {}
            }
        )

    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve conversation history for a session"""
        response = self.client.get_memory(
            memoryId=self.memory_id,
            sessionId=session_id,
            memoryType='SHORT_TERM',
            maxResults=limit
        )
        return response.get('memories', [])

    # Long-term memory operations
    def store_workflow_result(
        self,
        workflow_name: str,
        execution_id: str,
        result: Dict[str, Any],
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Store workflow execution result in long-term memory"""
        namespace = f"/dataops-agent/{self.environment}/persistent/workflows/{workflow_name}"
        return self.client.put_memory(
            memoryId=self.memory_id,
            memoryType='LONG_TERM',
            namespace=namespace,
            content={
                'execution_id': execution_id,
                'workflow_name': workflow_name,
                'result': result,
                'timestamp': datetime.utcnow().isoformat(),
                'tags': tags or []
            }
        )

    def retrieve_workflow_knowledge(
        self,
        workflow_name: str,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant workflow knowledge from long-term memory"""
        namespace = f"/dataops-agent/{self.environment}/persistent/workflows/{workflow_name}"
        params = {
            'memoryId': self.memory_id,
            'memoryType': 'LONG_TERM',
            'namespace': namespace,
            'maxResults': limit
        }

        if query:
            params['searchQuery'] = query
        if tags:
            params['tags'] = tags

        response = self.client.query_memory(**params)
        return response.get('memories', [])

    def end_session(self, session_id: str) -> None:
        """End session and optionally consolidate to long-term memory"""
        # AgentCore can auto-consolidate based on policy
        self.client.delete_session(
            memoryId=self.memory_id,
            sessionId=session_id,
            consolidateToLongTerm=True  # Policy-driven consolidation
        )
```

### 2.3 Enhanced Orchestrator with Memory

```python
# core/orchestrator_v2.py (Enhanced for AgentCore)

from infrastructure.agentcore.memory_manager import AgentCoreMemoryManager
from typing import TypedDict, Optional
import uuid

class OrchestratorStateV2(TypedDict):
    """Enhanced state with session management"""
    session_id: str               # Session identifier
    user_query: str
    detected_intent: str
    extracted_parameters: dict
    conversation_history: list    # Retrieved from AgentCore
    workflow_result: dict
    final_response: str
    memory_context: dict          # Long-term memory context

def create_session_node(state: OrchestratorStateV2) -> dict:
    """Initialize session with AgentCore Memory"""
    session_id = state.get('session_id') or str(uuid.uuid4())

    # Initialize memory manager
    memory_mgr = AgentCoreMemoryManager(
        memory_id=os.getenv('AGENTCORE_MEMORY_ID'),
        environment=os.getenv('ENVIRONMENT', 'production')
    )

    # Create session
    memory_mgr.create_session(session_id)

    # Add user query to conversation
    memory_mgr.add_to_conversation(
        session_id=session_id,
        role='user',
        content=state['user_query']
    )

    # Retrieve conversation history
    history = memory_mgr.get_conversation_history(session_id)

    return {
        'session_id': session_id,
        'conversation_history': history
    }

def enhanced_workflow_invocation_node(state: OrchestratorStateV2) -> dict:
    """Invoke workflow with memory context"""
    memory_mgr = AgentCoreMemoryManager(
        memory_id=os.getenv('AGENTCORE_MEMORY_ID')
    )

    # Retrieve relevant long-term knowledge
    workflow_knowledge = memory_mgr.retrieve_workflow_knowledge(
        workflow_name=state['detected_intent'],
        query=state['user_query'],
        limit=5
    )

    # Add knowledge to workflow input
    workflow_input = {
        **state.get('extracted_parameters', {}),
        'memory_context': workflow_knowledge,
        'conversation_history': state.get('conversation_history', [])
    }

    # Execute workflow (existing logic)
    result = execute_workflow(state['detected_intent'], workflow_input)

    # Store result in long-term memory
    if result.get('success'):
        memory_mgr.store_workflow_result(
            workflow_name=state['detected_intent'],
            execution_id=str(uuid.uuid4()),
            result=result,
            tags=[state['detected_intent'], 'production']
        )

    # Add assistant response to conversation
    memory_mgr.add_to_conversation(
        session_id=state['session_id'],
        role='assistant',
        content=result.get('output', ''),
        metadata={'workflow': state['detected_intent']}
    )

    return {'workflow_result': result}
```

## 3. Infrastructure as Code (Terraform)

### 3.1 Directory Structure

```
infrastructure/
├── terraform/
│   ├── environments/
│   │   ├── dev/
│   │   │   ├── main.tf
│   │   │   ├── terraform.tfvars
│   │   │   └── backend.tf
│   │   ├── staging/
│   │   └── production/
│   ├── modules/
│   │   ├── agentcore/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── ecs/
│   │   ├── networking/
│   │   ├── storage/
│   │   └── observability/
│   └── shared/
│       ├── variables.tf
│       └── backend.tf
└── cloudformation/  # Alternative/supplementary
    └── agentcore-stack.yaml
```

### 3.2 Core Terraform Modules

**AgentCore Memory Module** (`modules/agentcore/main.tf`):
```hcl
# AWS Bedrock AgentCore Memory
resource "aws_bedrockagent_memory" "main" {
  name        = "${var.project_name}-${var.environment}-memory"
  description = "Memory storage for ${var.project_name} agents"

  memory_configuration {
    type = "AGENT_MEMORY"

    storage_configuration {
      s3_bucket_name = aws_s3_bucket.memory_storage.id
      kms_key_id     = aws_kms_key.memory_encryption.arn
    }

    retention_policy {
      short_term_retention_days = 7
      long_term_enabled         = true
    }
  }

  tags = var.tags
}

# S3 bucket for memory storage
resource "aws_s3_bucket" "memory_storage" {
  bucket = "${var.project_name}-${var.environment}-agentcore-memory"

  tags = var.tags
}

resource "aws_s3_bucket_versioning" "memory_storage" {
  bucket = aws_s3_bucket.memory_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "memory_storage" {
  bucket = aws_s3_bucket.memory_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.memory_encryption.arn
    }
  }
}

# KMS key for encryption
resource "aws_kms_key" "memory_encryption" {
  description             = "KMS key for AgentCore memory encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = var.tags
}

output "memory_id" {
  value       = aws_bedrockagent_memory.main.id
  description = "AgentCore Memory ID"
}

output "memory_arn" {
  value       = aws_bedrockagent_memory.main.arn
  description = "AgentCore Memory ARN"
}
```

**ECS Fargate Module** (`modules/ecs/main.tf`):
```hcl
# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = var.tags
}

# Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project_name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "api"
    image = "${var.ecr_repository_url}:${var.image_tag}"

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = [
      {
        name  = "ENVIRONMENT"
        value = var.environment
      },
      {
        name  = "AGENTCORE_MEMORY_ID"
        value = var.agentcore_memory_id
      },
      {
        name  = "LLM_PROVIDER"
        value = "bedrock"
      }
    ]

    secrets = [
      {
        name      = "DATABASE_URL"
        valueFrom = aws_secretsmanager_secret.db_url.arn
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])

  tags = var.tags
}

# ECS Service
resource "aws_ecs_service" "api" {
  name            = "${var.project_name}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.alb_target_group_arn
    container_name   = "api"
    container_port   = 8000
  }

  depends_on = [var.alb_listener]

  tags = var.tags
}
```

## 4. Containerization

### 4.1 Multi-stage Dockerfile

```dockerfile
# Dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install UV package manager
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /build/.venv /app/.venv

# Copy application code
COPY core/ /app/core/
COPY workflows/ /app/workflows/
COPY infrastructure/ /app/infrastructure/
COPY cli/ /app/cli/
COPY langgraph.json /app/

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4.2 Docker Compose for Local Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - LLM_PROVIDER=anthropic
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./core:/app/core
      - ./workflows:/app/workflows
      - ./infrastructure:/app/infrastructure
    depends_on:
      - postgres
      - redis
    networks:
      - dataops-network

  chat-ui:
    build:
      context: .
      dockerfile: Dockerfile.streamlit
    ports:
      - "8501:8501"
    environment:
      - API_URL=http://api:8000
    depends_on:
      - api
    networks:
      - dataops-network

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=dataops
      - POSTGRES_USER=dataops
      - POSTGRES_PASSWORD=local_dev_password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - dataops-network

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    networks:
      - dataops-network

networks:
  dataops-network:
    driver: bridge

volumes:
  postgres-data:
  redis-data:
```

## 5. CI/CD Pipeline

### 5.1 GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop, 'claude/*']
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: dataops-agent

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install UV
        run: pip install uv

      - name: Install dependencies
        run: uv sync

      - name: Run linting
        run: |
          uv run ruff check .
          uv run black --check .
          uv run mypy .

      - name: Run tests
        run: uv run pytest --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Docker meta
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=semver,pattern={{version}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy-dev:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: development

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster dataops-agent-dev \
            --service dataops-agent-api \
            --force-new-deployment

  deploy-prod:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster dataops-agent-production \
            --service dataops-agent-api \
            --force-new-deployment

      - name: Verify deployment
        run: |
          aws ecs wait services-stable \
            --cluster dataops-agent-production \
            --services dataops-agent-api
```

## 6. Simple Chat Interface (Streamlit)

```python
# chat_ui/app.py
import streamlit as st
import requests
from typing import Dict, Any

st.set_page_config(
    page_title="DataOps Agent",
    page_icon="🤖",
    layout="wide"
)

# API configuration
API_URL = st.secrets.get("API_URL", "http://localhost:8000")

st.title("🤖 DataOps Agent Chat")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "metadata" in message:
            with st.expander("Execution Details"):
                st.json(message["metadata"])

# Chat input
if prompt := st.chat_input("Ask me anything about your data workflows..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call API
    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            response = requests.post(
                f"{API_URL}/api/v1/chat",
                json={
                    "message": prompt,
                    "session_id": st.session_state.session_id
                }
            )

            if response.status_code == 200:
                data = response.json()

                # Update session ID
                if not st.session_state.session_id:
                    st.session_state.session_id = data.get("session_id")

                # Display response
                st.markdown(data["response"])

                # Store message
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": data["response"],
                    "metadata": data.get("metadata", {})
                })

                # Show metadata
                if data.get("metadata"):
                    with st.expander("Execution Details"):
                        st.json(data["metadata"])
            else:
                st.error(f"Error: {response.status_code}")

# Sidebar
with st.sidebar:
    st.header("Session Info")
    if st.session_state.session_id:
        st.text(f"Session: {st.session_state.session_id[:8]}...")
    else:
        st.text("No active session")

    if st.button("New Session"):
        st.session_state.session_id = None
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.header("Workflows")
    workflows_response = requests.get(f"{API_URL}/api/v1/workflows")
    if workflows_response.status_code == 200:
        workflows = workflows_response.json()
        for wf in workflows:
            st.text(f"• {wf['name']}")
```

## 7. Migration Strategy

### Phase 1: Foundation (Weeks 1-2)
1. Set up AWS infrastructure with Terraform
   - VPC, subnets, security groups
   - AgentCore Memory setup
   - S3 buckets, DynamoDB tables
   - IAM roles and policies

2. Containerize application
   - Create Dockerfile
   - Set up ECR repository
   - Build and push initial image

3. Set up CI/CD pipeline
   - GitHub Actions workflows
   - Automated testing
   - ECR integration

### Phase 2: Memory Integration (Weeks 3-4)
1. Implement AgentCore Memory Manager
2. Update orchestrator for session management
3. Migrate existing workflows to use memory context
4. Add memory consolidation policies

### Phase 3: API & Interface (Weeks 5-6)
1. Build FastAPI application
2. Implement async workflow execution
3. Add WebSocket support for streaming
4. Deploy Streamlit chat interface

### Phase 4: Production Deployment (Weeks 7-8)
1. Deploy to dev environment
2. Integration testing
3. Performance testing and optimization
4. Production deployment
5. Monitoring and observability setup

### Phase 5: Workflow Migration (Weeks 9-12)
1. Migrate existing 5 workflows
2. Add 5-15 new workflows
3. Optimize for production workloads
4. Documentation and training

## 8. Cost Optimization

- **AgentCore Memory**: Pay per GB stored + API calls
- **ECS Fargate**: Right-size tasks (start with 0.5 vCPU, 1GB RAM)
- **S3**: Use lifecycle policies (Intelligent-Tiering)
- **Bedrock**: Use streaming to reduce token costs
- **CloudWatch**: Set log retention policies (30 days dev, 90 days prod)

## 9. Security Considerations

- All data encrypted at rest (KMS)
- Encrypted in transit (TLS 1.3)
- VPC with private subnets for ECS tasks
- PrivateLink for Bedrock access
- Secrets Manager for credentials
- IAM roles with least privilege
- CloudTrail for audit logging

## 10. Observability

- **CloudWatch Logs**: Centralized logging
- **X-Ray**: Distributed tracing
- **CloudWatch Metrics**: Custom metrics
- **CloudWatch Alarms**: Error rates, latency
- **MLflow**: Workflow-specific tracing (preserved)

## Next Steps

1. Review and approve architecture
2. Set up AWS account and permissions
3. Initialize Terraform state backend
4. Begin Phase 1 implementation

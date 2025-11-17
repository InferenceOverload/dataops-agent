# DataOps Agent Deployment Guide

Complete guide for deploying the DataOps Agent system to AWS with Bedrock AgentCore.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [AWS Infrastructure Setup](#aws-infrastructure-setup)
4. [CI/CD Pipeline Configuration](#cicd-pipeline-configuration)
5. [Production Deployment](#production-deployment)
6. [Monitoring & Observability](#monitoring--observability)
7. [Troubleshooting](#troubleshooting)
8. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### Required Tools

- **AWS CLI** v2.x or later
- **Terraform** v1.5.0 or later
- **Docker** v24.0 or later
- **Docker Compose** v2.x or later
- **Python** 3.11 or later
- **UV** package manager
- **Git**

### AWS Account Requirements

- AWS account with appropriate permissions
- Bedrock AgentCore enabled in your region
- ECR repository access
- ECS cluster creation permissions
- VPC creation permissions

### Required AWS Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agent:*",
        "bedrock-agent-runtime:*",
        "ecs:*",
        "ecr:*",
        "ec2:*",
        "s3:*",
        "dynamodb:*",
        "iam:*",
        "kms:*",
        "logs:*",
        "cloudwatch:*",
        "elasticloadbalancing:*"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Local Development Setup

### 1. Clone Repository

```bash
git checkout -b claude/langgraph-bedrock-refactor-013mkeJ7XiNtmKQgimZ4cnQc
```

### 2. Install Dependencies

```bash
# Install UV
pip install uv

# Install project dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

Required environment variables:

```bash
# LLM Configuration
LLM_PROVIDER=anthropic  # or bedrock for production
ANTHROPIC_API_KEY=your_api_key_here

# AWS Configuration (for Bedrock)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# AgentCore Memory (after infrastructure deployment)
AGENTCORE_MEMORY_ID=your_memory_id_here

# Environment
ENVIRONMENT=development
```

### 4. Start Local Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

Services:
- **API**: http://localhost:8000
- **Chat UI**: http://localhost:8501
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **MLflow**: http://localhost:5000

### 5. Test Local Setup

```bash
# Health check
curl http://localhost:8000/health

# List workflows
curl http://localhost:8000/api/v1/workflows

# Test chat (via UI)
open http://localhost:8501
```

---

## AWS Infrastructure Setup

### 1. Create S3 Bucket for Terraform State

```bash
# Create bucket
aws s3 mb s3://dataops-agent-terraform-state --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket dataops-agent-terraform-state \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket dataops-agent-terraform-state \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name dataops-agent-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 2. Deploy Infrastructure (Development)

```bash
cd infrastructure/terraform/environments/dev

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Apply infrastructure
terraform apply

# Save outputs
terraform output -json > outputs.json
```

### 3. Create AgentCore Memory

**Note**: AgentCore Memory creation may require AWS CLI or Console as Terraform support is limited.

```bash
# Create memory via AWS CLI
aws bedrock-agent create-agent-memory \
  --agent-memory-name dataops-agent-dev \
  --description "Agent memory for DataOps Agent development" \
  --memory-configuration '{
    "type": "AGENT_MEMORY",
    "storageConfiguration": {
      "s3BucketName": "dataops-agent-dev-agentcore-memory",
      "kmsKeyId": "alias/dataops-agent-dev-memory"
    },
    "retentionPolicy": {
      "shortTermRetentionDays": 7,
      "longTermEnabled": true
    }
  }' \
  --region us-east-1 \
  --output json > agentcore-memory.json

# Extract memory ID
MEMORY_ID=$(jq -r '.agentMemoryId' agentcore-memory.json)

# Update SSM parameter
aws ssm put-parameter \
  --name "/dataops-agent/dev/agentcore/memory-id" \
  --value "$MEMORY_ID" \
  --type String \
  --overwrite \
  --region us-east-1
```

### 4. Create ECR Repository

```bash
# Create repository
aws ecr create-repository \
  --repository-name dataops-agent \
  --region us-east-1 \
  --output json

# Create repository for chat UI
aws ecr create-repository \
  --repository-name dataops-agent-chat \
  --region us-east-1 \
  --output json
```

### 5. Build and Push Initial Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t dataops-agent:latest .

# Tag image
docker tag dataops-agent:latest \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/dataops-agent:latest

# Push image
docker push \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/dataops-agent:latest
```

---

## CI/CD Pipeline Configuration

### 1. GitHub Secrets

Configure the following secrets in your GitHub repository:

**Settings → Secrets and variables → Actions → New repository secret**

```
AWS_ACCESS_KEY_ID=<your-access-key>
AWS_SECRET_ACCESS_KEY=<your-secret-key>
AWS_PROD_ACCESS_KEY_ID=<production-access-key>
AWS_PROD_SECRET_ACCESS_KEY=<production-secret-key>
```

### 2. GitHub Environments

Create the following environments with protection rules:

**Development:**
- No protection rules
- Auto-deploy on push to `develop` or `claude/*` branches

**Staging:**
- Requires approval from 1 reviewer
- Auto-deploy on push to `main` after approval

**Production:**
- Requires approval from 2 reviewers
- Auto-deploy after staging deployment succeeds

### 3. Test CI/CD Pipeline

```bash
# Push to trigger pipeline
git add .
git commit -m "feat: Initial AgentCore integration"
git push -u origin claude/langgraph-bedrock-refactor-013mkeJ7XiNtmKQgimZ4cnQc

# Monitor workflow
# Visit: https://github.com/<owner>/<repo>/actions
```

---

## Production Deployment

### 1. Deploy Production Infrastructure

```bash
cd infrastructure/terraform/environments/production

# Initialize
terraform init

# Plan
terraform plan -out=tfplan

# Review plan carefully
terraform show tfplan

# Apply
terraform apply tfplan
```

### 2. Create Production AgentCore Memory

```bash
aws bedrock-agent create-agent-memory \
  --agent-memory-name dataops-agent-production \
  --description "Agent memory for DataOps Agent production" \
  --memory-configuration '{
    "type": "AGENT_MEMORY",
    "storageConfiguration": {
      "s3BucketName": "dataops-agent-production-agentcore-memory",
      "kmsKeyId": "alias/dataops-agent-production-memory"
    },
    "retentionPolicy": {
      "shortTermRetentionDays": 7,
      "longTermEnabled": true
    }
  }' \
  --region us-east-1 \
  --output json > agentcore-memory-prod.json

# Update SSM parameter
MEMORY_ID=$(jq -r '.agentMemoryId' agentcore-memory-prod.json)
aws ssm put-parameter \
  --name "/dataops-agent/production/agentcore/memory-id" \
  --value "$MEMORY_ID" \
  --type String \
  --overwrite \
  --region us-east-1
```

### 3. Deploy via CI/CD

```bash
# Merge to main branch
git checkout main
git merge claude/langgraph-bedrock-refactor-013mkeJ7XiNtmKQgimZ4cnQc
git push origin main

# CI/CD will automatically:
# 1. Run tests
# 2. Build Docker images
# 3. Push to ECR
# 4. Deploy to staging
# 5. Wait for approval
# 6. Deploy to production
```

### 4. Verify Production Deployment

```bash
# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --region us-east-1 \
  --query 'LoadBalancers[?contains(LoadBalancerName, `dataops-agent-production`)].DNSName' \
  --output text)

# Health check
curl https://${ALB_DNS}/health

# Test API
curl https://${ALB_DNS}/api/v1/workflows

# Test chat interface
open https://${ALB_DNS}
```

---

## Monitoring & Observability

### 1. CloudWatch Dashboard

Access CloudWatch dashboards for monitoring:

```bash
# Open CloudWatch console
open "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=dataops-agent-production"
```

Key metrics to monitor:
- **API Latency**: p50, p95, p99
- **Error Rate**: 4xx, 5xx errors
- **ECS Task Health**: Running/Pending/Failed tasks
- **Memory Usage**: Short-term and long-term memory
- **Workflow Execution Time**: Per workflow type

### 2. CloudWatch Alarms

Pre-configured alarms:
- High error rate (> 5%)
- High latency (p95 > 5s)
- Task failures
- Memory exhaustion

### 3. X-Ray Tracing

View distributed traces:

```bash
open "https://console.aws.amazon.com/xray/home?region=us-east-1#/traces"
```

### 4. MLflow Tracking

View workflow execution traces:

```bash
# Local MLflow
open http://localhost:5000

# Production MLflow (if deployed)
# Access via internal URL or VPN
```

---

## Troubleshooting

### Issue: ECS Tasks Not Starting

**Symptoms**: Tasks in PENDING state indefinitely

**Diagnosis**:
```bash
# Check task status
aws ecs describe-tasks \
  --cluster dataops-agent-production \
  --tasks $(aws ecs list-tasks --cluster dataops-agent-production --query 'taskArns[0]' --output text) \
  --region us-east-1

# Check CloudWatch logs
aws logs tail /aws/ecs/dataops-agent-production --follow
```

**Solutions**:
1. Check IAM role permissions
2. Verify ECR image exists
3. Check security group rules
4. Verify subnet configuration

### Issue: AgentCore Memory Not Working

**Symptoms**: `AGENTCORE_MEMORY_ID not set` warnings

**Diagnosis**:
```bash
# Check SSM parameter
aws ssm get-parameter \
  --name "/dataops-agent/production/agentcore/memory-id" \
  --region us-east-1

# Check environment variables in task definition
aws ecs describe-task-definition \
  --task-definition dataops-agent-api \
  --region us-east-1 \
  --query 'taskDefinition.containerDefinitions[0].environment'
```

**Solutions**:
1. Verify AgentCore Memory was created
2. Update SSM parameter with correct memory ID
3. Update ECS task definition environment variables
4. Force new deployment

### Issue: High Latency

**Symptoms**: API responses taking > 10 seconds

**Diagnosis**:
```bash
# Check ECS metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=dataops-agent-api Name=ClusterName,Value=dataops-agent-production \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region us-east-1
```

**Solutions**:
1. Scale up ECS tasks
2. Increase task CPU/memory
3. Enable caching (Redis)
4. Optimize workflow code

---

## Rollback Procedures

### Rollback ECS Deployment

```bash
# List recent task definitions
aws ecs list-task-definitions \
  --family-prefix dataops-agent-api \
  --sort DESC \
  --max-items 5 \
  --region us-east-1

# Rollback to previous version
PREVIOUS_TASK_DEF="dataops-agent-api:123"  # Replace with actual version

aws ecs update-service \
  --cluster dataops-agent-production \
  --service dataops-agent-api \
  --task-definition $PREVIOUS_TASK_DEF \
  --force-new-deployment \
  --region us-east-1

# Wait for deployment
aws ecs wait services-stable \
  --cluster dataops-agent-production \
  --services dataops-agent-api \
  --region us-east-1
```

### Rollback Terraform Changes

```bash
cd infrastructure/terraform/environments/production

# View state history
terraform state list

# Rollback to specific state version (from S3)
aws s3api list-object-versions \
  --bucket dataops-agent-terraform-state \
  --prefix production/terraform.tfstate

# Download previous version
aws s3api get-object \
  --bucket dataops-agent-terraform-state \
  --key production/terraform.tfstate \
  --version-id <version-id> \
  terraform.tfstate.backup

# Restore
cp terraform.tfstate.backup terraform.tfstate

# Apply previous configuration
terraform apply
```

---

## Appendix

### A. Environment Variables Reference

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `LLM_PROVIDER` | Yes | LLM provider (anthropic or bedrock) | anthropic |
| `ANTHROPIC_API_KEY` | If using Anthropic | API key | - |
| `AWS_REGION` | Yes | AWS region | us-east-1 |
| `AGENTCORE_MEMORY_ID` | Yes | AgentCore Memory ID | - |
| `ENVIRONMENT` | Yes | Environment name | development |
| `DATABASE_URL` | No | PostgreSQL connection string | - |
| `REDIS_URL` | No | Redis connection string | - |

### B. Port Reference

| Service | Port | Protocol |
|---------|------|----------|
| API | 8000 | HTTP |
| Chat UI | 8501 | HTTP |
| PostgreSQL | 5432 | TCP |
| Redis | 6379 | TCP |
| MLflow | 5000 | HTTP |

### C. Resource Limits

**Development:**
- ECS Tasks: 2
- Task CPU: 0.5 vCPU
- Task Memory: 1024 MB

**Production:**
- ECS Tasks: 4 (auto-scaling to 10)
- Task CPU: 1 vCPU
- Task Memory: 2048 MB

### D. Cost Estimates

**Monthly costs (production):**
- ECS Fargate (4 tasks): ~$120
- ALB: ~$22
- NAT Gateway: ~$32
- AgentCore Memory (50GB): ~$50
- S3 Storage (500GB): ~$12
- CloudWatch Logs: ~$10
- Data Transfer: ~$20

**Total**: ~$266/month

### E. Support & Contacts

- **Documentation**: `/docs`
- **Issues**: GitHub Issues
- **Emergency**: On-call rotation (PagerDuty)

---

**Last Updated**: 2025-11-17
**Version**: 1.0.0

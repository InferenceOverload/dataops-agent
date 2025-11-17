# Terraform Infrastructure for DataOps Agent

This directory contains Terraform configuration for deploying the DataOps Agent system to AWS with Bedrock AgentCore.

## Directory Structure

```
terraform/
├── environments/         # Environment-specific configurations
│   ├── dev/
│   ├── staging/
│   └── production/
├── modules/             # Reusable Terraform modules
│   ├── agentcore/       # AgentCore Memory resources
│   ├── ecs/             # ECS Fargate cluster and services
│   ├── networking/      # VPC, subnets, security groups
│   ├── storage/         # S3 buckets, DynamoDB tables
│   └── observability/   # CloudWatch, X-Ray
└── shared/              # Shared variables and backend config
```

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.5.0
3. **S3 bucket** for Terraform state (create manually first)
4. **AWS permissions** for creating:
   - VPC and networking resources
   - ECS cluster and services
   - Bedrock AgentCore Memory
   - S3 buckets and DynamoDB tables
   - IAM roles and policies
   - CloudWatch logs and metrics

## Quick Start

### 1. Initialize Terraform State Backend

First, create an S3 bucket for Terraform state:

```bash
aws s3 mb s3://dataops-agent-terraform-state --region us-east-1
aws s3api put-bucket-versioning \
  --bucket dataops-agent-terraform-state \
  --versioning-configuration Status=Enabled
```

### 2. Deploy Development Environment

```bash
cd environments/dev
terraform init
terraform plan
terraform apply
```

### 3. Deploy Production Environment

```bash
cd environments/production
terraform init
terraform plan
terraform apply
```

## Module Documentation

### AgentCore Module

Creates AWS Bedrock AgentCore Memory resources:
- AgentCore Memory instance
- S3 bucket for memory storage
- KMS key for encryption
- IAM roles and policies

**Usage:**
```hcl
module "agentcore" {
  source = "../../modules/agentcore"

  project_name = "dataops-agent"
  environment  = "production"

  tags = {
    Project     = "dataops-agent"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}
```

### ECS Module

Creates ECS Fargate resources:
- ECS cluster
- Task definitions
- ECS services
- Application Load Balancer
- Auto-scaling policies

**Usage:**
```hcl
module "ecs" {
  source = "../../modules/ecs"

  project_name          = "dataops-agent"
  environment           = "production"
  vpc_id                = module.networking.vpc_id
  private_subnet_ids    = module.networking.private_subnet_ids
  public_subnet_ids     = module.networking.public_subnet_ids
  agentcore_memory_id   = module.agentcore.memory_id

  # Task configuration
  task_cpu              = 512
  task_memory           = 1024
  desired_count         = 2

  tags = var.tags
}
```

### Networking Module

Creates VPC and networking resources:
- VPC with public and private subnets
- NAT Gateway
- Internet Gateway
- Security groups
- VPC endpoints for AWS services

### Storage Module

Creates storage resources:
- S3 buckets for artifacts
- DynamoDB tables for metadata
- Lifecycle policies

### Observability Module

Creates monitoring resources:
- CloudWatch Log Groups
- CloudWatch Dashboards
- CloudWatch Alarms
- X-Ray sampling rules

## Environment Variables

Each environment requires these variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `aws_region` | AWS region | Yes |
| `project_name` | Project name prefix | Yes |
| `environment` | Environment name | Yes |
| `vpc_cidr` | VPC CIDR block | Yes |
| `availability_zones` | List of AZs | Yes |
| `ecr_image_tag` | Docker image tag | Yes |

## Outputs

After successful deployment, Terraform outputs:

- `agentcore_memory_id` - AgentCore Memory ID
- `ecs_cluster_name` - ECS cluster name
- `alb_dns_name` - Load balancer DNS name
- `api_endpoint` - API endpoint URL

## Cost Estimation

Approximate monthly costs for production deployment:

- **ECS Fargate (2 tasks, 0.5 vCPU, 1GB RAM)**: ~$30
- **Application Load Balancer**: ~$22
- **NAT Gateway**: ~$32
- **AgentCore Memory (10GB)**: ~$10
- **S3 storage (100GB)**: ~$2.30
- **DynamoDB (on-demand)**: Variable
- **CloudWatch Logs (10GB)**: ~$5
- **Data transfer**: Variable

**Total**: ~$100-150/month (baseline)

## Security

- All data encrypted at rest using KMS
- VPC endpoints for private AWS service access
- Security groups with least-privilege access
- IAM roles with minimal permissions
- Secrets stored in AWS Secrets Manager

## Maintenance

### Updating Infrastructure

```bash
cd environments/<environment>
terraform plan
terraform apply
```

### Destroying Resources

**WARNING**: This will delete all resources!

```bash
cd environments/<environment>
terraform destroy
```

### State Management

State is stored in S3 with versioning enabled. To recover from state issues:

```bash
# List state versions
aws s3api list-object-versions --bucket dataops-agent-terraform-state

# Restore specific version
aws s3api get-object --bucket dataops-agent-terraform-state \
  --key <environment>/terraform.tfstate \
  --version-id <version-id> \
  terraform.tfstate
```

## Troubleshooting

### AgentCore Memory Not Created

Ensure you have enabled Bedrock AgentCore in your AWS account:

```bash
aws bedrock-agent create-agent-memory \
  --agent-memory-name test \
  --region us-east-1
```

### ECS Tasks Not Starting

Check CloudWatch logs:

```bash
aws logs tail /aws/ecs/dataops-agent-production --follow
```

### Permission Issues

Verify IAM role has required permissions:

```bash
aws iam get-role --role-name dataops-agent-production-ecs-task
```

## References

- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [ECS Fargate Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

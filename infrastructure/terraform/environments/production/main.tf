# Production Environment Configuration

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "dataops-agent-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "dataops-agent-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "dataops-agent"
      Environment = "production"
      ManagedBy   = "terraform"
    }
  }
}

# Local variables
locals {
  environment  = "production"
  project_name = "dataops-agent"

  tags = {
    Project     = local.project_name
    Environment = local.environment
    ManagedBy   = "terraform"
  }
}

# AgentCore Module
module "agentcore" {
  source = "../../modules/agentcore"

  project_name             = local.project_name
  environment              = local.environment
  aws_region               = var.aws_region
  short_term_retention_days = 7
  long_term_enabled        = true
  memory_retention_days    = 365

  tags = local.tags
}

# Outputs
output "agentcore_memory_bucket" {
  description = "S3 bucket for AgentCore memory"
  value       = module.agentcore.memory_bucket_id
}

output "agentcore_kms_key" {
  description = "KMS key for memory encryption"
  value       = module.agentcore.kms_key_id
  sensitive   = true
}

output "memory_id_parameter" {
  description = "SSM parameter storing AgentCore Memory ID"
  value       = module.agentcore.memory_id_parameter_name
}

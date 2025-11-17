# AWS Bedrock AgentCore Memory Module

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# KMS key for encryption
resource "aws_kms_key" "memory_encryption" {
  description             = "KMS key for ${var.project_name} ${var.environment} AgentCore memory encryption"
  deletion_window_in_days = var.environment == "production" ? 30 : 7
  enable_key_rotation     = true

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-memory-key"
      Environment = var.environment
    }
  )
}

resource "aws_kms_alias" "memory_encryption" {
  name          = "alias/${var.project_name}-${var.environment}-memory"
  target_key_id = aws_kms_key.memory_encryption.key_id
}

# S3 bucket for memory storage
resource "aws_s3_bucket" "memory_storage" {
  bucket = "${var.project_name}-${var.environment}-agentcore-memory"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-agentcore-memory"
      Environment = var.environment
      Purpose     = "AgentCore Memory Storage"
    }
  )
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
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "memory_storage" {
  bucket = aws_s3_bucket.memory_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "memory_storage" {
  bucket = aws_s3_bucket.memory_storage.id

  rule {
    id     = "transition-old-memories"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 180
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = var.memory_retention_days
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "GLACIER_IR"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# NOTE: As of the time of this implementation, AWS Bedrock AgentCore
# resources may not be fully supported in Terraform. This is a conceptual
# implementation. You may need to use CloudFormation or AWS CLI for actual
# AgentCore Memory creation.
#
# Placeholder for AgentCore Memory (to be replaced with actual resource when available)
resource "null_resource" "agentcore_memory" {
  provisioner "local-exec" {
    command = <<-EOT
      aws bedrock-agent create-agent-memory \
        --agent-memory-name ${var.project_name}-${var.environment} \
        --description "Agent memory for ${var.project_name} ${var.environment}" \
        --memory-configuration '{
          "type": "AGENT_MEMORY",
          "storageConfiguration": {
            "s3BucketName": "${aws_s3_bucket.memory_storage.id}",
            "kmsKeyId": "${aws_kms_key.memory_encryption.arn}"
          },
          "retentionPolicy": {
            "shortTermRetentionDays": ${var.short_term_retention_days},
            "longTermEnabled": ${var.long_term_enabled}
          }
        }' \
        --region ${var.aws_region} \
        --tags '${jsonencode(var.tags)}' \
        > /tmp/agentcore-memory-${var.environment}.json || true
    EOT
  }

  triggers = {
    bucket_id = aws_s3_bucket.memory_storage.id
  }

  depends_on = [
    aws_s3_bucket.memory_storage,
    aws_kms_key.memory_encryption
  ]
}

# IAM role for AgentCore Memory
resource "aws_iam_role" "agentcore_memory" {
  name = "${var.project_name}-${var.environment}-agentcore-memory"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-agentcore-memory"
      Environment = var.environment
    }
  )
}

# IAM policy for AgentCore Memory S3 access
resource "aws_iam_role_policy" "agentcore_memory_s3" {
  name = "${var.project_name}-${var.environment}-agentcore-memory-s3"
  role = aws_iam_role.agentcore_memory.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.memory_storage.arn,
          "${aws_s3_bucket.memory_storage.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey"
        ]
        Resource = [aws_kms_key.memory_encryption.arn]
      }
    ]
  })
}

# Parameter to store the memory ID (manual update required after creation)
resource "aws_ssm_parameter" "agentcore_memory_id" {
  name        = "/${var.project_name}/${var.environment}/agentcore/memory-id"
  description = "AgentCore Memory ID for ${var.project_name} ${var.environment}"
  type        = "String"
  value       = "PLACEHOLDER - Update after AgentCore Memory creation"

  lifecycle {
    ignore_changes = [value]
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-memory-id"
      Environment = var.environment
    }
  )
}

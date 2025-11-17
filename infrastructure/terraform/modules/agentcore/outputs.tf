output "memory_bucket_id" {
  description = "S3 bucket ID for AgentCore memory storage"
  value       = aws_s3_bucket.memory_storage.id
}

output "memory_bucket_arn" {
  description = "S3 bucket ARN for AgentCore memory storage"
  value       = aws_s3_bucket.memory_storage.arn
}

output "kms_key_id" {
  description = "KMS key ID for memory encryption"
  value       = aws_kms_key.memory_encryption.id
}

output "kms_key_arn" {
  description = "KMS key ARN for memory encryption"
  value       = aws_kms_key.memory_encryption.arn
}

output "iam_role_arn" {
  description = "IAM role ARN for AgentCore Memory"
  value       = aws_iam_role.agentcore_memory.arn
}

output "memory_id_parameter_name" {
  description = "SSM Parameter name storing the AgentCore Memory ID"
  value       = aws_ssm_parameter.agentcore_memory_id.name
}

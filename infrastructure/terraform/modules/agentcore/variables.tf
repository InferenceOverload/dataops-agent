variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "short_term_retention_days" {
  description = "Retention days for short-term memory"
  type        = number
  default     = 7
}

variable "long_term_enabled" {
  description = "Enable long-term memory"
  type        = bool
  default     = true
}

variable "memory_retention_days" {
  description = "Total retention days for memories before expiration"
  type        = number
  default     = 365
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

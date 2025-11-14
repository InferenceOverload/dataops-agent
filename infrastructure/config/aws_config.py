"""
AWS Configuration Management

Centralized configuration for AWS services across workflows.

Configuration Priority (highest to lowest):
1. Environment variables (.env file)
2. Workflow-specific config (passed at runtime)
3. Default values (defined here)

Usage:
    from infrastructure.config.aws_config import AWSConfig

    config = AWSConfig()
    bucket = config.get_s3_bucket()
    region = config.get_region()
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()


class S3Config(BaseModel):
    """S3 Configuration"""
    default_bucket: Optional[str] = None
    region: str = "us-east-1"


class DynamoDBConfig(BaseModel):
    """DynamoDB Configuration"""
    region: str = "us-east-1"
    default_table: Optional[str] = None


class AWSConfig:
    """
    Central AWS configuration manager.

    Reads configuration from:
    1. Environment variables (highest priority)
    2. Runtime overrides
    3. Default values (lowest priority)

    Environment Variables:
    - AWS_REGION: Default AWS region
    - AWS_S3_BUCKET: Default S3 bucket for workflows
    - AWS_DYNAMODB_TABLE: Default DynamoDB table
    - AWS_ACCESS_KEY_ID: AWS credentials (optional if using IAM roles)
    - AWS_SECRET_ACCESS_KEY: AWS credentials (optional if using IAM roles)
    """

    def __init__(self, overrides: Optional[Dict[str, Any]] = None):
        """
        Initialize AWS configuration.

        Args:
            overrides: Runtime configuration overrides
        """
        self.overrides = overrides or {}

        # Load from environment
        self.s3_config = S3Config(
            default_bucket=os.getenv("AWS_S3_BUCKET"),
            region=os.getenv("AWS_REGION", "us-east-1")
        )

        self.dynamodb_config = DynamoDBConfig(
            region=os.getenv("AWS_REGION", "us-east-1"),
            default_table=os.getenv("AWS_DYNAMODB_TABLE")
        )

    def get_region(self, service: Optional[str] = None) -> str:
        """
        Get AWS region for a service.

        Args:
            service: Optional service name (s3, dynamodb, etc.)

        Returns:
            AWS region string
        """
        # Check overrides first
        if service and f"{service}_region" in self.overrides:
            return self.overrides[f"{service}_region"]

        if "region" in self.overrides:
            return self.overrides["region"]

        # Service-specific region
        if service == "s3":
            return self.s3_config.region
        elif service == "dynamodb":
            return self.dynamodb_config.region

        # Default region
        return os.getenv("AWS_REGION", "us-east-1")

    def get_s3_bucket(self, bucket_name: Optional[str] = None) -> str:
        """
        Get S3 bucket name.

        Args:
            bucket_name: Explicit bucket name (highest priority)

        Returns:
            S3 bucket name

        Raises:
            ValueError: If no bucket configured
        """
        # Priority: explicit > override > env > error
        if bucket_name:
            return bucket_name

        if "s3_bucket" in self.overrides:
            return self.overrides["s3_bucket"]

        if self.s3_config.default_bucket:
            return self.s3_config.default_bucket

        raise ValueError(
            "No S3 bucket configured. Set AWS_S3_BUCKET environment variable "
            "or pass bucket_name parameter."
        )

    def get_dynamodb_table(self, table_name: Optional[str] = None) -> str:
        """
        Get DynamoDB table name.

        Args:
            table_name: Explicit table name (highest priority)

        Returns:
            DynamoDB table name

        Raises:
            ValueError: If no table configured
        """
        # Priority: explicit > override > env > error
        if table_name:
            return table_name

        if "dynamodb_table" in self.overrides:
            return self.overrides["dynamodb_table"]

        if self.dynamodb_config.default_table:
            return self.dynamodb_config.default_table

        raise ValueError(
            "No DynamoDB table configured. Set AWS_DYNAMODB_TABLE environment variable "
            "or pass table_name parameter."
        )

    def get_boto3_session_kwargs(self) -> Dict[str, Any]:
        """
        Get kwargs for boto3.Session() or boto3.client().

        Returns:
            Dict with region_name and optional credentials
        """
        kwargs = {"region_name": self.get_region()}

        # Only add credentials if explicitly set
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        if access_key and secret_key:
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key

        return kwargs


# Global config instance
_global_config = None


def get_aws_config(overrides: Optional[Dict[str, Any]] = None) -> AWSConfig:
    """
    Get global AWS configuration instance.

    Args:
        overrides: Runtime configuration overrides

    Returns:
        AWSConfig instance
    """
    global _global_config

    if _global_config is None or overrides:
        _global_config = AWSConfig(overrides)

    return _global_config

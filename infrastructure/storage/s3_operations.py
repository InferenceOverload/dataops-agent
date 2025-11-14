"""
S3 Operations Utility

Common S3 operations for workflows.

Design: Provide helpers, don't force usage.
Workflows choose which methods they need.
"""

import boto3
from typing import Any, Dict, List, Optional
import json
from botocore.exceptions import ClientError


class S3Operations:
    """
    Common S3 operations for workflows.

    Provides reusable S3 helpers that workflows can use optionally.
    Workflows are free to use these utilities or implement their own S3 logic.
    """

    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        """
        Initialize S3 operations.

        Args:
            bucket_name: S3 bucket name to operate on
            region: AWS region (default: us-east-1)
        """
        self.bucket = bucket_name
        self.s3_client = boto3.client('s3', region_name=region)

    def upload_file(self, local_path: str, s3_key: str) -> bool:
        """
        Upload local file to S3.

        Args:
            local_path: Path to local file
            s3_key: S3 object key (path in bucket)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.upload_file(local_path, self.bucket, s3_key)
            return True
        except ClientError as e:
            print(f"Error uploading file to S3: {e}")
            return False

    def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        Download S3 file to local path.

        Args:
            s3_key: S3 object key (path in bucket)
            local_path: Path to save file locally

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.download_file(self.bucket, s3_key, local_path)
            return True
        except ClientError as e:
            print(f"Error downloading file from S3: {e}")
            return False

    def read_text(self, s3_key: str) -> str:
        """
        Read text file from S3.

        Args:
            s3_key: S3 object key (path in bucket)

        Returns:
            File contents as string, empty string on error
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
            return response['Body'].read().decode('utf-8')
        except ClientError as e:
            print(f"Error reading text from S3: {e}")
            return ""

    def write_text(self, s3_key: str, content: str) -> bool:
        """
        Write text content to S3.

        Args:
            s3_key: S3 object key (path in bucket)
            content: Text content to write

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=content.encode('utf-8')
            )
            return True
        except ClientError as e:
            print(f"Error writing text to S3: {e}")
            return False

    def read_json(self, s3_key: str) -> Dict[str, Any]:
        """
        Read and parse JSON file from S3.

        Args:
            s3_key: S3 object key (path in bucket)

        Returns:
            Parsed JSON as dict, empty dict on error
        """
        try:
            text = self.read_text(s3_key)
            if text:
                return json.loads(text)
            return {}
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from S3: {e}")
            return {}

    def write_json(self, s3_key: str, data: Dict[str, Any]) -> bool:
        """
        Write dict as JSON to S3.

        Args:
            s3_key: S3 object key (path in bucket)
            data: Dictionary to write as JSON

        Returns:
            True if successful, False otherwise
        """
        try:
            json_content = json.dumps(data, indent=2)
            return self.write_text(s3_key, json_content)
        except (TypeError, ValueError) as e:
            print(f"Error serializing JSON for S3: {e}")
            return False

    def list_objects(self, prefix: str) -> List[str]:
        """
        List all object keys with given prefix.

        Args:
            prefix: Prefix to filter objects (e.g., "data/")

        Returns:
            List of object keys, empty list on error
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
        except ClientError as e:
            print(f"Error listing objects from S3: {e}")
            return []

    def delete_object(self, s3_key: str) -> bool:
        """
        Delete object from S3.

        Args:
            s3_key: S3 object key (path in bucket)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError as e:
            print(f"Error deleting object from S3: {e}")
            return False

    def object_exists(self, s3_key: str) -> bool:
        """
        Check if object exists in S3.

        Args:
            s3_key: S3 object key (path in bucket)

        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError:
            return False

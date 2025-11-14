"""
DynamoDB Operations Utility

Common DynamoDB operations for workflows.

Design: Provide helpers, don't force usage.
Workflows choose which methods they need.
"""

import boto3
from typing import Any, Dict, List, Optional
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError


class DynamoDBOperations:
    """
    Common DynamoDB operations for workflows.

    Provides reusable DynamoDB helpers that workflows can use optionally.
    Workflows are free to use these utilities or implement their own DynamoDB logic.
    """

    def __init__(self, region: str = "us-east-1"):
        """
        Initialize DynamoDB operations.

        Args:
            region: AWS region (default: us-east-1)
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.client = boto3.client('dynamodb', region_name=region)

    def put_item(self, table_name: str, item: Dict[str, Any]) -> bool:
        """
        Put item in table.

        Args:
            table_name: Name of DynamoDB table
            item: Item to put (dictionary)

        Returns:
            True if successful, False otherwise
        """
        try:
            table = self.dynamodb.Table(table_name)
            table.put_item(Item=item)
            return True
        except ClientError as e:
            print(f"Error putting item to DynamoDB: {e}")
            return False

    def get_item(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict]:
        """
        Get item by primary key.

        Args:
            table_name: Name of DynamoDB table
            key: Primary key (e.g., {"id": "123"})

        Returns:
            Item as dict if found, None otherwise
        """
        try:
            table = self.dynamodb.Table(table_name)
            response = table.get_item(Key=key)
            return response.get('Item')
        except ClientError as e:
            print(f"Error getting item from DynamoDB: {e}")
            return None

    def query(self, table_name: str, key_condition_expression, **kwargs) -> List[Dict]:
        """
        Query table with key condition.

        Args:
            table_name: Name of DynamoDB table
            key_condition_expression: Key condition (e.g., Key('pk').eq('value'))
            **kwargs: Additional query parameters (FilterExpression, IndexName, etc.)

        Returns:
            List of items, empty list on error
        """
        try:
            table = self.dynamodb.Table(table_name)
            response = table.query(
                KeyConditionExpression=key_condition_expression,
                **kwargs
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error querying DynamoDB: {e}")
            return []

    def scan(self, table_name: str, filter_expression=None, **kwargs) -> List[Dict]:
        """
        Scan table with optional filter.

        Args:
            table_name: Name of DynamoDB table
            filter_expression: Optional filter expression
            **kwargs: Additional scan parameters

        Returns:
            List of items, empty list on error
        """
        try:
            table = self.dynamodb.Table(table_name)
            scan_kwargs = {}
            if filter_expression:
                scan_kwargs['FilterExpression'] = filter_expression
            scan_kwargs.update(kwargs)

            response = table.scan(**scan_kwargs)
            items = response.get('Items', [])

            # Handle pagination
            while 'LastEvaluatedKey' in response:
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                response = table.scan(**scan_kwargs)
                items.extend(response.get('Items', []))

            return items
        except ClientError as e:
            print(f"Error scanning DynamoDB: {e}")
            return []

    def update_item(
        self,
        table_name: str,
        key: Dict[str, Any],
        update_expression: str,
        expression_values: Dict
    ) -> bool:
        """
        Update item attributes.

        Args:
            table_name: Name of DynamoDB table
            key: Primary key of item to update
            update_expression: Update expression (e.g., "SET #attr = :val")
            expression_values: Values for expression (e.g., {":val": "new_value"})

        Returns:
            True if successful, False otherwise
        """
        try:
            table = self.dynamodb.Table(table_name)
            table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            return True
        except ClientError as e:
            print(f"Error updating item in DynamoDB: {e}")
            return False

    def delete_item(self, table_name: str, key: Dict[str, Any]) -> bool:
        """
        Delete item from table.

        Args:
            table_name: Name of DynamoDB table
            key: Primary key of item to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            table = self.dynamodb.Table(table_name)
            table.delete_item(Key=key)
            return True
        except ClientError as e:
            print(f"Error deleting item from DynamoDB: {e}")
            return False

    def batch_write(self, table_name: str, items: List[Dict[str, Any]]) -> bool:
        """
        Batch write multiple items.

        Args:
            table_name: Name of DynamoDB table
            items: List of items to write

        Returns:
            True if successful, False otherwise
        """
        try:
            table = self.dynamodb.Table(table_name)

            # DynamoDB batch_writer handles batching automatically
            with table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)

            return True
        except ClientError as e:
            print(f"Error batch writing to DynamoDB: {e}")
            return False

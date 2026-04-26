"""
DynamoDB Helper Module
Group A — Media Sharing Platform
Database Administrator: BDSD Douglas

This module replaces MockDynamoDB with a real AWS DynamoDB connection.
It follows the same interface so the rest of the app works without changes.
"""

import boto3
import logging
import os
from typing import List, Optional
from datetime import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class DynamoDBHelper:
    """
    Real AWS DynamoDB adapter for the Media Sharing Platform.
    Implements the same methods as MockDynamoDB so it's a drop-in replacement.
    """

    def __init__(self):
        """
        Initialize connection to AWS DynamoDB using environment variables.
        Make sure your .env file has:
            AWS_ACCESS_KEY_ID
            AWS_SECRET_ACCESS_KEY
            AWS_REGION
            DYNAMODB_TABLE
        """
        self.table_name = os.getenv("DYNAMODB_TABLE", "MediaMetadata")
        self.region = os.getenv("AWS_REGION", "us-east-1")

        # Connect to AWS DynamoDB
        self.dynamodb = boto3.resource(
            "dynamodb",
            region_name=self.region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

        self.table = self.dynamodb.Table(self.table_name)
        logger.info(f"Connected to DynamoDB table: {self.table_name}")

    # ------------------------------------------------------------------ #
    #  CREATE / UPDATE                                                     #
    # ------------------------------------------------------------------ #

    def put_item(self, item_id: str, item: dict) -> bool:
        """
        Store or fully replace an item in DynamoDB.

        Args:
            item_id: The media_id (primary key)
            item:    Full item dictionary to store

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Make sure media_id is inside the item dict
            item["media_id"] = item_id
            self.table.put_item(Item=item)
            logger.info(f"put_item OK: {item_id}")
            return True
        except ClientError as e:
            logger.error(f"put_item FAILED ({item_id}): {e.response['Error']['Message']}")
            return False

    def update_item(self, item_id: str, updates: dict) -> bool:
        """
        Update specific fields of an existing item.

        Args:
            item_id: The media_id to update
            updates: Dictionary of fields and new values

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Always stamp updated_at
            updates["updated_at"] = datetime.utcnow().isoformat()

            # Build DynamoDB update expression dynamically
            expr_parts = []
            expr_names = {}
            expr_values = {}

            for i, (key, value) in enumerate(updates.items()):
                placeholder_name = f"#f{i}"
                placeholder_value = f":v{i}"
                expr_parts.append(f"{placeholder_name} = {placeholder_value}")
                expr_names[placeholder_name] = key
                expr_values[placeholder_value] = value

            update_expression = "SET " + ", ".join(expr_parts)

            self.table.update_item(
                Key={"media_id": item_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
            logger.info(f"update_item OK: {item_id}")
            return True
        except ClientError as e:
            logger.error(f"update_item FAILED ({item_id}): {e.response['Error']['Message']}")
            return False

    # ------------------------------------------------------------------ #
    #  READ                                                                #
    # ------------------------------------------------------------------ #

    def get_item(self, item_id: str) -> Optional[dict]:
        """
        Retrieve a single item by media_id.

        Args:
            item_id: The media_id to look up

        Returns:
            Item dictionary, or None if not found
        """
        try:
            response = self.table.get_item(Key={"media_id": item_id})
            item = response.get("Item")
            if item:
                logger.info(f"get_item OK: {item_id}")
            else:
                logger.warning(f"get_item NOT FOUND: {item_id}")
            return item
        except ClientError as e:
            logger.error(f"get_item FAILED ({item_id}): {e.response['Error']['Message']}")
            return None

    def scan(self) -> List[dict]:
        """
        Return ALL items from the table.
        Fine for small datasets (free tier use).

        Returns:
            List of all item dictionaries
        """
        try:
            response = self.table.scan()
            items = response.get("Items", [])
            logger.info(f"scan OK: {len(items)} items found")
            return items
        except ClientError as e:
            logger.error(f"scan FAILED: {e.response['Error']['Message']}")
            return []

    def query_by_status(self, status: str) -> List[dict]:
        """
        Return all items matching a given status.
        Uses a linear scan (fine for free tier).

        Args:
            status: One of 'pending', 'processing', 'done', 'error'

        Returns:
            List of matching items
        """
        try:
            response = self.table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr("status").eq(status)
            )
            items = response.get("Items", [])
            logger.info(f"query_by_status '{status}': {len(items)} items")
            return items
        except ClientError as e:
            logger.error(f"query_by_status FAILED: {e.response['Error']['Message']}")
            return []

    def query_by_uploader(self, uploader: str) -> List[dict]:
        """
        Return all items uploaded by a specific user.

        Args:
            uploader: Uploader name to filter by

        Returns:
            List of matching items
        """
        try:
            response = self.table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr("uploader").eq(uploader)
            )
            items = response.get("Items", [])
            logger.info(f"query_by_uploader '{uploader}': {len(items)} items")
            return items
        except ClientError as e:
            logger.error(f"query_by_uploader FAILED: {e.response['Error']['Message']}")
            return []

    # ------------------------------------------------------------------ #
    #  DELETE                                                              #
    # ------------------------------------------------------------------ #

    def delete_item(self, item_id: str) -> bool:
        """
        Delete an item by media_id.

        Args:
            item_id: The media_id to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            self.table.delete_item(Key={"media_id": item_id})
            logger.info(f"delete_item OK: {item_id}")
            return True
        except ClientError as e:
            logger.error(f"delete_item FAILED ({item_id}): {e.response['Error']['Message']}")
            return False

    # ------------------------------------------------------------------ #
    #  UTILITY                                                             #
    # ------------------------------------------------------------------ #

    def count(self) -> int:
        """
        Return total number of items in the table.

        Returns:
            Integer count
        """
        try:
            response = self.table.scan(Select="COUNT")
            return response.get("Count", 0)
        except ClientError as e:
            logger.error(f"count FAILED: {e.response['Error']['Message']}")
            return 0

    def health_check(self) -> bool:
        """
        Check if the DynamoDB table is accessible.

        Returns:
            True if table is reachable, False otherwise
        """
        try:
            self.table.load()
            logger.info(f"health_check OK: table '{self.table_name}' is ACTIVE")
            return True
        except ClientError as e:
            logger.error(f"health_check FAILED: {e.response['Error']['Message']}")
            return False

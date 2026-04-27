"""
Real AWS DynamoDB Adapter
Group A — Media Sharing Platform
Database Administrator: BDSD Douglas

Drop-in replacement for MockDynamoDB.
Activated by setting:  DB_TYPE=dynamodb  in your .env file
"""

import boto3
import logging
import os
from typing import List, Optional
from datetime import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class RealDynamoDB:
    """
    AWS DynamoDB adapter for the Media Sharing Platform.
    Implements the exact same interface as MockDynamoDB — zero changes needed
    in the rest of the app when switching between mock and real.

    Required environment variables:
        AWS_ACCESS_KEY_ID       — IAM access key
        AWS_SECRET_ACCESS_KEY   — IAM secret key
        AWS_REGION              — e.g. us-east-1
        DYNAMODB_TABLE_NAME     — e.g. MediaMetadata
    Optional:
        DYNAMODB_ENDPOINT       — override endpoint (e.g. for LocalStack)
    """

    def __init__(self):
        self.table_name = os.getenv("DYNAMODB_TABLE_NAME", "MediaMetadata")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        endpoint_url = os.getenv("DYNAMODB_ENDPOINT", None)  # None = real AWS

        kwargs = dict(
            region_name=self.region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url

        self.dynamodb = boto3.resource("dynamodb", **kwargs)
        self.table = self.dynamodb.Table(self.table_name)

        logger.info(
            f"RealDynamoDB initialised — table: '{self.table_name}', "
            f"region: '{self.region}'"
            + (f", endpoint: {endpoint_url}" if endpoint_url else "")
        )

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
            item["media_id"] = item_id          # ensure PK is in the item
            self.table.put_item(Item=item)
            logger.info(f"put_item OK: {item_id}")
            return True
        except ClientError as e:
            logger.error(
                f"put_item FAILED ({item_id}): {e.response['Error']['Message']}"
            )
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
            updates["updated_at"] = datetime.utcnow().isoformat()

            expr_parts = []
            expr_names = {}
            expr_values = {}

            for i, (key, value) in enumerate(updates.items()):
                name_ph = f"#f{i}"
                val_ph = f":v{i}"
                expr_parts.append(f"{name_ph} = {val_ph}")
                expr_names[name_ph] = key
                expr_values[val_ph] = value

            self.table.update_item(
                Key={"media_id": item_id},
                UpdateExpression="SET " + ", ".join(expr_parts),
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
            logger.info(f"update_item OK: {item_id}")
            return True
        except ClientError as e:
            logger.error(
                f"update_item FAILED ({item_id}): {e.response['Error']['Message']}"
            )
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
            logger.error(
                f"get_item FAILED ({item_id}): {e.response['Error']['Message']}"
            )
            return None

    def scan(self) -> List[dict]:
        """
        Return ALL items from the table (handles DynamoDB pagination).

        Returns:
            List of all item dictionaries
        """
        try:
            items = []
            response = self.table.scan()
            items.extend(response.get("Items", []))

            # DynamoDB paginates results — keep fetching until done
            while "LastEvaluatedKey" in response:
                response = self.table.scan(
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                items.extend(response.get("Items", []))

            logger.info(f"scan OK: {len(items)} items")
            return items
        except ClientError as e:
            logger.error(f"scan FAILED: {e.response['Error']['Message']}")
            return []

    def query_by_status(self, status: str) -> List[dict]:
        """
        Return all items matching a given processing status.

        Args:
            status: One of 'pending', 'processing', 'done', 'error'

        Returns:
            List of matching items
        """
        try:
            items = []
            response = self.table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr("status").eq(status)
            )
            items.extend(response.get("Items", []))

            while "LastEvaluatedKey" in response:
                response = self.table.scan(
                    FilterExpression=boto3.dynamodb.conditions.Attr("status").eq(status),
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                items.extend(response.get("Items", []))

            logger.info(f"query_by_status '{status}': {len(items)} items")
            return items
        except ClientError as e:
            logger.error(
                f"query_by_status FAILED: {e.response['Error']['Message']}"
            )
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
            items = []
            response = self.table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr("uploader").eq(uploader)
            )
            items.extend(response.get("Items", []))

            while "LastEvaluatedKey" in response:
                response = self.table.scan(
                    FilterExpression=boto3.dynamodb.conditions.Attr("uploader").eq(uploader),
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                items.extend(response.get("Items", []))

            logger.info(f"query_by_uploader '{uploader}': {len(items)} items")
            return items
        except ClientError as e:
            logger.error(
                f"query_by_uploader FAILED: {e.response['Error']['Message']}"
            )
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
            logger.error(
                f"delete_item FAILED ({item_id}): {e.response['Error']['Message']}"
            )
            return False

    # ------------------------------------------------------------------ #
    #  UTILITY                                                             #
    # ------------------------------------------------------------------ #

    def count(self) -> int:
        """Return total number of items in the table."""
        try:
            response = self.table.scan(Select="COUNT")
            # Handle pagination for count
            total = response.get("Count", 0)
            while "LastEvaluatedKey" in response:
                response = self.table.scan(
                    Select="COUNT",
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                total += response.get("Count", 0)
            return total
        except ClientError as e:
            logger.error(f"count FAILED: {e.response['Error']['Message']}")
            return 0

    def health_check(self) -> bool:
        """
        Check if the DynamoDB table is accessible.

        Returns:
            True if table is active, False otherwise
        """
        try:
            self.table.load()   # fetches table metadata from AWS
            logger.info(
                f"health_check OK: table '{self.table_name}' is ACTIVE"
            )
            return True
        except ClientError as e:
            logger.error(
                f"health_check FAILED: {e.response['Error']['Message']}"
            )
            return False

"""
DynamoDB End-to-End Test
Group A — Media Sharing Platform
Database Administrator: BDSD Douglas

Run this to verify your AWS DynamoDB connection works correctly.

Usage:
    python db/test_dynamo_helper.py
"""

import sys
import os
import uuid
from datetime import datetime

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.dynamo_helper import DynamoDBHelper


def print_result(test_name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}  {test_name}", f"({detail})" if detail else "")


def run_tests():
    print("=" * 60)
    print("  DynamoDB Connection Test — BDSD Douglas")
    print("  Group A — Media Sharing Platform")
    print("=" * 60)

    db = DynamoDBHelper()

    # ── Test 1: Health Check ─────────────────────────────────────
    print("\n[1] Health Check")
    result = db.health_check()
    print_result("Table is reachable", result)
    if not result:
        print("\n  ⚠️  Cannot connect to DynamoDB. Check your .env file and AWS setup.")
        sys.exit(1)

    # ── Test 2: Put Item ─────────────────────────────────────────
    print("\n[2] Create Item (put_item)")
    test_id = str(uuid.uuid4())
    test_item = {
        "media_id": test_id,
        "title": "Test Image",
        "uploader": "BDSD Douglas",
        "object_key": f"uploads/{test_id}.jpg",
        "status": "pending",
        "thumbnail_key": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "file_size": 1024000,
        "media_type": "image",
        "description": "Test record created by test_dynamo_helper.py",
        "error_message": None,
    }
    result = db.put_item(test_id, test_item)
    print_result("put_item", result, f"media_id={test_id[:8]}...")

    # ── Test 3: Get Item ─────────────────────────────────────────
    print("\n[3] Read Item (get_item)")
    item = db.get_item(test_id)
    print_result("get_item returns data", item is not None)
    print_result("title matches", item and item.get("title") == "Test Image")

    # ── Test 4: Update Item ──────────────────────────────────────
    print("\n[4] Update Item (update_item)")
    result = db.update_item(test_id, {
        "status": "done",
        "thumbnail_key": f"thumbnails/{test_id}_thumb.jpg"
    })
    print_result("update_item", result)
    updated = db.get_item(test_id)
    print_result("status is now 'done'", updated and updated.get("status") == "done")

    # ── Test 5: Scan ─────────────────────────────────────────────
    print("\n[5] List All Items (scan)")
    items = db.scan()
    print_result("scan returns list", isinstance(items, list))
    print_result("test item appears in scan", any(i.get("media_id") == test_id for i in items),
                 f"{len(items)} total items")

    # ── Test 6: Query by Status ──────────────────────────────────
    print("\n[6] Query by Status")
    done_items = db.query_by_status("done")
    print_result("query_by_status('done')", isinstance(done_items, list),
                 f"{len(done_items)} items found")

    # ── Test 7: Query by Uploader ────────────────────────────────
    print("\n[7] Query by Uploader")
    my_items = db.query_by_uploader("BDSD Douglas")
    print_result("query_by_uploader found test item",
                 any(i.get("media_id") == test_id for i in my_items))

    # ── Test 8: Count ────────────────────────────────────────────
    print("\n[8] Count Items")
    total = db.count()
    print_result("count returns integer", isinstance(total, int), f"{total} total items")

    # ── Test 9: Delete Item ──────────────────────────────────────
    print("\n[9] Delete Test Item (cleanup)")
    result = db.delete_item(test_id)
    print_result("delete_item", result)
    gone = db.get_item(test_id)
    print_result("item no longer exists", gone is None)

    # ── Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ✅ All tests passed! Your DynamoDB is connected and working.")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()

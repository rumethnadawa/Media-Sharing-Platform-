# Database Schema — MediaMetadata Table
**Group A — Media Sharing Platform**
**Database Administrator: BDSD Douglas**

---

## Table: MediaMetadata

### AWS DynamoDB Configuration
| Setting | Value |
|---|---|
| Table Name | `MediaMetadata` |
| Region | `us-east-1` |
| Billing Mode | On-Demand (Pay per request) |
| Partition Key | `media_id` (String) |

---

## Attributes

| Attribute | Type | Required | Description |
|---|---|---|---|
| `media_id` | String (UUID) | ✅ Yes — Primary Key | Unique identifier for each media record |
| `title` | String | ✅ Yes | Title of the media file |
| `uploader` | String | ✅ Yes | Name of the person who uploaded |
| `object_key` | String | ✅ Yes | S3 path to the original file |
| `status` | String (Enum) | ✅ Yes | Current processing status |
| `thumbnail_key` | String | ❌ Optional | S3 path to generated thumbnail |
| `created_at` | String (ISO) | ✅ Yes | Timestamp when record was created |
| `updated_at` | String (ISO) | ✅ Yes | Timestamp of last update |
| `file_size` | Number (bytes) | ✅ Yes | Size of the uploaded file |
| `media_type` | String | ✅ Yes | Type: `image` or `video` |
| `description` | String | ❌ Optional | Optional description of the media |
| `error_message` | String | ❌ Optional | Error details if processing failed |

---

## Status Enum Values

| Status | Meaning |
|---|---|
| `pending` | Uploaded, waiting in SQS queue |
| `processing` | Worker is generating thumbnail |
| `done` | Thumbnail generated, ready to view |
| `error` | Processing failed — see error_message |

---

## Sample Record (JSON)

```json
{
  "media_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "title": "Campus Sunset",
  "uploader": "BDSD Douglas",
  "object_key": "uploads/a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg",
  "status": "done",
  "thumbnail_key": "thumbnails/a1b2c3d4-e5f6-7890-abcd-ef1234567890_thumb.jpg",
  "created_at": "2026-04-26T08:00:00.000Z",
  "updated_at": "2026-04-26T08:00:15.000Z",
  "file_size": 2048000,
  "media_type": "image",
  "description": "Sunset photo taken at KDU campus",
  "error_message": null
}
```

---

## S3 Bucket Structure

```
group-a-media-bucket-xxx/
├── uploads/          ← original uploaded files
│   └── <media_id>.<ext>
└── thumbnails/       ← generated thumbnails
    └── <media_id>_thumb.jpg
```

---

## Notes

- All timestamps are in ISO 8601 UTC format
- `media_id` is a UUID generated automatically on upload
- `thumbnail_key` is null until worker completes processing
- Free tier limits: 25 GB storage, 25 read/write capacity units per second

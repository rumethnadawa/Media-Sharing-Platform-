# API Developer Guide

This guide is for the API developer role in Group A. It explains how to run the backend API, what endpoints exist today, and how to implement the upload flow correctly.

## 1. Scope

You are responsible for the HTTP API layer:
- Parse requests and validate required inputs.
- Call `MediaService` methods from `app/services/media_service.py`.
- Return consistent JSON responses and HTTP status codes.
- Handle file upload to S3 (real integration or local simulation).
- Push processing jobs to queue after metadata is created.

## 2. Current Backend Behavior

The backend already provides a working Flask app in `app/main.py` with these endpoints:

- `GET /health`
- `GET /api/stats`
- `GET /api/list`
- `GET /api/status/<media_id>`
- `POST /api/upload` (multipart upload is implemented)

Note: Current upload flow stores files locally in `backend/uploads/` and generates an S3-style `object_key`. This is suitable for development; replace the storage step with real S3 upload for cloud deployment.

## 3. Run Locally

From `backend/`:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app/main.py
```

Server starts on `http://localhost:5000`.

## 4. Service Layer Contract

Use these service calls from `MediaService`:

- `create_media(title, uploader, object_key, file_size, media_type, description=None)`
  - returns `(success, media, message)`
- `list_all_media()`
- `list_media_by_status(status)`
- `list_media_by_uploader(uploader)`
- `get_media(media_id)`
- `get_statistics()`

Validation rules enforced by service (`app/utils/validators.py`):
- `title`: required, string, max 255
- `uploader`: required, string, max 255
- `object_key`: required, string
- `file_size`: must be > 0 and <= 5 GB
- `media_type`: must be `image` or `video`
- `media_id`: must be valid UUID

## 5. API Endpoints and Response Contract

### 5.1 `GET /health`

Success (`200`):

```json
{
  "status": "healthy",
  "service": "MediaBackendService",
  "version": "1.0.0",
  "database": "OK"
}
```

### 5.2 `GET /api/stats`

Success (`200`):

```json
{
  "success": true,
  "statistics": {
    "total_media": 0,
    "pending": 0,
    "processing": 0,
    "done": 0,
    "error": 0,
    "total_size_bytes": 0
  }
}
```

### 5.3 `GET /api/list`

Optional query parameters:
- `status` (pending|processing|done|error)
- `uploader`

Success (`200`):

```json
{
  "success": true,
  "count": 1,
  "media": [
    {
      "media_id": "uuid",
      "title": "Example",
      "uploader": "user1",
      "object_key": "s3://bucket/uploads/example.mp4",
      "status": "pending",
      "thumbnail_key": null,
      "created_at": "2026-04-27T10:00:00",
      "updated_at": "2026-04-27T10:00:00",
      "file_size": 1234,
      "media_type": "video",
      "description": "optional",
      "error_message": null
    }
  ]
}
```

### 5.4 `GET /api/status/<media_id>`

Success (`200`):

```json
{
  "success": true,
  "media": {
    "media_id": "uuid",
    "status": "processing"
  }
}
```

Not found or invalid UUID (`404`):

```json
{
  "success": false,
  "error": "Media not found: ..."
}
```

### 5.5 `POST /api/upload`

Use multipart form-data:
- `file` (required)
- `title` (required)
- `uploader` (required)
- `description` (optional)

Success (`201`):

```json
{
  "success": true,
  "media_id": "uuid",
  "status": "pending",
  "message": "Media upload initiated"
}
```

Validation error (`400`):

```json
{
  "success": false,
  "error": "title and uploader are required"
}
```

## 6. Upload Endpoint Behavior

Current implementation does the following in order:

1. Validate form fields and file presence.
2. Detect media type from MIME type (`image/*` => `image`, otherwise `video`).
3. Save file to local storage and generate S3-style `object_key`.
4. Read file size from the uploaded file object.
5. Call `media_service.create_media(...)` with real values.
6. On success, send queue message via `queue.send_message(...)`:

```json
{
  "media_id": "<uuid>",
  "object_key": "s3://bucket/path",
  "action": "generate_thumbnail"
}
```

7. Return `201` with `media_id` and initial `status`.
8. If metadata creation fails, return `400` with service error message.
9. If unexpected error occurs, return `500`.

Additional behavior:
- Unsupported file extension returns `400`.
- Unsupported MIME type returns `400`.
- Oversized file returns `413`.

## 7. Curl Test Commands

Health:

```bash
curl http://localhost:5000/health
```

List all:

```bash
curl http://localhost:5000/api/list
```

List by status:

```bash
curl "http://localhost:5000/api/list?status=pending"
```

List by uploader:

```bash
curl "http://localhost:5000/api/list?uploader=user1"
```

Get statistics:

```bash
curl http://localhost:5000/api/stats
```

Upload:

```bash
curl -X POST http://localhost:5000/api/upload \
  -F "title=My File" \
  -F "uploader=user1" \
  -F "description=sample" \
  -F "file=@./sample.mp4"
```

Status by ID:

```bash
curl http://localhost:5000/api/status/<media_id>
```

## 8. Postman Requests

Use these requests if you prefer Postman instead of curl.

### 8.1 Health Check
- Method: `GET`
- URL: `http://localhost:5000/health`

### 8.2 List Media
- Method: `GET`
- URL: `http://localhost:5000/api/list`

### 8.3 Filter by Status
- Method: `GET`
- URL: `http://localhost:5000/api/list?status=pending`

### 8.4 Filter by Uploader
- Method: `GET`
- URL: `http://localhost:5000/api/list?uploader=user1`

### 8.5 Statistics
- Method: `GET`
- URL: `http://localhost:5000/api/stats`

### 8.6 Upload Media
- Method: `POST`
- URL: `http://localhost:5000/api/upload`
- Body type: `form-data`
- Fields:
  - `title` = `My File`
  - `uploader` = `user1`
  - `description` = `sample`
  - `file` = choose a file

### 8.7 Get Status by ID
- Method: `GET`
- URL: `http://localhost:5000/api/status/<media_id>`

## 9. Error Responses

Your API should return the correct status code for each case.

### 9.1 Bad Request (`400`)
Use this when validation fails.

Examples:

```json
{
  "success": false,
  "error": "title and uploader are required"
}
```

```json
{
  "success": false,
  "error": "unsupported file extension. allowed: ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'avi', 'mov']"
}
```

### 9.2 Not Found (`404`)
Use this when media ID does not exist.

```json
{
  "success": false,
  "error": "Media not found: ..."
}
```

### 9.3 Payload Too Large (`413`)
Use this when uploaded file exceeds the maximum allowed size.

```json
{
  "success": false,
  "error": "file too large. max allowed is 5368709120 bytes"
}
```

## 10. Common Mistakes to Avoid

- Returning inconsistent JSON keys across endpoints.
- Sending queue message before metadata is successfully created.
- Passing invalid UUID format to `/api/status/<media_id>` and expecting `200`.
- Using fake file size or object key in production API logic.
- Forgetting to include `description` as optional.
- Returning success before queue message is sent.
- Forgetting to test both happy-path and failure-path requests.

## 11. Definition of Done (API Developer)

- All endpoints above return correct status codes and JSON structure.
- `POST /api/upload` uses real uploaded file information.
- Queue messages are produced after successful metadata creation.
- Filtering works with `status` and `uploader` query params.
- Error handling is consistent (`400`, `404`, `500`).
- Endpoints tested with curl or Postman.

## 12. Submission Checklist

Before submitting your API work, make sure you have:

- [ ] Implemented all required routes in `app/main.py`
- [ ] Verified `POST /api/upload` with a real file
- [ ] Tested `GET /health`, `GET /api/list`, `GET /api/stats`, and `GET /api/status/<media_id>`
- [ ] Confirmed error handling for invalid input and missing media ID
- [ ] Updated documentation in `docs/API_DEVELOPER_GUIDE.md`
- [ ] Kept response JSON consistent across all endpoints
- [ ] Demonstrated the API with curl or Postman
- [ ] Imported the Postman collection from `docs/API_DEVELOPER.postman_collection.json`

## 13. Ready-to-Submit Note

You can include this short summary in your report:

"The API developer work is completed with working Flask endpoints for health, media listing, upload, status lookup, and statistics. The upload flow validates input, stores uploaded files in development mode, creates media metadata through the service layer, and dispatches processing jobs to the queue. The API was verified using curl and the included Postman collection."
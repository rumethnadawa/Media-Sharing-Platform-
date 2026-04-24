# Media Sharing Platform - Backend

## Overview

This is the backend implementation for Group A's Media Sharing Platform - a distributed systems mini project for CS4092.

**Backend Developer:** PHDB Nayanakantha

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run simulation to verify backend works
python simulation/run_simulation.py

# Expected output: All tests passed! Backend is working correctly.
```

### Project Structure

```
backend/
├── app/
│   ├── models/        # Data models (Media class)
│   ├── services/      # Business logic (MediaService)
│   ├── database/      # Database layer (MockDynamoDB)
│   └── utils/         # Utilities (validators, exceptions, queue)
├── simulation/        # Testing script
├── docs/              # Documentation
├── requirements.txt   # Dependencies
└── README.md          # This file
```

### Core Components

#### 1. Media Model (`app/models/media.py`)

Represents a media file record:
- `media_id`: Unique identifier (UUID)
- `title`: Media title
- `uploader`: User who uploaded
- `object_key`: S3 storage path
- `status`: pending|processing|done|error
- `thumbnail_key`: S3 path to thumbnail
- `file_size`: Bytes
- `media_type`: image|video

#### 2. MediaService (`app/services/media_service.py`)

Core business logic with methods:
- `create_media()`: Create new media record
- `get_media()`: Retrieve media by ID
- `list_all_media()`: List all media
- `update_media_status()`: Update processing status
- `update_media_processing()`: Mark as done/error
- `get_statistics()`: System statistics

#### 3. MockDynamoDB (`app/database/mock_dynamodb.py`)

Local database simulation:
- Stores data in JSON file
- Supports CRUD operations
- Query by status, uploader
- Persistence across runs

#### 4. MockSQS (`app/utils/queue.py`)

Local queue simulation:
- Send/receive messages
- Message tracking
- Queue management

### Usage Examples

#### Create Media

```python
from app.database import MockDynamoDB
from app.services import MediaService

db = MockDynamoDB()
service = MediaService(db)

success, media, msg = service.create_media(
    title="My Video",
    uploader="john_doe",
    object_key="s3://bucket/video.mp4",
    file_size=1024000,
    media_type="video"
)

if success:
    print(f"Created: {media.media_id}")
```

#### Process Media

```python
# Worker receives message
# Mark as processing
service.update_media_status(media_id, 'processing')

# Do work...

# Mark as done
service.update_media_processing(
    media_id,
    thumbnail_key="s3://bucket/thumb.jpg"
)
```

#### List Media

```python
success, media_list, msg = service.list_all_media()

for media in media_list:
    print(f"{media.title}: {media.status}")
```

### Integration Points

**API Developer** (L.K.D.H. Perera):
- Call `MediaService` methods for API endpoints
- See `docs/INTEGRATION_GUIDE.md` for examples

**Worker Developer** (DMPT Dissanayake):
- Consume SQS messages
- Call `update_media_status()` and `update_media_processing()`
- See `docs/INTEGRATION_GUIDE.md` for worker implementation

**Database Admin** (BDSD Douglas):
- Migrate from MockDynamoDB to real AWS DynamoDB
- Design table schema and indexes

**Frontend/DevOps** (KKVRM Kalyanapriya):
- Containerize backend with Docker
- Deploy to cloud
- Set up S3, SQS, DynamoDB

### Running Tests

```bash
# Run comprehensive simulation
python simulation/run_simulation.py

# This tests:
✓ Database CRUD operations
✓ Media service operations
✓ Queue integration
✓ Error handling
✓ Statistics
✓ End-to-end workflow
```

### API Integration

Backend supports these operations:

```
POST /upload
  → service.create_media()
  → Queue message sent

GET /list
  → service.list_all_media()

GET /status?id=<media_id>
  → service.get_media()

GET /stats
  → service.get_statistics()
```

### Documentation

- `docs/BACKEND_GUIDE.md` - Complete backend documentation
- `docs/INTEGRATION_GUIDE.md` - Integration guide for all team members
- `docs/DATABASE_SCHEMA.md` - Database schema design
- `docs/API_INTEGRATION.md` - API integration details

### Key Features

- ✓ Complete data model with validation
- ✓ Service layer with business logic
- ✓ Mock database with JSON persistence
- ✓ Queue simulation for async processing
- ✓ Error handling and retries
- ✓ Comprehensive logging
- ✓ Unit and integration tests
- ✓ Full documentation

### Technology Stack

- **Language**: Python 3.8+
- **Database**: DynamoDB (mocked locally)
- **Queue**: SQS (mocked locally)
- **Storage**: S3 (to be configured by DevOps)
- **Framework**: Flask (API layer)

### Local Development

```bash
# Setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run simulation
python simulation/run_simulation.py

# Use in your code
from app.services import MediaService
from app.database import MockDynamoDB

db = MockDynamoDB()
service = MediaService(db)
```

### Database File

Media records are stored in `media_db.json`:

```json
{
  "uuid-1": {
    "media_id": "uuid-1",
    "title": "Video 1",
    "status": "done",
    ...
  },
  "uuid-2": {
    "media_id": "uuid-2",
    "title": "Image 1",
    "status": "pending",
    ...
  }
}
```

### Error Handling

All service methods return: `(success: bool, data, message: str)`

```python
success, media, msg = service.get_media(media_id)

if success:
    print(f"Found: {media.title}")
else:
    print(f"Error: {msg}")
```

### Logging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Next Steps

1. ✓ Backend implementation complete
2. → Share with team for integration
3. → API developer implements endpoints
4. → Worker developer implements processing
5. → Database admin sets up cloud database
6. → DevOps sets up deployment

### Status

**✓ READY FOR INTEGRATION**

The backend is fully functional and ready for team integration. All team members should review the integration guide.

### Support

**Backend Developer:** PHDB Nayanakantha

For questions:
- Service methods: See `app/services/media_service.py`
- Data model: See `app/models/media.py`
- Database: See `app/database/mock_dynamodb.py`
- Integration: See `docs/INTEGRATION_GUIDE.md`

---

**Created:** April 2026  
**Status:** Ready for Use  
**Version:** 1.0.0

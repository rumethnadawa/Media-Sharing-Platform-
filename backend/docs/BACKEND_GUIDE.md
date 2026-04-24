# Backend Developer Documentation
## Group A - Media Sharing Platform

**Backend Developer:** PHDB Nayanakantha

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Core Components](#core-components)
5. [API Integration Points](#api-integration-points)
6. [Database Schema](#database-schema)
7. [Service Layer](#service-layer)
8. [Running the Backend](#running-the-backend)
9. [Integration Guide](#integration-guide)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The backend implementation provides the core business logic and data management for the Media Sharing Platform. It handles:

- **Media Record Management**: Create, read, update, and delete media records
- **Status Tracking**: Track media processing status (pending → processing → done/error)
- **Database Operations**: CRUD operations with local DynamoDB simulation
- **Queue Integration**: Interface with message queue for asynchronous processing
- **Error Handling**: Robust error handling and retry mechanisms
- **Validation**: Input validation and data integrity checks

### Technology Stack

- **Language**: Python 3.8+
- **Database**: AWS DynamoDB (mocked locally with JSON for development)
- **Queue**: AWS SQS (mocked locally for development)
- **Framework**: Flask (for API, developed by API Developer)
- **Storage**: AWS S3 (file storage, managed by Frontend/DevOps)

---

## Architecture

### High-Level Flow

```
User Request
    ↓
API Endpoint (API Developer)
    ↓
Backend Service (PHDB - You)
    ├→ Database Operations
    ├→ Validation
    └→ Queue Message Creation
    ↓
Worker/Processor (DMPT Dissanayake)
    ├→ Consume Message
    ├→ Process Media
    └→ Update Status via Backend
    ↓
Frontend Display (KKVRM Kalyanapriya)
```

### Component Interaction

```
┌─────────────────────────────────────────────────┐
│  Frontend / UI (KKVRM)                          │
│  (CLI or Web Interface)                         │
└────────────────┬────────────────────────────────┘
                 │
     HTTP/REST API Calls
                 │
        ┌────────▼────────┐
        │  API Endpoints  │
        │ (L.K.D.H. Perera)
        └────────┬────────┘
                 │
    ┌────────────┴──────────────┐
    │                           │
    ▼                           ▼
┌─────────────────┐    ┌─────────────────┐
│ Backend Service │    │    Database     │
│  (PHDB - You)   │◄──►│  (BDSD)         │
│                 │    │ DynamoDB/JSON   │
└────────┬────────┘    └─────────────────┘
         │
         │ Queue Messages
         │
    ┌────▼──────────┐
    │  Message Queue│
    │     (SQS)     │
    └────┬──────────┘
         │
         ▼
    ┌──────────────────┐
    │ Worker/Processor │
    │ (DMPT)           │
    │ Generate Thumbnail
    └──────────────────┘
```

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py                 # Application initialization
│   ├── config.py                   # Configuration settings
│   │
│   ├── models/                     # Data models
│   │   ├── __init__.py
│   │   └── media.py               # Media data model
│   │
│   ├── services/                   # Business logic layer
│   │   ├── __init__.py
│   │   └── media_service.py       # Media service (YOUR CORE LOGIC)
│   │
│   ├── database/                   # Database layer
│   │   ├── __init__.py
│   │   ├── interface.py           # Abstract interface
│   │   └── mock_dynamodb.py       # Mock DynamoDB implementation
│   │
│   └── utils/                      # Utilities
│       ├── __init__.py
│       ├── exceptions.py          # Custom exceptions
│       ├── validators.py          # Input validators
│       └── queue.py               # Mock SQS implementation
│
├── simulation/
│   └── run_simulation.py          # Comprehensive testing script
│
├── tests/                          # Unit tests (to be added)
│   └── test_media_service.py
│
├── docs/                           # Documentation
│   ├── BACKEND_GUIDE.md           # This file
│   ├── INTEGRATION_GUIDE.md       # Integration guide
│   ├── API_INTEGRATION.md         # API integration details
│   └── DATABASE_SCHEMA.md         # Database schema documentation
│
├── requirements.txt               # Python dependencies
├── docker-compose.yml             # Local development setup
├── Dockerfile                     # Container configuration
└── README.md                      # Project overview
```

---

## Core Components

### 1. Data Model (Media)

**File**: `app/models/media.py`

The Media class represents a media record with all necessary metadata.

```python
@dataclass
class Media:
    media_id: str                    # UUID
    title: str                       # Media title
    uploader: str                    # User who uploaded
    object_key: str                  # S3 storage path
    status: str                      # pending|processing|done|error
    thumbnail_key: Optional[str]     # S3 thumbnail path
    created_at: str                  # ISO timestamp
    updated_at: str                  # ISO timestamp
    file_size: int                   # Bytes
    media_type: str                  # image|video
    description: Optional[str]       # Optional description
    error_message: Optional[str]     # Error details if failed
```

**Key Methods**:
- `to_dict()`: Convert to dictionary for DB storage
- `from_dict()`: Create from dictionary
- `mark_processing()`: Set status to processing
- `mark_done()`: Mark successfully processed
- `mark_error()`: Mark as failed with error message

### 2. Database Layer (MockDynamoDB)

**File**: `app/database/mock_dynamodb.py`

Provides local development database with JSON file storage.

```python
class MockDynamoDB:
    def put_item(item_id, item)      # Create/update
    def get_item(item_id)             # Retrieve
    def update_item(item_id, updates) # Update fields
    def delete_item(item_id)          # Delete
    def scan()                        # List all
    def query_by_status(status)       # Filter by status
    def query_by_uploader(uploader)   # Filter by uploader
```

### 3. Service Layer (MediaService)

**File**: `app/services/media_service.py` ← **YOUR MAIN IMPLEMENTATION**

Core business logic for all media operations.

```python
class MediaService:
    def create_media(...)             # Create new media
    def get_media(media_id)           # Retrieve media
    def list_all_media()              # List all media
    def list_media_by_status(status)  # Filter by status
    def list_media_by_uploader()      # Filter by uploader
    def update_media_status(...)      # Update status
    def update_media_processing(...)  # Mark as done/error
    def delete_media(media_id)        # Delete media
    def get_statistics()              # System stats
    def health_check()                # Health status
```

### 4. Queue Integration (MockSQS)

**File**: `app/utils/queue.py`

Simulates SQS for local development.

```python
class MockSQS:
    def send_message(body)            # Send to queue
    def receive_messages(max_number)  # Receive from queue
    def delete_message(message_id)    # Delete after processing
    def get_queue_size()              # Queue length
    def clear_queue()                 # Clear all messages
```

### 5. Utilities

**File**: `app/utils/`

- `validators.py`: Input validation functions
- `exceptions.py`: Custom exception classes
- `queue.py`: Queue implementation

---

## API Integration Points

### What the API Developer Will Use

The API Developer (L.K.D.H. Perera) will call your backend service like this:

```python
from app.database import MockDynamoDB
from app.services import MediaService

# Initialize
db = MockDynamoDB()
service = MediaService(db)

# Upload endpoint
success, media, message = service.create_media(
    title=request.form['title'],
    uploader=request.form['uploader'],
    object_key=s3_key,
    file_size=file_size,
    media_type=file_type,
    description=request.form.get('description')
)

if success:
    # Send to queue for processing
    queue.send_message({
        'media_id': media.media_id,
        'object_key': media.object_key,
        'action': 'generate_thumbnail'
    })
    return {'media_id': media.media_id, 'status': media.status}

# List endpoint
success, media_list, msg = service.list_all_media()
return [m.to_dict() for m in media_list]

# Status endpoint
success, media, msg = service.get_media(media_id)
return media.to_dict() if success else {'error': msg}
```

### Expected API Endpoints

Your backend supports these API endpoints (to be implemented by API Developer):

```
POST /upload
  Input: title, uploader, file, description
  Backend Call: create_media(...)
  Queue Action: Send processing job
  
GET /list
  Backend Call: list_all_media()
  
GET /status?id=<media_id>
  Backend Call: get_media(media_id)
  
GET /summaries (optional)
  Backend Call: get_statistics()
```

---

## Database Schema

### Media Table

```json
{
  "media_id": "UUID (Primary Key)",
  "title": "String",
  "uploader": "String",
  "object_key": "String (S3 path)",
  "status": "Enum: pending|processing|done|error",
  "thumbnail_key": "String (S3 path, nullable)",
  "created_at": "ISO Timestamp",
  "updated_at": "ISO Timestamp",
  "file_size": "Integer (bytes)",
  "media_type": "String: image|video",
  "description": "String (optional)",
  "error_message": "String (optional)"
}
```

### Data Persistence

- **Local Development**: JSON file (`media_db.json`)
- **Cloud Deployment**: AWS DynamoDB table named "Media"

---

## Service Layer

### MediaService Class

Your main implementation handles all business logic.

#### Creating Media

```python
success, media, msg = service.create_media(
    title="My Video",
    uploader="john_doe",
    object_key="s3://bucket/video.mp4",
    file_size=1024000,
    media_type="video"
)
```

**Validation**:
- Title: Non-empty, max 255 chars
- Uploader: Non-empty, max 255 chars
- File size: > 0, max 5GB
- Media type: "image" or "video"

**Return**: `(success: bool, media: Media, message: str)`

#### Updating Status During Processing

```python
# Step 1: Mark as processing (when worker picks up)
success, msg = service.update_media_status(media_id, 'processing')

# Step 2: Mark as done (when worker completes)
success, msg = service.update_media_processing(
    media_id,
    thumbnail_key="s3://bucket/thumb.jpg"
)

# Step 3: Mark as error (if processing fails)
success, msg = service.update_media_processing(
    media_id,
    error_message="Processing failed: Invalid format"
)
```

#### Retrieving Data

```python
# Get single media
success, media, msg = service.get_media(media_id)

# Get all media
success, media_list, msg = service.list_all_media()

# Get media by status
success, media_list, msg = service.list_media_by_status('done')

# Get media by uploader
success, media_list, msg = service.list_media_by_uploader('john_doe')
```

---

## Running the Backend

### Prerequisites

```bash
Python 3.8+
pip (Python package manager)
```

### Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (optional but recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run Simulation

```bash
# From backend directory
python simulation/run_simulation.py
```

This runs comprehensive tests including:
- ✓ Database CRUD operations
- ✓ Media service operations
- ✓ Queue operations and worker integration
- ✓ Error handling
- ✓ Statistics
- ✓ End-to-end workflow

### Expected Output

```
======================================================================
                 Media Sharing Platform - Backend Simulation
======================================================================

ℹ Backend Developer: PHDB Nayanakantha
ℹ Project: Group A - Distributed Systems Mini Project
ℹ Use Case: Media Sharing Platform

ℹ Initializing backend components...
✓ Database initialized
✓ Media service initialized
✓ Queue initialized

Running test: Database Operations...
... [test results] ...

✓ All tests passed! Backend is working correctly.
```

---

## Integration Guide

### 1. API Developer Integration

**File to integrate with**: `app/services/media_service.py`

```python
# In your Flask app
from app.database import MockDynamoDB
from app.services import MediaService

db = MockDynamoDB()
media_service = MediaService(db)

@app.route('/upload', methods=['POST'])
def upload():
    success, media, msg = media_service.create_media(
        title=request.form['title'],
        uploader=request.form['uploader'],
        object_key=s3_key,
        file_size=file_size,
        media_type=media_type
    )
    
    if success:
        # Send to queue
        queue.send_message({
            'media_id': media.media_id,
            'object_key': media.object_key
        })
    
    return jsonify(media.to_dict() if success else {'error': msg})
```

### 2. Worker Developer Integration

**File to integrate with**: `app/services/media_service.py`

```python
# In worker process
from app.database import MockDynamoDB
from app.services import MediaService

db = MockDynamoDB()
service = MediaService(db)

def process_job(message):
    media_id = message['media_id']
    
    # Update status
    service.update_media_status(media_id, 'processing')
    
    try:
        # Process media...
        thumbnail_path = generate_thumbnail(...)
        
        # Mark complete
        service.update_media_processing(
            media_id,
            thumbnail_key=thumbnail_path
        )
    except Exception as e:
        # Mark error
        service.update_media_processing(
            media_id,
            error_message=str(e)
        )
```

### 3. Database Administrator Integration

**File to integrate with**: `app/database/mock_dynamodb.py`

The Database Administrator (BDSD Douglas) will:

- Design the DynamoDB table schema
- Replace `MockDynamoDB` with actual AWS DynamoDB client
- Implement proper indexing for queries
- Handle backups and disaster recovery

```python
# Future implementation
from boto3.dynamodb.conditions import Key

class DynamoDBAdapter:
    def __init__(self, table_name):
        self.table = dynamodb.Table(table_name)
    
    def put_item(self, item_id, item):
        self.table.put_item(Item=item)
    
    def get_item(self, item_id):
        response = self.table.get_item(Key={'media_id': item_id})
        return response.get('Item')
    
    # ... implement other methods
```

### 4. Frontend/DevOps Integration

**Files involved**:
- `app/services/media_service.py`
- `app/config.py`
- Database connection string
- Logging configuration

---

## Troubleshooting

### Issue: Database file not found

**Solution**: The database will be created automatically. Ensure write permissions in the backend directory.

```bash
ls -la  # Check directory permissions
chmod 755 backend  # Grant permissions if needed
```

### Issue: Import errors

**Solution**: Ensure all packages are installed.

```bash
pip install -r requirements.txt
python -c "import app.services; print('OK')"
```

### Issue: Simulation tests fail

**Solution**: Run with verbose output.

```bash
python -u simulation/run_simulation.py
```

### Issue: Media not persisting

**Solution**: Check that `media_db.json` exists and is writable.

```bash
ls -la media_db.json
cat media_db.json  # View database content
```

### Issue: Service returns False

**Solution**: Check logs for detailed error messages.

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Key Points for Integration

### ✓ Do's
- ✓ Use `MediaService` for all business logic
- ✓ Call `create_media()` for uploads
- ✓ Send queue messages after uploads
- ✓ Call `update_media_processing()` after work completes
- ✓ Handle return values: `(success: bool, data, message: str)`
- ✓ Use unique media_id (UUID) for all records

### ✗ Don'ts
- ✗ Don't call database directly (use service layer)
- ✗ Don't update status without service
- ✗ Don't create duplicate records
- ✗ Don't ignore validation errors
- ✗ Don't mix cloud and mock implementations

---

## Next Steps

1. **Share this with team members** in their respective roles
2. **API Developer**: Check `API_INTEGRATION.md` for endpoint details
3. **Worker Developer**: Check for worker integration examples
4. **Database Admin**: Plan DynamoDB migration
5. **Frontend/DevOps**: Set up Docker containers
6. **Project Lead**: Coordinate integration testing

---

## Contact & Support

**Backend Developer**: PHDB Nayanakantha

For questions about:
- Media data model → See `app/models/media.py`
- Service methods → See `app/services/media_service.py`
- Database operations → See `app/database/mock_dynamodb.py`
- Integration → See `INTEGRATION_GUIDE.md`

---

**Last Updated**: April 2026
**Status**: Ready for Integration

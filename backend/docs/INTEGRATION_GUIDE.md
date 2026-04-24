# Integration Guide for Team Members
## Group A - Media Sharing Platform

This guide explains how each team member integrates with the backend.

---

## 1. API Developer (L.K.D.H. Perera)

### Integration Points

Your Flask/Express API will use `MediaService` for all operations.

#### Upload Endpoint

```python
from app.database import MockDynamoDB
from app.services import MediaService
from app.utils import MockSQS

db = MockDynamoDB()
service = MediaService(db)
queue = MockSQS()

@app.route('/api/upload', methods=['POST'])
def upload_media():
    """Upload media file and metadata."""
    try:
        # Get file and metadata
        file = request.files['file']
        title = request.form['title']
        uploader = request.form['uploader']
        description = request.form.get('description')
        
        # Determine media type
        media_type = 'image' if file.content_type.startswith('image') else 'video'
        
        # Save to S3 (your responsibility)
        s3_key = save_to_s3(file)
        
        # Call backend to create media record
        success, media, msg = service.create_media(
            title=title,
            uploader=uploader,
            object_key=s3_key,
            file_size=file.content_length,
            media_type=media_type,
            description=description
        )
        
        if success:
            # Send processing job to queue
            queue.send_message({
                'media_id': media.media_id,
                'object_key': media.object_key,
                'action': 'generate_thumbnail'
            })
            
            return jsonify({
                'success': True,
                'media_id': media.media_id,
                'status': media.status,
                'message': 'Upload successful'
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': msg
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/list', methods=['GET'])
def list_media():
    """List all uploaded media."""
    try:
        success, media_list, msg = service.list_all_media()
        
        if success:
            return jsonify({
                'success': True,
                'count': len(media_list),
                'media': [m.to_dict() for m in media_list]
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': msg
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/status/<media_id>', methods=['GET'])
def get_status(media_id):
    """Get media status."""
    try:
        success, media, msg = service.get_media(media_id)
        
        if success:
            return jsonify({
                'success': True,
                'media': media.to_dict()
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': msg
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

#### Expected Return Format

Always return JSON in this format:

```json
{
  "success": true/false,
  "media_id": "uuid",
  "status": "pending|processing|done|error",
  "media": {
    "media_id": "uuid",
    "title": "string",
    "uploader": "string",
    "object_key": "s3://...",
    "status": "string",
    "thumbnail_key": "s3://... or null",
    "created_at": "ISO timestamp",
    "updated_at": "ISO timestamp",
    "file_size": 12345,
    "media_type": "image|video",
    "description": "string or null",
    "error_message": "string or null"
  },
  "message": "string"
}
```

### Testing Your Integration

```python
# Test API with backend
from app.database import MockDynamoDB
from app.services import MediaService

db = MockDynamoDB()
service = MediaService(db)

# Create test media
success, media, msg = service.create_media(
    title="Test Video",
    uploader="TestUser",
    object_key="s3://bucket/test.mp4",
    file_size=1000,
    media_type="video"
)

print(f"Created: {media.media_id}")
print(f"Status: {media.status}")
```

---

## 2. Worker/Processor Developer (DMPT Dissanayake)

### Integration Points

Your worker function will consume messages and update media status.

#### Worker Implementation

```python
from app.database import MockDynamoDB
from app.services import MediaService
from app.utils import MockSQS
import boto3
import json

db = MockDynamoDB()
service = MediaService(db)
queue = MockSQS()

def process_media(event, context):
    """
    AWS Lambda handler for media processing.
    Triggered by SQS message.
    """
    try:
        # Get message from SQS (in real AWS, this is handled automatically)
        messages = queue.receive_messages(max_number=1)
        
        if not messages:
            print("No messages to process")
            return
        
        message = messages[0]
        body = json.loads(message['Body'])
        
        media_id = body['media_id']
        object_key = body['object_key']
        
        print(f"Processing media: {media_id}")
        
        # Step 1: Mark as processing
        service.update_media_status(media_id, 'processing')
        print(f"Status updated to: processing")
        
        try:
            # Step 2: Download from S3
            s3 = boto3.client('s3')
            bucket, key = parse_s3_path(object_key)
            local_file = f"/tmp/{media_id}"
            s3.download_file(bucket, key, local_file)
            print(f"Downloaded: {local_file}")
            
            # Step 3: Generate thumbnail
            thumbnail_path = generate_thumbnail(local_file, media_id)
            print(f"Thumbnail generated: {thumbnail_path}")
            
            # Step 4: Upload thumbnail to S3
            thumbnail_key = upload_to_s3(thumbnail_path)
            print(f"Thumbnail uploaded: {thumbnail_key}")
            
            # Step 5: Mark as done with thumbnail key
            success, msg = service.update_media_processing(
                media_id,
                thumbnail_key=thumbnail_key
            )
            
            if success:
                print(f"Media processing completed: {media_id}")
                
                # Delete message from queue
                queue.delete_message(message['MessageId'])
                print(f"Message deleted from queue")
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'success': True,
                        'media_id': media_id,
                        'message': 'Processing completed'
                    })
                }
            else:
                raise Exception(f"Failed to update media: {msg}")
                
        except Exception as e:
            # Mark as error
            error_msg = f"Processing failed: {str(e)}"
            success, msg = service.update_media_processing(
                media_id,
                error_message=error_msg
            )
            
            print(f"ERROR: {error_msg}")
            
            # Don't delete message, let it retry
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'media_id': media_id,
                    'error': error_msg
                })
            }
            
    except Exception as e:
        print(f"Worker error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }

def generate_thumbnail(media_file: str, media_id: str) -> str:
    """Generate thumbnail from media file."""
    from PIL import Image
    import ffmpeg
    
    # Detect file type
    if media_file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        # Image thumbnail
        img = Image.open(media_file)
        img.thumbnail((150, 150))
        thumb_path = f"/tmp/{media_id}_thumb.jpg"
        img.save(thumb_path)
    else:
        # Video thumbnail using ffmpeg
        thumb_path = f"/tmp/{media_id}_thumb.jpg"
        ffmpeg.input(media_file, ss='00:00:01').output(
            thumb_path,
            vframes=1,
            q=5
        ).run()
    
    return thumb_path

def parse_s3_path(s3_path: str) -> tuple:
    """Parse S3 path into bucket and key."""
    # s3://bucket/path/to/file -> (bucket, path/to/file)
    parts = s3_path.replace('s3://', '').split('/', 1)
    return parts[0], parts[1] if len(parts) > 1 else ''

def upload_to_s3(local_file: str) -> str:
    """Upload file to S3 and return S3 key."""
    import boto3
    s3 = boto3.client('s3')
    
    bucket = 'media-sharing-bucket'
    key = f"thumbnails/{os.path.basename(local_file)}"
    
    s3.upload_file(local_file, bucket, key)
    return f"s3://{bucket}/{key}"
```

#### Status Workflow

```
1. Message in Queue
   ↓
2. Worker receives message
   ↓
3. service.update_media_status(media_id, 'processing')
   ↓
4. Worker processes media
   ├→ If success:
   │  service.update_media_processing(media_id, thumbnail_key=...)
   │
   └→ If error:
      service.update_media_processing(media_id, error_message=...)
   ↓
5. Delete message from queue (only on success)
   ↓
6. Next request to API shows updated status
```

### Testing Worker Integration

```python
# Test worker logic
from app.database import MockDynamoDB
from app.services import MediaService

db = MockDynamoDB()
service = MediaService(db)

# Create media
success, media, msg = service.create_media(
    title="Worker Test",
    uploader="WorkerTest",
    object_key="s3://bucket/test.mp4",
    file_size=1000,
    media_type="video"
)

media_id = media.media_id
print(f"Initial status: {media.status}")

# Simulate worker processing
service.update_media_status(media_id, 'processing')
success, media, msg = service.get_media(media_id)
print(f"After processing started: {media.status}")

service.update_media_processing(media_id, thumbnail_key="s3://bucket/thumb.jpg")
success, media, msg = service.get_media(media_id)
print(f"After processing done: {media.status}")
print(f"Thumbnail: {media.thumbnail_key}")
```

---

## 3. Database Administrator (BDSD Douglas)

### Integration Points

You will manage the database layer and schema.

#### Current Mock Implementation

```python
from app.database import MockDynamoDB

db = MockDynamoDB(storage_file="media_db.json")

# All operations available
db.put_item(media_id, media_dict)
db.get_item(media_id)
db.update_item(media_id, updates)
db.delete_item(media_id)
db.scan()
db.query_by_status(status)
```

#### Future DynamoDB Implementation

Replace `MockDynamoDB` with AWS SDK:

```python
import boto3
from boto3.dynamodb.conditions import Key, Attr

class DynamoDBHandler:
    def __init__(self, table_name='Media', region='us-east-1'):
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
    
    def create_table(self):
        """Create DynamoDB table (one-time setup)."""
        self.dynamodb.create_table(
            TableName='Media',
            KeySchema=[
                {'AttributeName': 'media_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'media_id', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'},
                {'AttributeName': 'uploader', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'status-index',
                    'KeySchema': [
                        {'AttributeName': 'status', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    'IndexName': 'uploader-index',
                    'KeySchema': [
                        {'AttributeName': 'uploader', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
    
    def put_item(self, item):
        """Store item in DynamoDB."""
        response = self.table.put_item(Item=item)
        return response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    def get_item(self, media_id):
        """Retrieve item from DynamoDB."""
        response = self.table.get_item(Key={'media_id': media_id})
        return response.get('Item')
    
    def query_by_status(self, status):
        """Query by status using GSI."""
        response = self.table.query(
            IndexName='status-index',
            KeyConditionExpression=Key('status').eq(status)
        )
        return response.get('Items', [])
```

#### Schema Design

```
Table: Media
- Primary Key: media_id (String)
- GSI 1: status (for queries by status)
- GSI 2: uploader (for queries by uploader)

Attributes:
- media_id: String (UUID)
- title: String
- uploader: String
- object_key: String (S3 path)
- status: String (pending|processing|done|error)
- thumbnail_key: String (optional)
- created_at: String (ISO timestamp)
- updated_at: String (ISO timestamp)
- file_size: Number
- media_type: String (image|video)
- description: String (optional)
- error_message: String (optional)

Indexes:
- status-index: Query all pending/done media quickly
- uploader-index: Query by user quickly
```

#### Backup & Recovery

```python
# Export data for backup
def backup_database():
    all_items = db.scan()
    with open('backup.json', 'w') as f:
        json.dump(all_items, f)

# Restore from backup
def restore_database(backup_file):
    with open(backup_file, 'r') as f:
        items = json.load(f)
    for item in items:
        db.put_item(item['media_id'], item)
```

---

## 4. Frontend/DevOps Specialist (KKVRM Kalyanapriya)

### Integration Points

You'll containerize and deploy the backend.

#### Docker Integration

```dockerfile
# Dockerfile for backend
FROM python:3.9-slim

WORKDIR /app

# Copy backend code
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/app ./app

# Run Flask API or worker
CMD ["python", "-m", "flask", "run"]
```

#### Docker Compose Setup

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "5000:5000"
    environment:
      - FLASK_APP=app.py
      - FLASK_ENV=development
      - DB_FILE=media_db.json
    volumes:
      - ./backend:/app

  localstack:  # Local AWS simulation
    image: localstack/localstack
    ports:
      - "4566:4566"
    environment:
      - SERVICES=s3,sqs,dynamodb
      - DEBUG=1

  worker:
    build: ./backend
    command: python worker.py
    depends_on:
      - backend
      - localstack
    environment:
      - AWS_ENDPOINT_URL=http://localstack:4566
```

#### Deployment Checklist

- [ ] Configure environment variables
- [ ] Set up S3 bucket
- [ ] Set up SQS queue
- [ ] Create DynamoDB table
- [ ] Set up CloudWatch logging
- [ ] Configure IAM roles/permissions
- [ ] Test end-to-end flow
- [ ] Monitor resource usage (stay in free tier)

---

## 5. Project Lead (JARN Jayasinghe)

### Integration Coordination

Ensure all parts work together:

1. **Testing Checklist**:
   - [ ] Backend simulation passes all tests
   - [ ] API endpoints work with service
   - [ ] Worker can process messages
   - [ ] Database persists data
   - [ ] End-to-end flow works

2. **Integration Testing**:

```python
# integration_test.py
from app.database import MockDynamoDB
from app.services import MediaService
from app.utils import MockSQS
import time

db = MockDynamoDB()
service = MediaService(db)
queue = MockSQS()

# Full workflow
success, media, msg = service.create_media(
    title="Integration Test",
    uploader="TestUser",
    object_key="s3://bucket/test.mp4",
    file_size=1000,
    media_type="video"
)

assert success, "Create failed"
media_id = media.media_id

# Queue processing job
queue.send_message({
    'media_id': media_id,
    'object_key': media.object_key
})

# Simulate worker
service.update_media_status(media_id, 'processing')
service.update_media_processing(media_id, thumbnail_key="s3://bucket/thumb.jpg")

# Verify final state
success, final_media, msg = service.get_media(media_id)
assert final_media.is_done(), "Final state incorrect"
print("✓ Integration test passed")
```

---

## Summary of Integration Points

| Component | Uses Backend Via | Key Methods |
|-----------|------------------|-------------|
| API | `MediaService` | `create_media()`, `get_media()`, `list_all_media()` |
| Worker | `MediaService` | `update_media_status()`, `update_media_processing()` |
| Database | `MockDynamoDB` | `put_item()`, `get_item()`, `update_item()` |
| Frontend | API responses | JSON from media records |
| DevOps | Docker files | Container configuration |

---

**All parts are now ready for integration!**

See `BACKEND_GUIDE.md` for detailed backend documentation.

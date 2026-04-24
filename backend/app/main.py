"""
Main application entry point
Flask API server for Media Sharing Platform
"""

from flask import Flask, request, jsonify
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import MockDynamoDB
from app.services import MediaService
from app.utils import MockSQS
from app.config import *

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Initialize backend components
db = MockDynamoDB(storage_file=DB_FILE)
media_service = MediaService(db)
queue = MockSQS()

logger.info(f"Backend initialized - Service Version: {SERVICE_VERSION}")


# Health Check Endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        is_healthy = media_service.health_check()
        
        if is_healthy:
            return jsonify({
                'status': 'healthy',
                'service': SERVICE_NAME,
                'version': SERVICE_VERSION,
                'database': 'OK'
            }), 200
        else:
            return jsonify({
                'status': 'unhealthy',
                'service': SERVICE_NAME,
                'error': 'Database check failed'
            }), 503
            
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


# Statistics Endpoint
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics."""
    try:
        stats = media_service.get_statistics()
        
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# List All Media Endpoint
@app.route('/api/list', methods=['GET'])
def list_media():
    """List all uploaded media."""
    try:
        status_filter = request.args.get('status')
        uploader_filter = request.args.get('uploader')
        
        if status_filter:
            success, media_list, msg = media_service.list_media_by_status(status_filter)
        elif uploader_filter:
            success, media_list, msg = media_service.list_media_by_uploader(uploader_filter)
        else:
            success, media_list, msg = media_service.list_all_media()
        
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
        logger.error(f"Error listing media: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Get Media Status Endpoint
@app.route('/api/status/<media_id>', methods=['GET'])
def get_media_status(media_id):
    """Get status of a specific media."""
    try:
        success, media, msg = media_service.get_media(media_id)
        
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
        logger.error(f"Error getting media status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Placeholder: Upload Endpoint (to be implemented by API Developer)
@app.route('/api/upload', methods=['POST'])
def upload_media():
    """
    Upload media file and create metadata record.
    This is a placeholder - implement with actual file handling.
    """
    try:
        # Expected form data: title, uploader, file, description (optional)
        title = request.form.get('title')
        uploader = request.form.get('uploader')
        description = request.form.get('description')
        
        # For now, create without file (file handling to be added)
        if not title or not uploader:
            return jsonify({
                'success': False,
                'error': 'title and uploader are required'
            }), 400
        
        # Simulate S3 upload (actual implementation in API layer)
        object_key = f"s3://bucket/uploads/{title.lower()}"
        file_size = 1000  # Placeholder
        media_type = 'video'  # Placeholder
        
        success, media, msg = media_service.create_media(
            title=title,
            uploader=uploader,
            object_key=object_key,
            file_size=file_size,
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
                'message': 'Media upload initiated'
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': msg
            }), 400
            
    except Exception as e:
        logger.error(f"Error uploading media: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Error Handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    logger.info(f"Starting {SERVICE_NAME} on port 5000")
    app.run(host='0.0.0.0', port=5000, debug=DEBUG)

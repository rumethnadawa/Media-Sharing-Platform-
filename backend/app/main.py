"""backend.app.main

Flask API server + local dev UI server for the Media Sharing Platform.

This file intentionally supports both legacy routes (e.g. /api/list) and the
frontend's simpler routes (e.g. /list) so the HTML pages in /frontend can run
without modification.
"""

from flask import Flask, request, jsonify, redirect, send_from_directory
import logging
import sys
import os
import mimetypes
from werkzeug.utils import secure_filename

# Ensure the backend root (parent of the `app` package) is on sys.path.
BACKEND_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, BACKEND_DIR)

# Workspace paths
REPO_DIR = os.path.abspath(os.path.join(BACKEND_DIR, os.pardir))
FRONTEND_DIR = os.path.join(REPO_DIR, 'frontend')
UPLOADS_DIR = os.path.join(BACKEND_DIR, 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)

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
db_file_path = DB_FILE
if not os.path.isabs(db_file_path):
    db_file_path = os.path.join(BACKEND_DIR, db_file_path)
db = MockDynamoDB(storage_file=db_file_path)
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
@app.route('/stats', methods=['GET'])
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
@app.route('/list', methods=['GET'])
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
@app.route('/status/<media_id>', methods=['GET'])
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


# Upload Endpoint
@app.route('/api/upload', methods=['POST'])
@app.route('/upload', methods=['POST'])
def upload_media():
    """Upload a media file (local dev) and create metadata record."""
    try:
        # Expected multipart/form-data: title, uploader, file, description (optional)
        title = request.form.get('title')
        uploader = request.form.get('uploader')
        description = request.form.get('description')

        file = request.files.get('file')
        
        if not title or not uploader:
            return jsonify({
                'success': False,
                'error': 'title and uploader are required'
            }), 400

        if not file or not getattr(file, 'filename', ''):
            return jsonify({
                'success': False,
                'error': 'file is required'
            }), 400

        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({
                'success': False,
                'error': 'invalid filename'
            }), 400

        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext and ext not in ALLOWED_EXTENSIONS:
            return jsonify({
                'success': False,
                'error': f'file type .{ext} is not allowed'
            }), 400

        # Save locally (dev mode). Store only the base filename in DB.
        local_name = f"{uploader}_{filename}".replace(' ', '_')
        local_name = secure_filename(local_name)
        save_path = os.path.join(UPLOADS_DIR, local_name)
        file.save(save_path)

        file_size = os.path.getsize(save_path)
        content_type = (file.mimetype or mimetypes.guess_type(filename)[0] or '').lower()
        media_type = 'video' if content_type.startswith('video') or ext in {'mp4', 'avi', 'mov'} else 'image'
        
        object_key = local_name
        
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
            
            # Auto-process to done for local dev without worker
            media_service.update_media_processing(media.media_id, thumbnail_key=None)
            media.status = 'done'

            media_url = f"/files/{media.object_key}"
            
            return jsonify({
                'success': True,
                'media_id': media.media_id,
                'status': media.status,
                'media_url': media_url,
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


@app.route('/files/<path:filename>', methods=['GET'])
def get_uploaded_file(filename: str):
    """Serve a locally uploaded file from the uploads directory."""
    return send_from_directory(UPLOADS_DIR, filename, as_attachment=False)


@app.route('/media', methods=['GET'])
def get_media_metadata_or_file():
    """Frontend-friendly endpoint: GET /media?id=<media_id>.

    Returns JSON with metadata + a `media_url` pointing to `/files/...`.
    """
    media_id = request.args.get('id')
    if not media_id:
        return jsonify({'success': False, 'error': 'missing id'}), 400

    success, media, msg = media_service.get_media(media_id)
    if not success or not media:
        return jsonify({'success': False, 'error': msg}), 404

    media_dict = media.to_dict()
    object_key = media_dict.get('object_key') or ''
    media_url = f"/files/{object_key}" if object_key else ''

    # Best-effort content type for previews
    content_type = mimetypes.guess_type(object_key)[0] or ''

    return jsonify({
        'success': True,
        'media': {
            **media_dict,
            'media_url': media_url,
            'content_type': content_type,
        }
    }), 200


# Download Endpoint
@app.route('/api/download/<media_id>', methods=['GET'])
@app.route('/download/<media_id>', methods=['GET'])
def download_media(media_id):
    """Download a media file."""
    try:
        success, media, msg = media_service.get_media(media_id)
        if not success or not media:
            return jsonify({'success': False, 'error': msg}), 404

        filename = media.object_key
        return send_from_directory(UPLOADS_DIR, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading media: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Delete Endpoint
@app.route('/api/media/<media_id>', methods=['DELETE'])
@app.route('/media/<media_id>', methods=['DELETE'])
def delete_media(media_id):
    """Delete a media file and its metadata."""
    try:
        success, media, msg = media_service.get_media(media_id)
        if not success or not media:
            return jsonify({'success': False, 'error': msg}), 404

        # Remove from db
        del_success, del_msg = media_service.delete_media(media_id)
        if not del_success:
            return jsonify({'success': False, 'error': del_msg}), 500

        # Remove file from uploads directory
        filename = media.object_key
        file_path = os.path.join(UPLOADS_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        return jsonify({'success': True, 'message': 'Media deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting media: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# --- Local Dev UI (serves /frontend) ---
@app.route('/', methods=['GET'])
def ui_root():
    if os.path.isfile(os.path.join(FRONTEND_DIR, 'media-list.html')):
        return redirect('/media-list.html')
    return jsonify({'success': False, 'error': 'frontend not found'}), 404


@app.route('/<path:filename>', methods=['GET'])
def ui_static(filename: str):
    # Avoid serving over API routes (these have explicit handlers anyway)
    full_path = os.path.join(FRONTEND_DIR, filename)
    if os.path.isfile(full_path):
        return send_from_directory(FRONTEND_DIR, filename)
    return jsonify({'success': False, 'error': 'Not found'}), 404


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

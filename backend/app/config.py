"""
Configuration module
"""

import os
from datetime import timedelta

# Application Settings
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# Database Settings
DB_FILE = os.getenv('DB_FILE', 'media_db.json')
DB_TYPE = os.getenv('DB_TYPE', 'mock')  # 'mock' or 'dynamodb'

# AWS Settings (for cloud deployment)
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')

# S3 Settings
S3_BUCKET = os.getenv('S3_BUCKET', 'media-sharing-bucket')
S3_ENDPOINT = os.getenv('S3_ENDPOINT', None)

# SQS Settings
SQS_QUEUE_NAME = os.getenv('SQS_QUEUE_NAME', 'media-processing-queue')
SQS_ENDPOINT = os.getenv('SQS_ENDPOINT', None)

# DynamoDB Settings
DYNAMODB_TABLE_NAME = os.getenv('DYNAMODB_TABLE_NAME', 'Media')
DYNAMODB_ENDPOINT = os.getenv('DYNAMODB_ENDPOINT', None)

# File Upload Settings
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'avi', 'mov']
ALLOWED_MEDIA_TYPES = ['image', 'video']

# Processing Settings
THUMBNAIL_SIZE = (150, 150)
VIDEO_THUMBNAIL_QUALITY = 5  # 0-10, lower is better quality

# API Settings
API_VERSION = 'v1'
API_TITLE = 'Media Sharing Platform API'
API_DESCRIPTION = 'Backend API for distributed media sharing system'

# Logging Settings
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Service Configuration
SERVICE_NAME = 'MediaBackendService'
SERVICE_VERSION = '1.0.0'

# Timeout Settings (in seconds)
PROCESSING_TIMEOUT = 300
DATABASE_TIMEOUT = 30
QUEUE_POLL_INTERVAL = 5

# Retry Settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Features
ENABLE_LOGGING = True
ENABLE_METRICS = True
ENABLE_MONITORING = True

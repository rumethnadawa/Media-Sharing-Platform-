"""
Database package - Database operations for Media Sharing Platform
"""

from .mock_dynamodb import MockDynamoDB
from .interface import DatabaseInterface

__all__ = ['MockDynamoDB', 'DatabaseInterface']

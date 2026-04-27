"""
Database package - Database operations for Media Sharing Platform
"""

from .mock_dynamodb import MockDynamoDB
from .real_dynamodb import RealDynamoDB
from .interface import DatabaseInterface

__all__ = ['MockDynamoDB', 'RealDynamoDB', 'DatabaseInterface']

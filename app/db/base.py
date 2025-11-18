"""
Database base module.

This module provides the declarative base for all SQLAlchemy models.
"""

from sqlalchemy.orm import declarative_base

# Create the declarative base that will be used by all models
Base = declarative_base()

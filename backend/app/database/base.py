"""
Shared SQLAlchemy declarative base and metadata.

Kept separate from `session.py` so Alembic can import models
without circular imports involving the engine/session factory.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""

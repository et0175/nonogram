"""Database connection and session management."""

# Re-export from session.py for backwards compatibility
from .session import (
    DATABASE_URL,
    engine,
    SessionLocal,
    get_session,
    get_db,
    session_scope,
)
from .models import Base

__all__ = [
    'DATABASE_URL',
    'engine',
    'SessionLocal',
    'get_session',
    'get_db',
    'session_scope',
    'Base',
]

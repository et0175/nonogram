"""Database connection and session management."""

import os

from . import session as _session
from .session import get_session, get_db, session_scope
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


def __getattr__(name):
    """Forward engine/SessionLocal/DATABASE_URL to session.py dynamically.

    A plain ``from .session import engine`` above would copy whatever
    session.engine happened to be at THIS module's first import — which is
    always None, since nothing has called _init_engine() yet at that point.
    That stale copy would never reflect a later-initialized (or
    later-changed) engine, silently breaking any caller doing
    ``from nonogram.db import engine``. Routing the access through
    __getattr__ (PEP 562) makes it a fresh lookup on session.py's own
    module-level state every time, initializing the engine on demand for
    the current DATABASE_URL.
    """
    if name in ('engine', 'SessionLocal'):
        _session._init_engine()
        return getattr(_session, name)
    if name == 'DATABASE_URL':
        return os.getenv('DATABASE_URL', None)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

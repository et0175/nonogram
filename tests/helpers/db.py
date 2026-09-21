"""Shared plumbing for tests that need a real database (CARD-102).

Three test files were each building their own SQLite engine and each passing a
made-up batch id to ``add_puzzle``. That worked only because SQLite does not
enforce foreign keys unless asked; Postgres, which production runs, refused
every one of those inserts. The conftest now asks, so the shortcut fails
everywhere at once — and the fix is here rather than repeated per file,
because the habit was the defect and a helper is what stops it coming back.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager


def sqlite_session_scope(tmp_path, filename: str = "admin.db"):
    """A session factory over a fresh SQLite file, with the schema created.

    Foreign keys are enforced on it: ``tests/conftest.py`` registers the
    ``PRAGMA`` against SQLAlchemy's ``Engine`` class, so an engine built here
    is covered without this function saying anything about it.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from nonogram.db.models import Base

    engine = create_engine(f"sqlite:///{tmp_path / filename}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    @contextmanager
    def scope():
        db = factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    return scope


def make_batch(
    session_factory,
    batch_id: str | None = None,
    *,
    source: str = "images",
    total_count: int = 0,
) -> str:
    """Insert a real ``batches`` row and return its id as a string.

    ``puzzles.batch_id`` is a foreign key to this table. A test that wants its
    puzzles to belong to a batch has to make the batch — there is no such
    thing as a puzzle in a batch that does not exist, and until CARD-102 the
    suite believed otherwise.
    """
    from nonogram.db.models import Batch

    batch_id = batch_id or str(uuid.uuid4())
    with session_factory() as db:
        db.add(
            Batch(
                id=uuid.UUID(batch_id),
                status="complete",
                source=source,
                total_count=total_count,
            )
        )
    return batch_id

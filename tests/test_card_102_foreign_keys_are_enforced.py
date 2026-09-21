"""CARD-102 — the test database enforces what the real one enforces.

SQLite ignores foreign keys unless each connection asks it to; Postgres always
enforces them. Until this card the suite built SQLite engines that never asked,
so every DB-mode test ran with referential integrity off while standing in for
a database that has it on — and 43 of them inserted puzzles against batch ids
that did not exist. They passed. Against Postgres not one of them could insert
a row.

This file is the guard on the arrangement itself. Without it the ``PRAGMA`` in
``conftest.py`` is a line nobody would miss if it were deleted, and the suite
would quietly return to being green about the wrong database.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from nonogram.admin.puzzle_review import PuzzleReviewService
from tests.helpers.db import make_batch, sqlite_session_scope


def _add(store, batch_id):
    return store.add_puzzle(
        grid=[[True] * 10 for _ in range(10)],
        clues_rows=[[10]] * 10,
        clues_cols=[[10]] * 10,
        width=10,
        height=10,
        theme="test",
        difficulty_score=10,
        difficulty_tier="easy",
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
        batch_id=batch_id,
        source_image="p.png",
    )


def test_a_puzzle_cannot_belong_to_a_batch_that_does_not_exist(tmp_path):
    """AC-3: the enforcement is on, and this test is how you find out.

    The exact insert that passed 43 times over, now refused — by SQLite, for
    the same reason and with the same meaning as the
    ``fk_puzzles_batch_id_batches`` violation Postgres raised when this was
    first noticed.
    """
    store = PuzzleReviewService(session_factory=sqlite_session_scope(tmp_path))

    with pytest.raises(IntegrityError) as excinfo:
        _add(store, str(uuid.uuid4()))

    assert "FOREIGN KEY" in str(excinfo.value).upper()


def test_a_puzzle_in_a_real_batch_is_stored(tmp_path):
    """The control: enforcement refuses the wrong thing, not everything."""
    scope = sqlite_session_scope(tmp_path)
    store = PuzzleReviewService(session_factory=scope)
    batch_id = make_batch(scope)

    puzzle_id = _add(store, batch_id)

    assert store.get_puzzle(puzzle_id)["batch_id"] == batch_id


def test_the_pragma_is_actually_set_on_a_connection(tmp_path):
    """Named directly, so deleting the conftest listener fails here first.

    Asserting the behaviour above would also catch it, but this says *why* in
    one line and points at the place to look.
    """
    scope = sqlite_session_scope(tmp_path)

    with scope() as db:
        assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1

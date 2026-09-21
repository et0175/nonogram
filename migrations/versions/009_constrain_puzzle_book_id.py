"""Constrain puzzles.book_id with a foreign key to books (CARD-103).

The column has recorded book membership since CARD-100 — every in-book guard
in the admin panel reads it — and nothing has ever checked that the book it
names exists. ``ON DELETE SET NULL`` so that deleting a book releases its
puzzles rather than leaving them pointing at nothing, matching what
``BookManager.remove_puzzle_from_book`` does one puzzle at a time.

**This migration will fail, loudly and without changing anything, if any row
violates it** — a ``book_id`` naming a book that is not in ``books``. That is
the intended behaviour and not a reason to force it: run
``python -m nonogram.admin.book_membership`` first, resolve anything it reports
as claimed by two books, and only then upgrade. PostgreSQL validates the
existing rows as part of ``ADD CONSTRAINT``, inside the transaction alembic
already wraps this in.

Revision ID: 009
Revises: 008
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None

_CONSTRAINT = 'fk_puzzles_book_id_books'


def upgrade() -> None:
    """Add the foreign key.

    ``batch_alter_table`` because SQLite cannot ``ALTER TABLE … ADD
    CONSTRAINT`` and recreates the table instead; on PostgreSQL, which is what
    production runs, this emits a plain ``ADD CONSTRAINT``.
    """
    with op.batch_alter_table('puzzles') as batch_op:
        batch_op.create_foreign_key(
            _CONSTRAINT,
            'books',
            ['book_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    """Drop it, leaving the column and its data untouched."""
    with op.batch_alter_table('puzzles') as batch_op:
        batch_op.drop_constraint(_CONSTRAINT, type_='foreignkey')

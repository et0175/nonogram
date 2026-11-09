"""Store what the title page prints beyond the title (owner, 2026-11-09).

Adds three nullable string columns to ``books``: ``subtitle``,
``series_name`` and ``authors``. Interior page 1 is a title and copyright
page (``BookPDFGenerator.vector_title_contents``); it prints the book's
title, and with these it can also print the series the book belongs to,
its subtitle, and who wrote it — the last also named in the copyright line.

They follow 018 (``player_domain``) in shape and in reasoning: short
per-book facts, read when the book is printed, never queried across books,
so they go on the row rather than in a table of their own. **No default and
no backfill**, as there: nobody has chosen a subtitle, a series or an author
line for any existing book, and the title page would rather print nothing
than print a guess. NULL means "not set", and the page leaves that line out.

**Rolling back.** Rolling the *code* back is safe: older code does not know
the columns and prints the plain title page. Rolling the *migration* back
drops the columns, so every book's stored values are lost and have to be
entered again on the General info step.

Revision ID: 020
Revises: 019
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None

#: The three columns, in the order they are added (and dropped in reverse).
TITLE_PAGE_COLUMNS = ('subtitle', 'series_name', 'authors')


def upgrade() -> None:
    # Batch mode for SQLite compatibility, like 004-019. Nullable, no server
    # default and no UPDATE: every existing row keeps NULL — see above.
    with op.batch_alter_table('books') as batch_op:
        for name in TITLE_PAGE_COLUMNS:
            batch_op.add_column(sa.Column(name, sa.String(), nullable=True))


def downgrade() -> None:
    """Drop the three columns; every other column and its data are untouched."""
    with op.batch_alter_table('books') as batch_op:
        for name in reversed(TITLE_PAGE_COLUMNS):
            batch_op.drop_column(name)

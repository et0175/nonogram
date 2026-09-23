"""Store a book's below-floor overrides with the book (CARD-121, FR-031, INV-006).

Adds one nullable JSON column, ``books.floor_overrides``: the puzzle ids the
owner admitted below NFR-008's 4.8 mm printed-cell floor (TERM-024/TERM-025),
as a flat list of id strings. INV-006 is enforced where membership is written
(``BookManager.add_puzzles_to_book``), and this column is the "stored with the
book" half of it — without somewhere to keep the override, a below-floor puzzle
could only ever be refused.

**Why a column and not a table.** The override is a set of ids that belongs to
exactly one book, is read and written in the same breath as ``puzzle_ids``, is
bounded by the book's own puzzle count (~150, ADR-0034), and is never queried
across books. A join table would buy referential integrity it cannot use —
``puzzle_ids`` beside it is already a JSON list of the same ids — at the cost of
a second write path and a second transaction boundary on every add. The two
neighbouring precedents (010's ``distribution_plan``, 004's print columns) both
keep per-book documents on the row; this follows them.

**No backfill.** Books that exist before this migration get NULL, which the
store reads as "no override was ever given" — the fail-closed reading, because
a member below the floor then needs an override before it may be added again.
Nothing is removed from any existing book: the floor gates *adds*, never the
selection a book already holds, so a legacy book keeps every puzzle it has.

Rolling the code back is safe for the same reason as 010: older code does not
know the column and simply ignores it. Rolling the *migration* back drops the
overrides, so a book reassembled afterwards would be asked for them again —
which is refusing rather than admitting, the safe direction.

Revision ID: 012
Revises: 011
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode for SQLite compatibility, like 004–011.
    with op.batch_alter_table('books') as batch_op:
        batch_op.add_column(sa.Column('floor_overrides', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Drop the column; every other column and its data are untouched."""
    with op.batch_alter_table('books') as batch_op:
        batch_op.drop_column('floor_overrides')

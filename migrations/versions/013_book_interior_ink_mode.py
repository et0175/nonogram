"""Store how a book's interior is printed (CARD-147; owner intake 2026-09-25).

Adds one nullable string column, ``books.interior_ink_mode``: ``'bw'`` or
``'colour'``, the two values of
:class:`nonogram.admin.book_page_spec.InkMode`. It is the second thing a book
stores about how it is *printed* rather than how it is *laid out* — the first
being the trim and the margins migrations 004/011 added — and it decides
exactly one thing: the colour space the interior's pages are composed and
written in. No page size, margin, cell, rule or count depends on it, so
ADR-0036/R1's geometry is untouched by this column.

There is deliberately no FR to cite: this is owner intake recorded at
``meta/architecture/inputs/raw-requirements.md`` (2026-09-25, "2 modes to pdf
generator: black/white and colors … we may add colors for book2") that the
architect station has not formalised.

**Why a column and not a table.** The mode is one short enumerated value that
belongs to exactly one book, is read in the same breath as ``trim_width_cm``
and is never queried across books. Its four neighbours — 004's and 011's print
columns, 010's ``distribution_plan`` and 012's ``floor_overrides`` — all keep
per-book print facts on the row; this follows them.

**Existing rows get the default, and they get it here.** Every book that
exists today is black-and-white in content, so the mode they must read as is
``'bw'``. Three things make that true, deliberately belt and braces, because
the cost of a book printing as colour by accident is money:

1. the column is added with a server default of ``'bw'``, which on PostgreSQL
   and on SQLite's ``ALTER TABLE ADD COLUMN`` fills the existing rows as it is
   added;
2. the explicit ``UPDATE`` below sets ``'bw'`` on any row the add still left
   NULL — a backend whose ``ADD COLUMN`` does not backfill, and any row
   inserted between the two statements by a process still running older code;
3. and the reader itself, ``book_page_spec.ink_mode_from_stored``, reads NULL
   and the empty string as ``DEFAULT_INK_MODE``, so a row that escapes both of
   the above still prints black-and-white.

Only (3) is load-bearing for correctness; (1) and (2) are what make the stored
state say plainly what every book is, rather than leaving a NULL for a reader
to interpret.

**Rolling back.** Rolling the *code* back is safe: older code does not know
the column and ignores it, and a book then exports the way it always did — as
``DeviceRGB``. Rolling the *migration* back drops the column, so a book that
had been set to colour returns to black-and-white, which is the cheap
direction and loses no ink: the interior's content is black and white whatever
the file declares.

Revision ID: 013
Revises: 012
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None

#: What a book with no stored mode is printed as — ``InkMode.BLACK_AND_WHITE``'s
#: value, transcribed rather than imported so this migration keeps describing
#: the schema it wrote even if the enum is later renamed (the standing rule for
#: migrations: they are history, not live code).
DEFAULT_INK_MODE = 'bw'


def upgrade() -> None:
    # Batch mode for SQLite compatibility, like 004-012.
    with op.batch_alter_table('books') as batch_op:
        batch_op.add_column(
            sa.Column(
                'interior_ink_mode',
                sa.String(),
                nullable=True,
                server_default=DEFAULT_INK_MODE,
            )
        )
    # Point 2 above: every existing book is black-and-white, said explicitly
    # rather than left to the backend's ADD COLUMN semantics (AC-3).
    books = sa.table('books', sa.column('interior_ink_mode', sa.String()))
    op.execute(
        books.update()
        .where(books.c.interior_ink_mode.is_(None))
        .values(interior_ink_mode=DEFAULT_INK_MODE)
    )


def downgrade() -> None:
    """Drop the column; every other column and its data are untouched."""
    with op.batch_alter_table('books') as batch_op:
        batch_op.drop_column('interior_ink_mode')

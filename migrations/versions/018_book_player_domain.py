"""CARD-332 — store the base of the public player each book is read at.

Adds one nullable string column, ``books.player_domain``: the absolute
``https://`` origin of the public player a reader of this book would open,
e.g. ``https://nonogram.adverax.io``. The panel joins it to ADR-0041/R1's
per-puzzle key as ``{base}/play/{key}`` — ``docs/deploy/player.md``'s own
``play`` shape — and CARD-210 will print that URL as a QR code.

It follows 013 (``interior_ink_mode``) and 017 (``interior_divider_pages``) in
shape and in reasoning: a short per-book fact about how the book is
*published*, read in the same breath as the trim and the margins, never
queried across books, so it goes on the row rather than in a table of its own.

**Where it deliberately does NOT follow them: there is no default and no
backfill.** Both of those columns have a value every existing book already
*is* — every book was printed black-and-white, and every book was printed with
its four dividers — so a server default plus a backfill states that plainly.
Nothing of the kind is true here: no base was ever chosen for any book,
because the public player did not exist when they were made (its first deploy
was 2026-10-30, ``docs/deploy/player.md``). NULL therefore means exactly "no
domain set", ``print_specs.stored_player_domain`` reads it as ``None``, and
the arrangement screen says so plainly instead of rendering a URL built from a
guess (CARD-332 AC-3). A wrong domain is wrong in every printed copy and
cannot be corrected after the run, which is why this column would rather hold
nothing than hold something nobody chose.

**No geometry, no page count.** Unlike 017 this moves neither — ADR-0036/R1's
sheet, the interior's page count, its parity and the spine are all untouched.
It changes what a screen shows, and later what is drawn inside CARD-204's
already-reserved 2 x 2 cm QR slot.

**Rolling back.** Rolling the *code* back is safe: older code does not know
the column and shows no player links, which is what the panel did before this
card. Rolling the *migration* back drops the column, so every book's stored
base is lost and has to be set again — no ink and no printed book is affected,
because what was printed carries the base in its own pages.

Revision ID: 018
Revises: 017
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode for SQLite compatibility, like 004-017. Nullable, no server
    # default and no UPDATE: every existing row keeps NULL, which is the
    # truthful reading — see the note above.
    with op.batch_alter_table('books') as batch_op:
        batch_op.add_column(
            sa.Column('player_domain', sa.String(), nullable=True)
        )


def downgrade() -> None:
    """Drop the column; every other column and its data are untouched."""
    with op.batch_alter_table('books') as batch_op:
        batch_op.drop_column('player_domain')

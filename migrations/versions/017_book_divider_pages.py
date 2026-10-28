"""Store whether a book's interior prints its divider pages (CARD-305).

Adds one nullable boolean column, ``books.interior_divider_pages``. It decides
whether the interior carries its **four** divider pages — one per non-empty
named level ("Easy", "Medium", "Hard"; AC-254) and the "SOLUTIONS" page that
opens the answer key (AC-292) — or none of them. One column for all four,
because they are one editorial decision and one page design: the generator
draws all four with ``create_divider_page``.

It follows migration 013's ``interior_ink_mode`` in shape and in reasoning: a
short per-book fact about how the book is *printed*, read in the same breath
as the trim and the margins, never queried across books, so it goes on the row
rather than in a table of its own.

**Unlike 013, this column DOES change geometry — deliberately, and that is the
whole point.** Turning the dividers off removes up to four interior pages, so
every later page's number and therefore its parity (FR-043) shifts, the KDP
page count and spine width shrink, and the table of contents loses a row per
level divider. ADR-0036/R1's *sheet* is untouched — no page size, margin, cell
or rule depends on this — but the page **count** is not, and the generator's
own ``interior_page_count`` check is what holds the two in agreement.

**Existing rows get the default, and they get it here.** Every book that
exists today was generated with all four dividers, because they were
unconditional before this column. Three things make that true, following 013's
belt and braces for the same reason — a book silently losing four pages is a
reprint:

1. the column is added with a server default of true, which on PostgreSQL and
   on SQLite's ``ALTER TABLE ADD COLUMN`` fills the existing rows as it is
   added;
2. the explicit ``UPDATE`` below sets true on any row the add still left NULL;
3. and the reader itself,
   ``book_page_spec.divider_pages_from_stored``, reads NULL and the empty
   string as ``DEFAULT_DIVIDER_PAGES``, which is ``True``.

Only (3) is load-bearing for correctness; (1) and (2) are what make the stored
state say plainly what every book is.

**Rolling back.** Rolling the *code* back is safe: older code does not know
the column, and prints the dividers unconditionally — which is what every row
with the default says anyway. Rolling the *migration* back drops the column,
so a book that had been set to "no dividers" starts printing them again. That
is the direction that adds pages rather than losing them, and no ink is lost;
re-apply and re-set it if the book was meant to go without.

Revision ID: 017
Revises: 016
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None

#: What a book with no stored choice prints —
#: ``book_page_spec.DEFAULT_DIVIDER_PAGES``, transcribed rather than imported
#: so this migration keeps describing the schema it wrote even if the reader is
#: later renamed (the standing rule for migrations: they are history, not live
#: code).
DEFAULT_DIVIDER_PAGES = True


def upgrade() -> None:
    # Batch mode for SQLite compatibility, like 004-016.
    with op.batch_alter_table('books') as batch_op:
        batch_op.add_column(
            sa.Column(
                'interior_divider_pages',
                sa.Boolean(),
                nullable=True,
                server_default=sa.true(),
            )
        )
    # Point 2 above: every existing book prints its dividers, said explicitly
    # rather than left to the backend's ADD COLUMN semantics.
    books = sa.table('books', sa.column('interior_divider_pages', sa.Boolean()))
    op.execute(
        books.update()
        .where(books.c.interior_divider_pages.is_(None))
        .values(interior_divider_pages=DEFAULT_DIVIDER_PAGES)
    )


def downgrade() -> None:
    """Drop the column; every other column and its data are untouched."""
    with op.batch_alter_table('books') as batch_op:
        batch_op.drop_column('interior_divider_pages')

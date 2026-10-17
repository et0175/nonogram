"""Move the books table's outside-margin default to CON-018's amended 0.5 in (CARD-222).

Migration 011 gave ``books.outside_margin_cm`` the server default ``'0.95'``
(0.375 in), which was CON-018's outside margin then. The constraint was
amended on 2026-10-17: the outside margin is **0.5 in (1.27 cm)**, the top
0.55 in and the bottom 0.47 in, and the gutter deliberately stays at KDP's
required 0.5 in. Only the side margins have columns, and only the outside one
moved, so this migration changes exactly one default.

**No backfill, exactly as 011.** A row that already stores ``'0.95'`` keeps
it: that is a margin the book was laid out on, and rewriting it would silently
re-paginate a book somebody may already have finalised. What such a row now
reads as is stated in ``book_page_spec``'s own docstring — ``'0.95'`` is no
longer the profile's storage form, so it is read as the 9.5 mm it says rather
than as the profile's old 9.525 mm. A row whose margin is NULL (from before
011) still falls back to the profile and therefore moves to the amended one,
which is what CON-018's "an empty margin falls back to this profile" means.

**Top and bottom have no columns** and are read from the profile, so the two
margins this amendment also moved need no schema change at all.

Revision ID: 015
Revises: 014
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode for SQLite compatibility, like 004-014.
    with op.batch_alter_table('books') as batch_op:
        batch_op.alter_column(
            'outside_margin_cm', existing_type=sa.String(), existing_nullable=True,
            server_default='1.27',
        )


def downgrade() -> None:
    """Put 011's own default back; every value already stored is untouched."""
    with op.batch_alter_table('books') as batch_op:
        batch_op.alter_column(
            'outside_margin_cm', existing_type=sa.String(), existing_nullable=True,
            server_default='0.95',
        )

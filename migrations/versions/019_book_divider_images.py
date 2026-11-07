"""Store the owner's uploaded divider pages (CARD-311).

Creates ``book_divider_images``: one row per ``(book, slot)`` holding the PNG
the panel re-encoded from an uploaded divider picture. The four slots are
``easy``, ``medium``, ``hard`` and ``solutions`` (``book_dividers.DIVIDER_SLOTS``).

**Why a table and a blob.** The cover is kept as a file in the OS temp
directory with its path in the session, and can be purged out from under the
book. A divider is a page of the book, so it must survive a restart and a
redeploy; the host's disk does not, the database does. A table of its own
rather than columns on ``books``, because the number of slots is a property of
the design and not of the book row, and an image does not belong in the row
every list query reads.

``ON DELETE CASCADE``: a deleted book takes its images with it (the unique
constraint is on the pair, so a second upload to a slot replaces the first).

**No backfill.** No book has an uploaded divider, and this migration changes no
existing row and no printed page.

**Rolling back.** Dropping the table loses every uploaded divider; nothing else
is touched. Re-upload them.

Revision ID: 019
Revises: 018
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'book_divider_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slot', sa.String(length=16), nullable=False),
        sa.Column('image', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('book_id', 'slot', name='uq_book_divider_slot'),
    )
    op.create_index(
        'ix_book_divider_images_book_id', 'book_divider_images', ['book_id']
    )


def downgrade() -> None:
    """Drop the table; every other table and its data are untouched."""
    op.drop_index('ix_book_divider_images_book_id', table_name='book_divider_images')
    op.drop_table('book_divider_images')

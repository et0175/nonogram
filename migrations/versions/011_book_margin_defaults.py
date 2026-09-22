"""Give the books table's side margins CON-018's Book 1 defaults (CARD-115).

Adds server defaults ``gutter_margin_cm = '1.27'`` (0.5 in) and
``outside_margin_cm = '0.95'`` (0.375 in). Migration 004 left both columns
nullable with no default; 008 already gave the trim its Book 1 default.

**No backfill.** Rows that exist before this migration keep their empty
margins. The book's PageSpec builder falls back to the Book 1 profile for an
empty margin (FR-030, AC-178), and older code, which never reads the margins,
keeps working on those rows unchanged (Increment 13 Rollback). Only the
defaults change; the columns stay nullable.

Revision ID: 011
Revises: 010
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode for SQLite compatibility, like 004–010.
    with op.batch_alter_table('books') as batch_op:
        batch_op.alter_column(
            'gutter_margin_cm', existing_type=sa.String(), existing_nullable=True,
            server_default='1.27',
        )
        batch_op.alter_column(
            'outside_margin_cm', existing_type=sa.String(), existing_nullable=True,
            server_default='0.95',
        )


def downgrade() -> None:
    """Drop the two defaults; every value already stored is untouched."""
    with op.batch_alter_table('books') as batch_op:
        batch_op.alter_column(
            'gutter_margin_cm', existing_type=sa.String(), existing_nullable=True,
            server_default=None,
        )
        batch_op.alter_column(
            'outside_margin_cm', existing_type=sa.String(), existing_nullable=True,
            server_default=None,
        )

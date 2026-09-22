"""Store a book's distribution plan with the book (CARD-120, FR-034, ADR-0034).

Adds one nullable JSON column, ``books.distribution_plan``: the puzzle count,
the easy/medium/hard split, the 4 x 3 per-longest-side matrix and the set of
hand-edited cells, as one document (its shape is ``BookManager``'s to define).

**No backfill.** Books that exist before this migration stay plan-less (NULL).
They remain readable and editable; ADR-0035's gate refuses them with a remedy
(CARD-124) rather than this migration inventing a plan the owner never chose.
Rolling the code back is safe for the same reason: older code does not know
the column and simply ignores it.

Revision ID: 010
Revises: 009
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode for SQLite compatibility, like 004–009.
    with op.batch_alter_table('books') as batch_op:
        batch_op.add_column(sa.Column('distribution_plan', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Drop the column; every other column and its data are untouched."""
    with op.batch_alter_table('books') as batch_op:
        batch_op.drop_column('distribution_plan')

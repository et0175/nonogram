"""Store the tier a random batch asked for (CARD-181; IDEA-073).

Adds one nullable string column, ``batches.requested_tier``. CARD-138 let a
random batch ask for a tier (FR-008) and passed it to the generator as an
argument, but stored it nowhere, so a batch's pages could not say what it had
aimed at. The admin panel now writes the canonical tier value
(``difficulty.parse_tier(...).value``: ``'easy'``, ``'medium'`` or ``'hard'``)
when it creates a random batch, and ``NULL`` for an untargeted batch or an
image batch.

**Why a column.** The tier is one short value that belongs to exactly one
batch and is read with the batch's other fields (``source``, ``sizes``). It
sits on the row beside them, the same way 013 kept ``interior_ink_mode`` on
``books``.

**Why NULL for existing rows.** There is no server default and no backfill.
A batch made before this migration may or may not have asked for a tier
(targeted batches have existed since CARD-138), and nothing on disk says which.
So every existing row stays ``NULL``, which the pages read as "no tier
recorded" and show as an em dash, never as "Any".

**Rolling back.** ``downgrade`` drops the column and nothing else: the recorded
tiers are lost, and no puzzle row and no other batch column is touched. Roll
the code back first: code that knows the column selects it, and fails against
a database without it.

Revision ID: 014
Revises: 013
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode for SQLite compatibility, like 004-013.
    with op.batch_alter_table('batches') as batch_op:
        batch_op.add_column(
            sa.Column('requested_tier', sa.String(), nullable=True)
        )


def downgrade() -> None:
    """Drop the column; every other column and its data are untouched."""
    with op.batch_alter_table('batches') as batch_op:
        batch_op.drop_column('requested_tier')

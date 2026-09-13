"""Add the legacy grade columns CARD-077's re-grade batch preserves into.

Expand-only, and that is the whole point of the migration (CARD-077 G-2). The
re-grade batch overwrites ``difficulty_score``/``difficulty_tier`` on every row
it can grade, and the values it replaces are the only record of what was there;
these two nullable columns are where they go, so that running the batch is
reversible by hand even though the rewrite itself is not.

Nothing is dropped, nothing is narrowed, nothing becomes NOT NULL, and there is
no backfill here: a row's legacy values are written by the batch at the moment
it overwrites that row, not by this migration. NULL therefore means "this row
has not been re-graded", which is exactly the condition ``admin/regrade.py``
reads to make the capture happen at most once. A backfill here would destroy
that signal by pre-filling every row.

Existing rows stay valid and readable across the upgrade — two nullable columns
appear, and every other column, ``strategies_used`` included, is untouched.

The downgrade drops the two columns and nothing else, which is the only thing a
reversal of *this* migration can mean. Dropping them once the owner has
reviewed the new distribution is a separate, deliberate card.

Revision ID: 006
Revises: 005
Create Date: 2026-09-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode for SQLite compatibility, like 004/005. Adding a nullable
    # column needs no table rebuild on any supported backend, so this is a
    # plain ALTER ... ADD COLUMN in practice.
    with op.batch_alter_table('puzzles') as batch_op:
        batch_op.add_column(
            sa.Column('legacy_difficulty_score', sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('legacy_difficulty_tier', sa.String(), nullable=True)
        )


def downgrade() -> None:
    # Dropped in the reverse of the order they were added, so a partially
    # applied upgrade unwinds in the order it was built.
    with op.batch_alter_table('puzzles') as batch_op:
        batch_op.drop_column('legacy_difficulty_tier')
        batch_op.drop_column('legacy_difficulty_score')

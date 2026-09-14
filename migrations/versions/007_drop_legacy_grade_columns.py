"""Drop the legacy grade columns migration 006 added — the snapshots replaced them.

006 added ``legacy_difficulty_score``/``legacy_difficulty_tier`` so CARD-077's
re-grade batch had somewhere to move the value it was about to overwrite, and
said in as many words that dropping them again once the owner had reviewed the
new distribution would be a separate, deliberate card. This is that card
(CARD-084).

Why they go rather than stay
----------------------------
They never held anything. Measured across all three databases carrying this
schema on 2026-09-14: 0 of 396 rows had a non-NULL value in either column
(Render 0/86, nonogram_dev 0/294, nonogram_admin.db 0/16).

That is not bad luck, it is the mechanism. The capture is once-per-row-*ever*
by construction — ``_capture_legacy_grade``'s guard closes permanently after
the first write, which is what made it safe — so the columns record the state
before the *first* re-grade and are blind to every run after it. Production's
one shot was spent out of band on 2026-09-13, before this schema existed, so
for the rows these columns were added to protect the capture path never ran at
all.

What holds the pre-run grades now is a JSON snapshot taken immediately before
a run and committed to git (``meta/ops/*-grades-backup-*.json``). It is
versioned and lives outside the database it protects, it records rows the batch
*skips* as well as rows it rewrites, and — the part the columns structurally
could not do — it can be taken again before every subsequent run.

Scope
-----
Exactly two columns, on one table. ``difficulty_score``, ``difficulty_tier``,
``strategies_used`` and every other column are untouched, and existing rows
stay valid and readable across the upgrade.

This does not edit 006. That migration is applied everywhere and remains part
of the upgrade path from any older copy; this one supersedes it forward.

Reversal
--------
``downgrade`` re-adds the two columns, nullable, restoring the *shape* 006
produced. It does not restore the values — they are dropped by ``upgrade`` and
this migration has no record of them. Reversing to 006 therefore gives back two
empty columns, which is exactly what every database held before this ran, but
say it plainly rather than imply an undo: the data lives in the snapshot files,
and restoring it is a deliberate act against those, not an ``alembic downgrade``.

Revision ID: 007
Revises: 006
Create Date: 2026-09-14 10:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode for SQLite compatibility, like 004/005/006. Unlike adding a
    # nullable column, dropping one *does* rebuild the table on SQLite, which
    # is precisely what batch_alter_table exists to do.
    with op.batch_alter_table('puzzles') as batch_op:
        batch_op.drop_column('legacy_difficulty_tier')
        batch_op.drop_column('legacy_difficulty_score')


def downgrade() -> None:
    # Re-added in the reverse of the drop order, so the column order matches
    # what 006 left behind rather than merely the column set.
    with op.batch_alter_table('puzzles') as batch_op:
        batch_op.add_column(
            sa.Column('legacy_difficulty_score', sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('legacy_difficulty_tier', sa.String(), nullable=True)
        )

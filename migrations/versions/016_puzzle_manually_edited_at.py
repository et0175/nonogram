"""Record when a puzzle's grid was last replaced by hand (CARD-245).

Manual editing gives ``puzzles.grid`` its first write path since the
generation pipeline. An edit re-derives everything derived from the grid —
``clues_rows``, ``clues_cols``, ``difficulty_score``, ``difficulty_tier``,
``strategies_used`` — but it deliberately leaves ``quality_score`` and
``recognizability`` alone: those measure fidelity to the source picture, and
a hand edit is a *deliberate* departure from it, so re-measuring would punish
the owner for improving the puzzle.

That leaves the quality figure stale, and this column is what makes keeping it
honest: non-null means "hand-edited, and the quality number predates the
edit", with the timestamp saying how long ago.

**A timestamp, not a boolean.** Non-null already does everything a
``manually_edited`` flag would, for the same migration cost, and it answers
*how* stale the score is rather than only *that* it is. It matches the
``created_at`` pattern beside it.

**Nulling ``quality_score`` instead was ruled out on evidence** (owner
decision 2026-10-18). A null ``quality_score`` already means "unmeasured" on
this board — it is what random mode stores since CARD-050 — and
``puzzle_review.filter_puzzles`` *excludes* a null from any ``quality_min``
filter, because an unmeasured puzzle cannot satisfy a minimum and SQL's
``NULL >= n`` is false. Nulling after an edit would therefore make a
hand-improved puzzle vanish from every quality-filtered view, which is the
list the owner picks book puzzles from.

**Nullable, with no backfill.** Every row written before this migration reads
"never hand-edited", which is true of all of them: nothing but this card's
save path ever writes the column.

Revision ID: 016
Revises: 015
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode for SQLite compatibility, like 004-015.
    with op.batch_alter_table('puzzles') as batch_op:
        batch_op.add_column(sa.Column('manually_edited_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Drop the column. Nothing else moves: no other column was touched."""
    with op.batch_alter_table('puzzles') as batch_op:
        batch_op.drop_column('manually_edited_at')

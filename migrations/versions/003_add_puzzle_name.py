"""Add puzzle_name column for curation filtering

Revision ID: 003
Revises: 002
Create Date: 2026-09-09 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add puzzle_name column to puzzles table
    # nullable initially (populate from source_image or leave empty)
    op.add_column('puzzles', sa.Column('puzzle_name', sa.String(), nullable=True))

    # Create index for filtering/sorting by puzzle_name
    op.create_index('ix_puzzles_puzzle_name', 'puzzles', ['puzzle_name'])


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_puzzles_puzzle_name', table_name='puzzles')

    # Drop column
    op.drop_column('puzzles', 'puzzle_name')

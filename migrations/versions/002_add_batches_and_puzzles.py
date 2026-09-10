"""Add batches and puzzles tables, migrate from nonograms

Revision ID: 002
Revises: 001
Create Date: 2026-09-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create batches table
    op.create_table(
        'batches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('source', sa.String(), nullable=False, server_default='random'),
        sa.Column('total_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('puzzle_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sizes', sa.JSON(), nullable=True),
        sa.Column('theme', sa.String(), nullable=True),
        sa.Column('quality_filter', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Rename nonograms table to puzzles
    # Note: Postgres FKs bind by OID, so existing FK constraints are preserved
    op.rename_table('nonograms', 'puzzles')

    # SQLite doesn't support all alterations; use batch mode for compatibility
    with op.batch_alter_table('puzzles') as batch_op:
        # Drop columns not used in the admin puzzle shape
        batch_op.drop_column('name')
        batch_op.drop_column('solution_grid')
        batch_op.drop_column('clues_rows')
        batch_op.drop_column('clues_cols')
        batch_op.drop_column('strategies_used')

        # Rename image_source_url to source_image for consistency
        batch_op.alter_column('image_source_url', new_column_name='source_image')

        # Add new columns
        batch_op.add_column(sa.Column('batch_id', postgresql.UUID(as_uuid=True), nullable=True))
        batch_op.add_column(sa.Column('grid', sa.JSON(), nullable=False, server_default='[]'))
        batch_op.add_column(sa.Column('clues_rows', sa.JSON(), nullable=False, server_default='[]'))
        batch_op.add_column(sa.Column('clues_cols', sa.JSON(), nullable=False, server_default='[]'))
        batch_op.add_column(sa.Column('strategies_used', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('recognizability', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=True))

        # Create FK constraint from puzzles.batch_id to batches.id
        batch_op.create_foreign_key('fk_puzzles_batch_id_batches', 'batches',
                              ['batch_id'], ['id'])

        # Create indexes
        batch_op.create_index('ix_puzzles_batch_id', ['batch_id'])
        batch_op.create_index('ix_puzzles_status', ['status'])


def downgrade() -> None:
    # Reverse the upgrade migration in correct order
    with op.batch_alter_table('puzzles') as batch_op:
        # Drop indexes first
        batch_op.drop_index('ix_puzzles_status')
        batch_op.drop_index('ix_puzzles_batch_id')

        # Drop FK constraint to batches table
        batch_op.drop_constraint('fk_puzzles_batch_id_batches', type_='foreignkey')

        # Drop new columns added in upgrade, in reverse order
        batch_op.drop_column('book_id')
        batch_op.drop_column('recognizability')
        batch_op.drop_column('strategies_used')
        batch_op.drop_column('clues_cols')
        batch_op.drop_column('clues_rows')
        batch_op.drop_column('grid')
        batch_op.drop_column('batch_id')

        # Rename column back to original name
        batch_op.alter_column('source_image', new_column_name='image_source_url')

        # Restore columns that were dropped in upgrade, matching migration 001's original types
        batch_op.add_column(sa.Column('clues_cols', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('clues_rows', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('solution_grid', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('strategies_used', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('name', sa.String(), nullable=True))

    # Rename table back to original name (must be outside batch_alter_table)
    op.rename_table('puzzles', 'nonograms')

    # Drop batches table
    op.drop_table('batches')

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

    # Drop columns not used in the admin puzzle shape
    op.drop_column('puzzles', 'name')
    op.drop_column('puzzles', 'solution_grid')
    op.drop_column('puzzles', 'clues_rows')
    op.drop_column('puzzles', 'clues_cols')
    op.drop_column('puzzles', 'strategies_used')

    # Rename image_source_url to source_image for consistency
    op.alter_column('puzzles', 'image_source_url', new_column_name='source_image')

    # Add new columns
    op.add_column('puzzles', sa.Column('batch_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('puzzles', sa.Column('grid', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('puzzles', sa.Column('clues_rows', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('puzzles', sa.Column('clues_cols', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('puzzles', sa.Column('strategies_used', sa.JSON(), nullable=True))
    op.add_column('puzzles', sa.Column('recognizability', sa.String(), nullable=True))
    op.add_column('puzzles', sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Create FK constraint from puzzles.batch_id to batches.id
    op.create_foreign_key('fk_puzzles_batch_id_batches', 'puzzles', 'batches',
                          ['batch_id'], ['id'])

    # Create indexes
    op.create_index('ix_puzzles_batch_id', 'puzzles', ['batch_id'])
    op.create_index('ix_puzzles_status', 'puzzles', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_puzzles_status', table_name='puzzles')
    op.drop_index('ix_puzzles_batch_id', table_name='puzzles')

    # Drop FK constraint
    op.drop_constraint('fk_puzzles_batch_id_batches', 'puzzles', type_='foreignkey')

    # Drop new columns
    op.drop_column('puzzles', 'book_id')
    op.drop_column('puzzles', 'recognizability')
    op.drop_column('puzzles', 'strategies_used')
    op.drop_column('puzzles', 'clues_cols')
    op.drop_column('puzzles', 'clues_rows')
    op.drop_column('puzzles', 'grid')
    op.drop_column('puzzles', 'batch_id')

    # Rename source_image back to image_source_url
    op.alter_column('puzzles', 'source_image', new_column_name='image_source_url')

    # Restore dropped columns as Text (pre-JSON format)
    op.add_column('puzzles', sa.Column('strategies_used', sa.Text(), nullable=True))
    op.add_column('puzzles', sa.Column('clues_cols', sa.Text(), nullable=True))
    op.add_column('puzzles', sa.Column('clues_rows', sa.Text(), nullable=True))
    op.add_column('puzzles', sa.Column('solution_grid', sa.Text(), nullable=True))
    op.add_column('puzzles', sa.Column('name', sa.String(), nullable=True))

    # Rename puzzles back to nonograms
    op.rename_table('puzzles', 'nonograms')

    # Drop batches table
    op.drop_table('batches')

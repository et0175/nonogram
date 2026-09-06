"""Create initial schema

Revision ID: 001
Revises:
Create Date: 2026-09-06 19:12:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('subscription_tier', sa.String(), nullable=True, server_default='free'),
        sa.Column('puzzles_generated_month', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Create nonograms table
    op.create_table(
        'nonograms',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('theme', sa.String(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('difficulty_score', sa.Integer(), nullable=True),
        sa.Column('difficulty_tier', sa.String(), nullable=True),
        sa.Column('quality_score', sa.Integer(), nullable=True),
        sa.Column('strategies_used', sa.Text(), nullable=True),
        sa.Column('solution_grid', sa.Text(), nullable=True),
        sa.Column('clues_rows', sa.Text(), nullable=True),
        sa.Column('clues_cols', sa.Text(), nullable=True),
        sa.Column('image_source_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, server_default='draft'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create books table
    op.create_table(
        'books',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('theme', sa.String(), nullable=True),
        sa.Column('target_audience', sa.String(), nullable=True),
        sa.Column('nonogram_ids', sa.Text(), nullable=True),
        sa.Column('cover_image_url', sa.String(), nullable=True),
        sa.Column('pdf_url', sa.String(), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, server_default='draft'),
        sa.Column('kdp_asin', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create generation_history table
    op.create_table(
        'generation_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('puzzle_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['puzzle_id'], ['nonograms.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create user_selected_books table
    op.create_table(
        'user_selected_books',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('puzzle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('selected_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ),
        sa.ForeignKeyConstraint(['puzzle_id'], ['nonograms.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'puzzle_id', 'book_id')
    )


def downgrade() -> None:
    op.drop_table('user_selected_books')
    op.drop_table('generation_history')
    op.drop_table('books')
    op.drop_table('nonograms')
    op.drop_table('users')

"""Add print specifications to books table

Revision ID: 004
Revises: 003
Create Date: 2026-09-09 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add print specification columns to books table
    op.add_column('books', sa.Column('trim_width_cm', sa.String(), nullable=True, server_default='15.24'))
    op.add_column('books', sa.Column('trim_height_cm', sa.String(), nullable=True, server_default='22.86'))
    op.add_column('books', sa.Column('gutter_margin_cm', sa.String(), nullable=True))
    op.add_column('books', sa.Column('outside_margin_cm', sa.String(), nullable=True))
    op.add_column('books', sa.Column('outside_margin_bleed_cm', sa.String(), nullable=True))


def downgrade() -> None:
    # Drop print specification columns
    op.drop_column('books', 'outside_margin_bleed_cm')
    op.drop_column('books', 'outside_margin_cm')
    op.drop_column('books', 'gutter_margin_cm')
    op.drop_column('books', 'trim_height_cm')
    op.drop_column('books', 'trim_width_cm')

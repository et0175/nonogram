"""Change the books table's default trim size from 6 × 9 in to 8.5 × 11 in.

004 gave ``trim_width_cm``/``trim_height_cm`` server defaults of 15.24/22.86 cm
(6 × 9 in, mislabelled "A5" in the book-scaffolding requirements). The default
book is now US Letter, 21.59 × 27.94 cm: it is the dominant trim among
top-selling nonogram books on Amazon (2026-09-15 snapshot), and 6 × 9 cannot
print 25×25–30×30 grids at a usable cell size.

Scope
-----
Only the server defaults change. Existing rows keep whatever trim size they
already store — a book set up at 6 × 9 stays 6 × 9.

Revision ID: 008
Revises: 007
Create Date: 2026-09-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode for SQLite compatibility, like 004–007.
    with op.batch_alter_table('books') as batch_op:
        batch_op.alter_column(
            'trim_width_cm', existing_type=sa.String(), existing_nullable=True,
            server_default='21.59',
        )
        batch_op.alter_column(
            'trim_height_cm', existing_type=sa.String(), existing_nullable=True,
            server_default='27.94',
        )


def downgrade() -> None:
    with op.batch_alter_table('books') as batch_op:
        batch_op.alter_column(
            'trim_width_cm', existing_type=sa.String(), existing_nullable=True,
            server_default='15.24',
        )
        batch_op.alter_column(
            'trim_height_cm', existing_type=sa.String(), existing_nullable=True,
            server_default='22.86',
        )

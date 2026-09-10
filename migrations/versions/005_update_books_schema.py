"""Update books schema for BookManager database integration

Revision ID: 005
Revises: 004
Create Date: 2026-09-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite doesn't support all alterations; use batch mode for compatibility
    with op.batch_alter_table('books') as batch_op:
        # Rename nonogram_ids to puzzle_ids and change to JSON
        # First, get existing data before altering
        batch_op.add_column(sa.Column('puzzle_ids', sa.JSON(), nullable=False, server_default='[]'))

        # Add puzzle_titles column for custom puzzle titles in the book
        batch_op.add_column(sa.Column('puzzle_titles', sa.JSON(), nullable=False, server_default='{}'))

        # Add book_metadata column for storing: size, cover_image_url, pdf_url, kdp_asin
        batch_op.add_column(sa.Column('book_metadata', sa.JSON(), nullable=False, server_default='{}'))

        # Add updated_at column for tracking changes
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.func.now()))

    # Data migration: copy and transform existing data
    # This needs to be done after the columns are added
    from datetime import datetime

    connection = op.get_bind()

    # Get all rows from books table
    result = connection.execute(sa.text("SELECT id, nonogram_ids, cover_image_url, pdf_url, page_count, kdp_asin FROM books"))
    rows = result.fetchall()

    for row in rows:
        book_id, nonogram_ids_str, cover_image_url, pdf_url, page_count, kdp_asin = row

        # Parse existing nonogram_ids (was stored as JSON string or empty)
        puzzle_ids = []
        if nonogram_ids_str:
            try:
                if isinstance(nonogram_ids_str, str):
                    puzzle_ids = json.loads(nonogram_ids_str) if nonogram_ids_str.startswith('[') else []
                else:
                    puzzle_ids = nonogram_ids_str if isinstance(nonogram_ids_str, list) else []
            except (json.JSONDecodeError, TypeError):
                puzzle_ids = []

        # Build metadata object
        metadata = {
            'size': '8x10',  # default size
            'cover_image_url': cover_image_url,
            'pdf_url': pdf_url,
            'kdp_asin': kdp_asin,
        }

        # Update the row with new columns
        connection.execute(
            sa.text(
                """UPDATE books SET puzzle_ids = :puzzle_ids, book_metadata = :book_metadata, updated_at = :updated_at
                   WHERE id = :book_id"""
            ),
            {
                'puzzle_ids': json.dumps(puzzle_ids),
                'book_metadata': json.dumps(metadata),
                'updated_at': datetime.utcnow(),
                'book_id': str(book_id),
            }
        )

    # After data migration, drop the old column
    with op.batch_alter_table('books') as batch_op:
        batch_op.drop_column('nonogram_ids')


def downgrade() -> None:
    # SQLite doesn't support all alterations; use batch mode for compatibility
    with op.batch_alter_table('books') as batch_op:
        # Re-add nonogram_ids column
        batch_op.add_column(sa.Column('nonogram_ids', sa.Text(), nullable=True))

        # Migrate data back
        # Note: This is a simplified reverse; we lose the structure of metadata fields

        # Drop new columns
        batch_op.drop_column('updated_at')
        batch_op.drop_column('book_metadata')
        batch_op.drop_column('puzzle_titles')
        batch_op.drop_column('puzzle_ids')

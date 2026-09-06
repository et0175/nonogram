# Database Migrations Strategy

**Status:** PLANNING  
**Part of:** CARD-001 (Database Layer Setup)  
**Tool:** Alembic (SQLAlchemy migration framework)  
**Environment:** Local dev + Railway PostgreSQL

---

## Overview

We'll use **Alembic** to manage database schema changes. This allows:
- ✅ Version control for schema (track changes in git)
- ✅ Reproducible deployments (migrations run in order)
- ✅ Easy rollback (if something breaks)
- ✅ Team collaboration (no manual "run this SQL" instructions)

---

## Setup (Part of CARD-001)

### 1. Install Alembic

```bash
pip install alembic sqlalchemy
```

### 2. Initialize Alembic in Project

```bash
cd /Users/omelnikova/PythonProject4
alembic init migrations
```

This creates:
```
migrations/
├── alembic.ini          # Alembic config (connection string)
├── env.py               # Migration environment setup
├── script.py.mako       # Migration template
└── versions/            # Individual migration files
    ├── 001_initial_schema.py
    ├── 002_add_users_table.py
    └── ...
```

### 3. Configure Connection String

**File:** `migrations/alembic.ini`

Update sqlalchemy connection string:
```ini
sqlalchemy.url = postgresql://user:password@localhost:5432/nonogram_poc
```

For Railway (production):
```ini
sqlalchemy.url = ${DATABASE_URL}  # Use environment variable
```

### 4. Update env.py

**File:** `migrations/env.py`

Connect Alembic to our ORM models:
```python
from src.nonogram.db.models import Base

target_metadata = Base.metadata
```

---

## Migration Workflow

### Creating a Migration

When you add a new table or change schema:

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add users table"

# This creates: migrations/versions/001_add_users_table.py
```

**Example migration file:**
```python
"""Add users table"""

from alembic import op
import sqlalchemy as sa

revision = '001_add_users_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('subscription_tier', sa.String(), nullable=True),
        sa.Column('puzzles_generated_month', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

def downgrade():
    op.drop_table('users')
```

### Running Migrations

**Local Development:**
```bash
# Upgrade to latest version
alembic upgrade head

# Upgrade to specific version
alembic upgrade 001_add_users_table

# Rollback one version
alembic downgrade -1

# Rollback all migrations
alembic downgrade base
```

**Production (Railway):**
```bash
# In Dockerfile or deployment script:
RUN alembic upgrade head
```

### Checking Migration Status

```bash
alembic current      # Show current version
alembic history      # Show all migrations
alembic branches     # Show branches (if any)
```

---

## Initial Schema (CARD-001)

### Step 1: Define ORM Models

**File:** `src/nonogram/db/models.py`

```python
from sqlalchemy import Column, String, Integer, DateTime, UUID, ForeignKey, Table, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    subscription_tier = Column(String, default='free')
    puzzles_generated_month = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Nonogram(Base):
    __tablename__ = 'nonograms'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=True)
    theme = Column(String, nullable=True)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    difficulty_score = Column(Integer, nullable=True)
    difficulty_tier = Column(String, nullable=True)
    quality_score = Column(Integer, nullable=True)
    strategies_used = Column(Text, nullable=True)  # JSON array as string
    solution_grid = Column(Text, nullable=True)    # JSON array as string
    clues_rows = Column(Text, nullable=True)       # JSON array as string
    clues_cols = Column(Text, nullable=True)       # JSON array as string
    image_source_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default='draft')       # draft, approved, in_book

class Book(Base):
    __tablename__ = 'books'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    theme = Column(String, nullable=True)
    target_audience = Column(String, nullable=True)
    nonogram_ids = Column(Text, nullable=True)    # JSON array as string
    cover_image_url = Column(String, nullable=True)
    pdf_url = Column(String, nullable=True)
    page_count = Column(Integer, nullable=True)
    status = Column(String, default='draft')       # draft, ready, published
    kdp_asin = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class GenerationHistory(Base):
    __tablename__ = 'generation_history'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    puzzle_id = Column(UUID(as_uuid=True), ForeignKey('nonograms.id'), nullable=True)
    image_url = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class UserSelectedBook(Base):
    __tablename__ = 'user_selected_books'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    puzzle_id = Column(UUID(as_uuid=True), ForeignKey('nonograms.id'), primary_key=True)
    book_id = Column(UUID(as_uuid=True), ForeignKey('books.id'), primary_key=True)
    selected_at = Column(DateTime, default=datetime.utcnow)
```

### Step 2: Generate Initial Migration

```bash
alembic revision --autogenerate -m "Create initial schema"
```

This auto-detects tables from models and creates migration file.

### Step 3: Review & Run

```bash
# Review the generated migration
cat migrations/versions/001_create_initial_schema.py

# Test migration locally
alembic upgrade head

# Verify tables exist
psql -d nonogram_poc -c "\dt"
```

### Step 4: Deploy to Railway

```bash
# In Dockerfile after installing dependencies:
RUN alembic upgrade head
```

---

## Making Schema Changes Later

**Scenario:** You need to add a new column to `nonograms` table.

**Steps:**

1. **Update ORM model** (`src/nonogram/db/models.py`):
   ```python
   class Nonogram(Base):
       # ... existing columns ...
       custom_field = Column(String, nullable=True)  # NEW
   ```

2. **Generate migration**:
   ```bash
   alembic revision --autogenerate -m "Add custom_field to nonograms"
   ```

3. **Review generated file**:
   ```bash
   cat migrations/versions/002_add_custom_field_to_nonograms.py
   ```

4. **Test locally**:
   ```bash
   alembic upgrade head
   # Query to verify
   psql -d nonogram_poc -c "SELECT * FROM nonograms LIMIT 1;"
   ```

5. **Commit to git**:
   ```bash
   git add migrations/versions/002_*.py
   git commit -m "migration: add custom_field to nonograms"
   ```

6. **Deploy**:
   ```bash
   git push origin main
   # Alembic runs in Dockerfile automatically
   ```

---

## Documentation Strategy

### Schema Documentation

**File:** `docs/DATABASE_SCHEMA.md`

Auto-generate from models:

```python
# script to generate docs
from src.nonogram.db.models import Base, User, Nonogram, Book

for table in Base.metadata.sorted_tables:
    print(f"## {table.name}")
    for col in table.columns:
        print(f"- {col.name}: {col.type} (nullable={col.nullable})")
```

Run this after each migration to keep docs up-to-date:
```bash
python scripts/generate_schema_docs.py > docs/DATABASE_SCHEMA.md
```

### Migration Log

**File:** `docs/MIGRATIONS.md`

Track all migrations:

```markdown
# Database Migrations

## 001 - Create Initial Schema (2026-09-07)
- Created users, nonograms, books, generation_history, user_selected_books tables
- Default statuses: draft, free tier
- UUIDs for primary keys

## 002 - Add custom_field to nonograms (2026-09-15)
- Added custom_field (String, nullable)
- For: [reason]

## 003 - Add index on nonograms.difficulty_score (2026-09-20)
- Added index for faster filtering
- Performance impact: queries 2x faster
```

---

## Local Development Setup

### First Time Setup

```bash
# Create local PostgreSQL database
docker run -d \
  --name postgres-nonogram \
  -e POSTGRES_DB=nonogram_poc \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:15

# Set connection string
export DATABASE_URL="postgresql://postgres:password@localhost:5432/nonogram_poc"

# Run migrations
alembic upgrade head

# Verify
psql $DATABASE_URL -c "\dt"
```

### Daily Development

```bash
# Make ORM changes
vim src/nonogram/db/models.py

# Generate migration
alembic revision --autogenerate -m "your message"

# Test
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

---

## Production Checklist (Railway)

- [ ] Connection string in Railway environment variables
- [ ] Alembic config reads `DATABASE_URL` env var
- [ ] Dockerfile includes `alembic upgrade head` before app starts
- [ ] Migration files committed to git
- [ ] `migrations/versions/` is tracked in version control
- [ ] Test migration on staging before prod deployment

---

## Backup Strategy

**Before each major migration:**

```bash
# Backup current database
pg_dump $DATABASE_URL > backup_2026-09-15.sql

# After migration, if rollback needed:
psql $DATABASE_URL < backup_2026-09-15.sql
```

For Railway, use Railway's built-in backup feature.

---

## Troubleshooting

### Migration Won't Apply

```bash
# Check migration status
alembic current
alembic history

# Check for syntax errors
alembic upgrade dry-run
```

### Need to Rollback

```bash
# Rollback one version
alembic downgrade -1

# Rollback to specific version
alembic downgrade 001_create_initial_schema
```

### Lost Local Database

```bash
# Recreate from scratch
docker rm postgres-nonogram
docker run -d --name postgres-nonogram -p 5432:5432 postgres:15
alembic upgrade head
```

---

## Files Created by CARD-001

After completing this card, you should have:

```
src/nonogram/db/
├── __init__.py              # Connection factory
├── models.py                # ORM models (User, Nonogram, Book, etc)
└── session.py               # SQLAlchemy session management

migrations/
├── alembic.ini              # Config
├── env.py                   # Alembic environment
├── script.py.mako           # Template
└── versions/
    └── 001_create_initial_schema.py

docs/
├── DATABASE_SCHEMA.md       # Auto-generated schema docs
└── MIGRATIONS.md            # Migration log

.env.example
├── DATABASE_URL=postgresql://localhost:5432/nonogram_poc
```

---

**Next Step:** Follow this guide during CARD-001 implementation.


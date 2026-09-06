# Nonogram Publishing Platform (POC)

Generate, curate, and publish nonogram puzzles on Amazon KDP. Features strategy-based difficulty analysis, image-to-puzzle conversion, and book curation for seniors-friendly puzzle collections.

**POC Deadline:** 15 November 2026  
**Status:** 🔄 Phase 1 (Database Setup)

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Node.js 20+
- Docker Desktop (recommended for PostgreSQL)

### Setup (5 minutes)

**1. Install dependencies:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e '.[dev]'
pip install alembic sqlalchemy psycopg2-binary
```

**2. Start PostgreSQL (choose one):**

**Option A: Docker (Recommended)**
```bash
docker-compose up -d postgres
```

**Option B: Homebrew (macOS)**
```bash
brew install postgresql@15
brew services start postgresql@15
createdb nonogram_poc
```

**Option C: System Package Manager (Linux)**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
createdb nonogram_poc
```

**3. Set environment variables:**
```bash
cp .env.example .env
# Edit .env with your database URL if needed
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"
```

**4. Run database migrations:**
```bash
alembic upgrade head
```

**5. Verify setup:**
```bash
# Check PostgreSQL is running
psql $DATABASE_URL -c "\dt"

# You should see 5 tables: users, nonograms, books, generation_history, user_selected_books
```

---

## PostgreSQL Setup Details

### Option A: Docker Compose (Easiest)

**Start:**
```bash
docker-compose up -d postgres
```

**Verify:**
```bash
docker ps  # Should show nonogram-postgres running
```

**Stop:**
```bash
docker-compose down
```

**Access psql:**
```bash
psql postgresql://postgres:postgres@localhost:5432/nonogram_poc
```

**Credentials:**
- User: `postgres`
- Password: `postgres`
- Database: `nonogram_poc`
- Port: `5432`

---

### Option B: Homebrew (macOS)

**Install:**
```bash
brew install postgresql@15
```

**Start:**
```bash
brew services start postgresql@15
```

**Create database:**
```bash
createdb nonogram_poc
```

**Verify:**
```bash
psql nonogram_poc -c "\dt"
```

**Connect:**
```bash
psql nonogram_poc
```

**Stop:**
```bash
brew services stop postgresql@15
```

---

### Option C: System Package (Linux)

**Install:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
```

**Start:**
```bash
sudo systemctl start postgresql
```

**Create user & database:**
```bash
sudo -u postgres createuser nonogram_user
sudo -u postgres createdb -O nonogram_user nonogram_poc
```

**Connect:**
```bash
psql -U nonogram_user -d nonogram_poc
```

---

## Database Migrations

Migrations are managed with **Alembic**. All changes are version-controlled in `migrations/versions/`.

### Running Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific version
alembic upgrade 001_create_initial_schema

# Check current version
alembic current

# View history
alembic history

# Rollback one version
alembic downgrade -1
```

### Creating New Migrations

When you modify ORM models in `src/nonogram/db/models.py`:

```bash
# PostgreSQL must be running for this
alembic revision --autogenerate -m "your migration description"
```

This creates a new file in `migrations/versions/` that you commit to git.

### Database Schema

See [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) for full schema documentation.

Current tables:
- **users** — User accounts (email, subscription tier, usage tracking)
- **nonograms** — Generated puzzles (clues, difficulty, quality scores)
- **books** — Curated puzzle collections for Amazon KDP
- **generation_history** — Analytics log
- **user_selected_books** — Many-to-many: users select puzzles for books

---

## Development Workflow

### 1. Start PostgreSQL

```bash
docker-compose up -d postgres
# or: brew services start postgresql@15
```

### 2. Activate venv

```bash
source .venv/bin/activate
```

### 3. Run tests

```bash
pytest                    # All tests
pytest tests/test_db.py  # Database tests only
pytest -v                # Verbose
```

### 4. Make code changes

Edit Python files in `src/nonogram/` and `nonogram-web/`

### 5. Create migrations (if schema changes)

```bash
alembic revision --autogenerate -m "describe changes"
alembic upgrade head  # Test locally
```

### 6. Commit

```bash
git add .
git commit -m "your message"
```

---

## Production Deployment (Railway)

### PostgreSQL Setup on Railway

1. Create Railway PostgreSQL database (built-in service)
2. Copy `DATABASE_URL` from Railway dashboard
3. Add to Railway environment variables:
   ```
   DATABASE_URL=postgresql://user:password@host:5432/nonogram_poc
   ADMIN_PASSWORD=your_password
   ```

4. Dockerfile automatically runs migrations:
   ```dockerfile
   RUN alembic upgrade head
   ```

See [docs/DEPLOYMENT_WORKFLOW.md](docs/DEPLOYMENT_WORKFLOW.md) for full deployment guide.

---

## Troubleshooting

### PostgreSQL Connection Failed

**Error:** `connection refused` or `could not translate host name`

**Fix:**
```bash
# Verify PostgreSQL is running
docker ps  # or: brew services list

# Check DATABASE_URL
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

### Migration Won't Apply

**Error:** `Target database is not up to date`

**Fix:**
```bash
# Check current version
alembic current

# Check history
alembic history

# Rollback and retry
alembic downgrade base
alembic upgrade head
```

### Lost Local Database

**Fix:**
```bash
# Option A: Docker
docker-compose down -v          # Remove volume
docker-compose up -d postgres   # Restart fresh
alembic upgrade head            # Reapply migrations

# Option B: Homebrew
dropdb nonogram_poc
createdb nonogram_poc
alembic upgrade head
```

### psql Command Not Found

**Fix:**
```bash
# Homebrew
brew install postgresql@15
export PATH="/usr/local/opt/postgresql@15/bin:$PATH"

# Or add to ~/.zshrc or ~/.bash_profile permanently
```

---

## Project Structure

```
.
├── README.md                 # This file
├── docker-compose.yml        # PostgreSQL container
├── alembic.ini              # Migration config
├── migrations/              # Database migrations
│   ├── env.py
│   ├── versions/
│   │   └── 001_create_initial_schema.py
├── src/
│   └── nonogram/
│       ├── db/              # Database layer
│       │   ├── models.py    # ORM models
│       │   ├── __init__.py  # Connection factory
│       │   └── session.py   # Session management
│       ├── analysis/        # Difficulty & quality calculators
│       ├── export/          # PDF/PNG/SVG exporters
│       ├── solver/          # Constraint solver
│       ├── sourcing/        # Puzzle generation
│       └── ...
├── nonogram-web/            # Next.js frontend + admin panel
│   ├── app/
│   ├── api/
│   └── ...
├── docs/                    # Documentation
│   ├── DATABASE_SCHEMA.md
│   ├── MIGRATIONS.md
│   └── ...
└── tests/                   # Test suite
```

---

## Command Reference

```bash
# PostgreSQL
docker-compose up -d postgres        # Start (Docker)
docker-compose down                  # Stop (Docker)
brew services start postgresql@15    # Start (Homebrew)
psql $DATABASE_URL -c "\dt"          # List tables

# Migrations
alembic upgrade head                 # Apply all
alembic downgrade -1                 # Rollback one
alembic revision --autogenerate -m   # Create new

# Tests
pytest                               # Run all
pytest -k difficulty                 # Run by pattern
pytest -v --tb=short                 # Verbose + short traceback

# Development
source .venv/bin/activate            # Activate venv
python -m pytest                     # Run tests
python -m nonogram generate --help   # CLI help
```

---

## Documentation

- [DATABASE_SETUP.md](docs/DATABASE_SETUP.md) — Detailed database configuration
- [DEPLOYMENT_WORKFLOW.md](docs/DEPLOYMENT_WORKFLOW.md) — Railway deployment guide
- [DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) — Full schema reference
- [MIGRATIONS.md](docs/MIGRATIONS.md) — Migration history & best practices
- [PROJECT_PLAN_POC.md](PROJECT_PLAN_POC.md) — Business plan & requirements
- [IMPLEMENTATION_BREAKDOWN.md](IMPLEMENTATION_BREAKDOWN.md) — Task breakdown & timeline

---

## Contributing

See [CLAUDE.md](CLAUDE.md) for development guidelines.

---

## License

Proprietary (Ольга & Анна partnership)

---

**Last Updated:** 2026-09-06  
**Status:** POC Phase 1 (Database Setup)

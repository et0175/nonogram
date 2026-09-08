# Nonogram Admin Panel Setup & Usage

Complete guide for setting up and using the Nonogram Admin Panel in both local development and production (Render) environments.

## Overview

The Nonogram Admin Panel is a Flask-based web application for:
- **Batch Generation**: Create batches of randomized nonogram puzzles with configurable parameters
- **Puzzle Review & Curation**: Filter, review, and approve puzzles for inclusion in books
- **Book Management**: Organize approved puzzles into books and generate PDFs
- **Quality Control**: Track puzzle metrics (difficulty, quality score, recognizability)

## Architecture

```
Admin Panel (Flask)
  ├── Batch Generator Service (puzzle generation)
  ├── Puzzle Review Service (database persistence)
  ├── Book Manager (book organization & PDF generation)
  └── Database (PostgreSQL)
      ├── Puzzles table
      ├── Batches table
      └── Books table
```

## Local Setup

### Prerequisites

- Python 3.14+
- PostgreSQL 15+ running locally
- Git

### Installation

1. **Clone and navigate to project:**
   ```bash
   cd /Users/omelnikova/PythonProject4
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e '.[dev]'
   ```

4. **Set up local PostgreSQL database:**
   ```bash
   createdb nonogram_poc
   export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"
   ```

5. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the Flask app:**
   ```bash
   export FLASK_ENV=development
   python -m flask --app src.nonogram.admin.app run
   ```

   The admin panel will be available at **http://localhost:5000**

### Local Usage

#### Create a Batch

1. Go to **Batch Generation** → **Create Batch**
2. Choose a preset or configure manually:
   - **Small Batch (Fast)**: 50 puzzles, sizes 10-15
   - **Medium Batch (Standard)**: 100 puzzles, sizes 15-25
   - **Large Batch (Complete)**: 200 puzzles, sizes 10-30
3. Click **Start Batch Generation**
4. Monitor progress on the Batch Status page
5. Once complete (100%), go to **Puzzle Review & Curation**

#### Review & Approve Puzzles

1. Go to **Puzzle Review & Curation** (or **View & Filter**)
2. Use filters to narrow results:
   - **Size**: Grid dimensions (10-30 px)
   - **Difficulty**: Easy / Medium / Hard
   - **Min Quality**: Quality score threshold (0-100)
3. Click checkmark (✓) to approve, X to reject
4. Approved puzzles move to "Approved" status for book inclusion

#### Create a Book

1. Go to **Books** → **Create Book**
2. Configure book parameters:
   - Book title
   - Number of puzzles to include
   - Difficulty distribution (Easy/Medium/Hard %)
   - Metadata (author, version, etc.)
3. Select "Generate PDF"
4. PDF downloads automatically

### Local Testing

Run the E2E test suite to verify batch generation and storage:

```bash
pytest tests/test_batch_generation_e2e.py -v
```

Expected output:
```
tests/test_batch_generation_e2e.py::TestBatchGenerationE2E::test_batch_generation_and_storage PASSED
tests/test_batch_generation_e2e.py::TestBatchGenerationE2E::test_puzzle_metrics_are_valid PASSED
```

## Render Production Setup

### Prerequisites

- Render.com account
- GitHub repo connected to Render
- PostgreSQL database on Render

### Initial Setup (One-Time)

1. **Create PostgreSQL Database on Render:**
   - Go to https://dashboard.render.com
   - Click **+ New** → **PostgreSQL**
   - Configure:
     - Name: `nonogram-db`
     - Database: `nonogram_prod`
     - User: (choose a username, not "postgres")
     - Region: Same as Flask service
   - Wait 2-3 minutes for provisioning

2. **Get Connection String:**
   - Copy the **External Database URL** from the database dashboard
   - Format: `postgresql://user:password@host:5432/nonogram_prod`

3. **Deploy Flask App to Render:**
   - Create a new **Web Service**
   - Connect to your GitHub repo
   - Configure:
     - Runtime: Python 3
     - Build command: `pip install -r requirements.txt && alembic upgrade head`
     - Start command: `python -m flask --app src.nonogram.admin.app run --host=0.0.0.0 --port=$PORT`

4. **Set Environment Variables:**
   - Go to **Environment** settings on the Flask service
   - Add: `DATABASE_URL` = (paste the connection string from step 2)
   - Render auto-redeploys with the env var

5. **Verify Deployment:**
   - Check Render logs for successful migration: `Running upgrade → 001`
   - Visit your service URL (e.g., https://nonogram-admin.onrender.com)
   - Should see the Dashboard with 0 puzzles

### Production Usage

Same workflow as local, but:
- Access at your Render service URL (e.g., https://nonogram-admin.onrender.com)
- Data persists in Render PostgreSQL across sessions
- Batch generation runs synchronously (can take 1-2 min for 200 puzzles)

### Production Monitoring

**View Logs:**
- Render Dashboard → Your service → **Logs** tab
- Search for errors or batch generation activity

**Database:**
- Render Dashboard → PostgreSQL service → **Connection**
- Optional: Connect with psql to inspect puzzles directly
  ```bash
  psql "postgresql://user:password@host:5432/nonogram_prod"
  ```

## Batch Generation Details

### Parameters

| Parameter | Range | Default | Notes |
|-----------|-------|---------|-------|
| Count | 50-200 | 100 | Number of puzzles to generate |
| Sizes | 10-30 | 10,15,20,25,30 | Comma-separated grid dimensions |
| Theme | christmas, halloween, easter, valentine, generic | christmas | Puzzle theme (metadata) |
| Source | random, images | random | Generation source |
| Quality Filter | 0-100 | 0 | Minimum quality score to store |

### Process

1. **Generation**: Random grids created with configurable density
2. **Metrics Calculation**:
   - **Difficulty Score**: 1-100 based on solving strategy complexity
   - **Difficulty Tier**: Easy / Medium / Hard (auto-classified)
   - **Quality Score**: 1-100 based on grid balance and solvability
   - **Recognizability**: low / medium / high
3. **Storage**: Each puzzle stored in database with full metadata
4. **Status**: New puzzles start in "draft" state (ready for review)

## Puzzle Metrics Explanation

### Difficulty Score (1-100)
- **1-33 (Easy)**: Simple logic, few strategies needed
- **34-66 (Medium)**: Mixed strategies, moderate deduction
- **67-100 (Hard)**: Complex patterns, extensive backtracking

**Strategies Tracked:**
- Line Logic (basic constraint checking)
- Constraint Propagation (cascading deductions)
- Block Elimination (spatial reasoning)
- Pointing Pairs (intersection analysis)
- Backtracking (exhaustive search)
- Ambiguity Detection

### Quality Score (1-100)
- **1-40**: Poor balance, potentially multiple solutions or unsolvable
- **41-70**: Good quality, well-balanced
- **71-100**: Excellent quality, optimal difficulty-to-complexity ratio

### Recognizability
- **high**: Grid density 0.7-0.9 (dense, clear patterns)
- **medium**: Grid density 0.4-0.7 (balanced)
- **low**: Grid density 0.1-0.4 (sparse, abstract)

## Troubleshooting

### Local Issues

**"ModuleNotFoundError: No module named 'nonogram.generation'"**
- Ensure virtual environment is activated: `source .venv/bin/activate`
- Reinstall package: `pip install -e .`

**"database does not exist"**
- Create database: `createdb nonogram_poc`
- Verify DATABASE_URL: `echo $DATABASE_URL`

**Puzzles don't appear after batch generation**
- Check logs for errors
- Verify database connection: `psql $DATABASE_URL -c "SELECT COUNT(*) FROM puzzles;"`
- Run E2E tests: `pytest tests/test_batch_generation_e2e.py -v`

### Render Issues

**"403 Forbidden" or connection refused**
- Verify Flask app is running in Render logs
- Check if port collision (use port 8888 locally instead of 5000)

**"No puzzles found" after batch generation**
- Verify DATABASE_URL env var is set and correct
- Check Render logs: `ERROR.*database` or `ERROR.*connect`
- Confirm PostgreSQL database exists and is running
- Verify migrations ran: look for `Running upgrade → 001` in logs

**Batch generation hangs**
- Free instances on Render spin down with inactivity
- Upgrade instance or ping it first to wake up
- Monitor: Render dashboard → service → **Metrics**

## Performance Notes

### Local Machine
- 50 puzzles: ~5 seconds
- 100 puzzles: ~10 seconds
- 200 puzzles: ~20 seconds

### Render (Free Tier)
- Much slower due to resource limits
- May take 60+ seconds for 200 puzzles
- Recommended: Use "Small Batch" (50 puzzles) for testing
- Use "Large Batch" (200 puzzles) for final book generation after hours

## Database Schema

### Puzzles Table
```sql
CREATE TABLE puzzles (
    id VARCHAR PRIMARY KEY,
    grid JSONB NOT NULL,              -- 2D boolean array
    clues_rows JSONB NOT NULL,         -- Row clues [[1,2], [3], ...]
    clues_cols JSONB NOT NULL,         -- Column clues
    width INTEGER NOT NULL,            -- 10-30
    height INTEGER NOT NULL,           -- 10-30
    theme VARCHAR,                     -- christmas, halloween, etc.
    difficulty_score INTEGER,          -- 1-100
    difficulty_tier VARCHAR,           -- Easy, Medium, Hard
    quality_score INTEGER,             -- 1-100
    recognizability VARCHAR,           -- low, medium, high
    strategies_used TEXT[],            -- [LineLogic, ConstraintProp, ...]
    status VARCHAR DEFAULT 'draft',    -- draft, approved, rejected, in_book
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Next Steps

After completing puzzle generation and review:

1. **Create Book**: Select approved puzzles and generate PDF
2. **Review Book**: Download PDF and verify layout/content with team
3. **Upload to KDP**: Submit final PDF to Amazon Kindle Direct Publishing
4. **Monitor**: Check Render logs regularly for errors

---

**Last Updated**: 2026-09-07  
**Admin Panel Version**: 1.0  
**Database**: PostgreSQL 15+

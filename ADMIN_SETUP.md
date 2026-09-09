# Admin Panel Setup — Local & Render

This guide covers setting up the Flask admin panel for batch puzzle generation with persistent database storage (PostgreSQL).

## Local Development Setup

### Prerequisites

- Python 3.14+
- PostgreSQL 15 (via Homebrew)
- Virtual environment

### 1. Install Python Dependencies

```bash
python3.14 -m venv .venv
./.venv/bin/pip install -e '.[dev]'
```

### 2. Start Local PostgreSQL

Homebrew Postgres is already installed. Start the service:

```bash
brew services start postgresql@15
```

Verify it's running:

```bash
psql -l | grep nonogram
```

If the database doesn't exist, create it:

```bash
createdb nonogram_dev
```

### 3. Run Database Migrations

```bash
export DATABASE_URL="postgresql://omelnikova@localhost:5432/nonogram_dev"
alembic upgrade head
```

This runs both migrations:
- `001_create_initial_schema` (users, books, generation_history)
- `002_add_batches_and_puzzles` (batches table, nonograms→puzzles rename)

Verify tables were created:

```bash
psql nonogram_dev -c "\dt"
```

Expected tables: `alembic_version`, `batches`, `books`, `generation_history`, `puzzles`, `user_selected_books`, `users`

### 4. Start Flask Admin Panel

```bash
export DATABASE_URL="postgresql://omelnikova@localhost:5432/nonogram_dev"
python -m flask --app src.nonogram.admin.app run --debug --port 8888
```

The app will start at **http://localhost:8888**

### 5. Test the Workflow

1. **Navigate to** http://localhost:8888/batch/create
2. **Upload images** (3-5 PNG/JPG images)
3. **Set options:**
   - Quality Score: 80 (default)
   - Size: Medium (default)
4. **Click "Next: Preview Images"**
   - Review cropped images
   - Adjust sizes if needed
5. **Click "Next: Generate Puzzles"**
   - Generation runs in real time
   - Puzzles are committed to PostgreSQL as they're created
6. **On "Generated Puzzles" page:**
   - View generated puzzles with SVG grids
   - Click "Approve" or "Reject" on individual puzzles
7. **Test crash recovery:**
   - Stop Flask (`Ctrl+C`)
   - Restart Flask (same command)
   - Navigate back to batch detail view
   - **Puzzles should still be there** (persisted to PostgreSQL)

### Troubleshooting Local Setup

**Port 8888 in use:**
```bash
lsof -i :8888
# Kill the process if needed, or use a different port:
python -m flask --app src.nonogram.admin.app run --debug --port 8889
```

**PostgreSQL connection refused:**
```bash
# Check if service is running
brew services list | grep postgres

# Restart if needed
brew services restart postgresql@15
```

**Database doesn't exist:**
```bash
# Create it manually
createdb nonogram_dev

# Then run migrations again
export DATABASE_URL="postgresql://omelnikova@localhost:5432/nonogram_dev"
alembic upgrade head
```

---

## Render Deployment

### Prerequisites

- Render account with PostgreSQL add-on already configured
- GitHub repository linked to Render
- `DATABASE_URL` environment variable set on Render

### Deployment Steps

1. **Push to main branch:**
   ```bash
   git push origin main
   ```

2. **Render automatically deploys:**
   - Pulls latest code
   - Runs build command: `pip install -r requirements.txt && alembic upgrade head`
   - Migration `002` runs against production Postgres
   - Flask app starts with DB-backed services

3. **Verify deployment:**
   - Check Render build logs for `alembic upgrade head` success
   - App should be running at your Render URL

### Testing on Render

1. **Navigate to** your Render app URL + `/batch/create`
2. **Upload 2-3 test images**
3. **Complete workflow** to approval stage
4. **Approve/reject** puzzles
5. **Kill the dyno** (Render dashboard → manually restart service)
6. **Wait for auto-restart** (30-60 seconds)
7. **Reload app** — batch and puzzles should still be there

---

## Architecture

### Database Schema

**Batches table:**
- `id` (UUID, PK)
- `status` (pending/generating/complete/error)
- `total_count` (number of images/puzzles to generate)
- `completed_count` (generation progress)
- `puzzle_count` (how many passed quality filter)
- `sizes` (JSON array of puzzle sizes)
- `theme` (e.g., "christmas")
- `quality_filter` (minimum quality score, 0-100)
- Timestamps: `created_at`, `updated_at`, `completed_at`

**Puzzles table:**
- `id` (UUID, PK)
- `batch_id` (FK → batches.id)
- `grid` (JSON: list[list[bool]])
- `clues_rows`, `clues_cols` (JSON: list[list[int]])
- `width`, `height` (10-30)
- `theme`, `difficulty_score`, `difficulty_tier`, `quality_score`
- `status` (draft/approved/rejected/in_book)
- `source_image` (filename, if from images)
- Timestamps: `created_at`

### Crash Recovery Design

- Batch row created with `status=generating` **before** generation starts
- Each puzzle committed **individually** as it's generated (not batched into one transaction)
- If generation crashes on puzzle 47/100:
  - Batch row left at `status=generating`, `completed_count=46`
  - 47 real Puzzle rows exist in database (queryable)
  - No data loss, but batch isn't auto-resumable (manual inspection only)
- On server restart, batch/puzzles are still visible in dashboard

### Code Location

- **Routes:** `src/nonogram/admin/app.py`
- **Services:**
  - `src/nonogram/admin/batch_generator.py` (creates batches, coordinates generation)
  - `src/nonogram/admin/puzzle_review.py` (stores/queries puzzles, filters)
- **Models:** `src/nonogram/db/models.py`
- **Migrations:** `migrations/versions/002_add_batches_and_puzzles.py`
- **Configuration:** `render.yaml` (includes `alembic upgrade head` in build step)

---

## Environment Variables

### Local
```bash
export DATABASE_URL="postgresql://omelnikova@localhost:5432/nonogram_dev"
```

### Render
- Automatically set via Postgres add-on
- Visible in Render dashboard: Settings → Environment Variables

---

## Next Steps

### Testing Checklist (CARD-401 to CARD-411)

**Local (CARD-401 to CARD-405):**
- [ ] Set up local Postgres (this guide)
- [ ] Run migrations
- [ ] Create batch, generate puzzles, verify persistence
- [ ] Test crash recovery: stop/restart Flask, verify data persists
- [ ] Approve/reject puzzles, verify status persists

**Render (CARD-410 to CARD-411):**
- [ ] Deploy to Render (git push)
- [ ] Create batch on live admin panel
- [ ] Verify data persists through dyno restart
- [ ] Create second batch, confirm multiple batches coexist

### Future Work

- [ ] Image-based generation (`source=images` path)
- [ ] Batch auto-resume on restart (currently inspectable-only)
- [ ] Bulk approve/reject operations
- [ ] Batch analytics dashboard
- [ ] Monitoring/alerting for generation timeouts


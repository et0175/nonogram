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

> **This machine only.** The admin panel has no login and a route that rewrites
> every stored grade, so it is reachable from this computer and nowhere else
> (CON-015, CON-016). Two things enforce that: the bind address, and a check on
> the `Host` header of every request.
>
> The command above is already loopback — that is Flask's default. What changed
> in CARD-081 is `python -m nonogram.admin.app`, the other entry point, which
> used to bind every interface with the debugger on.
>
> **If you were reaching the admin from a phone or another machine, that no
> longer works, and `flask run --host=0.0.0.0` will not bring it back** — the
> `Host` check refuses those requests whatever the socket is bound to. Use an
> SSH tunnel instead: `ssh -L 8888:127.0.0.1:8888 <this-machine>`, then open
> `http://localhost:8888` on the other device.

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

### Who can reach the deployed panel

**The admin panel has no login of its own beyond the password below, and
`POST /regrade` rewrites the difficulty score, tier and strategies of every row
it can grade — keeping no copy of what it replaced.** Anyone holding
`ADMIN_PASSWORD` can do that, delete puzzles, and run bulk curation against
production. Treat the password as the only thing standing between the internet
and the production data, because it is.

By default the panel refuses every request that did not come from the machine
it runs on (CARD-081), which on Render means **every request returns 404**.
That is not a broken deploy — it is the panel declining to be public. Remote
access is opt-in, and turning it on means setting all four variables below.

### Environment variables

| Variable | Set it to | Secret |
|---|---|---|
| `ADMIN_ALLOWED_HOST` | your service's hostname, e.g. `nonogram-admin.onrender.com` | no |
| `ADMIN_USER` | a username (defaults to `admin` if unset) | no |
| `ADMIN_PASSWORD` | a long random string | **yes** |
| `SECRET_KEY` | a long random string | **yes** |
| `DATABASE_URL` | Render's **internal** Postgres URL | **yes** |

`render.yaml` declares the secret-bearing ones as `sync: false`, so Render
prompts for the values instead of reading them from this repository. Never
commit a value for any of them.

Generate the two random strings with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**The app refuses to start** if `ADMIN_ALLOWED_HOST` is set and either
`ADMIN_PASSWORD` is missing or `SECRET_KEY` is still the built-in development
value. A half-finished setup fails the build with an `AdminConfigurationError`
naming the variable, which is deliberate: a build you can fix in a minute is
better than a panel that came up reachable with no password.

Setting `ADMIN_ALLOWED_HOST` **closes** the loopback door rather than adding to
it. In deployed mode a request claiming `Host: localhost` gets the same 404 as
any other stranger, even carrying valid credentials — behind a proxy the `Host`
header is written by the caller, so leaving that door open would make it a
password bypass.

### Prerequisites

- Render account with PostgreSQL add-on already configured
- GitHub repository linked to Render
- The environment variables above set in the Render dashboard

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
   - Check the logs for `AdminConfigurationError` — that means a variable above
     is missing, and the service will not be serving
   - Open your Render URL: the browser should show a password prompt. If you
     get a 404 instead, `ADMIN_ALLOWED_HOST` does not match the hostname you
     typed; if you get in with no prompt, stop and check the variables, because
     the panel is open.

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


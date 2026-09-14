# Operational snapshots

## Take a snapshot before every re-grade run

`admin/regrade.py` overwrites `difficulty_score`, `difficulty_tier` and
`strategies_used` on every row it can grade. **It keeps no copy of what it
replaced.** The only record of a row's pre-run grade is a snapshot taken
before the run and committed here.

This used to be the `legacy_difficulty_score`/`legacy_difficulty_tier` columns
(migration 006). CARD-084 dropped them in migration 007: the capture was
once-per-row-*ever* by construction, so it recorded the state before the
*first* run and was blind to every run after it — and across all three
databases it had held 0 non-NULL values, because production's rows were
re-graded out of band on 2026-09-13, before the columns existed.

### How

```bash
.venv/bin/python - <<'PY'
import json, datetime
from sqlalchemy import create_engine, text

URL = "postgresql://localhost/nonogram_dev"   # or the database you are about to run against
NAME = "nonogram_dev (local)"

eng = create_engine(URL)
with eng.connect() as c:
    before = c.execute(text("select count(*) from puzzles")).scalar()
    rows = c.execute(text(
        "select id, difficulty_score, difficulty_tier, strategies_used"
        " from puzzles order by id"
    )).mappings().all()
    after = c.execute(text("select count(*) from puzzles")).scalar()

# A snapshot read while the admin panel is in use is a torn read of a moving
# target, and a torn snapshot is worse than none: it looks authoritative.
assert before == after == len(rows), f"table moved during read: {before} -> {after}"

out = {
    "taken_at": datetime.datetime.now(datetime.UTC).isoformat(),
    "database": NAME,
    "rows": [
        {
            "id": str(r["id"]),
            "difficulty_score": r["difficulty_score"],
            "difficulty_tier": r["difficulty_tier"],
            "strategies_used": r["strategies_used"] or [],
        }
        for r in rows
    ],
}
stamp = datetime.date.today().strftime("%Y%m%d")
with open(f"meta/ops/dev-grades-backup-{stamp}.json", "w") as f:
    json.dump(out, f, indent=2)
    f.write("\n")
print(f"{len(rows)} rows")
PY
```

Then **commit it before running the re-grade**, not after.

Two rules the assertion exists to enforce:

1. **Quiet the database first.** Close the admin panel. A snapshot taken while
   rows are being created or deleted captures a row set that never existed.
2. **A snapshot is per-database.** Production, dev and the SQLite file have
   different rows; a snapshot of one says nothing about another.

## What is here

| file | database | rows | taken |
|---|---|---|---|
| `render-grades-backup-20260913.json` | `nonogram_ubss` (Render, production) | 86 | 2026-09-13, before the out-of-band re-grade |
| `dev-grades-backup-20260914.json` | `nonogram_dev` (local Postgres) | 294 | 2026-09-14, before migration 007 dropped the legacy columns |

The dev snapshot additionally carries `legacy_difficulty_score` and
`legacy_difficulty_tier` for each row, since it was taken while those columns
still existed. Both were NULL on all 294 rows.

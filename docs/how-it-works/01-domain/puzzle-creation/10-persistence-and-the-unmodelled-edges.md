# 10 — Persistence, and the edges the model does not draw (COMP-010 and beyond)

> Scope: `src/nonogram/db/` (726 lines), the dual-mode doubling it forces on the
> admin package, and the four parts of the tree no component in the model names.

## Why there is a database at all, and why only one caller reaches it

CON-017 superseded CON-003 on 2026-09-22. The pipeline persists nothing beyond its
exports; **the admin panel is the only exception and the only inbound edge to
COMP-010.** `c4/components-CTX-001.puml`'s persistence note says it outright, and
adds the evidence: "nothing outside `src/nonogram/admin/` imports `nonogram.db`
(grep-verified, CARD-112)."

That still holds. Grepping the tree for `nonogram.db` finds 47 hits, all inside
`admin/`: `regrade.py:91`, `puzzle_review.py` (20 sites), `book_manager.py` (18),
`book_membership.py:216`, `batch_generator.py` (5), `app.py:1375`. All of them are
**function-local** imports, deliberately, so SQLAlchemy stays the optional `db`
extra (`app.py:6230`).

`trace.yml:2389` records why COMP-009 and COMP-010 are two components and not one:
"nothing in `db/` knows the admin exists: `admin/` imports `db/`, never the
reverse, and the orchestrator-driven paths reach neither."

> **A gap worth knowing.** The import guard ranks `db` as a *capability* by
> **fallthrough** (`tests/test_cli.py:801`-`810`: not an adapter, not the
> orchestrator, not shared → rank 2), not by declaration. That happens to forbid
> a capability importing it (2 ≤ 2 fails) — but the property CON-017 actually
> states, "the admin panel is the only inbound edge to COMP-010", rests on **grep,
> not on the guard**. A future second adapter importing `db` would pass.

## Engine selection: one env var, no fallback

`db/session.py`:

| Name | Value / behaviour | Line |
|---|---|---|
| `_init_engine()` | reads `os.getenv('DATABASE_URL')` **fresh on every call** and rebuilds when it changed | `:183` |
| unset `DATABASE_URL` | `RuntimeError("DATABASE_URL not set. Database persistence disabled. …")` — **no sqlite fallback, no default** | `:196` |
| `POSTGRES_DRIVER` | `"psycopg2"`, named *in the URL* by `normalized_url` rather than inherited | `:70` |
| `CONNECT_TIMEOUT_SECONDS` | `10`, added as `connect_args` only for `_TIMEOUT_SCHEMES = ("postgresql", "postgres")` | `:40`, `:48` |
| `session_scope()` | the contextmanager every admin service is injected with: init, yield, **commit on success, rollback on exception, always close** | `:443` |
| `reset_engine()` | disposes the pool and clears the cache key; **its only caller is the test suite** | `:211` |

The fresh read is explicit about who it is for: the test suite's monkeypatch
toggling, and callers that import before the environment is set up.

`normalized_url` (`:79`) exists because of a real production outage.
`pyproject.toml:46` carries the history: SQLAlchemy was capped below 2.1 for a day,
because 2.1.0 changed the default DBAPI for a bare `postgresql://` URL from
psycopg2 to psycopg (v3) and **broke the deployed panel's boot with
`No module named 'psycopg'`**. CARD-148 removed the cap *and the reason for it* —
the driver is now named in the URL, and `tests/test_db_url_driver.py` fails if that
named driver is not installed. The connect deadline is read off the **raw** URL so
both spellings stay live, pinned by
`test_the_connect_deadline_still_reaches_a_normalised_url`.

`db/__init__.py` uses **PEP 562 `__getattr__`** (`:18`) to forward `engine`,
`SessionLocal` and `DATABASE_URL` to `session.py` dynamically, because a plain
`from .session import engine` "would copy whatever `session.engine` happened to be
at THIS module's first import — which is always `None`."

`get_db()` (`:437`) is labelled "Dependency for FastAPI (alias)" — a vestige.
Nothing in this repository is FastAPI.

## Dual mode: the structural fact that doubles the admin package

`create_app` chooses once, per call (`app.py:1367`), deliberately so because
"`DATABASE_URL` can differ per call (the test suite relies on this to toggle
DB-backed vs. in-memory mode via monkeypatch)":

- `DATABASE_URL` set → services built with `session_factory=session_scope`, log
  "Database persistence enabled (DATABASE_URL set)";
- unset or import failure → `session_factory=None`, **in-memory dicts**, log
  "Running in in-memory mode (DATABASE_URL not set)".

So every `BookManager` / `PuzzleReviewService` method has two arms (`if
self._session_factory is None:` … `else:` — e.g. `set_book_status` at
`book_manager.py:2282` vs `:2304`). **This doubling is the single biggest
structural fact about the admin package**, and it is what makes the owner's
observation that DB-mode tests can skip green matter: the in-memory arm is the one
exercised when no database is configured.

`sqlite_session_scope` is a **test helper**, not production
(`tests/helpers/db.py`), used by `tests/test_card_107_orphaned_book_ids.py:34`,
`test_batch_requested_tier.py:32`, `test_book_trim_persistence.py:61`,
`test_book_arrange_size_filter.py:51` and others. `test_batch_requested_tier.py:14`
states its purpose: "DB mode runs over `tests/helpers/db.py:sqlite_session_scope`
so it never [touches the real database]."

`gunicorn --workers 1` (`start.sh:46`), in-memory mode, and the two-phase manual
edit whose proof is held on a service instance together mean **the panel is
single-process by construction, not by configuration.** See
[09](09-the-three-inbound-adapters.md) and the SRE perspective.

## The schema: six tables, three of them unread

`db/models.py`, `Base = declarative_base()` (`:10`):

| Table | Model | Line | Read or written by code? |
|---|---|---|---|
| `batches` | `Batch` | `:25` | yes |
| `puzzles` | `Puzzle` | `:51` | yes |
| `books` | `Book` | `:113` | yes |
| `users` | `User` | `:13` | **no** |
| `generation_history` | `GenerationHistory` | `:207` | **no** |
| `user_selected_books` | `UserSelectedBook` | `:219` | **no** |

All three orphans were created by `migrations/versions/001_create_initial_schema.py`
(`generation_history` at `:71`, `user_selected_books` at `:84`, both dropped in its
`downgrade`). **No later migration — 002 through 016 — touches any of them.**

Grepping `src/`, `scripts/` and `migrations/` for `UserSelectedBook`,
`user_selected_books`, `GenerationHistory`, `generation_history` and `User`,
excluding `models.py` itself, returns **only the six lines inside migration 001**.
`generation_history` appears in exactly one test, and as a fixture proving nothing
writes it: `tests/test_puzzle_solver_page.py:1298` carries
`_WATCHED_TABLES = ("puzzles", "books", "batches", "generation_history")`, seeds a
row at `:1316`, and asserts at `:1324` that an open-play-solve cycle changes none
of them (AC-302).

> **The component diagram is right about two of the three, and understates the
> problem by one.** `c4/components-CTX-001.puml:… COMP-010` describes the store as
> "Batches, puzzles, books **and generation history** … The schema also carries
> `users` and `user_selected_books`, which no code path reads or writes."
> `generation_history` is in the *live* list and in fact belongs in the *unread*
> one. COMP-010's live contents are **three** tables, and the unread set is
> **three**, not two. `c4/containers.puml`'s Admin Database description makes the
> same claim.
>
> The puml calls the disposition "CARD-111 option B, undecided", so this is a
> recorded open question rather than forgotten code. **Not determinable from
> code:** whether any of the three holds rows. That would need the live database,
> which these docs were written without touching.

### What the column types encode

Three things in `models.py` are decisions worth carrying.

**`puzzles.grid`/`clues_rows`/`clues_cols` are plain `JSON`, deliberately NOT
`MutableList`** (`:58`): "these are written whole and never edited in place, and
`MutableList` tracks only top-level mutation — on a list of rows it would report
nothing while a cell changed, which is worse than not claiming to track them at
all." `clues_rows` is annotated `# display only` (`:63`) — **the authority is
always the grid, re-encoded**, which is also how
[08](08-playing-a-stored-puzzle.md) keeps a stale row from showing clues that
disagree with its own picture.

**`books.puzzle_ids`/`puzzle_titles`/`book_metadata` ARE
`MutableList/MutableDict.as_mutable(JSON)`** (`:139`), and the CARD-101 comment at
`:123` is the clearest failure story in the db layer:

> SQLAlchemy decides what to write by object identity, so `row.puzzle_ids[i] = x`
> changed the object in memory and wrote nothing at all. In DB mode, which is
> production, that silently lost every 'move up', every 'move down', and every
> title after a book's first… **the losing pattern is the one that looks correct,
> it is invisible in a diff, and it did not even fail consistently** — a write
> while the column was still NULL persisted, because `or {}` built a new dict.

And the wrapper is documented as **insufficient for one column**:
`distribution_plan` (`:154`) is `MutableDict` but "it tracks only TOP-LEVEL key
assignment … an in-place edit there such as `doc["cells"][2][2] = 20` is **NOT**
flagged dirty and is silently lost. The document must therefore always be replaced
whole — assign `plan_to_json(plan)`, as `BookManager.save_plan` does."
`floor_overrides` (`:169`) is `MutableList` and the comment explains why that *is*
enough there: no nesting at all.

**Three different NULL semantics sit side by side** (`:196`), and reading them
together is the fastest way to understand the book store:

| Column | NULL means |
|---|---|
| `distribution_plan` | no plan — refused at the readiness gate |
| `floor_overrides` | "no override was ever given" — the **fail-closed** reading |
| `interior_ink_mode` | **is** the default (`bw`), so "the backfill and the reader agree rather than one covering for the other" |

Trim and margins are stored as **strings** "for precision" (`:171`), defaulting to
`'21.59'` × `'27.94'` cm (= 8.5 × 11 in) with `'1.27'` cm gutter and outside.

`puzzles.book_id` → `books.id` carries `ondelete='SET NULL'` (`:86`), and the choice
is argued rather than defaulted: "RESTRICT would turn 'delete this book' into an
error the panel has no wording for, and would leave a deleted book's puzzles
permanently unrejectable — a worse hole than the one this closes" (CARD-103).

`db/models.py:69`'s comment is stale against ADR-0031:
`difficulty_tier = Column(String, nullable=True)  # 'easy'/'medium'/'hard'/'guess'`.

## The parts of the tree no component names

`trace.yml`'s `components:` block (`:2356`) maps ten COMPs to code globs. Four
things in `src/nonogram/` fall outside all of them. Re-derived with `wc -l` over
`find src/nonogram -name '*.py'`:

| Path | Lines | Status |
|---|---|---|
| `errors.py` | 190 | shared rank, covered by `trace.yml`'s prose but no COMP row |
| `limits.py` | 17 | same |
| `analysis/quality_metric.py` | 303 | **live shipped code**, no component |
| `analysis/strategy_counter.py` | 151 | unreferenced, no component |
| `__init__.py` | 54 | the canonical package map itself |
| **unmapped total** | **744 of 46,127** | **1.6% of the package** |

`trace.yml:2390` records that COMP-009 and COMP-010 were added in CARD-110 to close
a far larger version of this gap: "38% of the package (9,230 of 24,117 lines) had
no component, so rows about admin behaviour named COMP-008 — the web UI — for want
of an id." The package has since grown to 46,127 lines and the gap is down to 1.6%.

### `analysis/quality_metric.py` — live, and unmodelled

303 lines of NumPy/Pillow image analysis, imported at `admin/app.py:138`
(`from nonogram.analysis.quality_metric import measure_quality`) and called at
`:1942`. `admin/pdf_generator.py:200` records the policy it implements: "image mode
gets a real 1..100 from `measure_quality`" (CARD-050).

Three components — `calculate_visual_similarity` (`:119`),
`calculate_silhouette_match` (`:148`), `calculate_density_match` (`:209`) — are
folded by `measure_quality` (`:240`) into `QualityMetrics` (`:26`) with a
`Recognizability` enum (`:17`: HIGH ≥ 80%, MEDIUM 50–80%, LOW < 50%), an integer
`quality_score` 1–100, and `to_dict()` (`:43`) "for database storage".

**This is the machinery behind ADR-0032/R2** ("an unmeasured quality score is
unknown, never zero" — see [07](07-book-assembly-and-the-admin-panel.md)), and the
model does not mention the module at all. That is a genuine component gap rather
than a naming quibble: NumPy-heavy image analysis, on the shipping path, outside
every box any C4 diagram draws.

### `analysis/strategy_counter.py` — unreferenced, and a second scorer

151 lines with **no importer anywhere under `src/`**. Its only consumer is
`tests/test_strategy_counter.py:4`, which imports it as
`from src.nonogram.analysis.strategy_counter import …` — a `src.`-prefixed path,
not the installed package path.

What it contains matters more than that it is unused: a `Strategy` enum (`:17`:
`LINE_LOGIC`, `CONSTRAINT_PROPAGATION`, `BLOCK_ELIMINATION`, `POINTING_PAIRS`,
`BACKTRACKING`, `AMBIGUITY`) and `calculate_difficulty_from_strategies(counter)
-> int` (`:92`) — **a second, parallel difficulty scorer** whose vocabulary matches
neither the shipped three-rung ladder (`simple_overlap < line_dp <
probe_contradiction`, ADR-0029) nor its design: `BACKTRACKING` and `AMBIGUITY` are
the notions ADR-0031 retired as *difficulties*.

`src/nonogram/__init__.py:35` records it as deliberately kept — "a prototype of the
scoring design in `docs/REQUIREMENTS/DIFFICULTY_ENGINE.md` that nothing on the
shipping path calls (CARD-053 kept it deliberately — the rescoring question it
belongs to is still open)". So it is not forgotten, but it must not be read as part
of CAP-004.

Both `analysis/` modules are stylistically pre-forge (`from typing import Set,
List, Tuple`, no `from __future__ import annotations`), a tell that they entered
outside the card pipeline.

### Two dormant admin modules, and 120 KB of unmodelled browser code

Also outside any component, though inside `admin/`'s glob:

- `admin/pdf_generator.py` (349 lines) — the **only `reportlab` user in the tree**,
  reachable only from tests. `app.py:5799` records that a route "went through
  `admin/pdf_generator`" *until* CARD-135.
- `admin/book_membership.py` (277 lines) — a one-off repair utility (`backfill`,
  `release_orphans`, CARD-100), reachable only from tests, referenced in prose at
  `db/models.py:79`, `book_manager.py:1057`, `puzzle_review.py:2092`. Not wired to
  any route.
- `admin/static/solver.js` (76,946 bytes) and `solver_state.js` (42,903 bytes) —
  CAP-007's actual implementation, governed by ADR-0038, contained by no C4
  element. See [08](08-playing-a-stored-puzzle.md).
- `web/metadata.py` (140 lines) and `web/static/metadata.js` (380 lines) — the
  server-side module has no production caller and the client-side script does the
  shipped work. See [09](09-the-three-inbound-adapters.md).

**Not determinable from code** for `admin/pdf_generator.py`,
`admin/book_membership.py` and `web/metadata.py`: whether each is retained
deliberately or simply unremoved. No card states an intent for the *modules*
themselves — only for the call sites that were deleted.

## Bounds and honest gaps

- **Nothing in this aspect was verified against a live database.** Whether the
  three orphan tables hold rows, and whether any `puzzles` row still carries
  `difficulty_tier = 'guess'`, are not determinable from code. The readers would
  treat a surviving `'guess'` as "no recognisable tier":
  `difficulty.tier_of_record` returns `None`, and `book_plan.selection_cells`
  (`:359`) drops such a record from every bucket, so the row would silently belong
  to no plan cell.
- `reset_count()` (`session.py:356`) counts **calls, not disposals** — a detail
  that matters if you read it as a leak metric.
- `tests/test_quality_metric.py:6` and `tests/test_strategy_counter.py:4` import
  through `src.nonogram.…` rather than `nonogram.…`. Since
  `pyproject.toml` sets `pythonpath = ["src"]`, that exercises a second import path
  for the same files and can produce duplicate module objects alongside the
  installed package — the same class of trap `start.sh` documents for the
  `Procfile`'s `src.nonogram.admin.app` (see [09](09-the-three-inbound-adapters.md)).

## Related

- [07-book-assembly-and-the-admin-panel.md](07-book-assembly-and-the-admin-panel.md) — COMP-010's only caller
- [01-the-layered-pipeline.md](01-the-layered-pipeline.md) — why `db/` ranks as a capability
- ADRs: [ADR-0032](../../../../meta/architecture/decisions/adr/0032-admin-storage-guarantees.md) · [ADR-0006](../../../../meta/architecture/decisions/adr/0006-dependency-baseline.md)
- `DATABASE_MIGRATIONS.md` and `docs/DB_PERSISTENCE_IMPLEMENTATION.md` at the repo root · `migrations/versions/`

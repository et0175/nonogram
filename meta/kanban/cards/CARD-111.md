# CARD-111: CON-003 says "no persistence, ever" and the admin panel runs on Postgres

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d (option A) / 1d (option B)
**Complexity:** standard
**Skill:** business-analyst
**TDD:** false — model and documentation only; **no schema change, no migration**
**Branch:** card/111-con-003-persistence
**Worktree:** —
**Source:** CARD-110, which stopped on AC-3 for this reason (G-2); the contradiction is recorded in that card's Worktree notes and in `trace.yml`'s replacement for the old mapping-gap note
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** meta/architecture/requirements.yml (CON-003, and a superseding CON), meta/business/vision.md (the Non-goals line CON-003 is sourced from), meta/architecture/c4/containers.puml + context.puml + components-CTX-001.puml (three comments asserting there is no database), meta/architecture/decisions/open.yml (two collapsed decisions that leaned on CON-003) — and, under option B, a decision about `db/models.py`'s unused `User` tables
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

`CON-003` is live, unsuperseded, `type: organizational`, sourced from
`meta/business/vision.md`'s Non-goals:

> No multiplayer, user accounts, or persistence beyond local file export,
> **ever**.

The admin panel ships six SQLAlchemy tables, ten Alembic revisions and a
Postgres deployment. Two of that constraint's three clauses are contradicted by
code that is merged, deployed and being used to make books.

**This is not a stale comment; it is load-bearing.** CON-003 is cited as a
premise in places that made real decisions:

- `c4/containers.puml:15` — *"CON-003 (no persistence beyond local file export
  — hence NO ContainerDb)"*, and the diagram models exactly one container.
- `c4/components-CTX-001.puml:38` — *"No ComponentDb: CON-003 forbids
  persistence… the only durable state is the export file itself."*
- `c4/context.puml:14` — cites CON-001 and CON-003 as the context constraints.
- `decisions/open.yml:95` — a security decision was **collapsed rather than
  taken**: *"the 'no auth' half is already a hard business constraint
  (BCON-0001…) and a technical constraint (CON-003: no user accounts, ever).
  One option only => constraint, not decision."*
- `decisions/open.yml:114` — a concurrency decision collapsed the same way:
  *"BCON-0001 forbids multiple concurrent users outright and CON-003 forbids
  shared state. Constraint, not decision."*
- `ADR-0021` lists CON-003 among its references and states *"No new state is
  introduced anywhere in the system"* as a consequence.

CARD-110 could not draw COMP-009/COMP-010 into C4 without either contradicting
those comments or amending CON-003, so it stopped (its G-2) and left this.

## What is actually true, checked 2026-09-22

**Persistence — real, shipped, unambiguous.** `src/nonogram/db/models.py`
defines `batches`, `puzzles`, `books`, `generation_history`, `users` and
`user_selected_books`; `migrations/versions/` holds 10 revisions from
`001_create_initial_schema`; the owner runs it on Postgres, locally and on
Render.

**User accounts — in the schema, dead in the code.** `User` (with `email`,
`subscription_tier` in `'free'|'premium'`, `puzzles_generated_month`) and
`UserSelectedBook` are created by migration `001` and are referenced **nowhere
in `src/`** — grep-verified. They are scaffolding for a subscription website
that does not exist. So CON-003's "no user accounts" clause is contradicted by
the *schema* and upheld by the *behaviour*, which is a different problem from
the persistence one and wants a different answer.

**Multiplayer — still true.** Nothing here.

## Two precedents for how this goes

- **CON-001 → CON-007.** CON-001 said *"no web/GUI in v1"*. When the web UI
  shipped it was marked `status: superseded` / `superseded_by: CON-007`, and
  CON-007 carries the full replacement statement — *both* interfaces
  first-class, the new one an addition rather than a deprecation. Both
  directions of the link are present and the replacement is not a stub;
  `open.yml` explicitly records that this was the right shape and not worth
  re-litigating as a decision.
- **ADR-0030** already did the business half for the admin's security posture:
  it records that *"BCON-0001's 'one user on one machine' no longer describes
  the deployment"* and retires NFR-003's no-authentication clause **for the
  admin surface only**, leaving the web UI's untouched. The same
  surface-by-surface shape fits here: the generation pipeline still persists
  nothing; the admin panel does.

## The decision this card needs

- **Option A — supersede the persistence clause, narrowly.** Mark CON-003
  superseded by a new CON that says what is true: the CLI and web UI
  pipelines persist nothing beyond the export file, and the admin panel keeps a
  database of batches, puzzles and books. Amend the vision's Non-goals line to
  match, fix the three C4 comments, and note against the two collapsed
  decisions in `open.yml` that their premise changed. Leaves the `users` tables
  alone and says so. ~0.5d.
- **Option B — A, plus settle the `User` tables.** Decide whether
  `users`/`user_selected_books` are a direction you intend to keep or
  scaffolding to drop, and make the constraint text say it. If they are to go,
  that is a migration the **owner** runs — this card would write it and stop.
  ~1d.
- **Option C — A and B, plus reopen the two collapsed decisions.** The "no
  auth" collapse in `open.yml` leaned on CON-003 *and* BCON-0001, and ADR-0030
  has since put a credential on the admin anyway; the concurrency collapse
  leaned on "CON-003 forbids shared state", which a shared database plainly
  does not. Both deserve re-examination, but they are security and concurrency
  decisions, not a constraint edit.

**Recommended: A, with B's question asked plainly in the card's notes and C
filed.** The contradiction that blocks work today is persistence; the `users`
tables are inert and can wait for a decision about the product rather than one
about the model. But **A must not quietly narrow CON-003 to persistence and
leave "no user accounts, ever" standing over a `users` table** — the new
constraint has to state the schema's actual contents, even if the answer is
"these are unused and undecided".

## Acceptance criteria

- **AC-1** — CON-003 carries `status: superseded` and `superseded_by:` a new
  CON whose statement describes both surfaces: the pipeline persists nothing
  beyond exports, the admin panel keeps a database. Both directions of the link
  present, replacement not a stub — the CON-001/CON-007 shape.
- **AC-2** — `meta/business/vision.md`'s Non-goals line, which CON-003 cites as
  its source, no longer contradicts the shipped product. A constraint may not
  be superseded while the document it is sourced from still asserts it.
- **AC-3** — the three C4 comments (`containers.puml:15`,
  `components-CTX-001.puml:38`, `context.puml:14`) state what is true. Drawing
  the containers and components themselves is **CARD-110's AC-3**, still open —
  this card unblocks it and should say so rather than doing it.
- **AC-4** — the two collapsed decisions in `open.yml` (lines ~95 and ~114)
  carry a note that their stated premise has changed, with the date and this
  card's id. They are not reopened here (that is option C).
- **AC-5** — the `users`/`user_selected_books` tables are addressed explicitly
  in whatever the new constraint says: kept, deprecated, or recorded as unused
  and undecided. Silence is not acceptable, because "no user accounts, ever"
  standing over a `users` table is the defect this card exists to fix.
- **AC-6** — no schema change, no migration written or run, and pytest's
  pass/fail set is identical.

## Guardrails

- G-1: **No migration is written or run under option A**, and none is *run*
  under any option — the owner runs migrations against their own databases.
- G-2: No edits under `src/`. If the model turns out to need a code change,
  stop and say so.
- G-3: Do not reopen the collapsed decisions in `open.yml` — annotate them.
  Re-deciding authentication or concurrency inside a constraint edit is exactly
  the mistake CARD-110 avoided by stopping.
- G-4: Do not delete `User`/`UserSelectedBook` without the owner's explicit
  instruction. They are inert, but they are also the visible trace of a product
  direction, and deleting a table is not reversible from the model alone.
- G-5: Commit only your own files — explicit pathspecs.

## Architecture context

- **CON:** CON-003 (the subject), CON-001/CON-007 (the supersession precedent)
- **BCON:** BCON-0001 — "never network-exposed, single actor, no accounts";
  ADR-0030 already records that its first clause no longer holds for the admin
- **ADR:** ADR-0021 (lists CON-003, asserts no new state), ADR-0030 (the
  surface-by-surface precedent), ADR-0032 (states what the admin's storage
  guarantees are, and so assumes storage)
- **Components:** COMP-009, COMP-010 (CARD-110), whose C4 drawing this unblocks

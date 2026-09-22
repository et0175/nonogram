# CARD-110: Give admin/ and db/ a place in the architecture model

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Skill:** business-analyst
**TDD:** false — model and documentation only, no production code
**Branch:** card/110-admin-db-component-ids
**Worktree:** ../PythonProject4-CARD-110
**Source:** `meta/architecture/trace.yml:1414` ("KNOWN MAPPING GAP for the owner"), raised again by CARD-053's AC-1 and CARD-056's ADR-0032
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** meta/architecture/trace.yml (the `components:` block and the gap note), meta/architecture/c4/components-CTX-001.puml, src/nonogram/__init__.py (the package map's "not components" paragraph), possibly meta/architecture/domain/contexts.yml and aggregates.yml — see the decision below
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-22
**Closed:** 2026-09-22
**Actual:** 0.4d
**Merge commit:** —
**Blocked by:** —

## Why

`trace.yml:1414` says it plainly, and has for a while:

> KNOWN MAPPING GAP for the owner: COMP-008's declared code glob is
> `src/nonogram/web/**.py`, while the admin panel and DB live in
> `src/nonogram/admin/**` and `src/nonogram/db/**` — no component in this file
> or in `c4/` owns those globs.

`trace.yml`'s `components:` block declares COMP-001..COMP-008 with one code
glob each. Nothing there matches `admin/` or `db/`, so three rows that describe
admin behaviour point at **COMP-008, the web UI adapter**, because the task
that wrote them was told to use an existing id rather than invent one.

**The unowned code is not a corner of the tree.** `admin/` is 13 files and
about 8,600 lines; `db/` is 3 files and ~290. Together that is **9,230 of the
package's 24,117 lines — 38%** — including `app.py` at 2,879 lines on its own.

Two cards have now stopped at this gap rather than closing it:

- **CARD-053** narrowed its AC-1 to `analysis/`/`generation/` and said so,
  because listing `admin/` and `db/` in the package map meant inventing ids.
- **CARD-056** wrote ADR-0032 with both rules scoped `src/nonogram/admin/**`
  — a scope no component owns, which works for `system_rules.py` (it globs
  paths) but leaves the rules attached to no component in the model.

## What this card discovers, and it is bigger than an id

Grep the registry for what the admin panel *does* — books, batches, review and
approval, re-grading, print specs — and the result is:

    CON-015  the admin binds loopback only
    CON-016  the admin's two doors

**That is all.** There is no FR for assembling a book, none for batch
generation, none for the review/approve/reject lifecycle, none for the PDF a
customer actually buys. 38% of the code implements features the requirements
registry never states, which is why no component owns it: the model was never
extended to this half of the product, and a component id is the visible end of
that.

`meta/architecture/domain/aggregates.yml` has exactly one aggregate, AGG-001
(Puzzle). `Book` — which has its own table, its own membership rules
(CARD-100/101/103/107/108), and its own lifecycle — is not modelled at all.
`contexts.yml` already carries a `stale:` marker and argues single-context on
the grounds that "all 5 capabilities act on the single aggregate AGG-001";
that argument does not obviously survive a second aggregate.

## The decision this card needs from the owner

**How much of the model to extend.** Three honest stopping points:

- **Option A — ids only.** Add COMP-009 (Admin Panel, `src/nonogram/admin/**.py`)
  and COMP-010 (Persistence, `src/nonogram/db/**.py`) to `trace.yml`'s
  `components:` block and to the C4 diagram, repoint the three COMP-008 rows
  that are really about admin, and delete the gap note. Closes what
  `trace.yml:1414` asks for and unblocks CARD-053's AC-1 wording. Leaves the
  missing FRs and the unmodelled `Book` exactly as they are. ~0.5d.
- **Option B — ids, plus the admin's capabilities.** A, plus CAP entries for
  what the admin does that CAP-001..005 do not cover (book assembly, curation,
  batch production), so the components hang off capabilities like every other
  component does. Does not attempt the FRs. ~1d.
- **Option C — ids, capabilities, and the `Book` aggregate.** B, plus AGG-002
  and the contexts.yml re-examination that a second aggregate forces. This is
  the honest full answer and it is a different size of job — it reopens whether
  CTX-001 is still one bounded context. Multi-day, and it should be its own
  card rather than this one's tail.

**Recommended: A, with B's gap written down rather than done.** The gap note
asks for ids; ids are what two other cards were blocked on. Capabilities and
the `Book` aggregate are real work but they are *modelling the product*, not
closing a mapping gap, and doing them inside a P2 tech-debt card would bury a
decision about bounded contexts in a commit about globs. A should end by
replacing `trace.yml:1414`'s note with a narrower one naming what is still
unmodelled, so the next reader inherits the real question instead of a solved
one.

## What to implement (option A)

1. Add to `trace.yml`'s `components:` block, in the existing shape:
   - `COMP-009` — Admin Panel — `code: ["src/nonogram/admin/**.py"]`
   - `COMP-010` — Persistence — `code: ["src/nonogram/db/**.py"]`
2. Add both to `c4/components-CTX-001.puml`, with the same one-paragraph
   description style the others carry, and draw the edges that exist: the admin
   drives COMP-002/003/005/006 the way the CLI does, and reads and writes
   through COMP-010. **Do not draw an edge that is not in the code** — check
   each one by grep before adding it.
3. Repoint the three `components: [COMP-008, …]` rows that describe admin
   behaviour (`trace.yml:151` and the two others) at COMP-009 where that is
   what they meant. Read each row first: one of them may genuinely be about the
   web UI.
4. Replace the `trace.yml:1414` gap note with what is still true afterwards —
   no FRs for the admin's features, `Book` unmodelled — rather than deleting it.
5. Update `src/nonogram/__init__.py`'s "also in the tree, deliberately not
   components" paragraph (CARD-053 wrote it): `admin/` and `db/` become
   components with ids, and only `analysis/` stays in that paragraph.

## Acceptance criteria

- **AC-1** — `trace.yml`'s `components:` block has an entry whose `code` glob
  matches every file under `src/nonogram/admin/` and `src/nonogram/db/`, and
  `validate.py --root meta/architecture` reports no new error or warning.
  (The ADR-0025 supersession error is the forge tool's own false positive —
  CARD-071.)
- **AC-2** — no `components:` row in `trace.yml` names COMP-008 for behaviour
  that lives under `src/nonogram/admin/`.
- **AC-3** — `c4/components-CTX-001.puml` draws both new components, and every
  edge drawn from or to them is one that exists in the code, verified by grep
  and named in the Worktree notes.
- **AC-4** — the gap note at `trace.yml:1414` is replaced by a statement of
  what remains unmodelled (the missing FRs, `Book`), not deleted.
- **AC-5** — pytest is unaffected: model and documentation only, so the
  pass/fail set is identical before and after.

## Guardrails

- G-1: No edits under `src/` except `__init__.py`'s package-map docstring.
- G-2: Do not invent capabilities, aggregates or FRs under option A. If the
  work seems to need one, stop and say so — that is options B/C, and the point
  of splitting them is that they are decisions, not bookkeeping.
- G-3: Do not draw a C4 edge to make the diagram look complete. An edge that
  is not in the code is worse than a missing one, because it reads as verified.
- G-4: `c4/components-CTX-001.puml`'s COMP-006 text still describes
  `Tier.GUESS` and ADR-0025, both retired by CARD-098/ADR-0031. It is in the
  file this card edits, so fix it in passing **and say so in the notes** —
  but do not extend that to a general audit of the diagram's prose.
- G-5: Commit only your own files — explicit pathspecs.

## Architecture context

- **Components:** COMP-008 (whose glob is the one currently overreaching)
- **ADR:** ADR-0019 (web UI component boundary — defines COMP-008's scope),
  ADR-0032 (whose two rules are scoped to the unowned admin glob)
- **Trace:** `trace.yml:1414`, the gap note this card answers

## Worktree notes

### Delivered 2026-09-22 — option A, minus AC-3, which is stopped on G-2

**Done:** COMP-009 (Admin Panel, `src/nonogram/admin/**.py`) and COMP-010
(Persistence, `src/nonogram/db/**.py`) exist in `trace.yml`'s `components:`
block; all 16 files under those two directories are owned (AC-1). No row names
COMP-008 for admin behaviour (AC-2). The gap note is replaced rather than
deleted (AC-4). Suite unchanged at 3,681 passed (AC-5). Validator reports the
same single error as before — CARD-071's known false positive in the forge
tool.

**Not done: AC-3, the C4 diagram.** See below. G-2 says stop and say so.

### The card said three rows to repoint. It was three rows — but not those three.

I named `trace.yml:151`, `:508` and `:655`. Reading them: FR-017 ("Local web UI
exposing the same generation options as the CLI"), NFR-003 ("Web UI server
binds 127.0.0.1") and CON-008 ("Web UI v1 renders no in-browser preview") are
all genuinely about the web UI. AC-2 was already satisfied for them.

The rows that actually misused COMP-008 were:

- **CON-015** — "Bind-scope rule for the **ADMIN** panel"
- **CON-016** — "Host-refusal rule for the **ADMIN** panel"
- **FR-029** — the `strategies_used` DB column, the admin detail page and the
  admin filter; this is the row the gap note itself was written on

All three repointed: CON-015/CON-016 to COMP-009, FR-029's COMP-008 to
COMP-009 + COMP-010. `CON-010`, `NFR-004` and `CON-008` keep COMP-008, being
web-UI rules.

### Why two components and not one, verified rather than assumed

`admin/` imports `db/` in six modules; `db/` imports nothing from `admin/`; and
`cli.py`, `web/**` and `orchestrator.py` reach neither. Grep-verified before
the claim was written into `trace.yml` and the package docstring.

### AC-3 is blocked on a live constraint, not on drawing

Both C4 diagrams predate the admin panel, and **both assert there is no
database**:

- `c4/components-CTX-001.puml:37` — *"No ComponentDb: CON-003 forbids
  persistence beyond local file export, so the only durable state is the export
  file itself."*
- `c4/containers.puml:16` — *"ContainerDb: the tool has no database, no cache,
  no state…"*, and it models exactly one container.

**CON-003 is live and unsuperseded**: *"No multiplayer, user accounts, or
persistence beyond local file export, **ever**."* Its source is
`meta/business/vision.md`'s Non-goals. The admin panel ships SQLAlchemy models,
Alembic migrations and a Postgres deployment.

So drawing COMP-009/COMP-010 into the component diagram would either
contradict its own header comment and the container diagram beside it, or
require amending CON-003 — which is a business-level non-goal, sourced from the
vision, and exactly the kind of decision G-2 forbids this card from taking.
There is a precedent for how it should go: CON-001 said "no web/GUI in v1" and
was **superseded by CON-007** when the web UI shipped. CON-003 needs the same
treatment or an explicit carve-out for the admin panel, and that is the owner's
call.

Also noted, not fixed: **COMP-008 is not in the component diagram either.** It
draws COMP-001..007 inside one `Container_Boundary(cliTool, "Puzzle Creation
CLI")`. The web UI adapter has never been drawn, presumably because it is not
the CLI — the same reason the admin panel cannot simply be added to that
boundary. The diagram models the CLI container, and the model's component list
has outgrown it by three.

### G-4 — the stale Guess-tier text, fixed in passing

`components-CTX-001.puml` described COMP-006 as classifying with
`(score, branch_nodes)` and returning `Tier.GUESS` by that fact alone
(EC-015, ADR-0025) — retired by CARD-098/ADR-0031 on 2026-09-18. Four places
corrected: the header index line, the synthesis note, the `Component(...)`
description and the `Rel(orchestrator, difficulty, …)` label. The one remaining
mention of ADR-0025 records it as superseded, which is accurate. No other prose
in the diagram was audited (G-4).

# CARD-112: Draw the admin panel and its database into the C4 diagrams

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Skill:** business-analyst
**TDD:** false — diagrams only, no code, no model ids invented
**Branch:** card/112-c4-admin-containers
**Worktree:** ../PythonProject4-CARD-112
**Source:** CARD-110's AC-3, deferred there because CON-003 forbade what the code already did; unblocked by CARD-111 (CON-017)
**Idea:** —
**Wave:** —
**Depends on:** CARD-110 (the ids), CARD-111 (the constraint) — both done
**Touches:** meta/architecture/c4/containers.puml, meta/architecture/c4/components-CTX-001.puml, meta/architecture/c4/context.puml (only if the decision below says so)
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-22
**Closed:** 2026-09-22
**Actual:** 0.4d
**Merge commit:** e6d93f0
**Blocked by:** —

## Why

CARD-110 gave `admin/` and `db/` component ids (COMP-009, COMP-010) but could
not draw them: all three C4 diagrams asserted the tool has no database, on
CON-003's authority. CARD-111 superseded CON-003 with CON-017 and corrected
those three comments, each of which now names what is missing and points here.

So the ids exist, the constraint permits it, and the diagrams still do not show
**38% of the package**.

## What the diagrams show today, verified 2026-09-22

- **`containers.puml`** — one container, `Puzzle Creation CLI`, plus the local
  filesystem. No admin panel, no database.
- **`components-CTX-001.puml`** — COMP-001..COMP-007 inside a single
  `Container_Boundary(cliTool, "Puzzle Creation CLI")`. **COMP-008, the web UI
  adapter, is not drawn either** — it has never been in this diagram, though
  it has shipped since ADR-0019.
- **`context.puml`** — one system, one actor, the filesystem.
  `external_systems.yml` is `external_systems: []`.

## The facts the drawing has to match

**The admin panel is a second container, not a second adapter in the first
one.** `Procfile` runs it as its own web process
(`flask --app src.nonogram.admin.app run --host=0.0.0.0 --port=$PORT`), on
Render, against Postgres. The web UI is *not* a second container: ADR-0008
keeps one console entry point and `nonogram serve` is a subcommand of it, so
COMP-008 belongs inside the existing container beside COMP-001.

**COMP-009's edges, from a module-level import sweep of `src/nonogram/admin/*.py`:**

    nonogram.orchestrator   nonogram.sourcing   nonogram.solver
    nonogram.difficulty     nonogram.clues      nonogram.export
    nonogram.db             nonogram.analysis   nonogram.errors, nonogram.limits

Two of those are worth drawing deliberately rather than by habit: the admin
calls **COMP-004 (clues) and COMP-005 (solver) directly**, not only through the
orchestrator — that is ADR-0032/R1's storage guard re-deriving clues and asking
for a verdict at the boundary. ADR-0007 permits it (the admin is adapter-rank,
and an adapter may call a capability), and drawing it as "admin → orchestrator
only" would hide the thing ADR-0032 exists to state.

**COMP-010's only inbound edge is COMP-009.** Nothing outside
`src/nonogram/admin/` imports `nonogram.db` — grep-verified, and the same fact
CON-017 relies on.

**The admin also reads and writes the filesystem**: uploaded images in, book
PDFs and rendered grids out.

## The decision this card needs

**Whether to draw COMP-008 while you are in there.**

- **Option A — the two new components only**, exactly as CARD-110's AC-3 is
  worded. Leaves a component diagram that draws COMP-001..007, 009 and 010 but
  not 008, which is a knowingly incomplete diagram and the same class of defect
  this card exists to fix.
- **Option B — COMP-008 as well**, so the component diagram finally shows every
  component the model declares. Its edges are small and already decided by
  ADR-0019/ADR-0020/ADR-0021: the web adapter takes an HTTP request and makes
  the same synchronous call into COMP-002 that the CLI makes.

**Recommended: B.** The extra work is one `Component(...)` and two `Rel(...)`
lines, all of them settled by existing ADRs, and the alternative is shipping a
diagram whose omission we have already noticed and written down twice.

## What to implement

1. **`containers.puml`** — add `Container(adminPanel, …)` and
   `ContainerDb(database, …)` inside the existing `System_Boundary`, with:
   the owner → admin panel edge (HTTP, behind ADR-0030's credential when
   `ADMIN_ALLOWED_HOST` is set), admin panel → database, admin panel →
   filesystem (uploads in, PDFs out). Update the `cliTool` container's own
   description, which describes only the CLI although CON-007 makes the web UI
   a first-class interface in the same process.
2. **`components-CTX-001.puml`** — add `Component(admin, "COMP-009 …")` and
   `ComponentDb(persistence, "COMP-010 …")`, in the description style the other
   components use (what it owns, which ADRs govern it, what it must not do).
   Add the edges listed above, **each verified by grep before it is drawn**,
   and under option B add COMP-008 too. The admin is a second inbound adapter
   and does not belong inside a boundary named "Puzzle Creation CLI" — give it
   its own `Container_Boundary`, matching the container diagram.
3. **`context.puml`** — decide and record whether Postgres is an `EXT-XXX`.
   It is the system's own store rather than a third-party system, so the
   expected answer is **no** and the only change is the header comment CARD-111
   already left; `external_systems.yml` stays `[]`. If the answer is yes, that
   file changes too and the card says why.
4. Remove the "STALE DIAGRAM" / "not drawn" notes CARD-111 left in all three
   files, replacing them with nothing — once the thing is drawn, a note saying
   it is missing is itself stale.

## Acceptance criteria

- **AC-1** — `containers.puml` shows the admin panel as its own container and
  the database as a `ContainerDb`, and the CLI container's description
  acknowledges both of its adapters (CON-007).
- **AC-2** — `components-CTX-001.puml` shows COMP-009 and COMP-010 (and, under
  option B, COMP-008), with the admin outside the "Puzzle Creation CLI"
  boundary.
- **AC-3** — every `Rel(...)` added is backed by an import or call that exists
  in the code, and the Worktree notes list each edge with the grep that
  supports it. An edge that cannot be supported is not drawn (G-1).
- **AC-4** — the admin → COMP-004 and admin → COMP-005 edges are present, with
  the ADR-0032/R1 reason stated in the diagram's own comments, so a reader does
  not "correct" them to route through the orchestrator.
- **AC-5** — the three CARD-111 notes saying the diagrams are stale are gone,
  and `external_systems.yml` is unchanged unless step 3 decided otherwise with
  a reason recorded.
- **AC-6** — every diagram still renders. `plantuml -checkonly` if it is
  available; if it is not, say so in the notes rather than claiming it passed.
- **AC-7** — pytest is unaffected: no `src/`, no tests, diagrams only.

## Guardrails

- G-1: Do not draw an edge to make the picture look complete. An edge that is
  not in the code is worse than a missing one, because it reads as verified.
  (CARD-110's G-3, carried forward.)
- G-2: Do not invent component, capability or aggregate ids. COMP-009 and
  COMP-010 exist; nothing else is created here.
- G-3: Do not restate the architecture in the diagram's prose. Each component's
  description is one paragraph in the existing style — the ADRs remain the
  source of truth.
- G-4: Commit only your own files — explicit pathspecs.

## Noted while verifying, not for this card

`Procfile` launches the admin as `flask --app src.nonogram.admin.app` — the
`src.`-prefixed import path again, the same dual-import condition that hid an
ADR-0007 violation from the structural guard until CARD-050 (see CARD-053's
notes, and the seven test files still doing it). It works only because the repo
root is the process's working directory on Render. It is a deployment file, not
a diagram, so it is out of scope here — but it belongs with the
`from src.nonogram...` sweep when that card is opened.

## Architecture context

- **Components:** COMP-008 (undrawn), COMP-009, COMP-010
- **CON:** CON-007 (both interfaces first-class), CON-017 (what persists where)
- **ADR:** ADR-0008 (one console entry point — why the web UI is not a second
  container), ADR-0019/0020/0021 (COMP-008's boundary and edges), ADR-0030
  (the admin's credential), ADR-0032 (why admin → clues/solver is direct)

## Worktree notes

### Delivered 2026-09-22 — option B

All three C4 diagrams now describe the system that ships. The component diagram
draws **COMP-008 for the first time** (it predated the web UI) and adds
COMP-009 and COMP-010; the containers diagram goes from one container to three;
the context diagram's system description and relations include the admin panel.

**Suite: 3,681 passed** — diagrams only (AC-7). Validator unchanged: the one
known false positive (CARD-071).

### AC-3 — every edge, with the code behind it

| Edge | Evidence |
|---|---|
| admin → orchestrator | `admin/app.py:252` `orchestrator.generate(request)`; `admin/batch_generator.py:434` `orchestrator.generate_batch(` |
| admin → sourcing | `admin/app.py:2542` `ink_bounding_box, fit_crop_box`; `admin/image_manager.py:384` `derive_extent` |
| admin → clues | `admin/puzzle_review.py:13` `compute_clues` — the storage guard |
| admin → solver | `admin/puzzle_review.py` `solve` (storage guard); `admin/regrade.py:102` `solve` |
| admin → difficulty | `admin/regrade.py:350-351` `score_difficulty`, `classify` |
| admin → export | `admin/book_pdf_generator.py:209` `render_pages(` |
| admin → persistence | six admin modules import `nonogram.db`; nothing outside `admin/` does |
| admin → filesystem | `admin/app.py:1132` `file.save(...)`; read back at `:246`, `:1420` |
| admin → owner (PDF) | `admin/app.py:2265`/`:2278`, `:2409`/`:2426` — bytes, then `send_file` |
| web → orchestrator | `web/handler.py:52` `from nonogram import orchestrator`; `:797` `orchestrator.generate(` |
| cli → web | `cli.py:44` `from nonogram import …, web` |

Two hits from the first sweep were **not** accepted as evidence: the admin's
first `nonogram.orchestrator` import is only the constant `MAX_BATCH_COUNT`,
and the first `cli.py` match for "web" was its module docstring. Each edge was
redrawn from a real call or import rather than from whichever line grep found
first.

### One label I had wrong, caught before commit

I first labelled the admin's filesystem edge *"uploaded pictures in; book PDFs
out"*. Book PDFs are **never written to disk**: `generate_book_pdf` returns
bytes and `send_file` streams them to the browser. The edge now says it stores
and re-reads uploaded pictures, and a separate admin → owner edge carries the
PDF as a download. G-1 is about claims on an arrow as much as about the arrow.

### Two edges deliberately not drawn

- **No admin → tool container edge.** The admin panel imports the same
  generation package into *its own* process; it never calls the other
  container. An arrow would claim an inter-process call that does not exist.
  Recorded as a comment beside the relations so the absence reads as a decision.
- **No COMP-010 → anything.** Persistence is a leaf; the database engine is
  infrastructure, carried in the container diagram as a `ContainerDb`.

### AC-4 — the direct admin → clues/solver edges, defended in the diagram

The dependency-rule comment already said capabilities never call each other and
"every cross-capability hand-off goes through COMP-002". It now adds that the
admin is an *adapter*, so its direct arrows into COMP-004 and COMP-005 are legal
and deliberate — ADR-0032/R1's storage guard — and that routing them through
the orchestrator would erase the guarantee. Without that, the obvious tidy-up
is the wrong one.

### Step 3 — Postgres is not an external system

`external_systems.yml` stays `[]`. The database is the system's own store,
owned and migrated by this repository, so it is a `ContainerDb` inside the
boundary, not an `EXT-XXX` beside it. `context.puml`'s header comment says so
where CARD-111 had left a "not yet shown" note.

### AC-6 — rendering, stated honestly

**PlantUML is not installed** (`java` is; no `plantuml` binary or jar), so
nothing was rendered and I am not claiming it was. In its place, a structural
check over all three files: every `Rel()` endpoint is a declared element,
braces balance, quotes pair, and each file is framed by `@startuml`/`@enduml`.
All three pass. The checker was then mutation-tested — a misspelt element name
and a dropped closing brace — and caught both, so its pass is not vacuous. A
real render remains worth doing once, by whoever has PlantUML to hand.

### Fixed in passing

The component diagram's 2026-09-12 DELTA note still said COMP-006's classifier
"takes (score, branch_nodes)". That was my own leftover from CARD-110's G-4
pass, which corrected the tier count but not the signature. ADR-0031 made it
the score alone.

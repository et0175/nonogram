# CARD-112: Draw the admin panel and its database into the C4 diagrams

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Skill:** business-analyst
**TDD:** false — diagrams only, no code, no model ids invented
**Branch:** card/112-c4-admin-containers
**Worktree:** —
**Source:** CARD-110's AC-3, deferred there because CON-003 forbade what the code already did; unblocked by CARD-111 (CON-017)
**Idea:** —
**Wave:** —
**Depends on:** CARD-110 (the ids), CARD-111 (the constraint) — both done
**Touches:** meta/architecture/c4/containers.puml, meta/architecture/c4/components-CTX-001.puml, meta/architecture/c4/context.puml (only if the decision below says so)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
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

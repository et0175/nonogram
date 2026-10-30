# How it works

The layered, per-aspect account of how this system actually works, for the people
who need the mechanism: architects, developers and operators. Generated from ground
truth — the C4 diagrams, the domain registries under
`meta/architecture/domain/`, `requirements.yml`, `trace.yml`, the ADRs, the kanban
cards' `## Worktree notes`, and above all **the real code**.

**Every statement here is traceable to a file and usually to a line.** Where the
code and a model artefact disagree, the code wins and the disagreement is written
down rather than smoothed over — see
[Where the model and the code disagree](#where-the-model-and-the-code-disagree).
Where something is genuinely unknowable from the source, it says "not determinable
from code" and why.

## The system, in one paragraph

A tool that generates **uniquely-solvable** black-and-white nonogram puzzles. It
sources a solution grid — drawn at random, taken from a built-in library, or
converted from an uploaded picture — derives the row and column clues by run-length
encoding, proves with a hand-rolled constraint-propagation solver that the clues
have exactly one solution (recovering automatically, within bounds, when they do
not), grades the puzzle by the depth of line reasoning it demanded, and writes it
out as PNG, SVG, JSON, CSV or a two-page PDF. A separately deployed admin panel
turns batches of those puzzles into print-ready books for Amazon KDP, and lets the
owner solve a stored one in the browser.

## L1 — context

### The actor

**ACT-001 Puzzle Creator** (`meta/architecture/domain/actors.yml`) — the single
human actor, `type: human`. The developer/user who chooses mode, size, density and
difficulty tier, triggers export, reviews and curates batches, assembles books, and
plays stored puzzles. `actors.yml:14` is explicit that the extra surfaces added no
second actor: "**Not a second actor: one person, one role, two surfaces.**"

**ACT-002 System**, `type: system` — the tool's own automation (the solver, the
scorer, the regenerate/resample/pixel-nudge recovery loops), modelled as an actor
because it issues commands in reaction to POL-001..POL-005 rather than to human
input. `c4/context.puml` deliberately does **not** draw it: it is the same local
process, so "it appears as internal components at L3."

### External systems

`meta/architecture/domain/external_systems.yml` is `external_systems: []`, and
that is still correct. Three things that look like external systems are not:

- the **local filesystem** — drawn in the C4 views "as a boundary element for
  readability only … it is infrastructure, NOT an EXT-XXX";
- the **admin database** — "the system's own store, owned and migrated by this
  repository, so it is a `ContainerDb` inside the boundary";
- **Amazon KDP** — a print specification the book PDF meets (CON-018), not an
  integration.

So there is no broker, no gateway, no anti-corruption layer and no network
dependency anywhere in this system.

## L2 — containers

Three containers, one bounded context (`c4/containers.puml`):

| Container | Technology | What it is |
|---|---|---|
| **Puzzle Creation Tool** | Python 3.14 package (Pillow, NumPy) | the whole generation pipeline in one local process, with **two** first-class inbound adapters in it (CON-007): the `nonogram` console entry point, and a loopback-only web UI launched by `nonogram serve`. Keeps no state beyond the files it exports (CON-017). |
| **Admin Panel** | Python, Flask, behind gunicorn on Render | a separate process with its own entry point: batch generation through the same pipeline, review and curation, re-grading, and book assembly. Loopback-only by default; one credentialed door when `ADMIN_ALLOWED_HOST` is set (ADR-0030). |
| **Admin Database** | PostgreSQL via SQLAlchemy + Alembic | batches, puzzles and books — the only persistent state in the system. Reached by the admin panel alone. |

`containers.puml` carries a deliberate *absence* worth knowing: there is **no
relationship between the admin panel and the generation tool**, because "the admin
panel imports the same generation package into its OWN process; it never calls the
other container. An arrow here would claim an inter-process call that does not
exist."

## L3 — aspects

| Group | Aspect | Context |
|---|---|---|
| [01-domain](01-domain/) | [puzzle-creation](01-domain/puzzle-creation/) | **CTX-001 Puzzle Creation** |

One group and one aspect, because the system has one bounded context. The
[group README](01-domain/README.md) records why `integrations`, `surface-api` and
`operations` would each have been empty or duplicative, rather than creating them
hollow.

## Reading routes

### 🏛 Architect

1. [perspectives/architect.md](01-domain/puzzle-creation/perspectives/architect.md)
   — the single-context decision and how it was reached, the closed decisions
   (ADR-0006's dependency baseline, ADR-0007's direction, ADR-0033's placement of
   Book) and the guard behind each, plus the model drift you own.
2. [01 — the layered pipeline](01-domain/puzzle-creation/01-the-layered-pipeline.md)
   — the rank lattice and the `ast` walk.
3. [04 — uniqueness and recovery](01-domain/puzzle-creation/04-uniqueness-and-recovery.md)
   — CON-005, the one mandatory constraint, and the oracle that proves it.
4. [10 — persistence and the unmodelled edges](01-domain/puzzle-creation/10-persistence-and-the-unmodelled-edges.md)
   — what the model does not draw, and how much of the tree that is.

### 💻 Developer

1. [perspectives/developer.md](01-domain/puzzle-creation/perspectives/developer.md)
   — the four guards that will fail your build, the boundary contracts, the error
   semantics per adapter, and every extension point with the two-edit shapes.
2. [01 — the layered pipeline](01-domain/puzzle-creation/01-the-layered-pipeline.md),
   then whichever of
   [02](01-domain/puzzle-creation/02-sourcing-a-solution-grid.md) ·
   [03](01-domain/puzzle-creation/03-deriving-clues.md) ·
   [04](01-domain/puzzle-creation/04-uniqueness-and-recovery.md) ·
   [05](01-domain/puzzle-creation/05-difficulty-calibration.md) ·
   [06](01-domain/puzzle-creation/06-exporting-a-finished-puzzle.md) ·
   [07](01-domain/puzzle-creation/07-book-assembly-and-the-admin-panel.md) ·
   [09](01-domain/puzzle-creation/09-the-three-inbound-adapters.md) ·
   [11](01-domain/puzzle-creation/11-the-public-player.md) your change
   lands in.
3. The [doc → code map](01-domain/puzzle-creation/README.md#doc--code-map) when you
   need to find a file by what it does.

### 🔧 SRE / operator

1. [perspectives/sre.md](01-domain/puzzle-creation/perspectives/sre.md) — the one
   deployed service, the timeout chain derived from its constants, every bound with
   its constant, the failure modes, and the capacity figures the project measured.
   The public player is a second deployed *surface* and deliberately not a second
   service: [11](01-domain/puzzle-creation/11-the-public-player.md) and
   `docs/deploy/player.md`.
2. [09 — the three inbound adapters](01-domain/puzzle-creation/09-the-three-inbound-adapters.md)
   — the credentialed door, and the three disagreeing ways the admin socket can be
   opened.
3. [10 — persistence](01-domain/puzzle-creation/10-persistence-and-the-unmodelled-edges.md)
   — engine selection, the dual-mode fallback, and the three unread tables.

### 👤 ACT-001 Puzzle Creator

[perspectives/puzzle-creator.md](01-domain/puzzle-creation/perspectives/puzzle-creator.md)
— written for engineers reasoning about this actor's touchpoints internally, not as
a task guide. The four surfaces, what `GenerationRequest` encodes about intent, and
the rules that actually bound what the actor can ask for.

## How this documentation was derived, and from what

This matters because a later reader needs to know which parts rest on a **registry**
and which on a **diagram** — the two are not equally current here.

| Level | Derived from |
|---|---|
| L1 — context | `meta/architecture/domain/actors.yml`, `external_systems.yml`, `c4/context.puml` |
| L2 — containers | `c4/containers.puml`, `meta/architecture/platform.yml` |
| L3 — aspects | `domain/contexts.yml` (CTX-001), `domain/capabilities.yml` (CAP-001..CAP-007), `c4/components-CTX-001.puml` (COMP-001..COMP-010; COMP-011 is in `trace.yml` and not yet in the diagram) |
| L4 — mechanism | **the real code** under `src/nonogram/`, plus the test tree where a test *is* the mechanism, with `trace.yml:2356` giving each component's code glob |

All four domain registries exist and are current enough to derive from — they live
under **`meta/architecture/domain/`** rather than directly under
`meta/architecture/`:

```
meta/architecture/domain/actors.yml            ACT-001, ACT-002
meta/architecture/domain/external_systems.yml  []
meta/architecture/domain/contexts.yml          CTX-001, context_map: []
meta/architecture/domain/capabilities.yml      CAP-001..CAP-007
meta/architecture/domain/aggregates.yml        AGG-001, AGG-002
meta/architecture/domain/commands.yml  events.yml  policies.yml
```

Two configuration facts shaped the structure, and both are defaults rather than
choices:

- **There is no `meta/.skills.yml`** in this repository, so there is no
  `explain.*` configuration. The path (`docs/how-it-works/`), the group set and the
  technical role triple (`architect` / `developer` / `sre`) are the skill's
  documented defaults.
- **The actor-role perspective is derived, not assumed.** `actors.yml` carries one
  `type: human` actor, so there is one actor perspective
  (`puzzle-creator.md`). ACT-002 is `type: system` and gets none.

Honest gaps in the model itself, which these docs work around rather than hide:

- `c4/components-CTX-001.puml` claims to carry "the complete inventory for this
  model", and it does not: **CAP-007 (Puzzle play) is in `capabilities.yml` and
  `contexts.yml` but has no component line**, and `src/nonogram/analysis/` has no
  COMP id in `trace.yml` and no box in any diagram. The capability-to-component
  mapping in this documentation therefore comes from `capabilities.yml` +
  `trace.yml` + the code, with the puml used for structure and the *reasons* it
  records.
- **There is no `forge:docs` role folder** (`docs/` has no `role/` directory), so
  the actor perspective links to no task guide. It is written as mechanism and
  constraints throughout, which is the boundary the skill draws, and names the
  nearest hand-written end-user material instead.

## Where the model and the code disagree

Six places, all verified on both sides. **The code is the authority in every one**;
these are the deltas the model owes.

| # | Model says | Code says |
|---|---|---|
| 1 | `c4/components-CTX-001.puml:87` — COMP-003 sources "at a configured size **10x10..50x50**" | `limits.py:16` — `MIN_SIZE = 10`, `MAX_SIZE = 30`, **per side**; ADR-0022 narrowed the ceiling, and `orchestrator.py:327` notes the same narrowing against its own constant. Independently corroborated by `admin/book_plan.py:118`, where the four longest-side buckets partition 10..30 exactly and a 50-cell side would have no bucket. |
| 2 | `c4/components-CTX-001.puml:95` — COMP-005's ladder is **four** rungs, `simple_overlap < line_dp < cross_line < probe_contradiction` | `solver/propagate.py:148` — **three**. `:141` records `cross_line` as removed for good in the 2026-09-12 ADR-0029 revision, because it "made a puzzle grade differently from its own transpose"; the first cut graded **92% of line-solvable grids** differently (`:645`). The string `cross_line` appears nowhere in `src/`. |
| 3 | `c4/components-CTX-001.puml` COMP-010 — the store holds "batches, puzzles, books **and generation history**", and `users` + `user_selected_books` are the two tables nothing touches | `db/models.py` + `migrations/versions/001` — **`generation_history` is a third orphan.** It has a model and a table and no reader or writer anywhere in `src/`, `scripts/` or migrations 002–016. Its only appearance in the tests is as a fixture *proving* nothing writes it (`tests/test_puzzle_solver_page.py:1298`). Live contents: three tables. Unread: three. |
| 4 | `capabilities.yml` CAP-001 — sourcing is "reachable through either inbound adapter … since both invoke the same CMD-001/CMD-002/CMD-003" | `web/pages.py:441` — the shipped form offers **image mode only** since CARD-032, and the gap is pinned as two exact set equalities (`tests/test_web_server.py:1995`). CMD-001 and CMD-002 are reachable through COMP-008 only by a hand-written body. |
| 5 | `c4/components-CTX-001.puml` — COMP-008 keeps "no state beyond the export files (CON-017)"; same claim at `web/__init__.py:73` | `web/uploads.py:59` — a module-level, process-lifetime `OrderedDict` of retention tokens bounded at `MAX_RETAINED = 8`; `web/multipart.py:104` writes uploads via `tempfile.mkstemp`, outside `--out`; two routes read files back off disk. The spirit survives, the sentence does not — and nothing clears the store on Ctrl-C. |
| 6 | ADR-0020's Decision text — "a hand-written router over (method, path), the form page served as a static HTML string constant, urlencoded bodies … and, for the image-upload path specifically, multipart/form-data parsed by hand" | `web/handler.py:578` serves `GET /static/<file>` from disk, and `web/static/metadata.js` (380 lines) plus the inline `<script>` at `pages.py:452` are shipped client-side JavaScript. **Not** a CON-008 violation — CON-008 forbids previewing the *generated puzzle*, while `metadata.js` previews the *uploaded source* — but the ADR is behind the code. |

### `CLAUDE.md`'s remaining stale claims

`CLAUDE.md`'s component map was corrected for COMP-006 and COMP-007 by commit
`9c4e851a` ("COMP-006 and COMP-007 are built, not 'not yet built'"), so those two
rows are current. Six claims are not:

1. **`:45`** — "`cli.py  COMP-001  the **only** inbound adapter". There are three
   (`tests/test_cli.py:747`, asserted at `:914`), and `cli.py:3` says so itself.
2. **`:47`** — "`sourcing/ … (random implemented; **library/image are future
   work**)". Both ship: `library.py` is 415 lines with four registered templates,
   `image.py` is 1,251 lines.
3. **`:44`-`:52`** — the map omits COMP-008 `web/`, COMP-009 `admin/`, COMP-010
   `db/` and `analysis/` entirely: **29,225 of the package's 46,127 lines**, 63%,
   re-derived with `wc -l` (`web/` 2,835 + `admin/` 25,181 + `db/` 726 +
   `analysis/` 483).
4. **`:56`** — cites "`sourcing/random_grid.py`'s `validate_size`/
   `validate_density`". **There is no `validate_size`.** The public validator is
   `validate_extent`, and `random_grid.py:118` explains that a public one-integer
   validator is deliberately refused: "a *public* one-integer validator would be a
   supported way to keep reasoning about a grid as one number, and half an extent
   is not a thing the model validates" (ADR-0022/R1). Three test docstrings still
   name the old symbol too.
5. **`:58`** — "exactly stdlib + Pillow + NumPy as runtime dependencies (plus
   `pytest` as a dev-only extra)". The first half is exactly right
   (`pyproject.toml:23`). The parenthesis is not: `dev` is
   `["pytest>=8.3", "pytest-playwright>=0.7"]`, and there are **two further
   extras** — `admin = [Flask, Werkzeug, reportlab, gunicorn]` and
   `db = [SQLAlchemy, alembic, psycopg2-binary]`. `pyproject.toml:42` has the
   correct wording: "ADR-0006/R1's baseline is `project.dependencies` above, which
   stays exactly Pillow + NumPy — **the extras have always been outside it**."
6. **`:60`** — two claims. "a cooperative timeout (hook points already present …,
   **not yet enforced**)" — it **is** enforced: `orchestrator.py:1793` fixes one
   absolute instant per request, `propagate.py:983`/`:1129` and
   `search.py:1180`/`:1259` check it, and `propagate.py:221` raises `SolverTimeout`.
   The admin panel's storage guard depends on that enforcement. And "random
   mid-density grids at **40×40+**" names a size `limits.py` cannot produce.

Minor, same file: **`:40`** opens "This is a CLI tool that generates…", which
does not mention the deployed Flask panel on Postgres that is the product's actual
delivery vehicle.

`CLAUDE.md` is not edited by this documentation.

## Not determinable from code

These are written as unknowns in the files that would otherwise have had to guess.

| Unknown | Why | Where it matters |
|---|---|---|
| **What production actually runs** — start command, build command, Python version, whether `alembic upgrade head` runs on deploy, the env-var set | `render.yaml` declares itself non-authoritative on its own first line; `docs/deploy/render.md` marks each field `TODO(owner)`. Its one evidence line records that **as last observed on 2026-09-23 production ran Flask's dev server on `src.nonogram.admin.app`** — the `Procfile` shape, not `start.sh`. The Python version is a third answer again: `pyproject.toml:9` requires `>=3.14`, `runtime.txt` says `3.11.11`, `render.yaml` pins 3.11. | [09](01-domain/puzzle-creation/09-the-three-inbound-adapters.md), [sre](01-domain/puzzle-creation/perspectives/sre.md) |
| **Whether `users`, `user_selected_books` and `generation_history` hold rows** | Code-wise unreachable; answering needs the live database, which these docs were written without touching. The component diagram calls the disposition "CARD-111 option B, undecided". | [10](01-domain/puzzle-creation/10-persistence-and-the-unmodelled-edges.md) |
| **Whether any stored puzzle still carries `difficulty_tier = 'guess'`** | Retired by ADR-0031; `db/models.py:69`'s comment still lists it. The readers would treat it as "no recognisable tier" and `book_plan.selection_cells` would drop the row from every plan bucket, so it would silently belong nowhere. | [07](01-domain/puzzle-creation/07-book-assembly-and-the-admin-panel.md), [10](01-domain/puzzle-creation/10-persistence-and-the-unmodelled-edges.md) |
| **Whether `admin/pdf_generator.py`, `admin/book_membership.py` and `web/metadata.py` are retained deliberately or simply unremoved** | All three are reachable only from tests. Cards record the deletion of their *call sites* but state no intent for the modules themselves. (By contrast, `analysis/strategy_counter.py`'s retention **is** recorded, at `src/nonogram/__init__.py:35`.) | [09](01-domain/puzzle-creation/09-the-three-inbound-adapters.md), [10](01-domain/puzzle-creation/10-persistence-and-the-unmodelled-edges.md) |
| **Whether `web/handler.py:354`'s absolute-form-authority arm is reachable on this interpreter** | The docstring says not, by its own reading of the stdlib — "`http.server`'s own `parse_request` collapses a leading `//` to `/` before `do_GET` is called" — and labels it defensive. Verifying would mean running code. | [09](01-domain/puzzle-creation/09-the-three-inbound-adapters.md) |

## Keeping this current

Per the skill: when a card ships code, the affected aspect's L4 narrative,
diagrams, doc→code map and **every one of its perspective files** are regenerated
by re-reading the current source in the same pass. When the model changes, the
L1–L3 structure and the navigation are rebuilt. When `actors.yml` gains or loses a
human actor, every aspect's actor perspectives are recomputed.

Nothing here is a draft and nothing is marked for a human to fill in. If a
statement in these files no longer matches the code, the file is stale and should be
regenerated — not patched in place.

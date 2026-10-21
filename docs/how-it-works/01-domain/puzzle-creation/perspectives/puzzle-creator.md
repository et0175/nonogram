# Puzzle Creation (CTX-001) — ACT-001 Puzzle Creator's perspective

> **This is not a how-to guide.** It is the internal account of what the one human
> actor's touchpoints *are*, mechanically, and what actually bounds them — written
> for whoever is building or operating those touchpoints. There is no
> `forge:docs` role folder in this repository to link to (`docs/` has no `role/`
> directory), so nothing here defers to one; if one is created, the
> task-oriented content belongs there and this file should link to it instead of
> growing.

## Why this matters to `ACT-001`

`meta/architecture/domain/actors.yml` carries **one** human actor and it is this
one. Everything the system does is for them, and — more consequentially for anyone
reasoning about the design — almost every simplification in this codebase is paid
for by that fact.

`actors.yml:14` is explicit that the single actor is the whole story across every
surface:

> NOTE 2026-09-22 (book generator delta): the same human also assembles books in
> the admin panel (US-023..US-027, CMD-015..CMD-019, CMD-021) … **Not a second
> actor: one person, one role, two surfaces.**
>
> NOTE 2026-10-03 (puzzle player delta): the same human also solves stored puzzles
> on the admin panel's puzzle player (US-028, FR-044). **No command: playing
> changes no system state** (marks are browser-local, CON-021), so it adds neither
> an actor nor a CMD.

The second actor in the registry, ACT-002 "System", is `type: system` — the tool's
own automation (solver, scorer, recovery loops) modelled as an actor because it
issues commands in reaction to POL-001..POL-005 that the human does not. It is the
*same local process*, so `c4/context.puml` deliberately does not draw it: "it
appears as internal components at L3."

## Description

ACT-001 reaches CTX-001 through **four** touchpoints, and they are not equivalent:

| Touchpoint | What it is | Reaches |
|---|---|---|
| `nonogram generate …` | COMP-001, argv | all three sourcing modes, all five export formats |
| `nonogram serve` → the form | COMP-008, loopback browser | **image mode only** since CARD-032 |
| the admin panel | COMP-009, Flask, its own process | batches, review, curation, re-grade, books |
| the puzzle player | one admin route | reads one stored puzzle; writes nothing |

The asymmetry between the first two is real and pinned, not accidental.
`capabilities.yml` CAP-001 says sourcing is "reachable through either inbound
adapter … since both invoke the same CMD-001/CMD-002/CMD-003 commands via the
adapter-agnostic `GenerationRequest`". **The shipped form offers one mode.**
CARD-032 removed the source dropdown and the mode-specific fields
(`web/pages.py:441`), and the gap is held as two exact set equalities against the
CLI's own parser (`tests/test_web_server.py:1995`) rather than described in prose:

```python
assert argv_options - form_options == {"extent", "mode", "density", "library_key"}
assert form_options - argv_options == {"size"}
```

The urlencoded path still accepts all three modes, so CMD-001 and CMD-002 remain
reachable through COMP-008 by a hand-written request body — never from the form the
actor actually sees.

## Examples

**What one request from this actor is, as a data structure.**
`orchestrator.GenerationRequest` (`:349`) is the CLI/domain boundary type, and its
docstring is where "the actor's intent" is defined in code:

> This is the CLI/domain boundary type: the adapter fills it straight from the
> parsed argv and hands it inward. Its fields are therefore *syntactically* typed
> and widely optional on purpose … **Nothing here has been checked against a
> domain rule yet.**

Three of its fields encode distinctions about this actor's intent that the system
takes care not to flatten:

- `name=None` means "`--name` was not given", which selects the auto-generated
  name; `name=""` is a *given* name that is empty, and earns `InvalidPuzzleName`
  (AC-045). The two are not the same thing (`:402`).
- `difficulty=None` means "no tier requested", which makes POL-004's check
  **vacuous rather than absent** — every candidate is still scored and the first
  unique one is accepted. It is *not* "Easy" (`:409`).
- `width=25, height=None` is a bare `--size 25`: one number stated, the shape left
  for the domain to derive from the source, because "an unstated dimension is not a
  user intent, and 'assume square' is a claim about the picture that the CLI is the
  component least equipped to make" (`:370`).

**What the actor is told back, and why.** Reporting is a short, deliberate list
(`cli._run_generate`, `:405`):

- `seed: <n>` — printed **only** when the actor did not choose one, because
  ADR-0015 requires the auto-drawn seed be echoed: "otherwise a reproducible run
  has nowhere to be read from until the export file is opened."
- `wrote <path>` per file written.
- the FR-014 nudge line, printed **only when nonzero** — "zero nudges prints
  nothing at all (AC-041)", so the line's *absence* is the signal. The count is
  read straight off the aggregate and never recomputed.
- on failure: one line to stderr in one format, `nonogram: error: <message>`, from
  the single `_report` function that exists so the two reporting sites "cannot
  drift into two different-looking messages."

**Where the system refuses, and what it tells the actor to do about it.** The
refusals are worded as remedies, which is why they are worth reading as part of the
actor's surface rather than as error strings. The sharpest example is
`SizeTooSmallForSource` (`random_grid.py:347`):

> Ask for `--size {smallest}` or larger — **counter-intuitively, a LARGER puzzle
> accepts a picture that a smaller one refuses**, because its shorter side has
> further to fall before it reaches the 10-cell floor. Cropping the picture is not
> what fixes this; a different `--size` is, or stating both sides yourself as
> `--size WxH`.

And POL-001's abandonment (`orchestrator.py:1447`): "no candidate grid had exactly
one solution; try a different `--size`/`--density` combination, or another
`--seed`" — the levers that change the answer, named.

**The one thing done to the actor's own picture, and its bound.** POL-002's pixel
nudge alters up to `MAX_NUDGE_ATTEMPTS = 5` cells of an uploaded image's
conversion. `orchestrator.py:249` is explicit that this bound is a judgement about
the *actor*, not about cost, and that chaining it to the retry bound would be
wrong:

> The 30 above and the 5 here are two independent judgements from the same ADR
> about two different things — how many *fresh* candidates it is worth drawing
> before a request is called infeasible, versus **how much of the user's own
> picture it is acceptable to alter behind their back**. Chaining them would say
> the two move together, and they do not: a retune of the retry bound must not
> silently license twenty edits to an uploaded photograph.

The reveal policy (CARD-214) is the same instinct taken further: it changes *no*
cell and instead reveals up to 5% of the answer, and `MAX_GIVEN_CELL_SHARE_PERCENT`'s
comment frames it the same way — "not 'how long may we keep trying' but **how much
of the user's own puzzle may this tool give away behind their back**"
(`orchestrator.py:266`). It is off by default, and tried last.

**Owner decisions that are in the code as decisions.** Several constants record
that this actor chose them, with a date, which is why they cannot be retuned as
pure engineering:

- `MEDIUM_MAX_SCORE = 90.0` — "on the owner's decision of 2026-09-23 (CARD-137)"
  (`difficulty.py:212`).
- `DEFAULT_BINARISATION = None` — "**Flipped to `None` on 2026-09-17**, by the
  owner, after that gate: 25 pictures rendered both ways at 25×25" and "pinned
  rather than defaulted, because a binarisation change alters every converted
  picture and **the owner validates image work by eye, not by test**"
  (`image.py:291`).
- `MAX_BATCH_COUNT = 50` — "Down from 200 (CARD-088, **at the owner's
  proposal**)" (`orchestrator.py:315`).
- `_largest_remainder(..., ties_to_later=True)` — the plan's rounding breaks ties
  toward the *harder* tier, "owner's choice 2026-09-22" (`book_plan.py:259`).
- `book_proof.py`'s two pages exist to be printed at 100% and measured with a
  ruler: "the strokes ADR-0037 fixes are final only once that has happened"
  (`app.py:5535`).

## The business rules and limits that actually bound this actor

**What they may ask for.**

| | Limit | Where refused |
|---|---|---|
| grid side | 10..30 cells inclusive, **per side** — a 30×12 is as legal as a 12×12 | `random_grid.validate_extent` → `SizeOutOfRange` |
| bare `--size N` | the source may be no more elongated than N/5 : 1 | `derive_extent` → `SizeTooSmallForSource` |
| density | 1..99 percent — both degenerate ends refused (ADR-0027) | `validate_density` → `InvalidDensity` |
| library key | `cat`, `heart`, `house`, `moon` | `template_for` → `UnknownLibraryImage` |
| uploaded picture | must decode, and its ink box must be within 2× of the grid's aspect ratio | `load_greyscale` → `UnreadableImage`; `validate_aspect_ratio` → `ImageNeedsManualCrop` |
| difficulty tier | `easy`, `medium`, `hard` | `parse_tier` → `UnsupportedDifficulty` |
| name | not empty, not whitespace-only | `NameContext.name_for` → `InvalidPuzzleName` |
| export format | `json`, `png`, `svg`, `csv`, `pdf` | argparse `choices`, from the registry |
| batch size | 1..50 | `MAX_BATCH_COUNT` |

**What the system will not do for them, by decision.**

- **A requested tier is not a construction target** (CON-004). POL-004 *discards*
  candidates that classified elsewhere; it does not steer sourcing toward a tier
  (`orchestrator.py:26`, `difficulty.py:272`). Asking for Easy makes the pipeline
  throw work away, not make easier grids.
- **The difficulty bands are heuristic**, not a promise about how the puzzle will
  feel.
- **A puzzle that is not provably unique is never exported and never stored.**
  INV-002 gates export; the admin panel's storage guard re-derives the clues and
  asks the solver itself rather than trusting whoever called it (ADR-0032/R1). An
  unproven grid is refused exactly as a disproven one is — `errors.py:143`: "no
  caller has a different thing to do about them."
- **An existing export is never overwritten.** ADR-0017 auto-suffixes `-1`, `-2`,
  …, "so two runs of the same mode in the same minute would otherwise silently
  destroy the first run's artifact."
- **A puzzle inside a book is never modified.** Books reference puzzles by id
  (ADR-0033/R1). A re-grade that would move a *booked* puzzle into another tier is
  refused (INV-009, 409).
- **A published book's membership cannot be changed without confirming it**
  (INV-008, 409), and any membership change after draft returns the book to draft
  so it faces the readiness gate again (INV-012).
- **A book may only leave draft when its mix matches its plan**, within
  `READY_TOLERANCE_POINTS = 3` inclusive — and the refusal names *every* offending
  cell at once (AC-221), not the first.
- **A below-floor puzzle needs an explicit per-puzzle override** to enter a book
  (INV-006, the 4.75 mm floor).
- **Nothing about a play session is kept.** CON-021: marks are browser-local, and
  since the 2026-10-06 amendment `localStorage` in *that* browser only. Nothing
  server-side, for anyone.
- **The actor's own files are read, never modified in place.** Image mode reads the
  picture; the nudge alters the *conversion*, not the file.

**What is theirs alone.** The naming context
(`NameContext`, `orchestrator.py:439`) is ADR-0018's "current run", and
`DEFAULT_NAMES` is one instance per process — "which for the single-user,
single-process CLI of CON-001 means 'the names this invocation has handed out' —
one, normally." An explicitly given name is **never** counter-suffixed: "it is the
user's word for the puzzle, and AC-044 asks for it back verbatim." Only
auto-generated same-minute names get `-1`, `-2`.

**Access, and the one place it widens.** All three surfaces are loopback by
default. The admin panel gains exactly one credentialed door when
`ADMIN_ALLOWED_HOST` is set (CON-015, CON-016, ADR-0030), and that door *replaces*
the loopback rule rather than adding to it — so `Host: localhost` is refused in
deployed mode even with the correct credential, because behind a reverse proxy it
would otherwise be a password bypass. The deployed panel also removes the re-grade
entirely (`REGRADE_ENABLED = not remote_host`), because it "rewrites every stored
grade with no undo." Mechanism in
[09 — the three inbound adapters](../09-the-three-inbound-adapters.md).

## Related docs

- Narrative: [02 — sourcing a solution grid](../02-sourcing-a-solution-grid.md) · [05 — difficulty calibration](../05-difficulty-calibration.md) · [06 — exporting a finished puzzle](../06-exporting-a-finished-puzzle.md) · [07 — book assembly](../07-book-assembly-and-the-admin-panel.md) · [08 — playing a stored puzzle](../08-playing-a-stored-puzzle.md) · [09 — the three inbound adapters](../09-the-three-inbound-adapters.md)
- Siblings: [architect](architect.md) · [developer](developer.md) · [sre](sre.md)
- Model: `meta/architecture/domain/actors.yml` (ACT-001, ACT-002) · `meta/business/vision.md` · `meta/business/stories.md` (US-001..US-028)
- **No matching `forge:docs` task guide exists.** The nearest end-user material in
  the repo is `docs/guides/how-to-solve-nonograms.md`, `ADMIN_SETUP.md` and
  `docs/BOOK_WORKFLOW_UA.md`; none of them is a generated role doc, and this
  perspective deliberately does not duplicate their steps.

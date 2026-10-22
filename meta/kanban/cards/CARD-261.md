# CARD-261: Both component maps drift silently; hold them to the package the import walk already enumerates

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/261-control-the-component-map
**Worktree:** ../PythonProject4-card-261
**Source:** found 2026-10-22 while establishing what `forge:explain` could ground its L4 narrative on. Two of the five defects were corrected directly in `9c4e851a` (CLAUDE.md's two "not yet built" rows); the owner carded the rest rather than take a wider edit to the project's instruction file outside a card.
**Idea:** —
**Wave:** 53
**Depends on:** —
**Touches:** CLAUDE.md, src/nonogram/__init__.py, tests/test_cli.py
**Review score:** 7.5 (c1) → 7.8 (c2) → fix 2 `335c641e` → **cycle 3 (final, max_cycles 3)**
**Started:** 2026-10-22T08:08:13Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why — the map is read by every agent brief, and nothing reds when it lies

`CLAUDE.md` is loaded as project instructions in **every** session, and step 7a of the kanban
`start` procedure extracts its sections into **every implementation agent's brief**. Its package
layout block is therefore the most-read description of this system, and it names
`src/nonogram/__init__.py`'s docstring as "the canonical map". **Neither map has a control.** No test
under `tests/` reads `CLAUDE.md` at all — verified, the only occurrences are prose mentions.

**Measured 2026-10-22 against the code on disk — the first two were corrected directly in `9c4e851a`, the rest are this card's:**

| where | claim | reality |
|---|---|---|
| `CLAUDE.md:50` | `difficulty.py COMP-006 not yet built` | **fixed in `9c4e851a`** — 28 KB, 2 test files |
| `CLAUDE.md:51` | `export/ COMP-007 not yet built` | **fixed in `9c4e851a`** — 6 renderers, 5 test files |
| `CLAUDE.md:45` | `cli.py COMP-001 the only inbound adapter` | **three** adapters: COMP-001, COMP-008 `web/`, COMP-009 `admin/` |
| `CLAUDE.md:47` | `sourcing/ … random implemented; library/image are future work` | `sourcing/` holds `library.py`, `image.py`, `random_grid.py`, `templates/` |
| `CLAUDE.md:45-51` | the block lists seven components | **COMP-008, COMP-009, COMP-010 and `analysis/` are absent** — `web/`, `admin/`, `db/`, `analysis/`, re-derived with `wc -l` as **29,225 of 46,127 lines, 63%** of the package |
| `CLAUDE.md:56` | cites `sourcing/random_grid.py`'s **`validate_size`**/`validate_density` | **`validate_size` does not exist in `src/`.** The public validator is `validate_extent`; `random_grid.py:118` records that a one-integer public validator is *deliberately refused* under ADR-0022/R1 — "half an extent is not a thing the model validates". Three test docstrings still name the dead symbol |
| `CLAUDE.md:58` | "stdlib + Pillow + NumPy … plus **`pytest` as a dev-only extra**" | first half exactly right (`pyproject.toml:23`); the parenthesis is not — `dev` also carries `pytest-playwright`, and there are **two further extras**, `admin` (Flask, Werkzeug, reportlab, gunicorn) and `db` (SQLAlchemy, alembic, psycopg2-binary). `pyproject.toml:42` already has the correct wording |
| `CLAUDE.md:60` | "a cooperative timeout (hook points already present …, **not yet enforced**)" | **it is fully enforced** — `orchestrator.py:1793` fixes one `time.monotonic` deadline per request and passes it to the single `solver.solve` call at `:1859`; checked at every propagation fixed point (`propagate.py:983`, `:1129`) and every branch node (`search.py:1180`, `:1259`); `propagate.py:221` raises `SolverTimeout`, and the admin storage guard depends on it |
| `CLAUDE.md:60` | "random mid-density grids at **40×40+**" | `limits.py` caps a side at **30**, so that size cannot be produced |
| `src/nonogram/__init__.py:10-14` | COMP-003..COMP-007 each annotated `(later card)` | all five shipped |

So roughly half the shipped system is missing from the layout a new session reads first, and the file
CLAUDE.md defers to as canonical is stale in the same direction. **The two "not yet built" rows had
been misinforming briefs from 2026-09-08 to 2026-10-22 — about six weeks** — a card asking whether it could use the difficulty scorer was
reading that it did not exist.

**This is ADR-0039/R1's family, not a typo.** The map makes a claim about the code; the claim has no
control that can fail; it drifted. Correcting the text alone leaves the mechanism that produced the
drift exactly as it was, and this board has the measurement to show that is not enough — CARD-257 cut
prose with no control and its review found the same shape one file over, which became CARD-259, whose
own review found it one file over again.

## What to implement

1. **Correct both maps** to the shipped system: CLAUDE.md's three remaining defects (the "only inbound
   adapter" clause, the "future work" clause, and the three missing rows), and `__init__.py`'s five
   `(later card)` annotations. One statement per fact — do not restate a component's role in both
   files; CLAUDE.md already names `__init__.py` as canonical, so the terse map belongs there and
   CLAUDE.md's block should point at it rather than duplicate it. (CARD-257's and CARD-259's lesson:
   two copies of one statement is the defect, not the tidiness problem.)
2. **Give the row set a control, by extending the walk that already exists.** `tests/test_cli.py`
   already enumerates the package for its layering guard — `test_the_import_walk_actually_sees_the_package`
   (`:892`) is itself the control for that walk's reach, and `test_every_import_in_the_package_points_inward`
   (`:949`) consumes the enumeration. **Extend that enumeration into a map control; do not write a
   second walk.** The authority the runtime can enumerate is the package's own modules, which is what
   ADR-0039/R2 asks for.
3. **Default-deny, both directions.** A component module present in the package and absent from a map
   is a **FAILURE**; a row naming a module that does not exist is a **FAILURE**. A shape the control
   cannot analyse is a failure too, never a silent pass.

## Acceptance criteria

- **AC-1** *Given* the corrected maps, *then* every module the import walk enumerates as a component
  appears in the canonical map exactly **once**, and every row of the canonical map names a module
  that exists. (test: `TestComponentMap_EveryComponentIsListedExactlyOnce`)
- **AC-2** *Given* a **planted** component module added to the package and listed in neither map,
  *then* the control reds **naming that module**; removed, the control passes. And symmetrically: a
  **planted row** naming a module that does not exist reds, naming the row. Both states demonstrated,
  not reasoned about — a derivation whose plant does not red is the defect this criterion exists to
  prevent. (test: `TestComponentMap_APlantedModuleAndAPlantedRowBothRed`)
- **AC-3** *Given* CLAUDE.md, *then* its layout block carries no component row of its own — it points
  at `src/nonogram/__init__.py` — so there is exactly one place a row can drift from. If the owner
  prefers to keep a copy in CLAUDE.md, then that copy is held to the canonical one by the same control
  and the AC is met that way instead; **state which of the two shapes shipped and why.** (test:
  `TestComponentMap_ThereIsOneRowPerComponentAcrossBothFiles`)
- **AC-4** *Given* the extension, *then* `tests/test_cli.py`'s existing layering behaviour is
  unchanged: the same forbidden edges still red and the same legal ones still pass, demonstrated by
  re-running its existing edge-rejection parametrisation rather than asserting it.
- **AC-5** (guard) *Given* all edits, *then* no component's **description** is claimed to be
  controlled. The enumeration can hold the **row set**; it cannot judge whether "scores 0..100 from
  the solver's rung tags" is an accurate account of `difficulty.py`. Declare that bound explicitly in
  the control's docstring. An honest bound is required; a premise that hides the hole is the thing
  this board gates on.

## Guardrails

- G-1: **The layering guard's behaviour is unchanged.** This card extends what the walk's output is
  used for; it does not relax, retarget or delete any existing import rule or its controls.
- G-2: **No third copy of the map.** Not in `tests/README.md`, not in `docs/`, not in the new
  control's docstring. The control reads the maps; it does not restate them.
- G-3: No new runtime dependency (ADR-0006/R1); stdlib only.
- G-4: **CLAUDE.md's instruction content outside the layout block is untouched.** Commands, test style,
  the dependency-baseline paragraph and the boundary-types paragraph are not this card's to edit.
- G-5: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-6: ADR-0036/R4 — no codepoint in U+25A0..U+25FF, U+2022 or U+2219 in any `src/nonogram/**` string
  literal, docstrings included. This card edits `src/nonogram/__init__.py`'s docstring, so the rule is
  live: `pdf_generator.py`'s three U+2022 are the declared exemption and a clean-scan claim over the
  whole tree would be false.

## Architecture context

- **Components:** all of COMP-001..COMP-010 are named by the maps; the card changes none of them.
- **ADR:** ADR-0039/R1–R3 (a claim needs a control that can fail; the set is derived from an authority
  the runtime can enumerate and defaults to deny; an exemption carries a control for what it must not
  absorb). ADR-0006/R1 (closed dependency baseline). ADR-0036/R4 (no typed round marks).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card; it changes documentation and one
  test, no requirement's verifying test.

## System contract

_Derived at dispatch (2026-10-22) by `system_rules.py --card CARD-261 --root meta/architecture`
(`card_scope: touches`), curated under `meta/kanban/curation.md`: **projection 17 → kept 10, dropped
7**. A projection — fix the source artifact, never this list._

**Derivation:** keep every `check.kind: review-lens` rule (nothing executes them, so a reviewer is the
only enforcement), plus every `kind: test` rule belonging to an ADR whose text declares a reach limit —
the idiom *"reach, stated rather than implied"*, matched **in the ADR files and case-insensitively**,
because the lens output carries no comment text and ADR-0039 writes it in capitals. That selects
**ADR-0036, ADR-0037, ADR-0039**. The remaining 7 `kind: test` rules are dropped: the suite executes
them on every gate.

**Sanity check (curation.md's own):** `Touches` includes `tests/** and src/nonogram/**`, so ADR-0039 must be kept — it is
(ADR-0039/R1, ADR-0039/R2, ADR-0039/R3).

**ADR-0039/R1–R3 are this card's entire subject**: the component maps are claims about the code with no control, and the card's AC-2 asks for the set of component modules to be derived from the package itself and to default to deny.

**Review-lens — nothing executes these; the reviewer is the control** (5):

- **ADR-0022/R1** — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from one integer.
- **ADR-0038/R6** — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the solution before the puzzle is solved, and any public phase reopens this ADR (CON-021).
- **ADR-0038/R7** — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra.
- **ADR-0038/R8** — Browser tests run locally, against Chromium installed by `playwright install chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. Once a CI pipeline exists, it installs Chromium (playwright install chromium) before running them; until then there is no CI, and that is a known gap, not a met clause.
- **CON-021** — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). No other surface — the CLI, the web UI, or any public or hosted page — offers an interactive or playable puzzle. Play state is never persisted on the server: no progress, marks, error count, score or solve time is written to a database, file or server, no network request is made per mark, and no user account exists for playing (CON-017). The one place play state may be kept is the browser's own localStorage, per puzzle, so that a puzzle reopened in that browser resumes where it was; it never leaves that browser. The admin player ships the puzzle's solution grid to the browser to compute the error count and the solved state; this is permitted for the admin panel only, and a public or reader-facing player must not send a puzzle's solution to the browser before the puzzle is solved.

**Reach-limited — the ADR states its checks do not reach code written later** (5):

- **ADR-0036/R3** — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same difficulty glyph, and four slightly different dots cannot be fixed once a book is on paper. — check: `test_the_books_own_pages_carry_no_undeclared_round_mark`
- **ADR-0036/R4** — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: the cheapest way to print a difficulty dot is to append a bullet to a header string, and that route bypasses the one drawing site and CON-020's type floor at once. — check: `test_no_module_types_a_round_mark_as_a_character`
- **ADR-0039/R1** — A set a guard consults needs a completeness test written before the set, and any claim the guard makes about what it catches needs a control that can fail: caught WITH the set member present, missed WITHOUT it. A claim whose control cannot fail is narrative, not coverage, and must be narrowed to what is measured or deleted. — check: `test_the_control_for_each_spelling_depends_on_the_set`
- **ADR-0039/R2** — A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where no such authority exists, the guard defaults to deny: a shape it cannot analyse is a FAILURE, never a silent pass, and the unanalysable sites become named exemptions under ADR-0039/R3. — check: `test_the_guard_sets_are_derived_and_not_hand_written`
- **ADR-0039/R3** — An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT absorb — caught with the exemption removed, missed with it in place — is held to an equality against the sites that exist today, and records whatever it still cannot see as a measured bound with its own failing control. — check: `test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw`

_Dropped (7), each executed by the suite on every gate: ADR-0006/R1, ADR-0027/R2, CON-005, CON-009, CON-010, CON-011, CON-012._

## Worktree notes

- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`, reading the ADR
  files **case-insensitively** for the reach-limit idiom (the lens output carries no comment text and
  ADR-0039 writes the idiom in capitals). Sanity check: `Touches` includes `tests/**` and
  `src/nonogram/**`, so ADR-0039 must be in the kept set — if it is not, the derivation is broken, not
  the scope.
- **[Do not take timing measurements]** other cards may share this machine.
- **[The estimate is a claim-card estimate, not an edit estimate.]** The diff is a handful of prose
  lines and one test. It is cut at **0.75d** because the owner's wave-50 rule floors a card whose
  subject is a claim or a measurement at 0.75d and forbids `trivial`, whatever the diff size. Two
  waves of evidence: wave 50's two cards were cut at 0.25d and took ~0.8d each; wave 51's CARD-260 was
  cut at 0.75d and took **3.3d**. The estimate prices the edit; the cost is the certification.
- **[The trap, inherited from three cards in a row]** The failure mode when cutting a duplicated
  statement is cutting the sentence that is the **only** statement of a bound. CLAUDE.md's layout block
  is immediately followed by the paragraph that explains the layering rule and names
  `solver/propagate.py`'s `mask_runs` precedent — that paragraph is **not** a map row and is **not**
  duplicated in `__init__.py`. Do not take it with the rows. Split the retired text into clauses and
  show every clause survives somewhere, as CARD-257's AC-1 and CARD-259's AC-1 did.
- **[Why "the only inbound adapter" is the most expensive of the three]** It is not merely out of date,
  it is a statement an agent acts on. A brief that says there is one inbound adapter invites a card to
  add CLI surface for something the web UI or admin panel already exposes — and `tests/test_cli.py:754`
  already records that `cli` imports `web` as a deliberate launch edge, so the code contradicts it in
  the very file this card extends.
- **[Already corrected, do not re-fix]** `CLAUDE.md:50-51` were fixed in `9c4e851a` and verified on
  disk first. Three defects remain in that block plus five in `__init__.py`. Read the current file; do
  not work from the table in `## Why` as if it were the live state.
- **[Use CARD-260's committed instrument for any per-assertion measurement]** `tests/kill_matrix.py`,
  documented in `tests/README.md` from line 453. Do not write another. Keep deletion mutants
  **line-count-preserving**, aggregate **any-RED**, target the occurrence inside the arm you mean,
  re-run SHIPPED between mutants, and **report the domain** of every per-assertion figure.
- **[STRUCK — this note was wrong, and the error was the orchestrator's own]**
  ~~`forge:explain`'s structural inputs are missing from this project: `contexts.yml`,
  `capabilities.yml`, `actors.yml` and `external_systems.yml` do not exist under
  `meta/architecture/`.~~ **All four exist**, at `meta/architecture/domain/`, alongside
  `aggregates.yml`, `commands.yml`, `events.yml` and `policies.yml`. The orchestrator tested
  `meta/architecture/<name>.yml` and never looked in a subdirectory, then reported the registries
  absent and briefed a subagent on that premise. The subagent checked, found them, and wrote the docs
  against ground truth — declining the brief's instruction to record the absence because putting a
  known falsehood into authoritative documentation is what ADR-0039's grounding rule forbids. It was
  right to refuse. Consequences of the error that are now corrected: `docs/how-it-works/` **does**
  carry an actor-role perspective (`puzzle-creator.md`, from ACT-001 in `actors.yml`), and the project
  has **seven** capabilities, not six — CAP-007 *Puzzle play* (FR-044, US-028, CON-021, ADR-0038) is
  real, shipped code with its own L4 file. **Recorded rather than quietly deleted** because this is the
  card's own subject in miniature: a claim about the repository, asserted without a control, wrong.

---

### [Figure corrected] "51 waves" was never derivable; it is a date range

The orchestrator wrote that the stale map had misinformed briefs "for 51 waves" — in this card's `## Why`,
in the brief handed to the implementation agent, and to the owner in conversation. **It is not a figure
anything in this repository supports.** `git log -L 42,52:CLAUDE.md` shows exactly two commits ever
touching those lines — `96da6ac4` (2026-09-08, which introduced the block) and `9c4e851a` (2026-10-22,
which fixed two of its rows) — and `meta/kanban/retro.md`'s earliest dated wave is 28–30 on 2026-10-03,
so nothing maps 2026-09-08 to a wave number. The implementation agent re-derived this, declined to repeat
the figure in `CLAUDE.md`'s new sentence, and said why; the card is corrected to the date range it can
support.

**Second figure corrected, from the same hand-back.** The orchestrator's brief said the solver's
cooperative deadline is checked at **four** sites. It is checked at **six** — `propagate.py:983`,
`:1129`, `search.py:1180`, `:1259`, **`:1418`** and **`:1728`** (`grep -n 'check_deadline(' src/nonogram/solver/*.py`,
with the raise at `propagate.py:221` and the one per-request deadline fixed at `orchestrator.py:1793`).
A subset was stated as if complete. It changes nothing about the card — the point was that the timeout
*is* enforced, and six sites make that case more strongly than four — but a figure in a brief is a claim,
and its control is recomputation.

---

### Implementation summary (CARD-261)

**TDD, one line per criterion:**

- AC-1: test `TestComponentMap_EveryComponentIsListedExactlyOnce::test_every_component_the_walk_finds_appears_exactly_once` red→green (red naming `['errors', 'limits']` as *in the package, absent from the map* — the canonical map listed 11 of the 13 components the walk enumerates, with `errors.py`/`limits.py` carried as prose rather than rows).
- AC-2: test `TestComponentMap_APlantedModuleAndAPlantedRowBothRed` (6 methods) red→green, plus the real on-disk plants below.
- AC-3: test `TestComponentMap_ThereIsOneRowPerComponentAcrossBothFiles::test_claude_md_states_no_component_row_of_its_own` red→green (red naming all seven of CLAUDE.md's rows, lines 45-51).
- AC-4: no new test — `test_the_import_rule_rejects_each_forbidden_edge` (10 params) and `test_the_import_rule_allows_the_legitimate_edges` re-run unchanged, with the other 6 walk guards: 17 tests, exit 0. The parametrisation, `_ADAPTERS`, `_SHARED`, `_LAUNCH_EDGE`, `_rank` and `_outward_imports` are untouched; the extension only consumes `_MODULES` and `_component`.
- AC-5: the bound is declared in `_map_defects`' docstring, in its own paragraph: the control holds the **row set** and cannot judge a row's **description**; a row may be present, unique and describe its module wrongly and the control will pass.

**AC-3: the shape that shipped, and why.** CLAUDE.md's layout block carries **no component row** — it points at `src/nonogram/__init__.py`, which CLAUDE.md already named as canonical. Chosen over keeping a held copy on three pieces of evidence, not on which was easier to write: (1) the measured drift is in *both* copies and in *different places* (CLAUDE.md had the stale adapter count and the stale `sourcing/` clause; `__init__.py` had five `(later card)` annotations), so a second copy doubles the surface without adding a reader anything; (2) a held copy would carry **descriptions**, and AC-5 says descriptions are exactly what no enumeration can hold — a CLAUDE.md copy whose rows were pinned by name and whose prose was not is a control that looks stronger than it is; (3) G-2 forbids a third copy, so the only shape with one statement per fact is one file. The block keeps the layering paragraph after it untouched (G-4) and keeps exactly one corrected clause inline, the adapter count, because a brief is acted on.

**Clause survival — the retired CLAUDE.md text (old lines 42-52), clause by clause.** Nothing was taken with the rows:

| retired clause | survives |
|---|---|
| "Layered pipeline" | CLAUDE.md's bold lead-in (kept verbatim); `__init__.py` "layered pipeline package" |
| "one bounded context (CTX-001)" | CLAUDE.md lead-in; `__init__.py` "one bounded context, CTX-001" |
| "one dependency direction" | CLAUDE.md lead-in; `__init__.py` "Dependencies point inward only" |
| "`src/nonogram/__init__.py` docstring is the canonical map" | CLAUDE.md's new pointer sentence; `__init__.py`'s opening paragraph |
| `cli.py COMP-001` "inbound adapter (argparse)" | `__init__.py` `cli.py` row |
| "**the only** inbound adapter" | **retired as false** — corrected, not lost: CLAUDE.md now states three inbound adapters, and `__init__.py` carries `cli.py`, `web/` and `admin/` as rows |
| "parsing only, no domain validation" | `__init__.py` `cli.py` row (verbatim) |
| `orchestrator.py COMP-002` "owns the Puzzle aggregate" | `__init__.py` `orchestrator.py` row ("owns the Puzzle aggregate (AGG-001)") |
| "drives the capability modules below" | `__init__.py` `orchestrator.py` row (verbatim) |
| `sourcing/ COMP-003` "sources a solution grid" | `__init__.py` `sourcing/` row (verbatim) |
| "(random implemented; library/image are future work)" | **retired as false** — corrected to the three modules that exist, named: `random_grid.py`, `library.py` with `templates/`, `image.py` |
| `clues.py COMP-004` "pure run-length-encoding of a grid into row/column clues" | `__init__.py` `clues.py` row |
| `solver/ COMP-005` "hand-rolled constraint-propagation + backtracking uniqueness solver" | `__init__.py` `solver/` row |
| `difficulty.py COMP-006` "scores 0..100 from the solver's rung tags, then the Easy/Medium/Hard bands" | `__init__.py` `difficulty.py` row (verbatim) |
| `export/ COMP-007` "PNG/SVG/JSON/CSV/PDF renderers, plus `layout.py`'s shared page geometry" | `__init__.py` `export/` row (verbatim) |

The paragraph after the block — the layering rule and `solver/propagate.py`'s `mask_runs` precedent — was **not** touched, per the trap note. Nor were the Commands, boundary-types, dependency-baseline, solver or test-style paragraphs (G-4).

**AC-2's plants, each shown in both states.** Real plants on disk, not reasoned about; `cp -p` backup, `shasum -a 256` baseline, restore in a `trap`, verified byte-for-byte (both files matched their baseline digest, plant file removed):

| state | result |
|---|---|
| 0 SHIPPED | green (11 tests) |
| 1 planted module `src/nonogram/planted_component.py` on disk | **RED**, naming it: `{'in the package, absent from the map': ['planted_component']}` |
| 2 plant removed | green |
| 3 planted row `planted_row.py COMP-099` in the canonical map | **RED**, naming it: `{'named by a row, absent from the package': ['planted_row']}` |
| 4 plant removed | green |
| 5 planted row `cli.py COMP-001 the only inbound adapter` pasted back into CLAUDE.md | **RED**, naming the line: `['45: cli.py           COMP-001  the only inbound adapter']` |
| 6 plant removed | green |

**Deletion mutants — the mechanism itself, via the committed instrument.** `tests/kill_matrix.py`, six line-count-preserving deletion mutants (each branch body replaced by `pass` plus a comment on the same line count; assert topology re-derived and unchanged). ANY-RED aggregation. **DOMAIN:** 96 `ast.Assert` nodes in `tests/test_cli.py` (an `ast.Assert` node count, not a collected-test count), selection = the three `TestComponentMap_*` classes, 11 collected tests, 13 arms reached, child instrumentation **off**, `SHIPPED` 0 FAIL of 13 reached at pytest exit 0 and re-run between mutants. Both passes run:

| mutant (what was deleted) | recording pass | re-raising pass | killed by |
|---|---|---|---|
| the branch naming an unlisted component | 1 FAIL, exit 0 | 1 FAIL, exit 1 | `:1249` planted module |
| the branch naming a row with no module | 1 FAIL, exit 0 | 1 FAIL, exit 1 | `:1263` planted row |
| the branch naming a twice-listed component | 1 FAIL, exit 0 | 1 FAIL, exit 1 | `:1270` second row |
| the default-deny branch for an unreadable line | 1 FAIL, exit 0 | 1 FAIL, exit 1 | `:1280` unanalysable |
| the parser's record of a line it cannot read | 1 FAIL, exit 0 | 1 FAIL, exit 1 | `:1294` parser reports |
| the CLAUDE.md row reader's two patterns | 1 FAIL, exit 0 | 1 FAIL, exit 1 | `:1332` planted CLAUDE.md row |

6 of 6 killed, one arm each — no mutant was killed by two arms and no arm killed two mutants, so no branch is subsumed. Exit 0 under the recording pass is that pass's suppressed propagation, not a survival; the re-raising pass is the propagation reading.

**Every figure, re-derived, with its method.** None is reproduced from the card's `## Why` table:

- **29,358 of 46,260 lines, 63%** for `web/ + admin/ + db/ + analysis/`. Method: `find src/nonogram -name '*.py' | xargs wc -l | tail -1` for the denominator, and the same over the four directories for the numerator; `29358/46260 = 63.5%`. The card's 2026-10-22 figure was 29,225 of 46,127 — **both moved by exactly +133** (CARD-206's interior-pages work), and the percentage is unchanged. `wc -l` counts physical lines, blanks and comments included; that is the bound of this figure and it is not a measure of behaviour. **The figure is not repeated in either map** — it was a motivation for the card, not a claim either file now makes.
- **13 component modules, 13 rows, one each.** Method: the import walk's own enumeration, `{_component(m) for m in _MODULES}` over `src/nonogram/**/*.py` on disk — the authority ADR-0039/R2 asks for, not a list in the test. Derived, not read: `['admin','analysis','cli','clues','db','difficulty','errors','export','limits','orchestrator','solver','sourcing','web']`.
- **Three inbound adapters.** Method: `_ADAPTERS` at `tests/test_cli.py:747`, pinned literally and asserted by `test_the_adapter_allowlist_is_closed_at_the_two_known_adapters`, cross-checked against the three directories/files on disk. The code already contradicted CLAUDE.md in this very file.
- **`validate_size` occurs 0 times in `src/`.** Method: `grep -rn validate_size src/`. The public validator is `validate_extent`, `src/nonogram/sourcing/random_grid.py:131`; ADR-0022/R1's refusal of a one-integer public validator is recorded in `_validate_side`'s docstring (`:115` def, note at `:118-122`), not at `:118` as the brief's figure had it.
- **`MAX_SIZE = 30`** at `src/nonogram/limits.py:17` (`MIN_SIZE = 10` at `:16`), so a 40x40 grid cannot be produced. Method: read the module.
- **The cooperative deadline is checked at SIX sites, not four.** Method: `grep -n 'check_deadline(' src/nonogram/solver/*.py` — `propagate.py:983`, `propagate.py:1129`, `search.py:1180`, `search.py:1259`, **`search.py:1418`**, **`search.py:1728`**; raised at `propagate.py:221`; the one per-request deadline is fixed at `orchestrator.py:1793` and passed at `:1859`. The brief's four-site figure is a subset. Reporting the correction only — see the next section for why no edit followed.
- **Three optional-dependency extras**, not one: `dev` (`pytest>=8.3`, `pytest-playwright>=0.7`), `admin` (Flask, Werkzeug, reportlab, gunicorn), `db` (SQLAlchemy, alembic, psycopg2-binary). Method: read `pyproject.toml:28-56`.
- **Test runs.** `tests/test_cli.py` 107 collected, exit 0; the 11 `TestComponentMap_*`, exit 0; the 17 walk/layering guards (AC-4), exit 0; `tests/test_guard_integrity.py` + `tests/test_suite_profile.py` 530 collected, exit 0 (this is where ADR-0036/R4's and ADR-0039/R1-R3's own checks live). No durations measured or reported.
- **"51 waves" — not re-derivable, so narrowed rather than repeated.** Method attempted: `git log -L 42,52:CLAUDE.md` shows exactly two commits ever touching those lines — `96da6ac4` (2026-09-08, introduced the block) and `9c4e851a` (2026-10-22, the two direct fixes). `meta/kanban/retro.md`'s earliest dated wave is waves 28-30 on 2026-10-03, so no artifact in the repository maps 2026-09-08 to a wave number and "51" cannot be recomputed. CLAUDE.md's new sentence therefore says the copy drifted, without a figure.

**Claims I wanted to write and did not.**

- **The three remaining CLAUDE.md defects outside the layout block were left in place**, deliberately. `CLAUDE.md:56` (boundary types) still cites the non-existent `validate_size`; `:58` (dependency baseline) still says "plus `pytest` as a dev-only extra" against three extras; `:60` (solver) still says the cooperative timeout is "not yet enforced" and still cites 40x40 grids. All three are real and re-derived above. **G-4 is authoritative and names the boundary-types and dependency-baseline paragraphs explicitly**, and its first sentence covers the solver paragraph too; `## What to implement` step 1 enumerates exactly three CLAUDE.md defects, all three inside the layout block. Editing them would be a guardrail breach, so they are reported, not fixed — **they want a follow-up card**, and the "not yet enforced" one is the expensive one by the same argument the card makes about "the only inbound adapter": it is a statement an agent acts on, and a card told the timeout is absent may re-add it. The same follow-up should take the three test docstrings that still name `validate_size` (outside this card's `Touches`).
- **No clean-scan claim for ADR-0036/R4 over the tree.** G-6 is live and I edited a `src/nonogram/**` docstring, so I scanned **the file I edited** with an independent AST walk over its string literals (0 hits in U+25A0..U+25FF, U+2022, U+2219) and otherwise leaned on the committed guard. `pdf_generator.py`'s three U+2022 are the declared exemption and a whole-tree clean-scan claim would be false.
- **No claim that the descriptions are right.** `_map_defects`' docstring says the opposite, and AC-5 is why. I verified by hand the descriptions I moved into `src/` (5 export renderers plus `layout.py`; `difficulty.py`'s 0..100 rung bands; the three `sourcing/` modules; `solver/`'s two modules) — but a hand verification is not a control and is not claimed as one.
- **No claim that the control catches a prose restatement of the map in CLAUDE.md.** It catches the tabular row shape and any `COMP-NNN` id. A map rewritten as running prose with no ids would evade it. Declared in the class docstring.

**Honest bounds, all declared in the code that makes the claim.**

1. **Descriptions are not controlled** (`_map_defects`). The row set is; a row's account of its module is a human reading.
2. **CLAUDE.md is read for two shapes only** (`TestComponentMap_ThereIsOneRowPerComponentAcrossBothFiles`): a line-initial `name.py`/`name/` followed by two or more spaces, and any line naming `COMP-<digit>`. Prose with no ids evades it.
3. **The canonical map's parser claims the four-space-indent convention, and denies otherwise** (`_canonical_map`). A four-space-indented line that is not a row is returned as unanalysable and fails; the cost is that an unrelated indented example added to that docstring will red until it is indented differently. That is default-deny working, not a bug.
4. **The walk's granularity is the top-level name under `nonogram`.** `solver/search.py` is the `solver` component; the map says nothing about submodules and the control checks nothing about them. Inherited from `_component`, which the layering guard already used.
5. **`wc -l` is physical lines.** The 63% figure measures text, not behaviour or value.
6. **The kill matrix's domain is stated with every figure** above: pass, `ast.Assert` denominator, pytest exit code, child-instrumentation flag.

**What was touched:** `CLAUDE.md` (the layout block only), `src/nonogram/__init__.py` (docstring only; `__version__` unchanged), `tests/test_cli.py` (one `import re`, four module-level helpers, three test classes appended after the walk section; nothing existing edited). No runtime dependency added (G-3). `nonogram_poc` never named, created, connected to or dropped; `_refuse_unless_test_database` untouched (G-5). Full-suite lock: `NONOGRAM_FULL_SUITE_LOCK=/tmp/card261-impl.lock` exported for every pytest run; `meta/kanban/.full-suite.lock` never read, written or created. The full suite was not run.

---

### [Notes restored — the orchestrator destroyed them and recovered them]

The implementation's `## Worktree notes` summary above was **overwritten by the orchestrator** and then
recovered from the subagent's transcript. Recorded because the cause is a rule this board states
explicitly and I broke it.

`cmd-start-review.md`'s card-file ownership rule is one-way: pull agent notes **worktree → main**, and
*"never write in the other direction"*. All session I had been copying **main → worktree** after each
orchestrator edit, to keep each agent's copy current — which is correct *before* an agent runs and
destructive *after*. At `cbfe4d68` I corrected two figures on this card and copied main's version into
the worktree in the same breath, minutes after the agent had finished. That `cp -p` clobbered its
evidence record.

Recovery was possible only because the subagent wrote the notes with a shell heredoc, so the text
survived in its transcript's `command` field; a `Write` call would have been just as recoverable, but a
card edited in place with several small edits might not have been. **The durable fix is not to be more
careful — it is to stop copying main → worktree once an agent is live**, and to pull notes before any
orchestrator edit to the same card.

---

### [Build gate] PASSED: 8009 passed, 16 skipped, 0 failed, EXIT=0 — impact-scoped, with the override declared

185-file selection at `604cc542`. The 16 skips are `db_required`/browser, green. Run while CARD-262's
implementation was live in the sibling worktree, so the board lock was **not** taken — the redirect went
to a scratch path.

**The selector returned `FULL`, and narrowing it was derived rather than judged.** `CLAUDE.md` sits at
the repository root, outside `scripts/impact_set.py`'s `KNOWN_ROOTS`, so the selector cannot model it and
**fails closed** — correct behaviour, but a full suite takes the lock and would have red the sibling's
agent. The narrowing rests on a measurement, not a preference: **exactly one test file reads
`CLAUDE.md`** — `tests/test_cli.py`, which is in the changed set on its own merits, so selecting on it
covers the `CLAUDE.md` change completely. Every other test that mentions the file only names it in prose
(checked across all 40 files that mention it). The two modellable paths were handed to the selector
instead, and it chose 185 files.

**A gap in the selector this card exposes, worth feeding back.** A root-level file should be modelled by
**which tests read it**, not by a root prefix — `CLAUDE.md`, `README.md` and their kind will hit this
every time. The irony is load-bearing: before this card **nothing read `CLAUDE.md` at all**, and
CARD-261 is precisely what turns it into a real import edge. So the selector's blind spot and this card's
subject are the same defect, one level apart. Recorded in `meta/kanban/backlog.md` rather than fixed
here.

**And a figure the selection itself establishes:** 185 of 212 test files, because
`src/nonogram/__init__.py` is the **package root** — every test importing anything under `nonogram`
reaches it transitively. For a change to that file, impact scoping buys almost nothing *by construction*.
That is the mirror of `export/layout.py` at 186 files and `db/session.py` at 36: narrowing works for leaf
modules and collapses toward the full suite for roots and hubs. The reliable win here was never speed —
it was that 185 files ran **without taking the lock**, which is what let the sibling card keep working.

---

### [Review cycle 1] 7.5 / 10 — min_score 8, not a pass. Two Important, four scored minors, one pre-existing at zero

Report: `meta/review/20261022T085642Z-CARD-261-cycle1.yml` (synced out of the worktree; the reviewer
wrote nothing but that file, and never touched the card). Arithmetic:
`10 − 1 (F-101) − 1 (F-102) − 0.5 (four minors, clustered two-and-two) = 7.5`. Risk: medium.
Certification `deferred(cost)` — correctly, and for the right reason: the minimal fix for **either**
gating finding adds a test to the `TestComponentMap_*` classes, which is exactly the selection the
six-mutant matrix was computed over, so certifying now certifies a selection about to change.

**Both gating findings are this card's own subject turned on its own output.** Neither is a code
defect; both are control-coverage defects, which the reviewer notes is the only class of defect a card
like this can have.

| id | sev | the defect |
|---|---|---|
| **F-101** | important | the control forbids the row **shape**, not component **content** — and the shipped CLAUDE.md carries an uncontrolled component claim: *"there are **three** inbound adapters (`cli.py`, `web/` and `admin/`), not one"*. ADR-0039/R1 + R3; AC-3's own purpose ("exactly one place a row can drift from") is not reached for the adapter count |
| **F-102** | important | the canonical map's **COMP-id / CAP-id columns are unheld**, an enumerable authority exists (`meta/architecture/c4/components-CTX-001.puml:93/:100/:102`), and the declared bound absorbs them under the word *"descriptions"*. ADR-0039/R2 (authority exists, unused) + R3 (exemption absorbs an enumerable column silently) |
| F-103 | minor | `_canonical_map`'s docstring attributes the four-space rule to the `::` literal blocks; the parser claims every four-space-indented line in the whole docstring |
| F-104 | minor | the 63% figure's denominator is the **pre-card** tree — 46,260, not 46,289 at `604cc542`; the 29-line gap *is* this card's own `+55/−26` |
| F-105 | minor | CLAUDE.md's new sentence drops a word: *"both copies had, in different places"* does not parse |
| F-106 | minor | `_claude_md_rows` denies **any** CLAUDE.md line containing `COMP-<digit>` — prose or fenced code block — wider than the test's name and message claim |
| F-107 | minor, scored 0 | pre-existing, outside the diff: `test_the_adapter_allowlist_is_closed_at_the_two_known_adapters` asserts **three** names |

**The three things I asked it to attack, and what it found.** All three were *executed*, not argued.

1. **Bound 2's prose-evasion is real.** It appended a full prose restatement of the map to `CLAUDE.md`
   carrying four of the exact falsehoods this card measured — *"cli.py is the only inbound adapter"*,
   *"library and image modes still future work"*, *"difficulty.py is not yet built"*, *"export/ is not
   yet built either"* — with no rows and no COMP ids. **11 passed; the whole file green.** The drift
   this card exists to prevent walked straight back into the file every session loads, with zero
   signal. Restored, `shasum -a 256 -c` and `diff -q` both clean.
2. **Bound 3 is default-deny, not brittle.** Two plants of four-space-indented non-rows
   (`nonogram generate …`, `$ nonogram serve`) each produced **3 failures naming the offending line**.
   ADR-0039/R2's words are satisfied. The only defect there is F-103, one clause.
3. **AC-3's decision is sound, and it checked all three legs rather than accepting them.** It read
   `fac4896f`'s two copies and confirmed the drift was in both and in different places; and it
   **measured** the "a held copy carries descriptions no enumeration can hold" leg instead of reasoning
   it — putting `not yet built (later card)` back on `difficulty.py`'s row left all 11 tests green.
   But **the one inline clause it kept is not justified**: it is the beginning of the second copy the
   decision was meant to avoid, and it is the very condition that leg ruled out.

**The row-present-but-wrong class the brief predicted — three plants, all green.** A wrong COMP id
plus a CAP id belonging to nothing; `clues.py` relabelled `COMP-005` so **two rows claim one id and
COMP-004 vanishes from the map**; and the declared AC-5 description bound. Same single mechanism.

**AC-4 holds and the no-rottable-figure claim holds.** `git diff -U0 | grep -c '^-[^-]'` → **0**,
`--numstat` → `261 0`; `import re` is a pure insertion, so `_ADAPTERS`/`_SHARED`/`_LAUNCH_EDGE`/
`_rank`/`_outward_imports`/`_MODULES`/`_component` are byte-identical. A grep for every rottable
figure across both shipped files returns **zero hits** — the author's claim is correct.

**Figures: eleven of twelve reproduce by an independent method; one does not** (F-104's denominator).
Two corrections to the implementation's own notes, both mine to carry forward: `_ADAPTERS` is at
`tests/test_cli.py:748`, not `:747`; and the reviewer re-derived `validate_size` at **0** occurrences
in `src/`, `validate_extent` at `random_grid.py:131` — which is CARD-264's premise, now independently
confirmed.

**G-4's boundary respected in both directions.** The CLAUDE.md diff is one hunk, `@@ -39,17 +39,7 @@`,
entirely inside the layout block; all three out-of-block defects verified **still present** on disk and
correctly left for CARD-264. In-block, `grep -c "later card" src/nonogram/__init__.py` → **0**.

**One thing the reviewer could not establish, which the next cycle must.** The reported kill matrix
fuses `_CLAUDE_MD_ROW` and `_COMPONENT_ID` into a **single arm** ("the CLAUDE.md row reader's two
patterns"), so whether the two patterns are **independently** controlled is *not established* by the
reported figures. It also named two further arms worth adding: `_canonical_map`'s
`if not body or body[0].isspace(): continue` and `_component_modules`' walrus `is not None` guard.

---

### [Fix round 1] `feb3e6b5` — both gating findings closed, and the fixer corrected my brief on the way

Four files, explicit pathspecs, `+1285/−22`. `tests/test_cli.py` 107 → **130** tests; `TestComponentMap_*`
11 → **34** across five classes. Nine on-disk plants shown red→green; 16 mutants, 15 killed, 1 **proved**
behaviour-equivalent. Review cycle 2 dispatched; build gate running impact-scoped at `feb3e6b5` with the
board lock redirected to a scratch path, because CARD-262 is live in the sibling worktree.

**F-101, both halves.** `CLAUDE.md:42` states no count and names no module; it points at the canonical
map and at `_ADAPTERS`. The control that holds it, `test_claude_md_states_no_count_of_adapters`, **strips
markdown emphasis first** — and that detail is the interesting one: the shipped clause wrote `**three**`,
so a reader of bare words would have passed the exact line the control exists to refuse. Written before
the `CLAUDE.md` edit, it red on the shipped file quoting the clause verbatim. The bound itself is now a
committed table — `TestComponentMap_WhatTheClaudeMdReaderAbsorbs`, 5 must-catch and 5 known-miss asserted
one-for-one with a `len(CASES) >= 10` floor — plus the hole's **edge**: cycle 1's prose plant is missed,
the same paragraph with one `COMP-001` added is caught. Widening `_claude_md_rows` reds **three** tests,
one of which says *"the declared hole has closed … AC-3's bound and this class must be rewritten"*.

**F-102.** `_c4_components` parses the C4 authority by macro **prefix**, so `ComponentDb(`/`db/` is not
missed, and default-denies any declaration it cannot analyse. `_id_defects` carries ten kinds — four
needing no authority at all (id claimed twice, id no row carries, id no diagram enumerates, CAP id not in
the registry), four pairing comparisons, and two that hold the R3 exemption set **in both directions**.
Cycle 1's plant C now reds on **four** keys at once, plant D on three including `['COMP-004']` vanished,
and an em-dash→hyphen swap in the puml reds as `unanalysable Component declarations`.

**My brief was wrong about the CAP authority, and the fixer held it instead of exempting it.** I measured
`capabilities.yml` as pairing nothing with a module — true, and now asserted as a control. But I had
already read the puml lines where the **fourth** argument leads with the capability id
(`Component(sourcing, "COMP-003 …", "Python — sourcing/", "CAP-001: produces a …")`) and I did not see
it: the pairing was in my own grep output. It covers exactly `sourcing`/`clues`/`solver`/`difficulty`/
`export` — exactly the five map rows that carry a CAP id — with the residual hole measured at **one**
(`admin/` names CAP-006 mid-sentence, so parser and map agree on carrying none), pinned by
`test_the_capability_pairing_reads_only_a_leading_cap_id`. Cycle 2 is re-deriving it, because a
five-row agreement that is really a coincidence would be a control resting on luck.

**Every other figure of mine reproduced exactly:** 13 walk components; 10 COMP ids across `Component(`×9
plus `ComponentDb(`×1 at `:102`; module in the third argument with the trailing parenthetical excluded;
`errors`/`limits`/`analysis` id-less at 10 of 13; CAP-001..007; `_ADAPTERS` at `:748`; and both
denominators, 46,289 against 46,260, numerator 29,358 at both commits.

**The three arms cycle 1 could not settle all fired, separately.** `_CLAUDE_MD_ROW` alone (3/2 FAIL) and
`_COMPONENT_ID` alone (4/3 FAIL) each kill independently, so the fused-arm question is answered.
**Domain, as required:** 138 `ast.Assert` nodes in `tests/test_cli.py` — an assert-node count, not a
collected-test count; selection the five `TestComponentMap_*` classes; 34 collected tests; 55 arms
reached; SHIPPED 0 FAIL of 55 reached at exit 0; child instrumentation off; ANY-RED over both passes;
re-run at the final committed state and cell-for-cell identical.

**The one mutant that did not kill is proved a no-op, not a survivor** — and the proof is the kind this
board has been asking for. `_map_row_ids`' `isspace` guard is unreachable because `_ROW_IDS` is anchored
and the non-match path is `continue`: 13 rows with the guard, the identical 13 tuples without it. The
**asymmetry** is the load-bearing part — `_canonical_map`'s non-match path is *deny*, so the same guard
there does matter, and M3 killed 4/4.

**The bound it declared rather than closed, which is cycle 2's first target.** The canonical map now
carries a **"two pipeline adapters"** count with **no control** — no artifact pairs a component with
"is a pipeline adapter". The fixer's argument is that this count sits beside held rows and beside
`_ADAPTERS` where CLAUDE.md's sat alone. That may be right, but F-101 *was* an uncontrolled count in a
file agents read, and an uncontrolled count in `src/nonogram/__init__.py` is still one. Cycle 2 is asked
to decide whether the defect moved or closed, by planting a wrong count rather than by reasoning.

**AC-4 survives a second fix round.** `grep -c '^-[^-]'` against `fac4896f` → **0**; `--numstat` →
`1028 0`. Against `604cc542` it is `781 14`, and each of the 14 removed lines was checked individually as
absent from `fac4896f` — the fixer worked under the constraint of rewriting only lines *this card*
introduced. Cycle 2 re-derives it.

**AC-5 is met as written but outgrown**, and the fixer proposed amended wording rather than leaving it
to be noticed at the gate: substitute "English description" for "description", state that the COMP/CAP
columns are now held against the puml, and require the remaining hole to be *asserted* rather than
declared. The shipped artefact already satisfies the amended form. Cycle 2 judges the wording.

### Two decisions of mine, recorded

**F-107 stays on CARD-264** — routed there at `529d9543` as AC-7, after I measured it wider than cycle 1
filed it: three stale "two" claims, not one (the test's name, its docstring's first line, and the module
comment above `_ADAPTERS` which now reads as a prohibition on a decision that already landed). The
sequencing is the thing to watch: **CARD-261 is what creates the reachable pointer**, because F-101(a)
sends a `CLAUDE.md` reader straight to `_ADAPTERS` and that reader lands on a test whose name lies.
CARD-264 should go out in the next wave rather than sit unscheduled.

**A bug of mine in the gate script, worth recording because it is the third of its family this week.**
My first run reported `selected 6324 files` and `PYTEST_EXIT=4`. `SEL=${(f)"$(...)"}` assigns a **scalar**
in zsh, so `${#SEL}` counted characters and `"${SEL[@]}"` passed the whole listing as one argument —
pytest's usage error, not a test failure. Fixed by making it an array, `SEL=( ${(f)"$(...)"} )`. The
family: zsh does not word-split unquoted expansions, and every tool I write that pipes a file list into
`pytest` has to say so explicitly. The gate was re-run; the first run tested **nothing** and must not be
read as evidence of anything.

### The disclosure the fixer volunteered, which is a trap worth keeping

An early ad-hoc probe of its own ran `import nonogram` without the worktree's `src` on `sys.path` and
silently resolved to the **editable install's** copy in the main checkout, reporting **11** rows — the
*pre-card* map. No write, no test run there; it then verified through pytest that the worktree's own
`__init__.py` is loaded with 13 rows, and redid the affected proof. It flagged this itself.

Keep it: `pyproject.toml`'s `pythonpath = ["src"]` makes **pytest** correct inside a worktree, and makes
every ad-hoc `python -c "import nonogram"` **wrong there** — it reads main. Any structural probe from a
card worktree must go through pytest, or put the worktree's `src` first with `python -I`. A figure that
disagrees with a worktree's own tree by exactly the pre-card value is this, not a real disagreement.

### [Build gate, fix 1] PASSED at `feb3e6b5` — exit 0, 185 files, 8048 collected

Impact-scoped exactly as the first gate was: the selector returns `FULL` for this change set (`CLAUDE.md`
sits outside `KNOWN_ROOTS`), so the two modellable paths — `src/nonogram/__init__.py` and
`tests/test_cli.py` — were handed to it and it chose **185 of 212** test files. Board lock **not** taken;
`NONOGRAM_FULL_SUITE_LOCK` pointed at a scratch path and pytest announced the redirect itself in the run
output, which is the evidence that CARD-255's guard read the scratch file and not the board's.

**The collected count cross-checks the fix round independently.** 8048 now against the first gate's
**8025** (8009 passed + 16 skipped) at `604cc542` — a delta of **+23**, which is exactly the +23 tests
the fixer claims for `tests/test_cli.py` (107 → 130). Two different instruments, same figure.

**What this gate does not establish, stated rather than implied.** `PYTEST_EXIT=0` means nothing failed.
The passed/skipped split is **lost** — my `tail -15` truncated the summary line and kept the warnings
block instead, so I can report 0 failed and 8048 collected but not the pass/skip breakdown without
re-running. I am not re-running a 185-file selection for a figure the exit code already settles; the
count above comes from a separate `--collect-only` pass, which executes nothing.

Two pre-existing warnings surfaced again and are already on the backlog: `dog_in_house.py:6`'s invalid
escape sequence (`"\,"`), and `datetime.utcnow()` at `tests/test_image_batch_size_fix.py:395`.

---

### [Review cycle 2] 7.8 — FAIL, and the trigger is `min_improvement`, not the finding

Report: `meta/review/20261022T094719Z-CARD-261-cycle2.yml`. **Six of cycle 1's seven findings are
genuinely closed** — F-102, F-103, F-104, F-105, F-106 and F-101(b) all verified closed, and every
default-deny plant aimed at the new controls reds naming the offender. One Important remains.

**Read the two scores before reacting to the gap, because they are not on the same scale.** Cycle 1 was
`10 − 1 − 1 − 0.5 = 7.5`. Cycle 2 is `8.7 baseline − 0.6 − 0.15 − 0.15 = 7.8`. The reviewer re-based from
10 to **8.7**, so the +0.3 is partly an artefact of a changed denominator rather than a measure of how
much the card improved. The `min_improvement: 0.5` breach is real against the recorded numbers and I am
treating it as real — but a card that closed six of seven findings did not improve by three tenths of
anything, and the honest statement is that **the scales differ**.

**I-1 (Important) — one root cause, two executed symptoms, and it is in the control fix 1 added.**
The reach of a reader and the strength of its corpus are pinned by **quantity** instead of by the cases
that carry the claim. That is the interesting part: *everywhere else* this card pins the claim-bearing
artefact literally — `_ADAPTERS`, `_WITHOUT_A_COMPONENT_ID`, `_LAUNCH_EDGE` — and the one control added
this round did not get that treatment.

- **(a) the `>= 10` floor is padable.** `TestComponentMap_WhatTheClaudeMdReaderAbsorbs` claims *"the
  extent cannot now change in either direction … without a red."* The reviewer replaced three of the five
  known-miss cases — **including `(False, "`cli.py` is the only inbound adapter.")`, this card's own
  six-week defect and the only committed artefact telling a reader that F-101's wording still evades** —
  with near-duplicate must-catch rows, tuple still length 10. **Exit 0, no message.** The half of the
  corpus that *is* the class's purpose shrank 5 → 2 under a floor written so it could not silently shrink.
  The positive control holds: widening `_COMPONENT_ID` to `(?:COMP|CAP)-\d` reds two tests naming
  `['sourcing covers CAP-001 and nothing else.']`, reproducing the fixer's plant J exactly.
- **(b) `_adapter_counts` misses F-101's own wording.** Planted as prose: *"Both inbound adapters import
  the orchestrator; `cli.py` is the only inbound adapter that parses argv."* → exit 0 across both
  `test_cli.py` and `test_guard_integrity.py`. And the control's **own docstring** opens *"The retired
  block's worst error was 'the only inbound adapter'"* — a shape its regex cannot match. A 32-form sweep:
  caught are numerals, words, emphasis, split emphasis, fenced, `two adapters:`; **missed** are `both`,
  `the only`, `the sole`, `a pair of`, `a trio of`, enumerations, `three inbound entry points`,
  `eleven`, three-words-distance and hyphenated adjectives. It also **false-positives** on the deny side:
  *"See section 3 about inbound adapters."* reds, as does *"the four tests cover adapters"*.

Remedy, per the reviewer: **~30 lines in one file** — pin the must-catch/known-miss split and the specific
counterexample strings, give `_adapter_counts` its own CASES corpus, correct two docstrings.

### Three corrections to things I wrote, all three mine

**1. My brief's premise about the relocated count was wrong.** I told cycle 2 that the "two pipeline
adapters" count had *moved* from `CLAUDE.md` into the canonical map, and asked it to judge whether the
defect relocated. It did not: `git show fac4896f:src/nonogram/__init__.py` already said *"the two adapters
import `orchestrator`"* and *"There are exactly two adapters (ADR-0019)"*. The card's edit **inserted the
word "pipeline"**, narrowing a claim that was already there; `CLAUDE.md`'s count was removed and not
re-sited. The count *is* uncontrolled — filed as **M-1**, and it is the only row in the fixer's own table
whose control column says "none" — but on the question I actually asked, *is it worse or better for the
reader*, the answer is **strictly better**: scoped, true today, and three lines from held rows. The
fixer's argument was sound on the evidence and my framing was not.

**2. My gate-breadth justification rested on a false measurement.** I recorded that **exactly one** test
file reads `CLAUDE.md`. There are **two**: `tests/test_guard_integrity.py:80` binds
`GUIDANCE = REPO_ROOT / "CLAUDE.md"` and reads it at `:2840` (the interpreter-floor test, regex-scanning
`python(\d+)\.(\d+)\s+-m\s+venv`). I have verified this on main myself. 42 files under `tests/` mention
the file; **40** are prose citations — which is the read-versus-mention distinction my claim needed and
did not draw. **The conclusion survives**: that second reader scans the Commands section near line 10,
nowhere near the single hunk at line 42, it was inside the 185-file gate selection, and the reviewer ran
it green both at HEAD and under its plant. The puml/`capabilities.yml` half of the claim is true.

**3. Two smaller figures.** `import re` **was** added — at `604cc542`, not fix round 1 — so the fixer's
"no new import at all" is true of fix round 1 only, and G-3 still holds (stdlib, test file). And the
`CLAUDE.md` hunk header is `@@ -42,11 +42 @@`, not `@@ -42 +42 @@`.

### What cycle 2 verified independently, and these are the ones worth keeping

- **The five-row CAP coincidence is not luck.** One convention — lead the description with the CAP id —
  applied to exactly the five capability modules, with both artefacts following it. Loose set is
  `["admin"]` alone. Re-derived twice, by eye over the puml and via an isolated `_c4_components`.
- **The ten defect kinds are ten behaviours, not ten names.** All ten fire, **all 90 ordered pairs are
  separable** (86 on ten fabricated inputs, the last four on two built for them), all ten have a
  *committed* case, and every committed assertion is tight — `==` on the whole dict, or a subscript that
  `KeyError`s.
- **M1/M2 fire separately**, with disjoint offender sets. Cycle 1's fused-arm question is settled by
  observation rather than by a matrix.
- **M14 is a no-op and M3 is not, measured by output rather than argued.** M3 turns 0 unanalysable lines
  into **22**; M14's 13 tuples are cell-for-cell identical. `_ROW_IDS` verified anchored
  (`.match("    continuation")` is `None`) with `continue` on non-match, while `_MAP_ROW`'s non-match is
  **deny**. That is the asymmetry, demonstrated.
- **AC-4 is exact and needs no amendment**, and the reviewer improved the argument: `1028 0` against
  `fac4896f` *proves* no pre-card line was removed, so the 14 lines need no individual check. Eleven
  layering symbols byte-identical by AST source-segment comparison.
- **The AC-5 amendment is accepted** — with the observation that adopting it **turns I-1 and M-1 into AC
  violations rather than declared bounds**, which is an argument for adopting it *and* fixing them in the
  same round rather than either alone.
- Two new default-deny shapes also red: a line-wrapped `Component(clues,…)`, and a `Component(solver,…)`
  made non-line-leading so `_COMPONENT_MACRO` cannot see it — caught downstream by the floor plus
  *"in the package, neither exempt nor paired"*.

### Certification — deferred a second time, with a hard stop

`8f-mutation: deferred(cost) -- gating finding present; certify on the stable cycle`

Justified by I-1 and not nominally: the remedy edits the `CASES` tuple and two tests **inside the five
`TestComponentMap_*` classes**, which is the exact selection the 16-mutant matrix was computed over, and
`CASES` is the literal data several arms read. The reviewer **refuses to propose a third deferral** —
cycle 3 must run it regardless of findings, because the cost argument only holds while the selection is
still moving. Four of sixteen cells were verified independently (M1, M2, M3, M14, all hold); the other
twelve were not re-fired and the domain is recorded cell-for-cell for cycle 3.

### Guardrails and scope

G-1/G-2/G-4/G-5/G-6 met, G-3 met with the import correction above. G-4 verified **both** directions:
one hunk, and CARD-264's `:46`/`:48`/`:50` defects present and untouched. **Scope gate: large but
in-scope, no escalation** — four paths, exactly the card's `Touches` plus the card file, zero components
changed behaviourally, `__version__` unchanged. It overlaps 2 of CARD-264's 5 paths, pre-declared
because CARD-264 came out of this card's own cycle 1, and non-colliding in content.

### F-107 sequencing — the reviewer's input, and it sharpens the case

**Urgent, not blocking.** The *value* in `_ADAPTERS` is right and matches the map; the prose around it
lies in all three places. The newly-enabled failure mode is the one I had not thought of: a reader who
follows this card's new pointer, finds a set of three under prose saying two, and concludes `admin` is
the erosion — **removing a correct entry**. That is worse than the stale count it replaced, and it is
reachable *only* because of this card. Land AC-7 with or immediately after CARD-261.

---

### [Fix round 2] `335c641e` — and the certification finally ran

Two paths, explicit pathspecs: `tests/test_cli.py` (+321/−12) and the card (+340/−5). **`CLAUDE.md` and
`src/` are untouched this round** — `git diff --stat feb3e6b5 HEAD -- CLAUDE.md src/` is empty, so G-4
holds **by construction** rather than by inspection. I verified the diff shape myself: since `feb3e6b5`
only `tests/test_cli.py` and the card changed.

**I-1(a) — the floor is gone and the corpus is pinned by value.** The total `>= 10` floor is replaced by
per-side floors (≥ 5 must-catch, ≥ 5 known-miss) **plus a by-value pin**, with the
`` (False, "`cli.py` is the only inbound adapter.") `` row asserted **first** so its deletion names that
sentence rather than a count. The acceptance test of the round, both states: the reviewer's padding
attack is **GREEN exit 0** against the file at `feb3e6b5` and **RED exit 1** after, with the message
*"the known-miss case carrying F-101's own wording has been removed from CASES … It is not
interchangeable with another case"*.

**And a detail worth keeping, because it is the difference between a message and a diagnosis.** The first
ordering fired the floor arm first, so the padding attack would have failed with `assert 4 >= 5` — a true
red that tells the reader nothing about *which* sentence went missing. Reordered so the sentence-naming
arm runs first. The matrix shows them as two independent cells, which is the evidence that the reorder
did not collapse one into the other.

**I-1(b) — `_adapter_counts` both widened and narrowed.** Widened on what a quantity is (numerals, number
words, and words implying one: `both`, `only`, `sole`, `a pair/trio/couple/handful of`, plus
`zero/eleven/twelve`) and **narrowed** on distance — the gap to the noun goes from two words to **one**.
The narrowing is what closes all three measured false positives, which is the part I would not have
predicted: the fix for *"See section 3 about inbound adapters"* is a tighter window, not a smarter
pattern. Validated against cycle 2's own 32-form sweep **before** editing: all 19 must-catch forms
caught, all 12 must-not-match clean. The planted prose that defeated it last round now reds naming
line 40, where it was green at `feb3e6b5` across both `test_cli.py` and `test_guard_integrity.py`.

**AC-5 adopted in the amended form**, with `amendment_verdict: ACCEPT` recorded and the superseded wording
kept beside it. The clause's two previously unhonoured places — M-1 and the CASES corpus — are now both
*asserted*, which is what the amendment demanded and the reason cycle 2 argued for doing it in the same
round.

**M-1 — both halves, and the reason the number gets no control is a measurement.** The *scoping* now has
a control derived from the package walk; the *number* is asserted to be a hole, with cycle 2's Plant A
committed as an arm. Why: measured with the worktree's `src` first on `sys.path`, **all three adapters
import the orchestrator** — so the walk says three, the C4 diagram pairs all three with a COMP id, and
the only statement that two of them are *the pipeline's* is ADR-0019's prose. A number restated from a
literal in the test file is not a control (ADR-0039/R2), and a parser over an ADR's prose would be a new
authority on a card already `LARGE_BUT_IN_SCOPE` under `escalation: continue`. **And the hole test can
itself fail** — rewording the count past its planter (`the two pipeline adapters` → `the 2 …`) reds with
*"the lie was not planted … so this test has stopped measuring anything"*. A bound that notices when it
stops measuring is the strongest form of the shape on this board.

### Certification — RUN, not deferred a third time

**20 mutants, 19 killed**, M14 the no-op cycle 2 proved by output (cited, not re-derived). Cycle 2's 16
cells all **re-fired cell for cell**, plus four new ones over this round's arms: the padding attack on
`CASES` (**two** independent FAIL cells, `:2191` the by-value pin and `:2201` the floor), `_ADAPTER_COUNT`
narrowed to numerals, the gap widened back to two words, and the scoping sentence removed from the
canonical map.

**Domain, in full:** **155 `ast.Assert` nodes** in `tests/test_cli.py` — an assert-node count, **not** a
collected-test count (138 at `feb3e6b5`); selection the five `TestComponentMap_*` classes, unrenamed;
**39 collected tests** (34 before); **72 arms reached**; SHIPPED **0 FAIL of 72 reached at pytest exit 0**,
re-run between mutants and held cell-for-cell; child instrumentation **off**, so `0 BLIND` means the
overlay never ran; every mutant line-count preserving; ANY-RED across both passes.

**The sibling card's trap reproduced here fifteen times.** Under the recording pass **16 of 20 mutants
exited 0, and 15 of those carry FAIL cells** — a test-level reading would have published **fifteen kills
as survivors**, including all four new ones. Every verdict is an arm-level attribution cross-read against
the re-raising pass (exit 1 on all 19). That is now measured on two cards independently, which makes it a
property of this instrument rather than an anecdote: **pytest's exit code is not a kill signal here.**

**Nothing left un-refired**, and the one wrinkle was disclosed: the matrix was fired twice because a
blank-line reflow after the first firing shifted linenos by 2–3. Verdicts were identical mutant for
mutant, and the reported figures are the **second** firing against the exact committed bytes.

### Bounds stated as incomplete, which is the right handling

1. **The number in "There are exactly two adapters (ADR-0019)" still has no authority** — asserted as a
   hole, not closed. Closing it needs an enumerable set for "ADR-0019's adapters"; the repo states it
   only in prose.
2. **A floor or by-value pin cannot be certified by weakening its own assertion** — the instrument
   refuses an edit that moves the target's assert topology, so those arms are certified by mutating the
   *artefact* they pin. Stated as a bound of the certification rather than left to be inferred, which is
   the distinction this board keeps asking for.
3. The forms `_adapter_counts` still misses are **deliberately open** — enumerations, "three inbound
   entry points", more than one intervening adjective, hyphenated adjectives, "adapters x2" — all
   committed as `False` cases and named in both docstrings.
4. **No pass-count figure is quoted** for the scoped runs, because this repo's `-q` output prints no
   pass-count line: pytest's exit code and `--collect-only` figures are reported instead of a number that
   cannot be shown. I hit the same wall at the fix-1 gate from the other direction, by truncating the
   summary line with my own `tail`.
5. F-107 and the `_ADAPTERS` prose untouched, nothing renamed — correct, they are CARD-264's, now live.

### [Build gate, fix 2] PASSED at `335c641e` — exit 0, 185 files, 8053 collected

Same impact-scoped selection as both earlier gates (the selector returns `FULL` for this change set, so
the two modellable paths are handed to it and it chooses 185 of 212). Board lock **not** taken; the lock
was redirected to a scratch path, and the script refuses to report a gate on a selection under 100 files
— a guard I added after my own zsh bug made a run of **nothing** exit 0 at the fix-1 gate.

**The collected count cross-checks the fix round for the second round running.** 8053 against fix 1's
8048 — a delta of **+5** — and `tests/test_cli.py` collects **135**, against 130 at `feb3e6b5`. Both
figures are exactly what the fixer claimed, derived by a different instrument.

**An unresolved tooling fact, stated as unresolved.** The pass/skip summary line appeared in the first
gate's output (`8009 passed, 16 skipped` at `604cc542`) and has **not** appeared in either later run,
including one where my filter explicitly matched `passed`. The fix-2 fixer hit the same thing from its
own side and concluded this repo's `-q` output prints no pass-count line; I have a counterexample, so
neither statement is safe. `pyproject.toml:89` sets `addopts = "-q"` and `tests/conftest.py:155` imports
`pytest_terminal_summary` from `tests/full_suite_lock.py` under its own name, which is the only custom
summary hook in the tree — but I have not established that it is the cause and will not claim it.

**What that means for every gate figure on this board, which is the part that matters:** a pass count
cannot be relied on, so the defensible figures are **pytest's exit code** plus a separate
`--collect-only` pass, which executes nothing. Both gates on this card are reported that way. Recorded in
`meta/kanban/backlog.md` as an `@ops` item rather than chased here.

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
**Review score:** 7.5 (c1) → 7.8 (c2) → **8.5 (c3, PASS with 7 bounds)**
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
- **AC-5** (guard, **amended in fix round 2** — review cycle 2 `amendment_verdict: ACCEPT`; the
  superseded wording and the evidence for the change are in `## Worktree notes — fix round 2`)
  *Given* all edits, *then* no component's **English description** is claimed to be controlled. The
  enumeration holds the **row set**, and the COMP-id and CAP-id columns are held against
  `meta/architecture/c4/components-CTX-001.puml`; what no artifact in this repository decides is
  whether "scores 0..100 from the solver's rung tags" is an accurate account of `difficulty.py`.
  Declare that bound in the control's docstring **and assert that it is a hole**. An honest bound is
  required; a premise that hides the hole is the thing this board gates on.

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

---

### [Review cycle 3] **8.5 — PASS with seven bounds.** Not an escalation

Report: `meta/review/20261022T111323Z-CARD-261-cycle3.yml`. `10 − 1.0 (I-1) − 0.15 (M-1) − 0.15 (M-2)
− 0.15 (M-3) = 8.5`, on **cycle 1's basis**, stated rather than re-based.

**The scoring question is answered, and the answer is uncomfortable in both directions.** Cycle 2's
re-base was not a denominator change at all — it was a different *kind* of number, an absolute artefact
judgement minus penalties versus penalty-only subtraction. The proof that they are incommensurable:
cycle 2's own 0.9 of deductions placed on cycle 1's basis gives **9.1**, which is plainly not what it
meant by 7.8. So the two cannot be reconciled arithmetically, and cycle 3 re-derived cycle 2 onto cycle
1's basis instead: **≈8.45**.

Which means **my suspicion was right and it cuts against me as well as for me.** The real cycle-1→2
improvement was ≈**+0.95**, not +0.3, and **cycle 2 probably should have passed** — the escalation I ran
on the `min_improvement` breach was triggered by an artefact of a changed scoring convention. And the
corollary the reviewer stated rather than buried: on one consistent basis **this round's improvement is
only ≈+0.05**, because `feb3e6b5` was already worth ~8.45. It scored the artefact, not the delta, which
is the right call — but the fix round the owner authorised bought about a twentieth of a point.

**And the pass straddles the bar by convention, not by evidence.** A reviewer re-basing the way cycle 2
did would score this artefact ≈9.0, land at **7.95**, and fail it. Cycle 3 passes it because the basis is
cycle 1's and because it weights its Important at 1.0 — *"a regression against the previous round, not a
standing gap"*. That is disclosed on the card so the owner is not told a cleaner story than the evidence
supports.

**I-1(a) and I-1(b) are closed, by execution.** The paraphrase attack I asked for
(`"cli.py is our sole inbound adapter."`) **reds** — the pin is to the **string**, and the failure
message answers the question in its own words: *"It is not interchangeable with another case."* Reversing
`CASES` reds nothing that should not. Both sides are pinned by value. And cycle 2's Plant G verbatim now
reds naming line 40.

### The one Important: the narrowing was a two-way regression, proved by one plant against two revisions

My priority-2 instinct was right, and the shape is worse than "it might have lost a catch" — it lost one
*and* gained a false positive:

| plant in `CLAUDE.md` | `feb3e6b5` | `335c641e` |
|---|---|---|
| `"three distinct inbound adapters"` — a real count, two adjectives | **RED** | **GREEN exit 0** |
| `"Only the adapters import the orchestrator"` — states no count | **GREEN** | **RED**, *"CLAUDE.md states a count of adapters again"* |

A 44-form sweep at the new boundary found **eight** forms missed-or-falsely-caught that are in no
committed case and declared nowhere: a two-gap-word class of five, a parenthetical, a comma, a line
break, plus the new false positive. The inline comment at `:1119` declares the cost with a **three**-word
example for a bound that shipped at **two**, and the class docstring's *"every shape … is a committed
case below"* is false for all eight. And the FP class the narrowing was *justified by closing* is
narrowed rather than closed — `"ADR-0019 section 2 adapters discussion"` still reds.

**Net reach is still better than `feb3e6b5`** — about eight new catch forms including this card's own
defect, three FPs closed — which is why it is a bound and not an escalation. **~4 lines to close.**

### The self-checking bound: half real, and the reviewer defeated the other half

The planter self-check **is real** — reword `two` → `2` and it reds with *"the lie was not planted … so
this test has stopped measuring anything"*, verified.

**Then it was defeated, by closing the hole the way a later card actually would.** A new test reading the
count out of the docstring and holding it to a walk-derived figure left
`test_the_maps_adapter_count_is_the_other_hole_that_stays_open` **GREEN at exit 0**, and a third plant
proved that closure genuine. The measured reason: the planted lie touches exactly three lines, **all at
indent 0**, and `_canonical_map(doc) == _canonical_map(lie)` is **True** — so the two defect arms are
*provably duplicates* of live arms and cannot fail for the stated reason. A **live planter wrapped around
two dead arms.** By contrast `test_a_wrong_description_is_the_one_hole_that_stays_open` uses a fabricated
map and **is** a real hole-assertion. That distinction is the most portable thing this cycle produced.

### Two methodological results worth more than any single arm

**The two new cells are independent — and the matrix could not have shown it.** `:2191` and `:2201` were
settled by **neutering each arm alone** under the padding attack: floor neutered → red at `:2191` naming
the sentence; pin neutered → red at `:2201` with `assert 4 >= 5`. Disjoint semantics. But M17 makes both
conditions true at once, so *"two cells on one mutant"* is equally consistent with **one mechanism
counted twice**. The fixer's claim was right and **its evidence was insufficient** — exactly the
distinction this card exists to enforce, applied to the card's own certification.

**The recording-pass trap is now a property, on three independent measurements across two cards.** Both
of cycle 3's recording-pass mutants exited **0** while carrying FAIL cells. The mechanism is in the
instrument's own contract: `Pass.RECORDING`'s handler does not re-raise, so a failing arm records FAIL
and the test completes. **Pytest's recording-pass exit code is not a kill signal.** Draft wording for
`tests/README.md` is in the report, to land on the next card touching that file.

**The artefact-mutation substitution is sound — mutating the artefact is the *better* experiment — with a
residual the fixer did not name:** M17 reaches only **2 of the 12** pin arms, and the padding plant is
precisely the attack artefact-mutation alone would never find.

### Residual minors

- **M-2: the pin list pins the wrong five.** Two of five known-miss slots are still padable, and the
  unpinned `"sourcing covers CAP-001 and nothing else."` is the **only** corpus detector of the COMP/CAP
  widening. Padded out, that widening still reds — via a neighbour whose message **misattributes the
  cause to `capabilities.yml`**. Exit 1 rather than exit 0, hence Minor. **One line to close.**
- **M-3: three figures do not reproduce.** `:2194` is **not an assert lineno** (the cell is `:2191`);
  "five strings by value" on the adapter corpus is **six**; "removes one line" is **twelve**.

### Gates and guardrails — all met

G-4 cost one command: `git diff --numstat feb3e6b5 335c641e` returns exactly two paths, neither
`CLAUDE.md` nor anything under `src/`; CARD-264's defects present and unedited at `:46`/`:48`/`:50`.
**AC-4 is `1337 0` against `fac4896f`** — zero deletions, which is the proof itself — and all **12**
lines removed this round were checked individually against `fac4896f` by fixed-string match and are all
card-introduced. Eleven layering symbols byte-identical by AST; `_ADAPTERS` at `:748`. ADR-0036/R4: three
hits, all U+2022 in `pdf_generator.py`, the declared exemption. All six guardrails MET.

**AC-5 bound by bound:** three of five satisfy the amended clause cleanly (English descriptions;
`admin`'s CAP pairing, held by an **equality**; the `CLAUDE.md` prose, both directions). The **forms**
bound is asserted for its committed subset and **overclaims**. The **number** is asserted only
nominally. AC-5 is MET as written, with bounds 4 and 5 on a weaker footing.

**Scope gate: `LARGE_BUT_IN_SCOPE` unchanged, no escalation.** Zero components touched behaviourally.
CARD-264's overlap is unchanged and slightly **better**, since this round's `CLAUDE.md` diff is empty.

### Sequencing — and one thing that got cheaper

**CARD-261 is safe to merge ahead of CARD-264**, and this round adds a *second* place that reds if
`_ADAPTERS` changes, which makes CARD-264's rename cheaper than it was when AC-7 was written. But land
AC-7 **next**, not later: the pointer this card creates leaves a window in which a reader could act on
the lying name and remove a correct entry.

**The reviewer also ruled out the cause I had guessed for the missing summary line.** It reproduced the
absence in a green **and** a red run and ruled the `full_suite_lock` hook **out** — it only calls
`write_line`. So the backlog item stands with one candidate eliminated and no cause claimed.

---

## [One-way sync, 2026-10-22] The two fix rounds' own notes, pulled from the card branch

The AC/EC/G gate found that **main's copy still carried the superseded AC-5** — no "English", no puml
named, and **no "and assert that it is a hole"** — while the amended wording, its
`amendment_verdict: ACCEPT` provenance and the superseded record existed only on the branch. The two
copies had diverged 617/533. Had the merge landed main's copy, the card would have closed against the
wording cycle 2 ruled insufficient and the amendment's audit trail would have been lost. AC-5 above is
now the amended wording, verbatim from the branch, and both fix rounds' own notes follow in full.

That is the board's one-way rule doing its job, and it is the second time this session it has mattered:
`meta/` is excluded from a card's commits so card prose cannot enter the branch it describes, which means
the orchestrator owes the pull every time. I missed it here until the gate asked.

## Worktree notes — fix round 1 (review cycle 1, 7.5/10, two Important findings)

Review cycle 1 is `meta/review/20261022T085642Z-CARD-261-cycle1.yml`. Both gating findings were
control-coverage defects of this card's own subject applied to this card's own output: a claim shipped
into `CLAUDE.md` that no control could fail on (F-101), and a column of the canonical map left unheld
although an enumerable authority for it exists in-repo (F-102). Both are closed with controls, not with
prose. Figures below were re-derived here, not carried over.

### Every orchestrator figure re-derived (two of them had already been corrected on this card)

| figure | method | result |
|---|---|---|
| 13 components from the walk | own `rglob` of `src/nonogram/**/*.py`, `parts[0]`, `__init__.py` folded into its directory | REPRODUCES — `admin analysis cli clues db difficulty errors export limits orchestrator solver sourcing web` |
| 10 COMP ids in the puml, across **two** macros | own parse: `Component(` at `:81 :83 :85 :87 :89 :91 :93 :95 :100` (nine) + `ComponentDb(` at `:102` (one) | REPRODUCES — a `Component(`-only parser misses COMP-010/`db/` |
| the module lives in the third argument | `"Python — cli.py"`, `"Python — web/ (stdlib http.server)"`, `"Python — db/ (SQLAlchemy, Alembic; Postgres)"` | REPRODUCES — trailing parenthetical is not part of the module |
| `errors.py`, `limits.py`, `analysis/` have no COMP id | set difference, walk minus puml pairing | REPRODUCES — id column is **10 of 13** by construction |
| CAP-001..CAP-007 at `:45 :64 :76 :98 :118 :130 :182` | `^\s*-\s+id:\s*(CAP-\d+)` over `capabilities.yml` | REPRODUCES — seven ids |
| `_ADAPTERS` is at `tests/test_cli.py:748` | read disk | REPRODUCES (the implementation's `:747` was wrong; the orchestrator's correction is right) |
| `wc -l` denominator | `find src/nonogram -name '*.py' \| xargs wc -l \| tail -1`, 60 files, one `total` line | **604cc542 → 46,289**; `fac4896f` via `git archive` into a scratch dir → **46,260**; numerator **29,358 at both**. Gap 29 = this card's own `+55/−26` on `__init__.py`. See F-104 below. |

### [Correction] The CAP↔module pairing DOES have an authority — it is held, not exempted

The orchestrator's brief measured the CAP column as having *no* authority pairing a capability to a
module, and directed that the pairing be declared an ADR-0039/R3 exemption. **That figure does not hold,
and I did not act on it.** `capabilities.yml` indeed pairs nothing — its CAP entries carry only
`name`/`description`/`events`/`commands`/`aggregates`/`stories`/`requirements`, no component or module
key (asserted by `test_the_capability_registry_pairs_no_module`). But the **C4 diagram** pairs them: the
*fourth* argument of a `Component*(` macro **leads** with the capability id —

```
Component(sourcing, "COMP-003 Grid Sourcing", "Python — sourcing/", "CAP-001: produces a ...")
```

— for exactly `sourcing`/`clues`/`solver`/`difficulty`/`export`, which is **exactly the five rows of the
canonical map that carry a CAP id**. Measured: the five pairs are `CAP-001..CAP-005` in map order, and
the map agrees with all five. So the CAP column is **held against an authority**, not exempted.

**The residual, measured at one.** `admin/`'s description names CAP-006 *mid-sentence*
(`"... and CAP-006 Book assembly (ADR-0033: ..."`), not as a leading prefix, so the parser reads
`admin/` as carrying no capability — and the canonical map's `admin/` row carries none either, so the two
agree. The hole is therefore exactly one component wide, and
`test_the_capability_pairing_reads_only_a_leading_cap_id` pins the loose-mention set to `["admin"]`: a
second component picking up that habit reds rather than dropping silently out of the column's coverage.

### F-101 — the uncontrolled component claim in `CLAUDE.md`, both halves

**(a) The claim is gone.** `CLAUDE.md:42` no longer states a count or names a module. It was:

> there are **three** inbound adapters (`cli.py`, `web/` and `admin/`), not one.

It is now: *"its adapter count. This file now states no count at all — which modules are adapters is a
fact of the canonical map, and the closed set the layering guard holds them to is `tests/test_cli.py`'s
`_ADAPTERS`."* The diff is **one line**, `@@ -42 +42 @@`, inside the layout block (G-4 verified below).

**(b) The bound now has a control, and so does the claim.** Two new controls, both of which *can* fail:

- `_adapter_counts` + `test_claude_md_states_no_count_of_adapters` — denies any count of adapters
  anywhere in `CLAUDE.md`, in words or digits, markdown emphasis stripped first (the shipped clause wrote
  `**three**`; a reader that only saw bare words would have passed the exact line it exists to refuse).
  **What state would make it red: a count in `CLAUDE.md`. Does that state exist today: it did** — this
  test was written before the `CLAUDE.md` edit and red on the shipped file, naming line 42 and quoting
  the clause (pasted below). It is green now.
- `TestComponentMap_WhatTheClaudeMdReaderAbsorbs` — **10 committed cases**, five that must be flagged and
  five that are known to be missed, asserted one-for-one with a `len(CASES) >= 10` floor so the corpus
  cannot silently shrink. Plus `test_prose_with_no_ids_is_the_declared_hole_and_an_id_closes_it`, which
  measures the hole's **edge**: cycle 1's prose plant is missed, and the same paragraph with **one**
  `COMP-001` added is caught. The hole is "prose carrying no id", not "prose".
- `test_each_disjunct_carries_a_case_the_other_does_not` settles what cycle 1 recorded as
  unestablished: a line only `_CLAUDE_MD_ROW` catches (`conftest.py      # shared fixtures`) and a line
  only `_COMPONENT_ID` catches (`The solver (COMP-005) is ...`), so each pattern has its own arm.

### F-102 — the id columns, held to an enumerable authority

New: `_c4_components` (the authority parser), `_capability_ids` (the second authority),
`_map_row_ids` (the map's structured columns), `_id_defects` (**ten** defect kinds). Nothing in
`_canonical_map`, `_map_defects`, `_component_modules` or the shipped test classes changed except
docstrings, so the mutants aimed at them still apply.

- **Unconditional, no authority needed** (plant D's half, done first as the brief required): an id
  claimed by two rows; an id the diagram enumerates that no row carries; an id no diagram enumerates; a
  CAP id the registry does not list.
- **Pairing, both directions:** a row whose `(COMP, CAP)` pair is not the diagram's; a module the diagram
  pairs that the package lacks; a component in the package that is neither exempt nor paired.
- **Default-deny on the authority (ADR-0039/R2, matching bound 3's precedent in-file):** any
  `Component*(` macro whose label is not a COMP id, whose technology argument yields no module (a hyphen
  where the em dash is), or that is a second declaration for a module the dict would otherwise overwrite
  silently — each returned as unanalysable and turned into a failure naming the line.
- **The R3 exemption is itself held.** `_WITHOUT_A_COMPONENT_ID = {"analysis", "errors", "limits"}`, and
  `test_the_three_modules_with_no_component_id_are_named_not_skipped` asserts four things rather than
  skipping: the set is those three names, each really is in the package, the diagram really pairs none of
  them, and the map really labels none of them. `_id_defects` then reds in **both** directions — a module
  that *gains* a diagram entry while the map shows no id, and one that *gains* an id in the map while the
  diagram pairs none (`test_an_exempt_module_the_diagram_starts_pairing_reds`,
  `..._the_map_starts_labelling_reds`).
- **The skip in `_map_row_ids` is a hand-off, not a hole.** It `continue`s on a line it cannot read,
  which is only safe while `_canonical_map` *denies* that same line.
  `test_the_two_row_readers_accept_exactly_the_same_lines` pins that the two patterns accept the same
  set, so narrowing either one reds.

**What remains unheld after this, each with a control asserting it IS a hole:**

| hole | why | the control that asserts it is a hole |
|---|---|---|
| a row's **English description** (AC-5) | no artifact in this repo decides whether "scores 0..100 from the solver's rung tags" describes `difficulty.py` | `test_a_wrong_description_is_the_one_hole_that_stays_open` — the literal CARD-261 defect (`difficulty.py ... not yet built (later card)`) passes **both** `_map_defects` and `_id_defects`, asserted |
| `admin/`'s **CAP-006 pairing** | named mid-description, not as a leading prefix | `test_the_capability_pairing_reads_only_a_leading_cap_id` pins the loose set to `["admin"]` |
| `CLAUDE.md` **prose with no ids** | `_claude_md_rows` is two patterns, neither of which reads prose | `TestComponentMap_WhatTheClaudeMdReaderAbsorbs`, 10 cases + the edge case |
| the **"two pipeline adapters"** count inside the *canonical map* | ADR-0019 is its authority; no artifact pairs a component with "is a pipeline adapter", so there is nothing to enumerate. It sits beside held rows (`cli.py`/`web/`/`admin/` all carry COMP ids held to the diagram) and beside `_ADAPTERS`, unlike `CLAUDE.md`'s count which sat alone | **none — declared, not closed.** Candidate for CARD-264's family |

### F-103 / F-104 / F-105 / F-106

- **F-103** — `_canonical_map`'s docstring no longer attributes the four-space rule to the `::` blocks:
  *"The indent is the whole rule: this parser never looks for `::`, so its reach is every
  four-space-indented line in the docstring, inside one of the literal blocks or not."*
- **F-104** — the denominator is corrected to **46,289** with the tree named. Re-derived both ways:
  `46,289` at `604cc542` (60 files, one `total` line, no `xargs` batching), `46,260` at `fac4896f` via
  `git archive` into a scratch dir; numerator `29,358` at both; `29358/46289 = 63.4%`, `29358/46260 =
  63.5%` — **63% on either denominator**. The 29-line gap is exactly this card's own `+55/−26` on
  `src/nonogram/__init__.py`, i.e. the figure was taken before the author's own edit. **It was never
  shipped into either map** — re-verified: `grep -nE "29,?358|46,?2[0-9][0-9]|63%" CLAUDE.md
  src/nonogram/__init__.py` returns nothing — so nothing rots; the correction is to this card's notes
  only.
- **F-105** — *"both copies had, in different places"* → *"both copies had **drifted**, in different
  places"*.
- **F-106** — decided together with F-101(b), as the brief asked. **Renamed** rather than narrowed:
  `test_claude_md_states_no_component_row_of_its_own` →
  `test_claude_md_carries_no_component_row_and_names_no_component_id`, and the failure message now says
  *"carries a component-map row again, or names a COMP-NNN id ... and the id ban is wider than the row
  ban on purpose"*. `_claude_md_rows`' docstring states the real breadth (any line of the whole file,
  prose and fenced code blocks included, no scoping to the layout block), says the id ban is deliberate
  and why, and names the control that pins it. Narrowing was rejected: an id in `CLAUDE.md` is the first
  column of a second copy, and the whole-file reach is what caught plant H below.

### Both states, demonstrated on disk — every plant restored and digest-verified

`cp -p` backups of all four files, `shasum -a 256` baseline, restore in an `EXIT` trap, verified by
**both** `shasum -a 256 -c` and `diff -q`; `git status --porcelain` afterwards showed only the four
intended modifications. SHIPPED re-run before and after. Selection: the five `TestComponentMap_*`
classes, 34 collected tests.

| plant | result |
|---|---|
| SHIPPED | **34 passed, exit 0** |
| **C** `solver/ COMP-005 CAP-003` → `COMP-004 CAP-009` | **RED, 4 keys:** `duplicate: ['COMP-004']`, `enumerated and no row carries: ['COMP-005']`, `not the diagram's: ['solver: the map says COMP-004/CAP-009, the diagram says COMP-005/CAP-003']`, `registry does not enumerate: ['CAP-009']` |
| **D** `clues.py COMP-004` → `COMP-005` | **RED, 3 keys:** `duplicate: ['COMP-005']`, `enumerated and no row carries: ['COMP-004']` (COMP-004 vanished), `not the diagram's: ['clues: the map says COMP-005/CAP-002, the diagram says COMP-004/CAP-002']` |
| **F** `difficulty.py CAP-004` → `CAP-009` (CAP-id existence) | **RED:** `not the diagram's: ['difficulty: ... COMP-006/CAP-009 ... COMP-006/CAP-004']`, `registry does not enumerate: ['CAP-009']` |
| **G** puml `"Python — cli.py"` → `"Python - cli.py"` (authority default-deny) | **RED:** `unanalysable Component declarations: ["81: cannot read a module from 'Python - cli.py'"]` plus `COMP-001` unenumerated and `cli` unpaired |
| **H** prose + **one** `COMP-001` appended to `CLAUDE.md` | **RED:** `['54: The pipeline runs one way. `cli.py` (COMP-001) is the only inbound adapter.']` |
| **I** the same prose with **no** id | **GREEN — the declared hole, exactly as measured** |
| **J** `_claude_md_rows` widened (`or "adapter" in line`) | **RED, 3 tests**, incl. *"the declared hole has closed -- _claude_md_rows now catches prose with no ids, so AC-3's bound and this class must be rewritten"* |
| **K** `_CLAUDE_MD_ROW` narrowed (`\.py` → `\.pyx`) | **RED:** *"these lines no longer read the way ... says: ['conftest.py      # shared fixtures']"* |
| SHIPPED again | **34 passed, exit 0**; restore verified OK on all four files |

F-101(a)'s own red, before the `CLAUDE.md` edit (TDD, the state existed on the shipped file):

```
AssertionError: CLAUDE.md states a count of adapters again. A corrected count is still an
uncontrolled copy of the canonical map's adapter rows (F-101): point at src/nonogram/__init__.py
and at tests/test_cli.py's _ADAPTERS instead. ["42: ... there are three inbound adapters
(cli.py, web/ and admin/), not one."]
```

### Mutants — the committed instrument, with the full domain

Instrument: `tests/kill_matrix.py` (documented in `tests/README.md` from line 453). No second instrument
written. Every mutant **line-count preserving**; `Edit` validated before application; `cp -p` backup with
`shasum -a 256` + `diff -q` verification in the instrument's own `finally`; **SHIPPED re-run between
mutants** and held cell-for-cell; aggregation **ANY-RED** across both passes.

**DOMAIN, stated in full because a per-assertion figure is meaningless without it:** 138 `ast.Assert`
nodes in `tests/test_cli.py` — an **assert-node count, not a collected-test count**; selection = the five
`TestComponentMap_*` classes; **34 collected tests**; **55 arms reached**; SHIPPED **0 FAIL of 55
reached** at **pytest exit 0**; **child instrumentation off**; both `Pass.RECORDING` and
`Pass.RERAISING` fired.

**16 mutants, 15 killed, 1 proven behaviour-equivalent — no survivors.**

| mutant | recording | re-raising | verdict |
|---|---|---|---|
| M1 `_CLAUDE_MD_ROW` **alone** (`\.py`→`\.pyx`) | 3 FAIL | 2 FAIL | KILLED |
| M2 `_COMPONENT_ID` **alone** (`COMP-\d`→`ZCOMP-\d`) | 4 FAIL | 3 FAIL | KILLED |
| M3 `_canonical_map`'s `body[0].isspace()` guard → `pass` | 4 FAIL | 4 FAIL | KILLED |
| M4 `_component_modules`' walrus `is not None` → `is not False` | 6 FAIL | 6 FAIL | KILLED |
| M5 puml declaration deny → `pass` | 1 FAIL | 1 FAIL | KILLED |
| M6 puml module deny → `pass` | 1 FAIL | 1 FAIL | KILLED |
| M7 puml duplicate-declaration deny → `pass` | 1 FAIL | 1 FAIL | KILLED |
| M8 `_id_defects` duplicate check `> 1` → `> 2` | 2 FAIL | 2 FAIL | KILLED |
| M9 `_id_defects` mispairing `!=` → `==` | 6 FAIL | 6 FAIL | KILLED |
| M10 CAP existence `- capability_ids` → `& capability_ids` | 5 FAIL | 5 FAIL | KILLED |
| M11 `_WITHOUT_A_COMPONENT_ID` gains `"clues"` | 6 FAIL | 4 FAIL | KILLED |
| M12 `_adapter_counts` emphasis strip `"*"` → `"+"` | 1 FAIL | 1 FAIL | KILLED |
| M13 `_PUML_CAPABILITY` `:` → `\.` | 3 FAIL | 3 FAIL | KILLED |
| M14 `_map_row_ids`' `isspace()` guard → `pass` | 0 FAIL | 0 FAIL | **EQUIVALENT — see below** |
| M15 real map plant C on `__init__.py` | 1 FAIL | 1 FAIL | KILLED |
| M16 real map plant D on `__init__.py` | 1 FAIL | 1 FAIL | KILLED |

**M1 and M2 fired separately and each killed independently.** Cycle 1 recorded as *not established*
whether `_CLAUDE_MD_ROW` and `_COMPONENT_ID` are independently controlled, because the reported matrix
fused them into a single arm. They are: each kills on its own, and
`test_each_disjunct_carries_a_case_the_other_does_not` is the committed arm for it.

**M14 is a no-op mutant, not a survivor, and that is proved rather than asserted** — the brief's standard
is that the two look identical. Proof: `_ROW_IDS` is anchored `^(?P<name>[A-Za-z_]...)`, so a body whose
first character is whitespace can **never** match it, and `_map_row_ids`' non-match path is `continue`.
Removing the guard therefore cannot change the output. Measured against the worktree's own package:
`_map_row_ids` returns **13 rows with the guard and the identical 13 tuples without it**
(`a == b` → `True`), and `_ROW_IDS.match` is `None` for every whitespace-leading probe. The asymmetry
with M3 is real and load-bearing: `_canonical_map`'s non-match path is **deny**, not `continue`, so there
the same guard *is* load-bearing and M3 kills.

### AC and guardrail status

- **AC-1, AC-2, AC-3** — MET, unchanged in substance. AC-3's *"exactly one place a row can drift from"*
  is now reached for the adapter count too, which cycle 1 found it was not: the inline clause is gone and
  `test_claude_md_states_no_count_of_adapters` keeps it gone.
- **AC-4 — MET, and its figure holds verbatim against the pre-card tree.**
  `git diff -U0 fac4896f -- tests/test_cli.py | grep -c '^-[^-]'` → **0**; `--numstat` → **`1028 0`**. So
  **no line that existed before this card is removed or rewritten**, and `_rank`, `_outward_imports`,
  `_MODULES`, `_component`, `_SHARED`, `_LAUNCH_EDGE`, `_ADAPTERS` are byte-identical to `fac4896f`.
  **No AC amendment is needed.** For completeness, against the *reviewed* commit the numstat is
  `781 14` — and each of those 14 removed lines was checked individually against
  `git show fac4896f:tests/test_cli.py` and is **absent** from it, i.e. all 14 are lines this card itself
  added (the F-103/F-106/F-102 docstring and rename edits). The constraint I worked under was exactly
  this: rewrite only lines this card introduced, never a pre-card line.
- **AC-5 — MET, and the bound is now narrow as well as honest.** The wording *"no component's
  **description** is claimed to be controlled"* still describes the shipped artefact, but it is no longer
  the whole of what the AC should say, because the id columns it silently covered are now held.
  **Proposed amended wording, for the owner:** *"AC-5 (guard) Given all edits, then no component's
  **English description** is claimed to be controlled. The enumeration holds the row set, and the COMP-id
  and CAP-id columns are held against `meta/architecture/c4/components-CTX-001.puml`; what no artifact in
  this repository decides is whether 'scores 0..100 from the solver's rung tags' is an accurate account
  of `difficulty.py`. Declare that bound in the control's docstring **and** assert that it is a hole."*
  The shipped artefact already satisfies the amended form.
- **G-1 — MET.** Zero removed pre-card lines (above); the 17 walk/layering guards pass inside the 130.
- **G-2 — MET.** No third copy. The new docstrings describe parsers and bounds; they restate no row. The
  two false-prose fixtures in `TestComponentMap_WhatTheClaudeMdReaderAbsorbs.CASES` are **counter**
  examples — statements false of this package — and are commented as such.
- **G-3 — MET.** No new import at all; `re` and `pathlib.Path` were already imported. `pyproject.toml`
  untouched.
- **G-4 — MET in both directions, verified rather than assumed.** `git diff -U0 604cc542 -- CLAUDE.md` is
  **one hunk, `@@ -42 +42 @@`**, inside the layout block. The three out-of-block defects are present and
  byte-identical: `:46` still cites `sourcing/random_grid.py`'s `validate_size`, `:48` still says "plus
  `pytest` as a dev-only extra", `:50` still says the cooperative timeout is "not yet enforced" and still
  cites 40×40. `grep -nio '[a-z]* [a-z]* adapters\?' CLAUDE.md` returns **nothing** now; before the fix
  it returned only `42: inbound adapters`, so the adapter-count guard needed no edit outside the block.
- **G-5 — MET.** `nonogram_poc` appears nowhere; `_refuse_unless_test_database` untouched; no database
  connected. Every pytest, script and mutation run exported
  `NONOGRAM_FULL_SUITE_LOCK=/tmp/card261-fix1.lock`; `meta/kanban/.full-suite.lock` was never read,
  written or created, and the full suite was never run.
- **G-6 — MET for what was scanned; no whole-tree claim.** Independent `ast` walk over **every** string
  literal in `src/nonogram/__init__.py`: **zero** codepoints in U+25A0..U+25FF and zero U+2022/U+2219.
  Separately, every added line of the src-side diff scanned for the same codepoints: **zero**. The only
  non-ASCII codepoint added anywhere is U+2014 (em dash), which the rule does not cover.
  `pdf_generator.py`'s three U+2022 remain the declared exemption and no clean-scan claim is made.

### Tests run (never the full suite — CARD-262 is live in a sibling worktree)

- `tests/test_cli.py` — **130 passed, exit 0** (was 107 at `604cc542`: **+23** tests).
- `tests/test_cli.py -k TestComponentMap` — **34 passed, 96 deselected, exit 0** (was 11: **+23**).
- `tests/test_guard_integrity.py` + `tests/test_suite_profile.py` + `tests/test_kill_matrix.py` —
  **606 passed, exit 0**. This is where ADR-0036/R4's and ADR-0039/R1–R3's own checks live, and
  `test_kill_matrix.py` is added to the subset because this round used that instrument.
- **Breadth, and the honest limit.** `scripts/impact_set.py --base $(git merge-base HEAD main)` returns
  **`FULL`** — the selection cannot be narrowed at all this round, so `make test-impact` would have run
  the whole suite and taken the lock. **I did not run it**, by instruction; the orchestrator runs the
  real gate. The narrowing that replaces it rests on a measurement: **`tests/test_cli.py` is the only
  test file that reads `CLAUDE.md`, `meta/architecture/c4/components-CTX-001.puml` **or**
  `meta/architecture/domain/capabilities.yml`** — every other file that mentions `CLAUDE.md` names it in
  prose only (`grep -rn 'CLAUDE.md' tests/ | grep -vE 'read_text|open\(|Path'` leaves nothing). So the
  new controls' *inputs* are fully covered by the subsets above; what is **not** covered is the
  transitive blast radius of `src/nonogram/__init__.py` being the package root, which is the gate's job.
- **Verified which package the suite loads**, because every row figure depends on it: a throwaway test in
  the worktree printed `nonogram.__file__` =
  `/Users/omelnikova/PycharmProjects/PythonProject4-card-261/src/nonogram/__init__.py` with **13** rows
  in the docstring. (An early ad-hoc probe of mine imported `nonogram` without the worktree's `src` on
  `sys.path` and silently read the editable install's copy, reporting 11 rows; the M14 equivalence proof
  was redone with the worktree's `src` first on the path. Disclosed because the wrong number appeared in
  my own intermediate output.)
- **No timing measured and no duration reported.**

### Not done, stated as incomplete

- **F-107 is untouched, deliberately.** `test_the_adapter_allowlist_is_closed_at_the_two_known_adapters`
  (`tests/test_cli.py:787`) asserts `_ADAPTERS == {"cli", "web", "admin"}` — **three** names under a name
  and a docstring that both say **two**. It is pre-existing, outside the diff, and scored zero, and the
  brief forbids editing it unilaterally. It now matters more, not less: F-101(a)'s fix points a reader of
  `CLAUDE.md` straight at `_ADAPTERS`, and that reader lands on a test whose name lies. **Owner's call:**
  a one-word rename here, or move it to CARD-264 with the other three stale citations.
- The **"two pipeline adapters"** count inside the canonical map is declared, not closed (table above).
- The accuracy of each row's **English description** is unheld by construction (AC-5) and asserted to be
  a hole; it is not reviewed here.

## Worktree notes — fix round 2 (review cycle 2, 7.8/10, FAIL on `min_improvement`)

Scope as the owner constrained it: **four items, nothing else**. I-1(a), I-1(b), the AC-5 amendment, and
M-1. F-107 and the three stale "two" claims around `_ADAPTERS` are untouched and stay on CARD-264 — no
rename anywhere; `CLAUDE.md`'s `:46`/`:48`/`:50` are untouched (G-4, verified below). No new control
outside those four items.

### What changed, per item

| item | the change | the control that now holds it |
|---|---|---|
| **I-1(a)** the padable `>= 10` floor | the total floor is **gone** from `test_every_case_reads_the_way_this_class_says_it_does`; the corpus is pinned **per side** (≥ 5 must-catch, ≥ 5 known-miss) and **by value** | `TestComponentMap_WhatTheClaudeMdReaderAbsorbs::test_the_cases_that_carry_the_claim_are_pinned_by_value` — five strings pinned by value, the `` (False, "`cli.py` is the only inbound adapter.") `` row **first**, so deleting it names *that sentence* and not a count |
| **I-1(b)** `_adapter_counts` could not match its own docstring's example | `_ADAPTER_COUNT` **widened** (a quantity is a numeral, a number word, or a word implying one — `both`, `only`, `sole`, `a pair of`, `a trio of`; `eleven`/`twelve`/`zero` added) and **narrowed** (the gap to the noun 2 words → 1 word, which is what closed the three measured false positives) | `::test_every_adapter_count_case_reads_the_way_this_class_says_it_does` over the new `ADAPTER_COUNT_CASES` (22 cases), plus `::test_the_adapter_count_cases_that_carry_the_claim_are_pinned_by_value` (≥ 12 deny / ≥ 10 allow, five strings by value) |
| **AC-5** | amended in the card's `## Acceptance criteria` section, with the superseded wording recorded here | the amendment's own new clause ("assert that it is a hole") is now satisfied in **both** places it was not: M-1 below, and the CASES corpus above |
| **M-1** the map's "two pipeline adapters" | **both halves**: a control for the scoping, derived from the package walk; and the number itself asserted as a hole | `TestComponentMap_EveryComponentIsListedExactlyOnce::test_the_maps_adapter_count_is_scoped_and_the_walk_is_why` and `::test_the_maps_adapter_count_is_the_other_hole_that_stays_open` |

### M-1 — which of the two the brief offered I chose, and why: **both**, and the measurement that decides it

The brief allowed either a control or the asserted-bound form. The deciding measurement, taken with the
worktree's own `src` first on `sys.path` (`nonogram.__file__` printed as the worktree copy, not the
editable install): **all three adapters import `orchestrator`.**

```
admin imports: ['admin','analysis','clues','db','difficulty','errors','export','limits','orchestrator','solver','sourcing']
cli   imports: ['difficulty','errors','export','orchestrator','web']
web   imports: ['difficulty','errors','export','limits','orchestrator','sourcing','web']
adapters importing orchestrator = ['admin','cli','web'] -> count 3
```

So the **number** cannot be derived: the package walk says three, the C4 diagram pairs all three with a
COMP id, and neither artefact says that two of the three are *the pipeline's*. ADR-0019 says it in prose
("today there are exactly two adapters and one option set", `0019-web-ui-component-boundary.md:32`),
which is not a set a runtime can enumerate — and a number restated from a literal in the test file is
not a control (ADR-0039/R2). A regex over an ADR's prose would be a new authority and a new parser on a
card already flagged **large but in-scope**, and the escalation route was `continue`, not `expand`.

What **is** derivable is the **scoping**, and that is the half that carries the reader risk: the count is
only true because `admin/` is outside ADR-0019's scope, and the walk is what makes that sentence
necessary. So `test_the_maps_adapter_count_is_scoped_and_the_walk_is_why` holds three things against the
package: that every adapter in `_ADAPTERS` imports the orchestrator, that there are **three** of them,
and that the map still carries the scoping clause. The number itself is then asserted to be a hole —
cycle 2's Plant A as a committed arm rather than as a reviewer's disk plant.

I also accept the reviewer's correction of my previous framing without reservation: the count did **not**
relocate from `CLAUDE.md`. `fac4896f` already carried both sentences; this card's edit inserted the word
"pipeline", narrowing a pre-existing claim. My earlier note implied otherwise and was wrong.

### Both states, demonstrated on disk — every mutation restored and verified two ways

`cp -p` backups of all three targets, a `shasum -a 256` baseline file, restore in a
`trap ... EXIT INT TERM`, verified by **both** `shasum -a 256 -c` and `diff -q` per path. Scratch in
`mktemp -d`. Every mutation target was inside `/Users/omelnikova/PycharmProjects/PythonProject4-card-261`;
the main checkout's `.venv/bin/python` was used as an **interpreter only** and no path under the main
checkout or `-card-262` was read, written or named as a target. Every invocation exported
`NONOGRAM_FULL_SUITE_LOCK=/tmp/card261-fix2.lock` and pytest announced the redirect in its own output
each time. No timing measured, no duration reported.

**The acceptance test for this round — the reviewer's padding attack, GREEN before and RED after.** The
attack is exactly the one cycle 2 executed: delete `` (False, "`cli.py` is the only inbound adapter.") ``
and substitute a near-duplicate must-catch row, tuple length still 10.

| state | file under test | result |
|---|---|---|
| **1** the attack on `HEAD` (`feb3e6b5`, the reviewed state) | `git show HEAD:tests/test_cli.py` | **GREEN, 34 passed, `PYTEST EXIT=0`** — Plant I reproduces cell for cell |
| **2** the same attack after the fix | the committed file | **RED, `PYTEST EXIT=1`**, `test_the_cases_that_carry_the_claim_are_pinned_by_value`, message: *"the known-miss case carrying F-101's own wording has been removed from CASES. That sentence is this card's own defect … It is not interchangeable with another case: ['docs/GENERATION_ALGORITHM.md   the generation pipeline', 'tests/README.md    the suite guide', '`difficulty.py` is not yet built.', 'sourcing covers CAP-001 and nothing else.']"* |

The by-value pin is deliberately asserted **before** the per-side floors: in the first arrangement the
floor fired first and the message said "the known-miss side has shrunk" (`assert 4 >= 5`), which is true
but says less than the sentence the attack deleted. Both arms exist; the one that names the sentence
goes first.

**I-1(b) — the planted prose, GREEN before and RED after.** Plant G verbatim, as running prose
immediately under `CLAUDE.md`'s `## Architecture` heading:
*"Both inbound adapters import the orchestrator; `cli.py` is the only inbound adapter that parses argv."*

| state | result |
|---|---|
| **3** the plant on `HEAD` | **GREEN, `PYTEST EXIT=0`** over `tests/test_cli.py` **and** `tests/test_guard_integrity.py` (261 tests) — Plant G reproduces |
| **4** the same plant after the fix | **RED, `PYTEST EXIT=1`**, `test_claude_md_states_no_count_of_adapters`, naming the line: *"CLAUDE.md states a count of adapters again … ['40: Both inbound adapters import the orchestrator; cli.py is the only inbound adapter that parses argv.']"* |

**M-1 — the scoping control, GREEN before and RED after.** The scoping sentence
(*"… not a count of every entry point in the tree: ``admin/`` is a third one, outside ADR-0019's scope as
written."*) replaced, line count preserved, by a sentence that drops the scope.

| state | result |
|---|---|
| **5a** on `HEAD` | **GREEN, `PYTEST EXIT=0`** (34 tests) — the count had no control of any kind |
| **5b** after the fix | **RED, `PYTEST EXIT=1`**, `test_the_maps_adapter_count_is_scoped_and_the_walk_is_why`: *"the canonical map states a count of adapters and no longer scopes it. Two is ADR-0019's figure; the walk finds three adapters, all of which import the orchestrator, so the unscoped sentence is false of this tree — restore the scope or drop the count"* |
| **6a** Plant A after the fix (`two` → `five`, both sentences) | **GREEN, `PYTEST EXIT=0`** (39 tests) — **as asserted.** This is the hole, and `test_the_maps_adapter_count_is_the_other_hole_that_stays_open` is the arm that says so |
| **6b** the count reworded past the planter (`the two pipeline adapters` → `the 2 pipeline adapters`) | **RED, `PYTEST EXIT=1`** — *"the lie was not planted … so this test has stopped measuring anything"*. The hole-assertion is not a test that cannot fail |

**The adapter corpus' own pins, both demonstrated RED.** The reach control is covered by M18/M19 in the
matrix; these are the by-value pins over `ADAPTER_COUNT_CASES` itself, each by the same substitution
attack that defeated the old floor — one case replaced, the tuple's length unchanged.

| state | result |
|---|---|
| **7a** the false-positive case *"See section 3 about inbound adapters."* replaced by another allow-side row | **RED, `PYTEST EXIT=1`**, `:2323`: *"the false-positive case 'See section 3 about inbound adapters.' has been removed from ADAPTER_COUNT_CASES. Each of these red under the two-word bound this guard used to carry, and a deny-side guard that reds on a sentence stating no count is one the next card switches off."* |
| **7b** the F-101 deny case replaced by another deny-side row | **RED, `PYTEST EXIT=1`**, `:2307`: *"the case carrying F-101's own wording has been removed from ADAPTER_COUNT_CASES … so it is the one case"* |

### What state would make each control red, and whether that state exists today

| control | red when | exists today |
|---|---|---|
| `test_the_cases_that_carry_the_claim_are_pinned_by_value` | any of the five pinned strings leaves `CASES`, or either side drops below 5 | **No** — demonstrated by state 2 above, which is the only way to produce it |
| `test_every_case_reads_the_way_this_class_says_it_does` | `_claude_md_rows`' reach moves in either direction | **No** (cycle 2's Plant B produced it) |
| `test_every_adapter_count_case_reads_the_way_this_class_says_it_does` | `_ADAPTER_COUNT` narrows past a quantifier form or widens onto a sentence stating no count | **No** — M18 and M19 in the matrix below are exactly those two directions |
| `test_the_adapter_count_cases_that_carry_the_claim_are_pinned_by_value` | the F-101 sentence or any of the three false-positive cases leaves `ADAPTER_COUNT_CASES` | **No** |
| `test_claude_md_states_no_count_of_adapters` | `CLAUDE.md` states a quantity of adapters again, in any committed form | **No** — state 4 is the only way to produce it; `_adapter_counts` on the shipped file returns `[]` under the new pattern as it did under the old |
| `test_the_maps_adapter_count_is_scoped_and_the_walk_is_why` | `admin` stops importing the orchestrator, `_ADAPTERS` stops being three, or the scoping clause leaves the docstring | **No** — state 5b |
| `test_the_maps_adapter_count_is_the_other_hole_that_stays_open` | the count **gains** a control, or the map rewords the count past the planter | **No** — state 6b. It reds *when the hole closes*, which is what makes it a bound and not a wish |

### The amended AC-5, written onto the card, with the evidence

Adopted this round, as cycle 2's `amendment_verdict: ACCEPT` directs and for the reason it adds: adopting
it turns I-1 and M-1 into **AC violations** rather than declared bounds, which is why it belongs in the
round that fixes them. The card's `## Acceptance criteria` section now reads the amended form; the
superseded wording is kept here so the change is auditable:

> **Superseded (as created):** *"AC-5 (guard) Given all edits, then no component's **description** is
> claimed to be controlled. The enumeration can hold the **row set**; it cannot judge whether 'scores
> 0..100 from the solver's rung tags' is an accurate account of `difficulty.py`. Declare that bound
> explicitly in the control's docstring."*

Three substantive changes, each with its evidence:

1. **"description" → "English description".** Cycle 1's F-102 was possible *only* because the word
   "description" silently covered a structured identifier with an authority: a wrong COMP id, a
   `CAP-009` belonging to nothing, and two rows claiming `COMP-005` were all green under an AC that
   said descriptions are unheld. Naming the English makes that fold impossible to repeat.
2. **The authority file is named** — `meta/architecture/c4/components-CTX-001.puml` — so the AC states
   where the id columns are held rather than leaving a reader to find out.
3. **"and assert that it is a hole"** promotes ADR-0039/R3 from a practice this card chose into a
   requirement of the AC. That clause is the one that makes this round's work an AC obligation:
   it was honoured for the English description
   (`test_a_wrong_description_is_the_one_hole_that_stays_open`) and for `admin/`'s CAP-006
   (`test_the_capability_pairing_reads_only_a_leading_cap_id`), and it was **not** honoured for the
   adapter count (M-1) nor for the CASES corpus (I-1a) — both closed above.

**Checked against what I built.** AC-5 as amended: no component's English description is claimed to be
controlled; the row set is held; both id columns are held against the named puml; the bound is declared
in `_map_defects`' docstring **and** asserted by `test_a_wrong_description_is_the_one_hole_that_stays_open`.
The two bounds the clause newly reaches are now asserted as well — the adapter count by
`test_the_maps_adapter_count_is_the_other_hole_that_stays_open`, and the corpus' own extent by
`test_the_cases_that_carry_the_claim_are_pinned_by_value`. **MET, and met in the amended form.**

### AC and guardrail status after this round

- **AC-1, AC-2, AC-3 — MET, unchanged in substance.** No control they name was edited; the five
  `TestComponentMap_*` classes keep their names and their existing methods.
- **AC-4 — MET, figures as cycle 2 settled them and not re-derived.** `0` removed lines and `1028 0`
  against `fac4896f` are the cycle-2 figures and I did not reproduce them; what I checked is that this
  round preserves the property: **this round removes one line this card itself added** (the
  `assert len(self.CASES) >= 10, self.CASES` floor, added at `feb3e6b5`) and no pre-card line. Measured:
  `git diff -U0 fac4896f -- tests/test_cli.py | grep -c '^-[^-]'` → **0**.
- **AC-5 — MET in the amended form** (above).
- **G-1 — MET.** Zero removed pre-card lines; the layering guard's symbols are untouched. My one new
  read of the walk (`_imported_components` over `_MODULES`, in the M-1 scoping control) **consumes** the
  existing helpers and changes none of them: no rule relaxed, retargeted or deleted.
- **G-2 — MET.** No third copy. `ADAPTER_COUNT_CASES`' deny-side rows are *counterexamples* —
  statements this repository must not make — and the two that resemble the map's own wording
  (`the two pipeline adapters import ``orchestrator```) are there to be **refused**, not restated. The
  new docstrings describe patterns, authorities and bounds; they quote no row.
- **G-3 — MET.** No new import at all this round; `pyproject.toml` untouched.
- **G-4 — MET, and this round does not touch `CLAUDE.md` at all.** `git diff fac4896f HEAD -- CLAUDE.md`
  is unchanged from cycle 2's verified state (one hunk, `@@ -42,11 +42 @@`); this round's diff for
  `CLAUDE.md` is **empty**, so `:46`'s `validate_size` citation, `:48`'s "dev-only extra" and `:50`'s
  "not yet enforced"/40×40 are byte-identical by construction rather than by inspection.
- **G-5 — MET.** `nonogram_poc` appears nowhere in this round's diff; `tests/conftest.py` and
  `tests/database_guard.py` untouched; no database connected. Every pytest, script and matrix invocation
  exported `NONOGRAM_FULL_SUITE_LOCK=/tmp/card261-fix2.lock`, pytest announced the redirect each time,
  and `meta/kanban/.full-suite.lock` was never read, written or created. The full suite was never run.
- **G-6 — MET trivially this round: `src/nonogram/__init__.py` is not edited.** This round's only source
  change is `tests/test_cli.py` plus the card, so ADR-0036/R4's live surface is unchanged from the state
  cycle 2 verified. No whole-tree clean claim is made.

### Figures I did NOT re-derive, because cycle 2 settled them

As instructed. AC-4's `0` / `1028 0` against `fac4896f` (and that the `1028 0` is itself the proof no
pre-card line was removed); the five-row CAP agreement as a convention with the loose set `["admin"]`;
the ten defect kinds as ten behaviours with all 90 ordered pairs separable; M14 a no-op and M3 not
(0 → 22 unanalysable versus 13 cell-identical tuples). None of them is restated as mine.

### Certification — `8f-mutation` RUN, not deferred a third time

Cycle 2 refused to propose a third deferral, and this round does not ask for one. The matrix was
**re-fired in full over the changed selection**, including four new mutants over the arms this round
adds, so cycle 3 inherits a certified selection rather than one that moved under a certified matrix.

Instrument: the committed `tests/kill_matrix.py` (contract in `tests/README.md` from line 453). **No
second instrument written.** Every mutant line-count preserving; `Edit` validated before application;
assert topology re-derived from each mutated file; `cp -p` backup with `shasum -a 256` + `diff -q` in the
instrument's own `finally`; **SHIPPED re-run between mutants** and held cell-for-cell; aggregation
**ANY-RED** across both passes.

**DOMAIN, stated in full because a per-assertion figure is meaningless without it:**
**155 `ast.Assert` nodes** in `tests/test_cli.py` — an **assert-node count, not a collected-test count**
(138 at `feb3e6b5`, so +17 this round); selection = the **five `TestComponentMap_*` classes**, unchanged
and unrenamed; **39 collected tests** (34 at `feb3e6b5`); **72 arms reached**; SHIPPED **0 FAIL of 72
reached** at **pytest exit 0** with 39 collected; **child instrumentation OFF**, so the `0 BLIND` reading
means *the overlay never ran*, not that no arm is blind, and an arm executing only inside a child records
nothing; both `Pass.RECORDING` and `Pass.RERAISING` fired.

**20 mutants, 19 killed, 1 the known no-op — no survivors.**

| mutant | recording | re-raising | verdict |
|---|---|---|---|
| M1 `_CLAUDE_MD_ROW` alone (`\.py`→`\.pyx`) | 3 FAIL, exit 0 | 2 FAIL, exit 1 | KILLED |
| M2 `_COMPONENT_ID` alone (`COMP-\d`→`ZCOMP-\d`) | 4 FAIL, exit 0 | 3 FAIL, exit 1 | KILLED |
| M3 `_canonical_map`'s `isspace` guard → `pass` | 5 FAIL, exit 0 | 5 FAIL, exit 1 | KILLED |
| M4 `_component_modules` walrus `is not None`→`is not False` | 8 FAIL, exit 1 | 7 FAIL, exit 1 | KILLED |
| M5 puml declaration deny → `pass` | 1 FAIL, exit 1 | 1 FAIL, exit 1 | KILLED |
| M6 puml module deny → `pass` | 1 FAIL, exit 1 | 1 FAIL, exit 1 | KILLED |
| M7 puml duplicate-declaration deny → `pass` | 1 FAIL, exit 1 | 1 FAIL, exit 1 | KILLED |
| M8 `_id_defects` duplicate `> 1` → `> 2` | 2 FAIL, exit 0 | 2 FAIL, exit 1 | KILLED |
| M9 `_id_defects` mispairing `!=` → `==` | 7 FAIL, exit 0 | 7 FAIL, exit 1 | KILLED |
| M10 CAP existence `- capability_ids` → `&` | 6 FAIL, exit 0 | 6 FAIL, exit 1 | KILLED |
| M11 `_WITHOUT_A_COMPONENT_ID` gains `"clues"` | 7 FAIL, exit 0 | 5 FAIL, exit 1 | KILLED |
| M12 `_adapter_counts` emphasis strip `"*"`→`"+"` | 1 FAIL, exit 0 | 1 FAIL, exit 1 | KILLED |
| M13 `_PUML_CAPABILITY` `:` → `\.` | 4 FAIL, exit 0 | 4 FAIL, exit 1 | KILLED |
| M14 `_map_row_ids`' `isspace` guard → `pass` | 0 FAIL, exit 0 | 0 FAIL, exit 0 | **the known no-op** (below) |
| M15 real map plant C on `__init__.py` | 2 FAIL, exit 0 | 2 FAIL, exit 1 | KILLED |
| M16 real map plant D on `__init__.py` | 2 FAIL, exit 0 | 2 FAIL, exit 1 | KILLED |
| **M17 the padding attack on `CASES`** (new) | 2 FAIL, exit 0 | 1 FAIL, exit 1 | KILLED — `:2191` the F-101 by-value pin **and** `:2201` the known-miss floor, two independent arms |
| **M18 `_ADAPTER_COUNT` narrowed to numerals only** (new) | 1 FAIL, exit 0 | 1 FAIL, exit 1 | KILLED — `:2285`, the adapter corpus |
| **M19 `_ADAPTER_COUNT` gap widened back to two words** (new) | 1 FAIL, exit 0 | 1 FAIL, exit 1 | KILLED — `:2285`, the false-positive cases |
| **M20 the scoping sentence removed from the canonical map** (new) | 1 FAIL, exit 0 | 1 FAIL, exit 1 | KILLED — `:1614`, M-1's scoping control |

**M14 is the no-op cycle 2 proved, and I do not re-prove it.** Cycle 2 established it by output
comparison rather than by a matrix cell — `_map_row_ids` returns 13 cell-for-cell identical tuples with
and without the guard, because `_ROW_IDS` is anchored and the non-match path is `continue` — versus M3's
0 → 22 unanalysable, where the non-match path is deny. Its 0/0 here is consistent with that and is not
independent evidence of it.

**M17 is the acceptance test of this round, measured arm-level.** Its two recording-pass FAIL cells are
`:2191` (the by-value pin on the F-101 sentence) and `:2201` (the known-miss floor) — two arms, so the
pin and the floor are not one control wearing two names: the pin names the sentence, the floor catches a
shrinkage that leaves the sentence in place. Under the re-raising pass only `:2194` reds, because that
pass short-circuits at the first failing assert, which is exactly the attribution the recording pass
exists to make.

**The trap the brief carried from the sibling card reproduced here, 15 times.** Under the recording pass
**16 of the 20 mutants exited 0**, and **15 of those 16 carry FAIL cells** (all but M14). A test-level
reading of the recording pass would therefore have published fifteen killed mutants as survivors —
including every one of this round's four new ones. The kill verdicts above are arm-level attributions
from the matrix, cross-read against the re-raising pass's true propagation (exit 1 on all 19), and at no
point substituted with pytest's own exit code.

**Restore verification at exit:** `shasum -a 256 -c` over the two mutated paths → 2× OK; `diff -q`
against an independent pre-matrix copy of `tests/test_cli.py` → identical; `git status --porcelain`
shows only `meta/kanban/cards/CARD-261.md` and `tests/test_cli.py` modified (plus the two untracked
review reports, which are the reviewer's); `git diff --stat HEAD -- CLAUDE.md src/` is **empty**.

**Nothing left un-refired.** All 16 of cycle 2's cells were re-fired cell for cell, plus 4 new ones. No
cell is reported from cycle 2's numbers.

**Disclosed, because the linenos above have to match the committed bytes:** the matrix was fired twice.
The first firing was against a state two blank lines and one reflowed docstring paragraph earlier than
the commit, so its cells carried linenos 2–3 higher. The verdicts were **identical mutant for mutant**
(19 killed, M14 0/0; the same FAIL counts in both passes), and the figures reported above are the
**second** firing, taken against the exact bytes committed — `shasum -a 256 -c` over both mutated paths
→ 2× OK, and `diff -q` against an independent pre-matrix copy → identical. Nothing in this table comes
from the earlier run.

### Tests run (never the full suite — CARD-262 is live in a sibling worktree)

Scoped exactly as the brief binds: `tests/test_cli.py`, `tests/test_guard_integrity.py`,
`tests/test_suite_profile.py`, `tests/test_kill_matrix.py`. The main checkout's
`.venv/bin/python` was used **as an interpreter only**, with `cwd` = this worktree.

- `tests/test_cli.py` — **135 collected, exit 0** (130 at `feb3e6b5`: **+5**).
- `tests/test_cli.py -k TestComponentMap` — **39 collected, exit 0** (34 at `feb3e6b5`: **+5**). The
  five class names are unchanged; the five new methods sit inside two of them.
- The four scoped files together — **741 collected, exit 0** (`tests/test_cli.py` 135,
  `tests/test_guard_integrity.py` 131, `tests/test_kill_matrix.py` 76,
  `tests/test_suite_profile.py` 399). The collection figure comes from `--collect-only`, because this
  repository's `-q` run prints no pass-count line of its own; the verdict I report is pytest's **exit
  code**, and I do not quote a pass count I cannot show. Re-run against the exact committed bytes:
  `SUBSET_EXIT=0`.
- `tests/test_guard_integrity.py` was run at the fixed state **and** under the CLAUDE.md plant
  (state 3/4 above), which is the file cycle 2 corrected me about: it *does* read `CLAUDE.md`, at
  `:80`/`:2840`, in the Commands section around line 10 — nowhere near this card's single hunk at
  line 42. I carry that correction rather than repeating the claim it falsified; this round does not
  touch `CLAUDE.md` at all.
- Every invocation exported `NONOGRAM_FULL_SUITE_LOCK=/tmp/card261-fix2.lock`, and pytest announced the
  redirect in its own output each time. `meta/kanban/.full-suite.lock` was never read, written or
  created. `make impact-set` / `make test-impact` were not used.
- **No timing measured and no duration reported.**
- **Which package the suite loads, confirmed again** because every structural figure depends on it: the
  `python -I` probes printed `nonogram.__file__` =
  `/Users/omelnikova/PycharmProjects/PythonProject4-card-261/src/nonogram/__init__.py`, with the
  worktree's `src` first on `sys.path`. No ad-hoc `python -c "import nonogram"` was trusted for any
  figure — that is the editable-install trap, and it reports the pre-card 11-row map.

### Not done, stated plainly as incomplete

- **F-107 and the three stale "two" claims around `_ADAPTERS` are untouched**, by instruction: the
  module comment ("this set is closed at two names"), the test name
  (`test_the_adapter_allowlist_is_closed_at_the_two_known_adapters`) and its docstring's first line.
  Nothing renamed. They stay on **CARD-264**. My own M-1 control reads `_ADAPTERS` and asserts its
  members all import the orchestrator; it does not edit the set, the comment, the name or the docstring,
  and it adds a second place that will red if the set changes — which is a reason CARD-264's rename is
  cheap, not a reason to do it here.
- **The number in "There are exactly two adapters (ADR-0019)" still has no authority**, and that is now
  asserted rather than declared (M-1 above). Closing it would need an enumerable set for "ADR-0019's
  adapters"; the only statement of it in the repo is ADR-0019's prose. Not attempted this round: it is a
  new authority and a new parser, and the escalation route the owner picked was `continue`.
- **A floor or a by-value pin cannot be certified by weakening the assertion itself.** The instrument
  refuses an edit that moves the target's assert topology, "each node's lineno *and* what the assertion
  at it says", so a mutant that neuters an assert inside `tests/test_cli.py` is refused by design. Those
  arms are therefore certified by mutating the **artefact** they pin (M17 for `CASES`, M20 for the
  docstring's scoping sentence), which is the right direction but is worth stating as a bound rather
  than leaving it to be inferred from the mutant list.
- **The forms `_adapter_counts` still misses are not closed, deliberately** — an enumeration ("The
  adapters: cli, web, admin"), a count under another noun ("three inbound entry points"), a number more
  than one adjective away, a hyphenated adjective, "adapters x2", "adapters number three". Every one is
  a committed `False` case, and the helper's docstring and the test's docstring both now say so. The
  brief's standard was that the control's name, message and docstring state the shape it actually has,
  not that every form be caught.
- **The full suite and the real impact gate were not run**, by instruction. `scripts/impact_set.py`
  returns `FULL` for this card, so the coordinator's gate is the only instrument that can cover
  `src/nonogram/__init__.py`'s transitive blast radius — and `src/` is untouched this round, so the
  radius is unchanged from the gate that already passed at `feb3e6b5`.
- **M-2's three non-reproducing figures** (the gate-breadth measurement, the diff-hunk notation
  `@@ -42,11 +42 @@`, the `_id_defects` taxonomy grouping) are **not** corrected in the fix-round-1 notes
  above — those notes are the record of what that round claimed. The corrections are carried here
  instead: the gate-breadth sentence was false as stated (two files read `CLAUDE.md`), the hunk header is
  `@@ -42,11 +42 @@`, and two of the four `_id_defects` kinds the taxonomy sentence called
  authority-free — "a COMP id the diagram does not enumerate" and "a COMP id the diagram enumerates that
  no row carries" — are set differences against `authority` and do need it. Only the duplicate count over
  `rows` and the CAP-registry membership test hold with an empty authority.

---

### [AC/EC/G verification gate] **GATE PASSED** — and it found two merge preconditions the card did not carry

**The phantom-control check cleared first**, which is the one this station exists for. All five named
classes re-derived **per class by direct `--collect-only`**, not by arithmetic — including the `17` I had
handed over as arithmetic, which holds: 4 / 6 / 3 / **17** / 9 = **39**, matching the whole-selection
figure. `tests/test_cli.py` collects 135; AC-4's named parametrisation collects 11; G-6's control
collects 1. **No pytest exit-5 anywhere and no named class that exists nowhere** — the CARD-221 /
CARD-206 failure mode is absent. Package identity confirmed in an isolated `python -I`:
`nonogram.__file__` is the worktree's copy with **13 rows**, so the editable-install trap is excluded
from every figure.

**The card declares no ECs** — stated rather than left blank.

**Every control that admits a failing state was made to fail.** Plants: a real module
`src/nonogram/planted_component.py` (reds naming `planted_component`), a real planted row, a row pasted
into `CLAUDE.md` (reds naming `'55: cli.py COMP-001 the only inbound adapter'`), a wrong COMP id (reds
naming *"the map says COMP-004/CAP-003, the diagram says COMP-005/CAP-003"*), and a planted U+2022 in
`src/nonogram/__init__.py`'s docstring. Mutants: `_rank` degenerated to one rank, `_outward_imports`'
`<=` relaxed to `<` (**3 of 10** forbidden-edge params red — a live control over precisely the relaxation
G-1 forbids), and `_map_defects`' `> 1` → `> 0`.

**AC-4 got an independent structural re-derivation** rather than carrying cycle 3's: AST source-segment
comparison against `fac4896f` shows **17 symbols byte-identical**, the four walk guard functions
byte-identical, and the `parametrize` decorator carrying the ten forbidden edges byte-identical; numstat
`1337 0`; the diff is exactly two hunks — `+import re` at line 14 and a 1336-line append after line 1081.

**G-6 was re-derived by the gate's own AST scan over all 60 files** under `src/nonogram/**`: exactly
three hits, all U+2022, all at `admin/pdf_generator.py:321`, the declared exemption. No whole-tree claim.

### Two findings of the gate's own, beyond what cycle 3 named

**AC-3 — MET with a bound cycle 3 did not name.** `test_claude_md_points_at_the_canonical_map` and its
sibling assert only that the substrings occur **somewhere in `CLAUDE.md`**. Demonstrated: with line 42
stripped of both pointer sentences and the two tokens moved into an **HTML comment in the Commands
section**, all 39 tests pass at exit 0. So AC-3's *"points at `src/nonogram/__init__.py`"* half is
**tight in fact today** — exactly one occurrence of each token, both inside line 42 — **and loose in
form**. ~2 lines to close. This is the same shape as the card's own subject: a claim held by a
whole-file substring rather than at the place it is made.

**AC-5 — and the gate drew a line cycle 3 left implicit.** It verified against the **amended** wording
and separates two readings: AC-5's *own text* obliges one declared-and-asserted bound (the English
description), and that one has a control the gate made fail — so **AC-5 is MET on its text**. But the
card extended the clause to all five bounds, and under that reading **the number bound is asserted only
nominally, and the gate says plainly that a nominal assertion does not satisfy "assert that it is a
hole"**. Its evidence is four-fold and decisive: `_canonical_map(doc) == _canonical_map(lie)` **and**
`_map_row_ids(doc) == _map_row_ids(lie)` are both **True**, so the two defect arms evaluate the *same
values* as the live arms; the test red on every **unrelated** defect planted (module, row, wrong COMP id,
the `>1→>0` mutant); and it **stayed GREEN at exit 0 while the map stated a false count** (`two` → `five`
in both sentences, 39 passed). Its docstring's *"A later card that gives the count an authority will red
here and delete this test deliberately"* is **false for every mechanism anyone would actually use**.

**And three committed sentences overclaim, with the arithmetic.** `tests/test_cli.py:1109-1111` says
cycle 2's 32 forms are *"every one of them a committed case"* — the corpus has **22**, and of the **25**
forms recoverable from cycle 2's report **7 are represented by no case**; the universal is also
arithmetically impossible as written. `:1125`'s declared cost names `"three distinct inbound process
adapters"` while the real boundary is **one word narrower** — `'three distinct inbound adapters'` evades
the shipped pattern. And the card at `:983` claims every listed form is a committed `False` case;
**`'adapters x2'` is not in the file**.

**A correction to the bound I recorded from cycle 3.** I wrote that all five two-adjective forms were
caught at `feb3e6b5`. **It does not reproduce:** three were (`three distinct inbound adapters`,
`2 distinct inbound adapters`, `three inbound python adapters`); **`Both known inbound adapters` and
`a pair of distinct inbound adapters` were missed then too**, because `both`/`a pair of` were not in the
old alternation. So the regression is **three** forms, and the other two are **pre-existing gaps** — a
distinction that matters for CARD-265, where fixing a regression and closing a pre-existing gap are
different jobs.

### The seven bounds the owner accepts by merging

| # | What is being accepted | Status |
|---|---|---|
| 1 | A plain count of adapters standing **two adjectives** from the noun can go back into `CLAUDE.md` unnoticed; the comment at `:1125` states the cost one word too wide. **Three** of the forms are this round's regression, two are pre-existing. | prose only — ~4 lines (**CARD-265 AC-1/AC-2**) |
| 2 | A sentence stating **no** count can red the guard with a message claiming it states one. A deny-side guard with a misdescribing message is the documented route to being switched off. | prose only — ~2 lines (**CARD-265 AC-1**) |
| 3 | The hole-test for the adapter number will **not** notice the hole closing by any mechanism outside `_map_defects`/`_id_defects`, and its docstring says it will. Its planter self-check *is* a real control. | prose only, confirmed by execution — ~2 lines (**CARD-265 AC-4**) |
| 4 | Five of ten `CASES` slots are held by arithmetic rather than by value — including `"sourcing covers CAP-001 and nothing else."`, the corpus' **only** detector of a `_COMPONENT_ID` widening across the COMP/CAP boundary. | partly asserted — one line (**CARD-265 AC-3**) |
| 5 | The *"exactly two adapters (ADR-0019)"* **number** has no enumerable authority and cannot be derived; the **scoping** is controlled, the number is not. The number is **true** of the tree as written. | carded forward — needs an authority or a parser over ADR prose (**CARD-265 AC-4**) |
| 6 | The certification's 20 mutants do not establish that every by-value pin has its own control — M17 reaches **2 of 12** pin arms. | prose only — two more artefact mutants per corpus (**CARD-265**) |
| 7 | CARD-264's three stale "two" claims are now reachable from a pointer this card created at `CLAUDE.md:42`. | carded forward — **CARD-264, already implemented** |

Plus the gate's own eighth, recorded here because it was found at the gate and belongs with the others:
**AC-3's pointer half is a whole-file substring test**, tight in fact and loose in form, ~2 lines.

### Merge ahead of CARD-264 — measured, not argued

Done from the gate's own tree and the shared object store; it entered neither sibling worktree.
`git merge-base d40e9d4a 335c641e` = **`feb3e6b5`**, so CARD-264 is branched from this card's own fix-1
tip and already carries `import re` and the fix-1 classes. **Trial three-way merge
`git merge-tree --write-tree 335c641e d40e9d4a` → exit 0, zero conflicts**, result tree `d15e1685`. And a
*semantic* cross-check on the merged tree rather than only a textual one: this card's own helpers run
over the merged `CLAUDE.md` blob give `_claude_md_rows` → `[]` and `_adapter_counts` → `[]` with both
pointer substrings present, so CARD-264's three-line change reintroduces no COMP id and no count. All
five `TestComponentMap_*` classes intact; CARD-264 keeps the `_ADAPTERS` symbol and renames only the
test, so this card's M-1 scoping control survives the rename.

**Conclusion: merge CARD-261 first; CARD-264 needs no rebase beyond fast-forwarding past fix round 2.**

**Disclosed by the gate:** one `ls` stat of main's `.full-suite.lock` path at the end (result: no such
file). A stat, nothing read, written or created.

### [Merge gate, attempt 1] FAILED — **and the failure was mine, not the card's**

`PYTEST_EXIT=1`: **5 failed, 8844 passed, 1 skipped** at `ff4374f6`, all five in
`tests/test_admin_binding.py::TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine::test_a_request_addressed_to_this_machine_is_served`.

**I set `DATABASE_URL` for this gate and that is what broke it.** My reasoning was that CARD-259's merge
gate ran with it set and bought DB-mode coverage, so doing the same here was better. It was not: the five
tests fail **whenever a Postgres URL is configured**, and CARD-261 touches `CLAUDE.md`, a docstring in
`src/nonogram/__init__.py` and `tests/test_cli.py` — none of which can reach the admin panel's host
binding.

**Isolated in one command rather than reasoned about.** I ran the same five tests in CARD-262's worktree,
which is branched from **pre-CARD-261 main**:

| configuration | result |
|---|---|
| `DATABASE_URL` **unset** | **5 passed** |
| `DATABASE_URL=postgresql://localhost/nonogram_test` | **5 failed** |

So the card is exonerated by a tree that does not contain it, which is the only form of exoneration worth
having here.

**And the actual cause is worth more than the exoneration: `nonogram_test` is migrated but STALE.**

```
E  psycopg2.errors.UndefinedColumn: column puzzles.manually_edited_at does not exist
```

The database exists and is reachable (`select 1` → 1) and has **7 tables** including `alembic_version`,
so my first guess — an empty database — was wrong. Its `alembic_version` is simply **behind the models**:
`puzzles.manually_edited_at` is declared in `src/nonogram/db/models.py` and absent from the table. The
request the test makes reaches a query over `puzzles`, and the query fails.

**Why this matters beyond this gate.** The project's own instruction file says the suite is
`./.venv/bin/python -m pytest` with no `DATABASE_URL`, and in that configuration the DB-mode tests skip
and these five pass. So the board's gates have been measuring the **no-database** configuration —
while the owner's live admin panel runs on Postgres. Pointing `DATABASE_URL` at the test database today
does not buy coverage; it **fails hard** on a schema drift. Recorded as a backlog item. I have **not**
run `alembic upgrade head` against it: it is a database mutation nobody asked for, in the middle of a
merge, and the merge does not need it.

**Gate re-run in the project's default configuration** (no `DATABASE_URL`), same commit, same held lock.

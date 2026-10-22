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
**Review score:** —
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

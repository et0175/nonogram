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

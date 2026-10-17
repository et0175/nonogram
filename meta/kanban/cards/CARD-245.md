# CARD-245: An edited grid is re-verified and re-graded by one solve, or it is not stored

**Status:** ready
**Priority:** P1
**Category:** feature
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/245-edited-grid-verify-and-grade
**Worktree:** —
**Source:** owner's doc "Admin panel", 2026-10-18 — "after pressing 'save' - verify that it has a unique solution and calculate difficulty… Don't allow saving puzzles that don't have a unique solution"
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/puzzle_review.py, src/nonogram/admin/app.py, tests/test_puzzle_edit_store.py, tests/test_puzzle_edit_routes.py, tests/test_admin_review.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The server half of manual puzzle editing: given a replacement grid for an existing puzzle,
decide whether it may be stored, grade it, and store it with its derived data rebuilt. The
editor UI is **CARD-246** and is out of scope here.

**Read this before designing — most of the gate already exists.** Verified by reading the code,
not inferred:

- `puzzle_review.add_puzzle` already calls `_refuse_unless_uniquely_solvable(grid)`
  (`puzzle_review.py:443`) and that refusal **returns the proof**, from which
  `_strategies_of(proof)` reads the ladder. CARD-080 established that the store refusing a grid
  is a *bug in the caller*, because callers come from `orchestrator.generate`, which enforces
  INV-002.
- **There is no update path.** The store's write methods are `add_puzzle`, `rename_puzzle`,
  `_set_status` and `assign_to_book`. Nothing replaces a grid. **That absence is the whole
  attack surface of this card**: a new write path that does not go through the existing refusal
  is how a non-unique puzzle gets into the table, and it is the one defect here that corrupts
  data rather than merely annoying someone.
- `clues_rows` / `clues_cols` are marked **"display only"** on the model
  (`db/models.py:63-64`) — they are derived from the grid and must be re-encoded from the edited
  grid through COMP-004 (`clues.py`), never carried over.
- `difficulty.score_difficulty(signals)` takes `SolveResult.signals` and its docstring is
  explicit: *"Only the one solve that already happened is read; the search is never re-entered
  (ADR-0029/R2, guardrail G-1)."* `classify(score)` then gives the tier.

**So the central design constraint is: one solve, two answers.** The solve that proves
uniqueness is the same solve that must supply the grading signals. Do not verify and then
re-solve to grade — that doubles the most expensive operation in the system and contradicts
ADR-0029/R2. `_refuse_unless_uniquely_solvable` already hands back the proof; thread the signals
off it.

**The two-phase save, and the decision it needs.** The owner wants the difficulty *shown* with
Cancel/Approve before anything is stored, so a grade must be produced without committing. Three
ways, with a recommendation rather than a silent choice:

- **Recommended: solve once, stage the result.** The verify call solves, returns
  `{unique, score, tier, strategies}`, and stages the verified grid server-side keyed by puzzle
  id **and a hash of the grid**. Approve commits only if the hash still matches, so a grid that
  changed between verify and approve is refused rather than stored ungraded.
- Solve on verify **and again** on save. Simple and always correct, but it doubles solver cost,
  and CLAUDE.md records that random mid-density 40x40+ grids are a known-hard class taking
  seconds with **no cooperative timeout enforced yet** — two of those is a long wait in a
  browser.
- Trust the client to send back the grade. Rejected outright: the uniqueness verdict and the
  tier would then be client-supplied, which is the one thing this card exists to prevent.

**Judge the recommendation before implementing it** and say in the notes what you chose and
why. If you keep staging, say where the staged state lives and what happens when it expires.

## Acceptance criteria

- **AC-1** (happy, a unique edit is stored and re-derived): *Given* a stored puzzle and a
  replacement grid with exactly one solution, *when* it is saved, *then* the grid is stored and
  `clues_rows`, `clues_cols`, `difficulty_score`, `difficulty_tier` and `strategies_used` are all
  **re-derived from the edited grid**, not carried over.
  (test: `TestPuzzleEdit_StoresAndRederivesEverythingDerived`)
- **AC-2** (negative, the gate holds): *Given* a replacement grid with **zero** solutions and
  one with **two or more**, *when* each is saved, *then* each is refused, the stored puzzle is
  **byte-for-byte unchanged**, and the refusal names which case it was. Assert the unchanged row,
  not only the raised error. (test: `TestPuzzleEdit_RefusesZeroAndMultipleSolutions`)
- **AC-3** (happy, one solve serves both answers): *Given* a saved edit, *then* the uniqueness
  verdict and the difficulty come from **the same solve** — the search is not re-entered to
  grade. Prove it by counting solver entries, not by reading the code.
  (test: `TestPuzzleEdit_GradesFromTheProvingSolve`)
- **AC-4** (guard, a booked puzzle is not editable): *Given* a puzzle `in_a_book`, *when* an edit
  is saved, *then* it is refused, following the precedent the approve, reject and delete routes
  already set (`app.py:2392`, `:2415`, `:5554`). Editing a puzzle a finalised book prints would
  change that book's pages underneath it.
  (test: `TestPuzzleEdit_RefusesAPuzzleThatIsInABook`)
- **AC-5** (happy, verify does not persist): *Given* a verify call, *then* it returns the grade
  and the stored row is unchanged — the owner must be able to Cancel and lose nothing.
  (test: `TestPuzzleEdit_VerifyReturnsTheGradeWithoutStoring`)
- **AC-6** (edge, the grid changed between verify and approve): *Given* a verified grid and an
  approve carrying a **different** grid, *then* it is refused rather than stored with the earlier
  grade. This is the hole the two-phase flow opens and it must be closed by construction.
  (test: `TestPuzzleEdit_RefusesAnApproveWhoseGridMoved`)
- **AC-7** (edge, a malformed grid): *Given* a payload that is not a rectangular grid of
  booleans, *then* `_refuse_unless_shaped_like_a_grid` refuses it **before** any solve is
  attempted — a shape error must not be spent as solver budget.
  (test: `TestPuzzleEdit_RefusesAMalformedGridBeforeSolving`)

## Guardrails

- **G-1 (the one that matters): every write of a grid goes through
  `_refuse_unless_uniquely_solvable`.** Do not add a second uniqueness check and do not inline a
  solver call — reuse the store's existing refusal so there is exactly one gate to audit. Add a
  test that **fails if a new grid-writing method bypasses it**, derived from the class rather
  than hand-listed (ADR-0039/R2: the set is enumerated, and defaults to deny).
- G-2: `audit_uniqueness` keeps working and keeps *reporting only, never writing*. It answers
  "what is in there now?" and this card must not turn it into a repair tool.
- G-3: `id`, `batch_id`, `source_image` and `created_at` survive an edit unchanged.
- G-4: no new runtime dependency (ADR-0006/R1 — stdlib + Pillow + NumPy).
- G-5: capability modules never import laterally; `tests/test_cli.py` has an `ast` guard.
- G-6: no test retired without a named survivor (CARD-220's rule).

## Open question for the architect station — do not guess this one

**`quality_score` and `recognizability` measure fidelity against the *source image*
(`measure_quality(original_image, puzzle.grid)`, CARD-050). A hand-edited grid makes both stale,
and this card has no honest value to recompute them to** — the owner's edit is a deliberate
departure from the picture, so "fidelity to the source" is no longer a meaningful score.

Three candidate answers, all defensible, none obviously right: keep the old values and record
that they describe the pre-edit grid; null them and let the list show "—" for a hand-edited
puzzle; or re-measure against the source image and accept that a good edit may score worse.
**Settle this with the owner before implementing**, and whichever is chosen, a hand-edited
puzzle should be distinguishable from a generated one in the store — otherwise the two scores
silently mean different things for different rows.

## System contract

_Assembled 2026-10-18 by `system_rules.py --card CARD-245 --root meta/architecture` (58 rules returned, `card_scope: touches`). A projection — fix the source artifact, never this list._

**Curated to 11; 47 dropped and declared.** The projection returned **58**, of which **47** are scoped `src/nonogram/**` — package-wide, so they match every card in the project and narrow to nothing. Owner decision 2026-10-17: ship the curated form (6–14 rules, kept where the rule's scope names a file this card touches or the card names the rule's artifact) with the dropped count stated. This is not a judgement that the dropped rules do not apply — it is that a ~57-rule contract measurably produces **fake** coverage on this board: reviews emitted a count line claiming all rules checked while marking 45–48 of 53 `⚠ unchecked` and writing 6–12 verdict lines, where 10- and 13-rule contracts produced full coverage. The root cause is the package-wide scoping and is tracked in `meta/kanban/backlog.md`.

- **ADR-0006/R1** — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party
  package joins the installed dependencies without revising this ADR. Non-executable static assets
  (fonts and similar data files) may ship as package data instead, and doing so is not a dependency
  change. (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- **ADR-0029/R1** — The difficulty of a line-solvable puzzle is derived from the rung of the hardest
  technique its verifying solve required (simple_overlap < line_dp < probe_contradiction) and the
  share of cells settled at that rung; each rung is the fixed point of its technique, so the rung of
  a cell is a function of the clue set alon… (check: test:
  TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- **ADR-0029/R2** — Technique classification and the strategies list are computed inside the one
  verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle's
  strategies list, and the tier is derived from that same list — no second derivation, no second
  solver entry. The ladder's fixed points are phases… (check: test:
  TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- **ADR-0029/R3** — No clock reading — elapsed_seconds or any other — and no size or density term
  enters the difficulty score, the tier decision or the strategies list; the score is a pure
  function of the rung tags of the solve and branch_nodes, identical on every machine. (check: test:
  PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- **ADR-0029/R4** — The overlap masks that define the simple_overlap rung are computed relative to
  the line's already-known cells (the leftmost and rightmost placements consistent with them,
  intersected), and are re-derived natively inside the solver package; the solver never imports
  clues.py or any other capability module for the purp… (check: test:
  test_every_import_in_the_package_points_inward)
- **ADR-0029/R5** — Rung attribution is reported only for a clue set with exactly one solution; a
  clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attribution at all
  (empty or None per-cell tags, an all-zero per-rung histogram, an empty rung list). For uniquely-
  solvable clue sets, rung attribution is inva… (check: test:
  PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- **ADR-0031/R2** — A solve that branched is reported as the `guess` strategy
  (solver.STRATEGY_GUESS) in FR-029's strategies list, never as a tier. (check: test:
  TestTiers_BranchingIsAStrategyNotATier)
- **ADR-0039/R1** — A set a guard consults needs a completeness test written before the set, and any
  claim the guard makes about what it catches needs a control that can fail: caught WITH the set
  member present, missed WITHOUT it. A claim whose control cannot fail is narrative, not coverage,
  and must be narrowed to what is measured or … (check: test:
  test_the_control_for_each_spelling_depends_on_the_set)
- **ADR-0039/R2** — A guard's set is derived from an authority the runtime can enumerate, not hand-
  written. Where no such authority exists, the guard defaults to deny: a shape it cannot analyse is
  a FAILURE, never a silent pass, and the unanalysable sites become named exemptions under
  ADR-0039/R3. (check: test: test_the_guard_sets_are_derived_and_not_hand_written)
- **ADR-0039/R3** — An exemption is a claim. Every exemption a guard grants carries a control for
  what it must NOT absorb — caught with the exemption removed, missed with it in place — is held to
  an equality against the sites that exist today, and records whatever it still cannot see as a
  measured bound with its own failing control. (check: test:
  test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw)
- **INV-002** — A puzzle is only marked ready for export after its uniqueness check has confirmed
  exactly one solution (US-005, FR-011). (check: test: TestExport_RejectsUnverifiedPuzzle,
  TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
## Worktree notes

- **[Why this is architectural and P1]** It opens the first write path to `Puzzle.grid` since
  the generation pipeline, and the thing standing between that path and a corrupt table is one
  refusal it must be wired into rather than around. CARD-080's own note says reaching the store's
  refusal is a bug *because* every caller came from a solver-verified pipeline; this card creates
  a caller where the human **is** the generator, so for the first time that refusal is a working
  gate rather than a backstop.
- **[The cheapest way to get AC-3 wrong]** Verify with one call and grade with another. It will
  pass every functional test and only show up as doubled latency and a contradiction with
  ADR-0029/R2. Count solver entries in the test.
- **[House rules]** `hypothesis` is **not** in the dependency baseline — build grid corpora with
  seeded `random.Random` and assert a minimum case count inside the test. Prefer an independent
  second implementation over re-deriving with the function under test; for uniqueness there is
  already a precedent to reuse, `tests/helpers/brute_force_oracle.py`, which must **never** import
  `nonogram.solver` or the cross-check becomes circular.
- **[Do not take timing measurements on a loaded host]** Sibling cards are active. If you want to
  record the cost of a solve on an edited grid, state the host condition with the figure and
  prefer ratios to absolute seconds.

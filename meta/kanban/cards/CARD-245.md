# CARD-245: An edited grid is re-verified and re-graded by one solve, or it is not stored

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/245-edited-grid-verify-and-grade
**Worktree:** ../PythonProject4-card-245
**Source:** owner's doc "Admin panel", 2026-10-18 — "after pressing 'save' - verify that it has a unique solution and calculate difficulty… Don't allow saving puzzles that don't have a unique solution"
**Idea:** —
**Wave:** 46
**Depends on:** —
**Touches:** src/nonogram/admin/puzzle_review.py, src/nonogram/admin/app.py, tests/test_puzzle_edit_store.py, tests/test_puzzle_edit_routes.py, tests/test_admin_review.py
**Review score:** —
**Started:** 2026-10-18T05:09:31Z
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

## SETTLED 2026-10-18 (owner) — `quality_score` is kept, and a `manually_edited_at` stamp makes keeping it honest

The open question this card carried is **closed**. The owner asked whether to leave the original
score or add a "manually edited" label; the answer is **both**, because they are complements
rather than alternatives — the label is what licenses leaving the score.

**Nulling was ruled out on evidence, and it was the option neither of us had named as dangerous.**
A null `quality_score` **already means "unmeasured"** on this board — it is what random mode
stores since CARD-050 — and `puzzle_review.py:890` records the consequence: a null is **excluded**
from any `quality_min` filter, because "an unmeasured puzzle cannot satisfy a minimum" and SQL's
`NULL >= n` is false. So nulling after an edit would make a hand-edited puzzle **disappear from
every quality-filtered view**, i.e. the owner improves a puzzle and it vanishes from the list they
pick book puzzles from. It would also overload one value with two meanings, "never measured" and
"measured but stale", which is the same defect as the stale score itself.

**What to implement:**

- **`quality_score` and `recognizability` are kept unchanged across an edit.** They are *stale,
  not meaningless*: the grid still derives from the source picture, so fidelity becomes imprecise
  rather than false, and `quality_min` keeps working. Do **not** recompute them — re-measuring
  against the source image would punish a deliberate departure from it, which is exactly what an
  edit is.
- **Add `manually_edited_at` (nullable timestamp)** to `Puzzle`, set on every successful edit.
  **A timestamp, not a boolean** — non-null *is* the flag, so it does everything
  `manually_edited` would, and it additionally answers *how stale the score is* rather than only
  *that* it is stale. Same migration cost, and it matches the existing `created_at` pattern.
- It needs **migration 016** (015 is CARD-222's, already merged). Nullable with no backfill, so
  every existing row reads "never hand-edited", which is true.
- Surface it where the score is shown — the puzzle card and the list — so a reader seeing a
  quality figure can tell whether it predates an edit.

**Deliberately out of scope here**: a *filter* on "hand-edited" ("show me the ones I tuned"). It
is an obvious next want and a cheap follow-up, but adding a filter field is scope this card did
not ask for. Note it in the notes rather than building it.

**Acceptance criteria this adds** (numbered on from the seven above):

- **AC-8** (happy, the stamp is set and the score survives): *Given* a successful edit, *then*
  `manually_edited_at` is set and `quality_score` / `recognizability` are **unchanged**.
  (test: `TestPuzzleEdit_StampsTheEditAndKeepsTheQualityScore`)
- **AC-9** (negative, a refused edit stamps nothing): *Given* an edit refused for non-uniqueness,
  *then* `manually_edited_at` is **not** set — the stamp records a stored edit, not an attempt.
  (test: `TestPuzzleEdit_ARefusedEditLeavesNoStamp`)
- **AC-10** (guard, the quality filter still includes the puzzle): *Given* a hand-edited puzzle
  whose score is above a `quality_min`, *then* it still appears in that filtered list — the
  regression nulling would have caused, asserted so nobody reintroduces it.
  (test: `TestPuzzleEdit_AnEditedPuzzleStillPassesTheQualityFilter`)

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

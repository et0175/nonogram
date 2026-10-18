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
**Touches:** src/nonogram/admin/puzzle_review.py, src/nonogram/admin/app.py, src/nonogram/db/models.py, migrations/versions/016_puzzle_manually_edited_at.py, src/nonogram/admin/templates/_puzzle_table.html, tests/test_puzzle_edit_store.py, tests/test_puzzle_edit_routes.py  <!-- amended 2026-10-18: the three middle entries are the owner's SETTLED section (the column, migration 016, surfacing the stamp) and were missing from the field; tests/test_admin_review.py was listed and not needed. See [Touches drift] below. -->
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

### Implementation notes (worktree, 2026-10-18)

- **Two-phase save: the recommendation was taken, but moved.** "Solve once, stage the
  result" is what shipped — with the staging *inside the one gate* rather than beside it.
  `_refuse_unless_uniquely_solvable` now remembers the `SolveResult` it produced, keyed by a
  SHA-256 fingerprint of the grid's extent and cells; `verify_replacement_grid` additionally
  records which puzzle that grid's grade was *shown for*. The save calls the same gate (memo
  hit, no second solve) and then refuses unless this grid is one that was shown for this
  puzzle. Staging it *outside* the gate was tried on paper first and rejected: a save that
  wrote on the strength of a staged hash match would not call the refusal at all, which is
  precisely what G-1 forbids, and the G-1 test would then have had to be weakened to
  accommodate the design. Keeping the memo inside the gate means the write path reaches the
  one refusal **statically** (the guard walks `self.…` calls) and the flow still costs one
  solve.
- **Where staged state lives / what expiry does.** On the `PuzzleReviewService` instance, in
  this process, bounded at `MAX_REMEMBERED_VERIFICATIONS = 16` (LRU). Same place and same
  lifetime as the legacy mode's `self.puzzles`, and the panel runs one gunicorn worker
  (`start.sh`, CARD-086 G-4). **There is deliberately no clock.** A proof is a pure function
  of the grid and cannot go stale; the staleness that matters — the row being put in a book
  between verify and approve — is re-checked against the row at save time. So a verification
  is forgotten when 16 newer grids have been proved, or when the process restarts, and the
  save then refuses with `EditNotVerified` ("verify it again"), which costs one solve and
  cannot store anything ungraded. A verification is not consumed by a save, so a retried save
  of the same grid does not buy a second solve.
- **AC-2's zero-solution arm is unreachable from a grid payload, and the card does not say so.**
  The clue set is re-derived *from the grid* (`_why_this_is_not_a_puzzle` refuses to trust a
  caller's clues), and a grid always satisfies its own clues — the store's own comment records
  the measurement (120 derived clue sets: 97 unique, 23 ambiguous, 0 unsolvable). The test
  reaches it the only way it can, with the solver replaced, and pins the message; the 2-or-more
  arm is driven by a real ambiguous grid.
- **Deliberately out of scope**: the "hand-edited" *filter* (noted, not built, as the card
  asks), the editor UI (CARD-246), and MIN_SIZE/MAX_SIZE on a write — the store has never
  enforced the supported range on `add_puzzle` either, and this card does not change that.

### Orchestrator verification and the scope gate (2026-10-18)

Agent reports are not evidence on this board; these are the claims checked directly.

- **The commit is what it says it is.** `9f3743d`, seven files, 2083 insertions / 3
  deletions, `Co-Authored-By` trailer present. `git status --short` in the worktree shows
  only ` M meta/kanban/cards/CARD-245.md` — the card file was written and **not staged**, as
  required. The owner's `angel1-easy.pdf` and `snowflake2-easy.pdf` were never touched.
- **G-1's guard really is derived from the class, not hand-listed.** Verified by reading the
  test: `_service_class_ast()` parses `puzzle_review.py` off disk, `_methods_of()` takes every
  `FunctionDef`/`AsyncFunctionDef` in `PuzzleReviewService`'s body, and `_binds_a_grid()`
  keys on `ast.Store` context (which is what keeps readers like `row.grid` out), a `grid=`
  keyword, `setattr(x, "grid", …)`, or a dict literal with a `"grid"` key assigned into
  `self.…`. `{add_puzzle, save_edited_grid} <= writers` is asserted as a **floor**, not as the
  set. Five synthetic bypasses are controls that must each be detected AND reported ungated,
  and `_row_to_dict` / `_all_rows_for_audit` / `audit_uniqueness` are asserted absent. This
  satisfies ADR-0039/R2 (set derived from an enumerable authority, default-deny) rather than
  claiming it.

**[Touches drift]** The implementation touched three files the `Touches:` field did not name
and left one it did:

| file | in Touches? | verdict |
|---|---|---|
| `src/nonogram/db/models.py` | no | **mandated by the card** — the `manually_edited_at` column |
| `migrations/versions/016_puzzle_manually_edited_at.py` | no | **mandated by the card** — "It needs migration 016" |
| `src/nonogram/admin/templates/_puzzle_table.html` | no | **mandated by the card** — "Surface it where the score is shown — the puzzle card and the list" |
| `tests/test_admin_review.py` | yes | not touched; the behaviour landed in the two new test files instead |

So this is a **stale field, not scope growth**: the `Touches:` list was written before the
owner's 2026-10-18 settlement and the settlement added all three. The field is amended above
rather than left to look like drift at the next card that reads it. Two consequences checked
rather than assumed: the additions bring in two new hotspots (`migrations/**` and
`src/nonogram/db/**`), and **neither collides with CARD-224**, whose hotspots are
`export/layout.py` and `book_pdf_generator.py`; and `_puzzle_table.html` is **not** in
CARD-246's `Touches` (that card names `puzzles.html`, `puzzle_edit.html`,
`puzzle_solve.html`), so no ready sibling's slice was poached.

### ⚑ A process finding that outlives this card: `-q` makes pytest print no count at all

The agent found, and `pyproject.toml:89` confirms, that the project already sets
`addopts = "-q"`. **A gate command that adds its own `-q` therefore runs at `-qq`, and at
`-qq` pytest prints no summary count line whatsoever.**

This is very probably the mechanism behind the board's CARD-223 incident, where the
orchestrator's own gate summary printed `FAILED count: 0` on a run that `EXIT=1` proved red,
and it was recorded then as "a grep pattern that missed pytest's shape". That diagnosis was
half right: there was nothing for the pattern to match. The discipline adopted after it —
**EXIT is the authority** — was the correct response and would have held either way, which is
why the gate stayed trustworthy while the explanation was wrong. Filed in `backlog.md` so a
future gate script cannot re-acquire the habit.

### [Build gate] PASSED (full, 2026-10-18)

`EXIT=0` · **8215 passed, 1 skipped, 0 failed** · pytest's own figure **1196.14s** · commit
`9f3743d` · `DATABASE_URL` **SET** (`nonogram_pythonproject4_card_245_2d9f5b42e149_test`, this
worktree's own derived database) · run under `meta/kanban/.full-suite.lock`, released after.

The single skip is the platform one — `test_book_pdf_memory.py:1288`, `setrlimit(RLIMIT_AS)`
refused by this kernel — unrelated to this card and the same skip every gate since CARD-223
has reported. So **no `db_required` test skipped**, which is what makes this gate evidence for
AC-1..AC-10 rather than a vacuous green.

Collected 8055 → 8216 (**+161**), which reconciles exactly with the implementation's 161 new
tests. First-attempt green, unlike CARD-248's.

**Two figures here are NOT trendable, and the reason is recorded rather than smoothed over:**

1. The suite's own wall clock is **1196s against main's 788s (+52 %)**, and ms/test rises
   98 → 146. **CARD-224's implementation agent was running on this machine throughout.** A
   concurrent card can no longer corrupt a gate's *verdict* (CARD-244 gave each worktree its
   own database), but it still competes for CPU, so this line must not be read against the
   wave-45 lines as a cost trend. The verdict is unaffected; the duration is not comparable.
2. The wrapper's own `ELAPSED` was **4126s** against pytest's **1196.14s** — a ~2930 s gap
   outside pytest's session timer that the wrapper does nothing to explain (it runs one
   `git log` and two `date` calls around the invocation). **Unexplained, and left that way
   rather than attributed.** It does not touch the verdict (`EXIT` and pytest's own summary
   agree), but it means the wrapper's elapsed figure is not a measurement of anything on this
   host while a sibling agent is active, and no line in `suite-timing.log` should be written
   from it. Worth a look if it recurs; a single unexplained gap is not yet a defect.

Not written to `suite-timing.log`: every line there is a **merge** gate, and mixing a build
gate — especially one measured under concurrent sibling load — into that series would make the
ms/test trend read as a regression that is really a busy host. The merge gate's line will be
written when it runs, with its own condition stated.

### [Review 1/3] Score: 7.0 — FAIL (threshold 8)

Report: `meta/review/20261018T071108Z-CARD-245-cycle1.yml` (copied from the worktree to main
before the worktree is deleted). **No critical findings.** Three important, and the shape of
the result is worth stating plainly: **the behaviour is sound and the evidence is not.**

What the reviewer tried and could not break — stated because a gate's value is in what it
rules out: no reachable write to `Puzzle.grid` skips `_refuse_unless_uniquely_solvable`;
`save_edited_grid` is the only writer and calls the gate unconditionally; the memo is only ever
populated after a verdict of `solution_count == 1`, so a timeout or an objection is never
cached as a success; eviction and a missing verification both fail **closed**; the DB write is
one session, so no partial update is reachable; the migration is symmetric and
`batch_alter_table`-parity with 004..015, and nothing in the tree asserted a head or column set
it invalidates; `pyproject.toml` is untouched; `nonogram_poc` is unreachable from the diff and
`_refuse_unless_test_database` is neither widened nor bypassed. ADR-0029/R2's "exactly one
solver entry" was judged **sound as a measurement**, not merely the right number.

**Mutation pass ran (10 mutants, targeted, never the full suite), and it is what produced two
of the three importants.** M1, M3, M4, M5, M6, M9 killed; **M2 and M7 survived**; M8 partially
killed (only the hand-listed floor caught it); M10 the no-op control survived as intended,
which is what shows the selection is not red-by-default. All reverted; `git diff --stat` empty
afterwards.

**The three importants, each verified by me directly rather than taken on report:**

- **F-001 — the fingerprint's extent is load-bearing and untested.** Production is *correct*:
  `_grid_fingerprint` digests `f"{len(grid)}x{len(grid[0])}:{bits}"`, and its own docstring
  names the hazard verbatim ("a 2x6 and a 3x4 of the same bits would share a name"). **Nothing
  asserts it**, and M2 — drop the extent, keep the bits — survived all 161 tests. The
  demonstrated corruption: verify a unique 1×4 `[[T,F,F,T]]` (bits `1001`), then save the 2×2
  diagonal (same bits, **2 solutions**) — memo hit, solver never entered, verification pairing
  satisfied, **written**, and `audit_uniqueness` reports it afterwards. Exactly what this card
  exists to prevent, one deleted digest component away.
- **F-002 — G-1 is default-ALLOW, and the production code was shaped to satisfy it.** The
  *method set* is derived from the class, which is what the card's G-1 wording literally asked
  for; but the write *predicate* `_binds_a_grid` is a hand-written allow-list of four syntactic
  shapes **returning `False` for everything else**. Eight of nine plausible writer shapes the
  reviewer probed are invisible, including `.update({"grid": …})` and a `setattr` loop.
  **I confirmed a sharper form of this than the review states.** `puzzle_review.py:1038-1043`
  carries a comment saying the per-column longhand was chosen *because* a `setattr` loop
  "writes the grid in a way no reader — and no static guard — can see it happen, and this is
  the write G-1 exists to keep visible." So the production code was deliberately written to be
  **legible to its own guard** — a sound instinct, honestly commented — which means the guard's
  completeness rests on **discipline, not construction**. And three lines above, in the *same
  method*, the legacy branch writes `puzzle.update(derived)`, which the predicate cannot see at
  all: `save_edited_grid` enters the writer set only because the DB branch spells it out
  longhand. M8 is the proof — rewriting that branch as a behaviour-identical `setattr` loop
  dropped the method out of the derived set and `test_every_grid_writing_method_reaches_the_refusal`
  **still passed**; the only red test was the hand-listed floor, i.e. precisely the
  snapshot-of-today's-methods that G-1 names as the thing it must not be.
- **F-003 — `test_016_is_the_head` reintroduces brittleness a prior card paid to remove.**
  `assert get_heads() == [max(on_disk, key=int)] == ["016"]` — the trailing term pins the head
  by **name**, so migration 017 on an unrelated card reds it. `test_batch_requested_tier.py:300-302`
  records this exact history ("hardcoding `['015']` would have handed the same breakage to
  016"), and the new test's own docstring claims "Derived, not named", which the third term
  makes false.

**Two minors promoted into the fix cycle rather than routed:**

- **F-004** `second >= first` lets a **frozen** stamp pass — M7 survived. A non-strict
  inequality is not a claim that something moved.
- **F-012** the new marker is `class="badge rec" data-edited` with **no `data-level`**, while
  every other `badge rec` is styled by `data-level`. So it is probably **invisible on the
  page**, and no test can see that. The owner validates visually, so an invisible marker is a
  defect, not a nit.
- Plus **F-005** (a self-skipping AC-4 arm with a tautological `assert … in (True, False)`),
  **F-007** (a comment at `start.sh`'s `WEB_CONCURRENCY` knob, which silently breaks the
  two-phase flow at 2 — fails closed), and **F-011** (route the memo read through its accessor
  so the LRU refresh is not a latent trap).

**Residues routed, not absorbed** — recorded here so the next card inherits them rather than
rediscovering them:

- **F-006** the gate runs *before* the verification check, so an unverified save buys a full
  solve and can evict pending verifications from the 16-entry memo. Fails closed. Left as is.
- **F-008** `MIN_SIZE`/`MAX_SIZE` and `MAX_CONTENT_LENGTH` on the **first HTTP-reachable grid
  write in the system**. The implementer declared this out of scope on `add_puzzle` parity
  grounds, and the reviewer is right that the parity does not hold: `add_puzzle` is not
  reachable with a caller-chosen extent and these routes are. **Routed to the owner as a
  decision, not fixed** — a bound changes behaviour no AC asks for and could refuse a grid
  CARD-246's editor presents.
- **F-009** (`shown_for` unbounded per entry), **F-010** (a non-UUID `<puzzle_id>` answers a
  JSON route with the HTML 500 page — parity with approve/reject, but those advertise HTML),
  **F-013** (the pairing keys on `str(puzzle_id)` as given rather than a canonical UUID).

**What the reviewer says the CARD got wrong, and I agree with three of four:** the `Touches`
field named a file the commit does not change (already amended above); AC-2's zero-solution arm
is unreachable from a grid payload (the implementer caught it; the card now says so);
**G-1's wording specified the wrong thing** — "derived from the class rather than hand-listed"
constrains the *method set*, which the implementation satisfies literally while leaving the
predicate an allow-list, and had it said *a method is presumed a writer unless justified
read-only*, F-002 would have been hard to ship; and the card recommended a hash "of the grid"
**without specifying its domain**, which is the single most load-bearing line in the mechanism
(F-001). That last pair is the transferable lesson: a card that mandates a derived guard must
say what defaults to deny, and a card that recommends a hash must say what it covers.

### Implementation notes (worktree, 2026-10-18)

- **Two-phase save: the recommendation was taken, but moved.** "Solve once, stage the
  result" is what shipped — with the staging *inside the one gate* rather than beside it.
  `_refuse_unless_uniquely_solvable` now remembers the `SolveResult` it produced, keyed by a
  SHA-256 fingerprint of the grid's extent and cells; `verify_replacement_grid` additionally
  records which puzzle that grid's grade was *shown for*. The save calls the same gate (memo
  hit, no second solve) and then refuses unless this grid is one that was shown for this
  puzzle. Staging it *outside* the gate was tried on paper first and rejected: a save that
  wrote on the strength of a staged hash match would not call the refusal at all, which is
  precisely what G-1 forbids, and the G-1 test would then have had to be weakened to
  accommodate the design. Keeping the memo inside the gate means the write path reaches the
  one refusal **statically** (the guard walks `self.…` calls) and the flow still costs one
  solve.
- **Where staged state lives / what expiry does.** On the `PuzzleReviewService` instance, in
  this process, bounded at `MAX_REMEMBERED_VERIFICATIONS = 16` (LRU). Same place and same
  lifetime as the legacy mode's `self.puzzles`, and the panel runs one gunicorn worker
  (`start.sh`, CARD-086 G-4). **There is deliberately no clock.** A proof is a pure function
  of the grid and cannot go stale; the staleness that matters — the row being put in a book
  between verify and approve — is re-checked against the row at save time. So a verification
  is forgotten when 16 newer grids have been proved, or when the process restarts, and the
  save then refuses with `EditNotVerified` ("verify it again"), which costs one solve and
  cannot store anything ungraded. A verification is not consumed by a save, so a retried save
  of the same grid does not buy a second solve.
- **AC-2's zero-solution arm is unreachable from a grid payload, and the card does not say so.**
  The clue set is re-derived *from the grid* (`_why_this_is_not_a_puzzle` refuses to trust a
  caller's clues), and a grid always satisfies its own clues — the store's own comment records
  the measurement (120 derived clue sets: 97 unique, 23 ambiguous, 0 unsolvable). The test
  reaches it the only way it can, with the solver replaced, and pins the message; the 2-or-more
  arm is driven by a real ambiguous grid.
- **Deliberately out of scope**: the "hand-edited" *filter* (noted, not built, as the card
  asks), the editor UI (CARD-246), and MIN_SIZE/MAX_SIZE on a write — the store has never
  enforced the supported range on `add_puzzle` either, and this card does not change that.

### Review cycle 1 fixes (worktree, 2026-10-18)

Score 7/10 against a threshold of 8, build gate green, no critical findings.
Everything below is evidence rather than behaviour except where marked.

- **F-001 — the fingerprint's extent now has a round-trip test.**
  `TestPuzzleEdit_AProofDoesNotCrossGridExtents` verifies a unique 1x4
  (`[[T,F,F,T]]`) and then *saves* the 2x2 diagonal — the same four bits
  `1001` in another extent, and a grid with two solutions. The save must raise
  `NotUniquelySolvable` (not `EditNotVerified`: the gate must be what catches
  it), the stored row must be unchanged, the stamp must stay null, and the
  solver entry count must *rise*, because a memo hit is exactly how the
  corrupt write happens. Mutant M2 (`text = bits`) now fails 7 tests.
- **F-002 — G-1 is inverted to default-deny.** The write predicate was an
  allow-list of four *grid-write* shapes, so an unrecognised shape was
  classified "not a write". It is now a catalogue of *writes*: any store into
  something that is not a freshly built local, any `setattr`/`del`, any `**`
  splat, any mutating method call, a `{"grid": …}` payload handed to a call.
  Anything it names is a **candidate grid writer** that must reach the gate or
  sit on `WRITES_NO_GRID` (10 entries, each with its reason), and an entry
  there is machine-checked for not naming a grid and not writing an unreadable
  payload — so `save_edited_grid`, whose legacy branch is
  `puzzle.update(derived)`, *cannot* be excused. The parse is the **module**,
  not the one `ClassDef`, so a module-level writer is seen. All nine shapes
  cycle 1 probed are caught and are parametrised controls.
- **F-003 — `== ["016"]` dropped.** The test is renamed
  `test_the_head_is_the_highest_numbered_migration_on_disk`, because the old
  name made the claim the assertion must not make. `test_016_revises_015`
  remains as this card's legitimate named link.
- **F-004 — strict stamp movement on a frozen clock.** `frozen_clock` holds
  `puzzle_review.datetime.now`, two fixed instants are stored and pinned by
  prefix, and the assertion is `second > first`. Mutant M7 now fails.
- **F-005 — the legacy `in_book` arm no longer skips itself.**
  `Harness.set_the_legacy_in_book_status` writes the status directly (ORM in DB
  mode, dict in memory), the premise is asserted (`status == "in_book"` with a
  null `book_id`, so it really is the legacy arm), and both the save and the
  verify are asserted refused unconditionally.
- **F-007 — the coupling is stated at the knob.** A paragraph directly above
  `--workers` in `start.sh` names the two-phase flow and says what raising it
  would need; the default is unchanged and
  `tests/test_admin_serving.py::test_one_worker_unless_this_was_revisited`
  still owns that. Pinned by
  `TestPuzzleEdit_TheWorkerCountIsCoupledToTheTwoPhaseFlow`.
- **F-011 — one accessor.** `_remembered_proof` becomes
  `_remembered_verification`, returns the `_Verification`, and is the only way
  the memo is read outside its own methods. Pinned structurally and
  deliberately so: behaviour cannot tell the two versions apart today, which
  is precisely the trap.
- **F-012 (production) — the marker has its own class.** It wore
  `badge rec`, which is the *recognisability* chip's class keyed by
  `data-level`, so it rendered as a second identical grey chip beside the real
  one. It is now `badge edited` with its own `.badge.edited` rule in
  `admin.css` (warning tint, tokens only). Two assertions, because either half
  alone is vacuous: the template asks for the class, the stylesheet answers.
- **Not in this cycle, by the dispatcher's instruction**: F-006 (gate before
  the verification check — fails closed, recorded as residue), F-008
  (`MIN_SIZE`/`MAX_SIZE` and `MAX_CONTENT_LENGTH` — routed to the owner as a
  decision), F-009/F-010/F-013 (nits, routed).

### Orchestrator: fix cycle 1 boundaries verified (2026-10-18)

`7958832`, 6 files, +877/−153. Checked directly rather than on report: **`app.py`,
`db/models.py` and migration 016 are untouched**, and `start.sh`'s `${WEB_CONCURRENCY:-1}`
default is **unchanged** (the fix is a comment above the flag). So production movement is
confined to `puzzle_review.py` (34 lines), one CSS rule and the template marker — which is
what a cycle fixing *evidence* should look like.

**The G-1 inversion is real, and in the right direction.** Verified by reading it: every
function in the module — module-level **and** every class's methods — is now a *candidate grid
writer* **unless provably read-only**, which is default-deny. `WRITES_NO_GRID` holds **10**
entries, each with its justification inline and each **machine-checked** (it must not name
`grid` on the writing side and must not contain an unreadable payload write). The sharpest
test in the set is `test_save_edited_grid_could_not_be_excused_even_if_someone_listed_it` — the
one method whose legacy branch writes through `.update()` **cannot be moved onto the list to
silence a failure**. That is the finding closed at its root rather than at its instance.

Also recorded: the fix agent **disagrees with the reviewer on F-012 and is right** —
`admin.css:142` carries a base `.badge.rec` not keyed by `data-level`, so the marker rendered
as a fully styled grey chip, not an invisible one. The real defect was that it was
**indistinguishable from the recognisability chip two cells away in the same row**, i.e. it
read as a duplicate rec badge rather than as a new kind of marker. A correct diagnosis of a
real defect that the review had mis-mechanised; the fix addresses the semantics, not a missing
rule. And on **F-005** the fix says the review *understated* it: `mark_in_book` sets **both**
`status` and `book_id`, so the old test's refusal was being driven by `book_id` — already
covered elsewhere — and AC-4's legacy **status-only** arm was not covered at all. The
tautology was hiding a coverage hole, not a weak assertion. Both corrections are the kind this
board wants recorded, since an agent correcting a reviewer is the cheapest place to catch a
review error.

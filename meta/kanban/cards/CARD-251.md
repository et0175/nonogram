# CARD-251: A puzzle already in a book can be edited, behind a confirmation that names the book

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/251-edit-a-booked-puzzle
**Worktree:** —
**Source:** owner's doc "Nonograms - Print layout" → "Puzzle editor", 2026-10-19 — item 5: "Add a possibility to edit puzzles that are already in the book with additional 'are you sure question'" (intake in `meta/architecture/inputs/raw-requirements.md`)
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/puzzle_review.py, src/nonogram/admin/app.py, src/nonogram/admin/static/puzzle_edit.js, src/nonogram/admin/templates/puzzle_edit.html, src/nonogram/admin/templates/_puzzle_table.html, tests/test_puzzle_edit_routes.py, tests/test_puzzle_edit_store.py, tests/test_puzzle_editor_ui.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## ⚠ BLOCKING OBLIGATION — an INV-009 reading is owed before this card is dispatched

**Do not start this card until the registry question below is answered at the architect station.**
It is not a detail of the implementation; it decides what the card builds.

`save_edited_grid` re-derives `difficulty_tier` from the one solve that proved the grid unique. **INV-009**
requires a book's order to run easy → medium → hard, with a divider page before each non-empty level and
puzzle numbers running 1..n across the book — and it says in as many words that an *arrangement* move
"that would carry a puzzle across a level boundary is **refused** and the order is unchanged".

An approved edit that regrades a booked puzzle from easy to medium **does exactly what arrangement is
forbidden to do**, by a path INV-009 does not mention because no such path existed when it was written.
Three defensible answers, and the owner picks one:

1. **INV-009 gains a clause for a regrade inside a book** — the puzzle is re-placed in its new level and
   the book renumbered. Most faithful to item 5; the most work; changes pages the owner has arranged.
2. **The edit is refused when the new tier differs from the stored one** — "you may repaint it, you may
   not re-grade it while it is in a book." Cheapest, and it keeps INV-009 untouched. The refusal is
   knowable *before* anything is stored, because the verify phase already computes the new tier, so the
   owner learns it with the grade and not after Approve.
3. **The book is marked stale** and the owner re-arranges it. Needs a staleness concept the model does
   not have.

**Recommendation: (2) for this card, with (1) as a follow-up if the owner wants it.** It delivers the
owner's request — booked puzzles become editable — without silently re-paginating a book from a page
that shows no book. It is also the only one of the three whose failure mode is a refusal rather than a
surprise.

## What to implement

Today a booked puzzle is refused at **four sites**, and they must move together:

| site | what it does |
|---|---|
| `puzzle_review.py:892` `_row_an_edit_may_touch` | returns `None` for a booked row — the gate both CARD-245 store methods pass through (`:906`) |
| `app.py:2644` | the editor **page** route's 409, so a hand-typed URL is refused too |
| `app.py:2552` | the verify POST's `in_a_book` refusal reason |
| `app.py:1184` `EDIT_REFUSAL_REASONS` | the four reasons the client's allow-list of answers-that-never-write is keyed on (CARD-246 review cycle 2, G-001) |

The change is **not** "delete the guard". It is "the guard asks for a confirmation instead of
refusing", which means the confirmation has to reach the server — a client-side `confirm()` that then
posts the same unchanged request is not a guard at all, it is a dialog.

**Use the precedent the panel already has.** INV-008 / CARD-131: a **published** book's membership
changes only behind an explicit `confirmed` flag (`book_manager.py:1286`, `:1465`), and an unconfirmed
call "measures nothing and writes nothing" — it returns `needs_confirmation` rather than doing half the
work. Mirror that shape exactly: the save routes take the flag, an unconfirmed save of a booked puzzle
writes nothing and answers `needs_confirmation`, and the page turns that answer into the question.

**The confirmation names the book.** "Are you sure?" with no object is a dialog to click through; "This
puzzle is in *Winter Pictures* — edit it anyway?" is a question. The row carries `book_id`, and
`book_manager` can give its title.

## Three traps

**Trap 1 — `in_a_book()` cannot tell a draft book from a published one.** It is
`book_id is not None or status == IN_BOOK` (`puzzle_review.py:1642`), nothing more. So "ask once for
every book" is a **coarser instrument than the panel already has**: a draft book that has never been
exported and a published book with a KDP ASIN get the same question. Recommended, to be confirmed with
the owner: a draft book's puzzle is editable behind this card's confirmation; a **published** book's
puzzle needs the INV-008 confirmation it already requires, and the question says which it is.

**Trap 2 — the extent is not checked, and today nothing needs it to be.** `verify_replacement_grid`
(`puzzle_review.py:927`) reads the submitted grid's own `width`/`height` and **never compares them with
the stored row's**. The editor's board is built from the stored grid and cannot change its size, so the
hole is unreachable through the page — and irrelevant while booked puzzles are refused outright. **This
card opens that door.** A differently-shaped grid stored into a booked puzzle changes that book's
geometry, which is the harm the original rule was written to prevent (and which, correctly diagnosed, is
*not* caused by a repaint). Pin the extent at the store boundary: a replacement grid must have the
stored row's exact extent. Related to the owner decision already pending from wave 46 — CARD-245's
routes enforce no `MIN_SIZE`/`MAX_SIZE` and no request-size cap.

**Trap 3 — the client's allow-list is keyed on the refusal reasons.** `storeStateIsKnown`
(`puzzle_edit.js:181`) may say "nothing was stored" **only** for CARD-245's four declared reasons and
the bare 404/409/422 they arrive as; everything else leaves the store's state unknown and asks for a
reload (review cycle 2, G-001, and the inversion was deliberate — "the FIFTH refusal reason, whenever
it is added, fails safe instead of lying"). This card adds the fifth. **Adding `needs_confirmation` to
the allow-list is a claim that that answer never writes** — make it true at the route and assert it
(nothing stored, no `manually_edited_at` stamp), rather than adding the string and trusting it.

## Acceptance criteria

- **AC-1** (happy): *Given* a puzzle in a draft book, *when* its editor page is opened, *then* it is
  served (not 409) and says which book holds it.
  (test: `TestBookedEdit_TheEditorOpensForABookedPuzzle`)
- **AC-2** (guard, the unconfirmed save writes nothing): *Given* a verified grid for a booked puzzle,
  *when* the save is posted **without** the confirmation, *then* the store holds the original grid,
  `manually_edited_at` is unchanged, and the answer is `needs_confirmation` — asserted on the row, not
  on the status code. (test: `TestBookedEdit_AnUnconfirmedSaveWritesNothing`)
- **AC-3** (happy, confirmed): *Given* the same, *when* the save carries the confirmation, *then* the
  new grid is stored with its re-derived clues, grade and stamp, and the puzzle's `book_id` is
  unchanged. (test: `TestBookedEdit_AConfirmedSaveStores`)
- **AC-4** (boundary, the tier): *Given* a booked puzzle whose edit grades into a **different tier**,
  *then* the behaviour the architect station chose (see the blocking obligation) — and whichever it is,
  the owner learns it at the **verify** phase, with the grade, not after Approve.
  (test: `TestBookedEdit_ARegradeInsideABook`)
- **AC-5** (guard, the extent): *Given* a replacement grid whose extent differs from the stored row's,
  *then* the store refuses and writes nothing, for a booked puzzle and an unbooked one alike.
  (test: `TestEdit_AReplacementKeepsTheStoredExtent`)
- **AC-6** (guard, published books): *Given* a puzzle in a **published** book, *then* the confirmation
  it requires is the INV-008 one, and the question names the book and its status.
  (test: `TestBookedEdit_APublishedBookIsNamedInTheQuestion`)
- **AC-7** (guard, the other three refusals still refuse): *Given* approve, reject, restore and delete,
  *then* a booked puzzle is still refused by all of them — this card opens **editing** only, and the
  routes at `app.py:2404`, `:2427`, `:5782` are unchanged.
  (test: `TestBookedEdit_OnlyEditingWasOpened`)
- **AC-8** (guard, the allow-list stays true): *Given* the new `needs_confirmation` answer, *then* the
  page may say "nothing was stored" for it **because** the route stores nothing — asserted by driving
  the real route and reading the row, not by listing the string.
  (test: `TestBookedEdit_TheFifthReasonIsTrueNotListed`)

## Guardrails

- G-1: The confirmation is **server-side**. An unconfirmed request must write nothing; a client-side
  dialog that then posts an identical request is not an implementation of this card.
- G-2: Editing is the only action opened. Approve, reject, restore and delete still refuse a booked
  puzzle (AC-7).
- G-3: A replacement grid never changes the stored extent (Trap 2).
- G-4: `EDIT_REFUSAL_REASONS` and the client's allow-list stay in step, and the new entry is **proved**
  not to write (Trap 3, CARD-246 G-001).
- G-5: `tell(text, offer)` stays the single writer of the message and the Approve offer; the
  confirmation does not become a second writer (CARD-246 F-001..F-005).
- G-6: Nothing here re-derives a difficulty, re-encodes clues or re-checks uniqueness outside the one
  solve the store already runs (ADR-0029/R2, CARD-246 G-3).
- G-7: No new runtime dependency (ADR-0006/R1); no framework or build step (ADR-0038/R1).
- G-8: No test retired without a named survivor (CARD-220's rule).

## System contract

_Assembled 2026-10-19 by `system_rules.py --card CARD-251 --root meta/architecture` (58 rules returned, `card_scope: touches`). A projection — fix the source artifact, never this list._

**Curated to 10; 48 dropped and declared.** Nearly all of the projection is scoped `src/nonogram/**` or `src/nonogram/admin/**.py` — package-wide, so it matches every card on this board and narrows to nothing. Owner decision 2026-10-17: ship the curated form with the dropped count stated. Kept below are the rules a reviewer can hold *this diff* against.

- **ADR-0006/R1** — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-
  party package joins the installed dependencies without revising this ADR. Non-executable
  static assets (fonts and similar data files) may ship as package data instead, and doing so is
  not a dependency change. (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- **ADR-0029/R2** — Technique classification and the strategies list are computed inside the one
  verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle's
  strategies list, and the tier is derived from that same list — no second derivation, no second
  solver entry. The ladder's fixed points are phases of that o… (check: test:
  TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- **ADR-0032/R1** — Every puzzle stored through the admin panel has been proved uniquely
  solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from
  the grid it was handed and refuses, with NotUniquelySolvable, any grid whose clues do not have
  exactly one solution — including one whose solve timed out or could not… (check: test:
  TestStorageBoundary_AsksTheSolverNotTheCaller)
- **ADR-0038/R1** — The puzzle player's client is hand-written JavaScript and CSS served as
  static files by the admin panel. There is no front-end framework, no build step, no npm
  toolchain and no vendored third-party JavaScript library. Adding any of these reopens this ADR
  (and ADR-0006/R1 for vendored code). (check: review-lens)
- **ADR-0038/R6** — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a
  puzzle's solution grid to the browser. A public or reader-facing player must not send the
  solution before the puzzle is solved, and any public phase reopens this ADR (CON-021). (check:
  review-lens)
- **ADR-0038/R7** — Browser tests use pytest-playwright with Chromium, declared only in a dev-
  only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra.
  (check: review-lens)
- **ADR-0038/R8** — Browser tests run locally, against Chromium installed by `playwright install
  chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named
  skip reason visible in the run summary. They never pass silently. Once a CI pipeline exists,
  it installs Chromium (playwright install chromium) before running… (check: review-lens)
- **INV-008** — A published book's puzzle membership changes only after an explicit confirmation
  of that change (FR-038). (check: test: TestBookPublished_ConfirmedPuzzleChangeApplied,
  TestBookPublished_PuzzleChangeRequiresConfirmation,
  TestBookPublished_UnconfirmedChangeKeepsStatus)
- **INV-009** — A book's order is grouped by tier — every easy puzzle before every medium one,
  every medium before every hard one; within a level the order is the owner's arrangement,
  changed only by an explicit move inside that level (FR-041). (check: test:
  PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence,
  TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel,
  TestBookArrange_MoveAcrossLevelBoundaryRefused,
  TestBookArrange_MoveWithinLevelKeepsOwnerOrder,
  TestBookPdf_DifficultyOrderWithDividerPerLevel,
  TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- **CON-005** — The uniqueness check must never produce a false positive: a puzzle accepted as
  unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness
  property the whole tool depends on. (check: test:
  PropertyTest_Solver_NeverFalsePositiveUniqueness)

## Worktree notes

- **[This card reverses a rule this project recorded 24 hours before it was asked for]**
  `raw-requirements.md`, 2026-10-18: "Editing must follow that precedent — changing the grid of a puzzle
  a finalised book prints would re-paginate that book underneath its owner", carded as CARD-245 AC-4 and
  CARD-246 AC-7 and shipped. The owner has now asked for the opposite, behind a confirmation. That is
  the owner's call and the card implements it — but **the recorded reason was wrong about the
  mechanism**, and the correct one is what the blocking obligation above is for: a repaint does not
  re-paginate anything (the extent cannot change through the page), while a **regrade** does, through
  INV-009's tier grouping. Fixing the diagnosis is most of this card's value.
- **[TDD: true]** The guard being relaxed is pinned by shipped ACs in three test files. Write the new
  expectation first, watch the old assertion fail, and the retired claims are explicit rather than
  discovered at the AC gate.
- **[Why `architectural`]** It changes an invariant's reach, not a template. The complexity marker is
  what puts it on the quality-profile model (shared/skills-config.md rule 6).
- **[`app.py` and `db/**` are conflict hotspots]** Expect serialization against any sibling touching
  them; CARD-250 touches `app.py` only if it takes the non-recommended caching option.
- **[House rules]** `hypothesis` is not in the dependency baseline. Browser tests fail or skip loudly
  with a named reason (ADR-0038/R8). New browser tests go in `tests/test_puzzle_editor_ui.py` and must
  join its `PAGE_ISOLATION_DECLARATION` (CARD-235's glob cannot see that file).

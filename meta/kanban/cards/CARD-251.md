# CARD-251: A puzzle already in a book can be edited, behind a confirmation that names the book

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/251-edit-a-booked-puzzle
**Worktree:** ../PythonProject4-card-251
**Source:** owner's doc "Nonograms - Print layout" → "Puzzle editor", 2026-10-19 — item 5: "Add a possibility to edit puzzles that are already in the book with additional 'are you sure question'" (intake in `meta/architecture/inputs/raw-requirements.md`)
**Idea:** —
**Wave:** 47
**Depends on:** —
**Touches:** src/nonogram/admin/puzzle_review.py, src/nonogram/admin/app.py, src/nonogram/admin/static/puzzle_edit.js, src/nonogram/admin/templates/puzzle_edit.html, src/nonogram/admin/templates/_puzzle_table.html, tests/test_puzzle_edit_routes.py, tests/test_puzzle_edit_store.py, tests/test_puzzle_editor_ui.py
**Review score:** —
**Started:** 2026-10-19T10:39:26Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The decision that shapes this card — SETTLED 2026-10-19 (owner)

**An edit is refused when the new tier differs from the stored one, for a puzzle in a book.**
INV-009 is **not** amended: the invariant stands exactly as written, and this refusal is what keeps it
true. The owner chose this over giving INV-009 a regrade clause (re-place and renumber) and over a
book-staleness concept the model does not have.

The refusal is knowable at the **verify** phase, because that phase already computes the new tier. So
the owner learns it with the grade and before Approve — never as a surprise after storing.

### What that protects, checked rather than assumed

With the tier pinned (this decision) and the extent pinned (AC-5), the book's **structure** cannot move:
`print_order`'s grouping, INV-009's level runs and divider pages, the puzzle numbers 1..n, the band's
identity line and the difficulty dots all read the **stored tier** (`_draw_difficulty_dots` takes
`stored_tier`), and pairing requires equal tiers (`_pairable_tier`, INV-010).

### What it does NOT protect — measured, not inferred

**A repaint that keeps the tier and the extent can still split a two-up page and renumber the book
from there.** `compute_pair_layout` is computed **from the clues**, so a denser picture means deeper
clue gutters, a taller drawing, and at some depth the pair stops fitting. Measured on the Book 1
profile with two 10×10 easies, clue depth equal on both:

| gutter depth | result |
|---|---|
| 1, 2, 3 | pairs, cell 7.500 mm |
| 4 | pairs, cell **7.129 mm** (the shared cell has already shrunk) |
| **5** | **no pair — the page splits into two** |

A repaint from a sparse picture to a dense one crosses that in one edit, and every folio after it
moves. This is a **second mechanism** the owner's decision does not reach, because the question asked
was about the tier.

**SETTLED 2026-10-19 (owner): tell, do not refuse — it stays a warning.** The verify answer says when
an edit would change the book's page count, names the puzzle it shares the page with, and **Approve
remains available**; the confirmation repeats it. Refusing was offered and declined: it would block any
repaint that deepens a paired puzzle's clues, which is most real edits, and the owner's own principle
for the tier was "learn it at verify, with the grade".

**So this card carries two rules about one book, and they are deliberately different.** A regrade is
**refused** because it breaks an invariant the registry states (INV-009). A split pair is **announced**
because it breaks nothing — the book stays valid, it is one page longer, and the owner is the one who
decides whether that is acceptable for this edit. Do not "tidy" them into one behaviour.

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
- **AC-4** (boundary, the tier — **the settled rule**): *Given* a booked puzzle whose replacement
  grid grades into a **different tier**, *then* the **verify** answer refuses it, names both tiers and
  the book, offers no Approve, and nothing is stored; *given* a replacement that grades into the
  **same** tier, *then* it verifies normally. INV-009 is untouched by this card.
  (test: `TestBookedEdit_ARegradeInsideABookIsRefusedAtVerify`)
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
- **AC-9** (boundary, the page count — the mechanism the tier rule does not reach): *Given* a booked
  puzzle that shares a two-up page, *when* a replacement grid is verified whose clue gutters are deep
  enough that the pair no longer fits, *then* the verify answer **says the book's page count would
  change** and names the puzzle it shares the page with; **Approve remains available and an approved
  edit stores** — a warning, not a refusal (owner, 2026-10-19). Assert both halves: the words appear
  AND the save goes through, or the test passes equally against an implementation that refuses. The
  test drives the measured boundary: same tier, same extent, gutter depth 4 → paired, depth 5 → split.
  (test: `TestBookedEdit_ASplitPairIsAnnouncedBeforeApprove`)

## Guardrails

- G-1: The confirmation is **server-side**. An unconfirmed request must write nothing; a client-side
  dialog that then posts an identical request is not an implementation of this card.
- G-2: The tier refusal is enforced at the **store**, not only at the verify route — a save whose
  grid grades into another tier writes nothing even if it is posted directly (the same discipline G-1
  applies to the confirmation).
- G-3: The two book rules stay distinct: a regrade is **refused**, a split pair is **announced** and
  stores on Approve (AC-4 and AC-9). Collapsing either into the other is a change the owner declined.
- G-4: Editing is the only action opened. Approve, reject, restore and delete still refuse a booked
  puzzle (AC-7).
- G-5: A replacement grid never changes the stored extent (Trap 2).
- G-6: `EDIT_REFUSAL_REASONS` and the client's allow-list stay in step, and the new entry is **proved**
  not to write (Trap 3, CARD-246 G-001).
- G-7: `tell(text, offer)` stays the single writer of the message and the Approve offer; the
  confirmation does not become a second writer (CARD-246 F-001..F-005).
- G-8: Nothing here re-derives a difficulty, re-encodes clues or re-checks uniqueness outside the one
  solve the store already runs (ADR-0029/R2, CARD-246 G-3).
- G-9: No new runtime dependency (ADR-0006/R1); no framework or build step (ADR-0038/R1).
- G-10: No test retired without a named survivor (CARD-220's rule).

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
  INV-009's tier grouping. Fixing the diagnosis is most of this card's value — and it did not stop at one correction: the tier
  rule the owner chose closes the mechanism they were asked about, while a **second** one (clue depth
  splitting a two-up page) was found by measuring rather than by reasoning, and is handled by AC-9.
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

## Failure matrix

_Declared 2026-10-19, before any code was written (the `architectural` obligation). One row per
boundary × failure mode, each with the DECLARED behaviour. Wrong-but-declared beats undeclared._

| # | boundary × failure mode | DECLARED behaviour |
|---|---|---|
| F-1 | `POST /puzzle/<id>/edit` — the same **confirmed** save arrives twice (a double click, a retried write) | Both store. A verification is not consumed by a save (CARD-245), so the grid is still proved, the extent and the tier checks pass again, and the second save rewrites the same five derived columns and moves only `manually_edited_at`. No book state moves: an edit never writes `book_id`. |
| F-2 | the confirmation arrives for a puzzle whose **book changed underneath it** (joined a book, left one, or the book was published between verify and save) | The row is re-read at the save, so the save decides on the book **as it is now**, never on the verify's reading. Left the book → the flag is unnecessary and the save stores. Joined a book → the flag is required, and an unconfirmed save answers `needs_confirmation` and writes nothing. Published in between → the same one flag covers it (one flag, two sentences), so a confirmation given while the book was a draft still stores. Declared, not refused: the flag means "replace this puzzle's grid although a book prints it", which is as true of the newer book as of the older one, and what protects the book's *structure* — the tier check (AC-4) and the extent check (AC-5) — is re-run against the row as it stands. |
| F-3 | the process crashes **between verify and store** | Nothing is stored: the verify writes no row. The proof memo lives on the serving process's `PuzzleReviewService` and dies with it, so the next save answers `not_verified` and the owner verifies again — one solve, and nothing ungraded can be stored. Unchanged by this card. |
| F-4 | the **book's title cannot be read** — `get_book` answers `None` (a deleted row, a `book_id` the panel cannot resolve) or the title is blank | The flag is still required and still enforced at the store; the question names the book's **id** and says its title could not be read. The refusal is NOT widened to "may not be edited": the title is presentation, the guard is the flag. |
| F-5 | the page-count measurement — the book holds a member the **pairing walk cannot lay out** (`RuntimeError`), or the book has no readable print setup (`ValueError`) | The page-count effect is reported as **unknown**, in those words, and Approve stays available. An unmeasurable neighbour is no reason to refuse an edit the tier and the extent already permit, and claiming "the page count does not change" out of a failed measurement is exactly the lie the warning exists to prevent. |
| F-6 | the replacement **grades into another tier** for a booked puzzle | Refused at the **verify** (so the owner learns it with the grade, before Approve) **and** at the **store** (G-2), naming both tiers. Nothing stored, no Approve offered. |
| F-7 | the replacement's **extent differs** from the stored row's | Refused at the **store**, booked and unbooked alike (AC-5, G-5); nothing stored. The verify still grades such a grid — it writes nothing — which is unreachable through the page (the board cannot change size) and is declared here rather than guarded twice. |
| F-8 | a booked puzzle, **no confirmation**, and a grid that is not a puzzle at all | `needs_confirmation`. The flag is checked **first**, before the solve, precisely so that an unconfirmed call measures nothing and writes nothing (the INV-008 precedent). The owner learns the grid is not a puzzle at the verify, which is the phase that grades. |
| F-9 | `confirmed` arrives as `"true"`, `1`, `"yes"` or any other non-`True` value | Not a confirmation. The route reads `payload.get("confirmed") is True`, so only JSON `true` confirms. |
| F-10 | the **editor page** for a puzzle in a book the panel cannot name (the legacy `in_book` status with no `book_id`, or a migration's `""`) | 409, exactly as before this card. F-4's complement: the question must name the book, and where there is no book to name there is no question to ask — so the guard stays a refusal rather than becoming an unanswerable dialog. |
| F-11 | the confirmed save's **write fails** (the DB connection drops mid-write) | Unchanged by this card: the exception leaves the route, the page's answer is a 5xx with no reason, and `storeStateIsKnown` is false for it — the page says the store's state is not known here and asks for a reload. The new `needs_confirmation` answer does not join that class; it is proved not to write (AC-8). |

## Worktree notes (CARD-251 implementation)

- **STRUCTURE: the confirmation flag is `confirmed` in the save POST's JSON body, read as strict
  `True`, and enforced inside `PuzzleReviewService.save_edited_grid(..., confirmed=False)` before
  any solve** — the same parameter name and the same position in the method as INV-008 /
  CARD-131's (`book_manager.py:1286`, `:1465`), so an unconfirmed call measures nothing and writes
  nothing rather than doing half the work. The flag is a *body* field and not a query parameter
  because the editor already posts JSON and a confirmation that can be pinned to a URL is one a
  prefetch can give.
- **STRUCTURE: the three new store refusals are exceptions, not a change to the return shape**
  (`EditNeedsConfirmation`, `RegradeInsideABook`, `ReplacementExtentChanged`, all `ValueError`
  subclasses like `EditNotVerified` for the reason that class records). `save_edited_grid` keeps
  its `Optional[dict]` contract — `None` still means "no row an edit may touch" — so no shipped
  caller changes shape, and `app.py`'s existing `try/except` chain stays the one place a domain
  refusal becomes a code and a `reason`. The alternative, `book_manager`'s outcome dataclass, was
  not copied: that method had three outcomes to report and this one has one (the stored row), so a
  dataclass would have made every existing caller unwrap a success it already had.
- **STRUCTURE: a book this panel cannot NAME keeps the outright refusal.** `_holds_a_book` true
  with a falsy `book_id` — the legacy `in_book` status, or a migration's `""` — still leaves
  `_row_an_edit_may_touch` answering `None`, so the editor page and both POST routes refuse it with
  the `in_a_book` 409 they always did. The card's own reason: "'Are you sure?' with no object is a
  dialog to click through". This is also what keeps `in_a_book` a reason the edit routes still emit,
  so `EDIT_REFUSAL_REASONS`, the client's allow-list and the branch that words it all stay live
  instead of being retired (G-6, G-10).
- **STRUCTURE: the verify answer's `book` object is composed at the ROUTE, not in the store.**
  `puzzle_review` answers `book_id` (its own row's column) and nothing more; `app.py` adds the
  title, the status and the page-count effect, because a title is `book_manager`'s and the pairing
  geometry is `book_pdf_generator`'s, and `puzzle_review` imports neither (it imports only
  `book_plan`, for the one tier order).
- **STRUCTURE: the page-count effect is measured by running the REAL pairing walk twice** —
  `book_pdf_generator.print_order` then `BookPDFGenerator(book).puzzle_pages(...)`, once over the
  book's stored clues and once with the replacement's clues swapped in for the edited row. No
  second implementation of pairing geometry: INV-010 stays the layout's, and a change to
  `compute_pair_layout` moves this warning with it.
- **STRUCTURE: the question reaches the page through `tell` plus an in-page `role="alertdialog"`.**
  The sentence — the one that names the book — is written by `tell` and only by `tell` (G-7); the
  dialog carries its two static answers and nothing composed. `window.confirm` is never used, the
  rule Clear's and Cancel's confirmations already follow.

### TDD ledger — one line per criterion, with the red reason

- **AC-1**: test `TestBookedEdit_TheEditorOpensForABookedPuzzle` red→green — red as
  `assert page.status_code == 200` failing with 409 (`app.py:2891`'s `in_a_book` abort), and
  `test_the_page_names_the_book_that_holds_it` red as "the editor page says nothing about the book"
  (no `editor-book` paragraph existed).
- **AC-2**: test `TestBookedEdit_AnUnconfirmedSaveWritesNothing` red→green — red as
  `NameError: name 'EditNeedsConfirmation' is not defined`, then
  `TypeError: save_edited_grid() got an unexpected keyword argument 'confirmed'`.
- **AC-3**: test `TestBookedEdit_AConfirmedSaveStores` red→green — same `TypeError` on the keyword;
  the store returned `None` for every booked row.
- **AC-4**: test `TestBookedEdit_ARegradeInsideABookIsRefusedAtVerify` red→green — red as
  `NameError: name 'RegradeInsideABook' is not defined`, and at the route as
  `assert 'regrade_in_a_book' == 'in_a_book'`.
- **AC-5**: test `TestEdit_AReplacementKeepsTheStoredExtent` red→green — red as
  `NameError: name 'ReplacementExtentChanged' is not defined`; the shipped
  `test_a_resized_edit_moves_width_and_height` was green on the opposite behaviour and is retired
  with its survivors named in the new class's docstring.
- **AC-6**: test `TestBookedEdit_APublishedBookIsNamedInTheQuestion` red→green — red as
  `KeyError: 'book'` (no answer carried the book) and, before that, as an unhandled
  `EditNeedsConfirmation` escaping the save route.
- **AC-7**: test `TestBookedEdit_OnlyEditingWasOpened` red→green — red on its own control
  (`test_editing_the_same_puzzle_does_go_through`) with the unhandled `EditNeedsConfirmation`; the
  four refusals themselves were green from the start, which is the point of the class.
- **AC-8**: test `TestBookedEdit_TheFifthReasonIsTrueNotListed` red→green — red as
  `AssertionError: assert 'needs_confirmation' in ('not_unique', 'not_verified', 'in_a_book', 'not_found')`,
  then on each of the three reasons' row reads.
- **AC-9**: test `TestBookedEdit_ASplitPairIsAnnouncedBeforeApprove` red→green — red as
  `KeyError: 'book'` on the verify answer; the measured boundary (depth 4 pairs at 7.129 mm, depth 5
  splits) was re-measured on this worktree before the fixture was written and matches the card's
  table exactly.

**Written after their production code, and said so rather than claimed otherwise:** the browser
classes `TestBookedEdit_TheQuestionNamesTheBook` and
`TestBookedEdit_TheSplitPairIsWordedAsAWarning` were added once `puzzle_edit.js` already had the
flow (the red that drove that code was AC-2's and AC-8's at the route). Each is therefore shown
failing on a named mutant instead of on a missing implementation: M3 and M13 below.

### Mutants run, and what each did

| mutant | what it changes | result |
|---|---|---|
| **M1** | `save_edited_grid` drops the `_refuse_unless_confirmed_for_its_book` call | **killed** — 16 tests, including AC-2's three and AC-8's `needs_confirmation` row read |
| **M2** (M1's edge) | the confirmation is demanded even when `confirmed` is true | **killed** — 25 tests; AC-3, AC-6's store, AC-9's approved save. The claim "unconfirmed writes nothing / confirmed stores" is pinned on both sides |
| **M3** | `puzzle_edit.js` `post()` always sends `{ grid }` — the client keeps its dialog and posts an identical request | **killed** — `test_the_question_names_the_book_and_the_answer_stores` (the second request's `confirmed` is never true). This is G-1's own mutant |
| **M4** | the regrade refusal leaves the **verify** | **killed** — 5 tests, including "no proof is remembered for a refused regrade" |
| **M5** (G-2's own) | the regrade refusal leaves the **store** | **killed** — exactly 3: the F-2 path test and AC-8's `regrade_in_a_book`. Narrow, which is why the claim about it was narrowed to the path that reaches it |
| **M6** | the extent check leaves the store | **killed** — 7 tests, booked and unbooked |
| **M7** (M6's edge) | the extent is read off the row's `width`/`height` columns instead of its grid | **killed** — `test_the_extent_is_the_grids_and_not_the_rows_own_columns` |
| **M8** (the edge that bit) | the confirmation moves to **after** the uniqueness gate | **SURVIVED first**, then killed. The first version of `test_an_unconfirmed_save_measures_nothing_either` counted solves across a verify-then-save pair, which the proof memo makes a control that cannot fail. Narrowed to an unproved grid, with the confirmed call as the control that moves the counter |
| **M9** | `_page_count_effect` always answers `changes: False` | **killed** — AC-9's split test |
| **M10** (M9's edge) | the partner named is the edited puzzle itself | **killed** — AC-9's `partner == "second.png"` |
| **M11** | `_an_edit_may_touch` answers True for every membership | **killed** — 16 tests across all three files: the unnameable book's refusal, the `in_a_book` reason's liveness, the list row and the card |
| **M12** (M11's edge) | `_an_edit_may_touch` answers False for every booked row (the pre-card behaviour) | **killed** — 21 tests: AC-1, AC-3, AC-6, AC-9 and the control that the card offers Edit again |
| **M13** | the page's `{% if book %}` note never renders | **killed** — AC-1's two naming tests |
| **M14** (G-3's own) | the verify refuses with 409 when the page count would change — the collapse the owner declined | **killed** — AC-9's test and its `known` control. This is the mutant that proves AC-9 asserts BOTH halves |

Every mutant was applied from a byte-identical backup and `diff`-verified back
(`review:identical app:identical js:identical html:identical` after each run); the tree was never
left mutated across a pause.

### SCOPE+

- `SCOPE+ src/nonogram/admin/book_pdf_generator.py` — one additive module-level function,
  `puzzle_page_plan(book, puzzles)`: the pairing walk alone, no bitmap drawn. AC-9 has to ask
  `compute_pair_layout` itself or it is asking a model of it (INV-010 stays the layout's), and the
  walk's inputs are built by `BookPDFGenerator._payload`, which is private to that module. Putting
  the two-line wrapper where the walk lives keeps `app.py` from reaching into another module's
  private helper. Nothing existing was touched.

### What a reviewer should look at hardest

1. **M8's story** — the one claim that was wider than its mechanism, found by mutating rather than
   by reading. The narrowed test and its control are the fix; check the control really moves.
2. **The `in_a_book`/`needs_confirmation` split** — the decision that a book this panel cannot NAME
   keeps the old flat refusal. It is what kept `EDIT_REFUSAL_REASONS`'s fourth entry live rather
   than retired, and it is the one structural choice the card did not dictate.
3. **`_EDIT_ROUTES`' moved start marker and the widened reason scrape** in
   `test_the_refusal_vocabulary_is_load_bearing_on_both_sides` — a guard's own machinery was
   changed to see a second spelling (`_refused(reason, …)`). The residual is written down in the
   test; check the other direction (a vocabulary entry nothing emits) still bites.
4. **AC-9's measurement cost** — every verify of a booked puzzle now runs the pairing walk twice
   over the whole book. No timing was taken (the host may be running a gate); on a 150-puzzle book
   that is 150 `compute_pair_layout` calls per verify and may want a look.

### [Scope] orchestrator, 2026-10-19

Changed: `app.py`, `puzzle_review.py`, `static/puzzle_edit.js`, `templates/puzzle_edit.html` and the
card's three test files — **seven of the eight `Touches` entries** (`_puzzle_table.html` was predicted
and not needed). Plus **one file outside the prediction, declared as `SCOPE+`**:

**`src/nonogram/admin/book_pdf_generator.py` — a second declared conflict hotspot.** The change is one
additive module-level `puzzle_page_plan(book, puzzles)`; nothing existing was reordered or reshaped.
Read and accepted rather than waved through, for the reason the function's own docstring gives: AC-9
asks "would this edit split a page", and pairing is decided by `compute_pair_layout` **from the clue
sets**, so asking anything other than the real walk would be asking about a *model* of INV-010. A model
is exactly what the card's own measurement section warns against. No card is running beside this one,
so the hotspot carries no conflict risk today — the cost is that a reviewer must check it, which is
what this note is for.

**One thing in it for the reviewer:** it calls `generator._payload(puzzle)`, a private method of
`BookPDFGenerator`, from module level. That may be right — it is the same class — but a private call is
a coupling the card did not ask for, and it is worth a second opinion on whether the payload shape
should be reached some other way.

**Flagged by the agent and carried here because it is a real cost, not a nit:** every verify of a
**booked** puzzle now runs the pairing walk **twice over the whole book** — on a full book that is
roughly 150 `compute_pair_layout` calls per verify, on a path the owner waits on. No timing was taken
(correctly — the host was gating). The review is asked to judge whether the answer can be narrowed to
the pages that could possibly move.

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
**Review score:** 8.0 (cycle 1/3 — meets the number, two Important open, so the severity gate fails)
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
- **AC-6** (guard, published books): *Given* a puzzle in a **published** book, *then* the save requires
  the same server-side `confirmed` flag an INV-008 membership change requires — **the INV-008 *shape*,
  not a call into `book_manager`'s membership machinery** — and the question names the book **and says
  it is published**, so the owner is told which kind of book they are editing into.
  **AMENDED 2026-10-19 (orchestrator, review cycle 1 F-005).** As written, *"the confirmation it
  requires is the INV-008 one"* read two ways: routing through `book_manager`, or using an
  INV-008-shaped flag. The implementation took the second, which is the coherent one — **INV-008 governs
  book MEMBERSHIP and an edit moves none**, so routing an edit through a membership confirmation would
  be asserting a change that is not happening. `test_the_books_own_membership_rule_is_untouched` proves
  INV-008 still bites. The criterion is amended to what was built rather than left ambiguous, because an
  AC that reads two ways is the defect this wave has now produced on three separate criteria.
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
  **AMENDED 2026-10-19 (orchestrator, after fix cycle 1). The change is SIGNED, and the other direction
  is reachable.** *Given* two puzzles that each print on a page of their own, *when* a replacement's
  gutters are shallow enough that the pair now **fits**, *then* the same answer says the book gets one
  page **shorter**. Found by measurement while demonstrating the delta, not by review: on that input the
  shipped sentence said *"gets one page longer"* and had **no partner to name**. The card's own decision
  section was already direction-neutral — *"says **when** an edit would change the book's page count"* —
  so this amends the criterion to the decision it was always implementing, rather than widening either.
  **The delta is also proved to transfer to the whole interior**, against
  `BookPDFGenerator.interior_stream(...).page_count` rather than `app.py`'s own counter, so the
  cross-check is independent: 7 → 8 while the puzzle pages go 1 → 2. It holds because the guide is
  fixed, answers are one per puzzle and an edit adds no puzzle, the SOLUTIONS divider is one, and level
  dividers follow levels that **cannot move because AC-4 refuses a regrade at this same verify**.
  **CORRECTED 2026-10-19 (review cycle 2, F-001):** this amendment first said *"so retiring AC-4's
  refusal breaks that test rather than letting this sentence quietly become false"*. **That was false,
  and it was measured false** — removing the verify's regrade refusal kills five tests, every one of
  them AC-4's own, while the transfer test passes, and it **cannot** do otherwise because its three
  depth fixtures are all Easy, so no regrade is exercised there at all. Nor can the dependency be
  pinned from inside that class: a cross-tier replacement is **refused** by AC-4, so such a case would
  assert the refusal and be AC-4's test again. The transfer argument rests on AC-4 holding; **the
  guard for AC-4 is AC-4**.
  (test: `TestBookedEdit_ASplitPairIsAnnouncedBeforeApprove`,
  `…::test_the_puzzle_page_delta_is_the_whole_interiors_delta`,
  `…::test_a_replacement_that_lets_a_pair_fit_makes_the_book_shorter`)

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
- **STRUCTURE: a membership with NO BOOK IDENTITY keeps the outright refusal.** The predicate is
  `bool(book_id)` under `_holds_a_book`: true with a falsy `book_id` — the legacy `in_book` status,
  or a migration's `""` — still leaves `_row_an_edit_may_touch` answering `None`, so the editor page
  and both POST routes refuse it with the `in_a_book` 409 they always did. The card's own reason:
  "'Are you sure?' with no object is a dialog to click through". This is also what keeps `in_a_book`
  a reason the edit routes still emit, so `EDIT_REFUSAL_REASONS`, the client's allow-list and the
  branch that words it all stay live instead of being retired (G-6, G-10).
  **Said as the predicate rather than as "a book this panel cannot name"** (review cycle 1, F-005):
  a `book_id` pointing at a deleted row is equally unnameable and takes the OTHER branch — it IS an
  identity, so the edit is asked about, and the question names the id and says the title could not
  be read (failure matrix F-4). The seam is the identity, not the title.
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
  **It reports a DELTA and no absolute figures** (review cycle 1, F-001; orchestrator decision of
  2026-10-19). What the two walks count is PUZZLE pages, which is not the book's page count —
  `InteriorCounts.page_count`, the figure Finalise already shows for the same book, also counts the
  two-page guide, a divider per non-empty level, the SOLUTIONS divider and an answer page per
  puzzle (7 against 1 on AC-9's own fixture). The answer is now `added` alone, and the one claim
  made of it — that a puzzle page gained IS a book page gained — is **measured**, not argued:
  `test_the_puzzle_page_delta_is_the_whole_interiors_delta` walks the real interior on both sides of
  an approved save and holds the two deltas equal (7 → 8 while the puzzle pages go 1 → 2). It holds
  because every other term of the interior is fixed by the edit — the guide, one answer page per
  puzzle with no puzzle added, the one SOLUTIONS divider, and level dividers that cannot move
  because a regrade is refused at this same verify (AC-4). Retire AC-4's refusal and that test is
  what notices the sentence stopped being true.
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

## Worktree notes (fix cycle 1 — review cycle 1's ten findings)

Review cycle 1 scored **8.0** with two Important findings open. All ten are closed as `fixed` in
`meta/review/20261019T121439Z-CARD-251-cycle1.yml`, none dismissed. Nothing under `meta/` is
committed; the code and test changes are one commit on `card/251-edit-a-booked-puzzle`.

### F-001 (important) — the warning states a delta, and the transfer is MEASURED

The orchestrator's recorded decision was *state the delta, drop the absolute figures*, with one
obligation attached: **prove whatever transfer you state.** It is proved, so the words stay at "one
page longer" rather than retreating to "a puzzle page".

- `_page_count_effect` now answers `{known, changes, added, partner}`. `added` is
  `len(after) - len(before)` — signed — and `before`/`after` are **gone from the wire**, not
  renamed (`assert "before" not in pages and "after" not in pages`).
- **The transfer, measured rather than argued.**
  `TestBookedEdit_ASplitPairIsAnnouncedBeforeApprove::test_the_puzzle_page_delta_is_the_whole_interiors_delta`
  walks the REAL interior (`BookPDFGenerator.interior_stream(...).page_count`, asked of the export
  rather than of `app.py`'s `_interior_counts`, so the cross-check is independent) before the edit
  and after the approved save: **7 → 8, while the puzzle pages go 1 → 2**, and `after - before`
  equals the `added` the route announced. Both absolute figures are pinned in that test, so the two
  counts cannot be confused for one another again. Why it holds: the guide is fixed, answers are one
  per puzzle and an edit adds no puzzle, the SOLUTIONS divider is one, and level dividers follow
  levels that cannot move — a regrade is refused at this same verify (AC-4). That dependency is
  written into the test, so retiring AC-4's refusal breaks the test rather than the sentence
  quietly.
- `_page_count_effect`'s docstring asked *"Would storing this grade's clues change the book's page
  count?"* over something narrower; it now asks *"How many pages would storing this grade's clues
  add to the book?"* and states both the delta rule and the transfer.

### F-004, absorbed into F-001 — and the delta turned out to be SIGNED

"gets one page longer" was hardcoded beside a computed number. It is now derived
(`pageCountChange(added)`: `one page`/`N pages`, `longer`/`shorter`). Measuring for the test found
more than F-004 reported: **the delta can be negative, and that case is reachable.** Two depth-5
puzzles print on a page each; replacing one with the depth-3 grid lets the pair fit and the book
gets one page **shorter** — on which the shipped sentence would have said "the clues are too deep
for the page this puzzle is on … and gets one page longer", with no partner to name either. Pinned
by `test_a_replacement_that_lets_a_pair_fit_makes_the_book_shorter` (`added == -1`, measured on both
sides of the approved save) and by the `one page shorter` / `2 pages longer` shapes in the browser
corpus. The split sentence's mechanism clause was reworded to one that is true in both directions
("how deep its clues are decides whether the page it is on … holds two puzzles or one").

### F-002 (important) — failure matrix F-4's second half now exists

Fixed in the owner's favour, as directed. `namedBook(book)` in `puzzle_edit.js` is the **one place**
a book is named for all three surfaces — the question (`needsConfirmationText`), the grade's clause
(`bookNote`) and the editor page's paragraph (`puzzle_edit.html`, which had the same defect and was
the FIRST surface the owner meets). A readable title is named; otherwise *"a book whose title could
not be read (id <uuid>)"*. The id is printed in full: it is what the owner would have to quote to
find the row. Three new assertions drive it —
`TestBookedEdit_TheQuestionNamesTheBook::test_the_question_calls_an_unreadable_books_id_an_id`
(F-4's own row, and it re-checks that AC-6's "published" clause still composes with the new
wording), the `unknown` shape of
`TestBookedEdit_TheSplitPairIsWordedAsAWarning::test_the_five_shapes_say_five_different_things`, and
`TestBookedEdit_TheEditorOpensForABookedPuzzle::test_a_book_whose_title_cannot_be_read_is_named_as_an_id`
for the page. F-4 is left as declared: the code caught up to the row rather than the row to the code.

### The minors

- **F-003** — the `_EDIT_ROUTES` marker comment no longer claims a case the code does not realise.
  It now says what is true: no reason is emitted from inside those helpers today (`_refused` takes
  `reason` as a parameter and all three call sites are below `_edit_refusal`), the widening is
  forward cover over the whole POST surface, and the other direction still bites because
  `emitted == set(EDIT_REFUSAL_REASONS)` is an equality. Written as the convention for the next
  card: widen the slice when the surface grows, not when a reason goes missing.
- **F-005** — the seam stays (it is what keeps `in_a_book` live); the vocabulary is now the
  predicate. "A membership with no book IDENTITY" / `bool(book_id)` replaces "a book this panel
  cannot name" in `_an_edit_may_touch`, `_row_an_edit_may_touch`, `puzzle_is_editable`,
  `EditNeedsConfirmation.book_id`, `verify_replacement_grid`'s `Returns`, `EDIT_REFUSAL_REASONS`'
  note and the editor route — each saying that a `book_id` resolving to no readable book IS an
  identity and takes the other branch. STRUCTURE note 3 above carries the same correction.
- **F-007** — the cost is now stated where the reader meets it, in `_page_count_effect`'s own
  docstring: one row read per member (one `SELECT … WHERE id = ?` each in DB mode, ~150 on a full
  book) plus two pairing walks over the whole book, on every verify of a booked puzzle, a request
  the owner waits on. The two narrowings are **recorded as available and deliberately not taken** —
  `get_puzzles`' single `WHERE id IN (…)`, and starting the second walk at the edited puzzle's page
  since the greedy-forward prefix is provably identical. No timing was taken.
- **F-008** — the catch is narrowed to `(ValueError, RuntimeError)`, exactly what F-5 and
  `puzzle_page_plan`'s `Raises:` declare; F-5 needs no amendment. Two tests, because a narrowing
  nothing drives is prose: `test_a_defect_in_the_measurement_is_not_dressed_up_as_unknown` (a
  `TypeError` leaves the route instead of becoming a soft "unknown" with a log line) and
  `test_a_member_the_pairing_walk_cannot_lay_out_is_also_unknown`, which closes **F-5's untested
  `RuntimeError` arm**. The raise there is injected, and the test says why: no stored row reachable
  through this panel produces it — clue sets too long (`[[99]] * 10`), too few (`[[1]] * 3`),
  thirty-deep and absent were each tried, and `add_puzzle`'s gates and INV-006's 4.75 mm floor
  either refuse them or measure them fine. What F-5 declares is the ANSWER, and that is what the
  test drives.
- **F-009** — `_puzzle_table.html`'s comment now says a puzzle in a book the panel CAN name offers
  the control again, and that what offers none is a membership with no book identity. The file stays
  in `Touches` and is now touched.
- **F-010** — `tests/test_puzzle_editor_ui.py` grew the same `books` fixture
  `tests/test_puzzle_edit_routes.py` has (clears the module singleton on both sides);
  `TestBookedEdit_TheEditorOpensForABookedPuzzle._book` takes it instead of the app.
- **F-006** — already closed by the orchestrator's AC-6 amendment, which is in this card. No code
  change: the implementation was already the coherent reading.

### Mutants run in this cycle, and what each did

Every behaviour change was mutated. Each mutant was applied from a byte-identical backup and
`diff`-verified back after the run (`app.py:identical js:identical html:identical`); the tree was
never left mutated across a pause.

| mutant | what it changes | result |
|---|---|---|
| **M15** (F-001's own) | `_page_count_effect` reports a wrong number — `added = len(after) - len(before) + 1` | **killed** — all **6** tests of AC-9's class, including the transfer test (the interior's delta no longer equals the announced one) and the "no change" controls, which now announce one |
| **M16** (F-004's own) | `pageCountChange` returns `"one page longer"` whatever the delta — the hardcoded phrase, back | **killed** — `test_the_five_shapes_say_five_different_things` (the `-1` shape must read "one page shorter" and the `2` shape "2 pages longer") |
| **M17** (F-002's own) | `namedBook` falls back to `the book ${book.id}` — the shipped behaviour the finding is about | **killed** — **2** tests: the question's F-4 row and the grade clause's `unknown` shape |
| **M18** (M17's other surface) | the editor page's paragraph prints `{{ book.title or book.id }}` again | **killed** — `test_a_book_whose_title_cannot_be_read_is_named_as_an_id` |
| **M19** (F-008's own) | the catch is widened back to the six classes | **killed** — exactly 1: `test_a_defect_in_the_measurement_is_not_dressed_up_as_unknown`. Narrow by construction, which is the point: it is the only test that can tell the two catches apart |
| **M20** (M15's edge) | `changes` is hardcoded `True` while `added` stays right | **killed** — 3: the two "still pairs" controls and the one-puzzle book. `changes` is pinned independently of `added` |

**F-010 was not mutated and cannot usefully be**: the leak it closes is a cross-test ordering
hazard, so the mutant (dropping the exit clear) is green by construction on any single selection —
which is exactly why the reviewer filed it as latent rather than as a defect.

### Test selection, green

`tests/test_puzzle_edit_routes.py tests/test_puzzle_edit_store.py tests/test_puzzle_editor_ui.py` —
**393 passed, 4 skipped** (the 4 are the DB-mode class without `nonogram_test` on this host, as in
cycle 1; cycle 1's same selection was 389/4, and the three new route tests plus the two new browser
tests are the difference, one of the browser additions being a rename that grew assertions rather
than a new node). The browser classes execute rather than skip: cycle 1's own browser selection
(`-k 'TestBookedEdit_TheQuestionNamesTheBook or TestBookedEdit_TheSplitPairIsWordedAsAWarning or
TestBookedEdit_TheEditorOpensForABookedPuzzle or BookedPuzzleIsNotEditable or ReachableFromTheCard'`)
is **21 passed, 0 skipped**, up from 19. The full suite was not re-run — it is green on `119fc58`
and the gates own it.

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

**One thing in it for the reviewer, with the agent's own reason attached.** It calls
`generator._payload(puzzle)`, a private method of `BookPDFGenerator`, from module level. The agent's
stated reason is that the walk's inputs *need* `_payload`, so the two-line wrapper lives **where the
walk lives** rather than having `app.py` reach across a module boundary for a private. That is a real
argument — it trades a private call inside one module for a cross-module one — and it is why the
function sits in `book_pdf_generator.py` at all rather than in the card's own files. The review should
take it rather than inherit it: a private reached from module level in the same file is a different
thing from `app.py` reaching in, and only one of those was avoided.

**Flagged by the agent and carried here because it is a real cost, not a nit:** every verify of a
**booked** puzzle now runs the pairing walk **twice over the whole book** — on a full book that is
roughly 150 `compute_pair_layout` calls per verify, on a path the owner waits on. No timing was taken
(correctly — the host was gating). The review is asked to judge whether the answer can be narrowed to
the pages that could possibly move.

### [Build gate] FAILED (full, 985s) — attribution WITHDRAWN and re-opened · orchestrator, 2026-10-19

**EXIT=1, 5 failed, 8483 passed, 1 skipped.** All five are
`tests/test_admin_binding.py::…::test_a_request_addressed_to_this_machine_is_served`, and not one is an
HTTP-door assertion: every one died on
`psycopg2.errors.UndefinedTable: relation "puzzles" does not exist`.

**My first explanation was wrong and is withdrawn.** I wrote that the implementation agent had resumed
and was running tests in the same worktree, citing the gate's own `pytest procs before start: 2`. That
count was **self-matching**: it was `ps aux | grep -c "[p]ytest"`, and the invoking shell's own command
line contains the word, so it counted itself. The rewritten guard then reported **3 with nothing
running at all**, which is how the error surfaced. The true process count during gate 1 is **unknown**,
so the contention story has no evidence behind it.

What the failure signature does match is the **known `@ops` hazard already on this board**: wave 46
recorded the app's module-global engine surviving conftest's `DROP SCHEMA`, and the wave-46 smoke test's
first run died with `FATAL: database … does not exist` for the same family of reason — a connection
reaching the database outside the fixture that prepares it. That is a hypothesis, not a verdict, and it
stays open until the solo re-gate returns.

**The guard is fixed, and it took three attempts, which is the part worth keeping.** Version 1 matched
any command line containing "pytest" and counted its own shell. Version 2 anchored on
`python[0-9.]*` and matched **nothing**, because this machine's interpreter basename is `Python` with a
capital P. Version 3 matches on the *executable* (field 1) and was **verified both ways before use** —
2 while a run is alive, 0 when idle. The first two versions were written and trusted without that
check, which is the same defect in my tooling that this board files against cards: a control nobody
proved could fail, and then one that could only fail.

**Until the solo re-gate returns, this card has no gate verdict.** The red run above is evidence about
my instrumentation, not about `119fc58`.

### [Build gate] PASSED (full, 879s, SOLO) — orchestrator, 2026-10-19 · `119fc58`

**EXIT=0, first attempt of the solo run: 8488 passed / 1 skipped / 0 failed.**

**The count reconciles exactly.** `main` is **8394** collected; the branch is **8489**, so **+95** — and
the card's own three test files go **296 → 391**, also **+95**. Every test this card added is in its own
files and nothing else moved.

**Same commit, same database, red then green, no change to the tree.** That is the wave-45 CARD-248
pattern and it is recorded the same way: **a gate green only on its second attempt is not the evidence a
gate green on its first is.** Gate 1's five failures were therefore not about `119fc58`. Their
signature — `relation "puzzles" does not exist` raised inside a test that makes no database assertion —
belongs to the `@ops` family already on this board (wave 46: the app's module-global engine surviving
conftest's `DROP SCHEMA`; the wave-46 smoke test's first run dying on `FATAL: database … does not
exist`). The contention story I first reached for is withdrawn and the backlog item stands unchanged:
this is the third wave in which that hazard has cost a gate run.

**What the episode actually produced is a working guard**, after three tries, two of which were the
defect this board names in cards: a control that counted its own shell, then one that could only ever
pass. The third was verified in both directions before use and refuses a contended start outright.

### [Review 1/3] Score: 8.0 — 0 critical, 2 important, 7 minor, 1 info · [Severity gate] FAILS · [Review sync] 1 report

Report: `meta/review/20261019T121439Z-CARD-251-cycle1.yml`. Meets `min_score` and **does not pass**: two
Important are open and **Step 8f/8g emitted `deferred(cost)`**, so this cannot be the passing review —
the certification must run on the stable cycle.

**The card's spine was verified rather than inherited, and it holds.** G-1: `save_edited_grid` calls the
confirmation refusal as its **first** act after the row read, before the uniqueness gate, and the client
cannot reach a store without it — the browser test reads both request bodies off the wire. AC-8's fifth
reason is **proved** by driving the real route and reading the row back. AC-9 asserts **both** halves.
G-3's two book rules stay distinct. **M8's narrowed control really moves the counter** (`baseline` then
`baseline + 1`), and the reviewer swept all nine new controls for siblings of that shape and found none.
System contract 10/10. All six `STRUCTURE` decisions kept, including the `SCOPE+`: `_payload` is a
`@staticmethod` reached from **inside its own module**, there is no public payload builder, and `app.py`
reaches nothing private — accepted on its merits.

**[Review] F-001 (important) — a false number on the owner's decision path.** `_page_count_effect`
reports `len(puzzle_page_plan(...))`, which counts **only puzzle pages**, as *"the book's page count"* —
the term this codebase reserves for the figure that also counts the guide, one divider per level, the
SOLUTIONS divider and the answer pages (`InteriorCounts.page_count`, which is what Finalise already shows
for the same book). **Measured on the card's own AC-9 fixture: the verify answers `before: 1, after: 2`
while `interior_stream(...).page_count` is 7.** On a 150-puzzle book it is out by over a hundred, and it
contradicts what the same panel prints for the same book. Confirmed independently by the orchestrator
against `InteriorCounts`' own docstring. **The delta is right; the two absolute figures are false.**

**[Review] F-002 (important) — failure matrix F-4 is half-refuted.** F-4 declares the question names the
book's **id** *and says its title could not be read*. The id is named; nothing says the title was
unreadable — the only such text is a source comment. The owner reads *"This puzzle is in the book
3f2a1b0c-…"*, a bare uuid presented as a title. The load-bearing half (the flag is still required, the
store still enforces) does hold and is driven end to end.

**The seven Minors are mostly this wave's one family again**, and all are one-liners: a guard comment
one step wider than its mechanism (the `_EDIT_ROUTES` marker move is *safe* — the reviewer recomputed
both regexes with the old marker and got a byte-identical set — but its stated reason is a hypothetical
the code does not realise); "gets one page longer" hardcoded beside a computed delta; a docstring saying
"a book this panel cannot name" over an implementation of `bool(book_id)`; AC-6 reading two ways;
AC-9's cost recorded **only** in notes that are deleted at `done`; a catch of six exception classes where
F-5 declares two, the four undeclared ones being exactly the shapes a bug *in that helper* would take;
and a list-row comment that is now false.

**[Note] The `architectural` declaration obligation is currently unverifiable from history** — the
failure matrix and worktree notes are uncommitted (nothing under `meta/` is ever committed from a
worktree), so "declared before any code" rests on the agent's word plus the orchestrator's sync. Stated
rather than implied.

### [Decision] F-001 — drop the absolute figures, keep the delta (orchestrator, 2026-10-19)

The reviewer offered two closes: remove the figures and state the delta, or source `before`/`after` from
`_interior_counts` so the editor and Finalise agree. **Chosen: state the delta, drop the absolutes.**

- **AC-9 asks for the delta, not the absolutes** — *"says the book's page count would change and names
  the puzzle it shares the page with"*. Removing a false claim satisfies the criterion unchanged.
- **The alternative makes a cost the review already flagged worse.** F-007 records that every verify of a
  booked puzzle now reads the whole book row-by-row and walks the pairing twice; adding a full interior
  count to that path, on a request the owner waits on, buys two numbers the criterion never asked for.
- **The fix must prove the delta it states.** A split pair adds a puzzle page; whether that transfers
  one-for-one to the interior count depends on nothing else moving — and the tier is pinned, so level
  runs and their dividers cannot move. If that transfer can be shown, *"one page longer"* is honest; if
  it cannot, the message must say what was actually measured (a puzzle page) rather than borrow a term
  that means something larger. **Do not state a transfer you have not tested.**

### [Fix 1] declarations — orchestrator, 2026-10-19 · commits `46e5bfb`, `332f580`

**All ten findings closed.** 393 passed / 4 skipped in the card's three files (the 4 are the DB-mode
class without `nonogram_test`, as in cycle 1); the browser selection went 19 → 21. Six mutants, all
killed, each applied from a byte-identical backup and `diff`-verified back.

**The transfer was DEMONSTRATED, so the words stayed at "one page longer".** The brief required proof
rather than assertion, and `test_the_puzzle_page_delta_is_the_whole_interiors_delta` walks the real
interior — `BookPDFGenerator.interior_stream(...).page_count`, asked of the **export** rather than of
`app.py`'s own counter, so the cross-check is independent — and pins **7 → 8 while the puzzle pages go
1 → 2**. Why it holds is written into the test, and the load-bearing clause is that level dividers
follow levels that cannot move **because AC-4 refuses a regrade at this same verify**.

**⚑ And the sentence I wrote around that was itself a claim wider than its mechanism — refuted in
cycle 2 (F-001).** I wrote that retiring AC-4's refusal "breaks that test rather than letting this
sentence quietly become false", in the fix note, in the test's docstring **and inside AC-9's
amendment**. Measured: removing that refusal kills five tests, all of them AC-4's own, and the transfer
test passes — it cannot fail, because its three depth fixtures are all Easy. **A dependency I claimed
was made to fail loudly was made to fail nowhere.** Corrected at all three sites in `cf56185` and
above. This is the second time this wave a claim of mine inside an amended AC has been refuted by
measurement — the first was CARD-250's AC-7 "ignored in silence".

**⚑ The measurement found something the review did not: the delta is SIGNED and the negative case is
reachable.** Two depth-5 puzzles print on a page each; a depth-3 replacement lets the pair fit and the
book gets one page **shorter** — on which the shipped sentence said *"gets one page longer"* and had
**no partner to name**. Pinned by `test_a_replacement_that_lets_a_pair_fit_makes_the_book_shorter`
(`added == -1`, measured on both sides of the approved save), and the mechanism clause reworded to one
true in both directions. **This is the third time this wave a measurement taken to satisfy a brief found
a defect nobody had asked about** — CARD-250's MU-A and MU-J were the others.

**F-5's untested `RuntimeError` arm is closed, with its limit declared rather than hidden.** The raise is
**injected**: the test's own docstring records that no stored row reachable through this panel produces
it, and names the four shapes tried (clue sets too long, too few, thirty-deep, absent) — `add_puzzle`'s
gates and INV-006's floor either refuse them or measure them fine. Honest coverage of the declared
*answer*, and explicitly **not** coverage of a reachable cause.

**F-010 was not mutated, and the agent said so rather than skipping it quietly** — the mutant (dropping
the exit clear) is green by construction on any single selection, which is why the reviewer filed it as
latent rather than as a defect.

### [Decision] AC-9 amended for the signed delta (orchestrator, 2026-10-19)

The agent left AC-9 alone and put the question up: the negative direction is new behaviour, tested, but
the criterion is worded for the split case only and no failure-matrix row covers it. **Amended**, for
the reason that decides it: **the card's own decision section was already direction-neutral** — *"the
verify answer says WHEN an edit would change the book's page count"* — so AC-9's *given* was narrower
than the decision it implements, not narrower than the behaviour by design. Amending makes the criterion
say what the owner settled. No code changed; the behaviour and both tests already existed.

This is the **fourth criterion this wave** amended to read true (AC-5 and AC-7 on CARD-250, AC-6 and now
AC-9 here). That rate is itself a finding for the retrospective: criteria are being written narrower
than the decisions they serve, and it is the **measurement**, not the review, that keeps catching it.

### [Review 2/3] Score: 9.0 — 0 critical, 0 important, 3 minor, 1 info · **CERTIFICATION COMPLETE** · [Review sync] 2 reports

Report: `meta/review/20261019T130335Z-CARD-251-cycle2.yml`. **The certification cycle 1 deferred has
run in full**, which is the condition this card's merge depended on.

**16 mutants, 15 killed, 1 survived by declaration.** Every one applied from a byte-identical backup
and restored by writing the captured bytes back, md5 compared after each run (16/16), final `diff`
clean, `git status` unchanged, `git checkout` never used, the tree never left mutated across a pause.

- **The six fix cycle 1 reported as killed were RE-RUN, not inherited** — a certification carried on
  the fixing agent's own word is not a certification (CARD-250 cycle 3's precedent). All six killed,
  **with the kill counts reproduced exactly**.
- **The six spine targets cycle 1 verified by reading alone were mutated for the first time**: G-1's
  confirmation sitting *before* the solve (killed by cycle 1's own narrowed M8 control — so that
  control really does move), G-2 at both boundaries, the extent check, `_an_edit_may_touch`'s
  predicate (**16 kills across three files**), G-6's allow-list entry, and G-7's single writer.
  **INV-009's hold is now mutation-certified at both boundaries rather than read.**
- The one survivor is F-010's fixture mutant, which fix cycle 1 had **declared** unkillable by
  construction — the reviewer verified that declaration by measurement rather than accepting it.

**⚑ The one finding that matters is a claim of MINE, refuted by measurement.** I wrote — in AC-9's
amendment, in my fix note, and it was echoed in the test's docstring — that retiring AC-4's regrade
refusal would break the transfer test "rather than letting this sentence quietly become false".
**Removing that refusal kills five tests, every one of them AC-4's own, and the transfer test passes.**
It cannot fail: its three depth fixtures are all Easy, so no regrade is exercised there at all. And it
cannot be made to notice — a cross-tier replacement is *refused* by AC-4, so such a case would assert
the refusal and be AC-4's test again. **The guard for AC-4 is AC-4.** Corrected at all three sites.

**The reviewer asked the right question about severity and I am answering it on the record.** It filed
this Minor and wrote: *"escalate if the board holds a claim inside an AC to a higher bar than one in a
docstring."* **It does.** A docstring is read by whoever opens the file; an **acceptance criterion is
read at merge, by the AC/EC/G gate, and by every later card that inherits the area** — and this one
was written by the orchestrator while amending the criterion, which is the least supervised text on
the card. The finding stays Minor in the report (its gating halves all hold and are certified); the
*correction* was not optional.

**F-002, also worth the owner's eye rather than just the file's:** `changes` is a page-**count** key,
so a split the book's suffix **absorbs** is silent. Measured with the card's own fixtures — four Easy
10×10s at depths (4,4,4,5) plan as `[(1,2),(3,),(4,)]`, and replacing the first with the depth-5
picture plans as `[(1,),(2,3),(4,)]`: three pages either way, so nothing is said although that page
stopped holding two and the next puzzle moved off it. **Faithful to the decision as worded** (the owner
settled on the page *count*), now declared where the answer is built — and flagged here in case the
owner wants the wider question.

**No failure-matrix row is owed for the negative delta, and the reviewer said so plainly**: the matrix
is boundary × *failure mode*, and a measured negative delta is a successful measurement. F-4 and F-5
were both re-derived against the code as it now stands and both stand.

### [Build gate] merge gate — RED then GREEN, and the red one was a REAL finding · orchestrator, 2026-10-19

**Attempt 1 (858s): EXIT=1, 2 failed.** The guard read **0** before starting, so this run was genuinely
solo — the first red gate this wave that was neither contention nor my own instrumentation.

Both failures were in `tests/test_suite_profile.py`, and the second was a **knock-on** (it runs a
sandboxed sub-suite and asserts every outcome passed). The first: **the frozen `RENDER_HEAVY_SNAPSHOT`
no longer matched the grep that defines it**, because this card's route tests gained two mentions of
`RENDER_API_PATTERN` — `interior_stream` (fix cycle 1's transfer test, cross-checking the delta against
the export's own page count) and `puzzle_pages`, reached through `puzzle_page_plan`.

**That is the guard working exactly as designed.** Its own comment: *"frozen is only safe if drift is
loud… If a render call site is added to a new test file, this goes red and the snapshot (and the
profile) are restated **deliberately** rather than silently diverging."* Restated in `73bbacd`.

**⚑ Neither review cycle could have found this, and that is the point worth keeping.** Both were told
not to run the full suite — correctly, since the gates own it — so a cross-file registry invalidated by
the card's own test file was invisible to them. Two review cycles, a certification with 16 mutants, and
an AC/EC/G-grade sweep all passed over it. **The full suite is not a formality after the reviews; it
sees a class of thing the reviews structurally cannot.**

**One nuance recorded in the constant rather than left for the next reader: neither mention draws.**
`interior_stream` decides before it draws and the test reads `.page_count` off the plan without
iterating pages. The set is a **mention** grep by construction, so the entry is correct by its own
definition — but a share computed from this file's whole runtime **over-states** it, and
**CARD-218 and CARD-219 are sized against that figure.**

**Attempt 2 (866s, solo): EXIT=0, 8494 passed / 1 skipped / 0 failed.** The count reconciles exactly:
`main` 8394 collected → branch **8495**, **+101**, and the card's own three test files **296 → 397**,
also **+101**. Comparable with this branch's 879s build gate; the suite is ~104 → 102 ms/test while
gaining 101 tests.

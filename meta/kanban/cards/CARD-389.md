# CARD-389: A book's landing address is computed once — the bundle serves and the interior will print the same /b/<slug>, numbered in print order

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 2c (1d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner decision 2026-11-07 (one QR for the whole book): the code on the Play-online page opens `/b/<slug>`, "which lists the puzzles in book order", and each puzzle page says "Play puzzle 53 online". The architect pass found two ways the printed address and the landing page can disagree with the book, both measured below.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/player_bundle.py, src/nonogram/admin/print_specs.py, tests/test_player_bundle.py, tests/test_book_landing_address.py, docs/deploy/player.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The slug is NOT a new field. ADR-0041/R7 already decided (owner, 2026-10-24) that a book's public slug is a content hash of its puzzle keys, never stored and never a function of the title, and `player_bundle.book_slug` plus the `/b/<slug>` landing page (CARD-284) already exist and are deployed. A stored slug was weighed and rejected there for a reason that holds unchanged: a printed code cannot be re-pointed and a database can be re-seeded. So the printed address is `<the book's stored player domain>/b/<slug>`, computed. Collision with a puzzle key cannot happen: puzzles live under `/play/<key>`, books under `/b/<slug>`.

What is NOT yet true, read from the code on main (2026-11-07): `export_bundle` computes the slug over `book.puzzle_ids` in STORED order, while the interior prints `print_order(...)`, the level-grouped order (INV-009), and `print_order`'s own docstring says a book whose stored arrangement predates INV-009 "still reads back mixed". For a grouped book the two orders are equal and nothing moves. For a mixed legacy book the printed slug would differ from the one the bundle serves (a dead QR), and the landing page would number its tiles differently from the numbers the puzzle pages print ("Play puzzle 53" would name another puzzle). The landing tile numbers (`pages.js`, "numbered" = position in the book file) must be the printed numbers. ADR-0041/R8 states the rule; this card makes it true and testable before anything prints it.

**[G-3 ANSWERED BY MEASUREMENT 2026-11-07, orchestrator]** The author measured that a legacy book stored in MIXED order gets a new slug once the bundle follows print order, and asked whether that may happen. The only published bundle, `book/6578fe3f67.json` (160 puzzles, read from the deployed tree at `~/Documents/nonogram-reviews/deploy-2026-11-07/site`), lists its puzzles in three contiguous tier runs (easy 68, medium 57, hard 35): it is already in print order, so its slug does NOT move. A mixed legacy row can only be a pre-INV-009 book, none of which is published or printed, so the card computes print order for every book and no legacy pin or ADR is needed. The owner confirmed on 2026-11-07 that NO book has been printed yet, so no printed code can point at a slug this card moves; only an already-deployed bundle could matter, and the one deployed bundle is grouped. G-3 is closed: no legacy pin, no ADR.

## What to implement

1. **Measure first, and say what it showed.** Build a legacy mixed-order book fixture and a grouped one; compute the bundle's slug and the slug over `print_order`. State the result in the Worktree notes. Do NOT connect to the production database (`nonogram_poc`); the one published bundle (`6578fe3f67`, 160 puzzles, `docs/deploy/player.md`) cannot be re-derived here, so the owner is asked (see Guardrails G-3) before any book that is already exported changes slug.
2. **One implementation of the landing address.** A function in `player_bundle.py` (the module that owns `book_slug`) taking the book's rows in print order and its stored player domain and returning the landing URL, plus a short form for typing (the domain without its scheme, then `/b/<slug>`, e.g. `nonogram.adverax.io/b/6578fe3f67`). It returns `None` when the book has no stored player domain (`print_specs.stored_player_domain`): no domain means no address, never one built from a base nobody chose (the rule `docs/deploy/player.md` already records for the arrangement link). The interior card (CARD-390) calls this and re-derives nothing.
3. **The bundle follows print order.** `export_bundle` computes the keys for `book_slug` and for `book/<slug>.json`'s `puzzle_keys` from the book's rows in print order, so the landing's tile N is the page's puzzle N. The set must also agree: the interior numbers only puzzles it can draw and the bundle skips unreadable rows (`skipped`). Measure what each side skips; make the two sets the same one by one shared predicate, or make the book refuse to print and export (state which and why). A slug and a numbering that silently differ on one damaged row is the defect to remove.
4. **Docs.** `docs/deploy/player.md`: state that the printed shape is `/b/<slug>` only and that `/play/<key>` stays served but is not printed. The `qr-url-shapes` block there is held to `vercel.json` by a test; change prose only unless a test says otherwise.

## Acceptance criteria

- **AC-1** (happy, same slug): *Given* a finalized, level-grouped book, *then* the landing address function and `export_bundle` produce the same slug, and `book/<slug>.json` exists under it. (test: `TestBookLanding_PrintedSlugIsTheBundlesSlug`, which is the planned ref of ADR-0041/R8)
- **AC-2** (edge, legacy mixed order): *Given* a book stored mixed (medium, easy, hard, easy), *then* the slug is computed over print order on both sides, the book file lists keys in print order, and tile number i on the landing names the puzzle the interior prints as number i. (test: `TestBookLanding_NumbersMatchPrintNumbers`)
- **AC-3** (guard, grouped books do not move): *Given* a level-grouped fixture book, *then* its slug equals a literal captured from main BEFORE this change (written in the test). (test: `TestBookLanding_GroupedBooksKeepTheirSlug`)
- **AC-4** (negative, no domain): *Given* a book with no stored player domain, *then* the function returns `None` for both forms. (test: `TestBookLanding_NoDomainNoAddress`)
- **AC-5** (edge, short form): *Given* a stored domain `https://nonogram.adverax.io`, *then* the short form equals a literal in the test, with no scheme and no trailing slash. (test: `TestBookLanding_ShortAddressIsTypable`)
- **AC-6** (edge, damaged row): *Given* a book with one row whose grid is unreadable, *then* the bundle and the interior agree on the numbering of every puzzle after it, or the book refuses to export, as the Worktree notes state. (test: `TestBookLanding_ADamagedRowCannotShiftNumbers`)
- **AC-7** (guard, no answer leaks): *Given* the bundle, *then* the existing served-tree and bundle cleanliness tests stay green and `book/<slug>.json` still carries exactly `puzzle_keys`, `slug`, `title`. (tests: `test_bundle_is_clean_of_answers`, `test_served_tree_is_clean_of_answers`)

## Guardrails

- G-1: R7's recipe is untouched: prefix, separator, algorithm, truncation, case. Only the ORDER of the keys fed to it is made explicit (print order), and ADR-0041/R7 requires a new ADR for a change to the ordering. The architect's reading is that "book order" always meant the order the book prints in (R8 says so); if the measurement in item 1 shows a real grouped book whose slug moves, STOP and ask the owner, because that is the ADR case.
- G-2: The slug stays computed. No column, no migration.
- G-3: A book already exported and printed must not change slug silently. If the legacy-mixed measurement (item 1) shows any realistic book would, report it as an owner question rather than choosing.
- G-4: Read-only against the database (ADR-0041/R5); deterministic bundle bytes.
- G-5: No `player/**` edit (CARD-386 owns the shared-player assembly); the landing page is already numbered.

## System contract

- ADR-0041/R7 — slug recipe (check: `test_bundle_tree_and_clues_match_the_encoder`)
- ADR-0041/R8 — one QR, to the landing, printed slug is the bundle's (check: review-lens until CARD-391 flips it naming this card's AC-1 test and CARD-391's)
- ADR-0041/R5 — bundle read-only and deterministic (check: `test_export_is_readonly_and_deterministic`)
- ADR-0041/R2 — no solution in any public asset (check: `test_bundle_is_clean_of_answers`)

## Architecture context

- **FR:** FR-045 (public player and bundle).
- **ADR:** ADR-0041 R5, R7, R8.
- **Retires from CARD-210:** the "player_domain + key" link design (the per-puzzle printed link is gone); `stored_player_domain` and the no-domain-no-address rule stay.

## Worktree notes

**Measurement (item 1), on tests/test_player_bundle.py's real in-memory shelf, never the production database.** Slug over the stored order vs over `print_order`, unchanged main code: grouped 4-puzzle book (easy, easy, medium, hard) `d99a138bf3` = `d99a138bf3`; grouped 10-puzzle book (4 easy, 4 medium, 2 hard) `7b8dfb3d9f` = `7b8dfb3d9f`; the same four-puzzle fixture stored mixed (medium, easy, hard, easy) `d99a138bf3` stored vs `64b6f83d49` print. So a GROUPED book's slug does not move (G-1/AC-3 hold, no STOP); a legacy MIXED book's slug does move by construction, which is G-3's owner question (the one published bundle, 160 puzzles, could not be re-derived here). Also measured: `BookManager.add_puzzles_to_book` already stores a grouped order, so a mixed book exists only as a pre-INV-009 row.

**Item 3, the damaged row (decision and why).** Measured on the real `BookPDFGenerator`: `section_plan` keeps a row with an unreadable grid in its numbering, but `interior_stream` raises `RuntimeError` naming the puzzle (ragged, missing and empty grids alike), so the interior never prints such a book. The two sets are therefore not made the same set by a shared predicate; instead the bundle refuses the book: no `book/<slug>.json` is written for a book holding a row with no stored record or no readable grid, the row is named in `BundleReport.skipped` as before, and the book's readable puzzles stay in the library. `landing_address` raises `ValueError` for the same input. `export_bundle` previously wrote the book with the damaged row left out, which renumbered every later puzzle by one against the page.

**What changed.** `player_bundle.py`: `print_ordered_keys` (the one place rows become keys in print order, via `book_pdf_generator.print_order`), `landing_address` returning a `LandingAddress(slug, url, short)` or `None` with no domain, `BOOK_PATH`; `export_bundle` reads keys in print order. `print_specs.py` needed no change (`stored_player_domain` is the caller's: CARD-390 passes its result). Test oracles in `tests/test_player_bundle.py` (`provenance_violations`, `_book_order`) now state the expected order independently as print order. `tests/test_book_landing_address.py` is new and is listed in `RENDER_HEAVY_SNAPSHOT` (it matches the render grep through `interior_stream`). The sandbox test `test_the_outcomes_are_identical_with_and_without_the_log` mirrors only TRACKED files, so it reds on an uncommitted new render-matching module until the module is committed.

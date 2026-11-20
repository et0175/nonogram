# CARD-495: A stored "guess" row is Hard in the database filter too; the arrange row fits a phone

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/495-guess-filter-and-phone-buttons
**Worktree:** —
**Source:** owner 2026-11-20 ("yes, fix both"), on CARD-494 review F-005 and F-007.
**Idea:** —
**Wave:** 83
**Created wave:** 83
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/puzzle_review.py, tests/test_admin_tier_surfaces.py, src/nonogram/admin/static/admin.css, tests/test_book_arrange_play_link.py
**UI surface:** admin puzzle filter (tier); admin book arrange page on a phone
**Review score:** 9.6 (cycle 2/3 - CERTIFIED)
**Started:** 2026-11-20T07:48Z
**Closed:** 2026-11-20T08:39Z
**Actual:** 2c — ratio 2/1 = 2.0
**Merge commit:** cca388ba18c6a318758dbbebded83a1c4c3f41b3
**Blocked by:** —

## Why this card exists

1. **CARD-494 F-005.** `filter_puzzles`' database branch matched only the wanted tier's value and label, exactly; the in-memory branch reads every row through `tier_of_record`, which reads the retired "guess" as Hard (and any case or surrounding space). So on the live panel (database mode) a stored "guess" row appeared under no tier filter. Measured on sqlite 2026-11-20: Hard returned hard and Hard rows, not guess.
2. **CARD-494 F-007.** On a 390 px phone the arrange page's move and delete buttons ended 44 px past the puzzle card and the page scrolled sideways (426 px in 390); the 120 px preview lay over the info column. Measured 2026-11-20 with the panel's own stylesheets and Bootstrap.

## What to implement

1. The database branch matches every stored spelling `tier_of_record` reads as the wanted tier, compared trimmed and lower-cased (as the tier sort already does), derived from `_TIER_RANK_BY_SPELLING`, so the two branches cannot drift.
2. On a phone the arrange row stays inside its card at 320-820 px: preview at its 80 px column, the middle column may shrink, the info line wraps; at 480 px and under the title and the reader's link take their own rows (amended 2026-11-20 after review cycle 1, F-001: first cut at 360 px).

## Acceptance criteria

* **AC-1**: the same rows ("guess", "Guess", " GUESS ", "hard", "HARD", "easy") filtered for Hard and Easy give the same ids in the in-memory store and a SQLite-backed one; control: main's database branch reds it.
* **AC-2**: at the phone viewport the row's title and actions end inside the row and the page does not scroll sideways; control: main's admin.css reds it.
* **AC-3**: net test count 0.

## Guardrails

* **G-1**: a requested value that names no tier keeps the exact comparison (no widening on a typo).
* **G-2**: desktop arrange layout unchanged (the CSS sits in the existing max-width 820 px rule and a new 480 px rule).

## Worktree notes
Implemented by the orchestrator.

* **Item 1 / AC-1.** `filter_puzzles`' database branch now filters `trim(lower(difficulty_tier)) IN (...)` over the spellings in `_TIER_RANK_BY_SPELLING` that `tier_of_record` reads as the wanted tier ("guess" among Hard's), the form and table the tier sort already uses; a requested value naming no tier keeps the exact comparison (G-1). `func` added to the branch's local sqlalchemy import (the first run raised NameError). `PuzzleFilter.difficulty`'s comment now says both branches read a retired "guess" row as Hard. `test_the_filter_reads_a_stored_guess_row_as_hard` extended, not added: the same six spellings go through the in-memory service and a SQLite-backed one, and Hard and Easy must select the same ids in both. Control (main's puzzle_review.py): it reds, `{'database': {'p3'}} != {'database': {'p0', 'p1', 'p2', 'p3', 'p4'}}`.
* **Item 2 / AC-2.** admin.css, inside the existing `max-width: 820px` rule: the row's columns `2.5rem 80px minmax(0, 1fr) auto`, the preview `--thumb: 80px` (it stayed 120 px in an 80 px column), `.item-info` wraps with `min-width: 0`, `.item-title` `min-width: 0`; a new `max-width: 360px` rule puts the title and the reader's link on their own rows across columns 2-4. Measured with the panel's stylesheets and Bootstrap on CARD-490's capture of an ordinary book: before, at 390 px the actions ran to 401 px in a row ending at 357 and the document was 426 px wide; after, every descendant ends 13 px inside the row at 320, 360, 390 and 820 px and the document is exactly the viewport wide. Screenshots: ~/Documents/nonogram-reviews/CARD-495/arrange-phone-390-before.png, -390-after.png, -320-after.png. `test_the_url_stays_inside_the_row` (phone, 390 px) extended: the title and actions also end inside the row, and the page is no wider than the viewport. Control (main's admin.css): it reds, actions 369-401 px against a row ending at 357. The 360 px rule has no test of its own (the suite's phone viewport is 390 px); its evidence is the measurement above.
* **AC-3.** 10708 collected before and after; net 0.
* **Gate (unarmed, -o addopts= -rfs):** the arrange files (play_link, page_breaks, sort_by_size, size_filter, position), test_admin_design_tokens, test_admin_tier_surfaces, test_books_list_mobile, test_puzzle_edit_store: 405 passed, 0 skipped.

[Review 1/3] Score: 8.5, one gating finding, not certified. F-001 the 360 px rule left the reader's link in the shrinking middle column at 361-480 px: measured on a book with reader links, 21 px and 43 lines at 361 px, 35 px at 375, 50 px at 390 (main gave 107 px, with the row spilling); my screenshots used a book without links and the phone test checked containment only, so neither saw it. F-002 (medium) G-1 had no test on the database branch (a typo widened to every row, or by case, passed 759 tests); F-003 (low) the play-link docstrings still carried the pre-card 390 px figures; F-004 (low) the filter comment over-claimed: SQL `trim()` strips spaces only, so tab/newline padding reads as its tier in memory but not in the database; F-005 (info, pre-existing, out of scope by G-2) at 821-920 px the desktop row's content runs 6-90 px past the row, with no sideways page scroll. Both engines re-measured: SQLite and Postgres (the worktree's own _test database) select the in-memory branch's ids for 24 stored spellings and 18 requests except the tab/newline padding; no other query compares tiers in SQL.
Fix round 1 (orchestrator): F-001 the phone rule's breakpoint 360 -> 480 px (card item 2 and G-2 amended); measured on the suite's own live arrangement (reader links): link 116/156/171/186/210/276 px at 320/360/375/390/414/480, 141 px at 481 and 277 at 820 (middle column again), every row's actions 13 px inside, page width = viewport at all nine widths. `test_the_url_stays_inside_the_row` also requires the link to be at least 150 px wide at 390 px; controls: main's admin.css reds containment (actions 369-401 against 357), the 360 px first form reds the floor ("crushed: [50, 50, 50] px"). F-002 an "extreme" row added to the stored-guess test: "extreme" selects it and "Extreme" nothing, in both stores; control: a case-insensitive typo comparison on the database reds it. F-003 the docstring table and bullets carry the new 390 px figures. F-004 the comment now says the branches agree for case and space padding and not for tab/newline. Screenshots re-taken on a book with reader links: ~/Documents/nonogram-reviews/CARD-495/arrange-phone-{320,375,390,414}-links-after.png (the two link-less "after" shots of the 360 px form removed). After: the nine files 405 passed; collected 10708, net 0.

[Review 2/3] Score: 9.6, nothing gating, certified. F-001..F-004 closed and re-measured on all four books from 320 to 1024 px (the 481-820 px band every 20 px: narrowest link 141 px, 3 lines, at 481; desktop at 821 and 1024 px identical to main); the 150 px floor's two controls red; F-002's assertions red all five typo mutants across both stores; F-003's figures reproduce exactly; the 24-spelling probe on SQLite and Postgres agrees with memory except non-space padding. F-005 out of scope, unchanged. F-006 (info) the comment named tab and newline but a no-break space diverges too: fixed inline by the orchestrator ("any other whitespace"). F-007 (info) the 480 -> 481 px step (276 -> 141 px link, 3 lines) dips under the floor only at 481-489 px; not taken.

**Merge gate (orchestrator).** `make test-gate BASE=main` answered SELECTION: 9034 passed / 30 skipped (the expected unarmed count: 29 DATABASE_URL unset + 1 setrlimit) / 1 xfailed / 0 failed, plus 11 marked (wave_close_only) passed in the lifted files; the 2 owed marked tests run after the merge.

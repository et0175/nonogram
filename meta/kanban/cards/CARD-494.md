# CARD-494: The arrange page's continued label and warning-tinted "Not printed" line; the last "guess is a tier" passages

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/494-continued-label-and-guess-text
**Worktree:** —
**Source:** owner 2026-11-20 ("make these changes"), on the two questions left after wave 4: CARD-490 review F-003 and the three passages CARD-491 recorded outside its files.
**Idea:** —
**Wave:** 83
**Created wave:** 83
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/templates/book_arrange_puzzles.html, src/nonogram/admin/static/admin.css, tests/test_book_arrange_page_breaks.py, src/nonogram/export/__init__.py, src/nonogram/admin/puzzle_review.py, docs/GENERATION_ALGORITHM.md
**UI surface:** admin book arrange page (page labels, "Not printed" marker)
**Review score:** 9.5 (cycle 2/3 - CERTIFIED)
**Started:** 2026-11-20T06:45Z
**Closed:** 2026-11-20T07:32Z
**Actual:** 2c — ratio 2/1 = 2.0
**Merge commit:** 2f2b6d9e15743b9b2305d5cc5dbea509d617d20f
**Blocked by:** —

## Why this card exists

1. **CARD-490 F-003 (owner's call, 2026-11-20: change it).** When an unprintable puzzle splits a pair on the arrange page, the label "page 6 · two puzzles" is printed twice, which reads as two pages; and the "Not printed: cannot be drawn" line is styled exactly like a page label.
2. **CARD-491's leftovers (owner: fix them).** Three passages still describe `guess` as a fourth tier: `nonogram.export`'s `difficulty` field docstring ("four members, \"Guess\" among them", "cat-guess.pdf"), `PuzzleFilter.difficulty`'s comment in puzzle_review.py ("ADR-0025's four tiers included"), and docs/GENERATION_ALGORITHM.md §7 ("ADR-0025 (the fourth tier) replaced …"; "its error message lists all four tiers" — measured 2026-11-20: `parse_tier` lists easy, medium, hard).

## What to implement

1. A page label repeated after an unprinted row reads "page N, continued" (no "· two puzzles"); the label that opens a page is unchanged.
2. The "Not printed" line takes the warning colour token (`--color-warning`, 5.6:1 on surface) for its text and rules; no new colour literal.
3. The three passages and the doc's "all four" line say what is true today (ADR-0031: three tiers; `guess` is a strategy).

## Acceptance criteria

* **AC-1**: the re-label test asserts "page 6, continued" after the unprinted rows and "page 6 · two puzzles" exactly once; control: the old template reds it.
* **AC-2**: the marker's computed colour is the `--color-warning` token (checked the way the admin's existing computed-style tests check a token); control: drop the rule, it reds.
* **AC-3**: an ordinary book's arrange page byte-identical to main (no unprinted row reaches either change).
* **AC-4**: net test count 0.

## Guardrails

* **G-1**: the page plan, the marker's wording and `book_detail` unchanged.
* **G-2**: comment/doc edits only in the three passages' files; no code behaviour there.

## Worktree notes
Implemented by the orchestrator (the change is two template branches, one CSS pair and four comment lines).

* **Item 1 / AC-1.** `book_arrange_puzzles.html`: the label that opens a page is unchanged; the one repeated after an unprinted row is a separate `elif` and reads "page N, continued". `test_a_row_after_an_unprinted_one_says_its_page_again` now expects `["page 5 · Easy divider page", "page 6 · two puzzles", "page 6, continued"]`. Control C1 (main's template): that test reds, `assert [... 'two puzzles'] == [... '6, continued']`.
* **Item 2 / AC-2.** admin.css: `.page-break-divider[data-unprinted]` takes `color: var(--color-warning)` and its two rules `background: var(--color-warning)`. `test_an_undrawable_member_shifts_no_other_rows_page` now also collects every rule whose selector names `[data-unprinted]` (as tests/test_admin_design_tokens.py collects its rules) and asserts exactly those two, token-only. Control C2 (main's admin.css): it reds, `assert {} == {...}`. In Chromium (the branch's stylesheets served to the captured page) the marker's computed colour is rgb(133, 93, 0), equal to the resolved token; screenshots ~/Documents/nonogram-reviews/CARD-494/arrange-continued-{desktop,phone}.png.
* **Item 3.** `nonogram.export`'s `difficulty` docstring (three tiers; ADR-0031 retired "Guess"; `cat-hard.pdf`), `PuzzleFilter.difficulty`'s comment, docs/GENERATION_ALGORITHM.md §7's opening and its "lists all three tiers" (measured: `parse_tier('x')` says "supported tiers are: easy, medium, hard"). Comments and docs only. Two docs/how-it-works pages (05-difficulty-calibration, 06-exporting) quote the old docstring as past findings; left as they are.
* **AC-3.** CARD-490's capture script run on main and on the branch: the ordinary book (all sizes and the <=15 band) and the single-undrawable book byte-identical; the pair-straddle book differs in one line, "page 6 · two puzzles" -> "page 6, continued".
* **AC-4.** Collected over tests/: 10708 tests collected in 8.78s (no test added or removed).
* **Gate (unarmed, -o addopts= -rfs):** test_book_arrange_page_breaks.py + test_admin_design_tokens.py 34 passed, 0 skipped.

[Review 1/3] Score: 8.5, one gating finding, not certified. F-001 the new `PuzzleFilter.difficulty` comment said a retired "guess" row matches too; true of the in-memory branch only — the database query (the live panel's) filters on the tier's own spellings and leaves such a row out (measured on sqlite: hard+Hard returned, guess not); F-002 the stylesheet assertion missed two overrides that repaint the marker (a later `[data-unprinted="true"]` rule; a `.page-break-divider span` rule) and broke on a rule split over lines; F-003 (low) two docstring phrases still pointed at the retired tier; F-004 (info) the screenshots were shot without Bootstrap; F-005 (info, pre-existing on main) the database filter drops retired "guess" rows from every tier filter — owner's call. Template, CSS, AC-3 and AC-4 re-measured and held (the "continued" label never replaces a page-opening one across six scenarios and three size filters).
Fix round 1 (orchestrator): F-001 the comment now says the in-memory branch reads a retired "guess" row as Hard and the database query leaves it out. F-002 the assertion collects whole rules (split on `}`, so line breaks do not matter) whose selector names `data-unprinted` in any spelling or reaches into a `.page-break-divider`; mutants: the later attribute rule reds, the descendant `span` rule reds, the rule deleted reds, the same rule over three lines stays green; admin.css restored, no diff. F-003 "a tier value", "ADR-0025's tier existed"; the paragraph rewrapped. F-004 re-shot with Bootstrap loaded (the page's own CDN link let through): marker rgb(133, 93, 0) on the card's rgb(251, 248, 241), 5.6:1. test_book_arrange_page_breaks, test_admin_design_tokens, test_admin_tier_surfaces: 71 passed.

[Review 2/3] Score: 9.5, nothing gating, certified. F-001..F-004 closed and re-measured (guessfilter probe on both stores; seven override mutants including `@media`, `> span`, `div[data-unprinted="true"] !important` red; reformatted equal rules green; screenshots with Bootstrap, 5.56:1). F-005 stays the owner's question. F-006 (medium, non-gating) three overrides still passed: `!important` on the base divider colour, and a later equal-weight `.puzzle-list .page-break-divider` rule for colour or `::after` background. F-007 (info, pre-existing) on a 390 px phone the arrange row's move buttons run past the card edge; not this diff.
F-006 fixed by the orchestrator: the check now collects every rule naming `page-break-divider` or `data-unprinted`, asserts the selector set is exactly the base pair and the marker pair, that none carries `!important`, and pins the two marker bodies. Mutants: `!important` on the base colour, a later `.puzzle-list .page-break-divider` colour rule, the same for `::after`, a `.page-break-divider span` rule, a later `[data-unprinted="true"]` rule — each reds; the marker rule reformatted over three lines stays green; admin.css restored, no diff. The three files: 71 passed.

**Merge gate (orchestrator).** `make test-gate BASE=main` answered SELECTION: 10111 passed / 30 skipped (the expected unarmed count: 29 DATABASE_URL unset + 1 setrlimit) / 1 xfailed / 0 failed, plus 11 marked (wave_close_only) passed in the lifted files; the 2 owed marked tests run after the merge.

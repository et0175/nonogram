# CARD-492: Five small code-hygiene items: a script's hardcoded database, a helper's private imports, a private read, an upper-cased tier, and the margin minimum

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/492-code-hygiene
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 4 (cut 2026-11-20; premises re-read against main the same day). IDEA-035, IDEA-038, IDEA-054, IDEA-062, IDEA-044, each WSJF 3.08-3.85 and 0.125 d: bundled because each alone is below sizing.min_estimate.
**Idea:** IDEA-035, IDEA-038, IDEA-054, IDEA-062, IDEA-044
**Wave:** 83
**Created wave:** 83
**Deferred waves:** 0
**Depends on:** —
**Touches:** scripts/diagnose_postgres.sh, tests/helpers/admin_scripts.py, tests/test_start_admin_local.py, src/nonogram/admin/puzzle_review.py, src/nonogram/admin/app.py, src/nonogram/admin/print_specs.py, src/nonogram/admin/templates/puzzle_solve.html
**UI surface:** admin solve page (tier badge, tab title)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-035 (CARD-152).** scripts/diagnose_postgres.sh still greps for and suggests `nonogram_poc`, the defect CARD-150..152 removed from the other three scripts.
2. **IDEA-038 (CARD-152 F-005).** tests/helpers/admin_scripts.py imports private names from tests/test_start_admin_local.py (`_DOCKER_STUB`, `_PSQL_SHIM`, `_all_pairs`, …); renaming one breaks both suites.
3. **IDEA-054 (CARD-160 F-006).** app.py's `_board_page_payload` calls the private `PuzzleReviewService._as_readable_grid`.
4. **IDEA-062.** `puzzle_solve` passes `tier.value.upper()`, so the admin solve page's badge and tab title say "MEDIUM" where every other screen shows "medium".
5. **IDEA-044 (CARD-154).** `PrintSpecValidator.validate_margins` refuses nan/inf but accepts a margin below the 0.635 cm minimum ("0.5"). Unreachable from the UI today; a stored small margin makes Finalise fall back to "about N".

## What to implement

Re-verify each on main first; drop any already closed with one line in the notes.

1. diagnose_postgres.sh reads the database the way the other three scripts now do.
2. The shared names move to the helper (or a shared module) and both test files import them from there; no test file imports another test file's private name.
3. A public read on `PuzzleReviewService` (or a module function), and the route uses it; `_as_readable_grid` callers inside the class unchanged.
4. The solve page shows the tier as stored. Check every test that pins "MEDIUM"/upper-case and the public player (which must stay untouched, CARD-452 redid its title).
5. `validate_margins` refuses a value below the minimum with a message naming it; the minimum comes from the existing constant if there is one (find it), not a new literal.

## Acceptance criteria

* **AC-1**: one control per item where a test can hold it (items 3 and 5 each red when reverted; item 4's page test reds on `.upper()`); items 1 and 2 by a recorded run (`bash -n`, the two test files green).
* **AC-2**: the public player's pages and payloads byte-identical to main's (assemble and diff), since app.py and a template change.
* **AC-3**: net test count at most +2; report it.

## Guardrails

* **G-1**: the store's single solver call site rule (`test_there_is_exactly_one_solver_call_site_in_the_store`) still holds; puzzle_review.py gains a read, not a solve.
* **G-2**: gate: `make test-gate` (app.py changes widen it; take what it selects).

## Worktree notes

# CARD-503: Registry wording owed: INV-009's "move", AC-343's 24 px floor, FR-044's two unstated player rules

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/503-registry-wording
**Worktree:** ../PythonProject4-card-503
**Source:** roadmap wave 6 (cut 2026-11-20 on the owner's "please start the next wave"; premises re-read against main the same day). IDEA-159, IDEA-167, IDEA-064 (WSJF 2.31 each); bundled as registry amendments.
**Idea:** IDEA-159, IDEA-167, IDEA-064
**Wave:** 85
**Created wave:** 85
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/domain/aggregates.yml, meta/architecture/requirements.yml, meta/architecture/trace.yml, tests/test_check_ref_resolution.py
**UI surface:** —
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-20T15:14Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-159 (CARD-191).** aggregates.yml INV-009 says a level's order is "changed only by an explicit move"; EC-026 already says reorder. Its AC-7 wording should say a DB-mode unsized puzzle is an id with no row. Re-read 2026-11-20: "explicit move" still there.
2. **IDEA-167 (after CARD-193).** requirements.yml AC-343's `given` still says "(cells at the 24 px phone floor)"; CARD-193 removed that flat floor and CARD-196 made it numeral-driven. Re-read 2026-11-20: still there.
3. **IDEA-064 (wave-31 goal check).** FR-044 leaves two player rules unstated: a drag follows the line of its FIRST move away from the start cell, and board cells are pointer-only, while the statement says "every control" is keyboard-reachable (AC-310 covers only tools, undo, redo and reset).

## What to implement

1. Reword INV-009 and its AC-7 as above.
2. Reword AC-343's `given` to the floor the code applies today (read it from the player CSS/JS by name, not from memory).
3. Add the two FR-044 rules as ACs, each naming an EXISTING test that pins it (find it by `ast`; if none pins one, say so and use the honest form from memory "ADR check refs must be honest": no invented test name), and narrow the "every control" statement so it no longer contradicts pointer-only cells.

## Acceptance criteria

* **AC-1**: the forge validator (forge_1 copy, `--phase all`) reports 0 errors before and after.
* **AC-2**: every new `test:` name resolves to one `def` (ast); tests/test_check_ref_resolution.py green, any frozen class re-derived as a set, never pasted.
* **AC-3**: each new AC's test reds when the rule it names is broken (one plant per rule, on a scratch copy).
* **AC-4**: net test count 0.

## Guardrails

* **G-1**: no product code change; if a rule is not what the code does, stop and report.
* **G-2**: trace.yml and requirements.yml agree on every AC this card touches.

## Worktree notes
Implemented by a card agent (2026-11-20).

* **Premises re-measured before editing** (a scratch `git archive` copy under /private/tmp/claude-501/card503/copy, its run importing the copy's `src/nonogram` and `tests`, printed by a probe test). (a) Drag: start (1,2), first move to (1,3), then to (8,3) marks only (1,2),(1,3) — the first move fixes the row and the later position is projected onto it, as `solver_state.js` `dragLine` says (the row on a tie: `>=`). (b) **Board cells are NOT pointer-only.** The board stage (`.player-stage`, tabindex 0) is reached by Tab; arrow keys move a cursor cell, Space/Enter mark it with the brush (the click rules), X marks White, Delete/Backspace clears — the keydown handler on the stage in `solver.js`, from the 2026-11-17 pass-2 review (item 5). Measured: Tab reached the stage, ArrowRight x2 + ArrowDown + Space marked (1,1) filled. So item 3's second rule is false and, per G-1, **not written as an AC**; FR-044's "Every control is reachable from the keyboard" is not contradicted and is **left as it is**. No test pins that keyboard play (`ast`/text search over tests/: only `test_the_page_copy_describes_the_new_click` pins its help sentence) — for the orchestrator: an AC for it would need a test, which this card's budget does not add.
* **INV-009** (aggregates.yml): "changed only by an explicit move" -> "changed only by an explicit reorder inside that level — a move or Sort by size". `BookManager._move_within_level` and `BookManager.sort_puzzles_by_size` are the two callers of `reorder_puzzles` (`ast`). **AC-7 not edited:** it is CARD-191's own card criterion, with no home in the registry (no AC in requirements.yml names sort-by-size or `TestArrangeSortBySize_*`), and CARD-191.md is outside this card's Touches. The fact it wanted said holds in code: `db/models.py` declares `width`/`height` `nullable=False`, so in DB mode an unsized puzzle can only be an id with no row (`_size_of` answers None for it). EC-029 still says "an explicit move within that level" — same word, not in this card's scope; recorded, not changed.
* **AC-343** (requirements.yml): given now reads "cells at the column-numeral floor — the widest column number's digits × 0.6 × the 12 px numeral minimum, 14.4 px for its two-digit numbers". From admin.css by name: at <= 820 px `--player-cell-min` is 0, so the floor is `--player-col-floor` = `--player-col-digits` x 0.6 x `--player-numeral-min` (12px); `TestSolverMaybe_GlyphIsLegibleAtTheMinimumCell` measures 14.39 at 390. Test unchanged. trace.yml's FR-044 note that flagged the stale given gains a closing line.
* **AC-422 (new, FR-044)**: a drag's line is fixed by its first move away from the start cell; FR-044's drag sentence says the same. Test: `test_PropertyTest_SolverHistory_ReplayReproducesTheBoard` (EC-035's corpus; one `def` in tests/test_puzzle_solver_marking.py by `ast`). No example test pins this rule: under the plant below every `TestSolverMarking_DragMarksOneLine` case and every `TestSolverHistoryModule::test_drag_line` case stayed green (20 passed); only the corpus, whose independent `_line_cells` fixes the axis from the first path cell, reds. Named it rather than adding or changing a test (AC-4).
* **G-2**: FR-044's trace.yml row spelt that test `PropertyTest_SolverHistory_ReplayReproducesTheBoard` (no def by that name; it resolved to the prefixed def). Re-spelt as the def, so the row and requirements.yml name AC-422's (and EC-035's) test alike. AC-343's test is on the row already; FR-044 `_meta` gains `amended_2026_11_20`.
* **AC-1**: forge_1 validator `--phase all`: 0 errors, 104 WARN before; 0 errors, 104 WARN after, the same 104 findings (diffed by severity/file/locator/message).
* **AC-2**: frozen classes re-derived as sets with the module's own `_declared_refs`/`_verdicts`/`_fingerprint` (card498 snap.py), before vs after: FALSELY_DEAD 18 -> 17 (OUT `PropertyTest_SolverHistory_ReplayReproducesTheBoard`, IN none); CENSUS 599 -> 598 (OUT the same, IN none); TRACE_TESTS 509 -> 509 (OUT the unprefixed name, IN `test_PropertyTest_SolverHistory_ReplayReproducesTheBoard`); DEFINED 485 -> 484 (OUT the unprefixed name, IN none); BOOKKEEPING_ONLY, FALSELY_ALIVE, HONEST_DEAD (0), RESOLVED_FROM_AFAR unchanged, IN/OUT empty. Pins and their history comments updated in tests/test_check_ref_resolution.py.
* **AC-3 (control)**: plant on the scratch copy's `dragLine`: the axis re-decided by every path cell instead of fixed by the first. `test_PropertyTest_SolverHistory_ReplayReproducesTheBoard` reds on `assert step["board"] == "".join(s[0] for s in model.cells()), (index, op)` with `(1, ['drag', 'filled', [4, 10], [[9, 1], [9, 8]]])` (first move along row 4, then further down column 10) — `'uuuu...uufu' == 'uuuu...uuuu'`. Copy restored from HEAD (0 PLANT lines); the worktree was never planted (`git diff --stat` lists only the four Touches files and this card). One plant only: the second rule was not written.
* **AC-4**: 10711 collected before and after, net 0.
* **Gate (unarmed, `-o addopts= -rfs`)**: tests/test_check_ref_resolution.py, test_puzzle_solver_marking.py, test_puzzle_solver_maybe.py (AC-343's test), test_book_arrange_sort_by_size.py (INV-009's sort), and the files that read requirements.yml/aggregates.yml: test_cli.py, test_approval_guess_gate.py, test_book_page_packing_doc.py, test_book_pdf_band.py, test_book_pdf_two_up.py, test_grid_bound_agreement.py, test_orchestrator.py, test_public_player_pages.py, test_public_player.py, test_solver_strategies.py: 644 passed, 1 failed, 0 skipped. The failure was mine: `test_this_module_resolves_no_verifying_ref_at_all` — my pin comments spelt the corpus test's def name, which would revive it for the validator's text search; the comments now describe it without spelling it. tests/test_check_ref_resolution.py after: 26 passed, 0 skipped; all eight pins match the re-derived sets.

[Review 1/3] Score: 9.5, nothing gating, certified. Every changed statement read against the code: dragLine fixes the line at the first differing path cell (row on a tie); the stage keydown makes board cells keyboard-playable, so the pointer-only rule was rightly not written (G-1); AC-343's floor is --player-col-floor (14.4 px measured 14.39); reorder_puzzles has exactly two callers. AC-422's corpus test reds under two independent plants (re-decide per cell; decide by last cell) while all 20 example drag tests stay green. Frozen classes re-derived as sets: FALSELY_DEAD 18->17, CENSUS 599->598, DEFINED 485->484, TRACE_TESTS 509 (swap). Validator 0 errors before and after. F-001 (low) IDEA-159's AC-7 half dropped by decision (CARD-191's own AC, outside Touches); F-002 (low) EC-029 still says "explicit move", true but narrower than INV-009; F-003 (info) no test pins keyboard play on the board.

**Merge gate (orchestrator).** `make test-gate BASE=main` answered SELECTION: 5702 passed / 15 skipped / 9 deselected / 1 xfailed / 0 failed, plus 5 passed marked (8 marked owed at the wave close). The 15 skips: the selection's db_required tests (DATABASE_URL unset) plus the setrlimit platform skip.

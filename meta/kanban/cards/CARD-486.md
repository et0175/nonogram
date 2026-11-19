# CARD-486: The four CARD-183 hint minors, verified against today's ladder and fixed only where still live

**Status:** done
**Priority:** P3
**Category:** feature
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/486-hint-minors
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 3 (IDEA-149, WSJF 1.54, `verify_before_carding: true`); carried from wave 1, where it was held for verification.
**Idea:** IDEA-149
**Wave:** 82
**Created wave:** 82
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_hint.py
**UI surface:** admin solve page and public player (hint ladder)
**Review score:** 9.0 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-19T17:49Z
**Closed:** 2026-11-19T19:20Z
**Actual:** 1c — ratio 1/1 = 1.0
**Merge commit:** 5d62d5aeddf59a692264699c7f71bec8dcd4e161
**Blocked by:** —

## Why this card exists

CARD-183's review left four minors (F-011..F-014): two polite announcements per hint; Hint pressed by keyboard while the reset confirm is open moves focus to Reset; a 440 ms animation-test window; after Undo the announce region keeps the old hint's text. Since then the hint became a three-rung ladder (CARD-269), its text moved twice (CARD-409, CARD-455) and CARD-484 changed which cell it picks. None of the four was re-tested, so each may be moot.

## What to implement

1. **Verify first, in a real browser** (the player test fixtures), each of the four on today's ladder. Record per item: live or moot, with the command or test that showed it.
2. Fix only the live ones. A moot item gets one line in the notes and no code.
3. If all four are moot, the card closes with the notes alone.

## Acceptance criteria

* **AC-1**: each of F-011..F-014 has a recorded verdict (live / moot) backed by a browser observation, never by reading code alone.
* **AC-2**: every live item is fixed and has one control that reds when the fix is reverted.
* **AC-3**: owner's test budget: change existing tests rather than add; net test count at most +2; report it.

## Guardrails

* **G-1**: the ladder's rungs, wording and the cell CARD-484 picks are unchanged.
* **G-2**: the public player's pages and payloads change only if a live fix requires it, and then by the same edit as the admin (one source of truth, 2026-11-07).
* **G-3**: not published until the owner asks.

## Worktree notes

- [Verify] Each minor reproduced in Chromium through the suite's own fixtures (`browser_page`, `browser`, `live`, GRID from tests/test_puzzle_solver_marking.py) by a temporary probe test (tests/test_zz_card486_probe.py, deleted before commit; log at /private/tmp/claude-501/card486/probe.jsonl), on the branch base before any edit. Live regions on the page: #puzzle-player-announce, #puzzle-player-errors, #puzzle-player-hints (every `[role=status]`/`[aria-live]` not `off`), each watched with a MutationObserver.
- [Verify] F-011 — LIVE, CLOSED BY OWNER DECISION, no code change (see [Owner] below). Rungs 1 and 2 each mutate one live region (#puzzle-player-announce: "Hint: look at the highlighted row 1 (clue 3 1 5 3)." and the rung-2 sentence); rung 3 mutates two: #puzzle-player-announce "Hint: row 1, column 1 is black." and #puzzle-player-hints "Revealed: 1". Both recorded fixes break a guardrail or an accepted rule: folding the count into the sentence changes the ladder's wording (G-1), and silencing the counter undoes CARD-183 item 4's own `role=status` counter (read by TestSolverHint_RevealsOneCell::test_one_click_reveals_the_oracles_cell) — and after the F-014 fix below that counter is the only region that says anything when a hint is undone ("Revealed: 0"). The order in which a screen reader queues the two was not measured (observer callbacks fire per observer, not in write order).
- [Verify] F-012 — LIVE, FIXED. Reset opened (focus on "Keep marks"), one Tab reaches Hint with the confirmation still open; Enter 1 and Enter 2 (rungs 1, 2) keep focus on Hint and the confirmation open; Enter 3 reveals one cell (Revealed 1), closes the confirmation and moves focus to Reset; Enter 4 reopens the reset confirmation (focus on "Keep marks") instead of pressing Hint. The same rule moved focus from a pressed Undo / Redo button to Reset (pinned by TestSolverProgress_ResetAfterConfirm::test_a_board_change_while_asking_closes_the_confirmation[undo-button] and [redo-button-noop]).
- [Verify] F-013 — LIVE as a window, FIXED (tests only). Both "does animate" controls still read a no-fill animation that ends: TestSolverHint_ReducedMotion::test_without_reduced_motion_the_hinted_cell_animates (player-hinted-in, 2 × 220 ms = 440 ms, two evaluates after the click) and ::test_without_reduced_motion_the_line_highlight_animates (player-hint-line-in, 8 × 220 ms = 1760 ms, four evaluates). Bounded only by runner speed: 12 probe runs measured 6.7–10.0 ms from the third click returning to the last read, animation currentTime 0 at the read — no flake seen, but nothing but latency holds the window shut.
- [Verify] F-014 — LIVE, FIXED. After a reveal both channels hold "Hint: row 1, column 1 is black."; after Undo the cell is undecided, Revealed 0, the visible line (#puzzle-player-explain) is "" and #puzzle-player-announce still holds "Hint: row 1, column 1 is black."; still there after a further Ctrl+Z, and after a hint followed by an ordinary mark.
- [Fix] F-014 — say() and rung 3's reveal (showProgress) note the sentence they wrote in the live region's `data-said`; solver.js `commit()` empties #puzzle-player-announce, before `player.commit` (so rung 3's reveal and the solved banner still write after it), while it still holds that sentence. A first version that cleared it on EVERY commit reddened TestSolverRegion_AnnouncesItsState::test_the_automatic_disarm_is_announced in the gate ("Region off." is written by the stroke itself before it is recorded); a second, comparing with the visible line, reddened test_undo_and_redo_buttons (any pointerdown dismisses the visible line first, wireExplainDismiss). Probe on the first version: after Undo, after Ctrl+Z, and after a mark, the announce region is ""; the final version is held by the control below.
- [Fix] F-012 — solver.js `closeConfirm(refocus = true)`; `commit()` passes `refocus` only when focus is inside the confirmation or on body. The rule as it behaves: when a recorded change closes the confirmation, focus returns to Reset only when it was inside the confirmation or on the page body; otherwise it stays where the user put it. Accept and Keep marks (inside) and Escape (closeConfirm called directly) still return it to Reset, and so does every TestSolverProgress_ResetAfterConfirm case that starts inside the confirmation or on body. [Review 1] F-002 corrected this note: with focus Tabbed out to Hint, Ctrl+Z, a pointer stroke or setBoard now leave it on Hint (main sent it to Reset), and a keyboard mark on the board keeps focus on the board, which on main lost it to Reset after each mark — the reviewer's probe, not re-run here. Probe re-run on the fix: Enter 3 reveals, closes the confirmation, focus stays on Hint; Enter 4 is rung 1 with the confirmation closed. PROGRESS "reset" header updated. The two button params of test_a_board_change_while_asking_closes_the_confirmation now expect focus on Undo / Redo (they redden on the fix with the old "Reset" expectation: `'Undo' == 'Reset'`, `'Redo' == 'Reset'`).
- [Fix] F-013 — the two controls inject `animation-play-state: paused !important` for .is-hinted / .is-hint-line before the press (`_PAUSED`), so name, count and keyframes are read off an animation that cannot end. The reduced-motion test itself is unchanged and reads the page as shipped.
- [Controls] Each fix reverted one at a time by a driver (/private/tmp/claude-501/card486/mutate.py; file restored after each run, sha1 identical): F-014 revert (commit no longer clears announce) → TestSolverHint_IsOneUndoableStroke::test_undo_and_redo_buttons FAILED, `assert 'Hint: row 1, column 1 is black.' == ''`. F-012 revert (`closeConfirm()` always refocuses) → TestSolverHint_KeyboardAndNoRequest::test_keyboard_and_no_request FAILED, `Space — assert 'Reset' == 'Hint'`. F-013: a 600 ms / 2000 ms stall inserted before the reads → both controls 2 passed with the pause; with the pause removed and the same stall → both FAILED (`assert 0 == 1` on getAnimations().length).
- [G-1] Ladder rungs, sentences and the revealed cell unchanged: the probe's rung texts and revealed cell are identical before and after the fix; no solver_state.js change; the whole hint file passes in the gate below.
- [G-2] solver.js is the one source: scripts/assemble_player_site.py copies it to the public player at build time, so both fixes apply to the public player by the same edit; no template, payload or solver_state.js change.
- [G-3] Not published.
- [Tests] Net test count 0: `--collect-only -q -o addopts= tests/` → base (HEAD tree) 10701, branch 10701. Changed, not added: test_undo_and_redo_buttons, test_keyboard_and_no_request, the two "does animate" controls, test_a_board_change_while_asking_closes_the_confirmation.
- [Gate] player-card selection (tests/test_puzzle_solver_*.py, tests/test_player_*.py, tests/test_public_player*.py, tests/test_puzzle_editor_ui.py, tests/test_browser_fixture_scope.py, tests/test_cli.py, tests/test_kanban_review_record.py, tests/test_suite_profile.py; `-o addopts= -rfs`): first run 1 failed, 1744 passed (the Region-off red named under [Fix] F-014); after the fix was narrowed 1745 passed, 0 failed, 0 skipped. Full suite not run (player-card rule).
- [Owner] F-011 (owner, 2026-11-19): "Keep both" — the revealed hint keeps both announcements, the hint sentence in #puzzle-player-announce and the role=status "Revealed: N" counter. Closed by decision.
- [Review 1] Score 9.0, certified. F-001: the `|| document.activeElement === document.body` clause had no control. The undo-key case of TestSolverProgress_ResetAfterConfirm::test_a_board_change_while_asking_closes_the_confirmation now blurs focus to body first (asserted) and still expects Reset; test changed, none added. Clause removed in place → that case FAILED `assert None == 'Reset'` (1 failed, 13 passed in the class); solver.js restored, sha1 identical, no diff.
- [Review 1] F-003 (info, from the review): the F-014 fix also clears Check's sentence from the live region on the next stroke; a Redo of a reveal is silent in the announce region (the counter still changes); the wrong-guess offer text (openOffer writes no data-said) still survives the next commit, as on main.
- [Review 1] Results: tests/test_puzzle_solver_progress.py + tests/test_puzzle_solver_hint.py `-o addopts= -rfs` → 106 passed, 0 skipped; `--collect-only -q -o addopts= tests/` → 10701 (net 0).

[Review 1/3] Score: 9.0, nothing gating, certified. Ten mutants on archive copies, one per fix branch: every one reds a named test except the body-focus clause (F-001, fixed in `a76b5bc4`: the undo-key case now starts with focus on body and reds without the clause). F-012's Undo/Redo focus change judged correct (it matches `test_a_board_change_with_the_confirmation_closed_leaves_focus_alone` and also stops keyboard marking losing focus); F-014 wipes no new announcement and leaves no hint text standing; F-013's pause still discriminates (0 s duration and a removed animation each red). F-002 a note overclaimed which paths return focus to Reset: reworded in `eeeb0d32`. F-003 info recorded. F-011 closed by the owner's decision 2026-11-19 ("Keep both"). Public player gets the same solver.js by byte copy; nothing else public changes. Net test count 0.

**Merge gate (orchestrator).** `make test-gate BASE=main`: 1 failed / 7773 passed / 30 skipped (the expected unarmed count) / 1 xfailed, plus 7 passed marked. The one red, `tests/test_book_landing_page.py::test_the_way_back_from_a_puzzle_keeps_the_sections_and_the_place`, reds on main too and is outside this card.

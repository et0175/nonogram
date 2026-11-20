# CARD-504: Nine stale texts: docstrings, comments, a README version, a script message, a test helper's name, a narrow regex

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/504-stale-texts
**Worktree:** —
**Source:** roadmap wave 6 (cut 2026-11-20 on the owner's "please start the next wave"; premises re-read against main the same day). IDEA-026, 027, 030, 037, 039, 102, 134, 145, 197 (WSJF 2.31 each, each about 0.125 d: bundled because each alone is below `sizing.min_estimate`).
**Idea:** IDEA-026, IDEA-027, IDEA-030, IDEA-037, IDEA-039, IDEA-102, IDEA-134, IDEA-145, IDEA-197
**Wave:** 85
**Created wave:** 85
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/export/book_pdf_generator.py, src/nonogram/admin/book_proof.py, src/nonogram/admin/app.py, src/nonogram/web/__init__.py, scripts/README.md, scripts/*.sh, scripts/measure_difficulty_cutoff.py, tests/test_book_pdf_band.py, tests/test_difficulty_tiers.py, tests/test_start_admin_local.py, tests/test_admin_tier_surfaces.py
**UI surface:** —
**Review score:** 9.7 (cycle 2/3 - CERTIFIED)
**Started:** 2026-11-20T16:30Z
**Closed:** 2026-11-20T18:12Z
**Actual:** 2c — ratio 2/2 = 1.0
**Merge commit:** 38d9eb58b164338bebbcc389bf02ba8bca0e1337
**Blocked by:** —

## Why this card exists

Each re-read against main on 2026-11-20 unless marked:

1. **IDEA-026 (CARD-135 F-008).** `export_book`'s docstring (or the comment beside it) claims every route goes through it.
2. **IDEA-027 (CARD-134).** `answer_page_number()` in tests/test_book_pdf_band.py encodes one answer page per puzzle in its name (7 occurrences).
3. **IDEA-030 (CARD-155 F-005).** test_difficulty_tiers.py's docstring regression regex catches only uppercase `GUESS` and "or Guess", not a lowercase "guess" used as a tier.
4. **IDEA-037 (CARD-152 F-006).** The "not reachable" message names only two causes (server down, database missing), not a wrong host, port or credentials; same wording in several scripts.
5. **IDEA-039 (CARD-152 F-007).** scripts/README.md says "Python 3.11+" (pyproject requires 3.14); a stale docstring in tests/test_start_admin_local.py (find it by the claim, not the old line number).
6. **IDEA-102 (CARD-170 F-007).** tests/test_book_pdf_band.py's class docstring states the "no other ink within about a line's height sideways" rule loosely.
7. **IDEA-134 (CARD-179 F-003).** book_proof.py `_wrapped`'s docstring does not say the token after an over-wide × is taken as M.
8. **IDEA-145 (CARD-181).** `requested_tier_label`'s docstring says `None` for any non-tier, but "guess" reads Hard; no test pins `Tier.label`; migration 014's "no puzzle row touched" claim is untested.
9. **IDEA-197 (CARD-264).** src/nonogram/web/__init__.py's docstring says the structural guard knows "exactly two adapter names"; `_ADAPTERS` in tests/test_cli.py has more.

## What to implement

Re-verify each first; drop any already closed with one line. Each text states only what the code and its tests show. IDEA-030: widen the regex so a lowercase tier "guess" in a docstring reds, without matching the legitimate uses (find them first). IDEA-145: fix the docstring; pin `Tier.label` inside an existing test; for migration 014 either an assertion in an existing migration test or soften the claim. IDEA-197: state no adapter count (CLAUDE.md's precedent) and point at `_ADAPTERS`.

## Acceptance criteria

* **AC-1**: each item fixed or dropped with its evidence.
* **AC-2**: the widened regex reds on a planted lowercase "guess" tier docstring and stays green on main's texts.
* **AC-3**: the `Tier.label` pin reds when one label is changed (control).
* **AC-4**: net test count 0 (the rename and pins live in existing tests); report it.

## Guardrails

* **G-1**: no behaviour change; script messages change wording only, and any test pinning the old wording moves with it.
* **G-2**: the CARD-257/kill-matrix line anchors and any line pins in tests (e.g. test_book_export_interior_cover's) are re-derived if a docstring edit moves them.

## Worktree notes
- [Implement] All nine items re-verified against the worktree before any edit; none was already closed. Per item:
  1. IDEA-026: `BookPDFGenerator.export_book`'s docstring said every export route goes through it. An `ast` walk of `src/` finds no route calling it: `generate_book_pdf` and `generate_book_pdf_download` go through `_export_part`, which calls `export_interior` or `export_cover`. The docstring now says this, and that its callers are tests. The same claim in docs/how-it-works/01-domain/puzzle-creation/07-book-assembly-and-the-admin-panel.md was corrected the same way. (The card's Touches path `src/nonogram/export/book_pdf_generator.py` does not exist; the module is `src/nonogram/admin/book_pdf_generator.py`.)
  2. IDEA-027: tests/test_book_pdf_band.py's `answer_page_number` is renamed `answer_page_number_one_per_level` at its definition and 6 call sites. The old docstring's "one full answer page per puzzle ... for any book this module builds" was false, because this module also builds CARD-202 packed books where two same-level answers share a page. The helper now refuses (ValueError) a book where two puzzles share a level. Checked directly: a 3-tier book returns a page; two Easy puzzles are refused.
  3. IDEA-030: `test_the_classifier_module_describes_the_guess_tier_only_as_retired` now uses `(?<!\w)guess\b(?![`*\s]*strategy)` with IGNORECASE (it was `(?<![_A-Z])GUESS\b|\bor Guess\b`). A paragraph is exempt if it says `retir` or "never as a tier". Census of difficulty.py's 9 paragraphs naming guess in any case: under the new pattern, 5 hit (the old pattern hit 2); 4 of those 5 say "retir" and the 5th (the RUNG ladder comment, "``guess`` is deliberately **not** a rung ... never as a tier") is a legitimate use that the "never as a tier" exemption admits. The `guess` *strategy* paragraphs are not matched. Green on main's text. Control: planting `#: A puzzle is graded easy, medium, hard or guess by its score.` in difficulty.py fails the test with `AssertionError: difficulty.py describes the retired GUESS tier as live (ADR-0031/R1); paragraphs starting: ['#: A puzzle is graded easy, medium, hard or guess by its score.']`. On the same planted text the old pattern passes (1 passed). difficulty.py was restored; `git diff --stat` on it is empty.
  4. IDEA-037: the unreachable-database message in setup_admin_local.sh, run_admin_tests.sh and start_admin_local.sh now names the third cause: "Either PostgreSQL is not running, '$DB_NAME' does not exist, or the / URL's host, port or credentials are wrong (only the local psql check reads them)." No test pinned the old sentence, so nothing had to move. The new wording is pinned by one added assert in each existing not-reachable test: `test_the_old_bare_check_would_have_passed_here` (setup), `test_with_nothing_exported_the_panels_database_is_not_enough` (runner) and `test_it_still_fails_when_the_database_is_absent` (start). Control: restoring setup_admin_local.sh from HEAD fails the setup test with `assert "URL's host, port or credentials are wrong" in '...This script does not create a database.\n'`. The script was restored.
  5. IDEA-039: scripts/README.md now says Python 3.14+ (pyproject `requires-python = ">=3.14"`). The stale docstring (found by its claim) is `test_a_claim_about_the_scripts_names_the_script_it_holds_for`. It said the siblings still `export DATABASE_URL=` over the caller's value; CARD-152 fixed both. Measured: no documented script matches the test's `export DATABASE_URL=` pattern today. The docstring now says so, and keeps the check as a regression guard.
  6. IDEA-102: `TestBookPdf_BandPrintsOnceInTheExportedPdf`'s docstring and the section comment above `ONCE_TIERS` now state `_lines`'s actual rule. A copy is seen only where every other ink sharing its run of inked rows is at least that run's height away sideways: about a line's height in the band strip, slot gap and margins, but the grid's height beside the drawing. This follows CARD-170 F-007's suggestion.
  7. IDEA-134: `_wrapped`'s docstring now says the token after a grouped × is taken as M whatever it is, and that no rule applies to it. Repro measured at the 42 px DejaVu face: `"aaaa × ·"` at width 157 gives `['aaaa ×', '·']`, and `"aaaa × × bbbb"` at width 160 gives `['aaaa ×', '× bbbb']`. The opening-× sentence no longer says "not joined to anything" (`"× · aa"` gives `['× · aa']`); it now says the × opens no group of its own.
  8. IDEA-145: `requested_tier_label`'s docstring now says the retired "guess" labels "Hard" (probe: guess/GUESS/' Guess ' give 'Hard'; extreme, None and 3 give None), and that `BatchGenerator.create_batch` never stores it (it stores `parse_tier(...).value`). The `Tier.label` pin is inside the existing `TestBatchRequestedTier_LabelFilter::test_it_is_registered_for_the_templates`. It asserts guess -> Hard, then renames Hard's label to "Expert" via monkeypatch and asserts the filter prints `['Easy', 'Medium', 'Expert']`. Controls:
     - (a) CARD-181's surviving mutant M6 (the filter returns `tier.value.title()`). On HEAD's tests it survives: 132 passed across test_batch_requested_tier/test_difficulty_tiers/test_admin_tier_surfaces. With this card's test it reds exactly one test, with `AssertionError: assert ['Easy', 'Medium', 'Hard'] == ['Easy', 'Medium', 'Expert']`.
     - (b) One label changed in difficulty.py (HARD -> "Expert"). This reds the pin test, along with `test_stored_value_to_label[hard-Hard]`, `test_a_tier_is_its_flag_value_and_carries_a_display_label[hard]` and `test_both_spellings_of_every_tier_read_back_to_the_same_member` (4 failed).
     - Both files were restored (cmp / empty diff).
     - Migration 014: the claim is softened rather than tested. It no longer says "no puzzle row ... is touched". It now says that `downgrade` alters `batches` alone, that `TestBatchRequestedTier_Migration014IsReversible` shows the batch row's other columns come back, and that this test holds no puzzle row.
  9. IDEA-197: src/nonogram/web/__init__.py no longer says the guard "knows exactly two adapter names". It points at `_ADAPTERS` in tests/test_cli.py as the closed set and states no count (CLAUDE.md's precedent). `_ADAPTERS` is `{"cli", "web", "admin"}` today.
- [G-2] Line pin re-derived: `OUTSIDE_CALLERS_WITH_A_POSITION` in tests/test_book_export_interior_cover.py went from 758 to 762, because the `_wrapped` docstring moved the call. The call (`generator.page_spec(position)`) was re-located by `ast` (HEAD 758, worktree 762). Before the fix, `test_the_module_axis_bound_is_measured_rather_than_declared` failed; after it, its class passes (23 passed). The CARD-257 anchors in tests/test_kill_matrix.py and tests/README.md point into tests/test_db_engine_lifecycle.py, which this card does not touch; test_kill_matrix.py passed. No other executable line pin on an edited file was found: the other `file.py:NNN` hits in tests/ are prose comments.
- [Test count] `--collect-only` was 10713 before and 10713 after: net 0.
- [Gate, unarmed, -o addopts= -rfs] Run 1: test_difficulty_tiers, test_batch_requested_tier, test_admin_tier_surfaces, test_start_admin_local, test_setup_admin_local, test_run_admin_tests, test_admin_local_cost, test_cli, test_book_proof_pages, test_book_page_packing_doc, test_guard_integrity, test_impact_set, test_kill_matrix, test_shared_fixture_controls, test_check_ref_resolution, test_web_server, test_card_063_limits. Result: 1205 passed, 0 skipped, 0 failed. Run 2: test_book_pdf_band + test_book_export_interior_cover, before the pin fix. Result: 240 passed, 1 failed; the failure was the line pin above, and its class passed after the fix. Run 3, after the fix: test_book_export_interior_cover, test_admin_error_text, test_book_difficulty_dots, test_admin_import_consistency, test_approval_guess_gate, test_admin_auth, test_admin_binding, test_book_floor, test_solver_strategies, test_book_landing_address, test_book_page_frame, test_book_arrange_page_breaks. Result: 677 passed, 9 skipped (all "DATABASE_URL is not set", the expected unarmed reason), 0 failed. `impact_set.py --gate` answers FULL for this diff because migration 014 changed (docstring only), so the merge gate is the full suite.

### Fix round 1 (review cycle 1: 9.5, not certified)

- F-001 FIXED. In docs/how-it-works/01-domain/puzzle-creation/09-the-three-inbound-adapters.md, the "One site of the same claim is still open" callout now says CARD-504 closed it: web/__init__.py states no count and points at `_ADAPTERS`. Sweep of docs/, the how-it-works pages, the root README, CLAUDE.md and meta/architecture for each of the nine claims, searched by the claim: no further site that this diff made false. Remaining hits checked and left:
  - ADR-0019's "exactly two adapters" and handoff.md's "one answer page per puzzle" are historical records.
  - docs/book_generation_req BK-8 already marks itself closed.
  - docs/how-it-works/README.md and docs/deploy/render.md's "3.11" describe runtime.txt/render.yaml, which really do say 3.11.
  - 07-book-assembly's stale `:NNNN` line refs predate this card and make no claim this diff changed.
- F-002 FIXED. `answer_page_number_one_per_level`'s docstring now says an answer alone in its level always has a page to itself. A shared level may pack, or the degrade pass may keep its answers one per page, and the arithmetic cannot tell which, so such a book is refused. The refusal itself is unchanged.
- F-004 FIXED. The root README.md Prerequisites now say Python 3.14+ (`requires-python`).
- F-003 TIGHTENED, one hole left:
  - The excuse word `retir` no longer counts inside an identifier (`(?<![_A-Za-z])retir`).
  - The strategy exemption now needs the backticked word followed by an emphasised `strategy`, so a bare "guess strategy" is matched.
  - Underscore-glued names built on guess (`\w*_guess\w*|\w*guess_\w*`) are matched unless they are `STRATEGY_GUESS` or `_RETIRED_GUESS_TIER`.
  - The denial phrases now span line breaks, and "no longer a tier" joins them, because the `tier_of_record` Returns paragraph's only other excuse was the identifier.
  - Census of the 9 paragraphs naming guess (round-1 rule): 6 hit. Each is excused: #35 "never as a tier"; #39, #55, #76 and #81 by prose "retir"; #85 "no longer a / tier". #55 is `SolverSignals`'s "what is deliberately absent" paragraph, whose unemphasised ``guess`` strategy is now matched. The other 3 (#41, #58, #86) do not hit. Green on today's text.
  - Plants, each run against round 1's rule and cycle 1's rule:
    - `#: Tiers run easy, medium, hard and guess; see _RETIRED_GUESS_TIER.`: round 1 RED, cycle 1 passed.
    - `#: A branching solve is graded hard or guess strategy puzzles.`: round 1 RED, cycle 1 passed.
    - `#: GUESS_TIER is the fourth band, keyed on branch_nodes.`: round 1 RED, cycle 1 passed.
    - AC-2's `#: A puzzle is graded easy, medium, hard or guess by its score.`: RED under both.
    - Each red is `AssertionError: difficulty.py describes the retired GUESS tier as live (ADR-0031/R1); paragraphs starting: ['<the plant>']`. difficulty.py was restored with an empty `git diff --stat`.
  - LEFT LOOSE: the two denial phrases still excuse their whole paragraph rather than their own sentence. The ladder comment (#35) names ``guess`` in one sentence ("deliberately **not** a rung") and denies tierhood in the next, so a sentence-level rule reds today's text. The test docstring says this plainly.
- F-005: out of scope, left as instructed.
- [Fix round 1 gate, unarmed, -o addopts= -rfs]
  - test_difficulty_tiers + test_book_pdf_band: 159 passed.
  - test_cli, test_impact_set, test_check_ref_resolution, test_kill_matrix: 448 passed, 0 skipped.
  - test_admin_binding, test_db_url_driver, test_guard_integrity, test_start_admin_local (the tests that read README.md): 324 passed, 9 skipped (all "DATABASE_URL is not set"), 0 failed.
  - Collected count 10713, still net 0.

[Review 1/3] Score: 9.5, one gating finding, not certified. Every rewritten text measured against the code (export_book has no src caller; _wrapped's examples re-run; _lines's rule exact; tier_of_record, create_batch and migration 014's downgrade read; _ADAPTERS = {cli, web, admin}); AC-2 plants red; the Tier.label pin reds under a label change and CARD-181's M6; the line pin re-derived by ast (762); net 0. F-001 (Important) how-it-works 09-the-three-inbound-adapters.md still called the closed web/__init__ claim open; F-002 the renamed helper's docstring said "only when"; F-003 the widened regex's exemptions were loose (identifier "retir", "guess strategy", GUESS_TIER); F-004 the root README still said 3.11; F-005 (out of scope) two app.py sites title-case tier values instead of Tier.label. Fixed in `c102aaea`: F-001, F-002, F-004; F-003 tightened (three new plants red, today's text green), the paragraph-wide "never/no longer a tier" excuse left open with the reason stated.

[Review 2/3] Score: 9.7, nothing gating, certified. F-001..F-004 resolved and re-measured: a sweep of docs/, meta/architecture, src/, scripts/, tests/, both READMEs and CLAUDE.md found no other text this diff made false; the guess-paragraph census re-derived (9 name it, 6 match, each excused); the implementer's three plants, AC-2's and the reviewer's own tuple plant all red; the paragraph-wide "never/no longer a tier" excuse accepted as stated. Net 0 (422 on the seven changed files). F-006 (low) the docstring said identifier "retir" does not count, true only with a letter or underscore before it; an identifier starting with it, or "not retired", still excuses -- the docstring narrowed to say exactly that by the orchestrator, no rule change. F-005 (info, out of scope) carried.

**Merge gate (orchestrator).** main merged into the branch first (`9b22bf2a`: CARD-502 and CARD-505 had landed). `make test-gate BASE=main` answered FULL (migration 014 changed): 10658 passed / 30 skipped (the unarmed baseline: 29 DATABASE_URL unset + 1 setrlimit) / 1 xfailed / 0 failed, all 13 wave_close_only tests included.

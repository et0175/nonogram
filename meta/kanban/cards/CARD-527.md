# CARD-527: Every browser-test file must declare its page isolation, not only the test_puzzle_solver_* files

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/527-page-isolation-all-browser-files
**Worktree:** ../PythonProject4-card-527
**Source:** roadmap wave 14, cut 2026-11-23 on the owner's "pick a no-decision wave from the backlog". IDEA-181 (CARD-246 finding).
**Idea:** IDEA-181
**Wave:** 93
**Created wave:** 93
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_browser_fixture_scope.py; the browser-test files it newly covers, only if one needs a declaration
**UI surface:** —
**Review score:** 8.5 (cycle 1/3)
**Started:** 2026-11-23T08:10Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-235's `PAGE_ISOLATION` table in `tests/test_browser_fixture_scope.py` makes each browser-test file say how it isolates its page between tests, so a test cannot quietly depend on another test's page state. Its file list comes from the glob `tests/test_puzzle_solver_*.py`, so a browser-test file under any other name is never asked. CARD-246 (`tests/test_puzzle_editor_ui.py`) declared its isolation locally, by hand. The backlog triage on 2026-11-18 counted about 13 browser files outside the glob, by a text search that was not confirmed by collection.

## What to implement

1. Re-verify on main: derive the set of browser-test files the way the suite itself identifies them (the browser marker or fixture, resolved by collection or `ast`, not by text search), and list which fall outside the glob.
2. Make the isolation guard cover that whole set, so a new browser-test file under any name fails the suite until it declares its isolation. Each file that is newly covered gets its declaration, using CARD-235's existing categories, with the reason checked against how the file actually sets up its page.
3. Fold CARD-246's local declaration into the shared table if that is now redundant (one source, not two).

## Acceptance criteria

* **AC-1**: the guard's file set is derived from the suite's own browser-test identification, not from a filename glob. A test proves that the set equals the files collection marks as browser tests. Control: a mutant that restores the glob turns that test red.
* **AC-2**: every browser-test file has exactly one declaration, and a declaration for a file that no longer exists is refused. Controls: deleting one newly added declaration turns a named test red, and so does adding one for a missing file.
* **AC-3**: each new declaration's category matches the file's actual page setup, judged per file in the notes with the fixture each file uses.
* **AC-4**: no browser test's behaviour changes, so no fixture scope moves. Report the net test count; the owner's budget is to extend existing tests.

## Guardrails

* **G-1**: tests-only card; nothing under src/ changes.
* **G-2**: do not change any fixture scope; if a file's isolation looks wrong, record it in the notes as a finding, do not fix it here.

## Worktree notes

### 2026-11-23 implementation (agent)

**Premise re-verified by collection** (`--collect-only -m`-equivalent: a plugin reading `item.get_closest_marker("browser")` over all of `tests/`): 32 files carry a `browser`-marked test; 17 are `tests/test_puzzle_solver_*.py`, 15 are not: test_book_arrange_play_link, test_book_finalise_guide_preview_layout, test_book_landing_page, test_book_setup_print_mobile, test_book_workflow_steps, test_books_list_mobile, test_browser_fixture_scope (the guard itself: its child-pytest tests are marked), test_how_to_solve_page, test_player_base_css, test_player_public_mode, test_player_shared_ui_site, test_player_viewport_matrix, test_public_player, test_public_player_pages, test_puzzle_editor_ui. The marker is the suite's mechanism (registered in pyproject.toml; no conftest hook applies it). Fixture name is not: test_book_finalise_guide_preview.py and test_book_pdf_band.py request a fixture named `page` that is their own PDF page, not Chromium; neither carries the marker.

**What changed**
- `test_browser_fixture_scope._browser_files()` (new helper, cached): one child `pytest --collect-only -q -m browser tests` with PYTEST_ADDOPTS dropped and the warnings plugin off; the file set PAGE_ISOLATION must equal. `_family_files()` keeps the glob, now documented as CARD-235's measured family only (its registries — the artefact, ADDED_SINCE_BEFORE, the order/alone records — stay keyed on it, which is why the editor file's F-014 note had refused to widen the glob; this card does not widen it).
- `test_every_browser_file_declares_a_category_and_a_reason` (renamed from `test_every_family_file_...`): set equality with collection, the message naming both directions (undeclared browser file / declared file collection does not mark).
- `test_an_own_page_file_really_gets_its_own_page`: additionally, via new helper `_page_fixture_scopes`, every fixture a declared file can see (module, imported, class-defined) that takes `browser_page`/`browser_type`/`browser`/`context`/`page`, transitively, must be function-scoped.
- `test_the_reasons_name_state_the_file_actually_touches`: two mechanisms added — `child pytest` (subprocess.run, for the guard file) and `MutationObserver` (the one check test_puzzle_editor_ui's own test made that the shared test did not).
- `test_the_family_on_disk_is_the_family_the_registry_names`: its PAGE_ISOLATION door now compares the family to the table's family-named keys.
- `test_puzzle_solver_page.PAGE_ISOLATION`: 14 new `own-page` declarations; test_puzzle_editor_ui's moved in verbatim. test_puzzle_editor_ui.py: `PAGE_ISOLATION_DECLARATION` and `test_this_files_page_isolation_is_declared_and_true` removed (one table, not two).

**AC-3, per file** (page fixtures read off the fixture objects; every one function-scoped; all pages come from the session-scoped Chromium that `browser_type` launches, as the family's do):
- book_arrange_play_link: `desktop_page`/`phone_page` over `browser_page`, server `live_arrangement` — viewport + pageerror/console listeners.
- book_finalise_guide_preview_layout: `browser_page`, server `live_finalize` — viewport + pageerror listener.
- book_landing_page: `browser_page`, servers `pages_host`/`pages_site` — localStorage seeded/corrupted/cleared, init script making localStorage throw, pageerror/request listeners, viewport.
- book_setup_print_mobile: class fixture `phone_page` over `browser_page`, server `live_book` — viewport + listeners.
- book_workflow_steps: `browser_page`, `live_book` — one test, pageerror listener, relies on a fresh session's unit.
- books_list_mobile: `browser_page`, `live_books` — viewport + listeners.
- browser_fixture_scope: no page in-process; its browser tests run child pytests using test_puzzle_solver_page's `browser_page`/`live`.
- how_to_solve_page: `browser_page`, `pages_host` — navigation only; own-page inherited, not needed (no state a shared page would have to undo was found).
- player_base_css: `browser_page`, `bundle` — viewport, emulate_media, page.route + reload.
- player_public_mode: `browser_page`, `touch_page`, `touch_pages` (own contexts, closed at teardown), `serve`, `live` — listeners, localStorage, reload, viewport.
- player_shared_ui_site: `browser_page`, `touch_page`, `preview_host` — viewport, localStorage init script. (`fragment` is module-scoped but is an immutable rendered string, takes no page.)
- player_viewport_matrix: `screen` (own context per test, closed at teardown), inline contexts closed in `finally` — listeners, page.route, viewport.
- public_player: `browser_page`, `host` — one test, context request listener.
- public_player_pages: `browser_page`, `pages_host`/`counted_host` — listeners, page.route, viewport.
- puzzle_editor_ui: `browser_page`, `live` — the moved CARD-246 reason.
No suspect isolation found (G-2: no fixture scope changed).

**Controls** (each applied to the committed tree, run, restored with `git checkout`; `git status` clean after):
- C1 glob restored inside `_browser_files` -> `test_every_browser_file_declares_a_category_and_a_reason` red: `AssertionError: {... 'declared, but collection marks no browser test in it (gone?)': [... 14 non-family files ...]}`.
- C2 test_public_player.py's declaration deleted -> same test red: `{'a browser file with no PAGE_ISOLATION declaration': ['test_public_player.py'], ...}`.
- C3 declaration added for test_no_such_browser_file.py -> same test red: `{..., 'declared, but collection marks no browser test in it (gone?)': ['test_no_such_browser_file.py']}`.
- C4 `touch_page` widened to scope="module" -> `test_an_own_page_file_really_gets_its_own_page` red: `['test_player_public_mode.py: touch_page is module-scoped and takes a page or the browser', 'test_player_shared_ui_site.py: ...']`.
- C5 `child pytest` mechanism removed -> `test_the_reasons_name_state_the_file_actually_touches` red: `['test_browser_fixture_scope.py: the reason names no mechanism to check']`.
- C6 MutationObserver pattern pointed at nothing -> same test red: `['test_puzzle_editor_ui.py: reason claims MutationObserverXX, file has none']`.

**Gate** (unarmed, `-o addopts= -rfs`): tests/test_browser_fixture_scope.py tests/test_puzzle_solver_page.py tests/test_puzzle_editor_ui.py tests/test_wave_close_marker.py tests/test_suite_profile.py tests/test_impact_set.py -> 886 passed, 1 failed, 0 skipped. The failure is `TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured`, and it is **pre-existing**: red identically with this card's three files checked out at the merge base. Three family tests added by 9fd47469 (Player QA v3) are registered nowhere: two in test_puzzle_solver_clues.py's `TestSolverClues_RepeatedLengthCirclesWhereOnlyOneFits`, one in test_puzzle_solver_zoom.py's `TestSolverZoom_PinchOnAClueBoxIsTheBoardsZoom`. Not fixed here (outside this card; its ADDED_SINCE_BEFORE entries need that change's card/why).

**Net test count**: 10695 before, 10694 after (−1: the editor file's local declaration test, folded into the shared one).

[Review 1/3] Score: 8.5, one gating finding, not certified. Re-derived: 32 browser files and 802 browser-marked items by collection; controls C1, C3, C4 red with the notes' messages; `_browser_files` fails closed on a nonzero child exit or an empty set; 8 declarations sampled and all 15 scope-walked, categories true; net -1. The one failing test, `test_the_family_collects_exactly_what_card_217_measured`, fails identically on main (three node ids added by 9fd47469 not in ADDED_SINCE_BEFORE): pre-existing, not scored. F-001 (Important): folding CARD-246's declaration dropped its fixture-scope check of the editor file's own `browser_page` and `live`; the shared own-page test checks only fixtures whose signature takes a page, so no server fixture in the 15 new files has its scope checked (mutant: a module-scoped `live` in test_puzzle_editor_ui.py stays green on HEAD, red on main with 'module' == 'function'). F-002 (minor): two tests in test_player_public_mode.py request `browser_page` without the `browser` marker, so a file whose browser tests are all unmarked would escape the census. F-003 (low): fixture dependencies are read from signatures only; `request.getfixturevalue` is not followed. F-004 (low): test_how_to_solve_page.py's reason passes the mechanism check only through a negated `localStorage`. F-005, F-006 (pre-existing, info): the family-collection failure; the two unmarked tests run under `-m "not browser"`.

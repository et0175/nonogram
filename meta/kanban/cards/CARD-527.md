# CARD-527: Every browser-test file must declare its page isolation, not only the test_puzzle_solver_* files

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/527-page-isolation-all-browser-files
**Worktree:** —
**Source:** roadmap wave 14, cut 2026-11-23 on the owner's "pick a no-decision wave from the backlog". IDEA-181 (CARD-246 finding).
**Idea:** IDEA-181
**Wave:** 93
**Created wave:** 93
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_browser_fixture_scope.py; the browser-test files it newly covers, only if one needs a declaration
**UI surface:** —
**Review score:** 9.5 (cycle 2/3 - CERTIFIED)
**Started:** 2026-11-23T08:10Z
**Closed:** 2026-11-23T10:37Z
**Actual:** 2c — ratio 2/1 = 2.0
**Merge commit:** 83da95e2c7b2666666034cd2e65f4dcfc3f1fc24
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

### Fix round 1 (review 1: 8.5, not certified)

**Correction to the notes above.** "MutationObserver (the one check test_puzzle_editor_ui's own test made that the shared test did not)" was false: the removed test also asserted function scope for the `browser_page` and `live` bound *in that file*, which the shared test did not check (review 1, F-001; mutant M1 survived). The "marker is the suite's mechanism" premise was also incomplete: two tests reached `browser_page` unmarked (F-002).

**What changed** (commit 3344620c)
- New `tests/helpers/browser_census.py`: a pytest plugin loaded only by the guard's child collection. For every item that is `browser`-marked or reaches `browser_page`/`browser_type`, it records the marker and every fixture reached, with scope and module. "Reached" is the static closure plus literal `request.getfixturevalue("<name>")` names in the test and in any reached fixture, followed transitively; a non-literal argument is recorded as `<dynamic>` (scope `?`, so it is refused unless allowed).
- `test_browser_fixture_scope._browser_census()` (cached child `--collect-only tests` with that plugin, PYTEST_ADDOPTS dropped) replaces the `-m browser` child; `_browser_files()` now reads the marked files from it.
- F-001: `test_an_own_page_file_really_gets_its_own_page` also requires every fixture reached by every marked item to be function-scoped, or named `name@module` in the new `WIDER_FIXTURES_ALLOWED` with a reason (20 entries: Playwright's session fixtures, the shared `browser_type`, pytest-base-url's, pytest's `pytestconfig`/`tmp_path_factory`, four conftest session DB/writer fixtures, and `fragment`). An allowance no browser test reaches is refused too.
- F-002: `test_every_browser_file_declares_a_category_and_a_reason` first refuses any census item that is unmarked. `TestPublicMode_TheCensus::test_an_unclicked_step_is_found_by_the_sweep_not_only_by_the_census` and `TestPublicMode_LandscapeToolStrip::test_the_tools_stand_in_a_strip_left_of_the_board` are now `@pytest.mark.browser` (closes F-006 too). No fixture scope changed.
- F-003: `_page_fixture_scopes` adds a fixture's literal `getfixturevalue` names to what it takes (`<dynamic>` counts as taking a page). It still scans the module and class fixtures, so a page-taking fixture no test requests is checked too; the census cannot see that case.
- F-004: test_how_to_solve_page.py's reason now names its referer navigation and location-hash steps. The new mechanism `referer` checks `\.goto\([^)]*referer=` positively. The reason no longer mentions localStorage. Its "nothing else is installed or stored" part is a reading, not mechanically checked.
- F-005: not touched (owner deciding).

**Controls** (each applied to the committed tree, run, restored with `git checkout`; `git status` clean after):
- C1 `_browser_files` restricted to `tests/test_puzzle_solver_*`: `test_every_browser_file_declares_a_category_and_a_reason` goes red with `{... 'declared, but collection marks no browser test in it (gone?)': [...non-family files...]}`.
- C2 test_public_player.py's declaration deleted: the same test goes red with `{'a browser file with no PAGE_ISOLATION declaration': ['test_public_player.py'], ...}`.
- C3 declaration for test_no_such_browser_file.py: the same test goes red with `{... 'declared, but collection marks no browser test in it (gone?)': ['test_no_such_browser_file.py']}`.
- C4 `touch_page` changed to scope="module": `test_an_own_page_file_really_gets_its_own_page` goes red with `['test_player_public_mode.py: touch_page is module-scoped and takes a page or the browser', 'test_player_shared_ui_site.py: ...']`.
- C5 `child pytest` mechanism removed: `test_the_reasons_name_state_the_file_actually_touches` goes red with `['test_browser_fixture_scope.py: the reason names no mechanism to check']`.
- C6 MutationObserver pattern pointed at nothing: the same test goes red with `['test_puzzle_editor_ui.py: reason claims MutationObserverXX, file has none']`.
- C7 (= reviewer's M1) `@pytest.fixture(scope="module") def live(): yield None` appended to test_puzzle_editor_ui.py: `test_an_own_page_file_really_gets_its_own_page` goes red with `['tests/test_puzzle_editor_ui.py::...: live@tests.test_puzzle_editor_ui is module-scoped', ...]`.
- C8 (= M2) an unused module-scoped fixture in test_public_player.py calling `request.getfixturevalue("browser_type")`: the same test goes red with `['test_public_player.py: m2_shared_page is module-scoped and takes a page or the browser']`.
- C9 the marker removed from `test_the_tools_stand_in_a_strip_left_of_the_board`: `test_every_browser_file_declares_a_category_and_a_reason` goes red with `these reach browser_page or browser_type but carry no browser marker: ['tests/test_player_public_mode.py::TestPublicMode_LandscapeToolStrip::test_the_tools_stand_in_a_strip_left_of_the_board']`.
- C10 `referer=referer` removed from test_how_to_solve_page.py's `_open`: `test_the_reasons_name_state_the_file_actually_touches` goes red with `['test_how_to_solve_page.py: reason claims \.goto\([^)]*referer=, file has none']`.
- C11 a stale `nothing@tests.nowhere` allowance: `test_an_own_page_file_really_gets_its_own_page` goes red with `allowed but reached by no browser test: ['nothing@tests.nowhere']`.

**Census** (re-derived with the plugin over all of `tests/`): 804 records, all 804 marked, 0 unmarked, 32 browser files. The child census costs about 10 s once per process (the `-m browser` child was about 3.5 s).

**Gate** (unarmed, `-o addopts= -rfs`): tests/test_browser_fixture_scope.py tests/test_puzzle_solver_page.py tests/test_puzzle_editor_ui.py tests/test_player_public_mode.py tests/test_how_to_solve_page.py tests/test_wave_close_marker.py tests/test_suite_profile.py tests/test_impact_set.py tests/test_shared_fixture_controls.py gave 1037 passed, 1 failed, 0 skipped, in 637 s. The one failure is F-005, which was already failing before this card (`test_the_family_collects_exactly_what_card_217_measured`, same three node ids from 9fd47469).

**Net test count**: 10695 before the card, 10694 after (unchanged by this round, which only extended existing tests).

[Review 2/3] Score: 9.5, certified. Re-derived: 229 passed, 1 failed (the pre-existing family-collection test), 0 skipped; census 804 records, 32 files, 0 unmarked, 10694 collected; all 20 WIDER_FIXTURES_ALLOWED entries reached, none holds a page or a server (the four conftest session fixtures are a URL string, the schema/engine builder, the armed-DB check and a session monkeypatch; no browser test reaches the truncating DB fixture); controls C7, C9, C11 red for their own reasons; the census child fails closed on a nonzero exit, a missing output, an empty census or a 90 s timeout, and never takes the full-suite lock. Cycle-1 F-001, F-002, F-003, F-004, F-006 closed; F-005 pre-existing, owner deciding. F-101 (minor): `_reached` in tests/helpers/browser_census.py reads only the closest definition of a fixture name, so a function-scoped `def srv(srv)` override hides a wider parent (mutant green); no fixture in tests/ uses that pattern today. F-102 (info): the how-to reason says "only navigates" though its tests also click and evaluate; state lives in the page and the next navigation discards it. F-103 (info): the census child costs about 10 s per process, about three times the old one.

**Merge gate (orchestrator).** `make test-gate BASE=main` on `f1a4b3aa` (main, with CARD-530, merged into the branch first) answered SELECTION: 5646 passed / 24 skipped (unarmed; the gate prints no skip reasons, and its selection is wider than CARD-530's, which skipped 20) / 8 deselected / 1 xfailed / 0 failed in 26 min 40 s, then the marked run 6 passed. 7 marked tests are owed at the wave close.

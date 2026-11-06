# CARD-286: The impact derivation cannot see a coupling no import edge carries — so it fails OPEN on the player, and wide on the book

**Status:** in_progress
**Priority:** P2
**Category:** ops
**Estimate:** 3c (1d)
<!-- RESTATED in review cycles 2026-11-06 at queueing (the board counts Nc since ADR-0055; a waved card with no Nc term reddens tests/test_kanban_review_record.py). The day figure is the old estimate, unchanged. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/286-impact-set-sees-what-tests-read
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-286
**Source:** owner request 2026-10-23 ("we wouldn't run book rendering tests for changes in player or in core algorithms and vice versa") + CARD-271's fix pre-gate finding PG-2 and its merge gate, both measured; backlog.md @ops items "scripts/impact_set.py is blind to static assets" and "the browser-fixture family's node-id registry is discoverable only by a run nobody makes in the inner loop"
**Idea:** —
**Wave:** 79
**Created wave:** 55
**Deferred waves:** 0
**Depends on:** —
**Touches:** scripts/impact_set.py, tests/test_impact_set.py
**Review score:** —
**Started:** 2026-11-06T20:52Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`review.test_scope: impact` already narrows every review cycle, and the full
suite already runs only at the merge gate and the wave smoke test. The policy
the owner asked for is therefore in place; what is missing is a derivation that
can be trusted with it. Three measurements from CARD-271, 2026-10-23, all
reproducible from the commands quoted:

**1. It fails OPEN on a static asset — the one direction its own docstring
says it must never fail.** `scripts/impact_set.py
src/nonogram/admin/static/admin.css src/nonogram/admin/static/solver.js`
returns **23 files**, and the intersection with the **16** test files that name
`player-board` / `player-clue` / `player-stage` / `admin.css` is **EMPTY**.
The cause is in `select()` (`:307`): a changed path with no Python module name
resolves `module = module_name_for(...) or tests_module_name_for(...)` to
`None` and hits `continue` (`:344`/`:352`), on the stated grounds that it
"changes no import edge, and the always-on scanners already cover the
tracked-tree guards that DO read it". True for a guard that reads the asset as
**text**; false for a browser test that loads it at **runtime**, which is how
every player test reads these two files. `changed_from_git`'s own docstring
(`:378`) states the property being broken.

**2. And wide in the other direction at the same time.** The 23 files it does
return for `solver.js` include `tests/test_book_difficulty_dots.py`,
`tests/test_admin_binding.py`, `tests/test_admin_regrade.py` — book and
binding tests that do not read it. So for an asset card the selection is wrong
in **both** directions simultaneously: it names the always-on scanners and
omits the real readers. A cycle gated on it would run book renders and no
player board.

**3. A coupling can also be a subprocess, not an import.** CARD-271's merge
gate went red on
`tests/test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured`:
the card added 27 node ids to the browser-fixture family and registered none,
and **25 of the 27 had been owed since the implementation commit**. That guard
names none of the card's selectors, so it was outside the 17-file selection
the card gated on four times, and it reaches the family through a
`--collect-only` **subprocess**, so there is no import edge to follow either.
Four gate selections, two full-depth review cycles, a pre-gate and two
fix-round re-derivations passed over it. The first thing to see it was a
24-minute full suite.

**The fix shape, and it is one this script already uses elsewhere: derive the
edge, or fail closed.** A static asset's readers are derivable from the asset
itself — a test that loads `admin.css` at runtime names the file, or one of the
selectors/identifiers the asset declares. That is exactly the `SCAN_IDIOMS`
precedent at `:102`: match the tree as text where the import graph cannot see
the coupling. Where no reader is derivable for a changed path, the answer is
**`FULL`**, not a quiet omission — which is what every other unmodelled path
in this script already does (ADR-0039/R2's default-deny, applied to the
board's own evidence rather than to product code).

**What NOT to do.** Do not fix this with a hand-maintained map of families
("book tests ⊥ player tests"). Measured 2026-10-23, that partition is already
false: `tests/test_book_finalise_guide_preview_layout.py:6` reads
`static/admin.css` (the Finalise guide preview shares the admin stylesheet
with the player), so a "player" asset has a book reader. And a hand-maintained
map is the same artefact class as the registry in measurement 3 — a census a
card can break without ever learning it did. Derive it.

**The direction that is already right, and must stay right.** A core change
must keep pulling the book tests in: `src/nonogram/admin/book_pdf_generator.py`
imports `nonogram.difficulty`, `nonogram.errors`, `nonogram.export`,
`nonogram.export.layout` and `nonogram.export.pdf`, so the book pipeline sits
on top of the core algorithms and the import graph models that correctly. Only
the asset and subprocess couplings are missing.

**Price the work before trusting it.** The 2026-10-15 profile
(`meta/profiling/suite-hotspots-20261015.md`) puts the render-heavy set at
**21.23 %** of the suite and the browser family at **39.78 %**, so a player
card that stops running book renders and a book card that stops running the
browser family are worth roughly a fifth and two fifths of each cycle. Record
today's equivalents from `meta/profiling/suite-durations-20261023.txt` beside
them; a narrowing whose saving is not measured is a guess.

## Acceptance criteria

- **AC-1** (happy, the omission): *Given* `src/nonogram/admin/static/solver.js`
  and `src/nonogram/admin/static/admin.css` as the changed set, *when* the
  selection is derived, *then* it contains every test file that names those
  filenames or a selector the assets declare — at minimum the 16 files naming
  `player-board`/`player-clue`/`player-stage`/`admin.css` plus
  `tests/test_book_finalise_guide_preview_layout.py`. (test:
  `TestImpactSet_AStaticAssetSelectsTheTestsThatReadIt`)
- **AC-2** (guard, default-deny): *Given* a changed path for which no reader
  can be derived, *when* the selection is derived, *then* the answer is `FULL`
  and the reason names the path and the rule that produced it. (test:
  `TestImpactSet_AnUnderivablePathFailsClosedAndSaysWhy`)
- **AC-3** (happy, the subprocess coupling): *Given* a changed
  `tests/test_puzzle_solver_*.py`, *when* the selection is derived, *then* it
  contains `tests/test_browser_fixture_scope.py`. (test:
  `TestImpactSet_TheBrowserFamilyGuardFollowsItsFamily`)
- **AC-4** (guard, the direction that must not regress): *Given* a change to a
  core module the book pipeline imports (e.g. `src/nonogram/export/layout.py`),
  *then* the selection still contains the book render tests it contains today —
  asserted as a superset of a recorded baseline, so narrowing cannot silently
  drop them. (test: `TestImpactSet_ACoreChangeStillReachesTheBookTests`)
- **AC-5** (guard, completeness over the asset tree): *Given* every file under
  `src/nonogram/**/static/`, *then* each one has a derivation path and the set
  of asset extensions the script knows how to read is asserted as an equality,
  not a floor — a new asset type with no rule fails the suite rather than
  joining the silent class. (test:
  `TestImpactSet_EveryShippedAssetHasADerivation`)
- **AC-6** (edge, no false narrowing): *Given* each of the three measured
  cases above, *when* the derived selection is run, *then* it is a **subset**
  of what the full suite runs and a **superset** of the tests that actually
  exercise the change, both enumerated in the card. (recorded, verified by
  review)
- **AC-7** (happy, measured): *Given* the 2026-10-23 profile, *then* the card
  records what a player card and a book card each save under the repaired
  derivation, against the full-suite figure. (recorded, not asserted)


## [Addendum 2026-11-06, OWNER RULING] — the merge gate will run this derivation

The owner said on 2026-11-06, after the shared-player spike: "I think we shall dispatch tests by impact". The October ruling (2026-10-22 `review.test_scope: impact`, 2026-10-23 "we wouldn't run book rendering tests for changes in player or in core algorithms and vice versa") covered review cycles only; the MERGE GATE has run the full armed suite (about 11,100 tests, 35 to 50 minutes, holding `meta/kanban/.full-suite.lock`, which makes every other pytest run on the machine fail while it is held). **Once this card lands, the gate policy becomes: the impact selection plus the always-on set; the full suite runs at wave close and whenever the derivation answers `FULL`.** That puts this derivation under EVERY merge, so its correctness is now load-bearing rather than advisory, and design A of the shared-player spike (`solver.js` and `admin.css` shared with the public site) makes the static-asset blind spot above the most expensive one. The policy switch itself (config.yml and the gate briefs) is NOT part of this card: the orchestrator makes it after this card is certified.

Two more items for this card, beyond the three measurements above:

* **AC-8** (the gate recipe, recorded and tested): *Given* a changed set, *then* the script has a documented gate invocation that prints the selection, its size against the full suite's collected count, and, when it answers `FULL`, the path and rule that caused it; the output is one block a gate can paste into the card's note. There is no Makefile in this repository; do not add one (ADR-0006/R1 spirit): the invocation is the script. (test: named by the implementation)
* **AC-9** (replay, measured not asserted): *Given* the diffs of the last 20 merge commits on `main` (`git log --merges`), *then* the card records, per merge, the selection size, whether it answered `FULL`, and which of the three known misses (static asset, subprocess guard, always-on scanners) each would have hit; and the card states the fraction of merges that would have been `FULL`. This is the evidence for the owner's switch. (recorded, verified by review)

## Guardrails

- G-1: Fail **closed**. No change may make an unmodelled path return anything
  but `FULL`; the whole defect is a `continue` where a `FULL` belonged.
- G-2: The always-on scanners stay in every selection — they are what cover
  the tracked-tree guards, and this card narrows nothing that is already
  always-on.
- G-3: Do not edit `src/**`. This is board tooling; a production change to make
  a derivation easier is out of scope and would be a different card.
- G-4: Do not solve this by returning `FULL` more often in general. A
  derivation that answers `FULL` for every asset card is correct and useless —
  AC-6's subset/superset pair is what keeps both halves honest.
- G-5: Do not introduce a hand-maintained family map or any other census a card
  must remember to update (see "What NOT to do"). Every set this card adds is
  derived, or it is asserted as an equality with a completeness test
  (ADR-0039/R1, ADR-0039/R2).
- G-6: `--base <rev>` keeps returning `FULL` when a changed path lies outside
  `KNOWN_ROOTS` (`:95`) — e.g. the repo-root `ONLINE_GAME_SPECIFICATION.md`,
  which is why `--base main` answers `FULL` today. That behaviour is correct
  and is **not** to be "fixed" by widening `KNOWN_ROOTS`; if it is to change at
  all, it changes by making the path's readers derivable, and AC-2's reason
  line makes the `FULL` auditable instead of mysterious.
- G-7: Out of scope — the `Touches`-is-a-prediction problem (its own @ops
  item: a card can touch a hotspot it never declared, as CARD-206 did with
  `tests/helpers/book_corpus.py`), retiring subsumed tests (CARD-220), and
  reshaping the browser-family registry itself (its own @ops item). This card
  makes the registry *reachable*; it does not redesign it.

## Architecture context

- **FR:** — (board tooling)
- **ADR:** ADR-0039/R1 (a claim needs a control that can fail — AC-2/AC-5),
  ADR-0039/R2 (a guard set derived from an enumerable authority is
  default-deny — G-1/G-5), ADR-0006/R1 (no new dependency).
- **CON:** —
- **Components:** none (scripts + tests only).
- **Trace:** not applicable.

## Worktree notes

—


[Author round, commits `d98a4a31`, `75524c28`, `d8384e81`] Verified by the orchestrator by git facts only: worktree clean, three commits over the cut `3d2b74f0`; exactly the two Touches files (`scripts/impact_set.py` 809 lines changed, `tests/test_impact_set.py` 747 new lines; 1497 insertions, 59 deletions); `src/`, `meta/`, the `Makefile` and `docs/` unchanged; no added bare early `return`, skip or xfail. Not re-run by me. Author-reported (labels the author's: "measured" = this run): PREMISE CHECK: the card's line numbers are stale (cited by name); measurement 1 is true but WORSE: the old `select` for `solver.js` alone returned 38 files, exactly the always-on set (38 scanners), adding zero readers (the carried "23 files" is stale); measurement 2 (book tests in the selection) comes from the always-on set; measurement 3 true (`test_browser_fixture_scope` is not always-on and reaches the family by a `--collect-only` subprocess); STALE premise "no Makefile": a tracked Makefile exists (commit `0bd8eb15`) with `test-impact` and `impact-set` targets, its contract (stdout `FULL` or paths) unchanged, reasons go to stderr; STALE premise: the comment said `migrations/**` returns FULL but the code silently `continue`d (fixed). HOLES FOUND BY RE-MEASURING, all fail-open and fixed: relative imports read as the bare module name (5 such imports in the tree; a change to `db/session.py` did not select tests doing `from nonogram.db import get_session`); a `conftest.py` outside the tests root silently skipped (now FULL); a changed test file's importers not selected (the browser family shares `browser_page` by import); `git diff --name-only` rename detection hid the old path (added `--no-renames`); scripts, meta `.py` and non-py files under `tests/` silently skipped; everything under the repo-root `player/` returned FULL for the wrong reason (5 of the last 20 merges were player merges). WHAT IT DOES NOW: `derive(root, changed, corpus=None)` returns `Derivation(files, full, reasons)`, each `Reason(path, rule, detail)`; FULL rules: unanalysable, outside-known-roots, migrations, conftest, no-scanners, no-importer, no-reader, unknown-asset-type; `ASSET_RULES` maps css/js to executed, html to template, ttf/txt/LICENSE/PKG-INFO to named, .DS_Store to inert; executed assets select tests naming the file, tests naming a selector the asset declares, and browser tests that reach a module that loads it (a "load" is a code string, a tag or attribute, or an import/url/fetch line; a comment or docstring mention is not a load: without that rule one `solver.js` change selected 95 files = 58% of the tests); templates select tests naming them plus importers of the modules that render them, through include/extends; test files select importers (helpers transitively), tests naming them by path/glob/prefix, and the collection-census tests for any `tests/` change. GATE: `./.venv/bin/python scripts/impact_set.py --gate --against main` (also `--gate PATH [PATH...]`), run with no full-suite lock held because the count is a real `pytest --collect-only -q -o addopts=` (about 15 s); full-suite count measured: 11,236 collected. Sample blocks: `player/play.js` 5287 of 11236 tests (47.1%), 63 files (38 always-on); `book_pdf_generator.py` 7843 of 11236 (69.8%), 131 files; `solver.js` 6201 of 11236 (55.2%), 82 files; `ONLINE_GAME_SPECIFICATION.md` FULL (outside-known-roots, with the reason); a prose-only change (`meta/kanban/board.md`) 40 files = 3995 of 11236 (35.6%). AC-7 profile shares (source `meta/profiling/suite-durations-20261023.txt`, 1426 s over 214 files; files newer than the profile count 0 s, so lower bounds): prose only 35.6% (saved 64.4%), `player/play.js` 63.0% (37.0%), `book_pdf_generator.py` 55.5% (44.5%), `solver.js` 67.6% (32.4%), `export/layout.py` 65.9% (34.1%): **the saving is real but modest: the always-on scanners alone cost 35.6% of the profile and an asset change costs 63 to 68%.** Per-AC tests (all in `tests/test_impact_set.py`, 34 -> 92 node ids, 58 added, 0 removed or renamed): AC-1 `TestImpactSet_AStaticAssetSelectsTheTestsThatReadIt` (the 11 recorded readers as a superset, plus the player-selector readers with a floor of 16, a not-everything control), AC-2 `..._AnUnderivablePathFailsClosedAndSaysWhy`, AC-3 `..._TheBrowserFamilyGuardFollowsItsFamily`, AC-4 `..._ACoreChangeStillReachesTheBookTests`, AC-5 `..._EveryShippedAssetHasADerivation` (equality with `set(ASSET_RULES)`), AC-8 `..._TheGateInvocationPrintsOneBlock`, REGRET `..._RegretEveryKnownPastMissIsNowSelected` (10 ids, one per recorded row), extra controls `..._AMentionIsNotALoad`, `..._APageOutsideTheKnownRootsIsDerivedNotRefused`, `..._RelativeImportsAreEdges`, `..._ADeletionOrRenameIsNotInvisible`. TDD: 28 tests red against the old script. Census: 1159 passed + 3 skipped (unarmed DB) + 2 FAILED on the first run (a file name in the AC-4 baseline matched the grep behind `RENDER_HEAVY_SNAPSHOT` in `test_suite_profile`, CARD-251's shape; fixed by spelling the name in two pieces, CARD-218's precedent, without editing `meta/`); after the fix 10 of the 13 files re-run: 967 passed, 0 failed (test_cli, test_browser_fixture_scope and test_card_349_cold_database were NOT re-run after commits 2 and 3, which touch only the test file). Mutants (19, `-x`): static-asset readers dropped, collect-only census dropped, glob/prefix referrers dropped, unknown path returning narrow, unread asset narrow, unknown asset type inert, a rule dropped from the table, always-on set emptied, FULL downgraded to a list, browser filter dropped, relative imports reverted, rename detection back on (first survived because the staged `--cached` query listed the old path; the control now uses a committed rename), migrations rule removed, conftest rule removed, a mention counted as a load, a FULL reason losing its rule, tree readers dropped, the gate block losing the count, a root-level `.md` made derivable: each killed by a named test; TWO equivalent survivors (M2c importers-of-a-changed-test: the prefix/name rule already selects them; M6b the early return for pre-corpus FULL). AC-9 REPLAY of `git log --merges -20 --first-parent`, derived against each merge's own tree, new / old selection sizes: `4cb3e836` 57/39, `d78fd683` 215/208, `01edc331` 67/44, `652c16f8` (player) 51/FULL, `18c9a963` 71/41, `c8a19833` (player) 50/FULL, `adc8c9a5` 66/40, `423aef15` (player) 46/FULL, `a044dc62` 43/37, `c33797ea` 48/39, `8cbd720e` 51/40, `fd37038c` (player) 47/FULL, `dc90b19a` 46/38, `e4849464` 61/44, `18aeac30` (player) 45/FULL, `95db8fbe` 65/38, `f1c9ce93` 61/37, `597cdf57` (tests/conftest.py) FULL/FULL, `63f246a2` 39/36, `9971257a` (player) 40/FULL. **FULL fraction under the new script: 1 of 20 (5%), the `conftest.py` merge; the old script answered FULL on 7 of 20 (the 5 player merges, for the wrong reason: location).** Non-FULL sizes 39 to 215 files, median about 51 (the sizes include the collection-census tests, about 55 s of `test_browser_fixture_scope` on nearly every merge). None of the 20 hit one of the three known misses (all code or test merges: no `src` static asset changed, no `test_puzzle_solver_*` file changed, none prose-only), so the author also replayed the merges that did: `476abf18` (CARD-271): the old script omitted 4 recorded readers (`test_puzzle_solver_page`, `test_book_finalise_guide_preview_layout`, `test_puzzle_solver_hint`, `test_puzzle_solver_percent`), the new omits none; `49c5e826` (CARD-251): both cover `test_suite_profile`; `48457877` (CARD-305): a migration, now FULL by rule. REGRET EVIDENCE (past misses recorded in cards, roughly 9 cards went red at the gate on a test outside the review-cycle selection, several on the same two registries, the browser-fixture and the frozen census): CARD-271 (11 readers of `admin.css`/`solver.js` plus `test_browser_fixture_scope`, 27 unregistered ids), CARD-269 (`test_browser_fixture_scope` again, 35 ids; "no review cycle could have caught it"), CARD-218, CARD-268 (five browser tests red after a CSS flex shift, commit `cec9cd5e`), CARD-251 (`test_suite_profile` `RENDER_HEAVY_SNAPSHOT`), CARD-314 (`test_check_ref_resolution` frozen census +3), CARD-308 (the same census moved by CARD-285's merge, a main-moved case), CARD-223 (`test_browser_fixture_scope` document test), CARD-305 (`test_book_floor` TestMigration012); CARD-285 and CARD-204 record merge-order effects a per-card selection cannot see; excluded as not selection misses: CARD-261, CARD-299 (harness errors), CARD-234, CARD-237, CARD-292 (flakes). NOT modelled, so not claimed: dynamically built template names, behavioural coupling through JSON field names, routes (any browser test importing the admin app is selected for an admin asset), code outside src/tests/scripts/meta/docs/player; merge-order and integration effects stay with the wave-close full run. Over-selection is deliberate. Not done by the author: the policy switch (`config.yml`, gate briefs), the card file, a full-suite node-id comparison at base (only this test file was compared). Not yet reviewed.

[Review 1/3] Score: 5.5 (threshold 8.0 NOT reached; NOT CERTIFIED; 2 BLOCKERS = proven misses, plus majors F-002, F-004, F-005; cycle 2 required). Reviewer-reported, not re-run by the orchestrator; "mine" is the reviewer's. Findings in `meta/review/CARD-286-cycle1.yml` in a private clone (`scratchpad/r286/tip`), instruments, scripts and run outputs in `~/Documents/nonogram-reviews/CARD-286/review-cycle1-instruments/`. **THE CORE QUESTION: is the selection a superset? NO.** BLOCKER F-001 (mine): neutralising the `.plan-matrix input { min-inline-size ... }` rule in `admin.css` selects 96 files that do NOT include `tests/test_book_setup_print_mobile.py`, which goes RED (`TestPrintSetupMobile_PlanInputsShowThreeDigits::test_every_plan_input_shows_a_three_digit_value_in_full`, scrollWidth 56 > clientWidth 44); the whole 96-file selection run on the mutant gave 6568 passed, 19 skipped, 0 failed (29:51): a gate on the selection would have been GREEN while the full suite is red. Cause: that test builds the app through `from tests.test_puzzle_solver_page import _build_app` (a TEST module); `_Corpus.importers` follows only src-to-src edges, so the `importers(modules) & executors()` arm never sees it, and the test names no `.plan-matrix` selector (it uses element ids). This is the card's headline case (admin.css to browser tests) still open for this reader and is not in the card's "not modelled" list. BLOCKER F-003 (mine): `pytest --fixtures-per-test` shows 13 test files use conftest fixtures (`test_batch_history`, `test_bulk_operations`, `test_card_156_db_fixture`, `test_db_e2e_smoke`, `test_db_engine_lifecycle`, `test_db_isolation`, `test_puzzle_edit_routes`, `test_puzzle_preview`, `test_puzzle_review_bulk_read`, `test_wave1_e2e`, `test_wave2_async_generation`, `test_wave3_e2e`, `test_wave3_image_generation`); `tests/conftest.py` imports `admin.app`, `puzzle_review`, `batch_generator` and `db.session`; the derivation treats conftest as neither a node nor an edge. Proven: changing the mimetype in `api_get_image` (`admin/app.py`) to `application/octet-stream` reds `tests/test_wave3_e2e.py::TestWave3ImageGeneration::test_image_serving_endpoint_mime_types`, which is OUTSIDE the 126-file selection for `app.py` (the two selected files that name `/api/image/` stay green, 47 passed). Also outside the selection: for `app.py` `test_db_e2e_smoke` and `test_wave3_image_generation`; for `puzzle_review.py` `test_db_e2e_smoke`, `test_puzzle_preview`, `test_wave3_image_generation`; for any `export/*`, `solver/*`, `limits.py` or `errors.py` change `test_card_156_db_fixture`, `test_db_e2e_smoke`, `test_db_isolation`, `test_wave3_image_generation`. (The `puzzle_review.get_puzzle -> None` plant is masked: selected `test_bulk_operations` also reds.) MAJOR F-002: same mechanism, masked in the instance tried: deleting the admin.css `<link>` from `base.html` selects 141 files and omits `test_book_setup_print_mobile` (1 red), `test_books_list_mobile` (5 reds), `test_book_arrange_play_link` and `test_status_filter_default`, but the selected `test_admin_design_tokens::test_the_panel_serves_both_stylesheets` also reds; a `base.html` edit that leaves the link alone would not be masked; unselected browser tests by changed file (over-count): `admin.css` 2, `puzzle_edit.js` 9, `base.html` 6, `book_setup_print.html` 25, `book_finalize.html` 25. MAJOR F-004: helpers that `conftest.py` imports are not FULL though conftest is: `tests/hang_guard.py`, `database_guard.py`, `full_suite_lock.py`, `db_name.py`, `helpers/mock_generator.py`, `helpers/undefined_table_report.py`, `tests/__init__.py` (selections of 46 to 51 files); plant: hang-guard default 300 -> 0.05 kills `tests/test_solver.py` (outside the 47-file selection) with rc=1. MAJOR F-005 (gate contract): with a collection error in the tree the gate still prints "answer: SELECTION ... nothing more is owed" beside "tests: 9712 of unavailable (pytest --collect-only exited 2)", exit code 0; exit code is 0 for both FULL and SELECTION so a script cannot branch on it; every pytest run including `--collect-only` stops before collection under a held full-suite lock (read), so the count shows "unavailable" while the SELECTION text still prints; a held lock was not exercised. METHOD 1 (mine): the reviewer's own ast model over src/tests/scripts (relative imports, ancestor package `__init__`, dotted strings, importlib path loads, text references) plus an import-time ground truth (each of the 243 test files and `tests.conftest` imported in a subprocess, modules loaded recorded, 95 src and helper modules): after subtracting the conftest closure the only import-time misses are `db/__init__.py` and `db/session.py` omitting `tests/property/test_regrade_determinism.py` (no ancestor-package `__init__` edge), `tests/fixtures/__init__.py` omitting 3 files, `tests/property/__init__.py` omitting 31 files (practically masked because conftest imports `nonogram.db`); about 65 other scenarios (assets, templates, player/, fixtures, scripts, docs, meta, config) turned up no further real misses; path-from-pieces counter-example: planted tests reading `STATIC / f"{stem}{ext}"` and `os.path.join(..., "solver" + ".js")` are NOT selected for `solver.js` (a test that also names a declared selector or walks the directory is caught); the `no-importer` FULL rule never fires for a `nonogram.*` module because a bare `import nonogram` binds the whole subtree (over-selects, not a miss). METHOD 2 (mutation of 11 files in clones, unselected related tests run each time): RED outside the selection for `app.py` (F-003), `admin.css` (F-001), `base.html` (F-002, masked), `hang_guard.py` (F-004), `books_list.html` (renaming `data-off-plan` reds `test_books_list_mobile`, 3 reds outside the selection, masked because selected `test_books_list_plan_stats` also reds); no miss for `solver_state.js`, `tokens.css`, `metadata.js` (4 unselected browser files, 339 passed) and `player/play.js` (6 unselected browser files, 106 passed); `puzzle_review.py` masked; `limits.py` (MAX_SIZE 29) reds conftest at import so every selection sees it. METHOD 3 (history, 50 merges, first-parent 21 to 70 back, derived against each merge's own tree): **FULL 19 of 50 = 38%** (by rule: no-reader 9, outside-known-roots 8, migrations 2); **11 of the 19 are FULL only because the card committed `scratchpad/**` or `meta/profiling` probe scripts**; the rest `player/vercel.json` (2), `CLAUDE.md` (2), `.gitignore`/`.gitattributes` (2), migrations (2); non-FULL selections min 25, median 58, max 198 files; the author's 20 recent merges re-derived: 1 FULL (`597cdf57`, conftest), sizes match except the player merges (the card records 51/50/46/47/45/40; the tip gives 69/67/65/64/62/57: **the card's replay numbers for the player merges are STALE**); wider window (mine plus the card's 20): 20 of 70 = 29% FULL; regret corroboration: CARD-269 (`test_browser_fixture_scope`) and CARD-314 (`test_check_ref_resolution`, +3 census) both went red at the gate outside the cycle selection and both are selected by the tip on the merge trees; CARD-309, 336, 337, 304 each say the impact radius cannot see cross-card censuses; also selected on the replayed trees: `476abf18`, `4545911a`, `2d9793e5`; no history case found of a merge where a derived selection omitted a red test, but history cannot show the F-001/F-003 classes because those merges got the full suite. METHOD 4 (fail closed, mine): every FULL rule shown firing (`unanalysable`: `scripts/impact_set.py`, `tests/conftest.py`; `conftest`: `tests/sub/conftest.py`; `outside-known-roots`: `ONLINE_GAME_SPECIFICATION.md`; `migrations`; `unknown-asset-type`: `.xyz`; `no-reader`: `scripts/preview_player_site.py`, an unread template; `no-scanners`: a tiny repo; `no-importer`: `tests/helpers/zz_new.py`); the always-on set is derived (38 scanners on the tip tree incl. the census tests; a deleted scanner simply disappears; a scanner using an idiom outside `SCAN_IDIOMS` is not always-on: survivors S18/S19); smallest selection 38 files for any non-empty non-FULL change, 0 for an EMPTY changed set (`--gate --base HEAD` prints "answer: SELECTION ... tests: 0 of 11236 ... nothing more is owed"). METHOD 5: `--gate` reproduces the card's figures; share of collected tests by change: prose 3995 (35.6%), `player/play.js` 5287 (47.1%), `solver.js` 6201 (55.2%), `export/layout.py` 9712 / 210 files (86.4%); `--gate --against main` on the tip itself answers FULL because `scripts/impact_set.py` is UNANALYSABLE; the Makefile targets still work; the docstring still says "there is no Makefile" (stale). METHOD 6: node ids 34 -> 92, 0 removed, all 92 pass; Touches exactly the two files; no skip/xfail/bare early return added; the 13 census modules green on the tip (450, 92, 26, 68, 13, 167, 62, 41, 40, 8, 25 + 3 skipped, 31, 138); 17 analogues of the author's 19 mutants all KILLED; **M2c is NOT equivalent** (survives all 92 tests; on the live tree the importers branch adds files beyond the name/prefix rule for 5 changed test files through test-module chains A<-B<-C, e.g. `test_web_server` adds `test_export_a4_golden` and `test_layout_page_spec`); M6b not re-fired; the reviewer's 11 survivors: fail-open S4 (iterdir idiom dropped), S8 (prefix-name branch), S10 (collect returncode check dropped), S14 (unreadable test not treated as scanner), S15 (outside-root directory-namers), S16 (`chromium` executor idiom), S18 (`os.walk` scanner idiom); benign (over-select or more FULL) S1, S2, S3, S12; S20 (deleted-file existence guard inverted) selects a deleted test path so pytest then errors on the missing file; killed S5, S6, S7, S9, S13, S17, S19. PLAIN-WORDS VERDICT (reviewer): NOT YET: the gate as written would let a change through green that the full suite catches (proved twice: a CSS rule, then an admin app route). Two fixes close the main holes: (1) follow imports through test modules and through conftest when deciding which browser and fixture tests reach the app, OR (2) the cheap safe rule: an admin static, template or `admin/app.py` change selects EVERY browser test and every test using a conftest fixture; also make `--gate` refuse to print SELECTION when the count fails and give it a non-zero exit for FULL and failed counts, and make conftest-imported helpers FULL like conftest. If the owner switches anyway before those fixes: run the full suite at wave close and every N merges (suggest every 5); make admin/static, templates, `player/` and `admin/app.py`/`db/*` cards always get the full suite; treat a failed count as FULL. TIME SAVED (mine, re-derived from `meta/profiling/suite-durations-20261023.txt`, 1426 s over 214 files, lower bounds): prose-only 35.6% of the profile (saves 64%), `admin.css` 69.3% (saves 31%), `app.py`-class changes 50.6% to 69% (saves 31 to 49%), `export/layout.py` selects 86% of collected tests (saves almost nothing); over 18 non-FULL merges in the sample the profile share was min 35.5%, median 59.4%, max 84.2%; **mean saving on non-FULL merges 40.9%; counting FULL merges as zero, 25.4% over 29 merges; realistic saving today about a quarter to a third of the gate time, not two thirds.** Residual risk: a green gate then a red full suite at wave close, usually in a browser layout test or a fixture-driven admin test; cannot see merge-order effects (main moved after the branch), JSON-field and behavioural coupling, paths built from pieces, frozen cross-card censuses (the wave-close run owns those), and the conftest-fixture edge until fixed. Not done by the reviewer: full suite, `test_kill_matrix`, a held lock, one-by-one gate-red lists of the 70 replayed merges, M6b, armed DB variants (DATABASE_URL unset), exhaustive mutation (11 files chosen for a cheap unselected-test set).
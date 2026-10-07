# Backlog

_Merged 2026-10-02: this file and the old `## Backlog` notes in `board.md` were
two overlapping lists. They are now one, here. `board.md` shows only the top of
this file. Duplicates are folded into one entry, and every item that became a
card names its card._

## Owner decisions (nothing moves until you answer)
- [ ] CARD-147 F-007 (three cards old): should the baseline chain's fixtures get `superseded_by` back-pointers? Each fixture's `warning` ends "…and says so here", and its prohibition covers regenerating digests, which an additive key is not. Only card145 and card128 have one; card144, card149 and card146 don't. card146 matters most, because it's still live evidence (hardcoded as `PRE_CARD_BASELINE`)   @tech-debt
- [ ] Per-directory READMEs: no directory under `src/` has one, so every book card skips the docs step, and `tests/README.md` is still titled "Admin Panel Test Suite - Wave 1" (about 20 waves stale, names no book test file). Either make "no per-directory READMEs" the convention and drop the step, or create them once and rewrite `tests/README.md`   @tech-debt

## Architecture model (→ /forge:architect, one session)
- [ ] Dead `check:` refs on mandatory rules. These name tests that exist nowhere under `tests/`, only inside comments: ADR-0006/R1 `TestDependencyBaseline_IsExactlyPillowAndNumpy` (the real test is `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`, per CARD-161 F-007), **CON-005** `PropertyTest_Solver_NeverFalsePositiveUniqueness` (the one mandatory correctness property), INV-001 `TestComputeClues_MatchesGridExactly`, INV-002 `TestExport_RejectsUnverifiedPuzzle`, INV-008 (three checks), INV-012 (six checks), ADR-0029/R2, INV-009..INV-011. Step 8h has been reporting some of them as covered. Fix each ref (write the test, or re-type the check as `review-lens`)   @tech-debt
- [ ] `system_rules.py --verify-refs` matches text, so a name inside a comment counts as "found": it reports `dead_check_ref: []` with `check_refs_verified: true` while the refs above are dead. Make it resolve a collectible pytest node id, and make `adr_integrity` fail on a dead ref instead of warning (lives in forge_1, outside this repo)   @tech-debt
- [ ] ADR-0029/R4's ref `test_every_import_in_the_package_points_inward` exists but tests the import graph, not the rule (overlap masks relative to a line's known cells). No dead-ref check can catch a check that can't test its rule   @tech-debt
- [ ] Validator ERROR, pre-existing on main: `ADR-0025 circular supersession: ADR-0025 → ADR-0031 → ADR-0025`. The guess-tier ADR chain cannot be resolved   @tech-debt
- [ ] The deployed panel's 512 MB memory limit is not an NFR anywhere (CARD-145). The export could break it through five waves with every gate green. Needs an NFR with a check   @tech-debt
- [ ] Wave-30 goal-check (lean b, requirements incomplete): behaviours shipped by CARD-158/159 exist only as card ACs, not in requirements.yml: inches trims reachable on Print setup, the stored trim on the book page ("Not set"/"Cannot be read"), step prose agreeing with the stepper, /book/create keeping typed input, two download buttons per page, lost-cover handling (FR-043 has no AC for it). Formalise as ACs   @tech-debt

## Bugs and tech debt (not carded yet)
- [ ] CARD-120 F-007: typing an edited cell back to its current prefill value doesn't release the hand-edit mark; a count change judges edits against the old prefill. Site: `book_manager.py` (`revise_plan`)   @tech-debt
- [ ] CARD-120 F-008: the refusal page's Planned row is read from the stored plan, not the submitted one. Site: `app.py` (setup-print)   @tech-debt
- [ ] CARD-136 (owner-accepted 2026-09-23): in memory-only mode `get_book` returns the live `Book`, so a caller can write an invalid trim past `set_print_spec`'s validation. Fix by having memory mode return a copy   @tech-debt
- [ ] CARD-118 reviewer minors: the proof route's broad `except Exception` flashes raw exception text; `redirect(request.referrer or ...)` takes its target from the caller; a new `datetime.utcnow()` deprecation; the `ast` importer guard matches on bare filename, not relative path   @tech-debt
- [ ] CARD-148 F-003: `migrations/env.py`'s plaintext URL is kept out of logs only by configuration (`logger_sqlalchemy = WARNING`, no `echo`), not by an assertion. About 2 lines to pin, using the existing subprocess's stderr   @tech-debt
- [ ] CARD-150 F-003/F-004/F-005/F-007: the 14-of-18 figure is an artifact of `--check-only` not existing on the old script; the README tests' `returncode != 0` precondition is met by any failure; the two Docker branches match on database name only, dropping host, port and credentials, with no runtime coverage; nothing asserts G-3's launch target though the stub logs it   @tech-debt
- [ ] CARD-147 F-002/F-003/F-005: `_write_pdf`'s unreachable ValueError guard; the migration's confirmed-redundant UPDATE backfill; `_write_page`'s `mode: str = "RGB"` default one layer below the required keyword (dead today, but exactly the failure the keyword prevents)   @tech-debt
- [ ] CARD-147 F-006: the card's sentence welds two claims the digests can't both carry. The unmoved digests evidence the ink, not the colour space (the fixture's `interior_colorspace_note` already says so)   @tech-debt
- [ ] CARD-147 F-008: `book_proof.render_proof_pdf` still writes DeviceRGB. It's now the one interior-like path that does   @tech-debt
- [ ] CARD-140 F-005: the arrange screen's page labels are keyed by `id(row)`. Safe today, but fails silently if that ever stops holding. Agreed remedy: keep the key and add a count check (labelled rows vs `len(plan.printed)`) that flips `page_plan_failed`   @tech-debt
- [ ] CARD-140 F-006: `puzzle_section`'s `ValueError("ids must be parallel to payloads")` is a caller precondition but lands in the arrange route's WARNING clause with no traceback. Unreachable today   @tech-debt
- [ ] CARD-140 F-007: a row the interior can't draw renders between the "page 3" and "page 4" labels with no marker, so the screen implies it prints on page 3   @tech-debt
- [ ] CARD-145 minors: a same-length byte change would still pass the interior byte-length assertion; the uploaded cover's RGBA path is not measured for memory   @tech-debt
- [ ] CARD-135 F-008: `export_book`'s docstring still claims every route goes through it. Site: `book_pdf_generator.py`   @tech-debt
- [ ] CARD-134: `answer_page_number()` in `tests/test_book_pdf_band.py` still encodes one-answer-page-per-puzzle in its name (correct at both remaining call sites)   @tech-debt
- [ ] Image-mode difficulty sweep: re-run `scripts/measure_difficulty_cutoff.py` over image-derived puzzles and check the 90.0 cutoff against that distribution (owner deferred it after CARD-137)   @tech-debt
- [ ] CARD-155 out of scope: `meta/architecture/requirements.yml:1834` enum_note still says `difficulty.Tier` has "four members"; older ADR-0025 narrative remains in `tests/test_difficulty_tiers.py` around lines 148-204   @tech-debt
- [ ] CARD-155 F-005 (minor): the docstring regression test's regex catches only uppercase `GUESS` and the phrase "or Guess"   @tech-debt
- [ ] CARD-156 F-005: two test runs at once share `nonogram_test`, and the per-session `DROP SCHEMA public` wipes the other run's schema mid-flight. Only the full-suite lock prevents it today. Per-run databases or a session-level advisory lock would make it safe   @tech-debt
- [ ] CARD-156 F-006 (minor): the second `TestDbFixture_SchemaIsBuiltOncePerSession` test fails by design when run alone (`-k`, node id, `--lf`), because it compares against state recorded by the first   @tech-debt
- [ ] CARD-156 F-007 (minor): `DROP SCHEMA public` needs the test role to own `public`, and the recreated schema loses its default grants. Documented in tests/README.md, not handled in code   @tech-debt
- [ ] CARD-156 note: the CARD-097 `db_required` reachability hook still sends a read-only `SELECT 1` to whatever `DATABASE_URL` names, before the `_test` guard applies   @tech-debt
- [ ] CARD-152 out of scope: `scripts/diagnose_postgres.sh:90` still hardcodes `nonogram_poc`, the same defect CARD-150..152 removed from the other three scripts   @tech-debt
- [ ] CARD-152 F-006 (minor): the "not reachable" message names only two causes (server down, database missing), not a wrong host, port or credentials; same wording in all three scripts   @tech-debt
- [ ] CARD-152 F-005 (minor): `tests/helpers/admin_scripts.py` imports four private names from `tests/test_start_admin_local.py` (`_DOCKER_STUB`, `_PSQL_MODEL`, `_all_pairs`, `_plain`); renaming one breaks both new suites   @tech-debt
- [ ] CARD-152 F-007 / stale text: scripts/README.md says "Python 3.11+" (pyproject needs 3.14); stale docstring at `tests/test_start_admin_local.py:533`   @tech-debt
- [ ] CARD-153 F-003: the Finalise route calls BookManager's private `_refuse_unless_the_planned_book`; needs a public read-only gate in `book_manager.py`   @tech-debt
- [ ] CARD-153 F-009/F-011 (minor): a plan tripwire on GET Finalise is logged twice (helper + Flask); the G-1 "never laid out again" spy only sees layouts through `BookPDFGenerator` (the only path today, per ADR-0036/R2)   @tech-debt
- [ ] Wave-29 goal-check: `PrintSpecValidator.validate_margins` (CARD-154) refuses nan/inf but not a margin below the 0.635 cm minimum (accepts "0.5"). Unreachable today (no margin field on Print setup, `set_print_spec` writes no margins); a stored small margin makes Finalise fall back to "about N"   @tech-debt
- [ ] CARD-157 F-004: two more one-session-per-puzzle loops remain: `_book_member_records` (the /books list, app.py) and the floor-check loop (`book_manager.py` ~:1050). Both can use `PuzzleReviewService.get_puzzles`   @tech-debt
- [ ] CARD-159 F-002/F-003 (minor): no route-level test for below-minimum/zero/negative trims now the browser min is gone (the server refuses them); a refused New book shows the edit-mode alert ("General info not saved… Nothing stored was changed")   @tech-debt
- [ ] Wave-30 goal-check: on a book with no puzzles, /books offers the interior download (returns a 200 PDF) while /book/<id> disables the same button (book_detail.html ~:90-96). No AC covers either   @tech-debt
- [ ] CARD-160 F-004 (minor): the player's cell bounds (14px/28px) and thin-rule color-mix live as local custom properties in admin.css; promote them to tokens.css   @tech-debt
- [ ] CARD-160 F-006 (minor): the /puzzle/<id>/solve route calls the private `PuzzleReviewService._as_readable_grid`; expose a public read   @tech-debt
- [ ] CARD-160 F-012 (minor): `isBoard` reads `value.cells` instead of own data (mutant survived); outside the trusted-in-page scope the owner set, still refused before painting   @tech-debt
- [ ] CARD-161 F-008/F-009/F-010 (minor): the usage hint is never asserted visible (mutant survived); solver.js header says drags use "the selected tool" (it's the tool at pointerdown) and the isZ comment says "non-Latin" where it means any non a-z key; the older scripted-focus keyboard test is superseded by the parametrized ones   @tech-debt
- [ ] Puzzle player: cells cannot be marked from the keyboard (no AC asks for it; controls are keyboard-reachable). Needs its own card if wanted   @feature
- [ ] Flake watch: `tests/test_book_ready_gate.py::…test_save_plan_returns_the_book_to_draft[db-ready_for_pdf]` failed once in CARD-161's gate 0 and passed 3x in isolation and in every later gate   @tech-debt
- [ ] CARD-163 F-001/F-003 (minor): puzzle_solve.html header comment — "Its text is announced…" no longer clearly refers to the banner; the redo-button-noop case doesn't assert Redo is aria-disabled before the click   @tech-debt
- [ ] Wave-31 goal-check: the player passes `tier.value.upper()` (app.py ~:5332), so its header badge and tab title say "MEDIUM" where every other screen shows the stored "medium"   @tech-debt
- [ ] Wave-31 goal-check: the picture name is in the player's page source before solve (hidden solved banner, puzzle_solve.html ~:55) — not visible, AC-322 holds, and CON-021 already ships the solution in the page; matters only for a public player   @feature
- [ ] Wave-31 goal-check (requirements incomplete): FR-044 leaves two player rules unstated — a drag follows the line of its FIRST move away from the start cell (a drag that slips down first follows the column), and board cells are pointer-only (the statement says "every control" is keyboard-reachable; AC-310 covers only tools/undo/redo/reset). Formalise at /forge:architect   @tech-debt
- [ ] ADR-0038/R8 requires CI to run `playwright install chromium`, but the repo has no CI configuration; add it when CI exists (or record the rule as local-only)   @ops
- [ ] CARD-168 owner action: fill the TODO(owner) rows in docs/deploy/render.md from the Render dashboard (service type, Python version, Build/Start Command, env var names, migrations on deploy)   @ops
- [ ] CARD-168 F-002 (pre-existing): scripts/README.md "Manual Commands" still runs bare `pytest` with DATABASE_URL defaulting to nonogram_poc, which the test guard refuses; F-001: render.md's env table omits PYTHONUNBUFFERED (set in render.yaml); F-003: the 2026-09-23 incident evidence render.md cites is recorded nowhere in the repo   @tech-debt
- [ ] CARD-164 F-002: five sibling tests in tests/e2e/test_admin_workflow.py (test_tc_001, test_preview_page_displays_original_image, test_metadata_shown_on_preview, test_tc_002, test_tc_003 — lines ~86/100/112/130/170) still post the dead `images` field and pass on the "No images selected" redirect — hollow the same way test_size_configuration_applied was   @tech-debt
- [ ] CARD-164 F-001 (minor): test_size_configuration_applied posts field names straight to the route, so renaming the step-1 form's `default_size` select leaves it green (mutant M8) — GET /batch/create and assert the field names, or narrow the docstring   @tech-debt
- [ ] CARD-165 F-001/F-002/F-003 (minor): the printed-number test reads the band only via the single-puzzle-page path (no shared two-up fixture); the no-plan banner points to Finalise even when the cause is a code bug; the stored-order fallback with a repeated id is untested (mutant survived)   @tech-debt
- [ ] CARD-167 F-101/F-103 (minor): the 10 pt floor test measures top-to-baseline, so wrapped lines without capitals under-read (~8.4 pt for 11 pt type; at 11x17 cm "way." wraps alone); the spacing after each example drawing is untested; CARD-149's type-test docstrings quote the old guide text   @tech-debt
- [ ] CARD-167 spot-check: divider and cover pages set their type in pixels, not points (CON-020 is checked in pt elsewhere)   @tech-debt
- [ ] CARD-166 F-001/F-002 (minor): the plan-input CSS comment ties --space-2 to Bootstrap's literal .5rem padding (equal by value only); both new test files import private helpers and browser fixtures from tests/test_puzzle_solver_page.py — move shared fixtures to conftest/helpers   @tech-debt

- [ ] CARD-170 drafting: a puzzle printed alone goes through `_blank_page` → COMP-007 `render_pages`, which also renders the solved page that `_blank_page` throws away: one wasted full-size page image per lone puzzle (memory/time). Needs a `render_pages` change in COMP-007   @tech-debt

- [ ] CARD-176 F-001/F-002 (minor): no test row pins the documented echo of a bare leading token (`hunter2://`); AC-1's echo check accepts any corpus scheme rather than the one drawn for that case   @tech-debt
- [ ] CARD-176 F-003: a URL with leading whitespace (`' postgresql://…'`) now gets `<malformed scheme>` — a weaker operator hint than before; consider stripping before the grammar check   @tech-debt

- [ ] CARD-169 F-002 (minor): the guide strip's cell size `--strip-cell: 1.5rem` is a local value in admin.css — promote it to a design token or record it as a deliberate local value   @tech-debt
- [ ] CARD-169 owner check pending: look at ~/Documents/nonogram-reviews/CARD-169/finalise-guide-preview.png beside CARD-167's guide-book1-8.5x11.png (merged on pipeline evidence by owner choice)   @feature

- [ ] CARD-172 F-001/F-002 (minor): a test comment credits the 1493/2048 cap-height ratio to an OS/2 field the bundled font lacks (value correct); `_annotate`'s docstring claims square page 2 keeps its foot note but only 11×8.5 is asserted   @tech-debt
- [ ] CARD-172 F-003: `_annotate` takes a narrow outer side strip before a clue corner that fits — on e.g. an 8.5×8 trim with a small outside margin the note becomes 30+ one-word lines. Not reached on the card's trims; prefer the corner when the strip is narrower than N mm   @tech-debt

- [ ] CARD-175 F-001/F-002/F-004 (minor): the plan-hints summary uses the browser's default focus ring, not the `--color-focus` ring; plural-test comments name per-cell hints the test doesn't assert; a test comment still says ~176 px (now ~169 px)   @tech-debt

- [ ] CARD-171 note: catching ValueError around `set_book_status` in Finalise sends its other refusals ("published", "no puzzles", "invalid status") to a flash with no log line (never logged before either; only the plan-gate case is tested) — decide whether they are owner refusals or errors   @tech-debt

- [ ] CARD-170 F-007 (minor): tests/test_book_pdf_band.py class docstring states the "no other ink within about a line's height sideways" rule loosely; no measured case is misdescribed   @tech-debt

- [ ] CARD-174 F-004 (minor): tests/test_print_specs.py:524 comment says 18.8976 × 2.54 = 48.0 (it is 47.999904; the assertion is right). Also owner wording check: the inch minimum refusal says "on both sides" where the cm one says "in both dimensions"   @tech-debt

- [ ] CARD-169 owner look (2026-10-05): the deferred visual check found the Finalise guide preview needs changes — owner to say what   @feature

- [ ] CARD-177 drafting: other handlers still flash/return raw exception text — `delete_book` (pure DB call; strongest), the Finalise cover upload, proof pages (owner refusal mixed with real errors), batch upload/generate, and five API routes returning plain-text 500 bodies   @compliance
- [ ] Architect delta (CARD-183): FR-044 says "Hints are out of scope"; the owner chose a reveal-one-cell hint (2026-10-05) — amend FR-044 with the hint ACs   @tech-debt
- [ ] Architect decision (CARD-184): puzzle-page clue digits scale with the cell (8.6 pt on Book 1 30×30, 3.6 pt at the 10 cm trim; the 4.8 mm cell floor caps them ~8.4 pt) — should CON-020 exclude clue digits, or the cell floor rise? CARD-184 exempts them by name in its test; also flip CON-020 to its new test   @tech-debt

- [ ] Architect delta (owner solver test doc 2026-10-05, CARD-185..189): FR-044 gains the "?" mark (186), clue circling (188), % solved (187), brush-led click sequences superseding AC-303/AC-304 (189) and browser-local resume (185); CON-021 "play state is never persisted" and FR-044's "no play state is persisted" must allow this-browser localStorage BEFORE CARD-185 runs   @tech-debt

- [ ] CARD-179 F-003 (minor): `_wrapped` docstring doesn't say the token after an over-wide × is taken as M with no other rule   @tech-debt

- [ ] CARD-184 owner check pending: answer-page and no-Arial divider renders in ~/Documents/nonogram-reviews/CARD-184/ (merged on evidence by owner choice)   @feature
- [ ] CARD-184 F-001 (minor): `test_only_the_two_clue_writers_are_exempt` passes by construction (redundant with test_the_exemption_rule_by_name); stale 'card147' docstring at tests/test_book_pdf_memory.py:1163   @tech-debt

- [ ] CARD-177 owner check pending: the new generic flash wording (renders in ~/Documents/nonogram-reviews/CARD-177/; merged on evidence by owner choice)   @feature
- [ ] CARD-177 F-001/F-002 + OOS-3 (minor): no test asserts log-before-flash; AC-2 redirect tested only without Referer; /generate-pdf can show both success and failure flashes if sending the file fails (pre-existing)   @tech-debt

- [ ] CARD-178 owner check pending: 18.89 reopen renders in ~/Documents/nonogram-reviews/CARD-178/ (merged on evidence by owner choice)   @feature
- [ ] CARD-178 F-001/F-003: tests that reset db.session's engine don't restore module globals (fixed per test in CARD-178) — add an autouse conftest fixture snapshotting engine/SessionLocal/_engine_url   @tech-debt
- [ ] Retro note (CARD-178 F-005): reviewers this wave cited test counts/ids no run produced (CARD-178 cycles 1–2); the 8h spot-check caught it — keep the 'literal pytest output for every ✓' rule in the brief   @tech-debt

- [ ] CARD-180 owner check pending: ?status=all renders in ~/Documents/nonogram-reviews/CARD-180/ (merged on evidence by owner choice)   @feature
- [ ] CARD-180 F-001: the selection page intro ('pick the approved grids') and the stepper subtitle ('Pick approved grids') still say approved under ?status=all   @feature

- [ ] OWNER ACTION (CARD-181): back up nonogram_poc and apply migration 014 (`alembic upgrade head`) before using the panel; check Render's database (`alembic current` → 014) before deploying — batch pages 500 at 013   @ops
- [ ] CARD-181 F-001..F-003 (minor): requested_tier_label docstring says unknown → None but 'guess' reads Hard; no test pins Tier.label; migration 014 'no puzzle row touched' claim untested   @tech-debt

- [ ] CARD-188 owner check pending: clue-circle renders in ~/Documents/nonogram-reviews/CARD-188/ incl. the ~0.5 px pill/heavy-rule overlap on 30×30 (F-005) (merged on evidence by owner choice)   @feature
- [ ] CARD-188 F-008 (minor): no render at device scale 1 for the 14 px floor   @tech-debt

- [ ] Flake watch (CARD-183 merge gate): tests/test_puzzle_solver_page.py::TestSolverPageFits::test_the_largest_board_fits_a_laptop_screen[row-clues] returned a server 500 reading the puzzle with DATABASE_URL set, once; passed 3/3 alone   @tech-debt
- [ ] CARD-183 minors F-011..F-014: two polite announcements per hint; Hint by keyboard during the reset confirm moves focus to Reset; 440 ms animation-test window; after Undo the announce region keeps the old hint text   @tech-debt

- [ ] CARD-186 owner check pending: "?" mark and toolbar changes (narrower tool padding; banner in the tools' box on solve; "Hints" on a second row at 1180–1259 px) — renders in ~/Documents/nonogram-reviews/CARD-186/   @feature
- [ ] CARD-186 F-002/F-003 (minor): "?" glyph centring untested (only containment); a solved name of ~40+ chars moves the board 13 px at desktop widths   @tech-debt

- [ ] CARD-185 F-003/F-004/F-005: setBoard-started histories aren't saved (AC-365 wording needs an architect touch-up); G-1 exception should name test_puzzle_solver_hint.py:870; no-op redo corruption only tested at the top of the redo stack   @tech-debt

- [ ] CARD-190 owner check pending: review-page longest-side renders in ~/Documents/nonogram-reviews/CARD-190/ (merged on evidence by owner choice)   @feature
- [ ] CARD-190 F-002/F-003 + O-001/O-004/O-005 (minor): no test pins _side_bounds' 10..30 edge (E1/E4 mutants survive, pre-existing); AC-4 API test doesn't assert the store; pagination test passes under both meanings; stale 'either side' comment in puzzle_review.py; no FR traces the review filter   @tech-debt
- [ ] Flake watch: test_admin_binding.py::…test_the_port_stays_free_on_every_other_interface failed once under parallel pipelines (port held on the LAN interface); passed 3/3 alone   @tech-debt

- [ ] CARD-189 owner check pending: click-sequence renders and the help line (Undecided's first click on a blank cell shows black) in ~/Documents/nonogram-reviews/CARD-189/   @feature
- [ ] CARD-189 F-004/F-005 (minor): only the 'Keep marks' cancel path of Reset is tested for ending a repeat run (Escape path untested); the solver.js/puzzle_solve.html summaries omit the 'first click on a cell already in the brush's state moves on' rule   @tech-debt

- [ ] CARD-191 owner check pending: Sort by size button, confirm text and before/after renders in ~/Documents/nonogram-reviews/CARD-191/; the printed order and page count follow the sort (merged on evidence by owner choice)   @feature
- [ ] CARD-191 (architect): INV-009 says a level's order changes only by an explicit move — reword to 'reorder' (EC-026 already does); AC-7 wording: a DB-mode unsized puzzle is an id with no row   @tech-debt

- [ ] CARD-187 owner check pending: Progress counter renders in ~/Documents/nonogram-reviews/CARD-187/ (merged on evidence by owner choice)   @feature
- [ ] CARD-187 C2-1/C2-2 (minor): template comment rationale covers focus only, not WCAG 1.3.2; admin.css comment cites a test that doesn't assert it   @tech-debt

- [ ] CARD-192 owner check pending: band filter and left/over renders in ~/Documents/nonogram-reviews/CARD-192/ (merged on evidence by owner choice)   @feature
- [ ] CARD-192 minor: reorder-off note reads 'Show all sizes to move puzzles or sort them.' (card quotes it without 'or sort them'); card says 'Print setup (step 1)' but stepper shows step 2   @tech-debt
- [ ] Commit trailer on 04791f4 (CARD-192 implementation) reads Claude Sonnet 5, not the project's Opus 5.5 — history not rewritten; note only   @tech-debt

- [ ] CARD-196 owner check pending: clue-number renders in ~/Documents/nonogram-reviews/CARD-196/ (merged on evidence by owner choice)   @feature
- [ ] CARD-196 F-002/F-003/F-007/F-008 (minor, carried from review): a stale admin.css comment still claims the old two-digit column clearance; a stale class comment in test_puzzle_solver_phone.py about row-gutter width; a test docstring overclaims OWNER_ROW is the only adjacent single-digit row pair; an admin.css comment implies a mixed digit-count row pair is covered by a check it isn't   @tech-debt

- [ ] Architect delta (CARD-193, after it ships): FR-044 AC-343's "given" clause still says "cells at the 24 px phone floor" — CARD-193 removes that flat floor; amend to the CARD-196 numeral-driven floor wording   @tech-debt

## Tests
- [ ] CARD-120 F-009: the trim assertion in `tests/test_book_plan_storage.py` is vacuous in DB mode   @tech-debt
- [ ] Test isolation: `test_card_037_upload_retry` and `test_web_upload` glob the shared system temp dir for `nonogram-upload-*`, so two full suites running at once interfere   @tech-debt

## Features and UX (not carded yet)
- [ ] Online solver, public phase: hosting, the URL namespace for per-puzzle QR codes, and the persisted puzzle-number mapping (raw-requirements Delta 2026-09-24 (a)); the admin POC ships the solution inside the page, which a public solver must not   @feature

## Process (forge machinery, not this repo's code)
- [ ] Card-text defects for decompose: CARD-122 G-1 says "the template imports book_plan.bucket_of" (a Jinja template can't import); CARD-126 G-4 names a test a later card (CARD-131) creates, so it was unverifiable before then; forge:commit's no-Co-Authored-By rule contradicts the required attribution line   @tech-debt
- [ ] Gate hazard (CARD-138): from an older wave branch, `git diff main` reports main's newer files as deletions, including ones matching guardrail globs like `book_*.py`. Every scope and guardrail verdict must be taken against the merge base   @tech-debt
- [ ] Two full-suite lock conventions: cmd-start-review documents a `mkdir` lock on `meta/kanban/.full-suite.lock`, but the dispatcher takes it with `exec 9>` + `flock`, which creates a regular file the `mkdir` form can never acquire. Pick one   @tech-debt
- [ ] Near miss (2026-09-24): two mutation skeptics ran concurrently on the same file. The failure mode is a silently contaminated verdict. The card brief should forbid concurrent mutation skeptics on one file without a lock   @tech-debt
- [ ] Near miss (CARD-199, 2026-10-07): the dispatcher's own full-suite-lock staleness check used `date -j -f` without `-u`, parsing a UTC owner timestamp as local time and misjudging a ~6-min-old lock (held by CARD-193) as stale (>30 min), breaking it and possibly running two full suites concurrently for a few minutes. No corruption observed this time (both runs' results matched), but the script needs the `-u` fix before it mis-fires on a real stale/live boundary   @tech-debt
- [x] A stray locked worktree/branch (`.claude/worktrees/agent-a8a63b2ff3b31ebb2`, `worktree-agent-a8a63b2ff3b31ebb2`, HEAD `14de199`, disposable) was created when CARD-199's orchestrator accidentally passed `isolation: "worktree"` spawning its implementer; the agent recovered and did all real work in the correct CARD-199 worktree. Resolved 2026-10-07: the owning pid (67972) exited; both this one and a second decoy (`agent-a2178e4e07047afbf`, same root cause, from CARD-197's pipeline) force-removed along with their branches   @ops

## Carded 2026-10-05 (roadmap wave 1 → kanban wave 34)
- [x] CON-020 is `status: partial`: no test walks every interior face and asserts the 10 pt floor (CARD-149's three tests cover the guide page only). A test enumerating every `truetype`/`load_default` call on an interior page would make it `covered`   @tech-debt → **CARD-184**
- [x] CARD-161 F-006: player cells are ~18 px at 390 px width, a small tap target for phones (CARD-160 cell sizing)   @feature → **CARD-182**
- [x] CARD-166 observation (owner call): `?status=all` on the book-selection page shows NO puzzles (pre-existing, pinned by CARD-166's G-2) — should "all" list every status there, or be removed?   @feature → **CARD-180**
- [x] CARD-171 drafting (pre-existing): Finalise's outer handler flashes `str(e)`, so a DB error's text (possibly connection details) can reach the screen on a panel the public can reach (ADR-0030). Flash a generic message, log the detail   @compliance → **CARD-177**
- [x] CARD-172 F-004: proof-note wrapping can split a number from its unit ("4.58 / mm") and start a line with "×" — keep units and × with their numbers (owner accepted the current renders)   @feature → **CARD-179**
- [x] CARD-174 F-003: a book stored at 48.0 cm reopens in inches showing 18.90 next to the stated 18.89 in maximum — the reopen conversion should round inward like the limits   @feature → **CARD-178**
- [x] CARD-138: a targeted batch stores no record of the tier it asked for (`batches` has no column), so the panel can't show what a batch was aiming at. Needs a column and a migration   @feature → **CARD-181**
- [x] Online solver: a hint button (the owner's doc makes it optional; left out of CARD-160..162)   @feature → **CARD-183**

## Carded 2026-10-04 (roadmap wave 1 → kanban wave 33)
- [x] CARD-148 F-001: `db/session.py`'s `_scheme_of` echoes anything before the first `://`, so `postgresql:hunter2://h/db` puts the whole string in the RuntimeError, contradicting its own docstring. One-line fix (`scheme.partition(":")[0]`)   @tech-debt → **CARD-176**
- [x] CARD-153 F-010 (pre-existing): `finalize_book`'s outer `except Exception` only flashes, so a transient non-plan error on any Finalise POST action is never logged   @tech-debt → **CARD-171**
- [x] CARD-153 F-006: the global 500 handler shows Flask's generic text, so a page-plan error on GET Finalise isn't named on screen   @feature → **CARD-171**
- [x] CARD-158 F-005 (pre-existing): /books rows are ~650 px tall at 390 px because of the Against-plan hint list   @feature → **CARD-175**
- [x] CARD-159 F-001: Print setup's Limits box says "Maximum height 48 cm (18.90 in)"; 18.90 in is 48.006 cm, which the server refuses (18.89 in is the real maximum). Now the page's only statement of the inch limits   @tech-debt → **CARD-174**
- [x] CARD-159 F-005: trim refusals are worded in cm even after an inches submission; fixing it means editing `print_specs.py`   @feature → **CARD-174**
- [x] CARD-167 follow-up: the Finalise screen's guide preview (book_finalize.html) still says "How to use this book" with the old instructions — make it match the new guide page   @feature → **CARD-169**
- [x] Wave-32 goal-check: a recording PDF canvas saw the highest-tier answer-key band ("Puzzle 5 · Hard") drawn twice during an export — likely the fitting loop measuring before drawing, not a printed duplicate; confirm visually on a rendered answer page (book_pdf_generator answer-key path)   @tech-debt → **CARD-170**
- [x] CARD-118 known gap (tested, deliberate): a square or landscape trim (8.25x8.25, 8.5x8.5, real KDP sizes) leaves no room for the proof foot note, so `proof_pages` raises. Portrait trims all render. **Revisit when the page layout is finalised**   @feature → **CARD-172**
- [x] An unreadable stored print spec degrades into N per-tile "cannot be measured" messages with an override that can't succeed, and never names the remedy. Fails closed, but unhelpful   @feature → **CARD-173**

## Carded 2026-10-04 (roadmap wave 1 → kanban wave 32)
- [x] CARD-159 owner check pending: G-3, the owner's look at ~/Documents/nonogram-reviews/CARD-159/ renders (merged on pipeline evidence by owner choice). Also seen there, pre-existing: at 390 px the plan-table inputs clip "20" to "2("   @feature → **CARD-166 (clipped plan inputs; the owner look stays yours)**
- [x] CARD-163 F-002 (owner call): the player shows the size as ASCII "25x15" (AC-323's literal) where the rest of the admin uses "×"   @feature → **CARD-166 (owner: use ×)**
- [x] A hand-typed empty `?status=` turns off the approved-only default on the book-selection and puzzle-list routes (`request.values.get("status", "approved")` defaults only when the key is absent)   @ops → **CARD-166**
- [x] CARD-158 F-004 (pre-existing): the book page's # column is list order, not the printed puzzle number   @feature → **CARD-165**
- [x] Guide page: worked-example rows and the title wording. Both touch `create_guide_page` (same method as CARD-149)   @feature → **CARD-167 (owner: small fix now, tutorial later)**
- [x] Pre-existing failure: `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied` (red on 89ed292 and since wave 20)   @ops → **CARD-164**
- [x] Stale assertion: `tests/test_wave3_e2e.py:366` expects "Create Batch from Images"; f773015 (2026-09-14) renamed the heading "New batch". The page is fine, the test isn't   @tech-debt → **CARD-164**
- [x] DEPLOYMENT (found 2026-09-23, cost four redeploys): the Render service is managed in the dashboard, so `render.yaml` is ignored (buildCommand, startCommand, env vars). Production ran `flask run` on python3.14 while `render.yaml` pins 3.11, which bypassed CARD-086's gunicorn decision. Either adopt the Render Blueprint so `render.yaml` governs, or mark the file as not authoritative and record the dashboard settings somewhere they can be drift-checked   @ops → **CARD-168 (owner: dashboard stays, document it)**
- [x] CARD-152 (owner decision): `run_admin_tests.sh`'s default database `nonogram_poc` passes the runner's own check but pytest's `tests/database_guard.py` refuses any name without "test". Pre-existing; the README's examples export a `nonogram_test` URL. Change the default?   @ops → **CARD-168 (owner: default to nonogram_test)**

## Carded 2026-10-02
- [x] `setup_admin_local.sh` (:40, :64, :70-74) and `run_admin_tests.sh:24` repeat CARD-150's three defects → **CARD-152**
- [x] CARD-129 F-001/F-002/F-005 (`InteriorCounts.unreadable` never read; bare `except` swallows the plan tripwires; an uncountable book can leave draft; "runs to N" vs "About N") and F-004 (vacuous assertion) → **CARD-153**
- [x] CARD-136: plan and trim commit in two transactions; `validate_trim_size` accepts `"nan"` → **CARD-154**
- [x] CARD-138: `strategy_counter.py` second classifier on 30/70 literals; CARD-137 leftovers (`_CUTOFF_NAMES`, stale "fourth tier" docstring) → **CARD-155**
- [x] `tests/conftest.py` `db_session` drops `puzzles`/`batches` per test, causing 3 failures against a real `nonogram_test` → **CARD-156**
- [x] N+1 reads: CARD-122 `_selected_cells` (~300 sessions per render), CARD-124 status change (~150), CARD-126 F-002 order paths (~150 per click) → **CARD-157**
- [x] CARD-135 cover download on books list and book detail; CARD-130 raw UUIDs and 390 px overflow; CARD-136 stale "Size" row → **CARD-158**
- [x] CARD-130 "Step 1 of 4" and `PROSE_CHECKED`; CARD-130 `/book/create` discards input; CARD-136 inches unreachable → **CARD-159**
- [x] CARD-150 F-006 (launcher's `psql` check and driver-qualified URLs) → **CARD-151**

## Resolved (confirmed on main beaecdd, 2026-10-02)
- [x] CARD-120 O-2: in DB mode the trim from Print setup was never saved. Fixed by CARD-136 (`set_print_spec` writes the trim columns)
- [x] CARD-134 → CARD-129: Finalise's "~N" estimate overstated the page count. CARD-129 now reads the plan's exact `page_count` (`InteriorCounts`, `app.py:835`)

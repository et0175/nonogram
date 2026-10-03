# Backlog

_Merged 2026-10-02: this file and the old `## Backlog` notes in `board.md` were
two overlapping lists. They are now one, here. `board.md` shows only the top of
this file. Duplicates are folded into one entry, and every item that became a
card names its card._

## Owner decisions (nothing moves until you answer)
- [ ] CARD-147 F-007 (three cards old): should the baseline chain's fixtures get `superseded_by` back-pointers? Each fixture's `warning` ends "…and says so here", and its prohibition covers regenerating digests, which an additive key is not. Only card145 and card128 have one; card144, card149 and card146 don't. card146 matters most, because it's still live evidence (hardcoded as `PRE_CARD_BASELINE`)   @tech-debt
- [ ] Per-directory READMEs: no directory under `src/` has one, so every book card skips the docs step, and `tests/README.md` is still titled "Admin Panel Test Suite - Wave 1" (about 20 waves stale, names no book test file). Either make "no per-directory READMEs" the convention and drop the step, or create them once and rewrite `tests/README.md`   @tech-debt
- [ ] DEPLOYMENT (found 2026-09-23, cost four redeploys): the Render service is managed in the dashboard, so `render.yaml` is ignored (buildCommand, startCommand, env vars). Production ran `flask run` on python3.14 while `render.yaml` pins 3.11, which bypassed CARD-086's gunicorn decision. Either adopt the Render Blueprint so `render.yaml` governs, or mark the file as not authoritative and record the dashboard settings somewhere they can be drift-checked   @ops

## Architecture model (→ /forge:architect, one session)
- [ ] Dead `check:` refs on mandatory rules. These name tests that exist nowhere under `tests/`, only inside comments: ADR-0006/R1 `TestDependencyBaseline_IsExactlyPillowAndNumpy` (the real test is `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`, per CARD-161 F-007), **CON-005** `PropertyTest_Solver_NeverFalsePositiveUniqueness` (the one mandatory correctness property), INV-001 `TestComputeClues_MatchesGridExactly`, INV-002 `TestExport_RejectsUnverifiedPuzzle`, INV-008 (three checks), INV-012 (six checks), ADR-0029/R2, INV-009..INV-011. Step 8h has been reporting some of them as covered. Fix each ref (write the test, or re-type the check as `review-lens`)   @tech-debt
- [ ] `system_rules.py --verify-refs` matches text, so a name inside a comment counts as "found": it reports `dead_check_ref: []` with `check_refs_verified: true` while the refs above are dead. Make it resolve a collectible pytest node id, and make `adr_integrity` fail on a dead ref instead of warning (lives in forge_1, outside this repo)   @tech-debt
- [ ] ADR-0029/R4's ref `test_every_import_in_the_package_points_inward` exists but tests the import graph, not the rule (overlap masks relative to a line's known cells). No dead-ref check can catch a check that can't test its rule   @tech-debt
- [ ] Validator ERROR, pre-existing on main: `ADR-0025 circular supersession: ADR-0025 → ADR-0031 → ADR-0025`. The guess-tier ADR chain cannot be resolved   @tech-debt
- [ ] CON-020 is `status: partial`: no test walks every interior face and asserts the 10 pt floor (CARD-149's three tests cover the guide page only). A test enumerating every `truetype`/`load_default` call on an interior page would make it `covered`   @tech-debt
- [ ] The deployed panel's 512 MB memory limit is not an NFR anywhere (CARD-145). The export could break it through five waves with every gate green. Needs an NFR with a check   @tech-debt
- [ ] Wave-30 goal-check (lean b, requirements incomplete): behaviours shipped by CARD-158/159 exist only as card ACs, not in requirements.yml: inches trims reachable on Print setup, the stored trim on the book page ("Not set"/"Cannot be read"), step prose agreeing with the stepper, /book/create keeping typed input, two download buttons per page, lost-cover handling (FR-043 has no AC for it). Formalise as ACs   @tech-debt

## Bugs and tech debt (not carded yet)
- [ ] CARD-120 F-007: typing an edited cell back to its current prefill value doesn't release the hand-edit mark; a count change judges edits against the old prefill. Site: `book_manager.py` (`revise_plan`)   @tech-debt
- [ ] CARD-120 F-008: the refusal page's Planned row is read from the stored plan, not the submitted one. Site: `app.py` (setup-print)   @tech-debt
- [ ] A hand-typed empty `?status=` turns off the approved-only default on the book-selection and puzzle-list routes (`request.values.get("status", "approved")` defaults only when the key is absent)   @ops
- [ ] CARD-136 (owner-accepted 2026-09-23): in memory-only mode `get_book` returns the live `Book`, so a caller can write an invalid trim past `set_print_spec`'s validation. Fix by having memory mode return a copy   @tech-debt
- [ ] CARD-118 reviewer minors: the proof route's broad `except Exception` flashes raw exception text; `redirect(request.referrer or ...)` takes its target from the caller; a new `datetime.utcnow()` deprecation; the `ast` importer guard matches on bare filename, not relative path   @tech-debt
- [ ] CARD-148 F-001: `db/session.py`'s `_scheme_of` echoes anything before the first `://`, so `postgresql:hunter2://h/db` puts the whole string in the RuntimeError, contradicting its own docstring. One-line fix (`scheme.partition(":")[0]`)   @tech-debt
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
- [ ] CARD-152 (owner decision): `run_admin_tests.sh`'s default database `nonogram_poc` passes the runner's own check but pytest's `tests/database_guard.py` refuses any name without "test". Pre-existing; the README's examples export a `nonogram_test` URL. Change the default?   @ops
- [ ] CARD-152 F-006 (minor): the "not reachable" message names only two causes (server down, database missing), not a wrong host, port or credentials; same wording in all three scripts   @tech-debt
- [ ] CARD-152 F-005 (minor): `tests/helpers/admin_scripts.py` imports four private names from `tests/test_start_admin_local.py` (`_DOCKER_STUB`, `_PSQL_MODEL`, `_all_pairs`, `_plain`); renaming one breaks both new suites   @tech-debt
- [ ] CARD-152 F-007 / stale text: scripts/README.md says "Python 3.11+" (pyproject needs 3.14); stale docstring at `tests/test_start_admin_local.py:533`   @tech-debt
- [ ] CARD-153 F-010 (pre-existing): `finalize_book`'s outer `except Exception` only flashes, so a transient non-plan error on any Finalise POST action is never logged   @tech-debt
- [ ] CARD-153 F-006: the global 500 handler shows Flask's generic text, so a page-plan error on GET Finalise isn't named on screen   @feature
- [ ] CARD-153 F-003: the Finalise route calls BookManager's private `_refuse_unless_the_planned_book`; needs a public read-only gate in `book_manager.py`   @tech-debt
- [ ] CARD-153 F-009/F-011 (minor): a plan tripwire on GET Finalise is logged twice (helper + Flask); the G-1 "never laid out again" spy only sees layouts through `BookPDFGenerator` (the only path today, per ADR-0036/R2)   @tech-debt
- [ ] Wave-29 goal-check: `PrintSpecValidator.validate_margins` (CARD-154) refuses nan/inf but not a margin below the 0.635 cm minimum (accepts "0.5"). Unreachable today (no margin field on Print setup, `set_print_spec` writes no margins); a stored small margin makes Finalise fall back to "about N"   @tech-debt
- [ ] CARD-157 F-004: two more one-session-per-puzzle loops remain: `_book_member_records` (the /books list, app.py) and the floor-check loop (`book_manager.py` ~:1050). Both can use `PuzzleReviewService.get_puzzles`   @tech-debt
- [ ] CARD-158 F-004 (pre-existing): the book page's # column is list order, not the printed puzzle number   @feature
- [ ] CARD-158 F-005 (pre-existing): /books rows are ~650 px tall at 390 px because of the Against-plan hint list   @feature
- [ ] CARD-159 F-001: Print setup's Limits box says "Maximum height 48 cm (18.90 in)"; 18.90 in is 48.006 cm, which the server refuses (18.89 in is the real maximum). Now the page's only statement of the inch limits   @tech-debt
- [ ] CARD-159 F-005: trim refusals are worded in cm even after an inches submission; fixing it means editing `print_specs.py`   @feature
- [ ] CARD-159 F-002/F-003 (minor): no route-level test for below-minimum/zero/negative trims now the browser min is gone (the server refuses them); a refused New book shows the edit-mode alert ("General info not saved… Nothing stored was changed")   @tech-debt
- [ ] CARD-159 owner check pending: G-3, the owner's look at ~/Documents/nonogram-reviews/CARD-159/ renders (merged on pipeline evidence by owner choice). Also seen there, pre-existing: at 390 px the plan-table inputs clip "20" to "2("   @feature
- [ ] Wave-30 goal-check: on a book with no puzzles, /books offers the interior download (returns a 200 PDF) while /book/<id> disables the same button (book_detail.html ~:90-96). No AC covers either   @tech-debt
- [ ] CARD-160 F-004 (minor): the player's cell bounds (14px/28px) and thin-rule color-mix live as local custom properties in admin.css; promote them to tokens.css   @tech-debt
- [ ] CARD-160 F-006 (minor): the /puzzle/<id>/solve route calls the private `PuzzleReviewService._as_readable_grid`; expose a public read   @tech-debt
- [ ] CARD-160 F-012 (minor): `isBoard` reads `value.cells` instead of own data (mutant survived); outside the trusted-in-page scope the owner set, still refused before painting   @tech-debt
- [ ] CARD-161 F-008/F-009/F-010 (minor): the usage hint is never asserted visible (mutant survived); solver.js header says drags use "the selected tool" (it's the tool at pointerdown) and the isZ comment says "non-Latin" where it means any non a-z key; the older scripted-focus keyboard test is superseded by the parametrized ones   @tech-debt
- [ ] CARD-161 F-006: player cells are ~18 px at 390 px width, a small tap target for phones (CARD-160 cell sizing)   @feature
- [ ] Puzzle player: cells cannot be marked from the keyboard (no AC asks for it; controls are keyboard-reachable). Needs its own card if wanted   @feature
- [ ] Flake watch: `tests/test_book_ready_gate.py::…test_save_plan_returns_the_book_to_draft[db-ready_for_pdf]` failed once in CARD-161's gate 0 and passed 3x in isolation and in every later gate   @tech-debt
- [ ] CARD-163 F-001/F-003 (minor): puzzle_solve.html header comment — "Its text is announced…" no longer clearly refers to the banner; the redo-button-noop case doesn't assert Redo is aria-disabled before the click   @tech-debt
- [ ] CARD-163 F-002 (owner call): the player shows the size as ASCII "25x15" (AC-323's literal) where the rest of the admin uses "×"   @feature
- [ ] Wave-31 goal-check: the player passes `tier.value.upper()` (app.py ~:5332), so its header badge and tab title say "MEDIUM" where every other screen shows the stored "medium"   @tech-debt
- [ ] Wave-31 goal-check: the picture name is in the player's page source before solve (hidden solved banner, puzzle_solve.html ~:55) — not visible, AC-322 holds, and CON-021 already ships the solution in the page; matters only for a public player   @feature
- [ ] Wave-31 goal-check (requirements incomplete): FR-044 leaves two player rules unstated — a drag follows the line of its FIRST move away from the start cell (a drag that slips down first follows the column), and board cells are pointer-only (the statement says "every control" is keyboard-reachable; AC-310 covers only tools/undo/redo/reset). Formalise at /forge:architect   @tech-debt
- [ ] ADR-0038/R8 requires CI to run `playwright install chromium`, but the repo has no CI configuration; add it when CI exists (or record the rule as local-only)   @ops

## Tests
- [ ] Pre-existing failure: `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied` (red on 89ed292 and since wave 20)   @ops
- [ ] Stale assertion: `tests/test_wave3_e2e.py:366` expects "Create Batch from Images"; f773015 (2026-09-14) renamed the heading "New batch". The page is fine, the test isn't   @tech-debt
- [ ] CARD-120 F-009: the trim assertion in `tests/test_book_plan_storage.py` is vacuous in DB mode   @tech-debt
- [ ] Test isolation: `test_card_037_upload_retry` and `test_web_upload` glob the shared system temp dir for `nonogram-upload-*`, so two full suites running at once interfere   @tech-debt

## Features and UX (not carded yet)
- [ ] CARD-118 known gap (tested, deliberate): a square or landscape trim (8.25x8.25, 8.5x8.5, real KDP sizes) leaves no room for the proof foot note, so `proof_pages` raises. Portrait trims all render. **Revisit when the page layout is finalised**   @feature
- [ ] Guide page: worked-example rows and the title wording. Both touch `create_guide_page` (same method as CARD-149)   @feature
- [ ] An unreadable stored print spec degrades into N per-tile "cannot be measured" messages with an override that can't succeed, and never names the remedy. Fails closed, but unhelpful   @feature
- [ ] CARD-138: a targeted batch stores no record of the tier it asked for (`batches` has no column), so the panel can't show what a batch was aiming at. Needs a column and a migration   @feature
- [ ] Online solver: a hint button (the owner's doc makes it optional; left out of CARD-160..162)   @feature
- [ ] Online solver, public phase: hosting, the URL namespace for per-puzzle QR codes, and the persisted puzzle-number mapping (raw-requirements Delta 2026-09-24 (a)); the admin POC ships the solution inside the page, which a public solver must not   @feature

## Process (forge machinery, not this repo's code)
- [ ] Card-text defects for decompose: CARD-122 G-1 says "the template imports book_plan.bucket_of" (a Jinja template can't import); CARD-126 G-4 names a test a later card (CARD-131) creates, so it was unverifiable before then; forge:commit's no-Co-Authored-By rule contradicts the required attribution line   @tech-debt
- [ ] Gate hazard (CARD-138): from an older wave branch, `git diff main` reports main's newer files as deletions, including ones matching guardrail globs like `book_*.py`. Every scope and guardrail verdict must be taken against the merge base   @tech-debt
- [ ] Two full-suite lock conventions: cmd-start-review documents a `mkdir` lock on `meta/kanban/.full-suite.lock`, but the dispatcher takes it with `exec 9>` + `flock`, which creates a regular file the `mkdir` form can never acquire. Pick one   @tech-debt
- [ ] Near miss (2026-09-24): two mutation skeptics ran concurrently on the same file. The failure mode is a silently contaminated verdict. The card brief should forbid concurrent mutation skeptics on one file without a lock   @tech-debt

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

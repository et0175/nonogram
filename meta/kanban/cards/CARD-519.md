# CARD-519: Write the wave-30 book behaviours into requirements.yml as acceptance criteria

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** business-analyst
**TDD:** —
**Branch:** card/519-wave30-acs
**Worktree:** ../PythonProject4-card-519
**Source:** roadmap wave 11, cut 2026-11-22 on the owner's "start the no-decision wave 11". IDEA-010.
**Idea:** IDEA-010
**Wave:** 90
**Created wave:** 90
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/requirements.yml
**UI surface:** —
**Review score:** 7.0 (cycle 1/3)
**Started:** 2026-11-22T10:32Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

IDEA-010: behaviours CARD-158 and CARD-159 shipped exist only as card ACs, not in `meta/architecture/requirements.yml`, so nothing in the registry says a later change must keep them. Listed then: inches trims reachable on Print setup; the stored trim shown on the book page ("Not set" / "Cannot be read"); step prose agreeing with the stepper; /book/create keeping typed input; two download buttons per page; lost-cover handling (FR-043 has no AC for it).

## What to implement

Re-verify each behaviour on main first (it may have changed or been removed since wave 30): find the code and the test that verifies it today, by `ast`/import, not text search. Then add each still-true behaviour as an AC under the right FR, in the registry's existing format, naming the test that verifies it. A behaviour that no longer holds, or whose test no longer exists, is not added: say so in one line each.

## Acceptance criteria

* **AC-1**: each listed behaviour is either an AC in requirements.yml naming an existing test node that verifies it, or dropped with one line saying why.
* **AC-2**: every named test node exists and passes (run each by node id, report skips; a skip is not a pass), and is the test that actually asserts the behaviour (attribute by the enclosing test, not by file).
* **AC-3**: the registry's own checks stay green: tests/test_check_ref_resolution.py, the forge validator (meta/architecture validators, forge_1 copy), and tests/test_kanban_review_record.py. Frozen census pins that move are re-derived against a def/class line, never pasted from a printed number.
* **AC-4**: no code or test changes; net test count 0.

## Guardrails

* **G-1**: an AC names as its check only a verifier that exists and passes on main today, never a planned or future one.
* **G-2**: no edits outside requirements.yml, other than this card's notes and any census pin AC-3 forces (name it).

## Worktree notes
- [Premise] Re-verified on this branch's base (main 6e452bc1) before any edit. All six IDEA-010 behaviours still hold, and each is asserted by a class that exists exactly once (an `ast` index of tests/ and src/ finds one `class` line for each). No behaviour was dropped. The five classes (55 tests) run 55 passed, 0 skipped: TestPrintSetup_InchesTrimIsReachable 9, TestBookDetail_ShowsTheStoredTrim 4, TestBookStepPages_ProseAgreesWithTheStepper 17, TestBookCreate_RefusalKeepsTypedInput 12, TestBookPages_OfferBothExportFiles 13.
- [Change] meta/architecture/requirements.yml only: 11 ACs (AC-423..AC-433), each with a dated comment naming CARD-519/IDEA-010. No statement was edited. Each FR was chosen by where trace.yml already lists the class, which the validator requires ("acceptance test ... is not listed in this covered entry's tests").
  FR-030: AC-423 inches trim reachable (form bounds and server store) and AC-424 the 12 in width still refused, both TestPrintSetup_InchesTrimIsReachable. AC-425 the stored trim shown on the book page and AC-426 "Not set" / "Cannot be read", both TestBookDetail_ShowsTheStoredTrim.
  FR-038: AC-427 step prose and breadcrumb agree with the stepper on all five step pages (TestBookStepPages_ProseAgreesWithTheStepper). AC-428 a refused /book/create keeps the typed input, escaped, with nothing stored, and AC-429 only the refused field is marked, both TestBookCreate_RefusalKeepsTypedInput.
  FR-043: AC-430 interior and cover downloads on the book page and the list, AC-431 the cover is still offered for a book with no puzzles, AC-432 a lost cover disables the button and says why, and AC-433 the route refuses a lost cover while another book's cover stays offered. All four use TestBookPages_OfferBothExportFiles.
  The first draft had 7 ACs. The forge_1 validator warned "'then' bundles several outcomes" on 4 of them (2+ " and " in `then`), so those 4 were split into 11.
- [Attribution] Each ref names the enclosing class. This registry cannot name one method inside a class (the node-id form `path::name` takes one level), so classes are the format, as on every other AC. Mutants, one at a time, against the named class only; each file was restored by `git checkout` and `git diff --stat` came back clean. The methods that went red attribute each clause:
  AC-423: M1a `min="10" max="30"` back on the width input reds test_the_inches_form_admits_the_trim x3 and test_a_page_reopened_on_an_inches_trim_admits_its_own_values ("assert False" from the browser-bounds model). M1b `_submitted_trim_cm` returning the inch figure unconverted reds test_the_server_stores_the_inches_trim x3 ("assert 200 == 302").
  AC-424: M1b also reds test_the_server_still_refuses_an_inches_trim_beyond_kdp.
  AC-425: M2a showing metadata.size reds test_shows_the_trim_print_setup_stored and test_a_new_book_shows_the_profile_it_was_created_on ("assert '8x10' == '15.24 × 22.86 cm'").
  AC-426: M2b "Not set" wording removed reds test_a_book_with_no_print_spec_says_not_set_and_links_to_print_setup. M2c the unreadable branch removed reds test_an_unreadable_stored_trim_says_so_and_links_to_print_setup.
  AC-427: M3 lede hand-written "Step 1 of 4" reds test_the_printed_step_is_the_current_one[1] ("prose says [('1', '4')] while its stepper marks step 2 of 5"). M3b breadcrumb hand-written "step 1" reds test_the_breadcrumb_names_the_page_s_own_step[1] ("assert 1 == (1 + 1)"). The "all five pages" clause is the parametrization PROSE_CHECKED = (0, 1, 2, 3, 4): ids [0]..[4] are collected.
  AC-428: M4a refusal passes submitted=None reds test_every_refusal_carries_the_submission_back x4, test_a_value_with_html_specials_is_escaped_not_injected and test_a_refusal_naming_no_field_still_carries_the_input_back ("title came back as ''"). M4c `field_title|safe` reds the escaping test.
  AC-429: M4b error_fields=frozenset() reds test_the_refused_field_alone_is_marked x4 ("assert set() == {'title'}").
  AC-430: M5a and M5b cover forms posting part=interior (detail, list) red test_offers_a_cover_download_that_submits_part_cover[detail]/[list] and test_the_cover_form_as_rendered_downloads_the_cover_file ("assert {'part': 'interior'} == {'part': 'cover'}"). M5c the detail interior button removed reds test_offers_an_interior_download[detail].
  AC-431: M5a, M5b and M5c each red test_a_book_with_no_puzzles_still_offers_its_cover.
  AC-432: M6a cover_upload_lost=False on the book page reds test_a_lost_cover_upload_disables_the_cover_button[detail] and test_the_book_page_says_why_a_lost_cover_is_unavailable. M6b lost_covers always empty on the list reds [list] of the same test and test_the_list_says_why_a_lost_cover_is_unavailable_in_visible_text.
  AC-433: M6b also reds test_one_book_s_lost_cover_leaves_another_book_s_cover_on_the_list. The route's 302 refusal is the last assert of test_a_lost_cover_upload_disables_the_cover_button. This was established by reading the assert, not by a mutant: the route was not mutated (it is FR-043's existing lost-upload rule).
- [Census] No pin moved. All five refs were already declared by trace.yml (FR-030, FR-038 and FR-043 rows), so requirements.yml only adds a second source to existing refs. Checked with the module's own helpers, `_declared_refs()`, `_fingerprint()` and `_verdicts()`, with the edit stashed and then reapplied: 598 refs, fingerprint a99ee186711e2ec8 both times (= CENSUS). falsely_alive 114, falsely_dead 17 and bookkeeping 2 are the same sets both times. tests/test_check_ref_resolution.py: 26 passed. Its 2 UserWarnings ("bookkeeping-only lost 8", "honest-dead lost 21") are on the base too.
- [Validator] forge_1 copy (~/MyProjects/forge_1/forge/skills/architect-validate/scripts/validate.py --root meta/architecture): before 0 errors / 104 warnings, after 0 errors / 104 warnings. The sorted outputs are identical.
- [Not added] TestBookFinalise_LostCoverFileIsNotPassedOffAsUploaded (tests/test_book_export_interior_cover.py) is Finalise's lost-cover handling. It dates from 2026-09-22 (commit 2d82b992), not from CARD-158/159, so it is out of this card's scope. No authority under meta/architecture declares it today (a text search finds it only in meta/profiling duration logs). Recorded here only, per the cut bar.
- [Gate] Unarmed, -o addopts= -rfs: tests/test_book_workflow_steps.py, test_book_detail_page.py, test_book_create.py (the named classes' files), test_check_ref_resolution.py, test_kanban_review_record.py, plus the registry readers test_book_page_packing_doc.py, test_grid_bound_agreement.py and test_approval_guess_gate.py. Result: 322 passed, 0 failed, 0 skipped, 3 warnings (the 2 check-ref warnings above and SQLAlchemy's MovedIn20Warning, also on the base).
- [Net tests] --collect-only: 10692 before and 10692 after, net 0. No code or test file changed (AC-4, G-2).
[Review 1/3] Score: 7.0, three gating findings, not certified. All five classes run by node id: 55 passed, 0 skipped; registry checks 97 passed; forge_1 validator 0 errors / 104 warnings on branch and main alike; AC-423..AC-433 free on main. F-001 (Important) AC-432: on the book page the test finds the words and a finalize href anywhere in the body; mutants V1 (note inside an HTML comment) and V2 (note's own link removed) stay green. F-002 (Important) AC-423: the cm-page test asserts only cm figures; mutant I1 (`min="10"` on width only on a cm-opened page, the original CARD-159 bug) stays green, and the reopened-page test covers only 8.5 x 11. F-003 (Important) AC-428: "every submitted value filled in" contradicts the asserted `values["theme"] is None` for an unknown theme; "no book stored" is asserted only for the four field refusals. F-004 (low) AC-424: the height carried back is not asserted. F-005 (low) AC-427: step 0 is read at /book/<id>/edit ("General info"), not /book/create. F-006 (info): mutant R1 (the route's lost-cover check replaced by `if False:`) reds `test_a_lost_cover_upload_disables_the_cover_button[detail]` and `[list]` with "assert 200 == 302".
- [Fix 1, 2026-11-22] UNMEASURED: CARD-518's merge gate held the full-suite lock for the whole round, so no pytest ran after these edits. requirements.yml rewording, no other file touched. AC-423: claims only the inches-opened page (the three inch trims, each stored at its cm) plus a page reopened on the stored 8.5 x 11 in trim; the cm-opened clause is gone (F-002). AC-424: "the unit and the refused 12 in width carried back" (F-004). AC-427: pages named as the stepper names them, General info at /book/<id>/edit (F-005). AC-428: field refusals only; no book stored; each value back except an unknown theme, which leaves the select with no choice; escaping kept (F-003). AC-429: the no-field refusal marks none yet carries every value back. AC-432: the book page claims only that its markup carries "no longer on disk" plus a Finalise link somewhere; the list claims a text span id cover-lost-<book id> holding its Finalise link, not "visible", because that test also reads the raw body (mutant V3 is planned to test this and has not been run) (F-001). F-006: AC-433's route clause cites the reviewer's R1, not yet reproduced here. forge_1 validator after the rewording: 0 errors / 104 warnings, sorted output identical to main. Still owed: the five classes by node id, test_check_ref_resolution.py, test_kanban_review_record.py, and mutants R1/V3 (already in /private/tmp/claude-501/card519/mutants.py).

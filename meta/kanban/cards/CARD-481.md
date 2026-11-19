# CARD-481: A mandatory rule's check names a test that exists

**Status:** review
**Priority:** P1
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/481-mandatory-check-refs
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-481
**Source:** roadmap rescore 2026-11-18, wave 2 (IDEA-004, WSJF 5.08; absorbs IDEA-214 per meta/kanban/triage-outcomes.yml); premise re-read against main on 2026-11-19.
**Idea:** IDEA-004
**Wave:** 81
**Created wave:** 81
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/requirements.yml, meta/architecture/trace.yml, tests/test_check_ref_resolution.py
**UI surface:** none
**Review score:** 9.0 (cycle 3/3 - CERTIFIED; cycles 6.0, 8.0, 9.0)
**Started:** 2026-11-19T04:15Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The constraints and invariants are the rules the code must never break, and each names the test that holds it. Several of those names resolve to no `def` or `class` anywhere. Measured on main on 2026-11-19 by a definition search over `tests/`: **CON-005** (the solver never reports a false unique solution, the one mandatory correctness property) names `PropertyTest_Solver_NeverFalsePositiveUniqueness`, while the real test is `test_never_false_positive_uniqueness` in `tests/property/test_solver_uniqueness.py`. CON-010, CON-012, CON-014 and CON-019 are in the same state. The backlog item also lists ADR-0006/R1, INV-001, INV-002, INV-008, INV-009..INV-012 and ADR-0029/R2. The validator's text search reports some of these as covered, because the names appear in prose (see `tests/test_check_ref_resolution.py`'s docstring).

## What to implement

1. Derive the population: every `test:`/`ref:`/`check:` on a `CON-*`, `INV-*` or ADR rule in `meta/architecture/**` whose name resolves to no `def`/`class` line under `tests/` (by `ast` or an anchored definition search, never a word search).
2. For each: if a test asserting that rule exists under another name, re-point the ref (and its `trace.yml` row) to it; otherwise re-type the check as `review-lens` with one sentence naming what is untested. Never write a placeholder name.
3. `tests/test_check_ref_resolution.py`'s frozen classes (`HONEST_DEAD`, `FALSELY_ALIVE`, `CENSUS`, `TRACE_TESTS`, `DEFINED` …) will move. Record each move as a repair in that file's own style, re-derived on the branch; never paste a printed count.

## Acceptance criteria

* **AC-1**: the derived population is listed in the card notes, rule by rule, with the outcome (re-pointed to X / review-lens) for each.
* **AC-2**: CON-005's ref resolves to `test_never_false_positive_uniqueness`, and a run of that test by node id collects ≥ 1 case with 0 skipped.
* **AC-3**: every re-pointed ref is checked to actually assert its rule (read, not name-matched). A test that only mentions the rule is not a resolution.
* **AC-4**: `tests/test_check_ref_resolution.py` passes on the branch with its frozen classes re-derived, and each departure is explained as a repair.
* **AC-5**: no new tests (fewer-tests rule); net test count 0.

## Guardrails

* **G-1**: AC refs on FRs are out of scope: an open FR's AC legitimately names a test that isn't written yet.
* **G-2**: no edit to `src/`; this is a registry repair.
* **G-3**: the module's rule holds: its guard must not spell a dead ref into tracked non-Markdown code (that revives it).

## Worktree notes

### Round 0 (2026-11-19) — implementation, commit 38e37f9f

**Population (AC-1), derived, not carried.** Every ref the four authorities declare
(requirements.yml, trace.yml, the ADRs — `tests/test_check_ref_resolution.py`'s own
`_declared_refs()`, 585 refs, reproducing all nine stored pins at base e32da31b),
resolved twice: the module's definition search, and an independent `ast` index of
`tests/**/*.py` that also marks whether pytest would collect the def. A ref is in
scope when one of its declaration sites is a `CON-*` check, a criterion carrying
`invariant: INV-*`, or an ADR `check:`; it is in the population when it has no
collected def. Result: **36 distinct refs**, every one with zero def/class lines by
both resolvers (none was a defined-but-uncollected `PropertyTest_` class). The
backlog's list was partly stale: INV-008, INV-009, INV-010, INV-012, ADR-0006/R1 and
ADR-0029/R2 all resolve to collected tests on main today (repaired by earlier cards),
so they are not in the population. INV-004..INV-007 and INV-013 are clean too.

Where an FR criterion named the SAME dead ref as a mandatory rule, it was fixed with
the rule (same name, same claim). FR criteria with their own dead refs (e.g. FR-042
AC-291/AC-292, FR-044 EC-037) were left alone (G-1).

| Rule | Field(s) | Old ref | Outcome | Evidence the test asserts the rule |
|---|---|---|---|---|
| CON-005 | check; FR-006 EC-001 `test:`; trace FR-006; CON-005 trace note | `PropertyTest_Solver_NeverFalsePositiveUniqueness` | re-pointed: `tests/property/test_solver_uniqueness.py::test_never_false_positive_uniqueness` | asserts solver count == brute-force oracle count for every case of a ≥-floor corpus (so never 1 when truth ≠ 1), and that a reported grid re-encodes to the clues |
| CON-010 | check; NFR-004 EC-004; trace NFR-004, CON-010 | `PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest` | re-pointed: `tests/test_web_server.py::test_every_cross_origin_or_foreign_authority_request_is_refused` | a hand-built corpus with an asserted size floor (cross-site Sec-Fetch-Site, foreign Origin, absolute-form foreign authority, odd shapes) — every row answers 400, carries no form, writes nothing |
| CON-012 | check; FR-021 EC-007; trace FR-021, CON-012 | `PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore` | re-pointed: `tests/property/test_image_fit.py::test_property_aspect_guard_accepts_exactly_those_requests_retaining_half_or_more`, `::test_property_aspect_guard_pins_both_sides_of_the_inclusive_boundary` | the real `validate_aspect_ratio` accepts iff retained ≥ 1/2 over 1500 cases (≥300 each verdict); exact-2x accepted and one pixel past refused at every supported grid shape |
| CON-014 | check; NFR-007 EC-016; trace NFR-007, CON-014 | `PropertyTest_ScoreDifficulty_IndependentOfElapsedTime` | re-pointed: `tests/property/test_difficulty_ladder.py::test_independent_of_elapsed_time`, `::test_independent_of_elapsed_time_across_the_whole_input_space` | `dataclasses.replace(elapsed_seconds=…)` over real and synthetic (incl. branching) records — score and `classify` tier identical |
| CON-019 | check; FR-030 EC-020; trace FR-030, CON-019 | `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` | re-pointed: `tests/property/test_cli_exports_byte_identity.py::test_property_cli_exports_byte_identical_whatever_the_book_geometry`, `::test_property_web_ui_exports_byte_identical_whatever_the_book_geometry` | CLI and web-form PNG/SVG/PDF digests equal the pre-geometry golden over the corpus |
| INV-001 | FR-005 AC-014; trace FR-005 | `TestComputeClues_MatchesGridExactly` | re-pointed: `tests/test_clues.py::test_matches_grid_exactly` | every row/column clue equals an independently written reference encoder's output |
| INV-002 | FR-011 AC-030; trace FR-011 | `TestExport_RejectsUnverifiedPuzzle` | re-pointed: `test_export_rejects_an_unverified_puzzle` (defined in `tests/test_export_image.py` — the AC-030 PNG/SVG instance — and `tests/test_export_json.py`) | unjudged puzzle → `ExportRejected("not ready for export")`, nothing written |
| INV-002 | FR-016 AC-048; trace FR-016 | `TestExport_RejectsUnverifiedPuzzleForPDF` | re-pointed: `tests/test_export_pdf.py::test_export_rejects_an_unverified_puzzle_for_pdf` | same gate for PDF, nothing written |
| INV-002 | FR-025 AC-112; trace FR-025 | `TestRecovery_RecoveredGridIsReverifiedBySolver` | re-pointed: `tests/test_orchestrator.py::test_a_recovered_grid_is_reverified_by_the_solver` | accepted repaired grid: last solve was on its own clues, count 1, ready_for_export, re-solve gives 1 |
| INV-003 | FR-007 AC-019; trace FR-007 | `TestRegenerate_StopsAtMaxRetryBound` | re-pointed: `tests/test_orchestrator.py::test_regenerate_stops_at_max_retry_bound` | exactly MAX_REGENERATE_ATTEMPTS candidates, then `GenerationAbandoned` naming the bound |
| INV-003 | FR-010 AC-027; trace FR-010 | `TestResample_StopsAtMaxRetryBound` | re-pointed: `tests/test_resample.py::test_stops_at_max_retry_bound` | resample abandons at MAX_RESAMPLE_ATTEMPTS, never past it |
| INV-003 | FR-013 AC-035; trace FR-013 | `TestNudge_ReportsFailureAtCap` | re-pointed: `tests/test_nudge.py::test_nudge_reports_failure_at_cap` | abandons with the nudge bound in the message |
| INV-003 | NFR-002 AC-039; trace NFR-002 | `TestRetryLoop_BoundedIterations` | re-pointed: `tests/test_orchestrator.py::test_retry_loop_bounded_iterations` | `run_bounded` stops after exactly `bound` attempts, counter exhausted |
| INV-003, ADR-0024/R2 | FR-025 AC-113; ADR-0024/R2 check; trace FR-025 | `TestRecovery_RepairAttemptsCountAgainstRetryBound` | re-pointed: `tests/test_orchestrator.py::test_repair_attempts_count_against_the_retry_bound` | redraws + repairs == attempts == MAX_REGENERATE_ATTEMPTS, then `GenerationAbandoned` |
| INV-003, ADR-0024/R1 | FR-025 EC-013; ADR-0024/R1 check; trace FR-025 | `PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound` | EC-013 → `tests/property/test_recovery_bound.py::test_accepted_grids_have_real_verdicts_within_one_bound`; ADR-0024/R1 → that plus `tests/test_orchestrator.py::test_a_recovered_grid_is_reverified_by_the_solver` | every accepted grid re-solved from its own clues = 1; attempts ≤ bound; one solve per attempt |
| ADR-0024/R3 | check; FR-025 AC-114; trace FR-025 | `TestRecovery_RepairKeepsFilledCountExact` | AC-114 → `tests/test_orchestrator.py::test_repair_keeps_the_filled_count_exact`; R3 → that plus `::test_repair_flips_one_pair_inside_the_undecided_mask`, `::test_repair_leaves_every_cell_outside_the_mask_untouched` | filled count 160 after each of five repairs; exactly one filled→empty and one empty→filled inside the mask; no cell outside it moves |
| ADR-0022/R2 | check | `TestValidateExtent_RejectsSideAboveThirty` | re-pointed: `tests/test_sourcing_random.py::test_validate_extent_rejects_side_above_thirty`, `tests/property/test_grid_dimensions.py::test_every_source_mode_rejects_every_side_outside_ten_to_thirty` | pure `validate_extent` rejects 31 on either side and accepts 30x12; every mode raises the shared rule's error for ≥500 out-of-range pairs |
| ADR-0022/R3 | check | `TestFitImage_RefusesRatioMismatchBeyondTwice` | re-pointed: `tests/test_sourcing_image.py::test_fit_image_refuses_a_ratio_mismatch_beyond_twice`, `tests/property/test_image_fit.py::test_property_aspect_guard_judges_the_ink_box_before_any_crop_is_applied` | 3:1 into 20x20 refused, into 30x10 converts; ink box judged before any crop |
| ADR-0022/R4 | check | `PropertyTest_BareSize_DerivesShorterSideFromSourceShape` | re-pointed: `tests/property/test_grid_dimensions.py::test_a_bare_size_derives_the_shorter_side_from_the_source_shape`, `::test_the_derived_short_side_is_the_rounded_ratio_clamped_at_min_or_refused` | every mode, every N: grid = derived extent, long side N; refusals name the smallest working `--size` (≥500 refused, ≥500 clamped) |
| ADR-0023/R2 | check | `TestExport_RejectsSupersededSchemaVersion` | re-pointed: `test_a_version_1_file_is_refused_and_not_migrated` (defined in both `tests/test_export_json.py` and `tests/test_export_csv.py`, the rule's two decoders) | a real v1 document raises `ValueError` naming version 1 and the build's version |
| ADR-0026/R1 | check; FR-027 AC-126; trace FR-027 | `TestBinarize_ExactlyHalfCoverageIsFilled` | re-pointed: `tests/test_sourcing_image.py::test_binarize_exactly_half_coverage_is_filled` | grey 127 fills, 128 does not (the inclusive 50% boundary) |
| ADR-0027/R1 | check; FR-028 AC-128; trace FR-028 | `TestGenerateRandom_RefusesDensityZeroAndHundred` | re-pointed: `tests/test_sourcing_random.py::test_generate_random_refuses_density_zero_and_hundred` | 0 and 100 → `InvalidDensity` naming MIN/MAX_DENSITY |
| ADR-0027/R2 | check; FR-028 AC-130; trace FR-028 | `TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam` | re-pointed: `tests/test_sourcing_random.py::test_the_degenerate_density_verdict_is_made_at_the_validate_density_seam` | with `validate_density` stubbed, density 0 produces a grid — nothing downstream judges density |
| ADR-0029/R1 | check; FR-026 AC-119; trace FR-026 | `TestScoreDifficulty_DeeperLineReasoningScoresHigher` | AC-119 → `tests/test_difficulty.py::test_deeper_line_reasoning_scores_higher`; R1 → that plus `tests/property/test_difficulty_ladder.py::test_monotone_in_rung_order` | deeper rung scores strictly higher; over a seeded corpus the score orders exactly as an independent (rung, share) key |
| ADR-0029/R3 | check | `PropertyTest_ScoreDifficulty_IndependentOfElapsedTime` | re-pointed: the two CON-014 tests above | clock never moves score or tier (the rule's no-size/density clause is NOT asserted by these; its own trailing comment points at EC-018 for the strategies list) |
| ADR-0029/R5 | check | `PropertyTest_SolveStrategies_RungsInvariantUnderTransposition` | re-pointed: `tests/property/test_solver_witnesses.py::test_rungs_are_invariant_under_transposition` | per-rung counts, rung list, score and the per-cell tag map equal their transposes |
| ADR-0029/R6 | check | `TestScoreDifficulty_BranchingSolvePinsTheCeiling` | re-pointed: `tests/test_difficulty.py::test_a_branching_solve_pins_the_ceiling_and_outranks_every_ladder_score` | any branch_nodes > 0 → SCORE_MAX, ≥ full-share probe score, tier HARD |
| ADR-0031/R1 | check | `TestTiers_ThreeBandsAndNoFourthTier` | re-pointed: `tests/test_difficulty_tiers.py::test_tiers_three_bands_and_no_fourth_tier` | Tier == [easy, medium, hard], each with a band, no GUESS, `classify(score)` unary |
| ADR-0031/R2 | check; FR-026 AC-174; trace FR-026 | `TestTiers_BranchingIsAStrategyNotATier` | re-pointed: `tests/test_difficulty_tiers.py::test_tiers_branching_is_a_strategy_not_a_tier` | branching record → `STRATEGY_GUESS` in strategies, tier = classify(score) |
| ADR-0031/R3 | check | `TestTiers_LegacyGuessRowReadsAsHard` | re-pointed: `tests/test_difficulty_tiers.py::test_tiers_legacy_guess_row_reads_as_hard` | stored "guess" (any case/space) reads as Tier.HARD |
| INV-011 | FR-042 AC-261, AC-263, AC-264, AC-266, AC-270, AC-290, AC-293 `test:`; trace FR-042 | `TestBookAnswerKey_SixUpInPuzzleNumberOrder`, `…LargeAnswerThatWouldOverfillStartsNewPage`, `…PageBecomesFourUpOnceItHoldsAnswerAbove20`, `…LongestSideTwentyStaysSixUp`, `…DefaultPlanTakesThirtyPages`, `…EachLevelStartsNewAnswerPage`, `…DefaultPlanThreeLevelsTakesThirtyOnePages` | **unverified (no `test:`)** — the AC-field form of review-lens, per the CARD-316 precedent at AC-378 (the validator ignores an AC's `kind:`); a comment at each says why | **SUPERSEDED by fix round 1 — this reason was wrong** (review F-002): packing came back with CARD-202/CARD-232, and `pack_answer_pages` is called nowhere in `src`. See Round 1 for the per-criterion outcome (6 dropped, AC-290 re-pointed) |

That is 36 dead names: 29 re-pointed, 7 dropped. *(Corrected in fix round 1, F-007: the
re-pointed refs named 38 distinct tests — the 36 new to the census plus two already declared
elsewhere — i.e. 40 node ids; my round-0 collect run covered only the 36 new ones' 38 node ids,
223 tests. Round 1's figures supersede both.)*

**Validator of record** (`~/MyProjects/forge_1/.../architect-validate/scripts/validate.py
--root meta/architecture`, captured `> file 2>&1`): before **0 error(s), 100 warning(s)**;
after **0 error(s), 106 warning(s)** (round 0; round 1 below). WARN sets diffed with `comm`: OUT 1 — the INV-011
dead-ref warning (it bundled six of the seven dropped names; the seventh read alive on a
test docstring); IN 7 — "acceptance criterion has no 'test'" for the seven FR-042 criteria.
Dead-ref warning delta: **−1**. The 29 re-pointed names raised no warning before (all were
falsely alive on prose), so their repair is invisible to the validator's count.

**Frozen classes (AC-4)** — base e32da31b reproduces all nine pins; branch sets diffed:
FALSELY_ALIVE 144→114 (OUT 30 withdrawn, IN 0); HONEST_DEAD 17→11 (OUT 6 withdrawn,
IN 0); CENSUS 585→585 (OUT 36, IN 36, digest moves); TRACE_TESTS 514→510 (OUT 28, IN 24);
DEFINED 424→460 (OUT 0, IN 36). Unmoved, empty symmetric difference: BOOKKEEPING_ONLY,
FALSELY_DEAD, RESOLVED_FROM_AFAR, SAME_FILE_PROSE. Each move is recorded in the module
by site, no ref named (G-3). Side effect recorded there too: six of
BOOKKEEPING_ONLY_MEMBERS' stored digests are the dropped INV-011 refs, so that class now
emits the documented withdrawal UserWarning (base: none). The G-2 self-check caught the
module's own docstring spelling ADR-0022/R4's new ref whole; it is truncated now.

**Tests run** (all `-o addopts= -q -rfs`, from the worktree root, main venv):
`tests/test_check_ref_resolution.py` 26 passed (2 UserWarnings, see above);
CON-005's node id 1 passed; all 38 entrant node ids 223 passed, 0 skipped;
the registry readers (`test_approval_guess_gate.py`/`test_public_player.py`/
`test_public_player_pages.py` registry cells, `test_grid_bound_agreement.py`,
`test_nfr001_generation_time.py`, `test_impact_set.py`, `test_kanban_review_record.py`)
288 passed, 1 xfailed (the pre-existing AC-037 p95 xfail). Net test count 0; no `src/` edit.

**Judgment calls to check:** (1) several rules now name two or three tests where the old
logical name covered only part of the statement (ADR-0022/R2–R4, ADR-0024/R1, R3,
ADR-0029/R1); (2) ADR-0029/R3 and ADR-0026/R1 are still only partly asserted (no-size/
density term; resize-before-threshold order) — re-pointed, not re-typed, because the
named test does assert the clause the old name stood for; (3) INV-011's criteria were
dropped rather than re-pointed at EC-030's property test, because they describe a book PDF
the code no longer produces. *(Superseded by fix round 1, F-002.)*

### Fix round 1 (2026-11-19) — review cycle 1 (6/10), commit 0eaa5dc0

**Per finding**
- **F-001 (gating) — fixed.** Verified first: under the validator's own reader
  (`extract_rules_yaml` + YAML safe load, then `split_check_ref`) an unquoted
  `{kind: test, ref: a, b}` yields `ref: a` and a stray key `b`. Census of the class across the
  whole ADR set: exactly 7 unquoted multi-name check refs, all mine (ADR-0022/R2–R4,
  ADR-0024/R1, R3, ADR-0029/R1, R3); none pre-existing. All multi-name refs now quoted as
  ADR-0039/R4 and ADR-0041 do. Measured with scratch `readers.py`, which compares the
  validator's reader with this module's `_ADR_CHECK` + `_split` per rule: **49 ADR test checks,
  0 disagreements, 0 stray keys**. Mutation: un-quoting ADR-0022/R4 → `DIFF ADR-0022/R4
  validator: [first name] stray: [second name]`, 1 disagreement; restored with
  `git checkout --`, back to 0.
- **F-002 (gating) — fixed.** I read `plan_small_answer_pages` (book_answer_key.py; the only
  packing call in src, book_pdf_generator.py) and ran each criterion's own book through it:

  | AC | Its claim | Today's plan (extent-only walk) | Outcome |
  |---|---|---|---|
  | AC-261 | 12 → 2 pages of 6 | 3 pages: (1-4) (5-8) (9-12) | false → stays dropped |
  | AC-263 | 1-5 then answer 6 (25x25) starts a page | (1-4) (5,6) | false → stays dropped |
  | AC-264 | (1-4) on a 4-up page, 5 next, because a >20 answer forces 4-up | (1-4) (5) | outcome true but by a different rule (every page is 2x2); no test asserts it → stays dropped, comment says so |
  | AC-266 | one 6-up page | (1-4) (5,6) | false → stays dropped |
  | AC-270 | 30 answer pages | 38 | false → stays dropped |
  | AC-290 | (1-4) (5-7); medium starts a new page "although the first had room for 2 more" | (1-4) (5-7) | **re-pointed** to `TestBookSolvedAnswerKey_TierBoundaryClosesAPackedPageEarly` (tests/test_book_solved_answer_key.py), which asserts the level rule (3 easy + 2 medium → (1-3), (4-5), no page holds two levels); the "room for 2 more" clause is stale (the 2x2 page is full) and the comment says so |
  | AC-293 | 31 answer pages | 15 + 15 + 8 = 38 | false → stays dropped |

  The degrade pass only splits 4-up pages, so it can only add pages to the 38s. Each comment
  now describes today's key (`plan_small_answer_pages`, 2x2, one level per page, degrade to
  2-up, then to one answer per page — corrected in fix round 2). Mutation: deleting the level-boundary `flush()` in `plan_small_answer_pages` → the
  re-pointed class 2 failed; restored with `git checkout --`, 2 passed.
  **EC-030 correction:** `PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook` exercises
  `pack_answer_pages`, which nothing in `src` calls any more (docstring mentions and
  `__all__` only), so INV-011's EC-030 property checks retired code, not the product.
- **F-003 — fixed.** R1's ref gains `test_a_line_solvable_corpus_spans_all_three_bands`
  (asserts ≥1 line-solvable puzzle in each of Easy/Medium/Hard over a ≥floor corpus). R1's
  comment names it; R3's comment names the real class
  `TestPropertySolveStrategies_PureFunctionOfCluesAndPreservedEndToEnd`, and R3's ref gains
  its clock arm `test_a_fifty_times_slower_clock_changes_no_list`.
- **F-004 — fixed.** Read the test: the verdict is checked against the ink box's ratio on
  sources where the file ratio disagrees in both directions, and for a refusal every
  crop/resize/convert counter stays zero. Added to CON-012's check and EC-007's `test:`
  (and FR-021's trace row; CON-012's row already had it).
- **F-005 — no test exists; listed below.** No test runs the solver, scorer, export or
  batch on a degenerate-density grid. (The web test `test_the_adapter_hands_a_degenerate_density_inward_untouched`
  asserts the adapter half only.)
- **F-006 — fixed where a test exists.** Added: ADR-0022/R2 `test_the_cli_enforces_no_part_of_the_range_itself`
  (every extent parses at the adapter unchanged); ADR-0022/R3
  `test_property_fit_image_crop_box_is_the_largest_centred_rectangle_of_target_aspect`,
  `test_property_fit_image_never_stretches_and_never_pads`; ADR-0024/R3
  `test_the_disagreement_set_is_preferred_when_it_holds_a_pair`,
  `test_falls_back_to_the_undecided_mask_when_the_disagreement_set_has_no_pair`; ADR-0029/R5
  `test_a_clue_set_that_is_not_a_puzzle_carries_no_rung_attribution` (count ≠ 1 → all tags
  None, empty rung list, zero histogram). ADR-0026/R1 also gains
  `test_the_threshold_is_inclusive_half_coverage_on_the_resized_image` and
  `test_the_threshold_never_diffuses_error_between_neighbours`. AC-035: I added the sibling
  to the `test:` field and the validator then warned (its covered-trace check reads an AC's
  `test:` string unsplit: "acceptance test 'a, b' … not listed"). So AC-035 keeps one name
  with a comment, and the sibling is listed on FR-013's trace row instead.
- **F-007 — fixed.** Figures re-measured below.
- **F-008 — no change.** The standing UserWarning ("bookkeeping-only lost 6") clears when
  someone re-derives `BOOKKEEPING_ONLY_MEMBERS` from the current class, dropping the six
  withdrawn digests. That is a deliberate one-line edit to that frozenset, recorded as a
  repair in its note. The module's own policy is not to trim snapshots, which is why I
  have not done it here.

**For the owner — FR-042 / INV-011 clauses that no longer match the product** (not
rewritten here; amending them is the owner's / architect's call, and no card owns it):
- *"6 answers a page while every answer is ≤ 20 on its longest side, 4 once one is longer"*
  (FR-042, and INV-011's capacity clause): today every answer up to MAX_SIZE packs into a 2x2
  page; a page whose four tiles miss the minimum cell degrades to two 2-up pages, and if a
  pair cannot fit either, to one answer per full page (`_degrade_infeasible_packed_pages`)
  (`PACKED_MAX_WIDTH/HEIGHT = MAX_SIZE`, `PackedAnswerPage`; test
  `test_six_qualifying_easy_answers_pack_as_four_then_two`). INV-011's "at most 6 / at most 4"
  bounds are still *satisfied* (≤ 4), but they no longer describe the rule.
- *"An answer is the filled grid only — no row or column clues"* (FR-042): packed slots show
  clues (`TestBookSolvedAnswerKey_PackedSlotsStillShowClues`).
- *"each level's first answer page carries the level's name as a heading"* (FR-042):
  CARD-198's `TestBookSolvedAnswerKey_LevelVisibleViaPerPageBandNoSeparateHeading` asserts
  no heading page; the level shows on the per-page band.
- The page-count example (30 / 31 answer pages): the plan gives 38 for both books.
- EC-030's property test checks `pack_answer_pages`, which is off the product path.
- Unmeasured by me: the tile-geometry formula and the 5 mm answer-cell cap.
- **Still true today:** every answer exactly once, in puzzle-number order; no page holds two
  levels; a SOLUTIONS divider precedes the key when the book prints dividers.

**Validator of record** after round 1: **0 error(s), 105 warning(s)** (main: 0 / 100).
WARN sets diffed with `comm` against main: OUT 1 (the INV-011 dead-ref warning); IN 6
("acceptance criterion has no 'test'" for AC-261, 263, 264, 266, 270, 293). Against
round 0: OUT 1 (AC-290's no-test warning).

**Frozen classes**, re-derived against round 0's tip and diffed as sets: CENSUS 585→597
(OUT 0, IN 12), TRACE_TESTS 510→512 (OUT 0, IN 2), DEFINED 460→472 (OUT 0, IN 12). The other
six are unmoved (empty symmetric difference). Quoting moved none of them, because the
module's regex already read every name. Recorded in the module.

**Re-pointed population, re-measured:** 50 distinct test names across all re-pointed refs
(48 new to the census plus 2 already declared on main), 52 node ids built by `ast`
(two names are defined in two modules; one is a method addressed through its class) →
`--collect-only` **240 tests collected**; run: **240 passed, 0 skipped** (1 pre-existing
SQLAlchemy deprecation warning).

**Tests run** (all `-o addopts= -q -rfs`): `tests/test_check_ref_resolution.py` 26 passed,
2 UserWarnings; CON-005 node id + the registry readers (as round 0, minus
test_kanban_review_record) 218 passed, 1 xfailed (AC-037, pre-existing);
`tests/test_kanban_review_record.py` after this edit: 71 passed.

**Judgment calls, updated** (clauses that no named test asserts):
1. ADR-0027/R2 and AC-130: the downstream half (no later stage rejects on density).
2. ADR-0029/R3: "no size or density term enters the score" (tested only indirectly by
   `test_monotone_in_rung_order`'s mixed extents).
3. ADR-0026/R1: "after the LANCZOS resize, never on the source pixels". The property tests
   make the resize the identity, so they do not tell the two orders apart.
4. ADR-0024/R3: covered now. ADR-0022/R2, R3 and ADR-0029/R5: covered now.
5. AC-290 is re-pointed to a test that asserts its level rule on a different book; its
   "room for 2 more" clause is stale.
6. AC-264's outcome happens to hold today, but I dropped its `test:` because no test asserts
   that example and its stated rule is gone.

### Fix round 2 (2026-11-19) — review cycle 2 (8/10, certified)

- **F2-001 — fixed (commit e9cc60cb).** I added one assertion inside
  `test_the_derivation_reads_all_four_authorities`, the cell about reading the authorities
  completely. No new test function; collection is still 26. For every ADR check of kind
  `test`, it splits the flow mapping into entries the way YAML does (a plain scalar in flow
  context cannot hold a comma, so it splits on commas outside quotes). It then requires the
  keys to be exactly `kind` and `ref`, and the names to equal what `_ADR_CHECK` + `_split`
  read. **Reader choice:** stdlib, not the validator's reader or `yaml.safe_load`. forge_1
  lives outside the repo, and neither PyYAML nor ruamel is a declared dependency: both are in
  the venv with "Required-by: (none)". Importing one would break collection on a bare
  `pip install -e '.[dev]'` and step outside ADR-0006/R1's baseline. Scratch `readers.py`
  (the validator's real reader) still reports 0 disagreements on this tree.
  **Mutations** (both restored with `git checkout --`):
  - un-quoting ADR-0029/R5 → `1 failed, 25 passed`, and the failure is this cell;
  - the same un-quote with the assertion deleted → `26 passed`. So the assertion is what
    catches it.
- **F2-002 — fixed.** The six drop comments now name both fallbacks: two 2-up pages, then
  one answer per full page. AC-264's "OUTCOME still holds" now carries the extent-only-plan
  caveat. The two round-1 note lines that said "degrade to 2-up" are corrected above.
- **F2-003 — added to the owner list:** `qualifies_for_packing`'s docstring says
  "width<=15 and height<=20", and so do the module comment at book_answer_key.py:371 and
  the call-site comment at book_pdf_generator.py:5851. But `PACKED_MAX_WIDTH` and
  `PACKED_MAX_HEIGHT` are `MAX_SIZE` since the owner's 2026-11-09 decision. That is stale
  prose in `src/`; it was not edited here (G-2).

**Figures:** `tests/test_check_ref_resolution.py` 26 passed (26 collected, 2 documented
UserWarnings); validator of record 0 error(s), 105 warning(s), unchanged from fix round 1;
`tests/test_kanban_review_record.py` 71 passed.

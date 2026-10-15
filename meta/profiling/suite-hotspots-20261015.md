# Suite hotspots, 2026-10-15

Derived from `meta/profiling/suite-durations-20261015.txt`
(sha256 `7d204cf956580d9f36a223ee196a3d0b739fe5124a5af50265938630a37e760e`)
by `meta/profiling/rank_durations.py`. Every figure below is that script's
output; nothing here was counted by hand. To reproduce:

```bash
./.venv/bin/python meta/profiling/rank_durations.py \
    meta/profiling/suite-durations-20261015.txt
```

**The run.** Commit `56c716e` (worktree byte-identical to main), solo on the
host, 930.81 s wall, 7073 passed / 9 skipped / 0 failed, 7082 tests timed.
920.63 s (98.9 %) of the wall clock is attributed to individual tests; only
10.18 s is collection and imports. Shares below are of attributed time unless
stated otherwise.

---

## The answer to the card's question

The card offered two hypotheses. **The data supports neither as the
explanation.** Between the two, the render hypothesis is the stronger, but a
third family the card did not consider is larger than both combined.

| group | time | share | tests | ms/test |
|---|---|---|---|---|
| **Chromium-driven admin player tests** (`tests/test_puzzle_solver_*.py`, 12 files) | **366.19 s** | **39.78 %** | 422 | **868** |
| render-heavy files (the 29-path frozen set) | 195.42 s | 21.23 % | 1079 | 181 |
| `tests/property/*` (the seeded corpora) | 140.19 s | 15.23 % | 184 | 762 |
| — of which counted in *both* rows above | 70.75 s | 7.68 % | | |
| render ∪ property (the card's two hypotheses together) | 264.86 s | 28.77 % | | |
| admin-local script tests (`test_start_admin_local`, `test_run_admin_tests`, `test_setup_admin_local`) | 117.16 s | 12.73 % | 83 | 1412 |

Derived, not hand-counted — this is `rank_durations.py`'s own
cost-families block, quoted verbatim:

```
(the deciding table)

family                                   total   share  tests  ms/test
browser family (Chromium)              366.19s  39.78%    422      868
render-heavy frozen set                195.42s  21.23%   1079      181
property corpora                       140.19s  15.23%    184      762
property AND render                     70.75s   7.68%     11     6432
property OR render                     264.86s  28.77%   1252      212
admin-local script trio                117.16s  12.73%     83     1412
everything but the browser family      554.44s  60.22%   6660       83
```

- **The render hypothesis is real but minority**: 21.23 % of attributed time,
  not the bulk. It is the larger of the two the card named.
- **The corpus hypothesis is the weaker**: `tests/property/*` is 15.23 %, and
  more than half of that (70.75 s) is *also* render-heavy — the four tests in
  `tests/property/test_book_pdf_geometry.py` alone are 48.66 s. Property tests
  that are not render-heavy come to 69.44 s, 7.5 %.
- **Together the two hypotheses account for 28.77 %.** The browser family
  alone accounts for 39.78 %.

### Why the cost per test doubled

| | tests | wall | ms/test |
|---|---|---|---|
| wave 30 (2026-10-03T02:49Z) | 5858 | 398 s | 68 |
| this run (2026-10-15) | 7082 | 931 s | 131 |
| growth | +1224 | **+533 s** | +63 |

The browser family holds 366.19 s — **69 % of the entire +533 s** — while
being only 34 % of the new tests. It did not exist at wave 30: every one of
its twelve files was first committed between 2026-10-03T08:32Z and
2026-10-08T07:28Z, i.e. *after* the wave-30 run.

Split the current suite in two and the doubling disappears:

| | time | share | tests | ms/test |
|---|---|---|---|---|
| browser family | 366.19 s | 39.78 % | 422 | **868** |
| everything else | 554.44 s | 60.22 % | 6660 | **83** |

**A browser test costs 10.4× a non-browser test.** The non-browser suite sits
at 83 ms/test against wave 30's whole-suite 68 ms/test — it has barely slowed
down. The headline "the marginal test costs 5× the historical average" is not
a property of the marginal test in general; it is one family of 422 tests at
~0.87 s each.

### Setup, call and teardown are not the same problem

| phase | time | share |
|---|---|---|
| setup | 89.07 s | 9.67 % |
| call | 687.19 s | 74.64 % |
| teardown | 144.37 s | 15.68 % |

**96 % of all teardown time in the suite (137.97 s of 144.37 s) belongs to the
browser family** — roughly 0.33 s per test, no single test above 0.52 s. This
is browser-page teardown, paid once per test and invisible in any "slowest
tests" list. It is the clearest single lever on the board: it is diffuse
within the family, so it is not fixed by rewriting any one test, only by
changing how often a page is torn down.

By contrast the render-heavy set spends 176.82 s of its 195.42 s in `call` and
0.03 s in teardown; property tests are 136.46 s call, 0.00 s teardown. Those
are test-body costs.

### No single test is the problem

The slowest test is 30.94 s, 3.36 % of the run. The top 10 are 16.4 %, the top
50 are 32.1 %, and 6057 tests finish under 0.1 s and together hold 7.4 %.
There is no test to delete that materially changes the number.

### What this means for CARD-218/219/220

1. The largest prize by far is the browser family — 39.8 %, and 96 % of the
   suite's teardown. Session- or module-scoped browser pages, or collapsing
   per-interaction tests into fewer longer ones, is where the seconds are.
2. The render hypothesis is worth acting on second (21.2 %), and within it the
   four `tests/property/test_book_pdf_geometry.py` tests (48.66 s, 5.3 % in
   *four* tests) are the densest target in the suite.
3. The corpus hypothesis is largely a restatement of the render one and
   should not be pursued as a separate line of work.
4. The admin-local script trio is 12.7 % in 83 tests (1.41 s each) and is
   pure subprocess spawning — a cheap, self-contained fourth target.

---

## Caveats

- **Run-to-run variance is itself a finding.** The two cleanest prior gates on
  this host, hours apart on near-identical suites, were 1123 s (CARD-212) and
  939 s (CARD-221) — a 19 % spread. This run's 931 s sits at the fast end of
  that band. Treat any single-run difference under ~20 % as noise; the shares
  above are far more stable than the absolute seconds.
- **A system sweep overlapped this run** (see the artefact header): between
  roughly 05:24Z and 05:28Z a macOS management scan and a Spotlight re-index
  pushed the 1-minute load average to ~140 and cut pytest's CPU share from
  76 % to 25 %. No competing *suite* ran at any point.

  **The exposure runs toward the winner, not away from it.** The render set is
  in-process CPU work (176.82 s of `call`, 0.03 s of teardown); the browser
  family is the wait-bound one (137.97 s of teardown, blocked on another
  process). A CPU-starving sweep inflates a wait-bound measurement more than a
  CPU-bound one, so it inflates the family that won. That is the right way
  round to worry about it, and the conclusion survives on two measurements:

  - **A magnitude bound.** Roughly four minutes at 25 % rather than 76 % of a
    core is at most ~161 s of excess, spread across the *whole* suite. For the
    browser family to fall behind the render set it would have to shed
    **170.8 s** (366.19 → 195.42). Charging every second of the sweep's excess
    to that one family — which nothing supports — still leaves it ahead.
  - **The per-test teardown distribution shows no contention spike.** Across
    all 422 browser tests, teardown is mean 0.327 s, median 0.370 s, stdev
    0.144 s, max 0.520 s; per-file means span only 0.198–0.413 s. The
    histogram is bimodal — `{0.0: 41, 0.1: 22, 0.2: 37, 0.3: 81, 0.4: 141,
    0.5: 100}` — with a 41-test cluster near zero and the main mass at
    0.3–0.5 s. The load-bearing half is that main mass: it is tightly packed
    and **has no tail at all**, stopping dead at 0.520 s. A four-minute stall
    would have left a visible cluster of outliers among whichever tests ran
    through it, and a bounded maximum is precisely what rules that out. So
    the ~0.33 s per test is structural — the price of tearing down a browser
    page — not an artefact of the sweep. (The near-zero cluster is the
    opposite of a contention signal: those are tests that tear nothing down.)
- **Phase attribution is near-total** (98.9 %), so these shares are not hiding
  in unmeasured session fixtures.
- The card estimated "19 render-heavy files"; the grep that defines the set
  finds 29 paths (27 test modules plus 2 helpers that carry no tests). The
  larger set is the one measured here, so 21.23 % is if anything generous to
  the render hypothesis.
- **The browser family is defined conservatively.** It is the twelve
  `tests/test_puzzle_solver_*.py` files. Three further files drive the same
  `browser_page` fixture — `test_books_list_mobile.py` (4.71 s),
  `test_book_finalise_guide_preview_layout.py` (2.78 s) and
  `test_book_setup_print_mobile.py` (1.62 s) — and counting them takes the
  family to 375.30 s, **40.77 %**. The headline 39.78 % is the floor, and the
  margin over the render set is wider than stated, not narrower.

---

## Ranking 1 — the 50 slowest tests

```
   #      total      setup       call   teardown  test
   1    30.940s     0.060s    30.810s     0.070s  tests/test_puzzle_solver_maybe.py::TestSolverMaybe_BoardDoesNotMoveOnSolveAtAnyWidth::test_sweep[chromium]
   2    19.460s     0.000s    19.460s     0.000s  tests/property/test_book_pdf_geometry.py::test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_pdf_pages
   3    19.370s     0.000s    19.370s     0.000s  tests/property/test_book_pdf_geometry.py::test_PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity_pdf_pages
   4    17.480s     0.020s    17.460s     0.000s  tests/property/test_book_export_interior.py::test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage
   5    14.360s     0.000s    14.360s     0.000s  tests/test_start_admin_local.py::test_the_decision_over_an_enumerated_corpus_of_url_shapes
   6    11.860s     0.000s    11.860s     0.000s  tests/property/test_difficulty_calibration.py::test_medium_is_reachable_on_a_seeded_corpus
   7    10.360s     0.000s    10.360s     0.000s  tests/test_run_admin_tests.py::TestRunAdminTests_KeepsItsArguments::test_each_test_type_and_option_reaches_pytest
   8     9.860s     0.000s     9.860s     0.000s  tests/test_setup_admin_local.py::TestSetupAdminLocal_ChecksTheTargetDatabase::test_the_decision_over_a_pairwise_corpus_of_url_shapes
   9     8.800s     0.000s     8.800s     0.000s  tests/property/test_book_pdf_geometry.py::test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_pdf_pages
  10     8.530s     0.000s     8.530s     0.000s  tests/property/test_cli_exports_byte_identity.py::test_property_cli_exports_byte_identical_whatever_the_book_geometry
  11     8.400s     0.000s     8.400s     0.000s  tests/test_run_admin_tests.py::TestRunAdminTests_ChecksTheTargetDatabase::test_the_decision_over_a_pairwise_corpus_of_url_shapes
  12     7.420s     0.000s     7.420s     0.000s  tests/test_book_pdf_memory.py::TestBookPdfMemory_RealBookExportsUnderTheCap::test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under
  13     7.180s     0.000s     7.180s     0.000s  tests/property/test_nudge_mask.py::test_flipped_cells_come_from_the_solver_and_nest
  14     6.580s     0.000s     6.580s     0.000s  tests/test_sourcing_image.py::test_binarize_threshold_corpus_needs_no_more_nudges_than_dither
  15     5.960s     0.000s     5.960s     0.000s  tests/test_book_guide_page.py::TestGuidePage_IsTwoPages::test_the_exported_interior_opens_with_both_guide_pages_then_the_first_puzzle_or_divider
  16     5.940s     5.410s     0.530s     0.000s  tests/test_book_pdf_ink_mode.py::TestBookInk_InkPositionsDoNotDependOnTheMode::test_the_corpus_is_the_size_it_claims_and_varies
  17     5.340s     0.090s     4.730s     0.520s  tests/test_puzzle_solver_resume.py::test_PropertyTest_SolverResume_SaveAndRestoreRoundTrip
  18     4.820s     4.820s     0.000s     0.000s  tests/test_book_pdf_memory.py::TestBookPdfMemory_PeakDoesNotGrowWithPageCount::test_a_big_books_peak_is_a_small_books_peak
  19     4.710s     0.000s     4.710s     0.000s  tests/test_book_guide_page.py::TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyLegend::test_the_difficulty_legend_carries_its_three_labels_and_no_sentences
  20     3.900s     0.000s     3.900s     0.000s  tests/test_book_pdf_band.py::test_PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle
  21     3.860s     0.100s     3.300s     0.460s  tests/test_puzzle_solver_zoom.py::TestSolverZoom_SurvivesADoubledRedraw::test_a_burst_of_resize_events_redraws_once
  22     3.770s     0.030s     3.740s     0.000s  tests/test_puzzle_review_bulk_read.py::test_PropertyTest_BulkRead_MatchesPerIdReads[db]
  23     3.760s     0.010s     3.750s     0.000s  tests/test_start_admin_local.py::TestStartAdminLocal_AcceptsADriverQualifiedUrl::test_other_drivers_are_accepted_too
  24     3.340s     0.000s     3.340s     0.000s  tests/test_solver.py::test_the_verdict_does_not_depend_on_probe_width_or_restarts[probe-everything]
  25     3.230s     0.000s     3.230s     0.000s  tests/test_start_admin_local.py::TestStartAdminLocal_StillChecksTheTargetDatabase::test_the_check_carries_the_urls_host_port_and_credentials
  26     3.090s     0.000s     3.090s     0.000s  tests/test_solver.py::test_the_two_oracles_agree_under_givens
  27     3.030s     0.000s     3.030s     0.000s  tests/test_admin_binding.py::TestAdminPanel_BindsLoopbackOnlyByDefault::test_no_other_interface_is_served
  28     3.020s     0.000s     3.020s     0.000s  tests/test_book_proof_pages.py::test_PropertyTest_BookProof_EveryStoredPrintSpecPrintsItsOwnSheet
  29     2.950s     0.000s     2.950s     0.000s  tests/test_orchestrator.py::test_the_abandonment_rate_is_not_worse_than_pure_redraw
  30     2.930s     0.000s     2.930s     0.000s  tests/test_difficulty.py::test_no_corpus_puzzle_needed_a_real_branch
  31     2.900s     0.000s     2.900s     0.000s  tests/test_run_admin_tests.py::TestRunAdminTests_ChecksTheTargetDatabase::test_a_driver_is_stripped_for_psql_only
  32     2.900s     0.010s     2.890s     0.000s  tests/test_setup_admin_local.py::TestSetupAdminLocal_ChecksTheTargetDatabase::test_a_driver_is_stripped_for_psql_only
  33     2.860s     0.000s     2.860s     0.000s  tests/test_difficulty.py::test_a_line_solvable_corpus_spans_all_three_bands
  34     2.860s     0.000s     2.860s     0.000s  tests/test_difficulty.py::test_every_corpus_puzzle_that_never_left_overlap_scores_the_same_point
  35     2.860s     0.000s     2.860s     0.000s  tests/test_difficulty.py::test_the_corpus_covers_the_whole_supported_extent_range
  36     2.840s     0.000s     2.840s     0.000s  tests/property/test_book_pairing.py::test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly_interior_pages
  37     2.820s     0.000s     2.820s     0.000s  tests/test_solver.py::test_the_verdict_does_not_depend_on_probe_width_or_restarts[restart-constantly]
  38     2.750s     0.000s     2.750s     0.000s  tests/test_book_pdf_ink_mode.py::TestBookInk_InkPositionsDoNotDependOnTheMode::test_the_two_modes_agree_on_every_page_of_every_book
  39     2.610s     0.260s     2.350s     0.000s  tests/test_book_guide_page.py::TestGuidePage_TitledHowToSolveNonograms::test_the_search_finds_the_old_title_on_the_old_page
  40     2.460s     2.360s     0.100s     0.000s  tests/property/test_recovery_bound.py::test_accepted_grids_have_real_verdicts_within_one_bound
  41     2.450s     0.080s     2.010s     0.360s  tests/test_puzzle_solver_resume.py::TestSolverResume_SolvedPuzzleReopensSolved::test_solved_reopens_solved
  42     2.390s     0.000s     2.390s     0.000s  tests/test_db_connect_timeout.py::test_a_hanging_test_is_killed_and_its_stack_printed
  43     2.390s     0.000s     2.390s     0.000s  tests/test_resample.py::test_the_checkpoints_own_request_abandons_identically_on_either_clock
  44     2.360s     0.090s     2.080s     0.190s  tests/test_puzzle_solver_zoom.py::TestSolverZoom_SurvivesADoubledRedraw::test_a_resize_that_never_crosses_the_breakpoint_rechooses_the_layout
  45     2.330s     0.150s     2.080s     0.100s  tests/test_puzzle_solver_marking.py::TestSolverMarking_RevealsNoCorrectness::test_marking_all_but_the_last_solution_cell_changes_nothing_but_cell_states
  46     2.290s     0.070s     1.810s     0.410s  tests/test_puzzle_solver_page.py::TestSolverPage_EmphasisesEveryFifthLine::test_PropertyTest_every_size_has_height_rows_of_width_cells_and_fifth_lines_heavier
  47     2.270s     0.000s     2.270s     0.000s  tests/test_start_admin_local.py::test_the_harness_reaches_the_end_of_the_script
  48     2.260s     0.080s     1.820s     0.360s  tests/test_puzzle_solver_clues.py::test_PropertyTest_SolverClues_NeverCirclesWhatBruteForceDoesNot
  49     2.250s     0.100s     1.810s     0.340s  tests/test_puzzle_solver_marking.py::TestSolverMarking_NoRequestPerMark::test_strokes_leave_the_console_clean
  50     2.250s     0.080s     1.810s     0.360s  tests/test_puzzle_solver_marking.py::TestSolverMarking_NoRequestPerMark::test_twenty_strokes_issue_no_request
```

## Ranking 2 — the 20 slowest files, with wall-clock shares

```
   #      total    share   tests   s/test  file
   1     61.67s    6.70%      35   1.762s  tests/test_puzzle_solver_maybe.py
   2     59.27s    6.44%      72   0.823s  tests/test_puzzle_solver_marking.py
   3     51.17s    5.56%      37   1.383s  tests/test_start_admin_local.py
   4     48.66s    5.29%       4  12.165s  tests/property/test_book_pdf_geometry.py
   5     40.58s    4.41%      52   0.780s  tests/test_puzzle_solver_clues.py
   6     36.99s    4.02%      23   1.608s  tests/test_run_admin_tests.py
   7     33.99s    3.69%      44   0.772s  tests/test_puzzle_solver_brush_menu.py
   8     33.98s    3.69%      44   0.772s  tests/test_puzzle_solver_progress.py
   9     29.96s    3.25%      25   1.198s  tests/test_puzzle_solver_zoom.py
  10     29.00s    3.15%      23   1.261s  tests/test_setup_admin_local.py
  11     27.69s    3.01%      67   0.413s  tests/test_puzzle_solver_page.py
  12     21.69s    2.36%      25   0.868s  tests/test_puzzle_solver_hint.py
  13     20.94s    2.27%      15   1.396s  tests/test_puzzle_solver_resume.py
  14     20.42s    2.22%      49   0.417s  tests/test_book_guide_page.py
  15     18.84s    2.05%      45   0.419s  tests/test_book_pdf_memory.py
  16     17.77s    1.93%      22   0.808s  tests/test_puzzle_solver_percent.py
  17     17.48s    1.90%       2   8.740s  tests/property/test_book_export_interior.py
  18     14.34s    1.56%      45   0.319s  tests/test_solver.py
  19     14.09s    1.53%      55   0.256s  tests/test_book_export_interior_cover.py
  20     13.98s    1.52%      49   0.285s  tests/test_book_toc.py
```

## Ranking 3 — the render-heavy files' total share

```
files in the frozen set: 29
files that contributed timings: 27
tests in those files: 1079
time: 195.42s
share of attributed time:  21.23%
share of wall clock:  20.99%

(non-render remainder)
time: 725.21s
share of attributed time:  78.77%
```

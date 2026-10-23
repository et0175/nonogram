# Suite duration rankings
# source: suite-durations-20261023.txt
# sha256: 1f31d5ba36bb3f1a3dcfe8b96d2436492589ea74ff58e844d1d06e39d8c55d3c
# tests with timings: 8981
# phase records parsed: 26917
# attributed time (setup+call+teardown): 1426.16s
#   setup         96.78s    6.79%
#   call        1309.13s   91.79%
#   teardown      20.25s    1.42%
# pytest wall clock: 1433.47s
# unattributed (collection, imports, session fixtures): 7.31s   0.51%
# result: 8954 passed, 27 skipped
#
# Shares below are of attributed time, not of wall clock.

## Cost families (the deciding table)

family                                   total   share  tests  ms/test
browser family (Chromium)              353.06s  24.76%    488      723
render-heavy frozen set                554.47s  38.88%   1391      399
property corpora                       151.54s  10.63%    185      819
property AND render                     81.69s   5.73%     12     6808
property OR render                     624.32s  43.78%   1564      399
admin-local script trio                 11.98s   0.84%     86      139
everything but the browser family     1073.10s  75.24%   8493      126

## 50 slowest tests

   #      total      setup       call   teardown  test
   1    81.030s     0.000s    81.030s     0.000s  tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_each_door_axis_arm_catches_a_shape_the_other_misses
   2    67.080s     0.000s    67.080s     0.000s  tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_every_door_shape_is_read_or_refused_and_never_silent
   3    56.920s     0.000s    56.920s     0.000s  tests/test_kill_matrix.py::test_ac7_the_four_arm_grid_of_card_257_reproduces
   4    44.690s     0.000s    44.690s     0.000s  tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_every_planted_position_shape_is_caught_or_refused
   5    41.130s     0.000s    41.130s     0.000s  tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_the_declared_blind_spots_are_still_silent
   6    36.370s     0.030s    36.290s     0.050s  tests/test_puzzle_solver_maybe.py::TestSolverMaybe_BoardDoesNotMoveOnSolveAtAnyWidth::test_sweep[chromium]
   7    24.850s     0.000s    24.850s     0.000s  tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_every_callee_exemption_is_read_twice_on_its_own_branch
   8    21.180s     0.000s    21.180s     0.000s  tests/test_browser_fixture_scope.py::TestBrowserFixtures_OrderIndependent::test_reverse_order_passes
   9    21.110s     0.000s    21.110s     0.000s  tests/property/test_book_pdf_geometry.py::test_PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity_pdf_pages
  10    20.450s     0.000s    20.450s     0.000s  tests/property/test_book_pdf_geometry.py::test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_pdf_pages
  11    19.110s     0.000s    19.110s     0.000s  tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost
  12    18.000s     0.000s    18.000s     0.000s  tests/test_browser_fixture_scope.py::TestBrowserFixtures_OrderIndependent::test_shuffled_order_passes
  13    16.180s     0.020s    16.160s     0.000s  tests/property/test_book_export_interior.py::test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage
  14    15.680s     0.000s    15.680s     0.000s  tests/test_suite_profile.py::TestSuiteTiming_CollectsTheSameWithAndWithoutTheLog::test_the_outcomes_are_identical_with_and_without_the_log
  15    13.450s     0.000s    13.450s     0.000s  tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_the_receiver_resolution_bound_is_reported_rather_than_capped
  16    11.890s     0.000s    11.890s     0.000s  tests/property/test_difficulty_calibration.py::test_medium_is_reachable_on_a_seeded_corpus
  17    10.290s     0.000s    10.290s     0.000s  tests/test_book_pdf_memory.py::TestBookPdfMemory_RealBookExportsUnderTheCap::test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under
  18     9.620s     0.000s     9.620s     0.000s  tests/test_generation_failures.py::TestGenerationFailures::test_maximum_size_is_hard_to_generate
  19     9.370s     0.000s     9.370s     0.000s  tests/property/test_book_pdf_geometry.py::test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_pdf_pages
  20     8.980s     0.000s     8.980s     0.000s  tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_each_door_reaching_shape_is_refused_by_the_mechanism_that_refuses_it
  21     7.930s     0.000s     7.930s     0.000s  tests/property/test_cli_exports_byte_identity.py::test_property_cli_exports_byte_identical_whatever_the_book_geometry
  22     7.050s     0.000s     7.050s     0.000s  tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_the_callee_arms_fall_through_refuses_and_costs_nothing
  23     7.040s     0.000s     7.040s     0.000s  tests/property/test_nudge_mask.py::test_flipped_cells_come_from_the_solver_and_nest
  24     6.680s     0.000s     6.680s     0.000s  tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_each_geometry_door_carries_a_site_of_its_own
  25     6.460s     0.000s     6.460s     0.000s  tests/test_sourcing_image.py::test_binarize_threshold_corpus_needs_no_more_nudges_than_dither
  26     6.390s     0.000s     6.390s     0.000s  tests/property/test_book_pairing.py::test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly
  27     6.390s     5.840s     0.550s     0.000s  tests/test_book_pdf_ink_mode.py::TestBookInk_InkPositionsDoNotDependOnTheMode::test_the_corpus_is_the_size_it_claims_and_varies
  28     6.280s     0.000s     6.280s     0.000s  tests/test_kill_matrix.py::test_ac7_the_lock_guard_file_reproduces_130_of_130_pass_and_reached
  29     5.860s     0.000s     5.860s     0.000s  tests/test_book_guide_page.py::TestGuidePage_IsTwoPages::test_the_exported_interior_opens_with_both_guide_pages_then_the_first_puzzle_or_divider
  30     5.800s     0.000s     5.800s     0.000s  tests/test_kill_matrix.py::test_ac3_the_flag_off_reading_on_a_child_spawning_target_is_the_bound
  31     4.870s     4.870s     0.000s     0.000s  tests/test_book_pdf_memory.py::TestBookPdfMemory_PeakDoesNotGrowWithPageCount::test_a_big_books_peak_is_a_small_books_peak
  32     4.380s     0.000s     4.380s     0.000s  tests/test_kill_matrix.py::test_ac3_the_recording_pass_declares_the_blind_spot_the_re_raising_pass_kills
  33     4.310s     0.000s     4.310s     0.000s  tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_the_page_position_set_is_derived_from_the_one_geometry_door
  34     4.230s     0.000s     4.230s     0.000s  tests/test_browser_fixture_scope.py::TestBrowserFixtures_EveryTestPassesAlone::test_the_riskiest_tests_pass_alone[test_puzzle_solver_fifth_rule]
  35     4.160s     0.000s     4.160s     0.000s  tests/test_book_guide_page.py::TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyLegend::test_the_difficulty_legend_carries_its_three_labels_and_no_sentences
  36     4.150s     0.060s     4.030s     0.060s  tests/test_puzzle_solver_resume.py::test_PropertyTest_SolverResume_SaveAndRestoreRoundTrip
  37     4.080s     0.000s     4.080s     0.000s  tests/property/test_book_pairing.py::test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly_interior_pages
  38     4.010s     0.000s     4.010s     0.000s  tests/test_book_pdf_band.py::test_PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle
  39     3.600s     3.410s     0.190s     0.000s  tests/test_book_trim_persistence.py::TestBookTrim_ReopenInInchesStaysInsideLimits::test_the_fields_show_the_stated_limit_not_eighteen_ninety[postgres]
  40     3.290s     0.000s     3.290s     0.000s  tests/test_solver.py::test_the_verdict_does_not_depend_on_probe_width_or_restarts[probe-everything]
  41     3.150s     0.000s     3.150s     0.000s  tests/test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured
  42     3.130s     0.000s     3.130s     0.000s  tests/test_db_engine_lifecycle.py::TestEngineLifecycle_TheResetIsAPublishedSeam::test_every_text_that_names_card_252_points_here_and_agrees_on_the_parameters
  43     3.120s     0.060s     3.040s     0.020s  tests/test_puzzle_solver_fifth_rule.py::TestSolverFifthRule_GeometryAndOtherMarksUnchanged::test_the_rules_against_paper_are_untouched
  44     3.040s     0.000s     3.040s     0.000s  tests/test_admin_binding.py::TestAdminPanel_BindsLoopbackOnlyByDefault::test_no_other_interface_is_served
  45     3.030s     0.000s     3.030s     0.000s  tests/test_orchestrator.py::test_the_abandonment_rate_is_not_worse_than_pure_redraw
  46     3.000s     0.000s     3.000s     0.000s  tests/test_book_pdf_ink_mode.py::TestBookInk_InkPositionsDoNotDependOnTheMode::test_the_two_modes_agree_on_every_page_of_every_book
  47     2.970s     0.000s     2.970s     0.000s  tests/test_solver.py::test_the_two_oracles_agree_under_givens
  48     2.900s     0.070s     2.780s     0.050s  tests/test_puzzle_solver_zoom.py::TestSolverZoom_SurvivesADoubledRedraw::test_a_burst_of_resize_events_redraws_once
  49     2.860s     0.000s     2.860s     0.000s  tests/test_difficulty.py::test_no_corpus_puzzle_needed_a_real_branch
  50     2.850s     0.000s     2.850s     0.000s  tests/test_difficulty.py::test_a_line_solvable_corpus_spans_all_three_bands

## 20 slowest files

   #      total    share   tests   s/test  file
   1    344.29s   24.14%      90   3.825s  tests/test_book_export_interior_cover.py
   2     93.03s    6.52%      76   1.224s  tests/test_kill_matrix.py
   3     65.47s    4.59%      35   1.871s  tests/test_puzzle_solver_maybe.py
   4     58.65s    4.11%      29   2.022s  tests/test_browser_fixture_scope.py
   5     51.82s    3.63%       4  12.955s  tests/property/test_book_pdf_geometry.py
   6     50.11s    3.51%      84   0.597s  tests/test_puzzle_solver_clues.py
   7     47.11s    3.30%      76   0.620s  tests/test_puzzle_solver_marking.py
   8     44.60s    3.13%     117   0.381s  tests/test_puzzle_editor_ui.py
   9     28.44s    1.99%      44   0.646s  tests/test_puzzle_solver_progress.py
  10     28.11s    1.97%      50   0.562s  tests/test_puzzle_solver_brush_menu.py
  11     27.80s    1.95%      17   1.635s  tests/test_puzzle_solver_fifth_rule.py
  12     26.84s    1.88%      29   0.926s  tests/test_puzzle_solver_zoom.py
  13     22.01s    1.54%     399   0.055s  tests/test_suite_profile.py
  14     21.60s    1.51%      55   0.393s  tests/test_book_pdf_memory.py
  15     20.25s    1.42%      49   0.413s  tests/test_book_guide_page.py
  16     19.95s    1.40%      67   0.298s  tests/test_puzzle_solver_page.py
  17     17.71s    1.24%       3   5.903s  tests/property/test_book_export_interior.py
  18     16.76s    1.18%      53   0.316s  tests/test_book_toc.py
  19     15.39s    1.08%      25   0.616s  tests/test_puzzle_solver_hint.py
  20     15.06s    1.06%      15   1.004s  tests/test_puzzle_solver_resume.py

## Render-heavy files (the render hypothesis)

files in the frozen set: 33
files that contributed timings: 31
tests in those files: 1391
time: 554.47s
share of attributed time:  38.88%
share of wall clock:  38.68%

## Non-render remainder

time: 871.69s
share of attributed time:  61.12%

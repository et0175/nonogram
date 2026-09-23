# Backlog

## Deferred during implementation
- [ ] CARD-135 follow-up: the single download button on books_list.html and book_detail.html now fetches only the interior PDF — offer the cover file there too (FR-043). Site: src/nonogram/admin/templates/books_list.html, book_detail.html   @feature
- [ ] CARD-135 minor F-008: export_book docstring still claims every route goes through it. Site: src/nonogram/admin/book_pdf_generator.py   @tech-debt
- [ ] Pre-existing failure: tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied (red on 89ed292 and after wave 20)   @ops
- [ ] CARD-120 F-007: typing an edited cell back to its current prefill value does not release the hand-edit mark; a count change judges edits against the old prefill. Site: src/nonogram/admin/book_manager.py (revise_plan)   @tech-debt
- [ ] CARD-120 F-008: the refusal page's Planned row is read from the stored plan, not the submitted one. Site: src/nonogram/admin/app.py (setup-print)   @tech-debt
- [ ] CARD-120 F-009: the trim assertion in tests/test_book_plan_storage.py is vacuous in DB mode   @tech-debt
- [ ] CARD-120 O-2 (pre-existing): in DB mode the trim from Print setup is never saved   @feature
- [ ] CARD-122 follow-up: bulk PuzzleReviewService.get_puzzles(ids) — _selected_cells opens up to ~300 DB sessions per render; the naive single-query fix is wrong because it reads the puzzles.book_id mirror   @tech-debt
- [ ] Pre-existing: a hand-typed empty ?status= turns the approved-only default off on the book-selection and puzzle-list routes   @ops
- [ ] Card-text defects for decompose: CARD-122 G-1 says "the template imports book_plan.bucket_of" (a Jinja template cannot import); forge:commit's no-Co-Authored-By rule contradicts this session's required attribution line   @tech-debt
- [ ] CARD-124 follow-up: N+1 selection read — a status change on a 150-puzzle book opens ~150 DB sessions; needs the same batch getter in puzzle_review.py as CARD-122's follow-up   @tech-debt
- [ ] INV-008's three and INV-012's six declared checks exist nowhere under tests/   @tech-debt
- [ ] tests/README.md is titled "Admin Panel Test Suite - Wave 1", names no book test file and is ~20 waves stale — needs a rewrite, not a patch   @tech-debt
- [ ] Six system-contract check refs (ADR-0029/R2, INV-008..INV-012) name tests that do not exist yet — the model claims mechanical checks it does not have   @tech-debt
- [ ] Test isolation: test_card_037_upload_retry and test_web_upload glob the shared system temp dir for nonogram-upload-*, so two full suites running at once perturb each other   @tech-debt

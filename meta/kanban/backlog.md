# Backlog

## Deferred during implementation
- [ ] CARD-135 follow-up: the single download button on books_list.html and book_detail.html now fetches only the interior PDF — offer the cover file there too (FR-043). Site: src/nonogram/admin/templates/books_list.html, book_detail.html   @feature
- [ ] CARD-135 minor F-008: export_book docstring still claims every route goes through it. Site: src/nonogram/admin/book_pdf_generator.py   @tech-debt
- [ ] Pre-existing failure: tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied (red on 89ed292 and after wave 20)   @ops
- [ ] CARD-120 F-007: typing an edited cell back to its current prefill value does not release the hand-edit mark; a count change judges edits against the old prefill. Site: src/nonogram/admin/book_manager.py (revise_plan)   @tech-debt
- [ ] CARD-120 F-008: the refusal page's Planned row is read from the stored plan, not the submitted one. Site: src/nonogram/admin/app.py (setup-print)   @tech-debt
- [ ] CARD-120 F-009: the trim assertion in tests/test_book_plan_storage.py is vacuous in DB mode   @tech-debt
- [ ] CARD-120 O-2 (pre-existing): in DB mode the trim from Print setup is never saved   @feature

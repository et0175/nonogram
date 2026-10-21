# Puzzle Creation (CTX-001)

The system's **only** bounded context. `meta/architecture/domain/contexts.yml`
reached that outcome by ruling out every boundary signal rather than by defaulting
to a monolith: AGG-001 (Puzzle) is sourced, encoded, verified, scored and exported
as one object, its three invariants are cross-cutting by design, and three
candidate technical seams were considered and deliberately kept as *module* seams.
`context_map` is empty — there is nothing to integrate with, and
`external_systems.yml` is `[]`.

Two aggregates: **AGG-001 Puzzle**, and **AGG-002 Book**, which references puzzles
by id and never modifies them (ADR-0033).

Seven capabilities, three inbound adapters, ten components, one dependency
direction — enforced by an `ast` walk, not a convention.

Start at [01 — the layered pipeline](01-the-layered-pipeline.md). Every later file
assumes the direction of the arrows described there.

## Files

| File | Covers | Components / capability |
|---|---|---|
| [01-the-layered-pipeline.md](01-the-layered-pipeline.md) | ADR-0007's four ranks, the `ast` import guard, the orchestrator, the three invariants' enforcement points, `RetryCounter`/`run_bounded`, the enforced deadline | COMP-002 |
| [02-sourcing-a-solution-grid.md](02-sourcing-a-solution-grid.md) | three modes, two dispatch tables, extent resolution and the bare-N refusal, the exact-count sampler, the library's jittered boundary, the ink box and binarisation | COMP-003 / CAP-001 |
| [03-deriving-clues.md](03-deriving-clues.md) | run-length encoding, the `(0,)` marker, `strict=True`, why `clue_matches_line` is scoped to complete lines | COMP-004 / CAP-002 |
| [04-uniqueness-and-recovery.md](04-uniqueness-and-recovery.md) | the three stratified fixed points, the restart schedule, why probing is sound, the CON-005 re-encode backstop, the oracle, and the four recovery remedies | COMP-005 / CAP-003 |
| [05-difficulty-calibration.md](05-difficulty-calibration.md) | the strategy ladder, the two band tables and why they are not derived from each other, the retired fourth tier | COMP-006 / CAP-004 |
| [06-exporting-a-finished-puzzle.md](06-exporting-a-finished-puzzle.md) | the format registry, where the readiness gate is *not*, filenames and collisions, the shared page geometry, `PageSpec`, the five renderers | COMP-007 / CAP-005 |
| [07-book-assembly-and-the-admin-panel.md](07-book-assembly-and-the-admin-panel.md) | the storage guard, AGG-002's lifecycle and gate, the distribution plan re-derived, the three millimetre constants, the page-at-a-time PDF | COMP-009 / CAP-006 |
| [08-playing-a-stored-puzzle.md](08-playing-a-stored-puzzle.md) | the one route, why it has no command, the naming trap, and how "nothing is written" is tested | COMP-009 / CAP-007 |
| [09-the-three-inbound-adapters.md](09-the-three-inbound-adapters.md) | the CLI's parsing-only line and exit-code table, the web UI's bind and cross-origin refusal, the admin panel's credentialed door | COMP-001, COMP-008, COMP-009 |
| [10-persistence-and-the-unmodelled-edges.md](10-persistence-and-the-unmodelled-edges.md) | engine selection, the dual-mode doubling, the six tables (three unread), and the 1.6% of the package no component names | COMP-010 |

## Perspectives

| Role | Document | Why it is here |
|---|---|---|
| 🏛 architect | [perspectives/architect.md](perspectives/architect.md) | the single-context decision, the closed decisions and their guards, and the model-vs-code drift to carry back |
| 💻 developer | [perspectives/developer.md](perspectives/developer.md) | the four guards that fail your build, the boundary contracts, error semantics, and every extension point |
| 🔧 sre | [perspectives/sre.md](perspectives/sre.md) | the one deployed service, the derived timeout chain, bounds with their constants, failure modes, capacity figures |
| 👤 ACT-001 Puzzle Creator | [perspectives/puzzle-creator.md](perspectives/puzzle-creator.md) | the four touchpoints, what the request type encodes about intent, and the rules that actually bound this actor |

The technical trio is fixed and relevant to every aspect (the skill's default
`architect` / `developer` / `sre`, since there is no `explain.perspectives` config
in this repository). The actor row is there because `actors.yml` carries exactly
one human actor and `trace.yml` lands its stories in this context's components —
ACT-002 is `type: system` and gets no perspective. It is written as mechanism and
constraints, never as a task guide.

## Diagrams

| Diagram | Derived from |
|---|---|
[diagrams/01-dependency-ranks.puml](diagrams/01-dependency-ranks.puml) | `tests/test_cli.py:747`-`810` — the guard's rank table, not the C4 diagram |
[diagrams/04-solve-flow.puml](diagrams/04-solve-flow.puml) | `solver/search.py:7`-`56`, `:295`, `:100` |
[diagrams/04-recovery-policies.puml](diagrams/04-recovery-policies.puml) | `orchestrator.py:1591`-`2196` and the bound constants at `:192`/`:224`/`:261`/`:287` |
[diagrams/05-score-and-tier-bands.puml](diagrams/05-score-and-tier-bands.puml) | `difficulty.py:316`, `:342`, `:200`-`226`, `:464` |
[diagrams/07-book-lifecycle.puml](diagrams/07-book-lifecycle.puml) | `admin/book_manager.py:50`, `:2223`, `:2180`, `:488` |

The C4 views sit beside them in the model: `meta/architecture/c4/context.puml`,
`containers.puml`, `components-CTX-001.puml`.

## doc → code map

Component globs are `meta/architecture/trace.yml:2356`-`2402`. Line counts
re-derived with `wc -l` over `find src/nonogram -name '*.py'`.

| Path | Lines | Component | Role |
|---|---|---|---|
| `src/nonogram/__init__.py` | 54 | — | the canonical package map; re-exports nothing and imports no submodule, so importing `nonogram` cannot drag an adapter in behind a capability |
| `src/nonogram/cli.py` | 573 | COMP-001 | argparse adapter; syntax only; the sole owner of the exit-code table |
| `src/nonogram/orchestrator.py` | 2,675 | COMP-002 | owns AGG-001; the single enforcement point for INV-002 and INV-003; drives POL-001..POL-006 and the reveal policy; the only `solver.solve` call site in the pipeline |
| `src/nonogram/errors.py` | 190 | — (shared rank) | the flat, import-free, behaviour-free domain error hierarchy |
| `src/nonogram/limits.py` | 17 | — (shared rank) | `MIN_SIZE = 10`, `MAX_SIZE = 30`, per side |
| `src/nonogram/clues.py` | 125 | COMP-004 | run-length encoding; `encode_line`, `compute_clues`, `clue_matches_line` |
| `src/nonogram/sourcing/__init__.py` | 154 | COMP-003 | the two per-mode dispatch tables, `for_mode` and `shape_for_mode` |
| `src/nonogram/sourcing/random_grid.py` | 460 | COMP-003 | the exact-count sampler, **and** the shared extent/density validators every mode delegates to |
| `src/nonogram/sourcing/library.py` | 415 | COMP-003 | template registry (`cat`/`heart`/`house`/`moon`), exact-integer rescale, the jittered boundary threshold |
| `src/nonogram/sourcing/image.py` | 1,251 | COMP-003 | ink box, aspect guard, crop, binarisation (threshold vs dither), the degenerate-ink guard, and POL-002's nudge *mechanism* |
| `src/nonogram/sourcing/templates/` | 152 | COMP-003 | ASCII-art data as `.py` modules (so setuptools ships them); `dolphin`/`dog_in_house` are present but unregistered |
| `src/nonogram/solver/__init__.py` | 116 | COMP-005 | the whole public API: five names, documented as the complete surface |
| `src/nonogram/solver/propagate.py` | 1,205 | COMP-005 | line logic: overlap rule, placement-intersection DP, the fixed-point sweep, `RungTagger`, `check_deadline`, and `mask_runs` (the native clue-encode twin) |
| `src/nonogram/solver/search.py` | 1,815 | COMP-005 | `solve`, `SolveResult`/`SolveSignals`, the restart schedule, probing, the CON-005 re-encode backstop, `choose_givens` |
| `src/nonogram/difficulty.py` | 592 | COMP-006 | the ladder, `score_difficulty`, the one `classify`, `Tier`, `parse_tier` / `tier_of_record` |
| `src/nonogram/export/__init__.py` | 351 | COMP-007 | the format registry — the only list of format names in the codebase — `ExportPayload`, `write`, `_free_path` |
| `src/nonogram/export/layout.py` | 4,838 | COMP-007 | the shared print geometry; `compute_layout`, `PageSpec`, the comfort curve, the cell floor, two-up pairing |
| `src/nonogram/export/png.py` | 456 | COMP-007 | the raster, and `render_image` — the entry point the PDF reuses so the two cannot drift |
| `src/nonogram/export/svg.py` | 173 | COMP-007 | the vector, assembled as text; inches over a pixel `viewBox` |
| `src/nonogram/export/pdf.py` | 496 | COMP-007 | two pages from the same raster; the packaged DejaVu Sans header face |
| `src/nonogram/export/json_export.py` | 347 | COMP-007 | schema version 2, document + decoder; carries `strategies` and `binarisation` |
| `src/nonogram/export/csv_export.py` | 420 | COMP-007 | four marker-delimited sections; a closed `#meta` key set, which is why it carries neither new field |
| `src/nonogram/export/fonts/` | — | COMP-007 | `DejaVuSans.ttf` + `LICENSE` as package data (ADR-0006/R1, `pyproject.toml:79`) |
| `src/nonogram/web/__init__.py` | 96 | COMP-008 | re-exports `DEFAULT_PORT`, `LOOPBACK_HOST`, `create_server`, `serve_on` |
| `src/nonogram/web/server.py` | 116 | COMP-008 | `LoopbackHTTPServer`, the constant bind, the deliberate create/serve split |
| `src/nonogram/web/handler.py` | 930 | COMP-008 | the router, the transport bounds, the cross-origin refusal, `_generate`'s shared `try` |
| `src/nonogram/web/pages.py` | 882 | COMP-008 | the HTML as f-strings; `FORM_ACTION`; the image-only form |
| `src/nonogram/web/submission.py` | 350 | COMP-008 | urlencoded body → `GenerationRequest`, deciding nothing about the values |
| `src/nonogram/web/multipart.py` | 206 | COMP-008 | the hand-rolled multipart parser (no stdlib one exists after PEP 594) |
| `src/nonogram/web/uploads.py` | 115 | COMP-008 | opaque retention tokens, bounded by count at 8 |
| `src/nonogram/web/metadata.py` | 140 | COMP-008 | **no production caller**; the shipped work is `web/static/metadata.js` |
| `src/nonogram/admin/app.py` | 6,330 | COMP-009 | `create_app`, the boot-time refusals, the request hook, ~55 routes |
| `src/nonogram/admin/puzzle_review.py` | 2,350 | COMP-009 | the puzzle store, filters, review actions, **and the ADR-0032/R1 storage guard** |
| `src/nonogram/admin/batch_generator.py` | 858 | COMP-009 | batch generation through COMP-002 |
| `src/nonogram/admin/book_manager.py` | 2,783 | COMP-009 | AGG-002's store, the one `set_book_status`, the readiness gate |
| `src/nonogram/admin/book_plan.py` | 596 | COMP-009 | the distribution plan as pure domain; `DEFAULT_PLAN`, buckets, largest-remainder apportionment |
| `src/nonogram/admin/book_page_spec.py` | 576 | COMP-009 | the one door onto a book's sheet; `BOOK1_PROFILE`, `FLOOR_MM`, `InkMode` |
| `src/nonogram/admin/book_pdf_generator.py` | 7,114 | COMP-009 | the interior/cover export; fits no cell and places no grid line (ADR-0036/R2); `interior_stream`'s one-page-at-a-time generator |
| `src/nonogram/admin/book_answer_key.py` | 540 | COMP-009 | INV-011's answer-page capacity and order |
| `src/nonogram/admin/book_proof.py` | 795 | COMP-009 | ADR-0037's two measurable proof pages |
| `src/nonogram/admin/book_kdp.py` | 627 | COMP-009 | KDP's gutter table and the finalise check |
| `src/nonogram/admin/print_specs.py` | 419 | COMP-009 | `PrintSpecValidator`, the form-side trim/margin check |
| `src/nonogram/admin/image_manager.py` | 788 | COMP-009 | the uploaded-picture store, size presets, fit prediction |
| `src/nonogram/admin/image_to_puzzle.py` | 100 | COMP-009 | picture → grid + clues for the panel |
| `src/nonogram/admin/grid_renderer.py` | 53 | COMP-009 | `grid_to_svg` for preview and download |
| `src/nonogram/admin/regrade.py` | 573 | COMP-009 | the re-grade batch under the ADR-0029 ladder; `REGRADE_BUDGET_SECONDS` |
| `src/nonogram/admin/pdf_generator.py` | 349 | COMP-009 | **test-reachable only**; the tree's only `reportlab` user |
| `src/nonogram/admin/book_membership.py` | 277 | COMP-009 | **test-reachable only**; a one-off repair utility (CARD-100) |
| `src/nonogram/admin/templates/`, `static/` | — | COMP-009 | Jinja templates, `admin.css`, and CAP-007's `solver.js` / `solver_state.js` (120 KB, named by no component) |
| `src/nonogram/db/models.py` | 227 | COMP-010 | six tables; three of them read and written by nothing |
| `src/nonogram/db/session.py` | 461 | COMP-010 | engine selection from `DATABASE_URL`, `normalized_url`, `session_scope` |
| `src/nonogram/db/__init__.py` | 38 | COMP-010 | PEP 562 `__getattr__` forwarding, so a stale `None` cannot be captured at import |
| `src/nonogram/analysis/quality_metric.py` | 303 | **no component** | live: `measure_quality`, called from `admin/app.py:1942`; the machinery behind ADR-0032/R2 |
| `src/nonogram/analysis/strategy_counter.py` | 151 | **no component** | unreferenced; a second difficulty scorer whose vocabulary predates ADR-0029 |
| | **46,127** | | **744 lines (1.6%) fall outside every component glob** |

### Test tree, where it is part of the mechanism

| Path | Role |
|---|---|
| `tests/test_cli.py:732`-`1040` | the `ast` import guard that *is* ADR-0007's enforcement, plus the three guards on the guard |
| `tests/helpers/brute_force_oracle.py` | ADR-0014's independent oracle; **must never import `nonogram.solver`**; two counters that cross-check each other |
| `tests/property/test_solver_uniqueness.py` | EC-001/CON-005, the one mandatory property, both ADR-0014 directions, with the case floors asserted inside the tests |
| `tests/test_difficulty_tiers.py` | the `ast` walk proving `difficulty.classify` is the only band comparison in the package |
| `tests/test_web_server.py:2416`, `:2518` | the `ast` walk over `pages.py`'s interpolations, and the test that regexes the docstring's own numbers against it |
| `tests/test_export_a4_golden.py` | CON-019: CLI and web exports stay byte-identical under ADR-0036 |
| `tests/test_admin_serving.py` | reads `--timeout` out of `start.sh` and asserts it clears the route budgets |
| `tests/test_admin_auth.py`, `tests/test_admin_binding.py` | seven and four classes mapping one-to-one onto the panel's door |
| `tests/bench_generate.py` | ADR-0001's 5 s p95 benchmark gate — deliberately *not* an enforced constant |

## Related docs

- Model: `meta/architecture/requirements.yml` (FR/NFR/AC/EC, each naming its test) · `meta/architecture/trace.yml` · `meta/architecture/domain/` · `meta/architecture/decisions/adr/` (ADR-0001..ADR-0039)
- In-repo prose: `docs/GENERATION_ALGORITHM.md` (the pipeline as the code implements it) · `docs/REQUIREMENTS/DIFFICULTY_ENGINE.md` · `DATABASE_MIGRATIONS.md` · `ADMIN_SETUP.md` · `docs/deploy/` · `docs/book_layout/`
- Delivery: `meta/kanban/cards/CARD-*.md` — a card's `## Worktree notes` is often the best account of *why* a piece of code looks the way it does. The ones cited most often from these files are CARD-080, CARD-085, CARD-090/091, CARD-101, CARD-139, CARD-145 and CARD-032.
- Up one level: [the `domain` group](../README.md) · [the root overview](../../README.md)

# Backlog

## Deferred from Nonogram Generator brainstorm (2026-08-27)
- [ ] Support color/multi-value nonograms (not just black/white)                    @feature
- [ ] Interactive/playable puzzle output (web or local UI to solve the puzzle)      @feature

## Surfaced during delivery (Wave 7, 2026-08-29)
- [ ] Retune difficulty score weights/cutoffs (ADR-0005/ADR-0013) — `--difficulty hard`
      is unreachable and `medium` is hard to hit with real generated grids (measured
      ceiling ~43 vs. the Hard floor of 66, across 10x10-25x25 at 45-55% density).
      ADR-0005's own Consequences section predicted exactly this and deferred the
      numbers pending real distributions — CARD-010 (Wave 7) produced the first ones.
      Needs an ADR-0005/ADR-0013 revision (new weights and/or cutoffs), not a code
      change.                                                                       @tech-debt

## Surfaced during delivery (Wave 8, 2026-08-29)
- [ ] **Decision needed:** a non-ASCII `--name` (e.g. `кот`, `café`) renders as `.notdef`
      tofu boxes in the PDF header — Pillow's bundled default font is an ASCII-only
      subset (verified: identical bitmap to an unassigned codepoint). CARD-011 keeps
      `--name` verbatim (AC-044) and CARD-014 could not fix this without breaking a
      guardrail: shipping a font reopens ADR-0006/G-1 (closed dependency baseline),
      mangling the name contradicts AC-044. Filenames are unaffected (sanitization is
      already Unicode-aware) — only the PDF header text is impacted. Options: (a) ship
      a small TTF as package data and accept the dependency-baseline exception, (b)
      document ASCII-only PDF headers as a known limitation, (c) reject non-ASCII
      `--name` at the CLI boundary when `--export pdf` is requested. Needs a product
      call, not a code fix.                                                        @tech-debt
- [ ] `tests/test_export_image.py::test_the_png_contains_the_clues` is vacuous —
      asserts `crop(...).getbbox() is not None` on an ink-on-white RGB image, which is
      always true (white is non-zero), so the gutters are never actually checked for
      ink. Found while building CARD-014 (whose own tests use a real `_has_ink`
      predicate instead). Fix belongs in CARD-012's test file.                     @tech-debt
- [ ] `README.md`'s Status section is stale since CARD-007 and now four export formats
      out of date (JSON/PNG/SVG/CSV/PDF all shipped; README still describes an earlier
      state). Flagged repeatedly across CARD-010/011/014 with no owner yet.         @tech-debt
- [ ] PDF pages embed their raster as lossy JPEG (Pillow's default for an RGB page),
      producing measurable pixel drift on white background (up to 45/255 on some
      pixels) — invisible at print size, no AC/NFR currently governs it, but worth
      checking `quality=95` or an alternate save path if crisp reproduction ever
      matters more than file size.                                                 @tech-debt

## Surfaced during delivery (Wave 9, 2026-08-29)
- [x] ~~EXIF orientation ignored when converting an uploaded photo~~ — fixed 2026-08-29
      directly on main (commit follows): `load_greyscale` now applies
      `ImageOps.exif_transpose` before flattening, a no-op on files with no
      orientation tag. New test constructs a JPEG with an asymmetric marker, stores
      it pre-rotated with an Orientation=6 tag, and asserts the converted grid
      matches the un-rotated source exactly — verified to genuinely fail without
      the fix (reverted it locally, confirmed the test catches it) before
      confirming it passes with the fix restored. Full suite: 1122 passed, 1
      xfailed, no regressions.                                                    @tech-debt
- [ ] Export metadata (JSON/CSV) doesn't record the `--image` path or `--library-key`
      the way it records mode/size/density/seed — an image- or library-sourced export
      isn't self-describing enough to reproduce the run from the file alone. Pre-existing
      since CARD-008 (library mode), widened by one mode in CARD-015.               @tech-debt
- [x] ~~`TestNudge_ReportsFailureAtCap` forward reference~~ — resolved 2026-08-29,
      CARD-016 shipped `test_nudge_reports_failure_at_cap` in `tests/test_nudge.py`.
                                                                                     @tech-debt

## Surfaced during delivery (Wave 10, 2026-08-29)
- [ ] A large/hard uploaded image can now spend up to 6 solver invocations
      (1 conversion + 5 nudges) against the shared 30s generation deadline instead of
      1 — the budget itself isn't breached (the deadline is absolute across all
      solves), but on an unlucky image this could surface a generic `SolverTimeout`
      instead of CARD-016's "retry with a different image/size" advice. Low
      probability (the expensive full-search case is usually the one that
      recovers), but worth knowing when reporting exits for image mode.            @tech-debt
- [x] ~~Until CARD-017 ships nudge-count reporting, nudged image runs are
      silent~~ — resolved 2026-08-29, CARD-017 (Wave 11) shipped the count line.
                                                                                     @tech-debt

## Surfaced during delivery (Wave 11, 2026-08-29)
- [ ] `tests/test_nudge_reporting.py`'s AC-040 test (`test_export_reports_nudge_count`)
      asserts only the substring `"2 cells were nudged"`, leaving the line's tail
      ("to reach a unique solution" — the clause carrying the *why*, which ADR-0004's
      disclosure is actually about) unpinned. The fix-cycle's new singular-boundary
      test already pins the full sentence; make the plural one match for consistency.
                                                                                     @tech-debt

## Deferred from Local web UI brainstorm (2026-08-30)
- [ ] In-browser preview of the generated puzzle in the web UI (render the PNG
      inline after generation, instead of only confirming file paths)          @feature
- [ ] Progress/status feedback in the web UI for long-running generations —
      CARD-018's own measurements show some 20x20 mid-density requests still
      take up to ~30s, which is a poor experience behind a plain "submit and
      wait" form                                                                @feature
- [ ] Browse/list previously generated puzzles from the web UI                 @feature

## Deferred from CARD-022 (2026-08-31)
- [ ] `test_the_form_lists_every_registered_export_format` (tests/test_web_server.py)
      enumerates `export.FORMATS` with no minimum-count assertion, so it passes
      vacuously if the registry empties. Its sibling
      `test_the_form_lists_every_difficulty_tier_plus_an_unset_choice` has the same
      shape and is saved only by a trailing non-loop assertion. Same pattern
      AC-059 exists to eliminate, and same class as the existing
      `test_the_png_contains_the_clues` entry above; CLAUDE.md's convention
      ("assert a minimum case count inside the test itself so the corpus can't
      silently shrink") covers all three. Out of CARD-022's scope.       @tech-debt
- [ ] Measure or permanently retire the withdrawn shutdown bound from CARD-019's
      failure matrix row F-6. CARD-022 withdrew the number rather than measuring
      it; a matrix row with no bound is a declaration that has stopped declaring.
                                                                         @tech-debt
- [ ] Three inaccurate claims in `src/nonogram/web/handler.py`'s own prose, found by
      CARD-022's cycle-2 review (F-101/F-102/F-103) and deliberately NOT fixed there:
      the loop of correcting-claims-then-introducing-new-ones had run three cycles and
      a fourth pass was judged more likely to add a sixth than to converge.
      (a) `_respond`'s pre-override 400 description over-generalises — CPython 3.14.3
          assigns `request_version` BEFORE the word-count syntax check, so a >=4-word
          request line with a valid trailing version reached `send_error(400)` WITH a
          status line. Repeated at handler.py:280 and in CARD-019 row F-4.
      (b) `explain` is documented as "a static canned string from `responses`" — it is
          not; that table is what the STDLIB's send_error consults. Only the two 431
          call sites pass `explain`, as `str(err)` from `http.client`. The load-bearing
          half (nothing request-derived reaches it) is correct.
      (c) `test_the_docstring_names_every_access_control_check...`'s docstring says
          handler.py "says so in two places"; the same delta reduced it to one.
      All three are prose-only; the modules are executable-identical.        @tech-debt

## Surfaced during design discussion (2026-09-01)

- [ ] **Measure how close the finished puzzle is to the source picture** — a fidelity /
      recognizability metric. Nothing in the codebase measures this today (verified
      2026-09-01: no similarity, PSNR, SSIM or Hamming computation exists; the word
      "fidelity" appears only in the EC-002 *export round-trip* sense, which is an
      unrelated property). This is the gap worth naming: FR-020's aspect fit, FR-022's
      margin trim, and the 2026-09-01 decision to derive the grid shape from the picture
      are ALL aimed at "the puzzle should look like the picture", and every one of them
      was justified with *proxies* — retained-source-area percentages and blank-border
      counts. Those are inputs to fidelity, not fidelity. The only existing signal is
      FR-014's nudge count, which is partial and indirect: it counts the pixels the
      uniqueness-recovery loop deliberately flipped, and is blind to the far larger loss
      from downsampling, dithering and cropping.
      Cheap concrete form: upscale the dithered grid back to the source's dimensions,
      threshold the (trimmed) original the same way, and report per-cell agreement as a
      percentage. One pure function over two images, no new dependency, inside ADR-0006's
      baseline.
      What it would buy: (a) a user could choose a size knowing what it costs — "20x20
      recovers 91% of your picture, 25x25 recovers 96%" — which is exactly the question
      a person feeding in their own photos actually has; (b) it would retroactively
      validate, or contradict, all three of the 2026-09-01 design decisions, which
      currently rest on argument plus proxy measurements; (c) it gives the difficulty
      retune below a second axis, since a puzzle can be hard AND unrecognizable, and
      those should not be conflated.
      Note `docs/monogram_analyzer.md` deliberately declined to auto-compute "quality"
      because that brainstorm gave no algorithm for it. This item is narrower and does
      have one: not "is this a good puzzle" but "how much of the picture survived".
                                                                                @feature

- [ ] **Elaborate how difficulty is measured** — deepen the signals, not just retune the
      numbers. Distinct from the Wave 7 retune item above, and they should not be
      confused: that one keeps today's formula and moves its weights/cutoffs (Hard is
      unreachable — measured ceiling ~43 against a floor of 66); this one is about the
      formula being thin in the first place. Today's score is five weighted solver
      signals — backtracking 0.45, line logic 0.40, size 0.15, clue density 0.15, solve
      time 0.15 (`src/nonogram/difficulty.py`, ADR-0005/ADR-0013) — and solve time is
      the only one that varies with the machine rather than the puzzle, which is why it
      is weighted lightest.
      **The elaboration is already specified and does not need designing.** 12 intake
      lines derived from `docs/monogram_analyzer.md` were written into
      `meta/architecture/inputs/raw-requirements.md` on 2026-08-30 (currently around
      L65-L76) and were never formalized into `requirements.yml` — verified 2026-09-01.
      They cover: six-level technique classification with a histogram, branching /
      ambiguity tracking, information gain per deduction, a separate non-fail-fast
      search pass for backtracking statistics, dependency depth and bottleneck
      detection, clue-density statistics, grid symmetry, and image-complexity metrics.
      So the next step is an architect delta over those existing lines, not a
      brainstorm.
      Two decisions already recorded in that same intake and worth preserving when it is
      picked up: (a) all of it lives behind a NEW on-demand entry point (e.g. `nonogram
      analyze`) run against an already-generated puzzle — none of it runs during
      `generate`, and none of it is bound by NFR-001's generation-time budget; (b)
      FR-009's existing score and the Easy/Medium/Hard resample loop are unchanged by it
      — every new signal is an additive diagnostic, not wired into tier selection. That
      second one is what keeps this from being a risky change to a shipped mechanism.
      Also recorded there: difficulty, complexity and quality should be three
      independent outputs rather than one conflated score, and "quality" was
      deliberately left uncomputed because that brainstorm gave no algorithm for it —
      the picture-fidelity item above is the narrower, answerable slice of exactly that
      gap.                                                                     @feature

- [ ] **Three hard-coded cell-size modes, replacing the comfort table** — NFR-005's
      curve was tailored for seniors; the owner's judgement (2026-09-01) is that 9mm and
      8mm are too big, ~7mm is the better default, and a free-form `--cell-size MM` flag
      is overkill for today. Three named modes instead.
      **Measured on A4 (5 puzzles per size at 45% density, comfort cap lifted to expose
      pure page-fit, 2026-09-01) — cell size and grid size are NOT independent:**

      | target cell | largest grid A4 can actually deliver it on |
      |---|---|
      | 9mm | 14x14 |
      | 8mm | 16x16 |
      | 7mm | 19x19 |
      | 6mm | 22x22 |

      Past 22 cells a side, nothing yields more than 6mm. Pure page-fit runs 12.36mm at
      10x10 down to 4.57mm at 30x30.
      **The consequence to accept before building three of anything: the modes produce
      IDENTICAL output for any grid of 20 or more**, because page-fit takes over above
      each threshold and they converge. They bite only on grids <= 19. That is still
      worth having — it is most of the small-grid range — but it must not come as a
      surprise when `large` and `standard` render the same 30x30.
      **Shape:** each mode is ONE target number and page-fit clamps it —
      `cell = min(mode_target, page_fit)`. Suggested values: `large` 9mm (the current
      senior-oriented intent, kept as an option rather than the default; real to 14x14),
      `standard` 7mm (the new default; real to 19x19), `compact` 5.5mm (grid big, cells
      small, for people who prefer that trade).
      **The most valuable half — report when the mode does not get what it asked for.**
      e.g. "large cells requested (9.0mm); this 25x25 prints at 5.4mm — A4 cannot do
      better. A 14x14 would print at 9.0mm." This is the same idiom the project already
      uses for FR-021's aspect refusal and FR-014's nudge count: turn a silent
      degradation into a message. It tells the user the one thing they cannot work out
      themselves — that their GRID is why their cells are small.
      **Bonus, and it settles an earlier question: the five-point `CELL_COMFORT_MM` table
      can be deleted entirely.** Page-fit is already a declining function of the larger
      dimension (12.36 -> 4.57mm), produced by geometry rather than by a hand-tuned
      table; the comfort cap's only real job is stopping a 10x10 from printing 12mm
      cells. So `min(mode_target, page_fit)` satisfies NFR-005's "declining function"
      BY CONSTRUCTION. This is therefore not a revert of CARD-025 to a flat cap (the
      framing considered and discarded on 2026-09-01) — it replaces a table with the
      constraint that was doing the work anyway.
      **Subtlety to verify rather than assume:** page-fit varies per PUZZLE, not just per
      size, because it depends on clue-gutter depth — a sparse 20x20 may page-fit
      slightly larger than a dense 19x19. EC-008's non-increasing property may need to be
      stated over the mode target rather than the realized value. Exactly the kind of
      thing that passes review and fails a property test later.
      **Sequencing:** batch with the `--size N` semantics decision now gating CARD-027.
      Both change printed output and both touch NFR-005 territory; one architecture pass
      avoids revising the same area a third time in a week.                    @feature

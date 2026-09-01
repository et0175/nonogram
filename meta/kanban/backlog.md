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
- [x] **Decision needed:** a non-ASCII `--name` (e.g. `кот`, `café`) renders as `.notdef`
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
      Resolved 2026-09-01: option (a) taken — ADR-0006 revised to admit a bundled
      TTF as package data (dependency set unchanged), implemented by CARD-032.
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

- [ ] **A 40x40 "advanced" grid mode — image and library sources only** — supersedes the
      three-cell-size-modes idea, which the owner cancelled on 2026-09-01 in favour of
      this. Raise the supported range so an advanced user can ask for 40x40, printing at
      **3.30mm** per cell on portrait A4 (measured).
      **Feasibility is source-dependent, and that is the whole design constraint**
      (measured 2026-09-01, 45s deadline): a 40x40 derived from a picture (eagle, cat,
      img_2, wolf_face) verifies unique in **0.00-0.04s**, while a 40x40 random grid at
      45% density **times out with no verdict**. A structured silhouette has long runs
      and large uniform regions so line-logic alone cracks it; random mid-density noise
      is the solver's pathological class (CLAUDE.md already names 40x40+ random as
      known-hard). So the mode is **image/library only** — offering it for random would
      ship a request that cannot complete.
      **The uncomfortable adjacent finding: random mode already fails INSIDE today's
      range.** Same measurement, 3 seeds each at 45%: 20x20 solves in 0.02-0.08s; 25x25
      gives 1.60s / 0.08s / TIMEOUT; 30x30 gives TIMEOUT / TIMEOUT / 2.14s; 35x35 and up
      always time out. Corroborated the same day by CLI runs, where 5 of 8 `nonogram
      generate` invocations failed with "abandoned after 20 regenerations" or "solver
      passed its generation deadline". CON-011's "10..30 inclusive, every source mode"
      is therefore **nominal for random** — it genuinely works to about 20-25. This item
      does not cause that gap, it makes it impossible to ignore; the range should
      probably become source-dependent rather than one number for all three modes.
      **Pair it with page orientation.** A 40-wide grid is exactly the case that suffers
      most from the fixed portrait page and gains most from turning it (measured, pure
      page-fit): 40x20 prints 3.39mm portrait vs 5.00mm landscape (+47%); 45x25 3.05 vs
      4.40 (+44%); 60x10 2.29 vs 3.39 (+48%); tall grids prefer portrait (20x40 4.91 vs
      3.22). Matching the sheet's orientation to the grid's recovers ~45% of cell size on
      every rectangle, and it is one conditional in `layout.py` — the geometry is already
      there.
      **Two corrections to shipped prose this work should carry** (both measured
      2026-09-01): CON-011 justifies capping at 30 with "beyond about 30 cells a side the
      printed cell drops under ~6mm" — but 6mm is actually crossed at about **22** cells,
      and a 30x30 prints at 4.40-4.57mm, well under the threshold its own rationale
      invokes. And for reference, the theoretical A4 ceiling is about **70x70**, where
      page-fit reaches the 2.0mm `MIN_CELL_MM` floor; past that the cell pins at 2.03mm
      and the page grows beyond A4 instead.
      See also the NFR-005 entry below — that one is a trap sitting in CARD-027's path
      and should be resolved with, or before, this.                            @feature

- [ ] **NFR-005's "declining function of max(width, height)" is not a valid model for
      rectangles, and EC-008 is ill-posed because of it** — measured 2026-09-01. A 40x20
      and a 20x40 have the SAME `max(width, height)` of 40 and print at **3.39mm** and
      **4.91mm** on portrait A4. So printed cell size is not a function of
      `max(width, height)` at all: on a fixed-orientation page width and height are not
      interchangeable, because 40 columns fight the 210mm axis while 40 rows get the
      297mm one. A 40x20 even prints smaller cells than a 30x30 despite having fewer
      cells (800 vs 900).
      **Why this is urgent rather than merely wrong:** EC-008's property test
      `PropertyTest_Layout_CellSizeNonIncreasingInLargerDimension` is currently safe only
      because every grid this tool can produce is square. **CARD-027 introduces
      rectangles**, so it is the card that walks into this, and it is already cut and
      gated. The finding is also written into CARD-027's `## Architecture revision`
      section so whoever picks it up meets it there rather than in a review cycle.
      Fix direction: state the property over the term that actually binds (cells along
      each page axis), not over `max()`; and/or choose page orientation from the grid's
      shape, which makes the two axes symmetric again and is worth doing regardless
      (~45% bigger cells on every rectangle — see the 40x40 entry above).    @tech-debt

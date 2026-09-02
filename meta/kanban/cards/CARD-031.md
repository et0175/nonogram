# CARD-031: Image-mode puzzles auto-name from the source file's stem

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/031-image-mode-name-from-file-stem
**Worktree:** ../PythonProject4-card-031
**Source:** meta/architecture/handoff.md#increment-6
**Idea:** —
**Wave:** 19
**Depends on:** CARD-027
**Touches:** src/nonogram/orchestrator.py, tests/test_naming.py
**Review score:** 9.5 (cycle 1, gate passed first time)
**Started:** 2026-09-02T12:20:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`NameContext._auto_name` currently returns the library key for library-sourced puzzles
(AC-043) and otherwise falls through to `export.default_stem`'s
`<mode>-<YYYY-MM-DD>-<HHMM>`. Add the image-mode arm: an image-sourced puzzle with no
`--name` auto-names from the **source file's stem**, exactly as the library arm names from
its key. `cat.png` yields `cat`.

Mirror the existing library arm rather than inventing a parallel mechanism — including its
collision posture: ADR-0016 already states an auto-generated key like `"cat"` is not
guaranteed unique, and ADR-0017's export-time suffix is what resolves a collision. Two
puzzles from the same picture are two renderings of one picture, not a same-minute
accident, so they should behave exactly like two `"cat"` library puzzles do today.

A missing or unreadable file still falls through to the timestamp name, exactly as a
missing library key does — the run then fails in sourcing with the error that request
deserves, not a naming error.

## Acceptance criteria

- **AC-090** (happy) — test: `TestPuzzleName_AutoGeneratesFromImageFileStem`
  - **given** an image-mode generation request uploading a file named "cat.png" with no --name flag
  - **when** the puzzle is created
  - **then** the puzzle's name is auto-generated as "cat", not the "image-2026-09-01-1240"-shaped mode+timestamp default

## Guardrails

- G-1: AC-043's library-key naming is unchanged (test: `TestPuzzleName_AutoGeneratesFromLibraryKey`)
- G-2: AC-042's `<mode>-<date>-<time>` default still applies to random mode, and to image
  mode when the stem is unusable (test: `TestPuzzleName_AutoGeneratesModeTimestampForRandomMode`)
- G-3: AC-044/AC-045 unchanged — an explicit `--name` is still kept verbatim and an empty
  one still rejected inward of argparse. This card changes only the *auto-generated* default.
- G-4: Filename sanitization is untouched. `_filename_stem` is already Unicode-aware and
  passes `кот` through verbatim; a Cyrillic stem must keep reaching the filesystem
  unmangled. How such a name RENDERS in the PDF header is CARD-032's, not this card's.
- G-5: Do not edit `src/nonogram/sourcing/image.py` — owned by CARD-030 this wave
- G-6: Do not edit `src/nonogram/export/**` or `pyproject.toml` — owned by CARD-032
- G-7: Out of scope — the `<name>-<WxH>-<difficulty>.pdf` filename shape is DEC-026, held
  open until CARD-027 merges.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static asse... (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no doma... (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "si... (check: review-lens)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the othe... (check: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness... (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate... (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-lo... (check: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both ... (check: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded fil... (check: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never ex... (check: TestNudge_ReportsFailureAtCap, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-004 — A puzzle's grid width and height each lie within 10..30 cells inclusive, in every source mode and at every point in its regenerate/resample/nudge lifecycle (US-016, CON-011... (check: TestGenerateRandom_AcceptsMaxSide30, TestGenerateRandom_RejectsSideAbove30, TestGenerateRandom_RejectsSideBelow10)

## Architecture context

- **FR:** FR-015
- **NFR:** —
- **ADR:** ADR-0016, ADR-0017, ADR-0018
- **Components:** COMP-002
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- **[Env]** forge 2026.8.17 (project requires >= 2026.8.17 — skew gate passed).
- **[Dependency gate]** CARD-027 `done` (merge 632fd18) — the only dependency.
- **[Drift gate]** ⚠ warn, dismissed on inspection for the THIRD consecutive card:
  `orchestrator.py` appears in seven unprocessed `meta/drift-pending.yml` events, whose
  heads are 6a73512, a0798a2 and 197e7fa — all this project's own commits, the last one
  written this morning by the CARD-027 close. The gate is reporting forge's own
  bookkeeping as unreconciled external change. Filed to the backlog: a gate that fires
  on every card is one that gets ignored, and it will be ignored on the card where the
  drift is real.
- **[Stale guardrail, harmless]** G-5 says `sourcing/image.py` is "owned by CARD-030 this
  wave". CARD-030 merged (9424603) before this card started, so the exclusion is now
  historical rather than live. It still stands as scope guidance — this card has no
  reason to touch that file.
- **[G-7 is now decidable, but still not this card's]** G-7 holds DEC-026 (the
  `<name>-<WxH>-<difficulty>.pdf` shape) open "until CARD-027 merges". CARD-027 has
  merged, so the blocker named in the guardrail is gone. The decision is now takeable at
  the architect station; it is NOT taken here, and this card must not implement it.
- **[Implemented]** Added one arm to `NameContext._auto_name`
  (`src/nonogram/orchestrator.py`), between the library-key arm and the
  mode+timestamp fallback: `if request.mode == sourcing.IMAGE and request.image and
  request.image.stem: return request.image.stem`. Mirrors the library arm exactly —
  same collision posture (no disambiguation; ADR-0017's export-time suffix resolves a
  collision), same "falls through on a missing/unusable value" shape. Reads the path
  syntactically only (`Path.stem`, no filesystem access), so an unreadable or
  nonexistent file is still named from its stem and fails later in `sourcing.image`
  with `UnreadableImage` — a naming error is never raised. Only a `None` image or a
  path with no filename component (`Path(".").stem == ""`) falls through to the
  timestamp default.
- **[Tests]** `tests/test_naming.py`: added the AC-090 happy-path test
  (`test_puzzle_name_auto_generates_from_image_file_stem`, full `generate()` call
  with a scripted source and a `tmp_path / "cat.png"` image path — file need not
  contain real image data since naming never reads it), a no-counter companion test
  mirroring AC-043's, and a G-2 regression test for the unusable-stem fallback
  (`test_puzzle_name_auto_generates_mode_timestamp_for_image_mode_with_an_unusable_stem`,
  using `Path(".")`). Updated the module's AC/test-id docstring mapping and one
  pre-existing docstring (`test_the_auto_name_names_the_mode_it_was_generated_in`)
  that overclaimed "CARD-015 has not landed a grid source" — CARD-030 has, since.
- **[Mutation proof]** Disabled the new arm (`if False and request.mode ==
  sourcing.IMAGE and ...`), reran `tests/test_naming.py -k image_file_stem`: both new
  happy-path tests failed as expected (`'image-2026-08-27-1430' == 'cat'`). Reverted;
  `git diff src/nonogram/orchestrator.py` matches the intended diff exactly (no leftover
  mutation).
- **[Full suite]** 1476 passed, 1 xfailed (baseline 1473 passed, 1 xfailed; net +3
  tests, no regressions).
- **[Guardrails]** G-1, G-3, G-4, G-5, G-6 untouched by construction (no edits to the
  library arm, argparse, `_filename_stem`/sanitization, `sourcing/image.py`, or
  `export/**`). G-2's random-mode and empty-key paths are unchanged; its image-mode
  extension (fallback on an unusable stem) is now covered by a new test, above. G-7
  (DEC-026, the PDF filename shape) not implemented, per instruction.

- **[Orchestrator probe, pre-review]** The naming arm was exercised directly across path
  shapes before the review was launched, to see what `Path.stem` actually yields:
  `cat.png` -> `cat`; `pictures/sub dir/wolf_2.png` -> `wolf_2`; `кот.png` -> `кот`
  (G-4 holds, verbatim); `cat` -> `cat`; `.` -> falls through to the timestamp; `None` ->
  falls through. Two edges are worth a reviewer's judgement rather than a silent pass:
  `cat.tar.gz` -> `cat.tar` (plain `Path.stem` semantics, strips only the last suffix),
  and `.hidden` -> `.hidden`, which would name an output file with a leading dot and so
  hide it on Unix. Neither is in AC-090 and neither is obviously wrong; both are recorded
  so the decision is visible rather than inherited.

- **[Cycle-1 findings, both fixed]** F-001: the module docstring in `tests/test_naming.py`
  still said image mode "has no grid source yet (CARD-015)" — false since CARD-015, and
  the implementation pass had corrected the identical sentence one function away at line
  192 while missing this one. A half-fix inside a file the diff already edited, which is
  the family's signature. F-002: this card's own G-1 and G-2 cited
  `TestPuzzleName_UsesLibraryKeyVerbatim` and `TestPuzzleName_AutoGeneratesModeTimestamp`,
  **neither of which exists anywhere in the repo**; the real ids are
  `TestPuzzleName_AutoGeneratesFromLibraryKey` and
  `TestPuzzleName_AutoGeneratesModeTimestampForRandomMode`. A decompose-time defect in
  unchanged context, not the implementer's — the guardrails themselves hold. Both
  corrected here rather than carried, because both are false statements rather than
  missing durability, and correcting prose does not change the tree the review passed.

## AC/EC gate (2026-09-02)

**Verdict: PASS.** One acceptance criterion, no engineering constraints. AC-090's test
drives the full `generate()` pipeline and asserts `puzzle.name == "cat"` for an
image-mode request uploading `cat.png` with no `--name` — which settles both halves of
the criterion at once, since equality with `"cat"` excludes the
`image-<date>-<time>` default the `then` contrasts it against. Mutation-verified twice
(by the implementer and again independently): disabling the arm fails this test and its
no-counter sibling, and `orchestrator.py` restores to md5
`28169d7c6a7f3e44866ca8c9e69e1754`.

Guardrails were checked as criteria rather than assumed, since G-1 and G-2 name tests:
both hold, and both of their references were **dead as written** — corrected under F-002.

[AC/EC check] All criteria/constraints ✓ (evidence: AC-090 test_puzzle_name_auto_generates_from_image_file_stem, supported by test_puzzle_name_auto_generates_from_image_file_stem_without_a_counter for the collision posture and test_puzzle_name_auto_generates_mode_timestamp_for_image_mode_with_an_unusable_stem for G-2's image-mode fallback; G-1 test_puzzle_name_auto_generates_from_library_key; G-2 test_puzzle_name_auto_generates_mode_timestamp_for_random_mode; no engineering constraints on FR-015 for this card; suite 1476 passed, 1 xfailed) — all five names resolved to exactly one `def` before this line was written; verified on 2026-09-02.

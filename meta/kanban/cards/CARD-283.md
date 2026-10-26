# CARD-283: The public player page — the admin game served static, with no answer in the browser

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/283-public-player-page
**Worktree:** —
**Source:** ONLINE_GAME_SPECIFICATION.md#technical-architecture (owner decision 2026-10-23, commit 8b0ca0e2: one player app, routes /play/<key>, /b/<slug>, /library); backlog.md "A public online solver" @enabler
**Idea:** —
**Wave:** 61
**Depends on:** CARD-282
**Touches:** player/**, tests/test_public_player.py
**Review score:** 7.0 (cycle 3/3) — NOT CERTIFIED; all findings closed in round 6 of 6, that round uncertified by budget exhaustion; merged on a recorded gate decision
**Started:** 2026-10-26
**Closed:** 2026-10-26
**Actual:** 1.0d
**Merge commit:** 1b706f1b
**Blocked by:** — (was: the CON-021 / ADR-0038 reopen — landed 2026-10-23: CON-021 amended to the two-player form, ADR-0038 carries a dated amendment with R6 unchanged, ADR-0041 governs the public surface; unblocked the same day)

## What to implement

The game itself, as a **static page** — the spec's key decision is ONE player
app serving both the book QR codes and online browsing, hosted statically so a
QR scan never waits on a cold start and customer traffic never touches the
admin service. This card builds the `/play/<key>` route; CARD-284 adds the two
entry pages around it.

1. **A new top-level static-site directory `player/`** (plain HTML/JS/CSS — the
   stack ADR-0038 already chose for the player; no framework, no build step
   beyond file copying, nothing added to the Python package). It is not a
   Python module and must not live under `src/nonogram/`.
2. **`/play/<key>`**: fetch `puzzle/<key>.json` from the CARD-282 bundle,
   render the board — clue boxes left and above, every fifth line heavier, the
   header with title and tier — and the marking behavior the admin player
   already has: three cell states, drag along the first-move line, undo/redo,
   reset, region marking. **Reuse, don't fork:** the board state lives in the
   admin player's pure module (`solver_state.js`, split out by CARD-160 for
   exactly this reuse); serve the same file via a build-time copy from
   `src/nonogram/admin/static/`, with a test asserting the served copy is
   byte-identical to the source. UI glue that assumes Flask templating is
   rewritten in `player/`, not shared.
3. **Completion without the answer.** The page never has the solution
   (ADR-0038/R6), so "solved" is detected as *every row and column clue
   satisfied* — for a uniquely-solvable puzzle that is exactly the solution.
   The admin player's error COUNT (CARD-162) needs the answer and is therefore
   **not** in this card's scope — if the owner wants it publicly, that is a new
   architecture question, not a worktree decision.
4. **Play state** is kept in this browser's localStorage only (the shape
   CON-021's 2026-10-06 amendment allows for the admin player): resume on
   reload, nothing sent to any server, no accounts.
5. **Mobile-first.** Nearly every QR scan is a phone: thumb-sized tap targets
   (backlog already tracks "~18 px at 390 px" as too small on the admin page),
   pinch-zoom, clues sticky while panning. Desktop keyboard controls match the
   admin player where they exist.

## Acceptance criteria

FR-045 (registry entries minted by the 2026-10-23 architect delta, ADR-0041).

- AC-383: Given a bundle puzzle JSON, when `/play/<key>` loads, then the board
  renders that puzzle's grid and clues and cells can be marked through the
  three states with undo/redo, with the same state transitions as the admin
  player's `solver_state.js` (test: tests/test_public_player.py::
  test_play_page_renders_and_marks — Playwright over a static file server).
- AC-384: Given a board where every row and column clue is satisfied, when the
  last mark lands, then the page shows the solved state; given one wrong cell,
  it does not (test: tests/test_public_player.py::
  test_solved_fires_on_clue_satisfaction_only).
- AC-385: Given a partially solved puzzle, when the page reloads, then the marks
  are restored from localStorage, and no network request was ever issued other
  than fetching the page's own static assets (test: tests/test_public_player.py::
  test_resume_is_local_and_the_page_writes_nowhere).
- AC-386: Given a 390 px-wide viewport and the largest supported grid
  (limits.MAX_SIZE per side), when the page renders, then the board is
  playable: cells reachable, clues legible, no horizontal page scroll (test:
  tests/test_public_player.py::test_phone_viewport_is_playable).

## Engineering constraints

- EC-048 (ADR-0038/R6, ADR-0041/R2): no asset served by the public player —
  HTML, JS, JSON, anything in `player/` or the bundle — contains a solution
  grid or data from which one cell of it can be read, for any puzzle, not just
  AC-384's examples.
  test: tests/test_public_player.py::test_served_tree_is_clean_of_answers
- EC-050 (CON-021 as amended, ADR-0041/R4): play state persists in this
  browser's localStorage only — for every interaction sequence, zero write
  requests leave the page.
  test: tests/test_public_player.py::test_no_write_request_for_any_interaction

## Guardrails

- G-1: The admin player is behavior-unchanged: src/nonogram/admin/static/solver.js,
  solver_state.js, admin.css, templates/puzzle_solve.html are read (copied), never
  edited (test: existing tests/test_puzzle_solver_page.py suite green).
- G-2: Do not edit src/nonogram/** at all except nothing — this card's code is
  the `player/` tree and its tests; the bundle format is CARD-282's and is
  consumed as-is.
- G-3: The runtime dependency baseline stays closed (ADR-0006/R1) and
  pyproject.toml gains no runtime dependency; test tooling reuses the existing
  pytest-playwright dev extra (test: tests/test_export_pdf.py::
  test_the_dependency_baseline_is_still_closed).
- G-4: Out of scope — error count, hints, scores, accounts, any server-side
  write (ONLINE_GAME_SPECIFICATION.md defers the write API to the December
  features; CON-021 forbids it today).

## System contract

- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. (check: review-lens)
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. (check: review-lens)
- ADR-0039/R1 — A set a guard consults needs a completeness test written before the set, and any claim the guard makes about what it catches needs a control that can fail: caught WITH the set member present, missed WITHOUT it. (check: test_the_control_for_each_spelling_depends_on_the_set)
- ADR-0039/R2 — A guard's set is derived from an authority the runtime can enumerate, not hand-written. (check: test_the_guard_sets_are_derived_and_not_hand_written)
- ADR-0039/R3 — An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT absorb — caught with the exemption removed, missed with it in place — is held to an equality against the sites that exist ... (check: test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw)
- ADR-0041/R1 — A puzzle's public key is the first 10 lowercase hexadecimal characters of SHA-256 over the UTF-8 bytes of "{width}x{height}:" followed by the solution grid's cells row-major, '1' for filled and '0' for empty. (check: tests/test_player_bundle.py::test_bundle_tree_and_clues_match_the_encoder)
- ADR-0041/R2 — No public asset — nothing in player/, nothing in the exported bundle, nothing the assembled site serves — carries a solution grid or data from which any solution cell is recoverable, for any puzzle, on any export path. (check: tests/test_player_bundle.py::test_bundle_is_clean_of_answers)
- ADR-0041/R3 — The public player is static files only: plain hand-written JavaScript and CSS in the top-level player/ directory, no framework, no build toolchain, no npm, nothing added to the Python package. (check: review-lens)
- ADR-0041/R4 — The public player keeps play state in the visitor's browser localStorage only. (check: tests/test_public_player.py::test_no_write_request_for_any_interaction)
- ADR-0041/R5 — The player bundle is exported by an explicit admin-panel action, is read-only against the database (no INSERT/UPDATE/DELETE on any export path), takes its clues from compute_clues of the stored grid (the one encoder),... (check: tests/test_player_bundle.py::test_export_is_readonly_and_deterministic)
- ADR-0041/R6 — Nothing we ship stores, reads or transmits a visitor's IP address or any per-visitor identifier. (check: tests/test_public_player_pages.py::test_no_homegrown_tracking)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form r... (check: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. (check: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an e... (check: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-021 — Interactive play exists in exactly two forms. (check: review-lens)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: TestExport_RejectsUnverifiedPuzzle, ...)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never exceeds its configured maximum bound (NFR-002). (check: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, ...)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, ...)
- INV-006 — A puzzle whose cell on the book's trim is below the cell floor (TERM-024, 4.75 mm since 2026-10-17) is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR-008). (check: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, ...)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, ...)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: TestBookPublished_ConfirmedPuzzleChangeApplied, ...)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement, changed only by an explicit move inside that leve... (check: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, ...)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm), each under its own band; pairing never changes ... (check: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, ...)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4... (check: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, ...)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038;... (check: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, ...)
- INV-013 — The book's interior PDF holds no cover page and starts at the book's title / copyright page as a right-hand page 1 — no folio, no ink — with the guide following as a facing spread on pages 2 (verso) and 3 (recto); eac... (check: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, ...)

## Architecture context

- **FR:** FR-045 (AC-383..386; FR-044 defines the admin player whose behavior
  this page mirrors)
- **ADR:** ADR-0041 (the public surface: R2 no-solution, R3 static-only +
  byte-identical state-module copy, R4 localStorage-only), ADR-0038 (plain-JS
  player + Playwright; R6 shapes completion detection), ADR-0006
- **Components:** COMP-011 (Public Player)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md, tokens.css, components.md
- **UI components:** the player board as merged by CARD-160..162 (reuse its
  look: clue boxes, fifth-line rule, header badge); register the public page in
  components.md
- **Screens:** /play/<key>
- **Standards:** forge:engineering-standards §11 (tokens-only styling, states,
  a11y minimum)

## Worktree notes

—

### What was built

`player/` (new, greenfield, outside the Python package — ADR-0041/R3):

| file | what it is |
|---|---|
| `play.html` | the `/play/<key>` page: an empty frame, no puzzle, no answer |
| `play.js` | the glue — fetch, draw, input, solved check, localStorage save |
| `player.css` | mobile-first styling, tokens only, no colour literal |
| `vercel.json` | the host's rewrite `/play/:key` -> `/play/index.html` |
| `assemble.py` | the site assembler, and where EC-048 is closed |

Board state is **not** reimplemented: every transition goes through
`solver_state.js` (`clickStroke`, `dragStroke`, `resetStroke`, `record`,
`undo`, `redo`, `clickedState`, `gesturePaints`, `nextRegion`), served as a
byte-identical build-time copy of `src/nonogram/admin/static/solver_state.js`.
`tokens.css` travels the same way. Nothing under `src/` was touched at all
(G-1, G-2 — `git status` shows only `player/` and `tests/test_public_player.py`).

What the page has: clue gutters left and above with every fifth rule heavier,
three cell states on repeat taps, drag along the first-move line, Region,
undo/redo/reset, Ctrl/Cmd-Z, resume from localStorage, solved from clue
satisfaction. What it deliberately has not: error count, hints, progress
percent (all need the answer — G-4), and no analytics tag (F-3 below).

### How "no shipped field decodes to the grid" was established

CARD-282 cycle 2 routed a measured leak here: a stored `puzzle_name` that is
the base-64 of its own grid is published in the bundle's declared `title`, and
every provenance guard passes because "a stored title" is a named good source.
**A scan cannot answer this** — the set of encodings of a grid is not
enumerable, and CARD-282's own denylist missed 7 of 7 planted encodings. So
this card does not filter the channel, it removes it:

1. **Canonical rebuild (the guarantee).** `assemble.py` rebuilds every served
   `puzzle/<key>.json` from `SERVED_SCHEMA = (clues, height, key, tier,
   width)`. `title` is not in it and does not reach the site; a field the
   schema does not name is dropped and named in the report. The served bytes
   are held to a byte-for-byte rebuild from (key, extent, tier, clues) alone,
   so there is no spare room in the file at all.
2. **Enumerated domains, and a capacity figure that says what it covers**
   (rewritten in the cycle-1 fix round; the first version of this paragraph
   was measurably wrong — see "Cycle 1 fix round" below). `clues` and `key`
   are ADR-0041's two sanctioned projections (R5, R1) and are **exempt by the
   ADR**, not by anything the assembler measures: the clue field's own
   capacity is ~143 bits at 10x10 and `_clues` accepts clue sets no grid
   realises, so the integrity of those values is ADR-0041/R5's, upstream in
   the exporter. Every other served value is drawn from a domain the
   assembler enumerates, and two of the three are not free at all: `width`
   and `height` are refused unless they equal the lengths of the served clue
   axes, so a reader recomputes them. What is left is the `tier`, whose
   domain is the runtime's three-label tier enum. `check_capacity()` refuses
   to assemble unless every served name is either exempt or counted and the
   counted total is strictly below `MIN_SIZE**2` bits. Derived by the
   deployed code, not transcribed: `python player/assemble.py --capacity`
   prints **2.00 bits** (width 0.00 + height 0.00 + tier 2.00) against the
   **100-bit** trip-wire. That ceiling establishes only "no served field is
   wide enough to carry a grid" — **not** EC-048, whose threshold is one
   cell, which no capacity bound can reach while any field has a choice. The
   residual is named rather than implied: two bits of tier label a hostile
   store could choose by the answer. Closing it means not serving the tier,
   which is ADR-0041's decision, not a worktree one.
3. **Decoding sweep (the belt), with a live control.** `decoded_recoveries`
   folds five cell alphabets onto 1/0 and runs base64/base64url/base32/base85/
   hex over every token of at least 15 characters, matching eight readings of
   the grid (row/column major, each forward, reversed and complemented). The
   exempt fields are redacted first, so the game is not reported as a leak.
   **The same sweep runs over the bundle the site was assembled from and must
   find the grid there** — every fixture title is base-64 of its own grid,
   CARD-282's measured shape, 12x12 included. Dirty in, clean out, one scan:
   a sweep that had quietly stopped working cannot report this as a pass.
4. **Static invariance.** Assembled twice from two disjoint corpora, every
   asset but `puzzle/<key>.json` is byte-identical, with a planted difference
   proving the comparison can fail.

Stated bound, not closed: the clues determine the solution of a uniquely
solvable puzzle. That is the game, not a leak (ADR-0041's Context), and the
premise is measured against the real solver rather than asserted —
`test_every_fixture_puzzle_is_uniquely_solvable`.

### ACs and the node id verifying each

| AC / EC | node id (all in `tests/test_public_player.py`) |
|---|---|
| AC-383 | `test_play_page_renders_and_marks` |
| AC-384 | `test_solved_fires_on_clue_satisfaction_only` |
| AC-385 | `test_resume_is_local_and_the_page_writes_nowhere` |
| AC-386 | `test_phone_viewport_is_playable` |
| EC-048 | `test_served_tree_is_clean_of_answers` (+ `test_the_served_puzzle_files_are_rebuilt_not_copied`, `test_the_title_is_dropped_on_every_puzzle_and_named_in_the_report`, `test_the_capacity_bound_is_derived_and_can_fail`, `test_the_static_half_of_the_site_does_not_vary_with_the_puzzles`, `test_the_page_carries_no_answer_and_no_third_party_asset`) |
| EC-050 | `test_no_write_request_for_any_interaction` |
| G-1 / R3 | `test_the_state_module_and_tokens_are_byte_identical_copies` |
| G-3 / R3 | `test_the_runtime_dependency_baseline_is_untouched`, `test_the_player_tree_is_static_and_adds_nothing_to_the_package` |

23 tests, 23 passed, 0 skipped (`-m browser` selects 7). The suites that could
notice this card: `test_cli.py`, `test_guard_integrity.py`,
`test_suite_profile.py`, `test_collected_names.py` (585 passed),
`test_player_bundle.py` + `test_suite_profile.py` (503 passed),
`test_puzzle_solver_page.py` (67 passed, G-1),
`test_admin_design_tokens.py`, `test_export_pdf.py::test_the_dependency_baseline_is_still_closed`.
The full suite was deliberately NOT run: CARD-296 was live in another
worktree, and every run here redirected the lock with
`NONOGRAM_FULL_SUITE_LOCK`.

### Mutation record — 26 mutants, 26 killed, 0 dead

Each mutant deletes the mechanism a control names, runs that control alone,
and the file is restored and verified by sha256.

| mutant | control that redded |
|---|---|
| `served_puzzle` carries `title` through | `test_served_tree_is_clean_of_answers`, `test_the_served_puzzle_files_are_rebuilt_not_copied` |
| the state-module copy gains one byte | `test_the_state_module_and_tokens_are_byte_identical_copies` |
| `index.json` is copied into the site | `test_served_tree_is_clean_of_answers` |
| the two clue axes need not agree on the filled count | `test_a_puzzle_file_the_schema_cannot_accept_is_refused_and_named` |
| a clue longer than its line is accepted | same |
| the file name and the key need not agree | same |
| `check_capacity` is not consulted by `assemble` | `test_the_capacity_bound_is_derived_and_can_fail` |
| the run comparison becomes a per-line total | `test_solved_fires_on_clue_satisfaction_only` |
| the run comparison ignores run order | same |
| the column clues are never checked | same |
| the row clues are never checked | same |
| a `[0]` clue is satisfied by anything | same |
| a "?" note counts as filled | same |
| the phone cell floor drops to 18 px | `test_phone_viewport_is_playable` |
| the clue gutters stop sticking | same |
| the stage stops scrolling (page scrolls sideways) | same |
| the viewport meta forbids pinch zoom | same |
| nothing is written to localStorage | `test_resume_is_local_and_the_page_writes_nowhere` |
| the save is not read back at load | same |
| clicks bypass `clickedState` | `test_play_page_renders_and_marks` |
| a drag marks only its first cell | same |
| the heavier fifth rule is drawn on every line | same |
| one interaction POSTs to a server | `test_no_write_request_for_any_interaction` |
| a malformed key is fetched anyway | `test_an_unknown_or_malformed_key_draws_no_board` |
| a third-party script tag is added | `test_the_runtime_dependency_baseline_is_untouched` |

**Three of them were DEAD on the first pass and the controls were fixed, not
the note.** Worth reading, because two are exactly the family this board
escalates on:

* **the solved rule.** Three separate weakenings of `isClueSolved` (compare
  per-line totals, skip the columns, ignore run order) all left AC-384's test
  GREEN. The reason is structural: on a uniquely solvable puzzle almost every
  wrong board breaks many lines in many ways, so a weakened check still
  rejects it. Two fixes: a wrong board whose every row and column filled COUNT
  is right (one 2x2 rectangle rotated — `_count_preserving_swap`), and a table
  of hand-made clue sets driving the pure function through the served module,
  where exactly one thing is wrong per case. All six solved mutants now die;
* **the malformed key.** The test read the message on the page, and without
  the key-shape check the fetch simply 404s and shows the same message. Now it
  asserts that **no `/puzzle/` request is made at all** for a non-key path,
  with a published-key case as the positive control;
* **a clue longer than its line** was masked by the filled-count rule. The
  added case `clues-no-room` ([5,5] in a 10-cell line, both axes totalling
  100) is refused by the fits-the-line rule and by nothing else.

### Findings — where the brief or the card turned out to be wrong

**F-1 (the brief's premise about the dead refs was wrong, and the fix is not
what it said).** The brief says the four DEAD check refs are fixed by writing
the file, and to verify with `git grep -w <bare name>`. Neither holds. The
validator (`forge/.../validators/utils.py::symbol_exists`) runs
`git grep -lw "<the whole ref string>"` — `split_check_ref` splits on commas
only, so the pattern it searches for is
`tests/test_public_player.py::test_play_page_renders_and_marks`, path and all.
Two consequences the brief did not anticipate:
  * `git grep` reads **tracked** files, so an untracked new test resolves
    nothing. The five files are therefore left **staged** (uncommitted) —
    without that the refs stay DEAD however green the suite is;
  * the string has to appear in a non-`.md` file outside `meta/architecture`
    (those are the validator's only excludes). The card wraps each of
    AC-383..386's refs across two lines, so writing the tests did not revive
    them. Measured: before, 121 warnings with AC-383..386 DEAD; after adding a
    "Tests, by node id" table to the test module's docstring, **117 warnings
    and all four resolved**. The table is not decoration — it is held to the
    registry in both directions by
    `test_the_registrys_check_refs_for_this_card_all_resolve`, so a rename
    reds here instead of going quietly dead in the model.
  * Also observed while measuring this: AC-381's ref resolves today only
    because it appears in `meta/review/*.yml`, which the validator does not
    exclude. That is the matrix self-validating through review artefacts —
    not this card's to fix, but it is the same defect class.

**F-2 (the card's body contradicts its own AC, and the AC is right).** Item 2
asks for "the header with title and tier". The page shows **"Puzzle W x H"
and the tier, never the title**, for two independent reasons:
  * the picture's name IS the answer. That is precisely why CARD-163 took the
    name out of the admin player's header (FR-044 AC-322/AC-323) and left it
    only in that page's solved banner. Showing it on the public page before
    the puzzle is solved is a spoiler, EC-048 aside;
  * EC-048. A title is free text; free text cannot be scanned for an encoded
    grid; so the public surface serves none. This is the answer to the bound
    CARD-282 routed here, and it only works if nothing is served.
AC-383 does not mention the title, so no AC is weakened — this is the body/AC
divergence, resolved in the AC's favour.

**F-3 (ADR-0041/R6 and AC-385 contradict each other; R6's half is deferred to
the card that owns it).** R6 requires a GoatCounter script tag on the player
pages. AC-385 requires that "no network request was ever issued other than
fetching the page's own static assets", and a third-party counting beacon is
such a request. Both cannot hold on this page as written. The tag is NOT added
here: R6's own check ref is `tests/test_public_player_pages.py::test_no_homegrown_tracking`
(CARD-285), which is where the two rules have to be reconciled — and whoever
lands it has to amend AC-385's assertion to "same-origin, plus the one
counting endpoint R6 names", not simply add a tag and watch this test red.
`play.html` carries the note at the top so the absence reads as a decision.

**F-4 (EC-048's registry ref names only half of itself).** FR-045's EC-048
carries one check: `tests/test_player_bundle.py::test_bundle_is_clean_of_answers`
— the bundle half. The card and ADR-0041/R2's own comment both say the served
half is `tests/test_public_player.py::test_served_tree_is_clean_of_answers`,
which now exists. The ref should be the comma-separated pair (the validator
splits on commas). One word of `requirements.yml`, outside this card's declared
Touches, so it is reported rather than edited.

**F-5 (this card's site does not serve `index.json` or `book/<slug>.json`,
deliberately).** Both carry a free-text `title` too, and F-2's answer — serve
no free text — would have to be taken for them as well. A book's title on its
own landing page is a different editorial question from a puzzle's name, and
deciding it here would be deciding CARD-284's and CARD-285's cards. The
assembler names every bundle file it left out in its report, and
`test_the_index_and_book_files_are_not_served_by_this_page` pins it. **Whoever
takes CARD-284 inherits the title question for the library listing**, and
`assemble.py`'s `PLAYER_FILES` / `SITE_PUZZLE_DIR` are where to extend it.

**F-6 (the assembler is a sixth file nobody declared).** The card says "no
build step beyond file copying" and ADR-0041/R3 says "no build toolchain",
while the same rule requires a *build-time* byte-identical copy — which needs
something to make the copy. `player/assemble.py` is that something: stdlib
only, loads `src/nonogram/limits.py` by path rather than importing the package
(so nothing is added to it, and `MIN_SIZE`/`MAX_SIZE` stay single-sourced), not
under `src/`, not in any `package-data` glob, not imported by anything in the
package, and not collected by pytest (`testpaths = ["tests"]`). It is also the
only place EC-048 could be closed without editing `src/nonogram/admin/`, which
this card is forbidden to touch. Named here because it is outside the card's
"plain HTML/JS/CSS" description even though it is inside its declared Touches.

### Not verified, named rather than omitted

* **No render was eyeballed.** Every claim here is a measurement; nobody has
  looked at the page on a real phone. The owner validates visually, and the
  layout decisions (28 px cell floor, sticky gutters, the board scrolling
  inside its stage at 390 px while the page does not) are the kind that read
  as fine in a computed-style assertion and wrong to the eye.
* **The assembler was never run against a real exported bundle**, only against
  fixtures whose field names are derived from `player_bundle.PUZZLE_FILE_FIELDS`.
  A live `export_bundle` -> `assemble` -> deploy pass is still owed, and it is
  the step that would catch a bundle field the fixtures do not model.
* **Vercel was not exercised.** `vercel.json`'s rewrite is applied by the test
  server, which reads that same file rather than hand-coding the route — so the
  rule is exercised, the host is not.
* **Pinch zoom is asserted as "not forbidden"** (no `user-scalable=no`, no
  `maximum-scale`), not as working: Playwright cannot pinch.
* **Chromium only** (ADR-0038/R7). No iOS Safari, which is where most QR scans
  will actually land, and where `position: sticky` inside a scroll container
  and `touch-action` have the most history.
* **EC-050's "every interaction sequence"** is a deterministic sweep over
  every control the page has, then a seeded 24-step walk over the same set,
  plus a reload — not a proof. The exercised set is asserted equal to the
  control set and the control set is held to `play.html`'s own buttons, so a
  reseed or a new control cannot drop a path silently (that equality is the
  cycle-1 fix for F-3; the first version's seeded draw never pressed Reset and
  never dragged). The method and the origin of every request are asserted,
  never a request count alone.

---

## Cycle 1 fix round

Review `meta/review/20261026T062623Z-CARD-283-cycle1.yml` (score 6, three
gating). Handed back uncommitted. Changed: `player/assemble.py`,
`player/player.css`, `tests/test_public_player.py` (and this card).
`player/play.js`, `player/play.html`, `player/vercel.json` and everything
under `src/` are byte-unchanged — every mutation below was restored and
verified by sha256.

**31 tests, 31 passed, 0 skipped** (was 23). Neighbours re-run green:
`test_collected_names.py`, `test_suite_profile.py`, `test_guard_integrity.py`,
`test_cli.py`, `test_export_pdf.py::test_the_dependency_baseline_is_still_closed`
(721 passed together), `test_player_bundle.py` + `test_admin_design_tokens.py`
(109 passed). The full suite was again NOT run (`NONOGRAM_FULL_SUITE_LOCK`
redirected on every run).

### F-1 (gating) — the served `tier` was a real 56-bit channel

Reproduced before touching anything, with the reviewer's own plant: the first
56 cells of `GRIDS["min"]`'s answer as a 12-character base-26 string
(`tqlhkuhxpmgj`) stored in a bundle puzzle's **`tier`**, assembled, read back
from the served `puzzle/<key>.json`:

| | served `tier` | answer cells recovered | `--capacity` | refused | sweep |
|---|---|---|---|---|---|
| before | `tqlhkuhxpmgj` | **56 of 56** | 65.25 bits / 100 | none | clean |
| after | `""` | **0 of 56** | **2.00 bits** / 100 | none | clean |

Two fixes, because the finding was two things:

* **(b) the domain.** `TIER_ALPHABET` / `TIER_MAX_CHARS` (every lowercase
  string up to 12 characters — 56.46 bits, hand-written) are gone. The served
  set is `SERVED_TIERS = ("easy", "medium", "hard")`, the runtime's own
  vocabulary, held to `nonogram.difficulty.Tier` and to
  `nonogram.admin.book_plan.TIERS` from the test tree by
  `test_the_served_tier_set_is_the_runtimes_tier_vocabulary` (ADR-0039/R2;
  `assemble.py` cannot load `difficulty.py` by path the way it loads
  `limits.py`, because that module imports `nonogram.errors` — so it is the
  allow-list-plus-completeness-test form R1/R2 allow, and the cross-check is
  the `propagate.mask_runs` precedent CLAUDE.md names). Capacity fell to
  2.00 bits, derived;
* **(a) the threshold.** The claim "a channel that cannot hold the smallest
  published grid cannot hold any grid" never established EC-048, which forbids
  recovering **any** cell. `assemble.py`'s docstring now says what the ceiling
  does establish ("no served field is wide enough to carry a grid"), that
  EC-048's one-cell threshold is carried by the closed rebuild plus the
  enumerated domains instead, and that the residual is two bits of tier label
  — named, measured, and routed to ADR-0041 rather than claimed closed.
  `check_capacity` also now refuses a schema it has not **partitioned** into
  exempt and counted fields, so the next field added to `SERVED_SCHEMA` cannot
  go uncounted (which is how this one was 56 bits wide).

New: `DETERMINED_BY_CLUES` (`width`←`clues.columns`, `height`←`clues.rows`),
which is why those two count zero bits, with
`test_the_served_extents_are_recomputable_from_the_served_clues` on the served
files and one refusal case per axis.

### F-2 (gating) — the last-column weakening

Two table rows added to AC-384's clue table: `("every row right, the LAST
column wrong", …)` and its row twin. `col < width - 1` and `row < height - 1`
now both red.

### F-3 (gating) — the walk reached neither a drag nor Reset

The seeded draw is now a **deterministic sweep over the control set** followed
by the seeded walk, with `set(exercised) == set(controls)` asserted, and three
controls assert the handler actually ran (the drag marks its line, Region
flips, Reset announces itself). `_drag` is a real pointer drag
(down/move/move/up). The control set is held to `play.html`'s buttons by
`test_every_player_control_is_in_the_ec_050_walk`.

### Non-gating

* **F-4** — closed four of five: `readPayload`'s clue checks and
  `deserialize`'s clue comparison (`test_a_save_or_a_puzzle_file_the_page_
  cannot_trust_is_refused`, each with its positive control), the brush
  binding, Region's one-shot disarm and `touch-action` keyed to Region
  (`test_the_brush_region_and_touch_bindings_are_the_modules`). **Not
  closed:** the pointer-TYPE half of `gesturePaints` (a touch drag with Region
  off pans instead of marking). Playwright has no touch-drag API — only
  `touchscreen.tap` — and a synthetic `PointerEvent` cannot carry a real
  `pointerId`, so the armed positive control would break on
  `setPointerCapture`. The rule itself is `solver_state.js`'s and is covered
  by the admin suite; what is untested here is this page's binding of it, and
  the CSS half of the same behaviour (`touch-action`) now is tested;
* **F-5** — the "clues cannot be borrowed as a free numeric channel" claim is
  deleted from `assemble.py`'s docstring, `_line`, `_clues` and the test
  module's docstring, and replaced with the measurement (144 clues per 10-cell
  line, ~143 bits per 10x10, a clue set no grid realises is accepted) and with
  where the guarantee actually lives (ADR-0041/R5, upstream);
* **F-6** — `sweep_tree`'s second raw-text pass: the sentence is deleted, not
  implemented. Implementing it would read the exempt clue numbers, which is
  the one thing the sweep must not report;
* **F-7** — `assert len(GRIDS) >= 4` (and that the corpus still spans
  `MIN_SIZE`..`MAX_SIZE`) now lives inside
  `test_served_tree_is_clean_of_answers`;
* **F-8** — `check_out_dir` refuses an `--out` holding any top-level name an
  assembled site does not have, refuses the repository root by name, and
  offers `--force`. The entry set is derived from `PLAYER_FILES` /
  `COPIED_FROM_ADMIN` / `SITE_PUZZLE_DIR`;
* **F-9** — the phone floor is read from `player.css`'s own
  `--player-cell-min` **and** the token's value is asserted `>= 28`, so a 25 px
  token reds (it passed before) and so does a layout change that squeezes
  cells below the token;
* **F-10** — the dead `openapi.vercel.sh` disjunct is deleted; `play.js` and
  `play.html` now carry a flat "no `https://`". The exemption moved to
  `vercel.json`, where the URL actually is, as an **equality** against the
  URLs that exist (ADR-0039/R3);
* **F-11** — `.player-stage { width: fit-content; max-width: 100% }`, with
  `test_the_stage_fits_the_board_on_a_wide_screen` reading both the 1440 px
  stage (now the board's width, ±4 px) and the 390 px one (clamped, scrolling,
  page not scrolling). **No render was eyeballed; the owner validates
  visually.**
* **F-12** — `requirements.yml`, outside Touches. Not touched.

### Mutation record — cycle 1 fix round: 25 mutants, 25 killed

Each deletes the mechanism a control names, runs that control, and the file is
restored and verified by sha256.

| mutant | control that redded |
|---|---|
| `_tier` reverts to cycle 1's `^[a-z]{1,12}$` rule | `test_a_tier_outside_the_vocabulary_carries_no_cell_to_the_site` |
| `SERVED_TIERS` gains a label the enum has not | `test_the_served_tier_set_is_the_runtimes_tier_vocabulary` |
| `difficulty.Tier` gains `EXPERT` (src/, restored) | same |
| `check_capacity`'s partition check is deleted | `test_the_capacity_bound_is_derived_and_can_fail` |
| `width`/`height` are counted as free again | same, and `test_the_served_extents_are_recomputable_from_the_served_clues` |
| `_clues`'s row-axis length check is deleted | `test_a_puzzle_file_the_schema_cannot_accept_is_refused_and_named` |
| `_clues`'s column-axis length check is deleted | same |
| `check_out_dir` is not consulted (the measured data loss) | `test_an_out_dir_that_is_not_a_previous_site_is_refused` |
| `isClueSolved` drops the LAST COLUMN | `test_solved_fires_on_clue_satisfaction_only` |
| `isClueSolved` drops the LAST ROW | same |
| a POST planted in the RESET handler | `test_no_write_request_for_any_interaction` |
| a POST planted in the DRAG branch | same |
| a control is dropped from the walk table | `test_every_player_control_is_in_the_ec_050_walk` |
| `play.html` gains a fourth brush | same |
| `readPayload`'s two clue checks are deleted | `test_a_save_or_a_puzzle_file_the_page_cannot_trust_is_refused` |
| `deserialize`'s clue comparison is deleted | same |
| the brush handler ignores the chosen brush | `test_the_brush_region_and_touch_bindings_are_the_modules` |
| Region stops being one-shot on a drag | same |
| the `is-region` class is never toggled | same (`touch-action`) |
| the cell floor token drops to 25 px | `test_phone_viewport_is_playable` |
| the cell floor token drops to 18 px | same |
| the stage loses `width: fit-content` | `test_the_stage_fits_the_board_on_a_wide_screen` |
| an `https://` URL in `play.js` beside the exempted host | `test_the_runtime_dependency_baseline_is_untouched` |
| a second `https://` URL in `vercel.json` | same |
| `GRIDS` shrinks to one grid | `test_served_tree_is_clean_of_answers` |

One mutant was **DEAD on the first attempt and the control was fixed, not the
note**: deleting `_clues`'s column-axis length check left the new
`clues-column-count` case green, because dropping a clue line drops its filled
cells too and the two-axis agreement rule refused the payload first — the same
masking the first round hit with `clues-no-room`. Both length cases are now
built so the length is the only thing wrong (both axes still agree on the
filled count), and both checks die.

### New node ids

| what | node id (all in `tests/test_public_player.py`) |
|---|---|
| EC-048, the tier channel | `test_a_tier_outside_the_vocabulary_carries_no_cell_to_the_site` |
| ADR-0039/R2, the tier set | `test_the_served_tier_set_is_the_runtimes_tier_vocabulary` |
| the tier rule | `test_the_tier_is_narrowed_to_the_vocabulary_or_dropped` (renamed) |
| the zero-bit extents | `test_the_served_extents_are_recomputable_from_the_served_clues` |
| F-8's guard | `test_an_out_dir_that_is_not_a_previous_site_is_refused` |
| EC-050's completeness | `test_every_player_control_is_in_the_ec_050_walk` |
| F-4 A/B | `test_a_save_or_a_puzzle_file_the_page_cannot_trust_is_refused` |
| F-4 C/D/E | `test_the_brush_region_and_touch_bindings_are_the_modules` |
| F-11 | `test_the_stage_fits_the_board_on_a_wide_screen` |

## [FIX ROUND 1 PRE-GATE — 2026-10-26, orchestrator] PASSED

| check | result |
|---|---|
| **F-1, against MY OWN plant** | the 12-char payload that recovered **56 of 56** answer cells now gives served `tier: ''` — **0 of 56 recoverable**. |
| **capacity, deployed** | **65.25 → 2.00 bits** (`height` 0.00, determined by `clues.rows`; `tier` 2.00; `width` 0.00, determined by `clues.columns`; `clues`/`key` exempt). My brief predicted ~10.8 — the round derived 2.00, because width/height carry no free bits once the clue-axis equality is enforced. |
| **the threshold restated** | `--capacity` now prints that the ceiling establishes only "no served field is wide enough to carry a grid" and **not** EC-048's one-cell threshold. |
| **F-11, visually** | rebuilt, served and looked at: the stage hugs the board, the 942 px empty box is gone. |
| suite | `test_public_player.py` **31 passed, 0 skipped** (was 23); neighbours 721 + 109 passed. |

**Resume demonstrated by accident:** the cell I marked in an earlier session was
still black after the site was rebuilt from scratch, with Undo live and Redo
greyed — AC-385's local resume working across a rebuild, which no assertion
states in quite that form.

### ⚠ The residual is real and it is the owner's

**2.00 bits of `tier` remain choosable by a hostile store**, and EC-048's
threshold is **one cell**. So the card does not claim EC-048 closed; it claims
the rebuild and the enumerated domains carry it, with the tier label named as an
open residual and routed to ADR-0041 — closing it means **not serving the tier
at all**. That is a product decision (the tier is reader-facing), not a fix.

### The round corrected the brief in five places, three of them load-bearing

1. **My predicted post-fix capacity (~10.8 bits) was too high** — it is 2.00, derived.
2. **F-2's remedy was not cheap in the direction I assumed.** The round's first `clues-column-count` refusal case was a **DEAD mutant**: deleting the column-length check left it green, because dropping a clue line also drops its filled cells and the two-axis agreement rule refuses the payload first — the same masking the implementation round hit with `clues-no-room`. Both length cases are now built so the length is the only thing wrong.
3. **F-9's remedy as worded would have been regression-blind.** "Read `--player-cell-min` from player.css" makes the assertion follow the token down — a 25 px token would still pass. Both the token's value and the rendered measurement are now asserted.
4. **F-6 should not be implemented at all**: the described second raw-text pass would read the exempt clue numbers, the one thing the sweep must not report. Sentence deleted, reason recorded.
5. The review's prose named the leaking field `difficulty_tier`; it is `tier` (`served_puzzle`, `payload.get("tier")`). My brief's correction was right and is now confirmed from both sides.

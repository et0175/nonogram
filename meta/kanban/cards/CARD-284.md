# CARD-284: The QR landing and the library — /b/<slug> and /library around the player

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/284-book-landing-and-library
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-284
**Source:** ONLINE_GAME_SPECIFICATION.md#technical-architecture (owner decision 2026-10-23, commit 8b0ca0e2) and §1.1 Puzzle Selection
**Idea:** —
**Wave:** 63
**Depends on:** CARD-282, CARD-283
**Touches:** player/**, tests/test_public_player_pages.py, tests/test_public_player.py <!-- the last added 2026-10-28: the card could not be implemented without it, see the implementation round's F-1. CARD-283 shipped three tests that directly contradict serving the listings. Neither sibling card in wave 63 names it, so the wave's measured empty path intersection holds. -->
**Review score:** **6.5 cycle 1/3, NOT CERTIFIED** (min 8) — 0 critical, 5 important, 1 of them an owner ESCALATION
**Started:** 2026-10-28T07:23:17Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The two entry points into CARD-283's game — the spec's answer to "one player,
not two": a QR scan and an online visit land on the same app through different
doors.

1. **`/b/<slug>`** — the per-book landing the printed QR points at: the book's
   title, its puzzles from `book/<slug>.json` in book order (each tile: title,
   size, tier), tap one to `/play/<key>`. This page is a book customer's first
   contact with the product on a phone, seconds after scanning: it must render
   from the static JSON alone, instantly, with nothing else to load first.
   An unknown slug gets a friendly static not-found page, not a bare 404 —
   a misprinted or stale QR is exactly when the reader is most confused.
2. **`/library`** — all published puzzles from `index.json`, filterable by tier
   and size (spec §1.1), same tiles, same links. Client-side filtering over the
   one index file; no search backend.
3. Both pages are plain static HTML/JS in `player/`, same tokens and look as
   the board page, mobile-first.

The book slug in the URL doubles as the per-book usage signal — CARD-285 wires
the counting; this card only has to keep the slug the visible, bookmarkable
path (no fragment routing, no query-string indirection).

## Acceptance criteria

FR-045 (registry entries minted by the 2026-10-23 architect delta, ADR-0041).

- AC-387: Given a bundle with a finalized book, when `/b/<slug>` loads, then its
  puzzles are listed in book order and tapping one opens `/play/<key>` for that
  puzzle (test: tests/test_public_player_pages.py::test_book_landing_lists_and_links).
- AC-388: Given a slug not in the bundle, when `/b/<slug>` loads, then the
  not-found page renders with a way to the library, and no script error is
  thrown (test: tests/test_public_player_pages.py::test_unknown_slug_lands_softly).
- AC-389: Given the library page, when filtered by tier or size, then exactly the
  matching index entries remain and clearing the filter restores all (test:
  tests/test_public_player_pages.py::test_library_filters_the_index).

## Guardrails

- G-1: The admin player and panel are untouched: no edits under src/nonogram/**
  (same contract as CARD-283 G-1/G-2; this card's code is `player/` and tests).
- G-2: The bundle format is consumed as CARD-282 defined it — no new fields
  required of the exporter, no second index derived at page-load time.
- G-3: The runtime dependency baseline stays closed (ADR-0006/R1); no runtime
  dependency, no framework, no build tooling beyond the existing copy step
  (test: tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed).
- G-4: Out of scope — scores, daily puzzle, progress stats pages, any
  server-side write (deferred by the spec to the December write API).

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0038/R1 — The puzzle player's client is hand-written JavaScript and CSS served as static files by the admin panel. (check: review-lens)
- ADR-0038/R2 — Marking, undo, redo, the error count and the solved check run entirely in the browser. (check: TestSolverMarking_NoRequestPerMark)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). (check: TestSolverPage_ShowsTheClues)
- ADR-0038/R4 — The player's state logic (board, strokes, undo/redo history, error count, solved predicate) lives in a pure module with no DOM access, separate from rendering. (check: review-lens)
- ADR-0038/R5 — pyproject.toml package-data for nonogram.admin includes static/*.js alongside templates/*.html and static/*.css, so the player's script ships in every built wheel. (check: review-lens)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. (check: review-lens)
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

- **FR:** FR-045 (AC-387..389)
- **ADR:** ADR-0041, ADR-0038, ADR-0006
- **Components:** COMP-011 (Public Player)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md, tokens.css, components.md
- **UI components:** puzzle tile (new — register in components.md), reuse the
  tier badge look from the admin lists
- **Screens:** /b/<slug>, /library, the not-found page
- **Standards:** forge:engineering-standards §11

## Worktree notes

—

## Routed in from CARD-282's review cycle 1 (2026-10-24) — two items, one product question

CARD-282 builds the bundle this card's pages read. Two things surfaced there
belong here rather than on it, and are written down now rather than at that
card's merge.

### 1. F-8 — a half-written bundle advertises files that do not exist

A `_dump` failure part-way through an export leaves `index.json` listing puzzle
keys whose `puzzle/<key>.json` was never written. CARD-282's export is
**deterministic and read-only against the database**, and that is all it claims;
it does not claim **atomicity**, and cycle 1 did not ask it to.

**This card's pages are where that becomes visible**, because `/library` reads
`index.json` and `/b/<slug>` reads a book file, and either can name a file that
is absent. So decide it here, with the shapes stated so nobody re-derives them:
a 404 on a listed puzzle, a book page listing a puzzle that will 404, or a
library index that silently drops entries it cannot resolve. **Whatever is
chosen, the claim belongs in a test** — "the player degrades rather than
breaking on an incomplete bundle" is a claim like any other and needs a control
that fails.

Not CARD-282's to fix: making the export atomic is a change to the writer with
its own failure modes (a temp tree and a rename, which is not free on every
filesystem), and it would have landed in that card's last cycle with no review
left. Raised there, routed here.

### 2. The product question ADR-0041/R7 opened and does not answer

R7 excludes the book's **title** from the slug on purpose, so that an editorial
title edit cannot break a printed QR code (owner decision 2026-10-24, DEC-044b).
A consequence nobody foresaw: **two finalized books with identical puzzle
membership in identical order are now ONE slug with TWO candidate titles**, and
one `book/<slug>.json` has to speak for both.

CARD-282 made that **deterministic** — the title is reduced by a pure function of
the candidate values rather than of the store's read order, held by
`test_two_books_with_the_same_puzzles_are_one_public_book` with a mutant redding
a read-order settle. **The engineering is settled. The product answer is not**,
and CARD-282's round deliberately refused to invent a second rule one commit
after being pulled up for inventing the first.

**This card owns the pages that render a book's title**, so the decision is
here. The options, with what each costs:

* **Publish one title** (what ships today — the first in a stable order). Cheap,
  deterministic, and one book's title never appears publicly.
* **Refuse such a pair at export.** Arguably right if identical membership is a
  data error, but it makes a legitimate second edition unpublishable.
* **Disambiguate.** Needs a discriminator in the slug, which **re-opens R7** and
  is therefore an ADR touch, not a code change.

Worth knowing before choosing: a plausible real case is a reprint or second
edition with the same puzzles and a changed title — in which case one public
book with one title is arguably **correct**, since the slug names content and
the QR code resolves to the right puzzles. Only the displayed title is
ambiguous.

## [IMPLEMENTATION — 2026-10-28] `ab297c9c` + `7c0c9f5a` — and the title is NOT served

Two commits, 8 files, +2102/−38. **G-1 verified mechanically from git: 0 files
under `src/`, 0 under `meta/`.** Working tree clean, every file hash-checked
against HEAD. Wave 63, run concurrently with CARD-227 and CARD-267.

`/b/<slug>` renders from **one** fetch of `book/<slug>.json`, whose tiles the
assembler inlines at assembly time — so no second index is derived at page load
(G-2) and nothing else loads first. Puzzles in book order, numbered as the
printed book numbers them (position, not a field). `/library` reads the rebuilt
`index.json` and filters client-side by tier and size band.

### The decision this card had to take: the title is not served, on either listing

`index.json` and `book/<slug>.json` are now **rebuilt from closed schemas**
exactly as the puzzle files are — `SERVED_ENTRY_SCHEMA = ('height','key','tier',
'width')` (derived as `SERVED_SCHEMA` minus `clues`), `SERVED_INDEX_SCHEMA =
('puzzles',)`, `SERVED_BOOK_SCHEMA = ('puzzles','slug')`. **`title` is in none of
them.** This is the inherited answer rather than a new one: CARD-282 measured a
published title decoding back to **all 144 cells** of a 12×12 answer, a scan
cannot decide *"does this string carry a grid?"*, and CARD-283 removed the
channel rather than filtering it. Taking the opposite decision here would reopen
EC-048 **on the one page every book customer sees**.

**Established by removal, not by scan**, and with the sweep running in both
directions in one test: the bundle's `index.json` and `book/<slug>.json` **must**
be dirty (every fixture title is base-64 of its own grid) and the site **must** be
clean — so a sweep that had stopped working could not report this as a pass.
Mutant M3 is the live control: carrying the bundle's fields through reds it.
**[CORRECTED 2026-10-28, cycle 1's F-007 — M3 named the wrong cell.]** Adding
`"title"` to `SERVED_BOOK_SCHEMA` does not red this sweep's assertion: it reds
`check_listing_capacity` at *fixture setup* (4 failed / 4 passed, **11 errors**)
and the sweep never reaches its own assertion at all. Four independent
mechanisms guard that field and **no single-node mutant reaches past the third**,
which is why the attribution looked right. The sweep's real live control is
`_dump(…, book)` → `_dump(…, payload)`, which reds
`test_no_title_reaches_either_listing` **on its own assertion**. The code was
never the defect here — the record was. A mutant that dies in a fixture
certifies the fixture, not the claim under it.

### CARD-282's F-8 closed by construction rather than by a check

Every served listing entry **is** the served payload of that key's own
`puzzle/<key>.json` (`listing_entry` reads the served dict, never the bundle), so
a listing naming an absent file is **not possible** rather than merely detected.
The bundle's own `index.json` is then read as a **second, independent
instrument** — what the export *declared* — and every disagreement is named:
`unresolved`, `unlisted`, `index_unread`. **A bundle with no `index.json` reports
every served key as unlisted**: the instrument cannot read as "nothing wrong"
when it has nothing to read. Measured both ways: one puzzle file deleted →
`unresolved` names it and **0** keys are listed with no served file; `index.json`
deleted → `index_unread` is set and `unlisted` is 5 of 5.

### Kill instrument — 27 mutants, 27 killed, per assertion

Each deletes the mechanism a claim names, line-count-preserving, runs only that
claim's controls, restores and verifies `git hash-object`. Four are **edge**
mutants (M2, M8, M16, M24b, M26). **Two were DEAD on the first pass and the
CONTROLS were fixed rather than the notes** (`7c0c9f5a`): `.tile`'s touch floor
was measuring an accident — deleting `min-height: 72px` left every tile over
44 px anyway on this corpus — so the **declared** floor is now read off the
computed style and held to 44, with the one-pixel edge (43 px) redding; and
`readListing`/`isEntry` **had no control at all**, so four malformed listings now
exercise one branch each with the unedited listing as the positive control in the
same test. The CSS otherwise adds no mechanism any claim names, and the round
says so rather than inventing mutants for it.

### Pre-gate

**953 collected = 953 passed, 0 failed, 0 skipped**, exit 0, 87.22 s, over the
changed files plus the derived blast radius (every suite reading `player/**`,
`pyproject.toml`, the admin static files, or walking the test tree). `-rs`
printed **no skip section — there are no skips to attribute**. This card's own
file: 18 passed, of which `-m browser` selects 6.

Host cells at both ends: load **7.44 → 10.79**, **rival-pytest 3 → 3** — *and the
round correctly refused to treat that as noise*: the siblings were live and one of
their processes interfered with its tree (see F-5). The full suite was **not** run
and the board's lock was **not** taken.

### Figures, with their doors named (ADR-0039/R4, its first use on a live card)

Served puzzle file **2.00 bits** free against a 100-bit ceiling — unchanged by
this card, CARD-283's bound, same domain. Served listings **0.00 new free bits**:
`MIRRORED_FROM_PUZZLE_FILE` equals `SERVED_ENTRY_SCHEMA` and every value is built
*from* the served puzzle payload, so a listing reader learns nothing a puzzle-file
reader has. `check_listing_capacity()` returns `None` today and **raises when the
partition breaks in either direction** (M2, M7, M8). Declared residual: **the
order** a book's puzzles are listed in — `log2(4!) = 4.58` bits for the fixture,
`log2(24!) = 79.04`, `log2(120!) = 660.48`. Not a ratio, not mixed instruments.

### Could not establish, in those words

**No render was eyeballed** — nobody has looked at `/b/<slug>` or `/library` on a
real phone, and every layout claim is a computed-style or bounding-box assertion,
which is exactly the kind that reads fine and looks wrong. **The owner's visual
pass is owed.** Chromium only (ADR-0038/R7) — **no iOS Safari, where most QR scans
land.** Never run against a real exported bundle (fixtures only; CARD-283 owed the
same). Vercel itself not exercised — the two new rewrites are applied by the test
server reading the shipped `vercel.json`, so the rules are exercised and the host
is not. And **it does not claim EC-048 is closed**: `assemble.py`'s own docstring
records that EC-048's literal text is unsatisfiable by any ADR-0041
implementation, so every claim reads "except the two ADR exemptions and the
declared residuals".


## [CYCLE 1 — 2026-10-28] **6.5, NOT CERTIFIED** — 3 surviving mutants, and the title is an owner call taken in a worktree

Report: `meta/review/20261028T141949Z-CARD-284-cycle1.yml` (13 findings, parses).
Reviewed `7c0c9f5a` against merge-base `7a62d704`. **17 mutants fired, 14 killed,
3 survived**, 5 of them edge mutants. System contract: 36 rules, 11 ✓, 23 ⚠
unchecked, **2 ✗ violated** (ADR-0039/R1 and R3).

### The card's own declared finding, adjudicated: TRUE but MIS-SCOPED

*"The title is not served"* is **true** — `SERVED_BOOK_SCHEMA = ("puzzles",
"slug")`, no `"title"` appears anywhere in `assemble.py`, and the sweep that
enforces it is a live control (the `_dump(…, book)` → `payload` mutant reds
`test_no_title_reaches_either_listing` on its own assertion). It is also
**consistent** with AC-387/388/389 and G-1..G-4.

**What it is not is a worktree note.** Two different fields are being argued as
one:

- the **puzzle** title is the picture name, which **EC-048 forbids** on every
  asset the public site serves — not a choice at all, and serving it would have
  been the violation;
- the **book's display title** is owner-authored editorial text that EC-048's
  enumeration does not name.

This card's body (line 31) requires *"the book's title"* on `/b/<slug>`, the page
it calls *"a book customer's first contact with the product on a phone"*. The
card routed in **exactly three options** for the collision (publish one title,
refuse the pair at export, disambiguate — the third flagged as an ADR touch).
*"Serve no title at all"* is a **fourth option, taken in the worktree** — which
is the same move CARD-282's round was pulled up for one commit earlier. Body and
code now contradict each other and FR-045 resolves neither. **Escalated to the
owner; it is not the fix round's to decide.**

### The three surviving mutants — all verified independently by the orchestrator

1. **`isEntry` has six branches and four cases** (F-003). `Number.isInteger`
   appears at `pages.js:111` and **in no test**; the extent range plants only
   `MAX_SIZE + 1` (`tests/test_public_player_pages.py:479`) and never
   `MIN_SIZE - 1`. Both mutants survive. The docstring's *"four shapes, one per
   branch"* is false, and **this repo had already named this exact hole once** —
   "`MIN_SIZE-1` is the one value that reads it", in the puzzle-file table — and
   did not carry it across.
2. **`served_index`'s determinism has no control** (F-004). Reversing the served
   order survives 51 nodes: nothing asserts the index is key-sorted, every
   AC-389 assertion wraps `_tiles(...)` in `sorted(...)`, and `declared_data()`
   excludes `index.json` from the byte comparison.
3. **A destructive guard was widened with no denial control** (F-005).
   `check_out_dir`'s allow-set gained `index.json`, `book`, `b`, `library`,
   `pages.js`, so a directory whose only entry is `index.json` is now silently
   `rmtree`d where it was refused. The one negative control is drawn from the
   shape the guard was written from, and the mutant dropping `SITE_INDEX_FILE` is
   killed **by the positive control** — the suite pins what must be *allowed* and
   nothing pins what must still be *denied*. Textbook "widening a predicate and
   adding an exemption are one edit".

### Two false docstrings about live mechanisms

- **F-002** `assemble.py:140` still concludes *"the tier is this script's one open
  edge, it is two bits wide"* while **line 177 of the same file, same commit**
  declares a second residual the card sizes at log2(24!) = 79.04 bits. No diff
  hunk covers lines 100-155 — mechanically confirmed. This is the file carrying
  EC-048.
- **F-006** two docstrings say `/library` needs no rewrite and *"vercel.json only
  has to cover /b/<slug>"*; the same commit adds a `/library` rule, and killing
  it reds a test.

### One record defect, not a code defect

**F-007**: the implementation record's M3 names the wrong cell. Adding `"title"`
to `SERVED_BOOK_SCHEMA` reds `check_listing_capacity` at *fixture setup*
(4 failed / 4 passed / **11 errors**) and the sweep never reaches its assertion.
Four independent mechanisms guard it and no single-node mutant reaches past the
third, so the code is fine — the attribution was wrong.

### Also found

**F-009** `meta/design/components.md` is a required edit the card does not
declare — a `Touches:` correction — and the new public tile is unregistered
(the existing `## PuzzleTile` is the admin panel's). **F-010** filtering rewrites
the tile list, count and empty note with no `aria-live` and no focus move, while
`player.css` already ships CARD-283's unused `.player-announce`. **F-012**
`_open_pages` has no explicit timeout: one mutant cost **62.63 s** against a 2.9 s
baseline because two navigations each burned Playwright's 30 s.

### What the review could not establish, in its own words

**No render was eyeballed** — nobody has looked at `/b/<slug>` or `/library`;
every layout claim is a computed-style or bounding-box assertion, and
`review.visual: off`. **The owner's visual pass is owed.** Nothing was tested
outside Chromium, where most QR scans land (iOS Safari). The card's 953-node
pre-gate figure was not reproduced — a 208-node core subset was run instead, as
a deliberately different door. The validator was not run (0 files under `meta/`
makes the baseline unchanged by construction, not by measurement). Vercel itself
is never exercised; only the loopback fixture reading the shipped `vercel.json`.

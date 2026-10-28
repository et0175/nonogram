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
**Touches:** player/**, tests/test_public_player_pages.py, tests/test_public_player.py, meta/design/components.md, meta/architecture/requirements.yml <!-- the last added 2026-10-28: the card could not be implemented without it, see the implementation round's F-1. CARD-283 shipped three tests that directly contradict serving the listings. Neither sibling card in wave 63 names it, so the wave's measured empty path intersection holds. --> <!-- corrected 2026-10-28 at fix round 1, two paths edited and undeclared: meta/design/components.md (F-009 -- the card's own Design context required the registration and the declaration never existed) and meta/architecture/requirements.yml (FR-045's /b/<slug> clause and AC-387, carrying the owner's book-title decision; 17 insertions / 5 deletions at two hunks, measured against merge-base 7a62d704 -- NOT the 23/63 a diff against a newer main reports, which counts CARD-227's absent additions as deletions). AC ids unchanged, so trace.yml needs nothing, and a trial merge into main produces 0 conflict markers. -->
**Review score:** 6.5 → 7.5 cycle 2/3 → fix round 2 → awaiting cycle 3 (**its last**)
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

- AC-387 **[restated 2026-10-28, cycle 2 F-009 — this line was the pre-decision
  two-clause text while the registry it updated had four clauses]**: Given a bundle
  with a finalized book **that has a display title**, when `/b/<slug>` loads, then
  **the book's display title heads the page**, its puzzles are listed in book order,
  **no puzzle's title appears anywhere on it**, and tapping one opens `/play/<key>`
  for that puzzle (test: tests/test_public_player_pages.py::test_book_landing_lists_and_links).
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

## [IMPLEMENTATION — 2026-10-28] `ab297c9c` + `7c0c9f5a` — ~~and the title is NOT served~~

> **OVERTAKEN TWICE — read this heading as history.** The title **is** served, by
> owner decision 2026-10-28, under **ADR-0041/R2's third exemption** (amended the
> same day, because an FR cannot narrow a mandatory rule). Fix round 1 implemented
> it; fix round 2 closed the fixture half and removed the false "EC-048's
> enumeration does not name it" justification from all four sites that carried it.
> Everything below is the state before that, kept because the owed→landed trail is
> what makes the decision auditable.

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


## [FIX ROUND 1 — 2026-10-28] `c3f1a795` — the book's title is served, and 30 of 30 mutants die

Two commits (`d579f491`, `c3f1a795`), 9 files, +1512/−195. **0 files under `src/`**
(G-1 holds, measured) and 0 under `meta/kanban/`. **30 mutants fired, 30 killed,
11 of them edge mutants.**

### F-001 — the owner's decision, implemented

`/b/<slug>` serves and renders the **book's display title**, under an explicit
scoped exemption (`EXEMPT_LISTING_FIELDS = ("title",)`) with three ordered
refusals in `check_listing_capacity`: liveness, scope, partition. **The order is
load-bearing and the round found that out the hard way** — its first draft put
liveness and scope *after* the partition check, where both were unreachable dead
code, because any edit that reaches them breaks the partition first. Found with
the test, not by reading, and recorded in the docstring.

The two fields are separated in every sentence this round wrote: a **puzzle's**
title is the picture name EC-048 forbids, and `check_listing_capacity` now
**refuses to assemble** if it reaches a puzzle file or the library index; the
**book's** display title is editorial text that FR-045's own bundle clause already
lists ("its slug, display title and ordered puzzle keys") *in the same sentence
that forbids the picture name*. The decision also lands on one of the card's three
routed-in options — "publish one title" — with CARD-282's deterministic reduction
choosing which.

**The sweep is narrowed and still live**: `test_no_title_reaches_either_listing` →
`test_no_puzzle_title_reaches_either_listing`. The old control *could not* survive
the change, because the fixture's book title had to become editorial and a bundle
book file carries keys with no puzzle metadata, so it cannot be its own control.
Two controls replace one: the bundle's `index.json` proved dirty (≥2 grids), and
the leak **planted** into each served listing with the sweep required to report
**both** files.

### The capacity question, answered without pretending

**The book title costs 2410.18 bits** — 120 chars × log2(1 112 064). Against what
budget, stated rather than implied: **24.1× the 100-bit ceiling** and **2.68× the
900 cells of the largest publishable grid**. **There is no pass to be had and the
code does not pretend there is**: `book_title_residual_bits()` is deliberately not
compared against the ceiling and does not gate assembly, because one base-64
character already carries six bits against EC-048's one-bit threshold, so no
reachable cap is a bound. The cap is a **layout** bound and a **declaration**
bound, and the docstring says so.

**Control in a new domain — cells, not bits:** a `MIN_SIZE` grid is 100 cells and
its base-64 is 20 characters, well inside the cap, so the whole grid comes back.
The test names a book after one of its puzzles' answers and asserts the sweep
reports **exactly one file**, with `puzzle/` and `index.json` clean under the same
plant; with an editorial title the same tree sweeps clean. An aside recorded so
nobody misreads it: base-64 of a `MAX_SIZE` grid is 152 chars and the cap
truncates it — **an accident of base-64, not protection.**

### Both of this round's own survivors were in controls it had just written

Caught here rather than in cycle 2, which is the board's measured rule working as
intended:

- **M8**: the title residual's figure was held only as `round(bits, 2) ==
  2410.18`, and one code point in a million is four decimal places below that
  rounding. Now recomputed in a different domain — the surrogate block excluded
  *because those code points are not characters*, measured by
  `chr(0xD800).encode("utf-8")` raising, with `chr(0xD7FF)`/`chr(0xE000)` as the
  boundary control.
- **M24**: the design-inventory drift guard matched with `in`, so
  `data-pages-loading` was a substring of the typo `data-pages-loadingx` and **the
  guard read the typo as the thing it sought**. Word-boundary match now, with a
  second control for the genuine prefix pair (`data-pages-filter` really is a
  prefix of `data-pages-filters` and both are live hooks).

**And one cell attribution was corrected mid-round**: M14 (removing the tier guard
text) reds `assert guards == 5` — the *source arithmetic* — before the browser
loop runs, so it does **not** demonstrate `bad-tier`'s behavioural control. M30
(`TIERS.includes(tier)` → `true`, leaving the counted text intact) is the
behavioural one. Same correction for `bad-key` via M29.

### F-003 closed with seven cases, F-004's collateral taken in scope

`isEntry` now has **seven cases** over five refusal statements plus the wrapper and
the range's second edge, held as an arithmetic against the source — and the two
branches cycle 1 proved dead now have their **first readers ever** (`Number.isInteger`
and the low end of the extent range). F-004 took the collateral deliberately:
`test_the_served_index_is_key_sorted` **and** `test_two_assemble_runs_are_byte_identical`,
which is EC-049's property at the layer that actually deploys.

### F-005 — the marker file, which does not widen with the published set

`check_out_dir` now recognises `SITE_MARKER_FILE = ".player-site"`, written the
moment the directory exists, so it asks *"did this script write this tree?"*
rather than *"does this tree look like output?"* — and it **does not grow when the
published name set grows**, which was the whole defect (the set grew by five names
in this card's own commit). **Five denial controls, each built only out of names an
assembled site has**, so every one of them passed the old predicate: a lone
`index.json`, a lone `book/`, a lone `pages.js`, `index.json` beside a stranger,
and every site name but the marker. Each is then re-run **with** the marker and
must be accepted, so the refusals are a statement about the marker rather than
about the names. Asserted through `check_out_dir` directly, never through
`assemble`, whose next statement is `shutil.rmtree`. **Stated cost:** a tree
assembled before the marker existed needs `--force` once.

### F-012's figure, re-measured in cycle 1's own domain

The same mutant over the same whole file: cycle 1 **62.63 s** against a 2.9 s
baseline (18 nodes); now **9.72 s wall** against a 4.93 s baseline (25 nodes) —
**6.4× faster** and clear of the ~120 s truncation window. Per-mutant failures now
read `Timeout 3000ms exceeded` instead of burning 30 s each. `PAGES_SETTLE_MS =
3000` is ~10× the measured 0.1–0.24 s call times, with the measurement in its
comment.

### Gate

**2313 collected = 2313 passed, 0 failed, 0 skipped**, exit 0, 109.52 s over 27
files — the changed files plus a derived blast radius, a deliberately larger door
than the card's own 953-node selection, which was not reproduced. `-rs` printed no
skip section, so there is no skip to attribute. `tests/test_public_player_pages.py`
goes 18 → **25 collected**, with `-m browser` selecting **9 of 25**.

### Renders exist for the first time, and the owner's pass is still owed

Six captures in **`~/Documents/nonogram-reviews/CARD-284/`**: book landing at
phone 390 and desktop 1280, library at both, the unknown-slug not-found panel, and
the capped-title case. The round read three of them and reports the landing reads
as intended. **That is not the owner's pass** — it is Chromium at two synthetic
widths on fixture data.

### Two questions the round refused to answer for the owner, correctly

1. **`/library`'s listing order.** Key order is not an order a reader wants: the
   library shows 16×16, 23×23, 17×17, 30×30, 10×10, 24×24. No AC states an order,
   so `served_index`'s docstring now says explicitly that determinism is the only
   claim and **not** that it is an order anyone wants. A product decision.
2. **`SERVED_TITLE_MAX_CHARS = 120`** is generous to the point of ugly, asserted
   numerically *and* eyeballed not to break the layout. A taste call.

### Could not establish, in the round's own words

**No render eyeballed by the owner** · **Chromium only — nothing on iOS Safari,
where most QR scans land**, and these are the pages a scan reaches first · never
run against a real exported bundle, fixtures only · **Vercel itself never
exercised** (the rules are read from the shipped `vercel.json` by a loopback
fixture; the host is not) · **EC-048 is not claimed closed**, and the scope
statement is now wider: three exemptions (clues, key, book title) and four
declared residuals (the tier's two bits, and a book file's order, membership and
title) · **the title exemption is bounded in scope, not in size** — "a puzzle title
cannot get out" is mechanical and controlled; "a book title cannot carry an
answer" is **false and stated as false**, measured at 100 of 100 cells · the first
guard of `isEntry` is three disjuncts and only `null` has a case reading it alone
· the full suite was not run and the lock was not taken.


## [FIX ROUND 2 — 2026-10-28] `6aa4c5b9` — both halves of F-001 closed, and three stale R2 claims nobody had reported

Five commits on a merge of main (`10e25e28`, 0 conflicts — `7c0c9f5a` untouched, so
the implementation record still cites a live commit). Door: **604 passed, 0 failed,
0 skipped**, reproduced twice, over cycle 2's own four-file selection. 603 → 604 is
**exactly the one node added**, so cycle 2's figure is the control for this one.
0 files under `src/`, `meta/kanban/**` or `meta/architecture/**`. **17 mutants, 16
killed, 1 survivor by design, 0 undeclared survivors.**

### F-001's model half — the false justification is gone from all four sites

Every place that justified the served title by *"EC-048's enumeration does not name
it"* now cites **R2's 2026-10-28 exemption** and states the old argument as
**false**, with the reason. `grep -rn "enumeration"` over the diff returns only the
four sentences saying it was false.

**And three further stale R2 claims in `assemble.py` that cycle 2 did not report**,
each one a sentence cycle 3 would have gated on: `:66` claimed the bundle's `title`
*"is not in that schema and does not reach the site"* — flatly false since fix round
1; `:691`, **the listings' own section header where a reader starts**, said *"no
title is served, on either listing"*; and `:46`/`:172` said *"the two exemptions"*
when R2 has three. The R2 quotation at `:49` now carries the amendment's clause, so
the file no longer quotes a rule in a form the rule does not have.

### F-001's mechanical half — the two tests no longer disagree

`test_served_tree_is_clean_of_answers` now **passes both titles in explicitly and
asserts both outcomes**: a **puzzle** title cannot get out (served tree `== {}`
although every puzzle title in the bundle is base-64 of its own grid, with the
editorial book title asserted non-recoverable *first* so the half is not vacuous),
and a **book** title is admitted as the declared exemption **and only in the book
file** (the sweep reports exactly one path by name, with `puzzle/` and `index.json`
asserted clean under the same plant). It no longer takes `site`, **so no claim of
R2's rests on a fixture default.**

**C2-M41 re-fired at the final HEAD no longer splits them** — all three tests pass,
and the one node it reds is the test whose subject *is* the two fields getting
opposite answers.

### F-002 — the fix now has a control

`named()` takes the inventory text as a **parameter** and the boundary is asserted
**through the function**. The two inline regex re-derivations are gone. Both of
cycle 2's mutants now kill — including the 2-node counter-case (`in` plus a typo on
a *different* hook), **on the same cell**, because the control no longer depends on
which hook the test spells out.

### R2's check ref — the flip is verified and owed AT MERGE, not before

All three `path::name` strings resolve **on the branch** under the validator's own
exclusions. The flip text is recorded for the merge gate:

```
check: {kind: test, ref: "tests/test_player_bundle.py::test_bundle_is_clean_of_answers, tests/test_public_player.py::test_served_tree_is_clean_of_answers, tests/test_public_player_pages.py::test_the_book_title_exemption_is_scoped_and_its_cost_is_measured"}
```

**It must not be applied before this card merges** — two of the three resolve only
on this branch, and naming them on main would read as mechanically checked while
absent. The round also made the exemption's node id greppable **from the module
that defines it**, because beforehand the only hits were prose sentences in two
*other* files, either of which could lose a line and take the ref with it.

**One fragility passed on, not this card's:** R2's *existing* bundle-half ref
resolves only through one prose line plus two `meta/review/*.yml` files —
`tests/test_player_bundle.py` does not carry its own `path::name` string. That is
the backlog's "a review YAML can revive a dead check ref", **one artefact away from
firing.**

### The architect items this round surfaced are DONE (`4b4ca160`)

R2's exemption now reaches **the bundle's own `book/<slug>.json`**, because
`player_bundle.BOOK_FILE_FIELDS` has carried `title` since it was written — so the
first amendment's "and nowhere else" was false of the bundle on the day it was
written. **EC-048's statement** points at R2's exemptions instead of reading false,
and **its `test:` is now the pair**, since it claims both export paths while naming
only the bundle half. **FR-045's bundle sentence** narrowed the same way.

### And the validator split is root-caused, which retires a standing "known error"

Three rounds reported three figures. `validate.py` is **byte-identical** across the
two installs; `adr_integrity.py` is the **only** differing source. The plugin-cache
copy counts *"supersedes"* **and** *"superseded by"* as two edges, so a properly
two-sided supersession reads as a cycle; `forge_1`'s copy matches only the forward
phrase and says why. Measured on the ADRs: `0031:11` *"Supersedes: ADR-0025"* and
`0025:3` *"Superseded by ADR-0031"* — **one edge from both ends.** So **the honest
error count is 0**, and every report citing "the pre-existing ADR-0025 circular
supersession" was quoting a tool bug. The 3-warning gap to main is this card's own
doing: exactly the three AC-387/388/389 dead-ref warnings, dead on main and
resolved here because this card defines those tests.

### Minors — narrowed where the claim was wrong, fixed where it needed a mechanism

**Narrowed:** F-003 (the scope refusal is *not* dead code — all three scope edits
pass the partition predicate, and only liveness is order-dependent), F-004
(attribution swapped, with the measurement in the sentence), F-007 (byte-identity
is **intra-process**, naming the cross-process case it cannot see and the test that
owns that half), F-008 (six denial cases, not four, and which one is drawn from the
shape the old predicate was written from), F-010's causal sentence. **Fixed in
code:** a **sixth** denial case (a target whose only entry is a *directory* named
`.player-site`), F-006's ordering control (`_write` raising on its second call, so
the half-written target holds only the marker — and the old paragraph **passes**
under the same mutant, which is the discrimination), F-007's plant now appending a
byte **on disk** and re-walking with the same reader, and `page.goto`'s bound —
**with its own control**, an `ast` walk asserting both calls carry
`timeout=PAGES_SETTLE_MS` by name. *"I would not have claimed the bound without
this — a timeout argument cannot red on behaviour without a hung server."*

### Could not establish, in the round's own words

Half 2's *"and only in the book file"* assertions **are never the first reader** —
every single-node mutant that puts the book title elsewhere is intercepted earlier
by the scope refusal or by `served_index`'s own schema equality, which is cycle 1's
F-007 lesson repeating (four mechanisms, no single node reaches past the third), so
no mutant is claimed for them · the `=` half of F-002's boundary is held by the
real inventory rather than by its own cell, **and the hyphen in `[a-z-]` has no
control at all** · R2-M04 dies in a `raise`, not in an assertion · **no render
eyeballed by the owner** · **Chromium only, nothing on iOS Safari** · never run
against a real exported bundle · **Vercel never exercised** · EC-048 not closed and
not claimed closed · `tests/test_player_bundle.py` not re-run, so R2's bundle half,
R1, R5 and R7 are reported from the model rather than from a run · **why the two
installs ship different `adr_integrity.py` under identical `validate.py` bytes** —
established *that* they do, and that it is the whole disagreement; which install to
standardise on is a decision, not a measurement.

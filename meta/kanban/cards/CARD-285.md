# CARD-285: Hosting and counting — the player goes public without storing anyone's IP

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/285-player-hosting-analytics
**Worktree:** —
**Source:** ONLINE_GAME_SPECIFICATION.md#technical-architecture "Usage tracking" + the static-hosting decision (owner, 2026-10-23, commit 8b0ca0e2); backlog.md "A public online solver" ("the work is hosting + the public surface, not the game")
**Idea:** —
**Wave:** —
**Depends on:** CARD-283, CARD-284
**Touches:** player/**, docs/deploy/player.md, scripts/**, tests/test_public_player_pages.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The infrastructure half of the public phase: put the `player/` tree and the
CARD-282 bundle on a static host, count usage without login or stored IPs, and
produce the one fact CARD-210 is blocked on — a stable public URL base for
printed QR codes.

1. **Static hosting.** Deploy `player/` + the exported bundle to **Vercel**
   (DEC-045/ADR-0041 — free static hosting, CDN, no cold starts; the deciding
   constraint is that a QR scan from a book must load instantly, which rules
   out the sleepy admin service). Creating the account and the domain is the
   **owner's** action; this card
   delivers the deployable artifact (one directory that IS the site), a
   `scripts/` helper that assembles it (player files + bundle + copied
   `solver_state.js`), and the deploy doc.
2. **`docs/deploy/player.md`** — what runs where, how a new bundle gets
   published, and what is owner-managed vs repo-managed, in the same spirit as
   docs/deploy/render.md (which exists precisely because an undocumented
   dashboard-managed deploy bit this project before).
3. **Usage counting, privacy-first** (spec "Usage tracking"): the per-book slug
   in the QR URL is the primary signal (which book drives visits); the
   analytics script — **GoatCounter** (DEC-046/ADR-0041) — gives visits,
   estimated uniques, country and device with no cookies, no consent banner,
   and **no raw IPs stored by us** (an IP is personal data under GDPR, and
   carrier-NAT makes it a bad unique-visitor key anyway). The snippet is
   include-once across all player pages; the pages must render fine with it
   blocked or absent.
4. **The QR URL base.** Record the production base URL + the `/b/<slug>` and
   `/play/<key>` shapes where CARD-210 can consume them, and note on CARD-210
   that its two blockers (hosted public solver, stable namespace) are now one
   decision away from clear.

## Acceptance criteria

FR-045 (registry entries minted by the 2026-10-23 architect delta, ADR-0041).

- AC-390: Given a checkout with an exported bundle, when the assembly script
  runs, then one output directory contains everything the site serves —
  player pages, bundle JSON, shared state module — and serving that directory
  with a plain file server passes CARD-283/284's Playwright suites unchanged
  (test: tests/test_public_player_pages.py::test_assembled_site_is_self_contained).
- AC-391: Given any player page with the analytics script unreachable, when the
  page loads, then the game and navigation work and no uncaught error reaches
  the console (test: tests/test_public_player_pages.py::
  test_pages_work_with_analytics_blocked).
- AC-392: Given the assembled site, when its files are scanned, then no code in
  it reads, stores, or transmits a visitor IP, and the only analytics endpoint
  referenced is the one named in docs/deploy/player.md (test:
  tests/test_public_player_pages.py::test_no_homegrown_tracking).

## Guardrails

- G-1: No edits under src/nonogram/** except none — the admin service, its
  Render deploy, and render.yaml are untouched; this phase exists so customer
  traffic never reaches them.
- G-2: The runtime dependency baseline stays closed (ADR-0006/R1); the analytics
  integration is one script tag, not a package (test: tests/test_export_pdf.py::
  test_the_dependency_baseline_is_still_closed).
- G-3: No raw IP, user-agent fingerprint, or per-visitor identifier is stored
  by anything this card ships (spec "Usage tracking"; behavioral — AC-3 is its
  evidence).
- G-4: Out of scope — the write API (scores/leaderboard/daily puzzle, deferred
  to December), custom domains/DNS automation, and flipping CARD-210 to ready
  (that is the owner's unblock after the namespace DEC resolves).

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

- **FR:** FR-045 (AC-390..392)
- **ADR:** ADR-0041 (R5 bundle, R6 no visitor identifiers; DEC-045 Vercel,
  DEC-046 GoatCounter), ADR-0006 (baseline unchanged)
- **Components:** COMP-011 (Public Player), COMP-009 (Admin Panel — the bundle
  it assembles)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

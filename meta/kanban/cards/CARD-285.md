# CARD-285: Hosting and counting — the player goes public without storing anyone's IP

**Status:** in progress
**Priority:** P2
**Category:** enabler
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/285-player-hosting-and-counting
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-285
**Source:** ONLINE_GAME_SPECIFICATION.md#technical-architecture "Usage tracking" + the static-hosting decision (owner, 2026-10-23, commit 8b0ca0e2); backlog.md "A public online solver" ("the work is hosting + the public surface, not the game")
**Idea:** —
**Wave:** —
**Depends on:** CARD-283, CARD-284
**Touches:** player/**, docs/deploy/player.md, scripts/**, tests/test_public_player_pages.py
**Review score:** —
**Started:** 2026-10-29
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

## [Implementation round 1 — 2026-10-29. The three unverified claims now have tests, and the counting had to move to assembly time.]

Branch `card/285-player-hosting-and-counting` @ **`af160fd5`**, three commits on the
cut `464ae377`, tree clean, nothing under `meta/` touched. **6 files, +1583/−25** —
`docs/deploy/player.md` (new, 187), `scripts/assemble_player_site.py` (new, 238),
`player/assemble.py` (+147), `player/play.html`, `scripts/README.md`,
`tests/test_public_player_pages.py` (+986).

### The decision the whole card turned on, and it was forced

**Item 3's counting snippet collides head-on with CARD-283/284's own controls**, and
`player/play.html`'s existing comment predicted it. **Verified by the orchestrator:
four shipped browser tests assert that every request the page issues is
same-origin** — `test_resume_is_local_and_the_page_writes_nowhere`,
`test_no_write_request_for_any_interaction`,
`test_the_page_carries_no_answer_and_no_third_party_asset`,
`test_the_listing_pages_only_get_and_write_nothing` — three of them by the literal
`assert all(request.startswith(url + "/") …)`.

A GoatCounter tag hard-written into `player/*.html` is **cross-origin**, so it would
have red all four — and AC-390's load-bearing word **"unchanged"** would have been
false by the round's own hand.

**Resolution: the snippet is injected at assembly time, default-off.**
`ANALYTICS_SNIPPET` is the one copy of the tag anywhere in the repo, with
`--analytics-count` / `--analytics-script` both-or-neither and
`AssembleReport.counted`. With no flags — every fixture, every local run — no tag is
written. The card's own wording supports it: *"the pages must render fine with it
blocked **or absent**"*.

**The residual is declared, not hidden**, and turned into an assertion: CARD-283/284's
no-egress controls therefore measure the **uncounted** tree, so AC-390 asserts the
byte difference between the counted and uncounted trees is **exactly the snippet
line, in exactly the pages `report.counted` names, and nothing else.** Widen what
counting does and that assertion reds.

**Measured consequence: CARD-283/284's Playwright suites pass unchanged** — 59 passed
before the first line, 59 of 66 after, no suite body edited.

### The three ACs, and the gap they close

| AC | node id | at the cut | now |
|---|---|---|---|
| AC-390 | `…::test_assembled_site_is_self_contained` | **0 resolvers** | `def` at `:2299` |
| AC-391 | `…::test_pages_work_with_analytics_blocked` | **0 resolvers** | `def` at `:2454` |
| AC-392 | `…::test_no_homegrown_tracking` | **3, all review YAMLs** | `def` at `:2548` |

Re-measured by the orchestrator under the validator's own pathspec. AC-392's three
resolvers were CARD-218 cycle 1 and 2 and CARD-284 cycle 1 — **the board's one true
false alive, and it is gone.** This also closes **two of CARD-307's three honest
gaps**; CARD-307 was not edited.

Runs: both player modules **66 passed, 0 skipped**; `-m browser` **22 passed, 44
deselected** with **no Chromium skip** — `browser_type` calls
`pytest.fail(pytrace=False)` on a missing executable, so a missing browser is red
rather than an ungated door. Node ids **9748 → 9755, +7 / −0**. Mutants **7 of 7
killed**, no survivors, instrument proved on an unmutated tree first.

### Two false positives the scanner found on the real tree

Both findings about the scanner rather than the site, and both worth keeping:
`_IMPORT_TARGET` matched **English prose** in `player.css` (*"reads differently
from"* + a newline + a quoted phrase), and `solver_state.js:6` documents the admin
panel's own path inside a `//` comment — a rooted path that exists in the panel and
not in this tree, which is exactly what "resolves to nothing" is for. Comment forms
are now blanked before the quoted shapes are read, while `_ABSOLUTE_TARGET` runs on
the **unstripped** text so a full URL parked in a comment is still a finding.

A third correction worth recording: Chromium's text for an aborted subresource is
`"Failed to load resource: net::ERR_FAILED"` and **names no URL**, so a text-only
exemption would also have absorbed a failed load of a *page* asset — the one thing
AC-391 must not excuse. The handler records `(text, location.url)` and exempts by the
located URL.

### Where it disagrees with the card, measured

**AC-392's "the only analytics endpoint" is singular and the integration is two
origins** — the count endpoint and the script host `gc.zgo.at` — plus a pre-existing
third external reference that is not analytics at all: `player/vercel.json`'s
`$schema` → `openapi.vercel.sh`, the only absolute URL in the player tree at the cut.
**A scanner enforcing "one endpoint" would have red on a file CARD-283 shipped.** So
the doc carries two allow-list blocks, runtime (2) and non-runtime (1, declared as an
editor hint nothing fetches), and the scan is held to their union. The AC's intent is
met; its count is not literally satisfiable. **AC-392's wording is owed an
amendment.**

**`scripts/impact_set.py --base 464ae377` returns `FULL`** — measured, not guessed:
`player/` is not in its `KNOWN_ROOTS` (`src/ tests/ meta/ docs/ scripts/
migrations/`), and an unmodelled path returns FULL by design. **Fail-closed, not a
defect**, but it means this card has no narrowed impact set and the merge gate is the
only full reading.

**One existing test was edited and it had to be**:
`test_the_registrys_refs_for_this_file_resolve_or_are_card_285s` — CARD-284's
ref-bookkeeping test, which **asserted the three CARD-285 refs were absent**
(`assert refs - defined == card_285`). It could not survive this card landing. No
Playwright suite body was touched.

### Corrections to the orchestrator's brief

- **The brief's "57 tracked files" for ADR-0006/R1's ref: mine reproduces, the
  round's 53 does not.** Settled: all tracked **80**, under the validator's pathspec
  **57**, non-Markdown-only **57**, `*.py` **1**. The round's sharper point stands —
  that single `.py` hit is **prose, not the definition**.
- **The round's qualifier on AC-390/391's "zero resolvers" is unnecessary**, though
  honestly flagged as unverified: the validator excludes `meta/architecture`, so
  `requirements.yml` and `trace.yml` do not resolve, and `CARD-285.md` is `.md`.
  Zero is right.
- **The `setrlimit` skip is at `:1297`** — `:1296` is the `if verdict != "bites":`
  guard. The brief had it wrong, twice now.
- **Card item 4's instruction to "note on CARD-210" is a `meta/` edit** the brief
  forbids. Correctly not done and reported instead.

### What CARD-210 now has, and what it still lacks

`docs/deploy/player.md`'s `qr-url-shapes` block is machine-readable and **held to
`vercel.json`'s rewrite sources** — the authority a host actually routes by — by
`test_the_qr_url_shapes_here_are_the_shipped_routes`. The reasoning is the right one:
**a QR code printed in a book cannot be fixed by a redeploy.** What is still missing
is the **base**, explicitly marked `TODO(owner), NOT observed`. CARD-210's remaining
blocker is one owner action: create the Vercel project and write the domain into that
one line. **CARD-210 was not flipped** (G-4).

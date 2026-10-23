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

1. **Static hosting.** Deploy `player/` + the exported bundle to a static host
   (the spec names Cloudflare Pages / Vercel / Render static site — free, no
   cold starts; the deciding constraint is that a QR scan from a book must load
   instantly, which rules out the sleepy admin service). Creating the account
   and picking the provider/domain is the **owner's** action; this card
   delivers the deployable artifact (one directory that IS the site), a
   `scripts/` helper that assembles it (player files + bundle + copied
   `solver_state.js`), and the deploy doc.
2. **`docs/deploy/player.md`** — what runs where, how a new bundle gets
   published, and what is owner-managed vs repo-managed, in the same spirit as
   docs/deploy/render.md (which exists precisely because an undocumented
   dashboard-managed deploy bit this project before).
3. **Usage counting, privacy-first** (spec "Usage tracking"): the per-book slug
   in the QR URL is the primary signal (which book drives visits); a
   privacy-friendly analytics script — Plausible or GoatCounter — gives visits,
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

Spec-derived (owner doc 2026-10-23).

- AC-1: Given a checkout with an exported bundle, when the assembly script
  runs, then one output directory contains everything the site serves —
  player pages, bundle JSON, shared state module — and serving that directory
  with a plain file server passes CARD-283/284's Playwright suites unchanged
  (test: tests/test_public_player_pages.py::test_assembled_site_is_self_contained).
- AC-2: Given any player page with the analytics script unreachable, when the
  page loads, then the game and navigation work and no uncaught error reaches
  the console (test: tests/test_public_player_pages.py::
  test_pages_work_with_analytics_blocked).
- AC-3: Given the assembled site, when its files are scanned, then no code in
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

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. (check: review-lens)
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. (check: review-lens)
- ADR-0039/R1 — A set a guard consults needs a completeness test written before the set, and any claim the guard makes about what it catches needs a control that can fail: caught WITH the set member present, missed WITHOUT it. (check: test_the_control_for_each_spelling_depends_on_the_set)
- ADR-0039/R2 — A guard's set is derived from an authority the runtime can enumerate, not hand-written. (check: test_the_guard_sets_are_derived_and_not_hand_written)
- ADR-0039/R3 — An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT absorb — caught with the exemption removed, missed with it in place — is held to an equality against the sites that exist ... (check: test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form r... (check: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. (check: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an e... (check: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)

## Architecture context

- **FR:** — (untraced enabler; the public-surface FR and hosting ADR are owed
  by the architect delta blocking CARD-283)
- **ADR:** ADR-0006 (baseline unchanged); the hosting choice itself is ADR
  material for the owed delta
- **Components:** — (public surface component registered by the same delta)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

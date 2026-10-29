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
  it reads, stores, or transmits a visitor IP, and the only analytics endpoint <!-- SUPERSEDED 2026-10-29: fix round 1 reworded AC-392 in `requirements.yml`, because "the only analytics endpoint" is SINGULAR and the integration is two origins, plus a pre-existing non-analytics `$schema` reference. The live wording is the registry's: no reference names a visitor IP or per-visitor identifier; every external reference is one `docs/deploy/player.md` declares, in its runtime allow-list for what a browser fetches or its non-runtime allow-list for what nothing fetches at page load; AND A REFERENCE SHAPE THE SCAN CANNOT CLASSIFY IS A FAILURE. That last clause is the one F-002, F-005 and F-006 each broke, and an AC that does not say it cannot notice. The sentence below is the retired one. -->
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
  by anything this card ships (spec "Usage tracking"; behavioral — **AC-392** is its <!-- CORRECTED 2026-10-29, fix round 1's F-009: this named "AC-3", which FR-045 does not have -- stale from the 2026-10-23 renumbering. Confirmed: no copy of the stale name exists in any file this card owns. -->
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
AC-391 must not excuse. The handler records `(text, location.url)` and exempts by
matching an allow-listed **host** against **text OR reported location**.
<!-- CORRECTED 2026-10-29, fix round 1's F-007: this paragraph said "exempts by the
located URL", and so did the orchestrator's brief and the round's own docstring. The
predicate is `host in entry[0] or host in entry[1]`. The property survives — the
mutant was killed — but three documents described a mechanism the code does not have,
which is how a reader comes to trust the wrong half. -->

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

## [Review cycle 1 — 7.0, DOES NOT CERTIFY, 2026-10-29]

`min_score: 8`, cycle 1 of 3. **Three gating findings, all verified by the
orchestrator, none larger than two lines** — and **two of the three hit the exact half
of the argument the round says carries ADR-0041/R6: "the egress set is closed". It is
not closed.** The card does what it was for; three ACs that had no definitions now
have mutation-resistant tests and AC-392's false alive is gone.

### F-001, GATING — AC-390 makes the suite phone home

`test_assembled_site_is_self_contained` serves the **counted** tree and drives
Chromium with **no route interceptor**. Verified: `page.route` appears **exactly once
in the whole file, at `:2489`, inside AC-391** — AC-390 has none. The reviewer taped
that journey at HEAD:

```
TOTAL REQUESTS 19   NON-SAME-ORIGIN: [<the script host>/count.js]
FOREIGN RESPONSES: three HTTP 200s, every run
```

So a test makes **live third-party requests**, contradicts `docs/deploy/player.md`'s
own drift step 4 (*"Do not count locally"*), depends silently on a vendor's
availability, and **re-introduces from the test side the exact shape CARD-283/284's
four same-origin controls forbid**. Fix: the two lines AC-391 already has. Verified
green at 33 passed.

### F-002, GATING — the comment stripper eats protocol-relative URLs

`_COMMENTS`' `re.compile(r"(?<!:)//[^\n]*")` at `:2006` guards only `://`, so in
`src="//host/x"` the **quote** precedes the `//` and the whole reference is blanked;
`_ABSOLUTE_TARGET` needs `https?://` and misses it too. So `classify()`'s entire `//`
branch and `_URL_LITERAL`'s protocol-relative alternative are **unreachable dead
code**, and both of these are **silent passes** on a copy of the clean counted site:

```
<script src="//evil.example/t.js">              -> SILENT PASS
@font-face{src:url("//evil.example/f.woff2")}   -> SILENT PASS
```

That falsifies `scan_site`'s own docstring (*"never a silent pass … the one property a
denylist-shaped guard cannot have"*), the deploy page's equivalent claim, **and
ADR-0039/R2's default-deny *condition*** — which is the escape clause the whole
hand-written-set exemption depends on. Fix: one character class,
``(?<![:"'`])//[^\n]*``.

### F-003, GATING — a landmine aimed at this board's own sync

`test_the_deploy_page_is_the_only_place_that_holds_an_endpoint` runs
`["git", "grep", "-l", "--fixed-strings", url]` — verified, **no pathspec, no `--`** —
and asserts `files == [DEPLOY_DOC]`. **Review YAMLs sync into `main`, so cycle 2's own
report would break the suite the moment it quoted the URL.** Fix: `[… url, "--",
":!meta"]`, verified green with a probe staged.

**The reviewer deliberately spelled neither endpoint, and the orchestrator verified
its YAML before syncing: 0 occurrences of either.** Also measured: **0 tracked files
on `main` hold either full endpoint**, so the mine is not armed today.

**But the orchestrator came within one path segment of arming it.** This card's own
round record at `:212` names the script host as a bare host while recording the
two-origin finding. The test greps the **full** URL with `--fixed-strings`, so a bare
host does not match — margin of one path segment, in a tracked card file, written
while documenting the very hazard. Same shape as `dispatcher.state` resolving phantom
refs: **the file that records a trap is inside the trap's domain.**

### The strongest thing in the card, driven rather than argued

**The counted-vs-uncounted byte assertion genuinely constrains.** Three widening
mutants, each killed at a **different** line: a `<link rel=preconnect>` → `:2404`; a
page counted but omitted from `report.counted` → `:2399` **and** AC-392 at `:2589`; a
non-html file changed by counting → `:2399`. A second tag cannot even be built.

**And my "the deployed tree is never the tested tree" is FALSE as stated.** The
counted tree is browser-driven by **both** new tests. The real residual is narrower —
no browser-observed request-**set** closure on the counted tree — and the reviewer
judges it adequately covered by composition. The genuinely uncovered part is the
vendor script's own behaviour, which is DEC-046's premise and untestable offline **and
which F-001 means the suite currently exercises for real while asserting nothing.**

### The edited bookkeeping test kept its teeth, and gained some

A fourth undefined ref reds it at `:1919`. The pre-edit form also caught a fourth, so
**nothing was lost**, and `refs & defined == card_284 | card_285` now pins the
intersection exactly. The one direction neither version covers is the docstring's own
wording — pre-existing, a wording fix, not a finding. **No Playwright suite body was
edited**: `tests/` has exactly one file in the diff.

### The declared/derived split — not a denylist in derivation's clothes, but R2 is unsatisfied

The derivation is **real**: references from the tree, the permitted set via the *same*
`driver.allow_list` the deploy command calls, routes via CARD-283's `rewrites()`, and
nothing a literal in the test. The unenumerable-set argument is correct and
well-evidenced (the 7 grid fingerprints reproduce exactly, 5 in `solver_state.js` + 2
in `play.js`). **But R2's escape clause is conditional on default-deny, and that is
where it fails** — four measured silent passes between F-002 and F-005. **And the
bound is not stated where a reader meets the claim: the deploy page states the
opposite** (F-008).

### Non-gating, worth the fix round

- **F-004** the comment-stripping exemption has **no control** for what it must not
  absorb (ADR-0039/R3; the claim is true, untested, 4 lines).
- **F-005** shapes the scanner never looks for are silent passes:
  `el.src = atob(…)`, `new Worker(…)`, `new Image().src = …` — same R2 breach by a
  different route.
- **F-006** the two allow-list blocks are a **flat union**, so "non-runtime, nothing
  fetches it" is documentary only — a live `<script src="…/vercel.json">` planted in
  the site scans **clean**.
- **F-009** G-3 names "AC-3", which **FR-045 does not have** — stale from the
  2026-10-23 renumbering; it should be AC-392.

### Corrections, including two to the orchestrator and one that is nobody's error

- **The "exempts by the located URL" claim is wrong in BOTH my brief and the round's
  record.** The predicate is `host in entry[0] or host in entry[1]` — **text OR url**.
  The property survives (the mutant was killed), but the mechanism is not what either
  document says.
- **The brief's load figure of 22.25 was stale rather than wrong.** The reviewer
  measured 6.59/13.31/11.00 and nothing was slow. Load is time-varying: mine was real
  at dispatch with two cycles running, theirs real later. **The lesson is that a load
  figure does not belong in a brief at all** — by the time it is read it describes a
  different machine. Same shape as the `setrlimit` line number: a measurement without
  its moment attached is not a fact.
- **`setrlimit` is `:1297` and the brief was right this time** — consistent with the
  commit-dependence established on CARD-299.
- ADR-0006/R1's ref: **80 tracked / 57 non-md / 1 `.py`, and that one is prose** in a
  docstring at `tests/test_admin_serving.py:134`. **My 57 confirmed a third time.**
- Everything else reproduced: 66/0, 22+44, no Chromium skip, `db_required` 26 by
  collection, `impact_set` → FULL, node ids **9748 → 9755, +7/−0** re-derived from a
  scratch worktree at the cut, `src/` 0 lines, `pyproject.toml` absent.

**Hygiene for cycle 2: until F-003 is fixed, no report may quote either endpoint.**

## [Fix round 1 — all three gating findings closed, plus F-004…F-008, 2026-10-29]

`af160fd5` → **`79ecafcb`**, two commits. This round **3 files, +328/−39**; whole card
vs the cut **7 files, +1873/−26**, with `src/` and `pyproject.toml` **absent from the
diff entirely** — verified at 0 files. Nothing under `meta/kanban/` or `meta/review/`.

**All three gating fixes verified independently by the orchestrator:** `page.route`
now appears **twice** (AC-390 has one), the lookbehind at `:2019` is
``(?<![:"'`])//[^\n]*``, the pathspec at `:3042` is
`["git","grep","-l","--fixed-strings",url,"--",":!meta"]`, and AC-392's new wording
round-trips through `yaml.safe_load` with the **default-deny clause present**.

- **F-001** — the suite no longer reaches the vendor. Tape with the interceptor
  toggled: **3 foreign HTTP 200s before, 0 after and 3 aborts instead**, reproducing
  cycle 1's 19-request tape exactly. AC-390's own assertions unchanged; two added so
  an interceptor that caught nothing cannot pass. Mutant killed at `:2571`.
- **F-002** — both silent passes are now failures, measured pre/post on the same
  minimal tree in a throwaway worktree, and **the real tree stays clean**. Mutant
  killed at `:2816`.
- **F-003** — the mine is defused and the defusal is driven: with a probe YAML staged,
  no-pathspec fails and `:!meta` is green; the mutant reds with exactly the landmine's
  output. **`:!meta` is argued rather than assumed**: what must not hold a second copy
  is a file the site or tooling *reads*, and `meta/` is bookkeeping that quotes an
  endpoint while describing it — and it is the board's own sync path.
- **F-004…F-008** all taken: the comment-stripping exemption now has its
  both-directions control; `Worker`/`SharedWorker` and a `_PROPERTY_SINK` close the
  unreadable-sink hole; the two allow-list blocks are **no longer a flat union**, with
  a second control showing the static block's member is what permits `vercel.json`'s
  own `$schema`; and the bound is now stated in the deploy page's *Usage counting*
  section **immediately after the R6 claim**, with drift step 4 extended to say the
  "do not count locally" rule **binds the test suite too** — the record F-001 was
  owed, so the finding cannot come back when only code changes.

**7 of 7 mutants killed, no survivors**, all in a throwaway detached worktree with
blob and tree hashes asserted back after every one and the worktree removed
afterwards. **Node ids 9748 → 9755, +7/−0 — this fix round added and removed no
node**: every new control went inside an existing test. Zero skips in every run; no
Chromium skip; `db_required` 26 by collection.

### The correction worth carrying into the next brief

**A probe whose value another pattern already reads measures the other pattern.** The
round's first `Worker` control was `new Worker("//evil.example/w.js")`, and the mutant
that drops `Worker` from `URL_CALLS` **SURVIVED** it — because `_URL_LITERAL` reads any
quoted `//host/…` whatever call surrounds it. The probe was a control over the wrong
line. It is now the unreadable form, `new Worker(spec)`, which only the call name can
reach, and the survival is recorded in the test's own comment. That is commit
`79ecafcb`, and it is ADR-0039/R1 landing on the fix round's own work.

### Card-side corrections the round reported and the orchestrator owed

Applied above: **F-007**'s mechanism (`host in entry[0] or host in entry[1]` — text OR
reported location, which **three** documents described wrongly), **F-009**'s G-3
naming a non-existent AC-3, and a superseded note on the card's own AC-392 sentence.

### Four corrections to the orchestrator's brief, one of which is the third instance of a pattern

1. **`_conditional_silences` is defined at `tests/test_suite_profile.py:2743`, not
   `test_guard_integrity.py`** — which only mentions it in prose at `:1518`. **The
   orchestrator had this right first**, then accepted a correct report that
   `_module_scope_silences` (`:1511`) and `_check_log_invocations` (`:577`) live in
   `test_guard_integrity.py` — **two sibling functions, not that one** — generalised
   it to the third, and wrote the wrong location into two fix briefs **and into
   CARD-315's G-6, which had already shipped to `main`.** Corrected there.
2. The Chromium `pytest.fail(` is at **`:551`**, not `:550` (`:550` is the
   `if not Path(...).exists():` guard). The second site, `:676`, was exact.
3. **F-001 is not "two lines"** — it is four plus two assertions, because an
   interceptor whose non-empty set is not asserted passes a run in which nothing was
   blocked. The orchestrator carried "two lines" from cycle 1 without pricing it.
4. **The hygiene rule can be lifted.** With `:!meta` the `git grep` cannot see `meta/`
   at all, so neither the card record at `:212` nor a cycle-2 report can red the
   suite. Kept regardless for this round: neither full endpoint appears in either
   commit message or in the report.

---

## Fix round 2, 2026-10-29 — `76cfba58` → `6caccb65`, 3 commits, 4 files +436/−82

**Cycle 2's gating finding is closed, and the fix is not the one that was asked
for.** The brief and the review both framed F-101 as a lookbehind problem on the
two DOTALL block forms. The round took the lookbehinds **and** then took the
comment stripper **off the egress path entirely**, on cycle 2's own reasoning that
fixing only the reported instance is the pattern this board keeps repeating:

- **RAW text** (comments included) is now read by every pattern whose miss could
  be a channel — `_ABSOLUTE_TARGET`, the new `_HOST_LITERAL`, `_ATTR_TARGET`/
  `_CSS_TARGET`, `_PROPERTY_SINK`, the `URL_CALLS` loop, and `IDENTIFIER_SHAPES`.
- **STRIPPED text** is read by only two — `_IMPORT_TARGET` and the new
  `_ROOTED_LITERAL` — which are precisely the two patterns both *measured* false
  positives came from, and the only two whose misses cannot be egress: a module
  specifier or a rooted path resolving to nothing is a lost `unclassifiable`,
  never a lost `foreign`.

`_URL_LITERAL` was one pattern doing both jobs, which is why it is split.

**Nine swallow plants, each asserted four ways** (the shipped scan reports it; the
**pre-fix** stripper destroys it, so the plant really is the swallow shape; the
**shipped** stripper does not; and the scan reports it with the pre-fix stripper
patched back in, so the split is what carries the fix). **12 of 12 mutants killed,
no survivors.**

**The round's own first pass found two of its own raw reads uncontrolled** — moving
`_ATTR_TARGET`/`_CSS_TARGET` and `_PROPERTY_SINK` back to stripped text **survived**,
because a quoted `//host` is read by `_HOST_LITERAL` whatever surrounds it (fix round
1's `Worker` lesson again). So three of cycle 2's four plants were controls over the
wrong line. Five new plants exist as shapes **no other pattern can read**. That
survival is recorded in the test's own comment rather than quietly repaired, because
it is the same defect class as the finding.

**The honesty is restored rather than narrowed.** `_without_comments`' docstring now
states the residual that *can* still hide a finding — a delimiter is recognised by
the single character in front of it, so an opener after an unguarded character still
blanks a region, and the block forms cross lines — and then states what bounds it.
The same paragraph is in `docs/deploy/player.md`. Fix round 1's "the safe direction"
sentence is kept but is no longer the only thing declared.

**F-102 taken (6 lines) — and it closes the measured instance of CARD-308's hazard
that lived in this very module.** The guard now collects every whole
`tests/<this file>::(\w+)` the module docstring spells and holds that set to the
`def`s in the file, so **a ref whose authority is an ADR is held for the first time**.
Mutant M10 — cycle 2's survivor, a one-character rename of ADR-0041/R2's exemption
node — now **kills**. The docstring's claim that "the defining module is the one
place that cannot lose it unnoticed" is true as held for the first time.

**F-103 taken by inverting the flag, not by prose.** `--no-analytics` is now
**`--analytics`**: counting is opt-in, the default tree is the uncounted one every
fixture assembles, and "do not count locally" is the shape of the command rather than
something to remember. A new hold derives the flags the deploy page backticks from
the helper's own `--help` and asserts argparse accepts them — nothing held those two
to each other before. **⚠ This changes the documented deploy procedure: the publish
command now needs `--analytics`. OWNER DECISION PENDING — see below.**

F-104, F-105, F-106 and F-107 all taken. F-106 closes a probe asked for in three
consecutive cycles.

### Three refusals, each with a measurement

1. **Cycle 2's recommended F-104 assertion is tautological** — `hosts` is *defined*
   as the expression the assertion compares it to, two lines above, so it cannot fail
   under any mutation. A non-tautological equality derived from `REQUIRED_RUNTIME`
   went in instead, driven by M11.
2. **Cycle 2's "stronger and simpler alternative" for F-101 reds the real tree.**
   Applied exactly as recommended in a throwaway worktree, the scan **fails on the
   clean counted site** on the documented panel path sitting inside a `//` comment —
   one of the two measured false positives the stripper exists for, and the exact
   shape the round's own control asserts must be missed.
3. **`/` was not added to the `//` form's lookbehind.** `\\` alone closes the
   regex-literal shape (M9 measures it); `/` would widen the guard with no plant
   behind it.

### Node ids, and a correction to the orchestrator's brief

**9748 → 9771, +23/−0** against the cut. Of the 23, **7 are this card's** — the same
seven cycle 1 lists — and **16 arrived from `main`** through the merge taken before
this round. The round's own delta is **+0/−0**: every new control went inside an
existing test. **The brief's "9748 → 9755" was the pre-merge number and 9755 no longer
exists on this branch.**

### What the orchestrator got wrong, and it cost the round a run

**The brief's F-101 table row said the regex-literal plant swallowed a *following*
`fetch(...)`.** The `//` form's strip ends at the newline, so a `fetch` on the **next**
line survives the pre-fix stripper — the round's first plant put it there and its own
control correctly refused it as "not the swallow shape". Cycle 2's plant has both on
**one** line and its measurement stands; the orchestrator's paraphrase of it did not.

Also narrower than the brief implied: cycle 2's "the block forms have no guard at all"
is right about line-crossing, but **three of the four silent passes are block forms and
the fourth is the `//` form cycle 1 "fixed"** — the regex-literal miss is a `//`-form
miss.

### The residual, declared

A comment delimiter opened from an unguarded character still blanks a region for
`_IMPORT_TARGET` and `_ROOTED_LITERAL`. **Cost: a lost `unclassifiable` — a dangling
internal reference — never a lost `foreign`.** Not closable without re-admitting the
two measured false positives, which refusal 2 measures. Declared in the stripper's
docstring and in `docs/deploy/player.md`.

### OWNER DECISION 2026-10-29: the flag inversion is KEPT

`--analytics` (opt-in, counting **off** by default) stands, and the publish command
in `docs/deploy/player.md` carries the flag. The reason it was taken is the reason it
is kept: the card claimed *"default-off… every local run, no tag is written"* and that
claim was **false** while the flag was opt-out, so the inversion makes the claim true
structurally rather than by remembering a flag.

**The cost is accepted and named**: a real publish can now go out **uncounted** if the
flag is forgotten, where before it could go out **counted by accident**. The owner
chose the direction that fails toward not-counting, which is the direction that cannot
put a visitor in a log nobody intended. The hold added by fix round 2 — the deploy
page's backticked flags derived from the helper's own `--help` and asserted to be
options argparse accepts — is what stops the documented command and the helper from
drifting apart again, and it is mutation-driven (M12).

Review cycle 3 dispatched on this decision, so the reviewer judges the tree the owner
chose rather than one it might replace.

---

## Review cycle 3 — the LAST — 7.5, DOES NOT CERTIFY

Cycle 1 → 7.0, cycle 2 → 7.5, cycle 3 → **7.5** against `min_score: 8`.
`max_cycles: 3` is spent. **One gating finding, and it is a measured silent pass of
an egress reference.**

### F-201 (GATING) — the load-bearing claim is false in the under-claim direction

Fix round 2's whole design rests on *"the two patterns reading stripped text are the
only two whose misses cannot be egress — a lost `unclassifiable`, never a lost
`foreign`."* **Measured false**, by a route no cycle had looked at:

- **`_ROOTED_LITERAL` is not an internal-only reader.** It matches any quoted value
  whose first character is `/`, **including one beginning `//`**, and `classify()`
  routes every target beginning `//` down the **absolute branch → `foreign`**.
- **`_HOST_LITERAL`, the raw reader of that form, requires the authority's last label
  to be 2+ ASCII letters.** So for an authority that is **not** a dotted letter-TLD
  name, the only reader outside a markup/CSS/sink/call position is the **stripped** one.

Combine that with the round's own declared residual — an opener after an unguarded
character still blanks a region — and **four `foreign` references pass silently**, each
planted alone with the baseline asserted empty in the same run: an `import` of a
`//`-prefixed **IPv4** host behind `const open = "x/*"`; a bare CSS `@import` of one
behind `a{content:"x/*"}`; a **single-label** host (`//intranet/…`); and a **bracketed
IPv6** host. Controls in the same run isolate the cause to *both* ingredients — the same
references with **no comment** are caught; the same residual with a **dotted letter-TLD**
host is caught; the IPv4 host in a `src=` behind the same residual is caught.

**The fix is ONE LINE and the reviewer measured it**: relax `_HOST_LITERAL` to
`(["'`])(//[^/"'`\n][^"'`\n]*)\1`, still reading raw. The real counted site stays clean
in all three buckets, all four passes become `foreign`, both player modules **66 passed**
— and it makes the claim true as written.

**So the residual's cost statement is understated in two places** — the stripper's
docstring and `docs/deploy/player.md`, whose *"every quoted `//host` … is read from the
file as written"* is true only for dotted letter-TLD authorities. **A declared residual
with an understated cost is worse than an undeclared one.**

### F-202 (medium) — the owner's accepted cost has a SURVIVING mutant

The owner kept the flag inversion with one condition in mind: the new hold stops the
documented command and the helper from drifting apart. **It only half does.** The hold
holds the page's **backticked prose** to argparse's option set — renaming the option
**kills** it — but the publish command sits in an **indented block**, so its flags never
enter `page_flags`, and `--analytics` is satisfied by two *prose* mentions.
**Deleting ` --analytics` from the documented publish command leaves both player modules
at 66 passed — SURVIVED.** That is exactly the drift the decision was conditioned on.
~3 lines.

### Everything the cycle verified

Both of fix round 2's refutations of cycle 2 **reproduce**, and refutation 2 is the
strongest argument on the card: recompiling the scan with the rooted read on raw text
**fails on the clean counted site** on a documented panel path inside a comment, and
dropping the stripper entirely brings the second measured false positive back. **The
stripper genuinely cannot be removed.** Refutation 1 confirmed: cycle 2's recommended
assertion is True by construction, and the replacement can fail.

**All five new plants are genuine one-line controls** — each disabled raw read loses
exactly one plant and only its own. **F-102's guard catches the docstring-only
direction**: a phantom whole `path::name` inserted into the table, defined nowhere, is
killed, and the "arm is reached" control is non-vacuous. F-105, F-106, F-107 all confirmed.

### Three corrections, one of them the orchestrator's

- **"Nine plants, each asserted four ways" is three** (F-204): assertion (a) is
  **subsumed** by (d), because the shipped stripper blanks a subset so shipped findings
  ⊇ pre-fix findings. Worse, (a) matches on **filename**, and three plants open with a
  decoy that `_ROOTED_LITERAL` itself reports as `unclassifiable` in that same file — so
  for the two plants whose declared bucket *is* `unclassifiable`, (a) is satisfied by
  their own decoy with the controlled read entirely removed. **The controls survive; the
  count was one high.**
- **AC-391's own comment describes a mechanism the code lacks** (F-205) — with the two
  endpoints collapsed, *both* assertions pass, and the case is harmless anyway because
  the route pattern is host-keyed so one pattern aborts both. **The fourth document on
  this card to describe behaviour that is not there.**
- **The orchestrator's brief cited stale line numbers for F-107's two arms** — they are
  cycle 2's numbers at `79ecafcb`, not this HEAD's. Carried, not measured, again.

### What ships UNREVIEWED, stated because the cycles are spent

**The full suite — never run in three cycles.** The merge gate is the only full reading
this card will get, and **16 node ids that arrived from `main` were never run by it**.
Also: everything the pre-round merge brought; the rest of `docs/deploy/player.md`;
`player/play.html` (+24) and `scripts/README.md` (+31) read but not driven; authority
shapes beyond the four planted (percent/unicode-encoded, userinfo, port-only — the
measured one-line fix covers them by construction but they are unmeasured); and AC-390's
counted-tree request-**set** closure.

---

## Fix round 3 — under the owner's decision, no cycle behind it — `6caccb65` → `9140739f`

Two commits, two files (`tests/test_public_player_pages.py`, `docs/deploy/player.md`).
`git diff --name-only 464ae377..HEAD -- src/ pyproject.toml` → **0 lines across the whole
card**. Scope held: no new finding of substance was fixed, and the ones found are reported
below instead.

### F-201 closed — and the three "covered by construction" shapes are now MEASURED

The one-line change, `_HOST_LITERAL` → `(["'`])(//[^/"'`\n][^"'`\n]*)\1`, **still read
raw**. The real counted site stays clean in all three buckets, proven twice by two
independent equalities over two independent copies of the assembled tree.

**Seven authority shapes, each planted ALONE** into a copy whose baseline is asserted empty
in the same run, each asserted three ways — the shipped stripper really does blank the
region (so the plant is the declared residual, not a reference with a comment nearby), the
shipped scan reports it `foreign` **matched by needle rather than filename**, and the narrow
pattern patched back in makes it a **silent pass in every bucket**: IPv4 in an `import`,
bare CSS `@import`, single-label authority, bracketed IPv6, **percent-encoded**,
**userinfo**, and **port-only**. The last three are exactly what cycle 3 could only call
*"covered by construction"* — the narrow pattern misses all three because `[A-Za-z0-9.-]+`
cannot cross `%`, `@` or `:`, checked by hand as well as by run.

The **three isolating controls** are each asserted caught **under the narrow pattern too**,
which is what keeps the cause attributed to *both* ingredients rather than either alone.

**The false claim lived in FOUR places, not the two the orchestrator's brief named.**
Besides the pattern block, the stripper's docstring and the deploy page, **`scan_site`'s own
docstring carried the same proposition in shorter words** — *"the two whose misses are
internal"* — and **no report or brief mentioned it**. All four corrected, and the deploy
page states the correction rather than quietly rewriting it.

**What remains unread, stated in both documents:** an **unquoted** `//authority`, refused on
purpose with the argument already on the module (a bare `//` is a comment far more often
than a reference). `///path` is **not** in that gap — empty authority, resolves to the
serving origin — which is why the fix requires a non-slash, said where the pattern is defined.

### F-202 closed — the owner's condition now has teeth

The hold reads the publish **command**: it finds every line mentioning the helper, glues
backslash continuations, asserts the page documents an invocation, asserts the command's
flags are a subset of argparse's options, and asserts the opt-in flag is on it.
**Cycle 3's surviving mutant is killed**: deleting ` --analytics` from the documented
command now gives **1 failed / 65 passed** where cycle 3 measured **66 passed**. The
argparse direction got stronger too — a one-character rename reds **two** nodes.

### The three corrections, landed in code rather than in a report

- **F-204**: now stated as **four assertions, three independent**. (d) was kept with a
  reason — the plant is reported on the tree that *ships*, not only under a patched stripper
  — and **both (c) and (d) now match by needle as well as filename**, which closes the decoy
  self-satisfaction. Proved: with the CSS read disabled, (d) now reds where cycle 3 measured
  it passing with the controlled read entirely removed.
- **F-205**: AC-391's comment now says what the assertion buys, and records that the
  scenario it used to name is passed by both assertions and harmless anyway, because the
  route pattern is host-keyed so one pattern aborts both endpoints.
- **F-203**: `IDENTIFIER_SHAPES` is off the "can hide EGRESS" list in **both** places that
  carried it, with its real reason stated.

### It declared a cost of its OWN fix rather than leaving it to be found

The relaxation is stricter as well as broader: a quoted value that merely *begins* `//` —
`"// TODO"` parked in a string — is now a `foreign` finding where the narrow pattern said
nothing. **A false positive, not a silent pass**, so it fails in the direction this guard is
built to fail — but an undeclared cost is the defect class this card has been punished for
three times, and the first commit corrected two understated cost statements while
introducing one. The second commit declares it in both places, with the measurement:
**`player/**` holds no quoted value beginning `//` at all**, and the counted site scans clean.

### Two things it found that no report had

- **The code and fix round 2's record disagreed with each other about the plant count, and
  cycle 3 only measured the record.** The record said "four ways"; the *code comment* said
  "asserted three ways" while the code makes four assertions. The module was already wrong
  in the **opposite** direction from the record. Both now agree.
- **Cycle 3's F-204 recommendation does not add up** — "three assertions plus two
  text-level checks" is five items for four assertions. The structure was implemented, not
  the phrasing.

### Node ids, skips, and the two honest reservations

**+0/−0 this round** (9771 unchanged; every addition went inside two existing test bodies).
**Zero skips in every run**; a grep for `pytestmark|skipif|pytest.skip|xfail|importorskip`
across both player modules and both scripts returns **no hits at all**. Four mutants, all
killed, all in throwaway worktrees with blobs asserted back.

**Its own reservations, which are the right ones:** the **full suite has not been run by any
cycle of this card**, and the branch carries **16 node ids from `main` that no cycle has
exercised**. The merge gate is the right place for both.

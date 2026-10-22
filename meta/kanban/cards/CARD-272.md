# CARD-272: The import guard gains the composite-capability rank (ADR-0040)

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d  <!-- guard/claim card: the 0.75d claim-card floor applies, and every figure here needs a control -->
**Complexity:** architectural  <!-- first implementation of ADR-0040: this card turns the decision into the reference mechanism -->
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/272-composite-capability-rank
**Worktree:** —
**Source:** meta/architecture/decisions/adr/0040-book-production-composite-capability-rank.md (DEC-043, 2026-10-22; Migration: rewrite). Delta carded directly, no handoff increment — same posture as the 2026-10-03 delta.
**Idea:** —
**Wave:** —
**Created wave:** 54
**Deferred waves:** 0
**Depends on:** CARD-265
**Touches:** tests/test_cli.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

ADR-0040 adds a fourth tier to ADR-0007's rank table: the **composite-capability
rank**, between the orchestrator and the capabilities. This card teaches the
guard that tier. The guard lives entirely in `tests/test_cli.py`, so this card
edits that one file and **nothing under `src/`** — the tier's first resident,
`src/nonogram/book/`, arrives only with CARD-273, and the guard must stay green
on today's book-less tree.

Concretely:

1. **Rank table.** Insert the composite rank between `_ORCHESTRATOR_RANK` and
   `_CAPABILITY_RANK` (renumber as needed — the meta-tests must pin the
   *relationships*, not the absolute values).
2. **Membership is a pinned literal, default-deny.** `_COMPOSITES =
   frozenset({"book"})`, mirroring `_ADAPTERS`: the fallthrough rank stays
   capability, a name joins the composite rank only by a deliberate edit to the
   pin, and the pin has a walk-side assertion the way `_ADAPTERS` does. (The
   name-based `_rank()` resolves `"book"` now even though no such package
   exists on disk yet — the rule function is pure in the module name.)
3. **The one deny pin.** The pure rank comparison (`rank(imported) >
   rank(importer)`) makes `orchestrator → book` LEGAL (composite is deeper than
   orchestrator), and ADR-0040/R2 forbids exactly that edge. Add a pinned deny
   edge — the mirror image of `_LAUNCH_EDGE`'s single allow edge — so the
   generation pipeline can never grow a dependency on book production.
   `capability → book` needs no pin: it is outward by rank and already
   forbidden.
4. **The edge truth table, as committed cases** in
   `test_the_import_rule_rejects_each_forbidden_edge` /
   `test_the_import_rule_allows_the_legitimate_edges`:
   - allowed: `cli → book`, `web → book`, `admin → book`; `book → clues`,
     `book → difficulty`, `book → export`, `book → db`, `book → errors`,
     `book → limits`.
   - forbidden: `book → cli|web|admin`, `book → orchestrator`,
     `orchestrator → book` (the deny pin), `solver → book` and
     `export → book` (capability → composite, outward by rank).
   - the composite-sibling ban is the same-rank rule and is vacuous while
     `_COMPOSITES` has one member — say so where the tier is documented rather
     than committing a case that cannot be exercised.
5. **Meta-tests.** Extend the rank-table degeneration test so a table where the
   composite rank silently collapses into the capability rank (or into the
   orchestrator's) fails, and extend the pin-integrity assertions
   (`test_the_import_walk_actually_sees_the_package` et al.) to hold
   `_COMPOSITES` the way `_ADAPTERS` is held.

## Acceptance criteria

- **AC-1** *Given* the edge truth table above, *then* every allowed edge passes
  the rule function and every forbidden edge reds with a message naming the
  rule that rejects it — each as a **committed case**, not a sweep.
  (test: `test_the_import_rule_rejects_each_forbidden_edge`,
  `test_the_import_rule_allows_the_legitimate_edges`, extended)
- **AC-2** *Given* a line-count-preserving mutant deleting the
  orchestrator→composite deny pin, *then* at least one committed case reds —
  the ADR-0040/R2 control demonstrated by executing the mutant, not by reading
  the code. (test: the same class; certified with `tests/kill_matrix.py`,
  domain of every figure stated)
- **AC-3** *Given* the rank-table degeneration meta-test, *then* a rank table
  with the composite tier flattened away fails it — again shown by the executed
  mutant. (test: the meta-test, extended)
- **AC-4** *Given* `_COMPOSITES`, *then* it is a pinned `frozenset({"book"})`,
  the fallthrough rank for unknown names is still the capability rank
  (default-deny: a new name gets no composite privileges by placement or
  naming), and the pin is asserted by value like `_ADAPTERS`.
  (test: the pin-integrity assertions, extended)

## Engineering constraints

- EC(ADR-0040/R1): the rule function enforces the composite import law — a
  composite may reach only capability-rank and shared-rank modules, and only
  adapters may reach it. test: `test_the_import_rule_rejects_each_forbidden_edge`
- EC(ADR-0040/R2): the generation pipeline never depends on book production —
  the orchestrator→composite deny edge is pinned and has a failing control.
  test: `test_the_import_rule_rejects_each_forbidden_edge` (AC-2's mutant is
  the certification)

## Guardrails

- G-1: `tests/test_guard_integrity.py` unchanged — owned by CARD-266.
- G-2: `tests/README.md` unchanged — owned by CARD-265.
- G-3: **No `src/` edits.** `src/nonogram/book/` is NOT created here and no
  module moves — that is CARD-273's whole job. The suite must pass on a tree
  where the composite rank has zero residents on disk.
- G-4: `_ADAPTERS` stays `{cli, web, admin}`, `_LAUNCH_EDGE` stays
  `("cli", "web")`, and every pre-existing committed edge case passes
  unmodified — this card adds cases, it rewrites none.
- G-5: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-6: No new runtime dependency (ADR-0006/R1); no timing measurements.

## System contract

<!-- PROJECTION assembled by system_rules.py --card CARD-272 (scope: touches), 12 rules, 2026-10-22. Regenerated on every decompose; fix a wrong rule in its source artifact, never here. -->

- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. (check: review-lens)
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. (check: review-lens)
- ADR-0039/R1 — A set a guard consults needs a completeness test written before the set, and any claim the guard makes about what it catches needs a control that can fail: c... (check: test: test_the_control_for_each_spelling_depends_on_the_set)
- ADR-0039/R2 — A guard's set is derived from an authority the runtime can enumerate, not hand-written. (check: test: test_the_guard_sets_are_derived_and_not_hand_written)
- ADR-0039/R3 — An exemption is a claim. (check: test: test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw)
- ADR-0040/R1 — src/nonogram/book/ sits at the composite-capability rank: it imports only capability-rank modules (clues, difficulty, export, db, ...) and shared modules (er... (check: test: test_every_import_in_the_package_points_inward)
- ADR-0040/R2 — The generation pipeline never depends on book production: neither orchestrator.py nor any capability module imports src/nonogram/book/ (CON-019's one-way rul... (check: test: test_the_import_rule_rejects_each_forbidden_edge)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header ... (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its... (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)

## Architecture context

- **FR:** —
- **ADR:** ADR-0040 (R1, R2 — the subject), ADR-0007 (revised 2026-10-22: the
  rank table this card extends), ADR-0019 (the adapter set, unchanged),
  ADR-0039/R1–R3 (every claim this card writes needs a control that can fail)
- **Components:** none — the guard is test-side; no `src/` module changes
- **Trace:** meta/architecture/trace.yml — unchanged; no requirement's
  verifying test moves

## Worktree notes

- **[Sequencing]** CARD-265 owns `tests/test_cli.py` right now (the
  `_ADAPTER_COUNT` fold). This card builds on whatever bound 265 settles —
  start only after it merges, and rebase expectations are in its card.
- **[Board brief rules apply]** A claim states only what its tests demonstrate;
  every new test file/case is shown failing on at least one mutant before
  hand-off; deletion mutants are line-count-preserving; figures carry their
  domain; full-suite runs take the flock on `meta/kanban/.full-suite.lock`.
- **[The deny pin's shape]** `_LAUNCH_EDGE` is the in-file precedent for a
  single directed exemption — one pinned pair, the reversed direction
  committed as forbidden. The deny pin should read the same way, so the next
  reader finds one idiom, not two.

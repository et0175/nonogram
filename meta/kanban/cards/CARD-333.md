# CARD-333: An acceptance criterion has no lifecycle the validator reads — so a retired criterion can only announce itself as a defect

**Status:** blocked
**Priority:** P2
**Category:** tech-debt
**Estimate:** — (not estimable from this repository; the change is in `forge_1`)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** owner decision 2026-10-31, taken on a contradiction CARD-316's round surfaced and the orchestrator measured: CARD-317 and CARD-316 gave the same situation two different shapes 48 minutes apart. The owner chose CARD-316's shape and asked for the validator half to be carded.
**Idea:** —
**Wave:** —
**Created wave:** 72
**Deferred waves:** 0
**Depends on:** —
**Touches:** /Users/omelnikova/MyProjects/forge_1/forge/skills/architect-validate/scripts/validators/ — **outside this repository**
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** owner decision — the code to change is in `forge_1`, not in this repo, and this board has a standing rule never to edit anything under it. Same blocker as **CARD-319**; see "Why this is blocked".

## The defect, measured

**A CON has a lifecycle the validator reads. An acceptance criterion does not.**

Measured 2026-10-31 in the validator of record (`meta/kanban/config.yml:38` →
`forge_1/forge/skills/architect-validate/scripts/validators/requirements.py`):

- `_validate_con_lifecycle` reads a CON's `status:` — an unknown status is an **ERROR**,
  `superseded` without `superseded_by` is an **ERROR**, a superseded CON still carrying a
  `check:` is a **WARN**, and **a superseded CON is exempt from check-ref verification**
  (`utils.con_is_superseded`, whose own comment names its three consumers).
- `_validate_ac_ec_test_refs` walks **every** acceptance criterion carrying a `test:` and
  calls `_check_ref_findings(cs, …, "test", entry["test"], …)` with the **literal string
  `"test"`**. It never reads the entry's own `status:` and never reads its own `kind:`.

So for an AC, `status: superseded` is **prose that no tool reads**, and there is no way to
say "this criterion is deliberately unverifiable" in a form the machine understands.

**Consequences, both observed on this board:**

1. **A retired criterion can only announce itself as a defect.** Either it keeps its
   `test:` key and reports a `DEAD check ref`, or it drops the key and reports
   `acceptance criterion has no 'test'`. **Measured net zero** — CARD-317 found it first
   and CARD-316 confirmed it at seven criteria: seven dead-ref warnings out, seven
   no-`test` warnings in, total unmoved at 88. Neither warning says *deliberate*.
2. **`kind: review-lens` on an AC is a no-op.** CARD-316 planted it on AC-379, re-ran the
   validator, and measured the WARN set's symmetric difference **empty** with AC-379's
   dead-ref warning still reported verbatim. `review-lens` is in
   `VALID_CON_CHECK_KINDS` and belongs to a CON's or an ADR rule's `check:` mapping — all
   nine occurrences in `requirements.yml` are on CONs. Shipping it would have been a
   declaration that reads as doing something and does nothing, which is CARD-318's F-009
   in a new costume.

## What to implement

Extend the lifecycle the validator already has for CONs to acceptance criteria and
engineering constraints:

1. **Read an AC's/EC's `status:`** in `_validate_ac_ec_test_refs`, with the same
   vocabulary and the same severities the CON path uses.
2. **Exempt a criterion whose status says it is deliberately unverifiable** from
   check-ref verification — the CON path's existing behaviour, one rule along.
3. **Refuse the half-measures the CON path already refuses:** an unknown status, a
   `superseded` without `superseded_by`, and (the AC analogue of a superseded CON still
   carrying a `check:`) a retired criterion still carrying a `test:`.
4. **Decide what a forward declaration is**, because it is not a retirement. AC-379 is
   *owed* by CARD-226 — the behaviour is planned, not rejected — and `superseded` is the
   wrong word for it. Either a distinct status value or an explicit decision that a
   forward declaration carries no status and lives in a comment. **State which and why.**
5. **Inherit a SETTLED word for the never-adopted case, and do not re-open it lightly.**
   <!-- Routed in 2026-10-31 by CARD-316 fix round 2 (review F2-002). -->
   The registry's six retired acceptance criteria all carry `status: retired`, including
   the four that were **never adopted** (AC-129, AC-134, AC-206, AC-207). CARD-316 first
   gave those four a narrower `rejected` and withdrew it, because two **accepted** ADRs
   already spend `retired` on exactly those four and one of them names a precedent for
   doing so: `decisions/adr/0027-refuse-degenerate-density.md:167` ("AC-129, AC-134
   (retired)"), `decisions/adr/0034-default-book-plan-150-at-40-40-20.md:48` ("AC-206,
   AC-207 retired") and `0034-…:41` ("AC-206 … and AC-207 … are **retired unimplemented,
   following the FR-004 / ADR-0027 precedent**"). `requirements.yml:181` uses the same
   word for the adopted-then-amended pair. So `retired` is the word in force for both
   families, and today it is inert — an acceptance criterion's `status` is read **nowhere**
   in the validator of record (re-measured by CARD-316 fix round 2: `_validate_criterion`
   does not read it, `_validate_con_lifecycle`'s one call site is the constraints loop,
   and every other `status` read in the tree is over a trace entry, a CON, a DEC or an
   ADR). **This card is what makes it stop being inert**, so it is this card that must
   either adopt `retired` for both families or, if it wants the narrower split, carry an
   **ADR amendment** to ADR-0027 and ADR-0034 — not a block comment in the registry.

## Why this is blocked

The code is at
`/Users/omelnikova/MyProjects/forge_1/forge/skills/architect-validate/scripts/validators/requirements.py`,
**outside this repository**, and this board has a **standing rule never to edit anything
under `forge_1`**. That rule is the blocker, not the difficulty — the change itself is
small and the CON path is the working precedent sitting beside it.

**This is the second card blocked on the same decision.** CARD-319 is the first. If the
owner opens `forge_1` to edits, both should be considered together: CARD-319's surviving
defect is that `symbol_exists` is a **text** search whose domain excludes only
`meta/architecture/` and `*.md`, which is why fourteen unwritten criteria resolve from
prose comment tables and one (**AC-252**) resolves from a committed `.txt` duration dump.
That hazard and this one compound: a criterion exempted by lifecycle would stop being
asked the text question at all, which removes the prose-resolution hazard for exactly the
population most likely to hit it.

**CARD-319's other defect is already refuted and must not be re-inherited:** ADR rule
check refs *are* verified. `run()` calls `_validate_adr_rule_check_refs` one line above
the AC/EC check, and a nonsense ADR rule ref produces a WARN naming it — measured twice,
by CARD-317's fix round and independently by the orchestrator, 88 → 89 warnings.

## What this card is NOT

- **Not a licence to edit `forge_1` without the decision.** Read it; do not write it.
- **Not the registry-side work.** The owner's decision of 2026-10-31 standardises the
  repository side on **dropping the `test:` key**, with a status kept as the human record
  and labelled as prose until this card lands. That work belongs to **CARD-316's fix
  round**, which already owns `requirements.yml`, and covers all eleven criteria — its own
  seven plus FR-001's four from CARD-317.
- **Not a re-litigation of the warning count.** Both shapes cost one warning each; this
  card is about what a reader and a tool can *learn*, not about the total.

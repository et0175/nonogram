# CARD-104: Three shipped web-form features whose acceptance tests were never written

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/104-web-form-acceptance-tests
**Worktree:** —
**Source:** the 2026-09-21 branch sweep, which CARD-032's re-cut prompted
**Idea:** —
**Wave:** 1
**Depends on:** —
**Touches:** tests/test_web_server.py and/or tests/test_web_upload.py (ten test classes), meta/kanban/cards/CARD-030.md, CARD-031.md, CARD-033.md (closing them)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

Three cards sat in Ready with their features already shipped. That much is the
ordinary stale-card problem CARD-067, CARD-068 and CARD-032 all turned out to
be. What makes these three different is what the sweep found next:

**Every acceptance test they name is missing — and unlike CARD-032's, they
were never written anywhere.**

| card | on `main` | named test classes present |
|---|---|---|
| CARD-030 — inline success/error messages | yes: `web/handler.py:707` returns results inline instead of redirecting, and `multipart.py` re-populates the form | **0 of 3** |
| CARD-031 — image metadata and suggested dimensions | yes: an entire module, `src/nonogram/web/metadata.py` | **0 of 3** |
| CARD-033 — output directory and form polish | yes: CLI extent parsing moved, `prefers-color-scheme` styling | **0 of 4** |

Checked both ways: `class TestWebForm_…` for each of the ten names, against
`main` and against the branch that implemented the feature. None exists in
either place. CARD-032's two missing classes were at least *recoverable* from
its branch — these were simply never written.

Each branch also carries **two review files that never reached `main`**, and
`card/031-superseded-2026-09-03` closes its card with the commit message
*"chore(CARD-031): close the card — review cycle 2 passed with score 9.0"*. A
card was reviewed, scored nine out of ten, and closed, while the tests its
acceptance criteria named did not exist.

So this is the same shape as the defect CARD-100 repaired, one level up: a
check that everything downstream trusts, which is not happening. There the
guard read a column nothing wrote; here the criteria cite tests nobody wrote.

## What to implement

1. **Write the ten test classes**, named as their cards name them, against the
   behaviour on `main` today:
   - CARD-030 — `TestWebForm_DisplaysSuccessInline`,
     `TestWebForm_DisplaysErrorInline`, `TestWebForm_ClearsResultOnNewSubmit`
   - CARD-031 — `TestWebForm_SuggestsPuzzleDimensions`,
     `TestWebForm_DisplaysImageAspectRatio`,
     `TestWebForm_GeneratesWithSuggestedSize`
   - CARD-033 — `TestWebForm_HasOutputDirectoryField`,
     `TestWebForm_WritesFilesToSpecifiedDirectory`,
     `TestWebForm_DefaultsToWorkingDirectory`, `TestWebForm_HasPolishedLayout`
2. **Test the behaviour, not the markup, wherever the two can be separated.**
   `TestWebForm_HasPolishedLayout` is the one that cannot be — "polished" is
   not a testable claim. Either pin the specific thing the card meant (the
   card's own text says `prefers-color-scheme`, which *is* checkable) or
   record in the card that the criterion was aspirational and is retired, the
   way CARD-078 retired AC-2's unreachable half. Do not write a test that
   asserts a `<div>` exists and call it polish.
3. **Recover the six review files** from the three superseded branches into
   `meta/review/`, so the record of what was reviewed survives where the rest
   of the reviews live.
4. **Close CARD-030, CARD-031 and CARD-033** with notes saying what shipped,
   when, and that their tests arrived late and why.

## Acceptance criteria

- **AC-1** — each of the ten named classes exists and tests the behaviour its
  card describes, against the code on `main`.
- **AC-2** — every one of them fails if the feature it covers is removed
  (demonstrated by a mutation check, not by assertion).
- **AC-3** — any criterion that cannot be tested as written is retired in its
  card with the reason, not approximated by a test that passes vacuously.
- **AC-4** — the six review files are in `meta/review/`, and CARD-030,
  CARD-031 and CARD-033 are `done` with merge commits recorded.

## Guardrails

- G-1: **No production code changes.** If a test cannot pass against the code
  as it stands, that is a finding to report, not a licence to adjust the
  feature to match a card written three weeks ago.
- G-2: If a feature turns out not to behave as its card claims, stop and
  report it rather than writing a test that documents the discrepancy
  silently.
- G-3: Do not delete the superseded branches; they are the only record of
  this work's review history until item 3 lands.
- G-4: Commit only your own files — explicit pathspecs.

## Architecture context

- **FR:** FR-017 (web UI)
- **Components:** COMP-008
- **Trace:** none

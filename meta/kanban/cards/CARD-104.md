# CARD-104: Three shipped web-form cards — two were tested all along, one described a page that never existed

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** n/a — a deletion and a paperwork repair; the suite is unchanged at 3,613
**Branch:** card/104-web-form-acceptance-tests
**Worktree:** ../PythonProject4-CARD-104
**Source:** the 2026-09-21 branch sweep, which CARD-032's re-cut prompted
**Idea:** —
**Wave:** 1
**Depends on:** —
**Touches:** src/nonogram/web/pages.py, src/nonogram/web/handler.py (the unreachable metadata path), tests/test_web_server.py (the escaping guard's table and counts), meta/kanban/cards/CARD-030.md, CARD-031.md, CARD-033.md, meta/review/ (six recovered files)
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-21
**Closed:** 2026-09-21
**Actual:** 0.5d
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

### Correction, 2026-09-21 — this card was opened on a false premise

**The claim in the title and the Why section was wrong**, and it is left above
unedited because a card that quietly rewrites its own reasoning is worth less
than one that shows it.

What was measured: whether classes named `TestWebForm_…` existed. They did not.
What was reported: that the acceptance tests "were never written anywhere".
Those are not the same statement, and the second does not follow from the first.
Checked properly:

* **CARD-033** — all four criteria are tested by
  `TestWebUI_OutputDirectoryFieldAndStyling`, which names AC-131..134 in its
  docstring. Covered all along.
* **CARD-030** — AC-122 and AC-123 are tested in `tests/test_web_submission.py`,
  asserting the criteria's own words.
* **CARD-031** — the criteria are **not met**, but not for the reason the card
  gave. See below; this is the one real finding.

The 9.0 review this card held up as an indictment records
`coverage.read: [… tests/test_web_metadata.py]` and `tests_cover_change: true`.
It was reading real tests. The insinuation was unfounded.

The method that produced the error is the same one the error was about:
trusting a cheap proxy — a class name — instead of reading what the code does.

### The real finding: CARD-031 described a page that never rendered

Verified by reading, not by grep:

* `pages._metadata_section` / `pages._suggestions_section` — **zero call sites**.
* `form_with_result` took `image_metadata_str` and `suggestions`, interpolated
  neither.
* `handler._generate` computed both on every image upload and threw them away,
  inside `except (ImportError, Exception): pass`.

`Exception` already covers `ImportError`; the tuple is redundant and the clause
swallows everything, which is how a whole feature came to be computed and
discarded on every request without anyone noticing.

**Deleted, at the owner's decision** (option (a) of three): both builders, both
parameters, the handler block and its catch-all. The user-visible need is met
by CARD-034's client-side `/static/metadata.js`, and the
`.metadata`/`.suggestions`/`.suggestion-button` CSS stays because that script
writes exactly those classes. `web/metadata.py` stays too — its functions are
still exercised by the Python/JavaScript parity tests.

### What the escaping guard caught

Deleting `_suggestions_section` broke
`TestWebPages_EscapingRuleIsTheOneTheDocstringStates`, which walks `pages.py`'s
AST and compares it with the counts and the table of allowed unescaped
interpolations. Exactly as designed — its own docstring says a table entry the
module no longer interpolates "would otherwise keep vouching for nothing".
Counts updated 53/19/34 → 47/16/31, and the three stale entries (`width`,
`height`, `" ".join(buttons)`) removed. That test is the one piece of this
whole area that was doing its job unprompted.

### Delivered

1. The unreachable path deleted (above).
2. **AC-124's focus clause retired.** It asks that "focus returns to form
   inputs"; nothing moves focus and nothing should, because the listener fires
   on `input`, which cannot happen unless focus is already in a form control.
   The script's comment claimed to "manage focus" — it now says what the code
   does and why.
3. **Every `*test:*` line on the three cards repointed** at the test that
   actually covers it, or marked retired with the reason. That broken trail is
   the whole reason two tested cards looked untested for eighteen days.
4. **CARD-030, CARD-031 and CARD-033 closed**, each with notes recording what
   shipped and what was retired.
5. **Six review files recovered** into `meta/review/` from the superseded
   branches, where the rest of the reviews live.

**Full suite: 3,613 passed, 0 failed — the same count as before the deletion,
which is the evidence that what was removed was unreachable.**

### Not done, and deliberately

The AC-number collision (this repo has at least two live meanings for AC-122
through AC-134) is **not** addressed here. It is repo-wide, it needs a decision
about which numbering survives, and folding it into a card that has already
been wrong once is how the next mistake would get made.

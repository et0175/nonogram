# CARD-317: Six check refs name tests that exist under other names — and the dead ref on FR-001 has been hiding a grid bound the code abandoned

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** moderate
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-307's fourth premise re-measurement, 2026-10-29. CARD-307 was cut; this is one of its four successors, and the only one with a live defect behind it. Cut by the orchestrator on owner decision.
**Idea:** —
**Wave:** —
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/requirements.yml, meta/architecture/decisions/adr/0001-generation-time-thresholds.md, meta/architecture/decisions/adr/0006-dependency-baseline.md, meta/architecture/trace.yml
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists, and why it is not bookkeeping

Six check refs name tests that **do not exist under that name but do exist under
another**. Re-pointing them is clerical. **What makes this a P1 is what the clerical
work uncovers.**

### The defect: FR-001 still describes a 50x50 maximum the code abandoned

`requirements.yml` AC-001–AC-004 name four class-style tests that have no definition
anywhere. The behaviour is fully covered — by **function-style** tests in
`tests/test_sourcing_random.py`:

| AC | `requirements.yml` says | the test that actually covers it |
|---|---|---|
| AC-001 `:288` | a 20x20 grid is produced | `test_generate_random_produces_requested_dimensions` |
| AC-002 `:294` | **a 50x50 grid is produced without error** | `test_generate_random_accepts_max_side_30` |
| AC-003 `:300` | **rejects size above 50** | `test_generate_random_rejects_side_above_30` |
| AC-004 `:306` | rejects size below 10 | `test_generate_random_rejects_side_below_10` |

**AC-002 and AC-003 say 50. The code says 30.**
`tests/test_sourcing_random.py:107` asserts `random_grid.MAX_SIZE == 30` outright, and
`CLAUDE.md` instructs the reader to use `limits.py` *"instead of writing 10 or 30"*.
**ADR-0001 also still says "the 50x50 maximum"** in its reaffirmation paragraph.

So the model says 50 in two places and the code says 30, **and the dead check ref is
what let that sit.** A live ref would have pointed at a test asserting 30, and the
contradiction would have surfaced the first time anyone opened it. This is the
concrete answer to the question CARD-307 was reaching for — *what does a dead
`kind: test` ref actually cost?* It costs this.

**This card does not decide which number is right.** That is an architectural
question: either the supported range narrowed to 30 and the model is stale, or 50 is
still intended and the implementation regressed. The card's job is to **surface the
contradiction, record the decision, and leave the registry agreeing with exactly one
of them.** If the answer is "50 was never delivered", the honest outcome is an AC
whose `then` says 30 and an ADR-0001 amendment saying when and why it moved — not a
quiet edit of the number.

### The other two, and the ADR pointer

- **AC-268 / AC-269** (`:4047`, `:4056`) name `TestBookAnswerKey_CaptionPuzzleNumberAndTitle`
  and `..._CaptionUsesCustomBookTitle`. The family exists —
  `TestBookAnswerKey_CaptionSeparatorIsADrawnGlyph` and eight siblings in
  `tests/test_book_answer_key.py` — but neither of these two does. AC-269 already
  carries `# REWORDED 2026-09-22`. **These may be re-pointable or may be genuine
  gaps; the card must determine which and say so**, not assume the family's existence
  means coverage.
- **ADR-0006/R1's pointer.** Its check ref `TestDependencyBaseline_IsExactlyPillowAndNumpy`
  has **zero definitions**, while the rule itself **is** tested — at
  `tests/test_export_pdf.py:1249`, which pins the whole runtime list. This is a
  phantom pointer, not an unverified rule, and **every earlier framing on this board
  overstated it**. Twelve cards carry a hand-written `**DEAD REF**` note about it.
  Re-point it to the real test and the twelve notes become true.
  **Measured subtlety worth knowing before you start:** the phantom name is
  *text-present* in two tracked test files, so it raises no warning and would resolve
  falsely even if ADR rule refs were checked — which they are not (see CARD-319).

## What to implement

1. **Derive the set.** Walk `requirements.yml` and the ADR `check:` entries for refs
   whose named symbol has no `class`/`def` in `tests/`, and for each, search for a
   test covering the same behaviour under another name. **Per ADR-0039/R2, a ref the
   walk cannot classify is a FAILURE**, not a silent skip.
2. **Re-point the four FR-001 refs** to the function-style tests that cover them.
3. **Surface the 50-vs-30 contradiction as a decision**, not an edit. Record it where
   a reader meets it: the AC text, ADR-0001, and a line in this card saying which way
   it went and why. Reconcile `requirements.yml` and ADR-0001 so they agree with each
   other **and** with `limits.py`.
4. **Resolve AC-268/269** — re-point if a covering test exists, demote with a reason
   if not. Per ADR-0039 a demotion is a success here.
5. **Re-point ADR-0006/R1** to `tests/test_export_pdf.py:1249`'s test, and state in
   the ADR that the rule is verified by substance there.
6. **Do not leave the twelve cards' notes stale.** They are prose in `.md` files and
   still navigable, but once the pointer is live, say so in **one** place — this
   card's worktree notes — rather than editing twelve live cards.

## Acceptance criteria

- **AC-1** (the re-pointing is derived, not hand-listed): *Given* the registry,
  *then* every re-pointed ref is produced by a walk that resolves definitions from
  `tests/`, and an unclassifiable ref fails the walk.
- **AC-2** (every re-pointed ref resolves to a definition): *Given* the branch,
  *then* each named test has a real `def`/`class` in the file the ref names — asserted
  **by definition, not by text presence**, so a mention cannot satisfy it. This is the
  distinction the whole CARD-307 family exists to draw.
- **AC-3** (the bound agrees everywhere): *Given* the branch, *then*
  `requirements.yml`'s FR-001 criteria, ADR-0001's text and `limits.MAX_SIZE` state
  **the same number**, and a test asserts the registry's number equals the constant —
  so the two cannot drift apart again silently.
- **AC-4** (the decision is recorded with its alternative): *Given* the card and
  ADR-0001, *then* the chosen bound is stated **with why the other was not**, and with
  the date the divergence is believed to have started if that is recoverable.
- **AC-5** (AC-268/269 are honest): *Given* the branch, *then* each is either pointed
  at a test that exists or demoted to `review-lens` with a recorded reason, and
  neither remains `kind: test` with no definition.
- **AC-6** (the count moves only downward): *Given* `main` and the branch, *then* the
  validator of record reports **six fewer dead-ref warnings** and **no warning of any
  kind added** — warning **sets** diffed line by line, not counts compared.

## Guardrails

- **G-1: do not silently change the bound.** Editing `50` to `30` without recording
  the decision converts a visible contradiction into an invisible one. The ADR is the
  place; a commit message is not.
- **G-2: do not write a new test for behaviour already covered.** Four of these are
  re-pointing jobs. A duplicate test is a second thing to keep in sync.
- **G-3: resolve refs by DEFINITION, never by `git grep -lw`.** A text search is what
  made this population invisible. Use `git grep -nE '^[[:space:]]*(async )?def NAME\('`
  or `class NAME[(:]`, and `--collect-only` to confirm the node collects.
  **`\b` is undefined in POSIX ERE and silently matches nothing** — an instrument
  using it returns empty and reads as a clean verdict. Prove any instrument in both
  directions (finds a known name, rejects a nonsense one) before trusting it.
- **G-4: no test deleted, renamed, skipped or merged** — `parametrize` ids included.
  (**gate**: node-id set difference with `-o addopts=''`.)
- **G-5: do not compare this branch's warning count to main's without holding the
  review YAMLs equal** — `meta/review/**` is inside the validator's ref-resolution
  domain. Swap the files inside one worktree. **And do not validate a `git archive`
  copy**: no `.git` means staleness and drift checks fall silent (77 against 102).
- **G-6: name the validator binary beside every figure** — the `forge_1` copy named
  in `meta/kanban/config.yml`, not the plugin cache, whose phantom
  `[ERROR] ADR-0025 circular supersession` is a regex bug.
- **G-7: do not touch FR-029's refs.** Those are **CARD-318's** and are a genuine
  coverage gap, not a re-pointing job.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0001 — the generation-time thresholds and the supported grid range (check: **this card's subject** — the ADR's own text is one side of the contradiction)
- ADR-0006/R1 — the dependency baseline (check: **this card re-points the pointer**; the RULE is tested at `tests/test_export_pdf.py:1249`)

## Architecture context

- **ADR:** ADR-0001 (the bound), ADR-0006/R1 (the pointer), ADR-0039/R2 (derivation)
- **Components:** `src/nonogram/limits.py` is the authority the registry must agree
  with; no `src/` change is expected unless the decision goes the other way.
- **Trace:** FR-001's row is re-stamped once its ACs name live tests; FR-042's row is
  re-read after AC-268/269 resolve.

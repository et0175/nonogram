# CARD-365: Three refusal arms in the ink-mode stream reader are asserted and never demonstrated — the one AC clause with no control

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.25d)
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** F-003 of CARD-337's review cycle 1, 2026-11-04, which certified that card at 8.5 and named this as the single AC clause resting on an assertion nothing had been shown to fire. Carded rather than folded in because adding three cases after certification is a widening, and this board's wave-48 rule is that a late widening ships its final edit uncertified.
**Idea:** —
**Wave:** —
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** CARD-337
**Touches:** tests/test_book_pdf_ink_mode.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The gap, named by a reviewer that went looking for it

CARD-337's `pdf_page_declarations` refuses three ways:

1. a page with **neither** an image XObject **nor** a `Contents` stream — a named `AssertionError`
   citing ADR-0039/R2;
2. a page with **more than one** XObject;
3. a **non-Flate** stream — which raises out of `zlib` rather than by name.

**None of that card's six plants exercises any of the three.** So its AC-2 — *"a page the reader
cannot classify is a FAILURE"* — rests on an assertion **nothing has been shown to fire**.

**That is precisely the shape CARD-337's own AC-4 charges for a retirement:** *a retirement whose
survivor cannot fail is a deletion.* The same standard applied to a refusal arm says an
undemonstrated refusal is a comment. The card met AC-2 in substance and the reviewer said so;
what is missing is the control.

**Re-derive the three arms from the code** rather than from this list — the reader may have
changed, and a fourth arm would be a finding.

## Why it is cheap, which is the other reason it is a card and not a note

The reviewer costed it: **three cases in `TestBookInk_TheStreamReaderReadsOutsideStrings`**, which
already exists as this reader's control class, **fed hand-built minimal PDF bytes**. No `src/`
plant, no five-kind probe, no full corpus. A page with no XObject and no `Contents`, a page with
two XObjects, and a stream with a non-Flate filter are each a few dozen bytes of literal PDF.

**Do not reach for the probe or the corpus to test a refusal.** The arms are properties of the
reader, not of a rendered book, and building the input by hand is what makes each case name the
arm it fires.

## What to implement

1. **Derive the refusal arms from the reader** and state the count. Three is a dated reading.
2. **One case per arm**, each asserting the refusal fires **and** naming which arm — a case that
   merely expects "an exception" cannot tell arm 1 from arm 3, and arm 3 currently raises out of
   `zlib` rather than by name.
3. **Decide whether arm 3 should refuse by name**, and say which you chose. A `zlib` error reaching
   a reader's caller is a refusal the reader did not make; wrapping it is a small, real
   improvement, and leaving it is defensible if stated.
4. **Do not weaken the reader to make a case easy.** If an arm cannot be reached with hand-built
   bytes, that is a finding about the arm, not a reason to relax it.

## Acceptance criteria

- **AC-1** *Given* the reader, *then* the set of its refusal arms is **derived** from the code and
  its size stated; a fourth arm, or an arm that cannot be reached, is a **finding**.
  (test: named by the implementation; state it)
- **AC-2** *Given* each arm, *then* a case feeds it hand-built PDF bytes and asserts the refusal
  **fires and is attributable to that arm** — not merely that something raised.
  (test: named by the implementation; state it)
- **AC-3** *Given* arm 3, *then* the card states whether it now refuses by name or deliberately
  still raises out of `zlib`, with the reason.
  (check: review-lens)
- **AC-4** *Given* CARD-337's existing cells, *then* all 52 still pass **under the five-kind probe
  and on the committed raster tree**, and its six plants still kill — the control class gaining
  cases must not disturb what it already holds.
  (test: the module, both ways)
- **AC-5** *Given* the new cases, *then* each is shown able to fail: a plant that removes the
  refusal makes its case **red**, demonstrated.
  (test: named by the implementation; state it)

## Guardrails

- **G-1** — No `src/` change. These are a test helper's refusal arms.
- **G-2** — Do not relax a refusal to make a case pass. AC-1 names an unreachable arm as a
  finding, which is the escape hatch.
- **G-3** — Do not reach for the five-kind probe or the EC-1 corpus. Hand-built bytes are the
  point: they make each case name its arm.
- **G-4** — No new runtime dependency (ADR-0006/R1); stdlib only.
- **G-5** — Take no timing measurements and report no durations.
- **G-6** — A full suite needs the board's lock (structured, worktree identity, **no pid**). Never
  set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, never redirect `NONOGRAM_FULL_SUITE_LOCK`.
- **G-7** — **`scratchpad/` is now gitignored on main** (`.gitignore:104`, landed by CARD-335), so
  tracking a probe takes `git add -f` **and moves a pinned census**. Prefer leaving instruments
  untracked; if you must track one, expect `tests/test_check_ref_resolution.py` to red and
  **re-derive** its baselines rather than pasting the failure figure.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail: caught WITH the mechanism, missed WITHOUT
  (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate; where none
  exists it defaults to **deny** (check: review-lens)
- ADR-0038/R8 — failures are loud, never silent (check: review-lens)

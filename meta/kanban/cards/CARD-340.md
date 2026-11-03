# CARD-340: The arrangement screen spills its buttons off a phone, and has since before anyone looked

**Status:** ready
**Priority:** P2
**Category:** bug
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-332's fix round 1, 2026-11-03, found while writing the Chromium cell that guards *its own* layout fix. Its brief said "one cell"; one cell would have been wrong at either viewport, and finding out why surfaced a defect that is **not CARD-332's** and predates it. Raised, measured, named on that card and in the new test file's docstring, and deliberately left for an owner rather than absorbed.
**Idea:** —
**Wave:** —
**Created wave:** 73
**Deferred waves:** 0
**Depends on:** CARD-332
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/book_arrange_puzzles.html, tests/test_book_arrange_play_link.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

At phone width the book arrangement screen pushes its own controls off the page. Measured by
CARD-332's fix round at **390 px**: the row's `.item-actions` sits **44 px outside the row**,
and the page's `scrollWidth` is **401** against a 390 px viewport.

**It is not CARD-332's doing.** That round measured the same red **with its fix in place and
with the fix reverted** — which is what makes this a pre-existing defect rather than a
regression, and is why it was raised rather than absorbed.

**Figures to re-derive, not inherit.** Everything above is that round's measurement. CARD-332's
cycle 2 was asked to confirm the baseline red at the **merge-base** rather than only at HEAD,
because "pre-existing" is the entire scope argument and a figure measured at one commit does not
establish it. **Read that review's verdict before starting**, and if it refuted the claim, this
card is wrong and should be cut rather than built.

## Why it survived this long

Because nothing looked. `tests/test_book_setup_print_mobile.py` is CARD-166's Chromium test and
it asserts **exactly this defect class** — a control clipped out of its container at 390 px — but
for the *print setup* screen. **There was no browser test for the arrangement screen at all**
until CARD-332 added one, and that one exists to guard CARD-332's own fix.

So the pattern, the harness and the precedent were all already here; the screen simply was never
pointed at. That is the more useful half of this card: a defect class already guarded on one
screen and unguarded on its sibling.

## What to implement

1. **Re-derive the measurement first**, at the merge-base and at HEAD, at 390 px — and record
   both. If the red does not reproduce at the merge-base, stop and raise it: the premise is then
   false and this card should be cut, not fixed. This board has had five consecutive cards find
   their own premise false, so this step is the cheap one.
2. **Find what actually overflows.** `scrollWidth` 401 vs 390 is an 11 px page overflow while the
   actions sit 44 px outside the row — two different numbers, so do not assume one cause. Name
   the element and the property that does it.
3. **Fix it at the narrowest point that holds.** The sibling screen's fix is the precedent for
   shape, not necessarily for technique.
4. **Guard it where the harness already is.** `tests/test_book_arrange_play_link.py` exists from
   CARD-332 and already runs at **1024 px and 390 px** with the arrangement screen's fixtures.
   Add the containment cell there rather than building a second harness — and **do not edit
   `tests/test_book_setup_print_mobile.py`**, which is a standing G-3 control that must stay
   byte-identical.
5. **Prove the cell discriminates**: revert your own fix and show it reds, then restore,
   SHA-256 verified.

## Acceptance criteria

- **AC-1** — Given the arrangement screen at 390 px with at least one arranged puzzle, when the
  page is measured, then every row control lies **inside** its row, and the page's `scrollWidth`
  does not exceed the viewport.
  `check: {kind: test}`
- **AC-2** — Given the fix, when it is reverted, then the cell added here **reds**, demonstrated
  by a measured plant and restore rather than asserted.
  `check: {kind: test}`
- **AC-3** — Given the measurement, when it is taken at the merge-base and at HEAD, then both
  figures are recorded on the card, so a later reader can tell a regression from a repair.
  `check: {kind: test}`
- **AC-4** — Given `tests/test_book_setup_print_mobile.py`, when this card lands, then it is
  byte-identical to its state at the merge-base.
  `check: {kind: test}`

## Guardrails

- **G-1** — **Do not edit `tests/test_book_setup_print_mobile.py`.** It is CARD-166's control for
  this defect class on the sibling screen, and CARD-332 was credited for leaving it untouched.
  Reuse its *pattern*, never its file.
- **G-2** — The 1024 px cells CARD-332 added must keep passing unchanged. A phone-width fix that
  moves the desktop layout is a different card.
- **G-3** — This is owner-facing UI, so the render is part of the gate: **before and after at
  390 px**, into `~/Documents/nonogram-reviews/CARD-340/`. The owner validates this by looking.
- **G-4** — **Read the host load before trusting a browser timing.** A sibling review opened at a
  1-minute load of 89; a containment measurement taken under that is not evidence.
- **G-5** — ADR-0041/R2 still binds on anything this screen renders: no puzzle title, grid or
  solution cell in a link, attribute or copy target. CARD-332 built a closed whitelist over the
  rendered fragment — **extend it rather than working around it** if you change the markup.

## Notes

**Why 0.5d and not less.** The fix may be one declaration; the measurement is not. Two numbers
disagree (11 px of page overflow, 44 px of control overhang), the premise needs re-establishing
at a second commit, and a browser cell has to be proven to discriminate — on a screen whose
timings are only trustworthy on a quiet host.

**Why it depends on CARD-332.** Not for the fix, which is independent, but for the harness:
`tests/test_book_arrange_play_link.py` and the arrangement-screen fixtures arrive with it. Start
before it lands and this card builds a second harness for the same screen, which is the thing
item 4 exists to prevent.

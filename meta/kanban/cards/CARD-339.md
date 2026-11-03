# CARD-339: The public player gains the "?" glyph — and the mark that drifted enters the guard that exists to stop drift

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-323's round, 2026-11-01, which measured the divergence, refused to fix it (its own AC-4 makes re-declaring that rule a finding *against* it), and routed it to the owner. **The owner decided 2026-11-03: the public page gains the glyph.** The second half of this card is the orchestrator's, measured at the decompose station — see below.
**Idea:** —
**Wave:** —
**Created wave:** 73
**Deferred waves:** 0
**Depends on:** CARD-323
**Touches:** player/player.css, tests/test_public_player_agreement.py, tests/test_public_player_maybe.py <!-- test_public_player_maybe.py is NOT optional: CARD-323's cell-look guard treats a `?` glyph as a defect to catch, so AC-1 cannot land without teaching it the new expected shape. See G-2. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The two players disagree about what a "Maybe" mark looks like. The admin draws a **"?" glyph**
in the accent token, on both the cell and the swatch:

- `src/nonogram/admin/static/admin.css:655` — `.player-cell[data-state="maybe"]::after { content: "?"; … color: var(--color-accent); }`
- `src/nonogram/admin/static/admin.css:782` — `.player-swatch[data-state="maybe"]::after { content: "?"; … color: var(--color-accent); }`

The public page draws **a tint and no glyph** — `player/player.css:411`, one background
declaration, which CARD-323 matched on the swatch so the brush button would stop previewing
the wrong mark.

**The consequence is visible, not theoretical.** CARD-323's round measured the contrast and
the orchestrator confirmed it by opening the renders in
`~/Documents/nonogram-reviews/CARD-323/`: the **Maybe and Clear swatches are the same beige
square**, distinguishable only by which button happens to be selected, and on the board the
Maybe block is a tint barely separable from blank cells while "empty" carries a clearly
visible dot.

**Figures inherited from CARD-323's round, not re-derived here — re-derive them:**

| pair | ratio |
|---|---|
| maybe cell vs a blank cell | 1.169 : 1 |
| maybe swatch vs the Clear swatch | 1.018 : 1 |
| the admin's "?" glyph on a cell | 7.258 : 1 |

**The owner's decision, 2026-11-03: the public page gains the glyph.** The admin keeps what
it has. So this card adds to the public sheet; it does not remove from the admin's.

## The second half, and it is the half that matters

**Measured by the orchestrator 2026-11-03:** `tests/test_public_player_agreement.py` — the
guard whose entire job is to stop these two stylesheets drifting — contains the string
`maybe` **zero times**.

That guard is well built. It compares declaration *sets* rather than rule text, it carries a
`DECLARED_DIVERGENCES` registry in which every entry must be **a fact the guard measures**
and must **carry a reason**, and it reds in both directions — a planted fourth divergence is
reported, and a declared divergence that stops diverging is reported too, so a stale
exemption fails as loudly as a new one.

**None of that applied here, because the Maybe mark was never in the compared surface at
all.** It did not diverge past a guard; it diverged where no guard was looking. That is why
the drift reached a render before it reached a test, and it is the actual defect — the glyph
is only its symptom.

**So fixing the look without widening the surface would leave the mechanism exactly as it
is, and the next mark to drift would drift the same way.**

## What to implement

1. **Add the glyph to the public sheet**, on the cell and the swatch, matching the admin's
   two rules. Match them by **deriving the admin's declarations**, not by retyping them —
   the agreement guard's own technique, and the thing that keeps the two in step afterwards.
2. **Bring the Maybe mark into the compared surface.** Both looks — cell and swatch — become
   something the guard compares, by the same declaration-set comparison it already uses for
   the families it covers.
3. **If any part of the two looks must legitimately differ, declare it** in
   `DECLARED_DIVERGENCES` with a reason and a measured residue, as the existing entries do.
   Do not widen the surface by exempting what you widened it to catch. If nothing must
   differ, the registry gains no entry — that is the better outcome and should be stated.
4. **Check the other marks while you are there.** Filled, empty and unknown may or may not be
   in the compared surface; if they are not, say so and decide explicitly whether this card
   takes them or a follow-up does. Do not silently widen past the Maybe mark, and do not
   silently leave a sibling gap.

## Acceptance criteria

- **AC-1** — Given the public player, when a cell carries `data-state="maybe"`, then it
  renders the "?" glyph in the accent token, and when the Maybe swatch renders, it does the
  same — both verified against the admin's own declarations, derived rather than retyped.
  `check: {kind: test}`
- **AC-2** — Given the agreement guard, when the two sheets' Maybe looks are compared, then a
  divergence in either the cell look or the swatch look **reds**, demonstrated by planting
  one in each direction (public-only change, admin-only change).
  `check: {kind: test}`
- **AC-3** — Given the compared surface, when it is enumerated, then the Maybe mark is in it,
  and every divergence that remains declared carries a reason and a measured residue.
  `check: {kind: test}`
- **AC-4** — Given the rendered public player, when the four marks are shown together, then
  the Maybe mark is distinguishable from both a blank cell and the Clear swatch — measured as
  a contrast figure, not asserted, and the figure recorded.
  `check: {kind: test}`
- **AC-5** — Given the other three marks, when their coverage by the agreement guard is
  derived, then it is reported, and any gap is either closed here or named with an owner.
  `check: {kind: review-lens}` — owner: whoever reviews this card.

## Guardrails

- **G-1** — `src/` is not touched. The admin sheet keeps what it has; the owner's decision
  was that the public page gains the glyph, not that the admin loses it. An edit to
  `admin.css` is out of scope and a finding against this card.
- **G-2** — **Do not re-declare CARD-323's background declarations** — not for the cell, not
  for the swatch. This card **adds** a glyph; it must not duplicate or restate a background
  value either card already owns.

  **But G-2 does NOT mean you leave CARD-323's test module alone, and the first draft of this
  guardrail wrongly implied it did.** Corrected 2026-11-03, measured in CARD-323's worktree:
  that card's `test_the_maybe_cell_look_is_one_rule_declaring_one_background` is deliberately
  **pseudo-element-blind**, and its mutant table plants *"a `?` glyph added as an `::after`"*
  as something that **must change the report** — it is listed there as a defect to catch,
  because at the time no card was allowed to add one. **So AC-1 of this card trips that guard
  by design.** You must teach it that the glyph is now the expected shape, and that edit is the
  designed hand-off, **not a CARD-323 regression**. `Touches` already covers
  `tests/test_public_player_maybe.py`. Say so in the commit, or the first gate will read as a
  regression in a merged card.

  The same module's `test_the_swatch_previews_the_cell_with_the_cells_own_value` was pointed at
  this card's AC-1 by CARD-323's fix round, so its failure message already names you.
- **G-3** — The `DECLARED_DIVERGENCES` registry may gain an entry only with a reason and a
  measured residue. **An exemption added to make this card green is the defect it exists to
  fix**, arriving one level up.
- **G-4** — The render is part of the gate, not a courtesy: this is owner-facing UI and the
  owner validates it by looking. Render the four marks and the four swatches into
  `~/Documents/nonogram-reviews/CARD-339/`. The Chrome extension has been unreliable; the
  Chromium the suite already drives, against a real assembled site, is what CARD-323 used and
  is sufficient.
- **G-5** — ADR-0041/R2 still binds: no public asset may carry a solution grid or data from
  which any solution cell is recoverable. A glyph is constant markup, but say what you
  verified rather than assuming the rule is untouched.

## Notes

**Why this is not part of CARD-323.** That card's AC-4 makes re-declaring the Maybe rule a
finding against itself, so the round could not have fixed this without failing its own
acceptance criteria. It measured the divergence, refused to force it, and routed it — which
is the behaviour the board wants, and the reason this card exists rather than a silent edit.

**The estimate is 0.5d and the glyph is one line of it.** The cost is item 2: widening a
guard that compares declaration sets, in both directions, without weakening what it already
catches.

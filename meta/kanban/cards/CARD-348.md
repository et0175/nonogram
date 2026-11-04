# CARD-348: The White brush previews a plain square where the board draws a dot — this card's own defect, one state over

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** `card/348-the-white-brush-gains-its-dot`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-348
**Source:** Nominated by CARD-339's round as the strongest follow-up from its mark census, and confirmed by its review cycle 1 — which verified the divergence in the census, both contrast figures, and the visible gap in the render. It is the one routed finding the reviewer called "cheap enough to have been taken", and it was correctly left because CARD-339's own instruction forbids widening silently past the Maybe mark.
**Idea:** —
**Wave:** 76
**Created wave:** 74
**Deferred waves:** 0
**Depends on:** CARD-339
**Touches:** player/player.css, tests/test_public_player_agreement.py
**Review score:** —
**Started:** 2026-11-04T14:14Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The defect, and it is CARD-339's defect in a different costume

`.player-swatch.empty.glyph` is a **routed finding** in `SIBLING_FINDINGS`: the admin's White
swatch previews the cell's dot; the public page's draws nothing. So the brush button does not
show the mark it paints — which is exactly the class of defect CARD-323 fixed for the Maybe
brush and CARD-339 fixed for the Maybe glyph.

**It is visible in CARD-339's own render**, `~/Documents/nonogram-reviews/CARD-339/02-the-four-swatches.png`:
the White swatch is a plain square beside a Maybe swatch that now works.

Figures, re-derived independently by CARD-339's review from the token hex by WCAG 2.1 relative
luminance — **re-derive them again here, they are dated readings**:

| pair | figure |
|---|---|
| the admin's White-swatch dot (`#5c6070` on `#fffdf8`) | **6.144 : 1** |
| White swatch vs Clear swatch, with no dot (`#fffdf8` vs `#efe9dc`) | **1.190 : 1** |

**One correction to carry, because the nomination leaned on it:** CARD-339's `measured` field
says the 1.19 is *"below the 1.169:1 the owner already called indistinguishable"*. **1.19 is
marginally ABOVE 1.169** — the two swatches are a hair *more* separated than the Maybe tint
was, not less. Both figures are right; the comparative was backwards. The honest statement is
that 1.19 sits in the **same indistinguishable band**, which is still the reason to act. That
correction is CARD-339's fix round's to make (its F-7); do not restate the error here.

## What to implement

1. **Give the public White swatch the dot**, matching the admin's by **deriving its
   declarations** rather than retyping them — the agreement guard's own technique, and what
   keeps the two in step afterwards. CARD-339's `maybe.swatch.glyph` pair is the worked example
   to follow.
2. **Move the fact from routed to compared.** It currently sits in `SIBLING_FINDINGS`; once the
   two sides agree it belongs in `compared_surface`, and `test_no_mark_is_both_compared_and_routed`
   must still hold the tables disjoint. **Removing a routed entry is as load-bearing as adding
   one** — the census asserts `diverging == set(SIBLING_FINDINGS)`, so a stale routed entry
   reds. That is the mechanism working; do not silence it.
3. **Check whether the swatch needs a containing block**, as CARD-339's Maybe swatch did
   (`position: relative`, because the glyph is `position: absolute; inset: 0`). If the rule is
   already there from CARD-339, say so rather than re-declaring it.
4. **Do not touch the other routed facts.** Four remain and each is the board owner's decision.

## Acceptance criteria

- **AC-1** *Given* the public player's White swatch, *then* it draws the cell's dot, derived
  from the admin's declarations rather than retyped, and the two declaration sets are **equal**.
  (test: named by the implementation; state it)
- **AC-2** *Given* the agreement guard, *then* a one-sided change to the swatch dot **reds** in
  **both** directions — demonstrated by one public-only and one admin-only on-disk plant, each
  asserting the key appears in `disagreements` **and** that
  `set(found) - set(DECLARED_DIVERGENCES) == {key}`, so a plant the exemption table absorbed
  fails rather than passing as "something reddened".
  (test: named by the implementation; state it)
- **AC-3** *Given* the census, *then* `.player-swatch.empty.glyph` is **compared**, is **not**
  in `SIBLING_FINDINGS`, and `diverging == set(SIBLING_FINDINGS)` still holds for the remaining
  entries.
  (test: `test_every_census_fact_is_compared_routed_or_agreeing`)
- **AC-4** *Given* the rendered page, *then* the four swatches are mutually distinguishable,
  measured as contrast figures and recorded — not asserted. Include the White-vs-Clear pair
  after the change.
  (test: named by the implementation; state it)
- **AC-5** *Given* `DECLARED_DIVERGENCES`, *then* it gained no entry. If nothing must differ,
  say so — that is the better outcome and should be stated.
  (check: review-lens)

## Guardrails

- **G-1** — `src/` is not touched. The admin keeps what it has; the public page gains the dot.
  Plants into `admin.css` are measurements and must be restored from captured content with
  SHA-256 both ends.
- **G-2** — Do not re-declare a background either sheet already owns. This card **adds** a
  glyph, as CARD-339 did.
- **G-3** — `DECLARED_DIVERGENCES` may gain an entry only with a reason and a measured residue.
  An exemption added to make this card green is the defect one level up.
- **G-4** — **The render is part of the gate, not a courtesy.** Render the four swatches into
  `~/Documents/nonogram-reviews/CARD-348/`. **Do not use the Chrome extension** — it has been
  unreliable; use the Chromium the suite drives against a real assembled site
  (`bundle`/`site`/`host`/`browser_page` fixtures), which is what CARD-323 and CARD-339 used.
- **G-5** — ADR-0041/R2: no public asset may carry a solution grid or data from which any
  solution cell is recoverable. A dot is constant markup keyed on `data-state`, which the
  player's own strokes write — but **say what you verified** rather than assuming.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate
  (check: `test_every_census_fact_is_compared_routed_or_agreeing`)
- ADR-0041/R2 — no public asset carries recoverable solution data (check: review-lens)

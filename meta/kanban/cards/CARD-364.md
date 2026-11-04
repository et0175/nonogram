# CARD-364: The interior ink-mode feature loses its last subject when CARD-231 lands — a scheduled expiry with a named trigger

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Finding 4 of CARD-337's implementation round, 2026-11-04, measured while that card re-expressed the ink-mode claims against the content stream. It is not a defect today and will not be one until a specific other card lands, which is why it is a card rather than a note: the trigger is known and the decision is cheaper before than after.
**Idea:** —
**Wave:** —
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_pdf_ink_mode.py, meta/architecture/requirements.yml
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The mechanism, and it is arithmetic rather than a prediction

`books.interior_ink_mode` lets a book declare grayscale or RGB, and the claim that the **file
declares what the book chose** can only be read off a page that carries an image XObject with a
`/ColorSpace`. **That means a raster page.**

CARD-337 measured the interior's medium split on the real files:

| | baseline book | EC-1 corpus (14 books) |
|---|---|---|
| interior pages | 14 | 171 |
| **raster** — still mode-dependent | **4** | **40**, ≥2 in every book |
| vector — mode has no effect | 10 | 131 |

The 4 raster pages are **`PageKind.DIVIDER`**, which `_RASTER_DECLARATIONS` still declares raster
at `src/nonogram/admin/book_pdf_generator.py` — **verified at the station.** Its declaration
carries `expires_with=('CARD-231',)`.

**`DIVIDER` is the last declared interior bitmap.** So when CARD-231 lands and the divider becomes
operators, **the ink-mode feature has no subject anywhere in the interior file** — and
`assert_mode_reached_the_file`, the named survivor CARD-337 installed, will **red**.

**That red is the floor working as designed, not a regression.** CARD-337 built it precisely so
the retirement could not pass vacuously; its MUT-5 plant converted `DIVIDER` early and the module
failed loudly with 4 failed + 7 errors rather than going green. **This card exists so the feature's
fate is decided by someone rather than discovered by a gate.**

**Re-derive all of it** — the split, the `expires_with`, and whether `DIVIDER` is still the last
raster declaration. All are dated readings and the last one is exactly what CARD-231 changes.

## The decision this card owes, and it is a product decision

Three positions, and the card must choose with a reason rather than pick the cheapest:

1. **The interior ink-mode feature is retired.** If the interior is entirely operators and the
   vector writer cannot emit a non-grey colour, the setting controls nothing on the interior and
   saying so is honest. **Then `interior_ink_mode` either goes, or is narrowed to the cover** —
   which is permanently raster (`expires_with=()`) and where the mode genuinely still applies.
2. **The feature is kept and the vector writer gains colour.** `book_vector.ContentStream`'s
   entire colour vocabulary is `stroke_grey`/`fill_grey` — there is **no `rg`** — so this is a
   real feature build, not a repair. **And it is the position the owner's own intake points at**:
   CARD-337 records the intake line *"we may add colors for book2"*, which the conversion
   forecloses on every converted page. Routed to CARD-322 as its finding (A).
3. **The feature is kept, declared cover-only, and the interior claim retired with the cover as
   its named survivor.** The cheapest honest option, and it needs the retirement asserted rather
   than commented.

**Position 2 is a feature build and should not be smuggled in as a fix.** If it is the answer, say
so and expect a separate card to build it.

## What to implement

1. **Re-measure the split and the declaration**, and state whether `DIVIDER` is still the last
   interior raster kind. If another raster kind has appeared since, this card's trigger has moved.
2. **Choose a position and say why the other two lose.** Name who the decision belongs to if it is
   not a worktree call — CARD-337's round was explicit that the owner's intake points at 2.
3. **Whatever is chosen, leave the floor able to fail.** `assert_mode_reached_the_file` and
   `EC1_MODE_PAGES` are CARD-337's named survivor; a retirement that removes them removes the
   evidence that anything was ever checked.
4. **Do not pre-empt CARD-231.** This card decides the feature's fate; it does not convert the
   divider.

## Acceptance criteria

- **AC-1** *Given* the interior, *then* the medium split and `DIVIDER`'s `expires_with` are
  re-derived and stated, and whether `DIVIDER` remains the last raster declaration is **measured**.
  (test: named by the implementation; state it)
- **AC-2** *Given* the chosen position, *then* the card states it with the reason the other two
  lose, and names the owner if the choice is not a worktree call.
  (check: review-lens)
- **AC-3** *Given* a retirement of the interior claim, *then* its survivor is **named and
  asserted** — and a plant that empties the surviving arm makes the module **red**, demonstrated,
  not read. CARD-337's MUT-5 is the worked example.
  (test: named by the implementation; state it)
- **AC-4** *Given* CARD-231 landing later, *then* this card states what will happen when it does —
  so the gate that reds is expected rather than diagnosed.
  (check: review-lens)
- **AC-5** *Given* `interior_ink_mode`'s other consumers, *then* the set is **derived** rather than
  listed (ADR-0039/R2), and anything this card's position breaks is named with an owner.
  (test: named by the implementation; state it)

## Guardrails

- **G-1** — **Do not build colour support for the vector writer here.** That is position 2 and a
  feature card of its own. Choosing it is in scope; building it is not.
- **G-2** — Do not remove CARD-337's named survivor to make a retirement tidy. AC-3 is the guard:
  the surviving arm must still be able to fail.
- **G-3** — Do not convert `DIVIDER`. That is CARD-231's, and doing it here would trigger the very
  expiry this card exists to decide ahead of.
- **G-4** — No new runtime dependency (ADR-0006/R1).
- **G-5** — Take no timing measurements and report no durations.
- **G-6** — A full suite needs the board's lock (structured, worktree identity, **no pid**). Never
  set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, never redirect `NONOGRAM_FULL_SUITE_LOCK`.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate
  (check: review-lens)
- ADR-0042/R1 — interior pages are operators (check: review-lens)
- ADR-0042/R6 — a claim with no subject in the converted medium is re-expressed or retired with a
  named survivor (check: review-lens)

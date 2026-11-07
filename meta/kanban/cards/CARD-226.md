# CARD-226: A two-up page becomes two equal slots split by a light rule, with aligned bottoms

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** true
**Skill:** python-pro
**TDD:** —
**Branch:** card/226-two-up-equal-slots
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — issue 3 ("Two-up pages don't line up. Two stacked puzzles get different cell sizes and different left edges (pp. 9, 12), and nothing separates them") and "Small puzzles, two to a page"
**Idea:** —
**Wave:** —
**Depends on:** CARD-224 (centring), CARD-225 (the shared cell size), CARD-391 (the QR is gone and the two-up page has one shared footer line), CARD-392 (the footer band and so the area the two slots divide)
<!-- AMENDED 2026-11-07 (one-QR decision): was CARD-223 (each slot's own QR corner), which CARD-391 supersedes. -->
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_two_up.py, tests/test_book_page_numbers.py, tests/property/test_book_pdf_geometry.py, tests/fixtures/book_baseline_card226.json, tests/helpers/two_up_ink.py, meta/profiling/rank_durations.py, tests/test_book_*.py, tests/property/test_book_*.py, tests/helpers/book_corpus.py, tests/helpers/page_ink.py, tests/fixtures/
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## AMENDMENT 2026-11-07 — the owner removed individual QR codes (ADR-0041/R8); read this before the body

The body below was written for version A of the owner's layout (a QR at each slot's outer corner). The owner chose version B: puzzle pages carry NO QR, and a two-up page has ONE shared footer line below both slots ("Without the QR column, the two grids centre across the full width and share one footer line"). Consequences for this card, and only these:

- **What-to-implement item 2:** read "and its QR at the slot's outer bottom corner" as nothing. Each slot is the header, the centred grid at 42% and nothing at its foot; the page's one footer line (CARD-391) lies below BOTH slots, not inside each. The two slots divide the area between the header rule and that line.
- **AC-4 is replaced** by: *Given* a two-up page, *then* no QR ink lies on it and the page's single footer line lies below the lower slot and is not part of either slot's height. (test: `TestBookTwoUp_NoQrAndOneSharedFooterLine`)
- **AC-6** loses "and QR": both slots still hold their own grid and rule.
- The slot height is measured from the area CARD-392 sets (the footer band shrinks); do not take a number from the old 29.878 mm band. This is why the dependencies changed.
- Everything else (equal slots, light rule, shared left edge, aligned bottoms, the folio, the pairing-rate attribution) stands.

## What to implement

The owner's issue 3 names three separate defects on one page: different cell sizes, different
left edges, and nothing separating the two puzzles. CARD-225 fixes the first (both puzzles
take the smaller of their two book sizes). This card fixes the other two and makes the slot a
real region.

**What changes.**

1. The puzzle area splits into **two equal slots**, separated by a **light rule** across the
   text width. Equal means measured: the two slots' heights differ by at most a pixel.
2. Each slot "follows the same rule as a full page" (the owner's words): the grid centred
   horizontally, the 42% placement within the slot, and **its QR at the slot's outer bottom
   corner** (CARD-223's rule applied per slot, not per page).
3. **The two grids' bottoms align** with each other — the artifact's "its bottom aligned with
   the grid's bottom". With a shared cell size (CARD-225) and equal slots this follows, so the
   test is the proof that all three cards agree, and it is the one that fails first if any of
   them drifts.
4. Keep CARD-204's folio reservation on the lower slot. It was added for a real regression —
   two-up pages were losing their folios — and the owner accepted its measured cost (about 5%
   of pairs refuse to share a page). That cost does **not** change here.

## Acceptance criteria

- **AC-1** (happy, equal slots): *Given* a two-up page, *then* the two slots' heights differ
  by at most one pixel and a light rule lies between them, spanning the text width.
  (test: `TestBookTwoUp_SlotsAreEqualAndSeparated`)
- **AC-2** (happy, same left edge): *Given* two puzzles of the same grid size on one page,
  *then* their grids' left edges are identical. (test: `TestBookTwoUp_GridsShareTheirLeftEdge`)
- **AC-3** (happy, aligned bottoms): *Given* any admitted pair, *then* each grid's bottom sits
  at the same offset from its own slot's bottom. (test: `TestBookTwoUp_BottomsAlign`)
- **AC-4** (REPLACED 2026-11-07, see the amendment; the QR is gone): *Given* a two-up page,
  *then* no QR ink lies on it and the page's single footer line lies below the lower slot,
  outside both slots' heights. (test: `TestBookTwoUp_NoQrAndOneSharedFooterLine`)
- **AC-5** (guard, the folio survives): *Given* every two-up page, *then* it carries its
  folio, and the lower slot's reservation is unchanged.
  (test: `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber`)
- **AC-6** (edge, different grid sizes): *Given* a 15x15 and a 10x20 sharing a page, *then*
  both draw at the smaller book size and both slots still hold their own grid and rule (the QR clause was removed 2026-11-07).
  (test: `TestBookTwoUp_MixedGridSizes`)
- **AC-7** (edge, the pairing rate): *Given* the corpus, *when* the interior is exported,
  *then* the number of pages is recorded against the figure before this card, and any change
  is attributed — equal slots may admit or refuse a pair the old asymmetric layout did not.
  (test: `TestBookTwoUp_PageCountIsAttributed`)
- **AC-8** (registry, the flip back this card owes): *Given* this card merged, *then*
  `requirements.yml`'s **FR-040/AC-379** carries a `test:` key again, naming the test this
  card writes for the per-slot 42% float, and that test asserts AC-379's own `then` — each
  slot's drawing at 42% of **that slot's** spare height with 58% below, measured off the
  drawn ink — not merely a name that resolves.
  **AC-8 is TWO claims and they have two different kinds of control. Split, because a
  `(test: …)` slot covering only the narrower one is exactly the defect this family
  exists to catch, one layer up** (CARD-316 fix round 1, review cycle 1's F-003):

  - **the RESOLUTION half — mechanically checked.** (test: the criterion's restored
    `test:` key resolving to a real `def`/`class`, which
    `tests/test_check_ref_resolution.py` measures: AC-379's ref leaves that module's
    honest-dead class and enters its defined class, and its `CENSUS` baseline grows by
    one.) This is a real, failing-capable control and it witnesses the resolution and
    nothing more.
  - **the ASSERTION half — `check: review-lens`, owner: whoever reviews CARD-226.** That
    the restored test asserts AC-379's **own** `then` — 42% of *that slot's* spare
    height, 58% below, measured off the drawn ink — has **no mechanical control on this
    board and this card does not pretend otherwise**. Measured, in CARD-316's review
    cycle 1: a criterion re-pointed at an existing, defined, already-declared test that
    asserts something else leaves `tests/test_check_ref_resolution.py` at **23 passed,
    all green**, and takes the validator of record from **88 to 87** — one warning out,
    nothing in. So the combined gate is *cheaper* for that re-point than for an honest
    missing key, and no pin can see it. The reviewer of CARD-226 must read the restored
    test against AC-379's `then` and say so; a green suite is not evidence here
    (`adr-check-refs-must-be-honest`, ADR-0039/R1).

  <!-- Added 2026-10-31 by CARD-316. AC-379 was declared in requirements.yml as a forward
  declaration for this card and carried a `test:` key naming a test nobody has written, so
  an OWED test read as a PERFORMED one to forge:status and to the kanban AC/EC gate — one of
  seven such keys CARD-316 withdrew. CARD-316's own brief asked for `kind: review-lens`
  instead of a withdrawal; that was measured to be a no-op (the validator of record passes
  the literal "test" as the check kind for every AC `test:` ref and never reads the entry's
  `kind:`; planting the flip left the WARN set byte-identical), so the key was dropped like
  the other six and the obligation moved here. The reason it is an AC and not a note:
  a demotion with no card owing the flip is how a shim becomes an end state
  (`adr-check-refs-must-be-honest`). AC-379's text and id are unchanged in the registry;
  only its `test:` key is gone, and its comment block there records the planned name.

  AND THE GATE ON THIS CARD, recorded where the obligation sits (CARD-316 fix round 1,
  F-003): CARD-226 cannot start today. Its header carries `Revision pending: true` and
  meta/kanban/board.md lists it among the gated cards; its blocker turns on an
  architecture decision — ADR-0037/R2's device floor versus R7, which makes R2
  inapplicable to the interior — and that decision has NO CARD anywhere on the board.
  So AC-379's registry state is honest in the meantime (no key, a comment recording the
  plan) but the flip-back is owed by a card whose own blocker is un-carded, and the shim
  may stand for as long as that owner decision does. That is a weaker guarantee than
  "the obligation is carried by a card" sounds, and it is stated rather than implied. -->

## Guardrails

- G-1: FR-040 decides *which* puzzles pair; this card decides how a page holds them. No change
  to the pairing predicate (test: the existing pairing tests).
- G-2: The caption/folio collision CARD-204 Fix 8 closed stays closed, on both slots (test:
  the existing caption-slot and folio tests).
- G-3: **`_draw_solved_slot`'s return value has two consumers** — `solved_puzzle_page` and
  `_packed_answer_page` — and nothing enforces changing them together. This family has
  produced five gating regressions across CARD-203 and CARD-204. If this card touches that
  return value, both consumers change in the same commit, and the notes say so.
- G-4: Out of scope — the solution pages' tiles (CARD-232), the cell size rule itself (CARD-225).
- G-5: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-226 --root meta/architecture` (60 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **FR-040 — still owed.** Its "and only when" clause already needed an amendment at the
  architect station and **still does**: the 2026-10-17 delta carried CON-018, NFR-008, FR-030,
  FR-031, FR-032, FR-043 and INV-013 only, and did not touch FR-040.
- **Mirrored margins are now a geometric no-op on Book 1** (gutter == outside == 12.700 mm,
  CON-018 as amended 2026-10-17). FR-030's AC-272 and AC-273 now hold the same span
  (12.700..203.200 mm) and FR-032's AC-274/AC-275 the same left edge (25.45 mm), so on the
  default profile **a passing parity assertion about the usable area or a margin width is an
  identity, not evidence** that mirroring works. The mirroring rule (FR-030's last sentence,
  TERM-034) and EC-032's "gutter minus outside" formula stay true with a zero difference and
  still bite on any book storing **unequal** margins — the only configuration in which
  mirroring is actually under test. Owner decision 2026-10-17: record this, do not restore the
  asymmetry by changing a margin. An assertion about *which side* something sits on (left vs
  right by parity) still has teeth; one about *how wide* the margin is does not.
  For this card that lands on **AC-4**: "no QR ink in the gutter half of the page at either
  parity" is a claim about which *side* the slot's QR sits on, so it keeps its teeth — the
  identity only removes the margin-width half of a parity assertion, not the left/right half.
  Any slot-geometry assertion phrased as "the usable area moves with parity" is the identity.

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unch… (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_53 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-040, FR-043.
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0036/R2.
- **Components:** COMP-007, COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [Why AC-3 is the keystone] Aligned bottoms is the only assertion in the set that fails if
  *any* of CARD-224, CARD-225 or this card drifts. It is cheap to write and it is the one to
  keep green.

## Architecture revision (2026-10-25)

**Reason:** ADR-0042 (DEC-048) accepted 2026-10-25 — the book interior is written
as PDF content-stream operators; the cover stays raster because it is a
photograph, and the section dividers stay raster for now by owner decision the
same day. The phase that converts the interior is CARD-294..CARD-299 (waves
60-64), and this card is scheduled after it.

**Was:** a two-up page becomes two equal slots split by a **light rule** — and
the card cites ADR-0037/R2 directly, which is the rule that says the
furniture-vs-grid distinction "can no longer be solved by width" because "width
has reached the device floor" and "now rests on tone".

**Should be:** the same design, with width available again. In a vector interior a
light rule can genuinely be light — ADR-0042/R7 removes the floor that forced the
distinction onto tone alone.

**Delta:**
- The "light rule" is re-derivable as a width, not only as a grey. Re-decide which
  it is rather than inheriting the tone-only workaround.
- This card's citation of ADR-0037/R2 must be re-read against ADR-0042/R7 before
  the card is rewritten; the clause it leans on is the one R7 narrows.
- Its tests move from ink measurement to content-stream assertions.

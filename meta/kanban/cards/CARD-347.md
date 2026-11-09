# CARD-347: Retire the carried figures in the player family's records — the line-count column is one of five, and four are not in the README

**Status:** skipped
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** trivial
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Two findings from CARD-339's review cycle 1 (2026-11-04) that share one cause: a record that misdescribes, needing a file the originating card could not reach. The review ruled on both — item 7 ("keep the update, and card the retirement now rather than leaving the next card to rediscover it") and F-9 ("yes, the name now misdescribes what it asserts"). CARD-339's round argued for retirement and filed nothing, which is why this exists.
**Idea:** —
**Wave:** —
**Created wave:** 74
**Deferred waves:** 0
**Depends on:** CARD-339
**Touches:** docs/how-it-works/01-domain/puzzle-creation/README.md, docs/how-it-works/01-domain/puzzle-creation/11-the-public-player.md, tests/test_public_player_maybe.py, tests/test_public_player_agreement.py, player/player.css, meta/kanban/cards/CARD-323.md, meta/kanban/cards/CARD-339.md
<!--WIDENED 2026-11-04 by CARD-339's review cycle 2, whose pattern finding is that this card's scope was drawn too narrowly: it took the README COLUMN, but the figures that actually rotted sit in a card body, a module docstring, a stylesheet comment and a docs paragraph. The docs file joins Touches for MIN-2's five false play.js refs. -->
<!--WIDENED AGAIN 2026-11-04 by CARD-339's MERGE GATE, as its finding 3, and this one was the orchestrator's error: the note above names four locations and the Touches list reached only two of them. player/player.css, tests/test_public_player_agreement.py and meta/kanban/cards/CARD-339.md are now listed, so the card can actually reach the stylesheet comment, the module docstring and the card body it was widened to cover. A scope note that names more files than Touches grants is a card that cannot do what it says. -->
**Review score:** n/a — **RETIRED** on the owner's 2026-11-09 tech-debt triage. No work is owed here.
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Part 1 — the line-count column is an ungated convention with two measured failures

CARD-323's round set the policy: *a file-table line-count row for a file the card itself
changed is updated in the card's own round; a bare `path:line` cross-reference in prose stays
`/forge:explain`'s.* CARD-339 was the first card to inherit it, followed it as written
(`player/player.css` 482 → 521), and produced **two data points for retiring it instead**:

1. **The row was stale-by-construction the instant the edit landed, and nothing would have
   redded.** It is an ungated convention — the next card that forgets reproduces the defect
   silently.
2. **The same edit rotted two prose `path:line` refs** in
   `docs/how-it-works/01-domain/puzzle-creation/11-the-public-player.md` which the policy
   assigns to `/forge:explain` rather than to the card — `player.css:425` → `:485` (off by 60)
   and `` `:440`-`456` `` → `499-514`. So the convention produced one figure the card fixed by
   hand and two it was told to leave.

**The card's own instruction**, written before any of this was measured: *"If you find yourself
updating that row a second time, retire it instead and say so."* This is that second time
arriving as a separate card rather than as a second update.

**The precedent for retiring a figure rather than maintaining it** is on this board twice:
`config.yml` retired the validator's warning count, and CLAUDE.md retired the duplicated
component map in CARD-261 — in that case because *both* copies had drifted, in different
places.

**Re-derive the 521 and the two rotted refs yourself.** They are dated readings.

## Part 1b — the row went stale TWICE inside one card, and that is the third and fourth data points

**Measured by CARD-339's review cycle 2.** CARD-339 updated the row to **521** and was right at
that commit. Its own cycle-2 commit then added **three comment lines** to `player/player.css`
and did not revisit the row, so at that branch's HEAD the row said 521 against a file of
**524**. Attributed with `git log -L145,145`, not inferred.

The card's paragraph asserting *"`player/player.css` moved 482 → 521 **and the row says so**"*
was false in both halves — **inside the very paragraph citing the row's
stale-by-construction property as evidence for this card.** The gate corrected the digit; the
structural point is this card's.

**It then re-staled a SECOND time in the same card.** CARD-339's merge gate wrote a 12-line
clause and the count moved again — the row's final journey was **482 → 521 → 524 → 536**, three
movements inside one card, **with no declaration changing**, because the figure counts comments.
The gate re-derived 536 with **three** independent instruments and recorded that it holds *at
that merge commit and at no other moment*.

**So the convention has now produced, measurably: one figure fixed by hand, two prose refs its
own policy told the card to leave, five false `play.js` refs nobody counted, and TWO
self-restalings inside a single card.** That is not a convention with an exception; it is a
figure with no control.

## Part 1c — MIN-2: the docs file ships five false `play.js` refs, and nobody had counted them

CARD-339's round declined these on the recorded policy (it does not change `play.js`), which
was scope-defensible. Its reviewer then counted them. **Re-derive the table — these are dated
readings and the offsets move:**

| ref | claims | measured actual | out by |
|---|---|---|---|
| `play.js:16` | the UI-glue comment | `:16` | **0** ✓ |
| `play.js:21`-`45` | "THE PAGE NEVER HAS THE ANSWER" | `:21` | **0** ✓ |
| `play.js:174` | `isClueSolved` | `:184` | 10 |
| `play.js:191` | the `nonogram-public:<key>` save key | `:201` | 10 |
| `play.js:352` | sets `--player-wave` | `:363` | 11 |
| `:422` | writes `data-solved` | `:437` | 15 |
| `:235` | `deserialize` | `:245` | 10 |

**Five of seven false**, offsets clustered at 10–15 — one insertion near the top of `play.js`.
The card had measured **two**. And `play.js:352` sits in the **second clause of the very
sentence** whose first clause CARD-339 retired from a line ref to names, which is where "not
this round's to carry" stops being comfortable.

**Retire these to names, as CARD-339 did for its own two.** Do not refresh the numbers.

## Part 2 — a test name that outlived its assertion

`tests/test_public_player_maybe.py::test_the_maybe_cell_look_is_one_rule_declaring_one_background`
now asserts that the cell look is **two** rules —
`['.player-cell[data-state="maybe"]', '.player-cell[data-state="maybe"]::after']` — plus the
glyph's `content` and `color`. CARD-339 taught it the new shape (that was its designed hand-off
from CARD-323) but could not rename it, because **`meta/kanban/cards/CARD-323.md` cites the
method name and is outside CARD-339's `Touches`**, and a rename goes dead under a text-search
check-ref resolver. CARD-339's round recorded the nit in the module docstring, which was the
right interim.

This card holds both files, so it can rename and re-point in one move.

**Also in scope, measured by the same review (its F-6):** `player/player.css` names a node id
that does not exist —
`TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_the_paper_under_the_maybe_mark_is_a_routed_finding_and_not_an_exemption`.
Both halves exist; the combination does not (the method lives in
`TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed`). It is not a `check:` ref so the
validator never reads it, but it sends a reader into a `-k` that selects nothing and **exits 0**.

## What to implement

1. **Retire the line-count column** from the file table, the way `config.yml` and CLAUDE.md
   retired theirs: remove the figure, and say in its place what a reader should do instead.
   Do not replace it with a different uncontrolled figure.
2. **Fix the two rotted prose refs** by retiring them to **names**, not by refreshing the
   numbers — a `path:line` in prose is a carried figure with no control, which is the whole
   lesson here.
3. **Rename the test** to what it asserts, and re-point every reference. **Derive the reference
   set** with a text search across the repo (that is how the resolver works), not from this
   card's list.
4. **Fix `player/player.css`'s dead node id** — one class name.

## Acceptance criteria

- **AC-1** *Given* the file table, *then* the line-count column is gone and no uncontrolled
  numeric figure replaced it.
  (test: named by the implementation; state it, or state that none is possible and why)
- **AC-2** *Given* the docs tree, *then* no `path:line` reference into `player/player.css`
  **or `player/play.js`** remains — derived by search, not by this card's list, and the count
  found is stated. CARD-339's review measured seven refs into `play.js` of which five were
  false; a different number is the finding, not a discrepancy to reconcile.
  (test: named by the implementation; state it)
- **AC-2b** *Given* every record in this card's `Touches` plus `tests/test_public_player_agreement.py`
  and `player/player.css`, *then* each remaining numeric figure either **carries a control that
  can fail** or is **retired**, and the set is **derived** rather than listed (ADR-0039/R2).
  This is the widening CARD-339's review asked for: the figures that rotted were in a card
  body, a module docstring, a stylesheet comment and a docs paragraph — not only in the README.
  (check: review-lens)
- **AC-3** *Given* the renamed test, *then* every reference to the old name is re-pointed,
  **derived by text search across the whole repo**, and the new name describes what the test
  asserts. A `-k` on the new name selects it; a search for the old name finds nothing.
  (test: named by the implementation; state it)
- **AC-4** *Given* `player/player.css`'s node-id reference, *then* the full `path::name` string
  resolves to a real class and method by `ast`.
  (test: named by the implementation; state it)
- **AC-5** *Given* the whole change, *then* `tests/test_check_ref_resolution.py` is green and no
  check ref went dead — a rename under a text-search resolver is exactly how one does.
  (test: `tests/test_check_ref_resolution.py`)

## Guardrails

- **G-1** — No `src/` change.
- **G-2** — Do not retire a figure by deleting the sentence that needed it. Retiring means the
  reader is pointed at the authority instead; CLAUDE.md's component-map retirement is the model.
- **G-3** — Do not rename anything whose references you have not derived. The resolver is a
  **text** search, so an unre-pointed mention reads as dead however green the suite is.
- **G-4** — No new runtime dependency (ADR-0006/R1).
- **G-5** — Take no timing measurements and report no durations.

## System contract

- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate, not
  hand-written (check: review-lens)
- ADR-0039/R4 — a figure recomputed and refuted is retracted everywhere it was written
  (check: review-lens)
- ADR-0038/R8 — tests fail or skip loudly, never silently (check: review-lens)

## RETIRED 2026-11-09 — tech-debt triage

Its targets, the old player test modules, were deleted by CARD-399. The one useful leftover (the player docs still describing play.js) is a separate small docs task.

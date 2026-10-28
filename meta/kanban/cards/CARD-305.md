# CARD-305: The four divider pages become an option on Print setup

**Status:** done
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/305-divider-pages-option
**Worktree:** —
**Source:** owner request, 2026-10-28 — "please add an option on admin panel to add 4 pages (easy-medium-hard-solutions dividers)".
**Idea:** —
**Wave:** 67
**Depends on:** —
**Touches:** migrations/versions/017_book_divider_pages.py, src/nonogram/db/models.py, src/nonogram/admin/book_page_spec.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/print_specs.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_setup_print.html, tests/test_book_divider_pages_option.py
**Review score:** 7.5 → **8.5 cycle 2/3 CERTIFIED**, zero critical, zero important
**Started:** 2026-10-28T12:30:00Z
**Closed:** 2026-10-28T19:54:16Z
**Actual:** 0.9d
**Merge commit:** 48457877
**Blocked by:** —

## The request, and what was already true

The owner asked for an option to **add** the four divider pages. They were
already there — and unconditional. Every book this generator has ever written
carries them:

| page | where | emitted by |
|---|---|---|
| **Easy / Medium / Hard** | one before each non-empty named level | `puzzle_section` → `DividerPagePlan` |
| **SOLUTIONS** | between the last puzzle page and the first answer page | `interior_stream` |

So the deliverable is not the pages. It is the **switch**, which did not exist,
and the arithmetic that has to follow it. The pages stay on by default, so no
existing book changes.

**One divider per non-empty named level, not three.** A book with no hard
puzzles has two level dividers, and the figure this card quotes is therefore a
*delta per book* and never a constant four. AC-5 is the edge that pins it.

## Why this is not a checkbox and an `if`

The divider count is an input to four other things, and all four had to move
with it:

1. **Page numbering and parity.** Four fewer pages shifts every later page's
   number, and a page's parity is where its gutter side comes from (FR-043).
2. **The KDP estimate** (`book_kdp`), which feeds the gutter band and the
   spine. An estimate that disagrees with the written file prints the wrong
   gutter for the book's real length — a defect visible in no render of any
   page.
3. **The table of contents**, which has a row per level divider *pointing at
   that divider's page*. With no divider there is no page for the row to name.
4. **The plan/draw tripwires**, which exist to make exactly this kind of
   change fail loudly. Both fired during implementation, which is the system
   working.

## Acceptance criteria

- **AC-1** (happy, the default): *Given* a book with nothing stored, *then* it
  prints all four divider pages, as every book did before this card.
  (test: `TestDividerPages_TheDefaultIsEveryBookAsItWasBefore`.)
- **AC-2** (happy, the switch): *Given* a book whose option is off, *when* the
  interior is generated, *then* no divider page is planned or drawn and the
  page count falls by exactly one per named level plus one.
  (test: `TestDividerPages_TurningThemOffRemovesExactlyThoseFourPages`.)
- **AC-3** (guard, the walk and the count agree): *Given* either setting,
  *then* the number of pages the walk produces equals the count the interior
  declared. The generator's own `_as_planned` raises otherwise, so this
  asserts the figure **and** that the figure is the one the pages were drawn
  against. (test: same class, `test_the_walk_produces_exactly_the_count_it_declared`.)
- **AC-4** (edge, the level axis): *Given* a book of one named level, *then*
  the delta is **two**, not four — a hardcoded four anywhere would survive
  AC-2 and die here. (test: `test_a_single_level_book_falls_by_two`.)
- **AC-5** (edge, an empty book): *Given* a book with no puzzles, *then* the
  setting changes nothing, because there is no answer key to open.
  (test: `test_a_book_with_no_puzzles_is_the_same_length_either_way`.)
- **AC-6** (guard, the estimate follows): *Given* either setting, *then*
  `unpaired_interior_page_count` equals the interior's own
  `unpaired_page_count`, and the estimate itself moves by the same delta — so
  it cannot agree by ignoring the setting.
  (test: `TestDividerPages_TheKdpEstimateAgreesWithTheInterior`.)
- **AC-7** (guard, the TOC): *Given* the option is off, *then* the TOC carries
  the guide row and the solutions row and nothing else, and the solutions row
  names the **first answer page**. (test: `TestDividerPages_TheTableOfContentsFollows`.)
- **AC-8** (guard, the tripwire inverts rather than disappearing): *Given* a
  page plan that still holds a divider while the book prints none, *then*
  `structural_toc_entries` raises — and the original matching check still
  raises in the other direction. (test: `TestDividerPages_ThePlanAndTheWalkCannotDisagree`.)
- **AC-9** (happy, the screen): *Given* Print setup, *then* the box is ticked
  for a book that prints the dividers, unticking it stores the choice, and
  reopening shows it. (test: `TestDividerPages_PrintSetupStoresTheChoice`.)
- **AC-10** (guard, the one that matters — see below): *Given* a submission
  that does not carry the control at all, *then* the stored choice is
  **unchanged**. (test: `test_a_submission_without_the_control_leaves_the_stored_choice_alone`.)

## The defect this card most risked, and the mechanism against it

**An unticked checkbox posts nothing.** "The owner turned them off" and "this
form has no such field" arrive at the server as the same bytes. Read naively,
the first Print-setup save from any client built before this control — or from
any other form posting to that route — would silently strip four pages out of
a book that wanted them, and the owner would find it at the proof.

The form therefore carries a hidden `interior_divider_pages_present` marker.
The **marker** says the control was on the form; the **checkbox** says what it
was set to. No marker means the submission does not carry the control, and the
stored value is left alone — the same posture `interior_ink_mode` already
takes for the same reason.

That is not just asserted by AC-10: **every other route test in the suite posts
without the marker**, so they are all that case, and they all still expect
their dividers.

## Guardrails

- **G-1: the default is on, and a stored NULL reads as on.** Three independent
  things say so — the column's server default, migration 017's explicit
  backfill, and `divider_pages_from_stored` itself. Only the third is
  load-bearing; the other two make the stored state say plainly what every
  book is.
- **G-2: no page's ink changes.** This card adds and removes whole pages; it
  does not touch how any page is drawn. `create_divider_page` is unedited.
- **G-3: ADR-0036/R1's sheet is untouched.** No page size, margin, cell or
  rule depends on this. The page **count** does, which is the point, and the
  generator's own `interior_page_count` check is what holds the two together.
- **G-4: `None` never means "off".** Not in the column, not in `PrintSpec`,
  not in `create_spec` (which deliberately does **not** default this field the
  way it defaults the ink mode), not in the route.

## What this card owed the architect — **LANDED in fix round 1, not owed**

> **CLEARED 2026-10-28 (cycle 2 F-004).** Everything below was written when this
> card did not touch the registry. **Fix round 1 edited it** — 122 lines: EC-029
> quantified, FR-041 and FR-042 bodies made conditional, `given` clauses on
> AC-253/254/292/293, and **AC-400..AC-405** added with all six refs resolving to
> real definitions. The gap was also **wider than the two entries named here** —
> cycle 1 found five further entries, EC-029 the heaviest, being a standing
> engineering constraint whose property test always built on the default. The
> section is kept rather than deleted because the owed→landed trail is what makes
> the registry edit auditable; read it as history. It sits above the cycle
> sections, so without this note a reader asking "what does this card owe the
> architect" meets a landed item first.

**AC-254 and AC-292 state behaviour that is conditional**, and at the time this
was written the card did not edit the registry:

- **AC-254** — "each divider page's only content is its level's name" is still
  exactly true *when the book prints them*; the criterion needs a clause
  saying so.
- **AC-292** — "the page immediately after the last puzzle page and
  immediately before the first answer page carries only the word SOLUTIONS"
  is now false for a book with the option off.

Both existing tests still pass, because both build books on the default. The
honest change is a `given` clause on each naming the setting, plus a new
criterion for the off case — which is an architect-station edit, not this
card's. **Recorded here rather than done, so it is a visible gap and not a
phantom one.**

## Worktree notes

- **The TOC tripwire was the one real surprise.** `structural_toc_entries`
  cross-checks the plan's dividers against the book's own level runs and
  raises when they disagree. With the dividers off it raised, correctly — the
  plan had none and the runs had three. The fix was **not** to relax the
  check: it inverts. When the caller says the book prints no dividers, a
  section that still holds one raises instead. Both directions are tested
  (AC-8), because a check that only fires one way is half a check.
- **The estimate is the *unpaired* count.** `unpaired_interior_page_count`
  computes one page per puzzle and one answer page per puzzle, so it equals
  the interior's `unpaired_page_count` and **not** its `page_count`, which
  pairing and packing have already shortened. AC-6 holds it against the right
  one; holding it against `page_count` would have failed for a reason that has
  nothing to do with this card.
- **`interior_page_count` gained `solutions_divider`, not a second count.**
  The existing `level_dividers` parameter is a *count*, and a book without
  dividers reports 0 of its own accord because `dividers` is derived as
  `len(section) - len(plan)`. The SOLUTIONS page was the term with nowhere to
  be said — it had always been a bare `+ 1`.
- **Measured, both settings, on AC-253's five-member book (2 easy, 2 medium,
  1 hard):** 18 pages → **14**. Three level dividers and SOLUTIONS. The walk
  produced 18 and 14 respectively, which is the generator's own tripwire
  agreeing, not a second count of mine.

### [SYNCED TO MAIN — 2026-10-28, orchestrator]

This card file reached `main` only now. It was committed on
`card/305-divider-pages-option` at `317d665c` and the CARD SYNC PROTOCOL's
one-way copy into the main repo never ran, so for the whole of waves 63–67
`meta/kanban/cards/CARD-305.md` did not exist here: the board could not count
it, `/forge:kanban CARD-305` could not find it, and `main` ended up carrying
this card's **cycle-2 review report** (`3b242f86`) while having no record of
the card it reviews.

One field is changed in the copy, and only one: **`Status: in progress` →
`review`**. The branch copy's status contradicted its own `Review score:`
field, which records a certified cycle 2 — a card with two completed review
cycles is not in implementation. Per the protocol's own definition, `review`
covers the review↔fix cycle, the AC/EC gate, and a card that has passed and
awaits `done`. Nothing else was edited; the body is the branch copy verbatim.

**Not yet done for this card, stated so it is not assumed:** no AC/EC/G gate
line (the same board-wide gap CARD-267's merge exposed — `done` step 2a has
been refusing nothing), and no merge gate against a base re-merged from
current `main`. Its own recorded gate was green at 1502 on the branch, which
is not the same claim.

## [GATE — 2026-10-28] green at 1502, and four guards had to be answered first

**`1502 passed, 0 failed, exit 0`** over 22 files (the book export, page-spec,
print-spec, plan-storage, workflow and CLI sets), rival-pytest **0 / 0**, on
the branch rebased onto main at `9a61b928` (CARD-227 merged while this was
being built).

The first run was **44 failed**, all in `tests/test_book_export_interior_cover.py`.
**Main was measured green on that file first (133 passed)** before any of it
was attributed here — the board's own CARD-295 lesson. Four distinct guards
had to be answered, and not one of them was a number raised until green:

1. **The door-axis anchor (42 of the 44).** `DERIVED_POSITION` is a *verbatim
   copy* of `interior_stream`'s `first_answer_page` statement, which the walk
   replaces **line-count-preservingly** with each planted shape, asserting it
   occurs exactly once. Its own docstring promises that "an edit to it reds
   rather than quietly planting nothing" — so 42 reds is the guard working.
   The statement was reflowed to eight lines by this card; it is now back to
   **three**, with the conditional kept **inline**. Hoisting it into a local
   would have put a term of a page position behind a name, which is the
   laundering `test_no_door_shape_is_laundered_by_an_unrelated_resolving_occurrence`
   exists to catch. The anchor is re-stamped to the new text, still one
   occurrence, still three lines.
2. **The exemption's term vocabulary.** `self.divider_pages` adds `self` and
   `.divider_pages` to the terms the walk reads-but-declines-to-follow,
   because what they resolve to is a stored column on one book. The **site**
   count is unmoved at 5 — the terms landed on a position that was already
   exempt — and the two figures are asserted separately, so a change that
   added a sixth site would still red. Both new literals (`0`, `1`) are
   already in `POSITION_LITERALS`.
3. **`CALLEE_EXEMPTION_COST`, re-stamped the way CARD-227 re-stamped it:
   772 → 776, 519 → 522, and 204 unmoved.** Derived before it was touched,
   from the four calls this card adds — `book_divider_pages` ×1, `TocEntry`
   ×2, `RuntimeError` ×1. Total takes all four (**+4**); the `("builtins",)`
   step excludes `RuntimeError` and takes three (**+3**); the "definitions and
   imports" step absorbs all three non-builtins — one *import*, two
   module-level *definitions* — so its remainder is **unmoved**. Three
   figures, three derivations, one of which predicts *no* movement.
   **Cross-checked in a second domain:** my own `ast` walk of the module reads
   **834 → 838**, exactly +4, independent of the test's instrument.
4. **Two consequences of changed surfaces**, each a real declaration:
   `PrintSpec.to_dict()` gained `interior_divider_pages`, which is `None`
   after a bare `create_spec()` **on purpose** (no default — see G-4); and
   `test_book_pdf.py`'s `interior_page_count` stub mirrors the real signature
   rather than swallowing extras in `**kwargs`, so a forgotten parameter reds
   instead of being dropped. It reds; it was.

**Nothing in the feature changed to make a guard pass.** The only production
edit in this round was reflowing one statement back to three lines — same
arithmetic, same terms, same result — and the 22 assertions verified earlier
by plain-Python probe were re-run afterwards and still hold.


## [CYCLE 1 — 2026-10-28] **7.5, NOT CERTIFIED** — the production code survives 8 deletion mutants; the flagship test cannot fail

Report: `meta/review/20261028T142020Z-CARD-305-cycle1.yml` (7 findings, parses,
written into the main repo). Reviewed `1e6087b3` against merge-base `9a61b928`.
**10 mutants + 3 re-fires, 8 killed, 2 survived** — and **both survivors are test
defects, not code defects**, proven by a discriminator that is green at HEAD and
red on each mutant. Validator **0 errors / 113 warnings**, exactly main's
baseline. Gate 1189 passed / 1 skipped / 0 failed, the one skip attributed by
name (the pre-existing platform `setrlimit` one).

**A figure correction that lands on this card and on the orchestrator's brief:
the diff is 14 files (+1241/−21), not 22.** `git diff --name-only
9a61b928..HEAD | wc -l` = 14, confirmed. The 22 is this card's *gate selection*
size, not its diff, and both the card and the dispatch brief stated it as the
diff.

### F-001 (important) — the card's flagship defence is driven from the one state where its defect is invisible

`tests/test_book_divider_pages_option.py:403` is nominated on the card as *"the
one test that would have caught the defect this card most risked"*, and its
docstring reasons: *"Driven from 'off', because a book already at the default
would pass this test whatever the code did."* **That reasoning is inverted, and
the orchestrator re-read the test to confirm it.** From OFF, the broken naive
read yields `bool(None)` → `False` — precisely the value the test asserts.
Mechanism-working and mechanism-deleted produce the same byte.

Both mutants that delete the mechanism **survive it**: `app.py:3715`'s marker
guard → `if True:`, and `book_manager.py:1003`'s `is not None` guard → `if True:`.
AC-10's cell passes in both storage modes under each. The review's attribution
control is the right shape — a cell driving the same no-marker POST from the
**default (ON)** book, green at HEAD and red on both mutants. **The production
code is correct; the test is the defect.** The fix is to keep the from-OFF leg
and add the from-ON leg.

Corroborating and confirmed: `interior_divider_pages_present` appears in no test
file but the new one, while 18 other test files POST to that route — but all of
those books sit at the default and none asserts the column afterwards, so they
exercise the path without discriminating on it either.

### F-002 (important) — the architect gap is real and **under-scoped by five entries**

The card records that AC-292 goes false for an option-off book and AC-254 needs a
clause. Both calls are right, and AC-254 is correctly judged the subtler one (its
`when` is vacuous over an empty set, so it stays true). **But the same argument
reaches five further entries the card does not name, one of them heavier than
either:**

- **EC-029** (`requirements.yml:3786`) — "the book PDF holds exactly one divider
  per non-empty level … **for every sequence, not only the measured examples**".
  Now false. It is an **engineering constraint** — a standing property — and its
  property test asserts `names == levels` on every step of every trial while
  creating every book through `create_book`, therefore always on the default. It
  passes and verifies nothing about the off state. Exactly the shape the card
  diagnoses for AC-254/292, one layer up.
- **FR-041** and **FR-042** bodies carry unconditional divider prose.
- **AC-253** and **AC-293** ("after 1 SOLUTIONS divider page (32 pages)") go false
  for an option-off book.

### F-003 (medium) — no parity control for the off state

The card names FR-043 parity as the widest consequence and is right. The new file
controls page **count**, TOC rows, the walk/declared tripwire and the KDP
estimate — **none would catch a page drawn on the frame of a parity it no longer
has.** Two independent signals: `tests/property/test_book_export_interior.py`
co-changed with the generator **22× in 12 months** and is absent from this diff,
and it hardcodes the divider model with no off arm; and the board's precedent for
the mirror change (one page *added*) is
`TestGuidePage_ExtraPageShiftsEverythingByOneKeepingParity`, with no equivalent
here for four pages removed. Severity medium because the mechanism is
structurally sound — one page-number source, `page_is_right_hand(n) = n % 2 == 1`,
every frame from `self.page_spec(page_number)` at draw time.

### The four guards: all genuinely answered, none bumped

Independently re-derived, including the one that matters most: the
`CALLEE_EXEMPTION_COST` triple (772→776, 519→522, 204 unmoved) was re-measured
**in a new domain** — the reviewer's own `ast.Call` walk reads **834 → 838, +4**,
per-callee `RuntimeError +1`, `TocEntry +2`, `book_divider_pages +1`, matching the
card's enumeration — and then validated end to end with an instrument control
that makes it rise (+1 at step 0) and a negative near-miss that correctly stays
unmoved (`bool` is excluded at that step). The `DERIVED_POSITION` anchor is 3
lines, occurs exactly once, and its edge mutant reds at the stated cell. No
production edit was made to pass a guard beyond the documented 3-line reflow.

**And the blast radius was swept for the defect the orchestrator found before
dispatch** — other signature-pinning stubs and patched callables — with **none
found** beyond the `interior_page_count` lambda already fixed.

### Minors and out-of-scope

**F-004** `app.py:3716` reads the checkbox with `bool(request.form.get(...))`,
bypassing the module's own declared reader, so marker + `interior_divider_pages=0`
stores **True**; harmless for the shipped template, but `_DIVIDER_PAGES_FALSE` is
unreachable from the one inbound path, against the card's "one door" framing.
**F-005** a string-vocabulary comment claims a reachability ("what SQLite hands
back for a boolean on some drivers") that is not reachable and names no driver.
**F-006** `interior_page_count`'s `toc_pages=None` default still budgets TOC rows
for level dividers regardless of `solutions_divider` — latent only.

**F-007 (out of scope)** migration 017 is executed by **no test**: the one
`upgrade(..., "head")` call is intercepted by a fake engine factory before any
SQL runs. At its precedent, not below it — migration 013 has none either. The
chain was checked by reading (clean: `revision 017`, `down_revision 016`, no
fork; `server_default=sa.true()` plus an explicit backfill; batch mode for
SQLite; downgrade drops only the column). **The server default and backfill are
unverified on Postgres**, which is what production runs; all measurement was
SQLite via `create_all` from `models.py`, which never runs the migration.

### Could not establish, in the review's own words

The card's **1502 passed** figure — the card never enumerates its 22 files, so its
domain cannot be reconstructed; the review's 1189 is a different domain and
neither confirms nor refutes it. The card's **rival-pytest 0/0** figure — it names
no instrument that could be located or re-run. **Migration 017 on Postgres.**
**No render was captured and no page eyeballed** (G-2 verified statically
instead — `create_divider_page` is not in the diff). Seven admin route suites and
the Playwright mobile file were not run.


## [FIX ROUND 1 — 2026-10-28] `daaa2f2f` — the flagship control can fail, and the registry is honest

7 files, +610/−40. F-001..F-006 closed; F-007 untouched as out of scope, but **its
one open question was established by measurement** (below).

**The card's diff figure, stated once and correctly: 17 files, +1951/−42** against
merge-base `9a61b928`. The "22" was never the diff — it is a *gate selection* size,
and it had propagated into the card, the dispatch brief and cycle 1's brief before
anyone measured it.

### F-001 closed — and the fix is a second cell, not a second leg

The survival was reproduced first (both deletion mutants **pass** the shipped cell
at HEAD), then the discriminating case was added as **its own cell** rather than a
leg inside the existing one — because a test short-circuits at its first failing
assert, so two cells give two verdicts.
`test_a_submission_without_the_control_leaves_the_default_on_alone` drives from
*nothing stored* — every production book's actual state — and reds for **both**
mutants (`app.py:3715`'s marker guard → `if True:`, `book_manager.py:1005`'s
`is not None` → `if True:`) in **both** storage modes. Verified by the
orchestrator: the cell is defined at `tests/test_book_divider_pages_option.py:656`
and collects 2 node ids.

The inverted docstring reasoning is corrected in three places — the new cell, the
from-OFF cell (which now **states that it cannot fail on the mechanism**, and why
it is still worth keeping), and the module docstring, which repeated the same
false claim. *A guard-cite correction with it: the guard is at `book_manager.py:1005`,
not `:1003` as cycle 1 cited.*

### F-002 closed — six new criteria, every ref resolving, and no phantom check

**EC-029** is quantified: grouping, within-level order and the unbroken 1..n stay
unconditional, and only the one-divider-per-level clause is conditional on the
setting. **FR-041** and **FR-042** bodies made conditional. **AC-253/254/292/293**
gained `given` clauses naming the setting, each with a comment giving the reason —
including that AC-293's quoted "32 pages" is really 31.

Six criteria added: **AC-400** (no divider page at all), **AC-401** (parity, both
states), **AC-402** (unticked stores off), **AC-403** (FR-042's own SOLUTIONS page
off), **AC-404** (the per-level-plus-one delta), **AC-405** (the absent-marker
rule, pointing at the discriminating cell **by name**). **Orchestrator-verified:
all six refs resolve in `tests/` via `git grep -w`** — zero dead refs, which is the
rule this board repaired across ADR-0042's four checks on 2026-10-25.

**And EC-029's existing `kind: test` ref really sweeps both states now**, because
the off-state arm was written into `tests/property/test_book_order.py` **in the
same commit** — so no `review-lens` was needed and no card owes a flip.
`_expected_section`/`_planned_section` take a `dividers` parameter so one
expectation covers two states and they cannot drift into two rules. Proof the old
arm covered *nothing*: the file never sets the column and every book is built by
`_parity_book`/`BookPDFGenerator(None)`, so it was on the default **by
construction** — a proof, not a sample.

### F-003 closed, and the attribution is exact

`TestDividerPages_EveryPagesParityIsStillItsOwnPosition` reads parity off the
**rendered ink** (`drawing_of`), on a book with unequal side margins, in both
states — the same instrument and configuration as the board's precedent for the
mirror change. A second cell asserts the two states put the first measurable
drawing on **different sides** (page 6 left with dividers, page 5 right without),
without which the parity cell would pass for a generator that ignored the setting
when numbering.

**Killed by exactly one cell out of the file's 89** — the `[False]` parity cell,
and nothing else — for `first_answer_page`'s `(1 if self.divider_pages else 0)` →
`1`. That is precisely the defect the finding said nothing would catch: answer
pages keep their numbering while four pages are gone, so they are drawn on the
wrong parity, and the walk/declared tripwire does not fire.

**`tests/property/test_book_export_interior.py` is deliberately OUT of scope**, with
reasons rather than silence: the off state is unreachable in it by construction
(no occurrence of the column; every book comes from the routes or `_parity_book`),
its divider model is **narrower rather than wrong**, and what it would add is
corpus *breadth* while the missing thing was the invariant — now asserted directly
against the real `interior_pages` walk in both states. Recorded as owed if the
board wants the breadth too.

### F-004/F-005 fixed, F-006 recorded and left latent on purpose

**F-004**: the route's `bool()` read made `_DIVIDER_PAGES_FALSE` unreachable from
the one inbound path, so the module's "one door" was prose. New
`divider_pages_from_form` is the form's door onto the same vocabulary, where empty
means **off** — the opposite of what the stored-column door makes of it, which is
why it is a second function. An unrecognised value raises `ValueError`, which the
route already turns into a flashed refusal storing nothing, so **no new error path
was invented**. 10 cells red for the mutant; the edge mutant on the
empty-means-off guard reds 9 including the shipped template's own path.

**F-005** narrowed, not deleted: the driver half named no driver and was
unreachable, so it is gone; the form half is now **true**, because F-004's fix
makes the route go through it. **F-006** recorded with a paragraph stating plainly
that `solutions_divider` does not reach the `toc_pages=None` default — not
"fixed", because making the default follow the parameter would turn an upper bound
over every book into one caller's figure, and every production caller passes
`toc_pages`.

### A pre-existing GATING failure in this card's own diff, found by the fix round

`meta/profiling/rank_durations.py`'s frozen render set is a grep over
`tests/**/*.py` asserted as an **equality** by `tests/test_suite_profile.py`. This
card's new test file matches it (through `interior_stream`), so
`test_the_frozen_render_set_still_matches_the_grep_that_defines_it` was **red at
HEAD** — and **neither the card's own 22-file gate selection nor cycle 1's 21-file
selection included that file**, so the guard fired exactly as designed and was
simply never run. Closed at CARD-222's precedent (added, not dodged), with the
restatement that the file is in **neither** durations artefact, so it contributes
0 s and 0 tests and every recorded share stays the same number over the same
artefact. `tests/test_suite_profile.py` now **410 passed**.

*The round's own figure for that set was wrong first and corrected: it wrote 34,
re-derived 36 through two doors (an `ast` parse of the tuple, and the comment's own
defining `grep`), and found the entries' running prose total had already drifted.*

### F-007's open question — ESTABLISHED, on a scratch database

Cycle 1 recorded "the server default and backfill are unverified on Postgres,
which is what production runs". Measured now against PostgreSQL 18.1 on a
throwaway database the probe creates and drops (`nonogram_card305_probe`;
production's `nonogram_poc` untouched), and **not** as a test, so F-007 stays
exactly where it was: at revision 016 the column does not exist; a row written at
016 reads `interior_divider_pages = t, is null = f` after `upgrade 017` — **the
server default and the explicit backfill do fill an existing row**; the column
declares `boolean | nullable YES | default true`; a new row omitting the column
reads `t`; and `downgrade 016` drops the column while **both rows survive**.

### The round's own measurement error, self-reported rather than hidden

Its parity edge mutant was aimed at `page_is_right_hand` and **survived**. The
reason is that this function governs the answer caption box and the guide's text
side, **not** the sheet's mirrored margins the instrument reads — those come from
`book_page_spec._parity`, whose mutant reds all three cells. So the class's edge
*is* covered, and no false claim shipped, because `page_is_right_hand` is named in
no shipped docstring. **Declared and not closed:** `page_is_right_hand → return
True` survived the three files it was fired against, and whether anything else in
the suite kills it was not established. Pre-existing; this card does not edit it.

### Gate and validator

**1982 passed / 0 failed / 0 skipped** over 25 files in two runs (A: 10 files,
1030 passed, 138.60 s — backgrounded, because it exceeds the 120 s tool timeout;
B: the whole `setup-print` route blast radius, 15 files, 952 passed, 61.77 s).
Zero skips in either run, so there is none to attribute; cycle 1's single
platform `setrlimit` skip is in a file this selection does not include. Both
storage modes really ran — `memory` and `db` cells are named in the mutant logs.

**Validator 0 errors / 113 warnings**, with both controls: an independent recount
in a new domain (`grep -c` on the indented labels) agreeing at 113/0, and the
baseline re-measured *in the same place* by writing HEAD's `requirements.yml` over
the working copy, re-running, and restoring with a verified sha256 — so it is
baseline-for-baseline rather than baseline-by-assertion. An intermediate reading of
115 was two `'then' bundles several outcomes` warnings on the first draft of
AC-400 and AC-402, closed by **splitting** them into AC-400/404 and AC-402/405 —
a better shape, not a suppression.

**RETRACTED AND EXPLAINED (cycle 2 F-001).** This paragraph claimed the 112-vs-113
split sat on a **byte-identical** `requirements.yml` with "sha256 equal both
sides". **That is false and was checkable**: main's copy hashes `0408c9f4…` and the
branch's `9c761cf8…`, differing by 122 lines — this card's own registry delta.
Main carries none of this card's commits, so the two files *cannot* be identical.
The orchestrator re-measured both hashes before retracting this.

The real cause is exact, reproduced on both sides, and **wider than this card**:
the differing warning is the pre-existing INV-013 `check_ref_missing` for
`TestGuideSpread_SitsOnPagesTwoAndThree`, and the validator decides ref existence
with `git grep -w` excluding only `:(exclude)meta/architecture` and
`:(exclude)*.md` — so **`meta/review/**.yml` is inside the search domain**. In
main that symbol is found in `meta/review/20261028T142020Z-CARD-305-cycle1.yml`
(exit 0); in the worktree there is no match (exit 1). **This card's own cycle-1
report resurrects the dead ref**, which is why main reads one warning fewer. The
branch's **113** is the honest number, and a cycle's report can flip the next
cycle's count in either direction. Recorded in `meta/kanban/backlog.md` as its own
item, since it quietly weakens `kind: test` — the mechanism the board repaired
across ADR-0042's four checks on 2026-10-25.

### Still could not establish

The card's **1502 passed over 22 files** — the card still does not enumerate those
22 files, so its domain cannot be reconstructed; 1982 over 25 is a different
domain and neither confirms nor refutes it. The card's **rival-pytest 0/0** figure
— it names no instrument that can be located or re-run. **No render was captured
and no page eyeballed by a human**; the parity cell reads real rendered ink, but
that is an instrument reading pixels, not the owner's eye on a proof.


## [CYCLE 2 — 2026-10-28] **8.5 CERTIFIED** — every cycle-1 finding closed by measurement, and the orchestrator's board call on three prose defects

Report: `meta/review/20261028T171709Z-CARD-305-cycle2.yml`. Reviewed `a05956b2`.
**10 mutants, 10 killed.** Zero critical, zero important. System contract: 56
rules, 14 ✓, 41 ⚠, 1 ✗ (ADR-0039/R4, the prose defects below).

**All four cycle-1 findings closed in substance, not presence:**

- **F-001** — both deletion mutants red the new cell and **nothing else**, in both
  storage modes, with the from-OFF cell passing under each. The fix round's
  `:1005` cite was right and cycle 1's `:1003` was wrong.
- **F-002** — EC-029's existing `kind: test` ref genuinely sweeps both states:
  M3 and M4 each red the property test **through the off arm's own assertion**
  (`tests/property/test_book_order.py:341`), not through the pre-existing on arm.
  The `DIVIDERS_OFF` fixture's "two arms differ in one setting and nothing else"
  was probed independently and holds. All six new refs resolve to real
  `class`/`def` definitions, not docstring mentions.
- **F-003** — the exactness claim is **true**: M5 reds **1 of 89** cells, the
  `[False]` parity cell and nothing else, and the class has a real edge mutant
  (M9 reds all three). `MEASURABLE_PAGES = 10` is asserted inside the cell, so a
  loop that stopped finding pages would fail.
- **F-004/F-005** — the two-door asymmetry is intended, controlled and asserted
  as "the EDGE" across an 11-case parametrisation; three mutants pin it. An
  unrecognised value really reaches the route's **existing** flash path, executed
  outside `tests/`: one alert, HTML-escaped by Jinja (no injection), status 200,
  stored choice unchanged. **F-006's latency is safe** — all four production
  callers pass `toc_pages` (`book_pdf_generator.py:7093/7275/7289`,
  `book_kdp.py:559`).

**Two residuals the fix round declared unclosed are now closed**, and one of them
did not matter: `page_is_right_hand → return True` is killed by **9 cells across
4 files**, including INV-013's own property test — the fix round's three-file
selection simply did not include them. And the `rank_durations.py` guard is green,
with the "necessarily red at pre-fix HEAD" claim established **by construction**
rather than by memory.

### The orchestrator's board call on three prose defects

Cycle 2 filed three refuted figures/cites as **Minor** while flagging that Step 8h
prescribes Important as the minimum for a mandatory rule (ADR-0039/R4), and
explicitly left the disposition to the board rather than deciding it. **Ruled:
blocking before the merge gate, not blocking the certification.** The score is
8.5 either way; the claims were false and checkable, which is ADR-0039/R1's own
family and the largest single source of gating findings on this board. All three
are fixed above and in `373ca08b`:

1. the "byte-identical `requirements.yml` / sha256 equal both sides" claim —
   **false**, re-measured by the orchestrator (`0408c9f4…` vs `9c761cf8…`, 122
   differing lines), retracted and replaced with the measured cause;
2. "the file's 88" — the file holds **89** (`--collect-only` says 89; 88 was the
   *survivor* count in the M5 run);
3. the new cell's docstring cited `app.py:3715` — its own commit moved the guard
   to **:3724**.

**These three edits ship uncertified**, and that is said plainly rather than
glossed: they were applied on the final reviewer's own prescription, so "the
reviewer told me to" is not "a reviewer saw the result". What the merge gate alone
establishes about them is that the suite is green with them in; nothing mutates
them, because they are prose and a line number.

**Carried, not closed (cycle 2 F-005):** the route-refusal cell's *first*
assertion is tautological on this page — `DIVIDER_PAGES_COLUMN in response` is
satisfied by every render, because the template renders that string as `name=`
and `id=`. The docstring positions it as a flash check. Its **second** assertion
is load-bearing and genuinely strong (M7 and M8 both red the cell through it), so
nothing is unguarded; the fix is to match `alert-danger`/`role="alert"` or the
measured phrase "must be empty or a boolean", which no plain render produces.

### Out of scope, and the second one is board-level

- **AC-292's check ref is DEAD** — `TestBookAnswerKey_SolutionsDividerPrecedesAnswerKey`
  resolves nowhere in `tests/`. Strictly pre-existing (it is in main's 112-warning
  baseline) and the fix round's "no dead refs" claim was correctly scoped to the
  six refs it wrote — **but F-002's remediation amended that very entry's
  `given`**, so FR-042's on-state SOLUTIONS criterion now reads as
  narrowed-and-checked while nothing checks it. The off state (AC-403) does have a
  live ref. AC-268/269 share the shape.
- **`git grep -w` is a weaker check than it reads, and this board's own naming
  convention defeats it.** EC-029's registry ref is
  `PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence`; the real symbol is
  `test_PropertyTest_BookOrder_…`, and `-w` cannot match it because `_` is a word
  character — the only `-w` hit is a docstring. The test exists and was proven to
  red (M3/M4), so nothing here is broken, but every "verified with `git grep -w`"
  on a `PropertyTest_` name is softer than it sounds.

### Could not establish, in cycle 2's own words

The card's **1502 over 22 files** (still unenumerated, so its domain cannot be
reconstructed) · the card's **rival-pytest 0/0** (names no locatable instrument) ·
**fix round 1's 1982 over 25 files** (its two selections are named only by
description, never by file list; 1147 over 14 is a different domain and neither
confirms nor refutes it) · **migration 017 on Postgres this cycle** (fix round 1's
probe stands as a single-domain measurement, un-re-derived) · **whether any page of
an option-off book looks right to a human — no render captured and no page
eyeballed in either cycle.**

## [LANDED — 2026-10-28] `48457877` — the merge gate was RED first, and the fix is the durable part

The card's own recorded gate was **green at 1502** — a NARROWED selection, which
never ran `tests/test_book_floor.py`. The merge gate against a base re-merged from
current `main` was **red on one test**:
`TestMigration012::test_no_backfill_and_a_downgrade_that_drops_the_column`,
`no such column: books.interior_divider_pages`. **Both arms measured before
attributing** — main alone GREEN, this branch RED — so it was this card's, not the
host's and not main's. That is the CARD-295 lesson arriving a third time: a
certified cycle with zero gating findings does not mean "merges clean" when the
review ran a targeted selection.

**The mechanism, and why the obvious fix was refused.** The test pins the chain to
literal revision `"013"` and then read books through `BookManager`. The ORM always
describes HEAD, so that SELECT names every column the chain has ever added,
including 017's. **This was the second occurrence** — the comment at that line
records CARD-147's 013 adding `interior_ink_mode` and the fix then being to move
the read 012 → 013. Moving the pin forward expires on the next column, so it was
not taken a third time. The read is **core SQL** now, which names only the columns
it asks for, and the pin and its documented rationale are untouched.

**A weakening was avoided rather than shipped.** The deleted ORM block was not
redundant: `assert legacy.floor_overrides == []` is INV-006's fail-closed reading
(stored NULL → `[]`, not an unset attribute), and it appeared **exactly once in the
whole suite** — on the line the fix removes. It moved to its own test against a
head-state database instead of being dropped, and it is **proved able to fail**:
two mutants in `book_manager.py`, one per path it asserts (`:736`'s `or []` for the
attribute, `:1019`'s fallback for the method), **both killed**, source restored
byte-clean after.

**Latent class, wider than this card and owed a card of its own:**
`tests/test_book_page_spec.py` and `tests/test_book_plan_storage.py` also pin a
literal revision AND use the ORM. Neither fails today. Both meet this wall on the
next card that adds a `Book` column — and that card will find out at its merge
gate, exactly as this one did.

**Gates.** AC gate 46 passed / 0 skipped / 0 failed by node id, all 10 ACs resolved
to real nodes — **zero skips matters here**, because this card touches `migrations/`
and `db/models.py` and DB-mode tests skip GREEN on this box. G-2/G-3/G-4 checked
structurally. Merge gate **9517 / 27 / 0** in 1238.41 s, skip count the baseline
exactly, load 5.59 → 5.16, rival-pytest 0 at both ends, hang dump 0 bytes,
collection **+89** reconciling exactly to the new file, the four existing test files
it edits changing no node count. Deferral scan 1 hit, incidental.

**Still owed by the owner:** that a switch defaulting ON is what was wanted. The
dividers were already unconditional; this card did not add them.

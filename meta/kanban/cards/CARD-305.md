# CARD-305: The four divider pages become an option on Print setup

**Status:** in progress
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/305-divider-pages-option
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-305
**Source:** owner request, 2026-10-28 — "please add an option on admin panel to add 4 pages (easy-medium-hard-solutions dividers)".
**Idea:** —
**Wave:** 67
**Depends on:** —
**Touches:** migrations/versions/017_book_divider_pages.py, src/nonogram/db/models.py, src/nonogram/admin/book_page_spec.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/print_specs.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_setup_print.html, tests/test_book_divider_pages_option.py
**Review score:** **7.5 cycle 1/3, NOT CERTIFIED** (min 8) — 0 critical, 2 important, both about evidence rather than behaviour
**Started:** 2026-10-28T12:30:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
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

## What this card owes the architect, and does not do itself

**AC-254 and AC-292 now state behaviour that is conditional**, and this card
does not edit the registry:

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

# CARD-339: The public player gains the "?" glyph — and the mark that drifted enters the guard that exists to stop drift

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** `card/339-the-public-player-gains-the-glyph`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-339
**Source:** CARD-323's round, 2026-11-01, which measured the divergence, refused to fix it (its own AC-4 makes re-declaring that rule a finding *against* it), and routed it to the owner. **The owner decided 2026-11-03: the public page gains the glyph.** The second half of this card is the orchestrator's, measured at the decompose station — see below.
**Idea:** —
**Wave:** 74
**Created wave:** 73
**Deferred waves:** 0
**Depends on:** CARD-323
**Touches:** player/player.css, tests/test_public_player_agreement.py, tests/test_public_player_maybe.py, docs/how-it-works/01-domain/puzzle-creation/README.md, docs/how-it-works/01-domain/puzzle-creation/11-the-public-player.md
<!-- The two docs files added 2026-11-03 from CARD-323's cycle 2: this card inherits obligations in both, and without them in Touches it would land leaving a finding described as open after it was closed. See 'What this card inherits'. --><!-- test_public_player_maybe.py is NOT optional: CARD-323's cell-look guard treats a `?` glyph as a defect to catch, so AC-1 cannot land without teaching it the new expected shape. See G-2. -->
**Review score:** —
**Started:** 2026-11-04T03:50Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The two players disagree about what a "Maybe" mark looks like. The admin draws a **"?" glyph**
in the accent token, on both the cell and the swatch:

- `src/nonogram/admin/static/admin.css`, rule `.player-cell[data-state="maybe"]::after` —
  `{ content: "?"; … color: var(--color-accent); }`
- `src/nonogram/admin/static/admin.css`, rule `.player-swatch[data-state="maybe"]::after` —
  `{ content: "?"; … color: var(--color-accent); }`

**Both line numbers this card shipped with had rotted by 8** (`:655` → `:663`, `:782` → `:790`,
verified at the decompose station 2026-11-03) and are **retired rather than refreshed**:
a `path:line` in a card is a carried figure with no control, and the rules resolve by name.
The same applies to the three `path:line` references below, all retired in this round.

The public page drew **a tint and no glyph** — rule `.player-cell[data-state="maybe"]` in
`player/player.css`, one background declaration, which CARD-323 matched on the swatch so the
brush button would stop previewing the wrong mark.

**The consequence is visible, not theoretical.** CARD-323's round measured the contrast and
the orchestrator confirmed it by opening the renders in
`~/Documents/nonogram-reviews/CARD-323/`: the **Maybe and Clear swatches are the same beige
square**, distinguishable only by which button happens to be selected, and on the board the
Maybe block is a tint barely separable from blank cells while "empty" carries a clearly
visible dot.

**Figures inherited from CARD-323's round, re-derived in this one (2026-11-04) from the token
hex in `meta/design/tokens.css` by WCAG 2.1 relative luminance. All three reproduce exactly,
so nothing is retracted under ADR-0039/R4:**

| pair | inherited | re-derived |
|---|---|---|
| maybe cell vs a blank cell (`--color-surface-hover` #f1ebdd vs `--grid-paper` #fffdf8) | 1.169 : 1 | **1.169 : 1** |
| maybe swatch vs the Clear swatch (#f1ebdd vs `--color-surface-sunken` #efe9dc) | 1.018 : 1 | **1.018 : 1** |
| the admin's "?" glyph on a cell (`--color-accent` #1f5f5b on #fffdf8) | 7.258 : 1 | **7.258 : 1** |

**And the figures the card could not carry, measured here because AC-4 is about the mark as
it now renders on *this* page:**

| pair | ratio |
|---|---|
| the "?" this card adds, on a public cell (#1f5f5b on the tint #f1ebdd) | **6.207 : 1** |
| the "?" this card adds, on the public Maybe swatch | **6.207 : 1** |
| the public Maybe swatch's "?" against the Clear swatch's paper (#1f5f5b on #efe9dc) | **6.099 : 1** |

So the mark goes from 1.169:1 (invisible) to 6.207:1 — past WCAG AA's 4.5:1, short of AAA's
7:1, which the admin's 7.258:1 clears. **The 1.051 shortfall is the tint, and it is the one
thing this round measured and deliberately did not decide** (see the judgment calls below).

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

## What this card inherits from CARD-323 — added 2026-11-03 from its cycle 2

CARD-323 measured this divergence, routed it, and recorded the hand-off **on its card and in
one assertion message**. Its cycle-2 review found the finding's **other carriers still describe
a state that is now superseded**, and they are yours to retract, because they only become false
when you land:

1. **`player/player.css`, the comment beside the `.player-swatch[data-state="maybe"]` rule** — it said the
   disagreement *"is a FINDING for the owner and not a worktree call"*. Once you add the glyph,
   the owner has decided and this card is the worktree call. Retract it where it stands.
2. **`docs/how-it-works/01-domain/puzzle-creation/11-the-public-player.md`, the "Marking" section** — described the
   public page as drawing *"a tint one step off the paper"* with the disagreement open. It
   becomes false on your merge, and **CARD-323 could not fix it**, because the state it
   describes was true then.
3. **`docs/how-it-works/01-domain/puzzle-creation/README.md`** — its file-table row for
   `player/player.css` reads **482**, and you change that file. CARD-323's round chose the
   policy for these rows, recorded for CARD-324..327: *a file-table line-count row for a file
   the card itself changed is updated in the card's own round; a bare `path:line` cross-reference
   in prose stays `/forge:explain`'s.* You are the first card to inherit it.

**Both docs files are now in `Touches` for exactly this reason.** Without them the card would
land correct code and leave three records saying the question is still open.

**One limit of that policy, measured by the same review and worth knowing before you apply it:
nothing reds when such a row goes stale.** It is an ungated convention, so the next card that
forgets reproduces the defect. The review named a third option neither CARD-323 nor this card
has taken — **retire the figure**, as `config.yml` did for the validator's warning count and
CLAUDE.md did for the duplicated component map (CARD-261). **If you find yourself updating that
row a second time, retire it instead and say so.**

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
  `check: {kind: test, ref: "tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark"}` — eleven arms: the rule is found once per sheet
  per hook, each side is held to its own property set (the anti-vacuity floor `DOT_PROPERTIES`
  already carries), the two declaration sets are compared per hook, the mark is asserted to be
  `"?"` in `var(--color-accent)` written out independently of either sheet, and the
  `--player-numeral-min` the cell glyph's `font-size` reads is compared as its own value
  because it lives in each stylesheet rather than in the byte-identically copied `tokens.css`.
  The shape is held from the other side by
  `tests/test_public_player_maybe.py::TestPublicMaybe_TheLookIsDeclaredOnce`.
- **AC-2** — Given the agreement guard, when the two sheets' Maybe looks are compared, then a
  divergence in either the cell look or the swatch look **reds**, demonstrated by planting
  one in each direction (public-only change, admin-only change).
  `check: {kind: test, ref: "tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_a_one_sided_change_to_the_maybe_mark_is_reported"}`
  — four parametrised cases, two per hook and one per direction, each planting on the real
  sheet text and asserting the plant appears as an **undeclared** disagreement (so a plant the
  exemption table absorbed would fail rather than pass as "something reddened"). The third
  direction equality cannot carry — a glyph *deleted* makes one side unreadable rather than
  unequal — is
  `tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_a_glyph_deleted_from_this_page_is_a_failure_and_not_an_absence`.
  Both plants were also run **on disk** in this round, with SHA-256 before and after restore;
  the measurement is in the round's report.
- **AC-3** — Given the compared surface, when it is enumerated, then the Maybe mark is in it,
  and every divergence that remains declared carries a reason and a measured residue.
  `check: {kind: test, ref: "tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_the_maybe_mark_is_a_fact_this_guard_compares"}`
  — asserts both Maybe facts and `numeral-floor.value` are in `compared_surface`, that neither
  is in `DECLARED_DIVERGENCES`, and that neither side of either is empty. The registry's own
  reason/residue arms are unchanged and still green:
  `tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared`.
- **AC-4** — Given the rendered public player, when the four marks are shown together, then
  the Maybe mark is distinguishable from both a blank cell and the Clear swatch — measured as
  a contrast figure, not asserted, and the figure recorded.
  `check: {kind: test, ref: "tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_the_paper_under_the_maybe_mark_is_a_routed_finding_and_not_an_exemption"}`
  — the arm that carries the figures, because the figures belong to the thing the glyph did
  **not** fix. The ratios are re-derived in the table above (all three inherited ones
  reproduce) and recorded in `SIBLING_FINDINGS`' `measured` fields, which
  `TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_every_routed_finding_carries_a_reason_and_a_measured_figure` holds to carrying a
  figure at all. The render G-4 asks for is
  `~/Documents/nonogram-reviews/CARD-339/`, with Chromium's own computed values beside the
  pictures in `computed.txt`.
- **AC-5** — Given the other three marks, when their coverage by the agreement guard is
    then it is reported, and any gap is either closed here or named with an owner.
  `check: {kind: review-lens}` — owner: whoever reviews this card. **Answered, and
  mechanised rather than only reported**: `tests/test_public_player_agreement.py`'s `mark_census` enumerates every state
  `solver_state.js` declares (the authority, ADR-0039/R2) against both hooks and both sheets,
  and `TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_every_census_fact_is_compared_routed_or_agreeing` requires every fact of it to
  be compared, agreeing, or **routed** in `SIBLING_FINDINGS` with a reason and a measured
  figure. Five facts are routed, none closed here — see "What this round decided" below.

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

## What this round decided, where the card left the call open

**Item 3 — `DECLARED_DIVERGENCES` gained NO entry.** That is the outcome the card named as the
better one and it is stated here rather than left implicit: the two Maybe glyphs agree
declaration for declaration on both hooks, so there is nothing to exempt, and the registry is
the same three entries CARD-328 shipped.

**The tint was measured and deliberately NOT decided.** The admin's Maybe cell carries no
background rule at all, so it draws the glyph on the board's paper where this page draws it on
`--color-surface-hover`. Three doors were open and the third was taken:

1. compare the whole look and **delete** the tint — rejected: it reverses CARD-323's one CSS
   line and changes a rendered pixel the owner did not ask to change. The owner's decision was
   that the page *gains* the glyph.
2. compare the whole look and **declare** the tint in `DECLARED_DIVERGENCES` — rejected under
   G-3: the reason would have been invented to make this card green, which is the defect this
   card exists to fix arriving one level up, and the card forbids exempting what the surface
   was widened to catch.
3. compare **the glyph** — which is what `compared_surface` already does for the Empty mark
   (`dot.declarations` is the `::after` and not the paper under it) — and route the tint as a
   **measured, undecided finding** that is pinned so it cannot change in either sheet
   unremarked. Taken, because this module's own standing rule is that two players disagreeing
   about a mark is a finding for the owner and deciding which side is right is not a worktree
   call. It is the rule CARD-323 followed to produce this card.

`SIBLING_FINDINGS` is that queue. It is **not** a second exemption table: its entries are facts
*outside* the compared surface, nothing is permitted by being in it, and an entry that stops
diverging reds as loudly as a new one.

**Item 4 — the other three marks. Reported, not taken.** The census says the compared surface
covers the Empty **cell** mark (the dot) and, from this card, both Maybe glyphs. Five facts
diverge and are routed, each with an owner named below:

| routed fact | what differs | measured |
|---|---|---|
| `.player-cell.maybe.paper` | the tint, under the glyph this card added | 1.169:1 tint vs a blank cell; the glyph reads 6.207:1 here against 7.258:1 in the admin |
| `.player-swatch.maybe.paper` | the swatch half of the same tint (CARD-323's line) | 1.018:1 against the Clear swatch |
| `.player-swatch.empty.glyph` | **the admin's White swatch previews the cell's dot; this page's draws nothing** | the dot is 6.144:1 on the swatch's paper; without it, White and Clear are two squares 1.19:1 apart |
| `.player-swatch.unknown.paper` | the Clear swatch is `--color-surface-sunken` here, `--grid-paper` in the admin | 1.19:1 |
| `.player-cell.filled.paper` | CARD-270's inset hairline, admin-only | 1 px of `box-shadow` in `--player-thin`, a token `admin.css` declares and no public asset is served |

**Owner for all five: the board owner, via this card's reviewer.** None is taken here, because
each is a rendered mark on a page the owner validates by looking, and the card's own
instruction is not to widen silently past the Maybe mark. **The strongest follow-up candidate
is `.player-swatch.empty.glyph`**: it is this card's defect one state over — a brush button
showing a plain square for a mark the board draws a dot for — and it is visible in this round's
render at `02-the-four-swatches.png`, beside the Maybe swatch that now works.

**The README line-count row: UPDATED, not retired.** The policy CARD-323 recorded says the
first card to change a file updates its row, and this is the first card to inherit it, so
following it as written is also the measurement the policy needs — the datum is now one, not
zero. `player/player.css` moved 482 → 521 and the row says so; its "Covers" text gained the
Maybe mark's "?". The retirement option stands for the **next** card that finds itself updating
it, exactly as the card instructs, and this round adds one piece of evidence for it: the row
was stale-by-construction the moment the edit landed and nothing would have reddened.

**Size datum, for calibration, in place of a wall-clock actual.** The clock measures the
queue rather than the work (owner's standing call), so no wall-clock figure is recorded and
its absence is deliberate rather than an omission. The derived datum: **six files, and the
whole rendered change is four lines of `player/player.css`** — the two `::after` rules lifted
from `admin.css`, `position: relative` on `.player-swatch` so the swatch glyph has a
containing block, and the `--player-numeral-min` the admin's `font-size` reads. Everything
else in the diff is the guard, the census and the records. That ratio is the card's own claim
— "the estimate is 0.5d and the glyph is one line of it" — measured rather than asserted.

## Notes

**Why this is not part of CARD-323.** That card's AC-4 makes re-declaring the Maybe rule a
finding against itself, so the round could not have fixed this without failing its own
acceptance criteria. It measured the divergence, refused to force it, and routed it — which
is the behaviour the board wants, and the reason this card exists rather than a silent edit.

**The estimate is 0.5d and the glyph is one line of it.** The cost is item 2: widening a
guard that compares declaration sets, in both directions, without weakening what it already
catches.

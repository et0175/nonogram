# CARD-339: The public player gains the "?" glyph — and the mark that drifted enters the guard that exists to stop drift

**Status:** done
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
**Review score:** 8.4 (cycle 2 of 3 — CERTIFIED)
**Started:** 2026-11-04T03:50Z
**Closed:** 2026-11-04T07:14Z
**Actual:** A **derived size datum**, not a clock reading. Landed on main: **6 files, 1520 insertions / 77 deletions** — `tests/test_public_player_agreement.py` **958/5**, `meta/kanban/cards/CARD-339.md` **293/17**, `tests/test_public_player_maybe.py` **157/35**, `player/player.css` **63/9**, `11-the-public-player.md` **48/10**, `README.md` **1/1** — with **30 tests added, 0 lost** and **0 lines of `src/`** (G-1). The sharper datum is the ratio the card claims for itself: of `player.css`'s 63 added lines, the **rendered-declaration delta is 4** — 298 → 302 declaration lines, derived by a comment-stripped line diff rather than by trusting the figure, and those four are exactly the two `::after` rules, `position: relative` and `--player-numeral-min`. So **1520 insertions buy four rendered lines**; the rest is the guard, the census and the records, which is the card's own thesis measured rather than asserted. **The wall-clock figure is excluded**, under the owner's standing ruling that wall-clock actuals are unusable for estimate calibration because the clock measures the **queue** rather than the work — this card's gate ran beside CARD-336 and main advanced four times during it (`02393431` → `95a93eb1` → `dde78f35` → `38ee04d0`), none of which is work done on this card. The size datum above substitutes for it, and this sentence is here so a reader **meets** the exclusion rather than noticing an omission. **Estimated 2c (0.5d) and certified on cycle 2 of a 3-cycle budget, so the cycle estimate was exact** — the **second exact cycle estimate on this board**, after CARD-278's 1c-on-cycle-1. The one duration recorded anywhere here is the suite's own wall-clock as pytest printed it (1476.98s), quoted as a gate fact; nothing in this card's code was timed.
**Merge commit:** `dd3488f9` — merged `--no-ff` onto `38ee04d0`, **two kanban-only commits past the `95a93eb1` the branch was rebased onto** (CARD-350..353 + `board.md`); neither touches `tests/`, `src/`, `player/` or this card's docs, and main's own collection is **unchanged at 10236** across them, so the gated tree's baseline is unaffected. Gated tree `070bd569`; merge-base `95a93eb1`. **Full suite on the frozen gated tree, `DATABASE_URL` armed, `-o addopts=` as two argv items and `-rEfs`, under the board's own lock held as this worktree (no pid — identity is the worktree): 10264 passed / 0 failed / 0 errors / 1 skipped / 1 xfailed, exit 0, 1476.98s.** **Not vacuous:** passed + skipped + xfailed = 10264 + 1 + 1 = **10266 = the collected count exactly**. **Skip attributed from `-rEfs`, not from memory — and the count is 1, not the 27 of unarmed gates:** the single skip is the `setrlimit(RLIMIT_AS)` platform gate in `tests/test_book_pdf_memory.py`. The bare-`DATABASE_URL` check fired **zero** times and the per-worktree `*_test` resolution gate fired **zero** times, which is the positive evidence that the arming took — the 26 tests that skip unarmed were **executed**. (27 is the *unarmed* baseline; arming and still seeing 26 bare-`DATABASE_URL` skips would have been the finding, and is not what happened.) **Neither DB hazard was live, checked before the run rather than diagnosed after:** the derived database `…_card_339_1816751863c4_test` already existed, so CARD-349's missing-**database** red could not fire, and its `alembic_version` was **018** against a latest migration of **018**, so the stale-schema missing-**column** red could not either. **Node-id delta, derived by whole-suite collection with `-o addopts=` on both sides: 10236 → 10266, 0 lost and 30 gained** — all 30 in the two touched modules (27 + 3), and the gained **set** is identical to an independent pre-rebase derivation and cross-checked against an `ast` walk of the modules' test functions (67 functions parametrizing to 83 arms), so two instruments agree on the set and not merely on the total. A pre-rebase collection showed **1 lost**, `tests/test_timeout.py::test_the_blind_set_is_derived_from_the_solvers_own_call_graph`; attributed with `git log -S` rather than guessed, it arrived on main with **CARD-278** (`13bae856`) after this branch's merge-base and is absent at `0ead085d` — never this card's loss, and 0 lost on the merged tree. **G-1 verified on the merged tree:** `git diff --name-only 38ee04d0 HEAD -- src/` empty and `git status --porcelain src/` clean, and `admin.css`'s SHA-256 equals main's blob, so every mutant the round, both reviewers and this gate planted into `src/` was restored byte-identically. **G-5 / ADR-0041/R2:** exactly **one served file** changed (`player/player.css`); no file added, deleted or renamed; the gate's own delta is **comment-only**, measured — comment-stripped `player.css` is byte-identical across all three branch commits (`58be7a883354eed1`) at raw 521 / 524 / 536 — and nothing added can carry a solution cell, the four declarations being a literal `"?"`, a positioning context and a font-size floor. **G-4:** the five files in `~/Documents/nonogram-reviews/CARD-339/` still correspond and were **not** re-rendered, which is a measurement and not an assumption — the gate's clause sits inside a `/* */` block and the comment-stripped stylesheet is byte-identical to the rendered commit's, so no pixel can have moved. No Chrome extension was used. **Card conflict resolved by taking main's metadata header and the branch's body, verified by diff rather than eyeballed:** both sides split at the first section heading (line 28, `## Why this card exists`), the resolved header byte-identical to main's and the resolved body byte-identical to the branch's, with the adopted header delta being `Status: in_progress` (**underscored** — the spaced form reds `test_no_declaration_outlives_the_cards_that_remove_it`), the quoted `Branch:` value, the `Worktree:` path and `Started:`. The rebase took **no conflict beyond that one file**, and the merge itself took none at all.
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
  figure. The census is **16 facts = 3 compared + 7 agreeing + 6 routed**; none of the six is
  closed here and every one is named with an owner — see "What this round decided" below.

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
   **measured, undecided finding**, pinned as *diverging* (and, for these two papers alone,
   by written-out values — see the retraction below, which is narrower than this line's first
   draft was). Taken, because this module's own standing rule is that two players disagreeing
   about a mark is a finding for the owner and deciding which side is right is not a worktree
   call. It is the rule CARD-323 followed to produce this card.

`SIBLING_FINDINGS` is that queue. It is **not** a second exemption table: its entries are facts
*outside* the compared surface, nothing is permitted by being in it, and an entry that stops
diverging reds as loudly as a new one.

**Retraction, cycle 1 F-3 — what "routed" pins, narrowly.** The first draft of this card and
of `RoutedFinding`'s docstring said the guard pins a routed fact so neither sheet can change it
unremarked. **That is false for four of the six**, and it was falsified by plant, not by
reading: change the admin's filled-swatch `border-color` to another token, or repaint the
public Clear swatch in `--grid-ink` — a rendered pixel — and each fact still *diverges*, so
`test_every_census_fact_is_compared_routed_or_agreeing` stays green. What is mechanised, and it
is real: **a routed fact is pinned as _diverging_, in both directions — its content is not
held.** A seventh fact that starts diverging reds as unclassified; a routed fact that stops
diverging reds as stale. Value-pinning exists only for the two Maybe papers, and only through
hand-written literals in
`test_the_paper_under_the_maybe_mark_is_a_routed_finding_and_not_an_exemption`.

**And the retraction itself needed narrowing, cycle 2 IMP-2 — by plant, which is the third
time in this card's history that a claim about what a guard holds survived reading and died on
a plant.** "The two Maybe papers" is two *facts* but **four fact-sides**, and only **three**
are pinned by value. The arm writes its two literals for `.player-cell.maybe.paper` alone, so
the cell's admin and public sides are both held. The *swatch*'s **public** side is held
transitively, by the arm's closing `census[cell][1] == census[swatch][1]` — CARD-323's claim
that the button previews the cell — so changing `player.css`'s Maybe-swatch background does
red. **The swatch's ADMIN side is held only to diverging from this page's.** `admin.css`
declares no background on its Maybe swatch, so that fact falls through to `.player-swatch`'s
`--grid-paper`; planting one there moves the census while **both** the Maybe-paper arm and the
classification arm stay green — and, measured at this gate, so does every one of the 83 arms in
the two touched test modules. The counter-plant (this page's swatch paper → `--color-surface-sunken`)
reds, through that equality. The fourth side joins the residue **CARD-346** owes. The
narrowing clause is written at five sites: the module docstring and the Maybe-paper arm's own
docstring in `tests/test_public_player_agreement.py`, `player/player.css`'s Maybe-swatch
comment (the worst-placed instance — it sits directly above the selector and said "a change
here reds", which is true of *that* line and false of its admin counterpart),
`11-the-public-player.md`, and this paragraph.

`DECLARED_DIVERGENCES` already carries the counterpart this table lacks — `RESIDUE_CONTROLS`,
which exists because **CARD-328's cycle-1 review raised it as IMP-1**, the same lesson one
registry over. **CARD-346 owes `SIBLING_FINDINGS` the derived residue**; this card owes the
retraction, which is the paragraph you are reading, and the matching ones in
`tests/test_public_player_agreement.py` (module docstring, `RoutedFinding`, the classification
arm and the Maybe-paper arm), `player/player.css` and `11-the-public-player.md`.

<!-- MIN-4, cycle 2, recorded here rather than by amending the commit (the board's standing
rule is never to --amend bare). The cycle-2 commit message (aed7802a) says the retraction is
made "in all five places the overclaim was written" and then lists SEVEN. It is wrong in both
halves, measured in the parent e8c90745: the overclaim — "pinned so it cannot change in either
sheet unremarked" — was WRITTEN in FOUR places (the module docstring, `RoutedFinding`, the
`player.css` comment and this card), and the RETRACTION LANDED in SEVEN, the three extra being
the classification arm, the Maybe-paper arm and `11-the-public-player.md`, none of which had
carried the overclaim. `11-the-public-player.md` carried no instance of it at all. The
enumeration above, written on the card, is the correct one; only the commit message's count and
its characterisation are wrong, and the message is immutable. -->

**Item 4 — the other three marks. Reported, not taken.** The census is **total at 16 facts**
(4 states x 2 hooks x {paper, glyph}) and splits **3 compared + 7 agreeing + 6 routed**.
Cycle 1's first draft of this section said "5 routed" and "8 agreeing" — wrong in two
cancelling terms, which is why the total still checked out (cycle-1 F-2), and one short of the
registry the code actually ships (F-1). Re-derived 2026-11-04 by calling `mark_census` on the
live sheets; the split below is that output, not a recount of the prose.

**Compared (3):** `.player-cell.empty.glyph` (the dot, `dot.declarations`),
`.player-cell.maybe.glyph` and `.player-swatch.maybe.glyph` (this card).

**Agreeing (7), named rather than counted** — three agree on a *value* and four on *neither
sheet drawing a glyph there*, which is a real answer and not an absence:

| agreeing fact | both sheets |
|---|---|
| `.player-cell.empty.paper` | `background: var(--grid-paper)` |
| `.player-cell.unknown.paper` | `background: var(--grid-paper)` |
| `.player-swatch.empty.paper` | `background: var(--grid-paper)` |
| `.player-cell.filled.glyph` | neither draws one |
| `.player-cell.unknown.glyph` | neither draws one |
| `.player-swatch.filled.glyph` | neither draws one |
| `.player-swatch.unknown.glyph` | neither draws one |

**Routed (6), each with an owner named below:**

| routed fact | what differs | measured |
|---|---|---|
| `.player-cell.maybe.paper` | the tint, under the glyph this card added | 1.169:1 tint vs a blank cell; the glyph reads 6.207:1 here against 7.258:1 in the admin |
| `.player-swatch.maybe.paper` | the swatch half of the same tint (CARD-323's line) | 1.018:1 against the Clear swatch |
| `.player-swatch.empty.glyph` | **the admin's White swatch previews the cell's dot; this page's draws nothing** | the dot is 6.144:1 on the swatch's paper; without it, White and Clear are two plain squares 1.19:1 apart — a hair **above** the 1.169:1 the owner already called indistinguishable, and in the same indistinguishable band as it |
| `.player-swatch.unknown.paper` | the Clear swatch is `--color-surface-sunken` here, `--grid-paper` in the admin | 1.19:1 |
| `.player-cell.filled.paper` | CARD-270's inset hairline, admin-only | 1 px of `box-shadow` in `--player-thin`, a token `admin.css` declares and no public asset is served |
| `.player-swatch.filled.paper` | the admin sinks the Black swatch's border into its fill (`border-color: var(--grid-ink)`); here the base `--color-border-strong` edge stays around the ink | one declaration: `border-color: var(--grid-ink)` present there, absent here, so the border stays #7f755f (3.9:1 on surface) around a #1c2333 fill |

**Owner for all six: the board owner, via this card's reviewer.** None is taken here, because
each is a rendered mark on a page the owner validates by looking, and the card's own
instruction is not to widen silently past the Maybe mark. **The strongest follow-up candidate
is `.player-swatch.empty.glyph`**: it is this card's defect one state over — a brush button
showing a plain square for a mark the board draws a dot for — and it is visible in this round's
render at `02-the-four-swatches.png`, beside the Maybe swatch that now works. **Cut as
CARD-348**, with both figures and the render confirmed in cycle-1 review.

**Three cards carry what this one names and does not take:** CARD-346 (the derived residue
control for `SIBLING_FINDINGS`), CARD-347 (retire the README line-count column, rename
`test_the_maybe_cell_look_is_one_rule_declaring_one_background`, and take `CARD-323.md` with
it), CARD-348 (the White swatch's dot). Nothing further is filed from this round.

**The README line-count row: UPDATED, not retired.** The policy CARD-323 recorded says the
first card to change a file updates its row, and this is the first card to inherit it, so
following it as written is also the measurement the policy needs — the datum is now one, not
zero. `player/player.css` went **482 → 521 → 524 → 536** across this card's three commits, and
the row now reads **536**, which is **the count at the merge commit this card closes on and at
no other moment** — stated that way deliberately, because the figure is dated and the row has
no control: the very next comment edit to the stylesheet re-stales it in silence. Its "Covers"
text gained the Maybe mark's "?". The retirement option stands for the **next** card that finds
itself updating it, exactly as the card instructs — and it is now **CARD-347's**, with four
pieces of evidence from this round rather than one:

1. the row was stale-by-construction the moment the edit landed, and nothing would have
   reddened;
2. the sibling convention for *prose* `path:line` refs, which the same policy assigns to
   `/forge:explain`, produced two freshly-widened false refs in a file this card had open
   (cycle-1 F-4) — fixed here by retiring them to names;
3. **and those two were already false on `main` before this branch existed**, measured in
   cycle 2 rather than relayed: `11-the-public-player.md` claimed the dot `::after` at
   `player.css:425` where `main` has it at `:446` (21 lines out) and the solved reveal at
   `:440` where `main` has `@keyframes player-solved-in` at `:470` (30 out). This card did not
   rot them; it widened a rot nothing reds on. An ungated convention does not decay at the
   moment someone edits the file — it is already decayed, and the edit only makes it visible.
4. **and the row re-staled inside this one card, twice, without any declaration changing**
   (cycle 2's IMP-1, and the gate's own re-derivation). Cycle 1 correctly wrote 521. Cycle 2
   then added three **comment** lines to `player/player.css` and did not revisit the row, so
   the row said 521 against 524 on disk — stale again, in the same card that had just updated
   it, with the file in its own `Touches`. The merge gate added twelve more comment lines
   writing IMP-2's narrowing clause and the count is now 536. That is the argument the column
   cannot survive: the figure counts **comments**, so it is falsified by edits that change no
   rendered pixel and no declaration — `player.css` with its comments stripped is byte-identical
   across all three commits, verified by SHA-256 at this gate — and nothing reds when it goes
   wrong. A card cannot keep it true for the length of its own review. **This is the data point
   the row's own argument landed on**, and it is CARD-347's strongest.

**Size datum, for calibration, in place of a wall-clock actual.** The clock measures the
queue rather than the work (owner's standing call), so no wall-clock figure is recorded and
its absence is deliberate rather than an omission. The derived datum: **six files, and the
whole rendered change is four lines of `player/player.css`** — the two `::after` rules lifted
from `admin.css`, `position: relative` on `.player-swatch` so the swatch glyph has a
containing block, and the `--player-numeral-min` the admin's `font-size` reads. Everything
else in the diff is the guard, the census and the records. That ratio is the card's own claim
— "the estimate is 0.5d and the glyph is one line of it" — measured rather than asserted.

## Worktree notes

<!-- MARKERS WRITTEN POST-HOC BY THE ORCHESTRATOR 2026-11-04, and the provenance matters.
     The retrospective derives `cycles_used` by counting EXACTLY the `[Review N/max] Score:`
     line, which cmd-review-cycle.md's SYNC POINT writes once per completed review cycle. This
     wave's reviews were dispatched DIRECTLY as agents rather than through that command, so no
     marker was ever written -- the same data-quality defect wave 73's retrospective reported,
     now in its second consecutive wave, and the reason that retro could export NO calibration
     signal at 0-of-3 cycle coverage.
     These lines are not fabricated: each cycle genuinely ran and its verdict is recorded twice
     over -- in this card's `Review score` field ("cycle N of 3") and in the untracked review
     YAML under meta/review/. The markers restate what those artefacts already say, in the one
     spelling the retro's extractor matches. A marker that drops the `/M` denominator does NOT
     match, which is why they are written in full. -->

[Review 1/3] Score: 7.5 — NOT certified; back to the round on four gating findings (F-1 the routed table one row short, F-2 the census arithmetic wrong in two cancelling terms, F-3 'routed' claiming to pin when it does not, F-4 two prose path:line refs). Review artefact: meta/review/CARD-339-cycle1.yml.

[Review 2/3] Score: 8.4 — CERTIFIED on cycle 2. Eight of cycle 1's nine findings verified closed, the ninth (F-5) unverifiable because no cycle-1 YAML existed at the time. 0 gating findings; six record corrections folded in at the merge gate. Review artefact: meta/review/CARD-339-cycle2.yml.


**Why the code is shaped this way, for whoever reads it next.**

**The glyph is written into `player.css` by a script that read `admin.css`, not by hand.** AC-1
asks for the admin's declarations "derived rather than retyped", and in CSS there is no import
to derive through — ADR-0041/R3 copies `solver_state.js` and `tokens.css` byte-identically and
nothing else, so the admin's rule is *the look this matches, not a file this one reads*. The
derivation therefore lives in two places: the rule bodies were lifted programmatically out of
`admin.css` at authoring time, and the standing derivation is the agreement guard, which parses
both sheets and holds the declaration sets to each other so neither can move alone.

**`--player-numeral-min` is in `player.css` because the derivation demanded it, not as a
nicety.** The admin's cell glyph reads `max(var(--player-numeral-min), calc(var(--player-cell)
* 0.6))`, and that token is declared in `admin.css`, *not* in the copied `tokens.css`. Copy the
declaration without the token and `max()` is invalid, `font-size` is invalid, and the glyph
renders at body size — a silent visual defect that every declaration-set comparison would call
agreement. Once each sheet declares its own copy, the two `font-size` strings can read equal
while rendering at different sizes, so the token's value is compared as its own fact
(`numeral-floor.value`). It never binds here: `--player-cell-min` is 28px, so 0.6 x cell never
falls under 16.8px. It is carried because the *declaration* is what agrees.

**`position: relative` on `.player-swatch` is load-bearing, not tidying.** The swatch glyph is
`position: absolute; inset: 0`, matching the admin's; without a positioned ancestor it resolves
against the initial containing block and the "?" lands in the page's top-left corner. The
admin's own `.player-swatch` carries `position: relative` for exactly this reason.

**Why the Maybe *glyph* is compared and the Maybe *paper* is not.** This is the one judgement
call in the round and it looks arbitrary until you see the precedent: `compared_surface` has
always treated the Empty mark as its `::after` alone (`dot.declarations`), never the paper
under it — the public sheet writes `.player-cell[data-state="empty"] { background: … }` and the
admin writes no such rule at all. The Maybe mark follows that precedent exactly. The paper that
is left over genuinely diverges, nobody has decided it, and this module's own standing rule is
that deciding which side is right is not a worktree call. So it is routed, not exempted and not
silently dropped. See the retraction above for what routing does and does not pin.

**Why `cell_states()` is reimplemented here rather than imported.**
`tests/test_public_player_maybe.py` already reads `CELL_STATES`, but that module imports this
one's CSS parser, so importing its reader back would be a cycle. Thirteen lines of regex is the
trade CLAUDE.md's `mask_runs` precedent names.

**Why the plants live in memory.** Every permanent control substitutes on text read from disk
and never writes to `src/` — G-1 is structural here, not a promise. The on-disk plants in the
round's report were one-off measurements, restored from captured content and SHA-256 verified.

**The cascade a planted divergence causes, so a future gate reader does not misread it.** Any
live undeclared divergence also reds the six pre-existing
`test_real_drift_inside_a_declared_divergence_is_reported[…]` cells and
`test_a_fourth_divergence_in_the_compared_surface_is_reported`, because those arms assert the
key-level table *still absorbs* their own plant. That is designed — the guard's own failure
message says to read `test_the_disagreements_are_exactly_the_declared_ones` first — and it is
not collateral damage.

## Notes

**Why this is not part of CARD-323.** That card's AC-4 makes re-declaring the Maybe rule a
finding against itself, so the round could not have fixed this without failing its own
acceptance criteria. It measured the divergence, refused to force it, and routed it — which
is the behaviour the board wants, and the reason this card exists rather than a silent edit.

**The estimate is 0.5d and the glyph is one line of it.** The cost is item 2: widening a
guard that compares declaration sets, in both directions, without weakening what it already
catches.

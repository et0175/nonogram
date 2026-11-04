# CARD-348: The White brush previews a plain square where the board draws a dot — this card's own defect, one state over

**Status:** done
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
**Review score:** 9.0 (cycle 1/3 — CERTIFIED)
**Started:** 2026-11-04T14:14Z
**Closed:** 2026-11-04T18:25Z
**Actual:** 1c — ratio **1.000 (exact)**, certified cycle 1. Sized by derived datum, **wall-clock excluded** per the owner's standing ruling that the clock measures the queue rather than the work: this card sat behind a concurrent review that held the full-suite lock, so elapsed time here is queue, not effort. Datum: 2 files, +522/−36 (`player/player.css` +18/−0 — one rule line and 17 comment lines; `tests/test_public_player_agreement.py` +504/−36); **+12 test arms, 62 → 74**; census movement 1 key across 3 tables.
**Merge commit:** `9971257a`
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

## Worktree notes

[Review 1/3] Score: 9.0 — **CERTIFIED** (threshold 8.0). 0 Critical, 2 Important (1 discharged by the reviewer itself), 3 Minor, 1 Nit. Artefact: `meta/review/CARD-348-cycle1.yml`. Merge-base `c021a10f`; `git diff --stat c021a10f main` empty for all three touched paths, so no rebase exposure. Diff 2 files, +522/−36; arm count **62 → 74** verified by `--collect-only` on both sides.

**Written by the orchestrator — this card had no `## Worktree notes` section and the review's sync point wrote no marker.** Second occurrence in this wave, CARD-363 being the first, which is direct evidence for CARD-363's premise. Estimate **1c, certified on cycle 1 — ratio 1.000, exact.**

[Review 1/3] Every quantitative claim the round made **reproduced exactly** when independently re-measured: the 18/17 plant reds, plant C's 32, all six WCAG contrast figures (15.444 / 13.209 / 12.978 / 1.190 / 1.169 / 1.018, dot-on-White-paper 6.144, re-derived by an independent WCAG 2.1 implementation under `python -I` with no import of the module), the containing-block hole, and the SHA-256 pairs on both sheets.

[Review 1/3] **The orchestrator's station reading was the over-reading, and the round was right.** Resolved by *enclosing test* rather than by file: the only pre-card cell naming `.player-swatch.empty.glyph` outside `SIBLING_FINDINGS` sits inside `test_the_census_is_not_vacuous`, whose assertion is bare dict membership and says nothing about routing — routing was held solely by `diverging == set(SIBLING_FINDINGS)`. So the anti-vacuity line survives the move unchanged and still correct. See [[attribute-by-test-not-by-file]].

[Review 1/3] **The `position: relative` arm is the only DIAGNOSTIC detector, not the only detector.** Widened across all seven player-CSS test files: planted **18 failed / 243 passed (595s)** against an unplanted control of **261 passed / 0 failed (115s)**. The 17 e2e arms that red are all `Page.click: Timeout 30000ms exceeded` from **CARD-339's Maybe glyph** intercepting pointer events — they name nothing about the containing block. The new arm costs 0.4s instead of ten minutes of opaque timeouts. "No control" should read "no control that names the cause."

[Review 1/3] Cascade attribution verified: subtracting the new class's own reds (5 under plant A, 4 under B) both plants land on exactly **13**, and it is the **same** 13 arms — so the cascade did not change and the delta above the predicted 8–16 band is this card's own new arms.

[Review 1/3] **F-3 discharged by the reviewer, not deferred.** It ran the full pass the finding owed, on `01731bf5` itself, unarmed: **10280 passed / 0 failed / 27 skipped / 1 xfailed** in 1502.59s. Skips read off `-rEfs` rather than recalled — 26 `tests/conftest.py:207` (bare `DATABASE_URL`) + 1 `tests/test_book_pdf_memory.py:1297` (`setrlimit`) = 27, exactly the measured **unarmed** expectation. Lock acquired at 15:21:24Z and released; neither override env var touched. **So the merge gate owes no full suite.**

[Review 1/3] ADR-0041/R2 verified by grep over every `dataset`/`setAttribute` write under `player/`: `play.js` writes a *swatch's* state in exactly one place (`play.js:442`, the player's chosen brush); lines 357/375 write `.player-cell` state, not swatch state; no `setAttribute("data-state", …)` anywhere under `player/`. The load-bearing half holds.

[Review 1/3] Three non-gating follow-ups carded: **CARD-371** (the new WCAG helper has no reference anchor — a third unanchored implementation in this tree), **CARD-372** (one plant anchor over-fires: `calc(var(--player-cell) * 0.6)` occurs twice in `admin.css` under a bare `css.replace()`; pre-existing CARD-339 debt), **CARD-373** (AC-4's six-pair table is durable only inside a failure message a green run never prints).

[Review 1/3] The round's lock disclosure is now **CARD-370**, re-cut on the measured mechanism: the lock is mandatory on refusal and purely advisory on acquisition. CARD-348's reviewer acquired correctly; CARD-363's did not acquire at all.

## AC → test mapping

Applied on main from the merge gate's report; the branch carried nothing under `meta/` (INV-023
verified clean). All node ids in `tests/test_public_player_agreement.py`.

| AC | test |
|---|---|
| **AC-1** | `TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_two_swatch_dot_declaration_sets_are_equal` |
| | *floors, which are not the test:* `::test_the_admin_sheet_declares_the_swatch_dots_properties`, `::test_the_public_sheet_declares_the_swatch_dots_properties`, `::test_the_mark_both_swatches_draw_is_a_round_dot_in_the_secondary_ink`, `::test_the_swatch_dot_is_declared_once_in_each_sheet` |
| **AC-2** | `::test_a_one_sided_change_to_the_swatch_dot_is_reported[the admin swatch dot is drawn as a square]` and `[the public swatch dot is drawn in the board's ink]`; plus `::test_a_swatch_dot_deleted_from_this_page_is_a_failure_and_not_an_absence` |
| **AC-3** | `TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_every_census_fact_is_compared_routed_or_agreeing`, with `::test_no_mark_is_both_compared_and_routed` holding disjointness and `TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_white_mark_is_a_fact_this_guard_compares` |
| **AC-4** | `TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_four_brush_buttons_are_mutually_distinguishable` |
| **AC-5** | review-lens, but **held by an assertion**: `TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_white_mark_is_a_fact_this_guard_compares` |
| *implementation item 3 — containing block* | `TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_swatch_is_the_containing_block_both_marks_resolve_against` |
| *the defect statement itself, intra-sheet* | `TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_brush_button_previews_the_mark_the_board_draws` |

## Merge gate

**MERGED `9971257a`** (first parent `24bbb741`, second `01731bf5`), verified a real two-parent merge
commit with the branch tip an ancestor of main. Staged `--no-ff --no-commit`, suite run, then
committed — so the tree the suite ran on (`61dac57a`) is byte-for-byte the tree committed.

**Suite: 10306 passed / 0 failed / 0 errors / 1 skipped / 1 xfailed** in 1586.47s, `-o addopts=
-rEfs -q`, `PYTHONDONTWRITEBYTECODE=1`, **`DATABASE_URL` ARMED.** The 1 skip is
`tests/test_book_pdf_memory.py:1297` (`setrlimit` refused by this kernel). **Zero
bare-`DATABASE_URL` skips, which is how the arming is known to have taken** — a 27 here would have
been the finding, not the baseline. Cross-checks the reviewer's unarmed pass exactly:
`10280 + 26 = 10306` and `27 − 26 = 1`. Those 26 database tests had never run on this card's tree
before the gate.

**The gate corrected its own stated reason rather than quietly fixing it.** Its lock's `why` claimed
main's movement reached the check-ref search domain through `meta/kanban/dispatcher.state`. The
factual half was range-dependent — the orchestrator's nine-file `.md`-only figure is right for the
last two commits, and `dispatcher.state` genuinely moved over the gate's five-commit range — but the
**exposure** half was asserted unmeasured and measures **false both ways**: `IGNORED_YET_TRACKED` is
**exactly 488 and unmoved** with `meta/kanban/` contributing 0 (the `.md` files are doubly
ineligible, stripped by `EXCLUDED_SUFFIX` before `check-ignore` and not ignored anyway), and the
added lines carry no `test_<name>` token and no `::` node id, with a control proving the search was
not dead. **Corrected reason: a conservative precaution with no identified exposure — plus the one
reason that stands alone, that no suite had ever run on the merge result**, which is the direct
discharge of IMP-1/F-3, this card's own disclosed defect.

**The stale-schema trap was armed and waiting, and the gate pre-empted it** rather than diagnosing a
red: the per-worktree test database sat at `017` against a head of `018`
(`018_book_player_domain.py`), so it migrated before arming. The next gate to arm without checking
would have taken a red in a book/player DB module on a card touching only CSS — and been trained to
re-run instead of look.

**Self-disclosed:** one `--collect-only` (collection only, no execution) ran in the same worktree
during the suite. It cannot move a result, but it was a second pytest under the gate's own lock and
should have been deferred.

# CARD-323: The public player gains the Maybe brush — the fourth mark whose look already ships

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** `card/323-the-public-player-gains-the-maybe-brush`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-323
**Source:** owner request 2026-10-30 — "the player misses a lot of the player from the admin player: e.g. no maybe brush, no hints etc... I'd like both to reuse the same functionality", raised against a locally assembled site at `http://localhost:8081/play/00d5d88065`. The orchestrator measured the gap before carding it; this is the cheapest of the five cards it produced, and the only one whose styling already exists.
**Idea:** —
**Wave:** 73 <!-- STAMPED 2026-10-31 at dispatch, opening wave 73. Wave 73, on the owner's "and some player card also". Chosen from five mutually-exclusive player cards -- all five touch player/play.js, play.html and player.css, so only one can run -- and chosen as the SMALLEST because its round establishes the house style the other four inherit. PREMISE VERIFIED AT DISPATCH: player/player.css:411 already carries .player-cell[data-state="maybe"] and player/play.js contains the string `maybe` ZERO times, so the look ships and the behaviour does not, exactly as the card claims. -->
**Created wave:** 69
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/play.js, player/play.html, player/player.css, tests/test_public_player_maybe.py, tests/test_public_player.py, docs/how-it-works/01-domain/puzzle-creation/11-the-public-player.md, docs/how-it-works/01-domain/puzzle-creation/README.md <!-- the last three added in round 1: the EC-050 walk reds on an unwalked control, and the two docs carry three-brush sentences this card makes false -->
**Review score:** —
**Started:** 2026-10-31T12:18:26+00:00
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists, and why it is this small

`MAYBE` is **already one of the four members of `CELL_STATES`** in
`solver_state.js`, which ADR-0041/R3 requires the public site to serve as a
**byte-identical copy** of the admin player's module — so the public page is
already shipping every transition the fourth mark needs. Measured 2026-10-30:
`clickedState` and `clickStroke` handle `MAYBE` with no special case, and
`player/player.css` **already carries its look**, as the one rule
`.player-cell[data-state="maybe"] { background: var(--color-surface-hover); }`
(at `:411` when this card was cut — **locate it by the selector, not by the line**:
that file gained 45 lines from an out-of-pipeline commit within half an hour of
this card being written, and a bare line number is the figure CARD-281 exists
because of).

What excludes it is **one line and one button**: `player/play.js`'s `TOOLS`
constant is `[FILLED, EMPTY, UNKNOWN]`, and its comment states the reason —
*"MAYBE ("?") is the admin player's fourth and is not offered here, so a cell
reachable from this page is one of these three (CARD-283, 'three cell states')"*.

**That is a scope decision, not a constraint.** Unlike the error count, the
progress percent and Check — which take `solution` and are therefore
unreachable from a page that by design never has the answer — the Maybe brush
needs nothing the page does not already have. The owner's 2026-10-30 decision
reverses the scope choice and leaves the three answer-dependent features out.

## What to implement

1. `player/play.js`: add `MAYBE` to the `TOOLS` array, imported from
   `/solver_state.js` alongside the three already there. **The order is the
   DOM's** (the constant's own comment says so), so place it where the button
   sits — the admin's order is filled, empty, maybe, unknown
   (`puzzle_solve.html:257-260`), and matching it is the point of the card.
2. `player/play.html`: a fourth `data-player-tool="maybe"` radio in
   `.player-tools`, built exactly like its three siblings — `role="radio"`,
   `aria-checked="false"`, and a `.player-swatch` carrying the state so the
   swatch inherits the look the stylesheet already defines.
3. `player/player.css`: **only if a swatch rule is genuinely missing.** The
   cell look exists; check whether `.player-swatch[data-state="maybe"]`
   resolves through the same rule before adding anything. **A rule that
   duplicates one already there is a finding against this card**, not a
   deliverable — the whole premise is that the look already ships.

## Acceptance criteria

- **AC-1** (the brush marks): *Given* the public player with the Maybe brush
  chosen, *when* a cell is clicked, *then* that cell carries
  `data-state="maybe"` and the recorded history holds one stroke whose state is
  the module's `MAYBE`. (test: `TestPublicMaybe_TheBrushMarksACell`)
- **AC-2** (four tools, in the admin's order): *Given* the page, *then*
  `.player-tools` holds exactly four `data-player-tool` buttons and their DOM
  order is `filled, empty, maybe, unknown` — **the same sequence as the admin
  player's menu**, asserted against that template's order rather than against a
  list spelled twice. (test: `TestPublicMaybe_FourToolsInTheAdminsOrder`)
- **AC-3** (the radio group still behaves): *Given* four tools, *then* exactly
  one carries `aria-checked="true"` at any time, and choosing Maybe unchecks
  the previous tool. (test: `TestPublicMaybe_OneToolIsCheckedAtATime`)
- **AC-4** (the look is not re-declared): *Given* the stylesheet, *then* the
  maybe cell's appearance is defined in **exactly one place** and that place is
  the rule that existed before this card — a per-rule check, not a grep for the
  word. (test: `TestPublicMaybe_TheLookIsDeclaredOnce`)
- **AC-5** (the save round-trips a maybe): *Given* a board with maybe marks,
  *when* the page is reloaded, *then* those cells come back as
  `data-state="maybe"` — the public save is `play.js`'s own, so this is the
  arm that proves the fourth state survives it. (test:
  `TestPublicMaybe_AReloadRestoresMaybeMarks`)

## Guardrails

- **G-1: do not edit `solver_state.js` or `tokens.css`.** Both are
  byte-identical build-time copies (ADR-0041/R3); `player/assemble.py`'s
  `COPIED_FROM_ADMIN` table checks the equality at assembly time **and** from
  the test tree. An edit here is caught, but by the wrong gate and late.
- **G-2: no solution reaches the page.** `puzzle/<key>.json` carries clues and
  extent only (measured 2026-10-30: `clues`, `width`, `height`, `key`, `tier`).
  This card adds no field to it (ADR-0041/R2, CARD-283 G-4).
- **G-3: the three existing brushes are untouched** — their values, their DOM
  attributes and their tests stay as they are.
- **G-4: styling from tokens only** — `var(--color-*)`, never a literal.
- **G-5: no test deleted, renamed, skipped or merged**, `parametrize` ids
  included (gate: node-id set difference with `-o addopts=''`).
- **G-6: do not touch `src/nonogram/admin/**`.** CARD-268 is editing the admin
  player's static files in a sibling worktree; this card's whole footprint is
  under `player/` precisely so the two cannot collide.

## System contract

- ADR-0041/R2 — no public asset carries a solution grid or data from which any solution cell is recoverable (check: CARD-282's and CARD-283's guards)
- ADR-0041/R3 — the board-state module and the design tokens are reused by byte-identical build-time copy, never edited (check: `player/assemble.py`'s `COPIED_FROM_ADMIN`, plus its test-tree half)
- ADR-0041/R4 / CON-021 — play state persists only in this browser's localStorage, per puzzle; nothing server-side (check: review-lens)
- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check: review-lens)
- ADR-0038/R2 — no network request per mark (check: `tests/test_public_player.py::test_no_write_request_for_any_interaction`) <!-- round 1 named the admin test's "public-side equivalent", which is not a resolvable ref: the validator resolves a check ref by TEXT search for the whole path::name string, so a prose paraphrase reads as a dead ref however green the test is. The real public-side test is the one now named; this card extends it with brush-maybe and it is green in the 249-test impact scope. -->
- ADR-0038/R8 — a browser test refuses LOUDLY when Chromium is absent, never skips green (check: CARD-160's fixtures, imported by `tests/test_public_player.py`)

## Architecture context

- **FR:** FR-045 (the public player)
- **ADR:** ADR-0041/R1-R4, ADR-0038/R1-R2, R8
- **Components:** COMP-011
- **Trace:** `meta/architecture/trace.yml` — not updated by this card (a scope reversal inside a shipped FR, like the player features before it; the owner decision goes through `inputs/raw-requirements.md` on the architect side, and the ACs above are the card-local statement the gate holds onto — quick-card rule)

## Design context

- **Design system:** `build/site/tokens.css` is the byte-identical copy of `src/nonogram/admin/static/tokens.css`; `player/player.css` is the public player's own sheet and every value in it is a token (G-4).
- **UI components:** `.player-tools` gains a fourth `.player-tool-item`; `.player-cell[data-state="maybe"]` already exists.
- **Screens:** `/play/<key>`.
- **Standards:** real buttons with accessible names, `role="radio"` + `aria-checked` as the three siblings already do; the owner validates the look on a real puzzle render before merge.

## [Re-verified 2026-10-30 15:15] `main` moved under this card, and every premise was re-measured

**Another session committed to the public player, directly on `main`, outside the
card pipeline**, within half an hour of these five cards being cut:

- `2400501b` *"player: the white mark is a dot and solving is revealed, matching the
  panel"* — `player/play.js` **+3**, `player/player.css` **+57/−12**,
  `tests/test_public_player.py` **+143**, `tests/test_public_player_pages.py` **+9**.
  That is this card's exact footprint.
- `7ec579e4` and `7d34892e` — docs only (`docs/deploy/player.md`,
  `docs/how-it-works/**`), no code.

**Every measured premise in this card was re-derived afterwards and all of them
still hold** (15:15, against `7a2cfdf1`):

| premise | at cutting | now |
|---|---|---|
| `TOOLS = [FILLED, EMPTY, UNKNOWN]` | yes, `play.js` | yes, `play.js:83` |
| `.player-cell[data-state="maybe"]` styled | yes | yes, one rule |
| `player.css` zoom rules | 0 | **0** |
| `player.css` circle rules | 0 | **0** |
| `player.css` crosshair rules | 0 | **0** |
| `play.js`'s false hint comment present | yes | **yes**, verbatim |
| `play.js` length | 576 | **579** |

**What changed that a dispatching agent must know:** that commit brought a sixth
feature over by hand — the white mark as a dot, and a solved sweep whose
per-cell delay `play.js` now sets as `--player-wave`, *"as solver.js sets it for
the admin player"*. So the public player is being closed toward the admin
player's feature set **from two directions at once**: these cards, and
direct-to-`main` commits. **Re-measure this card's figures at dispatch rather
than trusting the table above** — it is a record of one moment, and the moment
had already moved once.

## Worktree notes

- **[Serialization, not dependency]** This card and CARD-324, CARD-325,
  CARD-326 and CARD-327 all touch `player/play.js`, `player/play.html` and
  `player/player.css`, so their predicted overlap is **1.0** and the
  dispatcher's conflict graph will serialize any two of them in one wave.
  That is deliberately **not** written as a `Depends on` edge: none of them
  needs another's output, and a sequencing preference written as a dependency
  pollutes the graph the dispatcher reasons over (the board's own rule, stated
  on CARD-220's `Wave:` field). Run them in any order.
- **[Smallest first]** This is the cheapest of the five and the only one whose
  styling already exists, so it is the natural first slot — it proves the
  public player's test harness and the four-tool DOM before the larger cards
  build on them.

## [Round 1, 2026-11-01] What shipped, the pattern it sets, and the one finding

**The premise held, re-measured at this worktree's base `f407c350`**:
`player/player.css` carried `.player-cell[data-state="maybe"]` (one rule), and
`player/play.js` contained the string `maybe` **zero** times. `main` moved to
`7c987f67` during the round and touched none of this card's files
(`git diff --stat f407c350..main` over `player/`, the two test modules and the
two docs is empty).

**The pattern this round sets for CARD-324..327**, since all five are one JS
feature plus one test module over the same three files:

1. **One test module per card**, named for the feature
   (`tests/test_public_player_maybe.py`), **importing the harness** —
   `bundle` / `site` / `host` and the `_open` / `_tap` / `_state` helpers —
   from `tests/test_public_player.py` by name, which is the mechanism that
   file already uses for CARD-160's browser fixtures. No second server, so
   every card measures the site the assembler really builds, and ADR-0038/R8's
   loud refusal comes along for free rather than being re-implemented per card.
2. **One class per AC**, named exactly as the card's AC names it
   (`TestPublicMaybe_<claim>`), so a check ref resolves to a class and
   "attribute by test, not by file" is answerable without reading the module.
3. **Two tiers, split on what a browser adds.** A claim about *files* (the
   markup's order, the stylesheet's rules) is a tree test; a claim about *the
   running page* (the mark, the radio group, the reload) is a browser test.
   The tree tier is where the cheap, total, mutation-controlled checks live.
4. **The authority for a shared fact is the other side's file**, never a list
   spelled twice: the tool order is read from `templates/puzzle_solve.html`,
   the state values from `solver_state.js`'s own `export const` lines, the
   corpus floor from the page's own tool count. **Amended by fix round 1 —
   read the amended wording in the Fix round 1 section below, not this one:
   the declaration also has to exist on the WRITTEN side, and the reader has
   to fail with a named message.**
5. **Every tree-tier claim ships its mutant table** — the same reading
   function run over planted text, asserted to report the plant.
6. **The EC-050 walk in `tests/test_public_player.py` must be extended** by any
   card that adds a control. It is derived from `play.html` and reds on three
   assertions at once otherwise; that is a feature, and it fired on this card.

**The one finding, measured and NOT fixed here (out of this card's AC-4):**
the two players disagree about what a "?" looks like. `admin.css` draws a "?"
glyph in the accent token on both the cell and the swatch; `player.css` draws a
tint and no glyph. Contrast, computed from `tokens.css`:

| pair | ratio |
|---|---|
| maybe cell vs a blank cell | **1.169:1** |
| maybe swatch vs the Clear swatch | **1.018:1** |
| the admin's "?" glyph on a cell | 7.258:1 |

So the shipped mark is very nearly invisible and the Maybe brush button is very
nearly the Clear button — visible in `~/Documents/nonogram-reviews/CARD-323/`.
AC-4 pins the cell's look to the one pre-existing rule and makes re-declaring
it a finding against this card, so this round did not touch it; the
`test_public_player_agreement.py` docstring says a disagreement between the two
players is "a finding for the owner" and not a worktree call. **The fix is one
line** — the pre-existing cell rule's value — and the swatch follows it
automatically, because `TestPublicMaybe_TheLookIsDeclaredOnce` asserts the two
declarations are **equal** rather than asserting each separately.

**Where that finding actually went — corrected 2026-11-03, because the round's
own commit overstated it.** Commit `95f3a2c3`'s subject says the disagreement
was *"carded as a measurement"*. **When it was written that was false**: there
was no backlog entry and no card file, and the finding's only carriers were
this section, the comment block at `player/player.css:147-164` and one sentence
in `docs/.../11-the-public-player.md`. Cycle 1 measured that and was right to
raise it. What is true, and true only by a **later** act outside this worktree:

- the finding was **measured and routed here**, which is the part the round did
  do and which was the right call for a card whose AC-4 makes re-declaring that
  rule a finding against *itself*;
- **the owner decided on 2026-11-03**: the public player gains the "?" glyph,
  the admin keeps what it has;
- **the decision is carried by CARD-339**, cut and committed on `main` — *"The
  public player gains the '?' glyph — and the mark that drifted enters the
  guard that exists to stop drift"*, `Depends on: CARD-323`, `Touches:
  player/player.css, tests/test_public_player_agreement.py,
  tests/test_public_player_maybe.py`.

So the claim is true today and was not true when it was made; this paragraph,
not the commit subject, is this card's record of it.

**Also outside `Touches` and necessarily edited:**
`tests/test_public_player.py` (the EC-050 walk, see 6 above) and two
`docs/how-it-works/01-domain/puzzle-creation/` files, whose "three brushes"
sentences this card makes false. The card's `Touches` was incomplete, not wrong.

## [Fix round 1, 2026-11-03] Cycle 1 scored 6.5 — what was mechanised, what was owned elsewhere

Cycle 1: three Important, two Minor, **no Critical and no blocker**; its own
summary was *"the feature itself is correct, well tested, and `src/` is
untouched. Every finding is in the evidence and the disposition, not the
behaviour."* `main` was `382a8ac1` when this round ran.

### F-001 — the save's "closed set" was a self-comparison, and is now closed

`test_the_save_gains_no_field_for_the_fourth_brush` compared the key sets of
**two outputs of the same `serialize()` call**, so a field added
*unconditionally* appeared on both sides and every equality still held. Cycle 1
measured it: `fingerprint: payload.key.length` planted into `serialize()`'s
object literal survived at **218 passed, 0 failed**. The docstring's claim —
*"A new field — a fingerprint, a hint count, anything — reds, whatever its
value"* — was therefore **false**: it red only for a field added *conditionally
on the brush*.

The save is now held to a **literal** key set, the way the served
`puzzle/<key>.json` half of the same class already was, with the differential
kept as the **second** arm (it is what proves the literal was matched against
two real saves rather than one save read twice):

```python
_SAVE_FIELDS = ["columns", "done", "height", "key", "rows", "undone", "v", "width"]
_STROKE_FIELDS = ["cells", "state"]
```

**Derived, not pasted — and the difference mattered.** Cycle 1's suggested
literal was `["columns","done","height","key","rows","undone","v"]`, **seven
keys**. `serialize()` returns **eight**: `v, key, width, height, rows, columns,
done, undone` (`player/play.js:216-223`). Pasting the review's list would have
red the test on `width` on the first run. The literals are deliberately *not*
read back out of `play.js` either: the thing under test **is** `serialize`, and
a set derived from it grows with it, which is precisely how the first version
came to pass against the plant.

**The mutant re-fired, and it now reds** (`PYTHONDONTWRITEBYTECODE=1`,
`__pycache__` swept both ends, plant by text with occurrence asserted `== 1`,
SHA-256 `fce02577…` before the plant and after the restore, **MATCH**):

```
>  assert sorted(save) == _SAVE_FIELDS, (tool, sorted(save))
E  AssertionError: ('maybe', ['columns', 'done', 'fingerprint', 'height', 'key', 'rows', ...])
   1 failed
```

The docstring now states the two arms and says which one is the closure — and
records that the differential arm alone is **not** one.

### F-002 / F-003 — one root cause (RC-1), now owned by CARD-339

Both findings said the same thing: the contrast divergence was parked without
being owned. It is owned now, by an act outside this worktree, and the
correction to this card's own record is in the Round 1 section above. The
remaining half is F-003's registry entry:

- the divergence is **absent from `DECLARED_DIVERGENCES`**, and round 1 cited
  that module's docstring as authority to defer *without using its mechanism*;
- **CARD-339 owns the registry entry.** Its `Touches` names
  `tests/test_public_player_agreement.py`, its AC-2 requires a planted
  divergence to red in both directions, and its AC-3 requires the Maybe mark to
  be **in** the compared surface with every remaining declared divergence
  carrying a reason and a measured residue. So the reviewer's *"it must be
  assigned, not left unowned"* is satisfied by a **named owner**, not a promise;
- and the shape of the defect, measured independently at this round:
  `tests/test_public_player_agreement.py` contains the string `maybe`
  **zero times**. The mark was never in the compared surface, so it did **not**
  diverge *past* a guard — it diverged **where no guard was looking**. CARD-339
  says exactly this, and nothing on this card contradicts it. The registry entry
  may well end up unnecessary (if nothing must legitimately differ once the
  glyph lands, the better outcome is no entry at all) — which is CARD-339's AC-3
  to settle, not this card's.

`tests/test_public_player_agreement.py` is outside this card's `Touches` and
editing it here would be the wrong card doing CARD-339's first task.

### F-004 — pattern point 4, split because half of it collides with G-6

Point 4 (*"the authority for a shared fact is the other side's file"*) is right
for `solver_state.js`, which ADR-0041/R3 already makes a byte-identical copy.
It was **under-built for the admin template**: `admin_tool_order()` does a
brace-free HTML slice, and cycle 1 measured three admin-side changes giving
three different outcomes — a **reorder** reds informatively, a **wrapper div**
truncates the slice and fires the floor with a named cause (genuinely
default-deny), and a **class rename** gave a bare `ValueError: substring not
found` with no diagnosis. Over four modules each re-reading that template, one
rename yields four uninformative failures at once.

**(ii) The reader is hardened here.** `str.index` is replaced by `str.find`
plus a named assertion per failure mode, and `_ADMIN_MENU_HOOK` names the one
string whose disappearance makes this module's authority unreadable. Proven by
planting the rename `player-tool-menu` → `player-brush-menu` in the admin
template (SHA-256 `8e8b3a24…` before and after the restore, **MATCH**; `git
status` clean of `src/`, so **G-6 holds** — a plant that is measured and
restored is a measurement, not an edit):

```
E  AssertionError: 'class="player-tool-menu"' is not in puzzle_solve.html: the admin
   brush menu's class was renamed or moved, so the authority this module reads the tool
   order from is gone. Re-point _ADMIN_MENU_HOOK at the block carrying the
   data-player-tool buttons (the public player's test modules read it; this is not a
   defect in the admin page).
```

**(i) Declaring the coupling on the written side is NOT done here — it touches
`src/nonogram/admin/**` and G-6 forbids it. It is an obligation for CARD-324's
brief**, and it is the amended pattern point, which supersedes point 4 above for
CARD-324..327:

> **4 (amended).** The authority for a shared fact is the other side's file,
> never a list spelled twice — **and a shared fact read from the other side's
> file must be declared on the written side and read through a reader that fails
> with a named message.** Reading side only is half a declaration: the person who
> renames the class is on the written side, and today sees none of the three
> records (`templates/puzzle_solve.html` carries no note that the public
> player's tests read it, `player/assemble.py`'s `COPIED_FROM_ADMIN` — the one
> declared channel between the two trees — does not list it, and this card
> deliberately does not update `trace.yml`). CARD-324 owes the written-side
> declaration: a comment at the `.player-tool-menu` block naming the public-player
> test modules that read it, or a non-copying entry beside `COPIED_FROM_ADMIN`.

### F-005 — one policy for line-count rows, applied to all three

Round 1 updated the `play.js` row of
`docs/how-it-works/01-domain/puzzle-creation/README.md` (579 → 590) and left two
rows of the **same table** stale for files this card changed, while the commit
message said bare line numbers are *"left alone, `/forge:explain` owns them"* —
so the stated policy covered all three rows and the opposite policy was applied
to one.

**The policy, chosen and recorded for CARD-324..327: a file-table line-count row
for a file the card itself changed is updated in the card's own round; a bare
`path:line` cross-reference in prose is left to `/forge:explain`.** The
alternative (revert `play.js` to 579 and leave all three) buys consistency by
writing a number that is known to be false, which is the worse of the two. So:

| row | was | now | actual |
|---|---|---|---|
| `player/play.js` | 590 | 590 | 590 ✓ (round 1, already right) |
| `player/player.css` | 461 | **482** | 482 ✓ |
| `player/play.html` · `library.html` · `book.html` | 100 · 95 · 99 | **102** · 95 · 99 | 102 · 95 · 99 ✓ |

### F-006 — the corpus floor moved above its consumer

`_MIN_DRAWS_PER_TOOL` now sits above `TestPublicMaybe_OneToolIsCheckedAtATime`,
beside the module's other shared constants (`_TOOL_ATTR`, `_ADMIN_MENU_HOOK`,
`_MAYBE_ATTR`, `_MAYBE_IN_PAGE`), which all already precede their consumers.

### The lesson for CARD-324..327: an AC that a near-invisible control satisfies

Cycle 1's sharpest structural point, and it is **not** a defect in the
implementation: **this card passes AC-1 as written while shipping a control a
user cannot distinguish from the adjacent one.** AC-1's *then* is about
`data-state="maybe"` and the recorded history and says **nothing about
perceptibility**; the Maybe swatch measures 1.018:1 against the Clear swatch.
The implementation did what the AC asked. The defect is **in the AC**.

> **A card delivering a visible control owes a perceptibility clause** — an AC
> whose *then* says the control can be told apart from its neighbours, measured
> as a figure rather than asserted. CARD-339's AC-4 is the first instance of it
> on this board ("distinguishable from both a blank cell and the Clear swatch —
> measured as a contrast figure, not asserted, and the figure recorded"), and
> CARD-324..327 each ship a visible control and each owe one.

**Also fixed, not a finding:** a future card that gives the cell a `::after`
glyph without the swatch would have red in
`test_the_swatch_previews_the_cell_with_the_cells_own_value` as a bare
declarations-dict mismatch — desired behaviour, unreadable message. **CARD-339
is exactly that card**, so the assertion now says what it means ("the swatch
stopped previewing the cell…") and names CARD-339's AC-1 as the thing the reader
should look at.

### Measurement, this round

- impact scope, the six modules unchanged from cycle 1:
  `pytest -o addopts='' -rfs tests/test_public_player.py tests/test_public_player_maybe.py tests/test_public_player_agreement.py tests/test_public_player_pages.py tests/test_player_bundle.py tests/test_browser_fixture_scope.py`
  → **249 passed, 0 failed, 0 skipped** (asserted: `-rfs` as **one** flag, and
  the browser tests really ran — 0 skipped is the assertion, not a side note);
- the frozen-registry family `tests/test_suite_profile.py` → **450 passed, 0
  failed, 0 skipped**, re-derived rather than carried over;
- no file under `src/` is modified (`git status` clean of `src/` after both
  plants were restored at matching SHA-256).

## [Merge gate, 2026-11-03] Cycle 2 scored 8.5 — the three Minors dispositioned

Cycle 2: **three Minor, no Important, no Critical, no blocker**; certified at
**8.5** (6.5 → 8.5, one fix round). This section is the gate round's record of
all three, including the one that is **not** this card's to fix.

### N-001 — the guard that reds hardest now says what it is (closed here)

`test_the_maybe_cell_look_is_one_rule_declaring_one_background` reddened as a
bare list mismatch while its sibling two lines below already carried a message
naming CARD-339's AC-1. It is the guard CARD-339's AC-1 trips **first and on
both assertions** (`maybe_rules` counts a `::after` rather than filtering it, so
the glyph lands in `cell_rules` and `cell_declarations` at once), so it is the
output the receiving engineer sees first. Both assertions now share one named
`handoff` message, and the test gained the docstring it never had.

**Measured, not asserted.** CARD-339's AC-1 planted as
`.player-cell[data-state="maybe"]::after { content: "?"; color: var(--color-accent); }`
appended to `player/player.css` (`PYTHONDONTWRITEBYTECODE=1`; SHA-256
`774c1768…` before the plant and after the restore, **MATCH**, so this was a
measurement and not an edit):

```
E  AssertionError: the maybe cell's look is decided in more than one place. If the second
   place is a "?" glyph as an ::after on .player-cell[data-state="maybe"], this is
   CARD-339's AC-1 landing and this message is the one it will read: teach this test the
   new expected shape — and the swatch its matching half — rather than dropping the
   assertion. Anything else is the re-declaration AC-4 makes a finding against CARD-323.
   Read as cell rules ['.player-cell[data-state="maybe"]',
   '.player-cell[data-state="maybe"]::after'].
```

**The second half: the mutant whose name outlived what it catches.** The
`MUTANTS` entry `"a ? glyph as an ::after"` stays **green** across CARD-339 —
once the sheet legitimately carries a glyph rule, the plant appends a *second*
one and the report still differs — so from that merge the name describes a shape
that is no longer a defect while the plant goes on testing something real. It is
renamed to **`"an extra cell rule, as an ::after"`**, which is the arithmetic the
plant actually exercises and is true on both sides of CARD-339, and the `MUTANTS`
comment now records why the name is shape-neutral.

**This is a rename of a parametrize id, and G-5 forbids renaming a test,
`parametrize` ids included. Stated plainly rather than buried:** the module
collects **18** node ids before and after (`-o addopts='' --collect-only -q`),
the plant and its reading are untouched, and the only change is the label —
`…::test_the_reading_reports_each_planted_defect[a ? glyph as an ::after]` →
`…[an extra cell rule, as an ::after]`. No frozen registry enumerates this
module's test names (`tests/test_suite_profile.py` does not mention it), and
against `main` nothing is lost, because the whole module is new on this branch.
G-5 exists to stop a card quietly shedding coverage; the coverage here is
identical and the rename was ordered by the review that raised N-001. **It is
still an exception to the guardrail's letter and is recorded as one**, not as a
no-op.

### N-002 — not this card's to fix; the disposition verified, and no third carrier

Cycle 2 found two of F-002's three carriers still describing the divergence as an
open owner question. **This card cannot truthfully retract either**: both
sentences become false only **when CARD-339 lands**, and until then they
describe the state that actually ships.

Verified against `main`'s copy of CARD-339 at this gate, not taken on trust:

- its **`Touches` names both docs files** —
  `docs/how-it-works/01-domain/puzzle-creation/README.md` and
  `…/11-the-public-player.md` — added 2026-11-03 "from CARD-323's cycle 2", with
  `tests/test_public_player_maybe.py` named as not optional;
- its **"What this card inherits from CARD-323"** section names all three
  obligations at the line: `player/player.css:162` (the "FINDING for the owner"
  comment), `…/11-the-public-player.md:119` (the "tint one step off the paper"
  sentence with the disagreement open), and the README's `player/player.css`
  row at **482**.

So the hand-off is **real and sufficient**: an owner, a named line per carrier,
and both files inside the receiving card's footprint.

**The third-carrier search came back empty**, which was the one thing this gate
could add. A case-insensitive sweep of the branch tree for *finding for the
owner* / *open finding* / *finding from CARD-323* / *not a closed divergence* /
*not a worktree call* returns, outside the two named carriers and the review
YAMLs, only:

- `tests/test_public_player_agreement.py:76-78` — the **standing policy** that a
  disagreement is the owner's call, not a claim about this divergence;
- `CARD-328.md:190`, `CARD-322.md:715` — the same standing policy, quoted by
  other cards;
- `CARD-323.md:238` — this card's own round-1 sentence, which quotes that policy
  to explain why round 1 did not touch the rule, and which the corrected
  paragraph below it already supersedes.

`docs/.../README.md` carries no divergence sentence at all (its only stake is the
line-count row, which is N-003's subject).

### N-003 — the F-005 policy's two unstated limits, recorded to agree with CARD-339

The policy stands as written in F-005 above — *a file-table line-count row for a
file the card itself changed is updated in the card's own round; a bare
`path:line` cross-reference in prose stays `/forge:explain`'s*. Two limits it did
not state, recorded here in the **same terms CARD-339 already carries** rather
than in new ones:

- **(a) Nothing reds when such a row goes stale.** It is an **ungated
  convention** — no mechanical check anywhere — so the next card that forgets
  reproduces F-005 exactly. The policy buys consistency by discipline only.
- **(c) There was a third option, and neither card took it: retire the figure.**
  The board's own remedy for a number that moves on every merge is to stop
  carrying it — `meta/kanban/config.yml` did exactly that for the validator's
  warning count, and `CLAUDE.md` did it for the duplicated component map
  (CARD-261). A `Lines` column in a docs file-table is the same class of number.
  **CARD-339 carries the instruction**: if it finds itself updating that row a
  second time, it retires the column instead and says so.

Cycle 2's limit **(b)** — that the policy created an obligation the receiving
card was not carrying — **is closed by fact, not by promise**: CARD-339 changes
`player/player.css`, so the `482` written this round is wrong at its merge, and
`docs/how-it-works/01-domain/puzzle-creation/README.md` **is now in CARD-339's
`Touches`** with the inherited row named explicitly as item 3 of its "What this
card inherits" section. Verified at this gate.

# CARD-270: Filled cells merge across the heavy fifth rules — ink-on-ink hides the cell divisions

**Status:** in_progress
**Priority:** P2
**Category:** ops
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/270-fifth-rule-divisions
**Worktree:** ../PythonProject4-card-270
**Source:** quick — owner bug report 2026-10-22: "Regions around wider lines (5x cell number) don't have gray cell divisions around black cells"; no handoff increment
**Idea:** —
**Wave:** 54
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/tokens.css, tests/test_puzzle_solver_fifth_rule.py, tests/test_admin_design_tokens.py
**Review score:** — (implementation landed `4f41bbb4`; cycle 1 running)
**Started:** 2026-10-22T17:20:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The defect, with its mechanism verified in the code

**Symptom (owner).** Around the heavier every-fifth rules, runs of black cells
show no gray cell divisions — adjacent filled cells merge into one blob, so
the player cannot count cells exactly where the heavy rule exists to help them
count.

**Mechanism.** A filled cell's background and the heavy rules are the same
token:

- `.player-cell[data-state="filled"] { background: var(--grid-ink); }`
  (`admin.css:575`)
- the heavy rules are `var(--player-rule-major) solid var(--grid-ink)` — on
  `.major-right`/`.major-below` (every fifth line, assigned in `solver.js`
  `drawBoard` at `:557-558`), on the board's outer edges
  (`admin.css:530-531`), and on the clue-gutter edges
  (`.player-clue.is-col`/`.is-row`, `admin.css:525-527`).

The *thin* dividers are `var(--player-thin)` (gray), so between two filled
cells across an ordinary border the division reads. Wherever the divider is a
major rule, it is ink on ink: invisible between filled cells. The defect class
is **any ink-colored rule adjacent to an ink-colored fill** — the fifth lines
the owner reported, and equally the outer border and the gutter edges when the
run of filled cells touches them.

## What to implement

Make the cell division between filled cells legible across every major rule,
without weakening the major rules against paper. Recommended mechanism, to be
confirmed by the owner on a render:

1. **An inner hairline on filled cells** — an inset `box-shadow` (or inset
   outline) of `var(--player-thin)` at `var(--player-rule)` width on
   `.player-cell[data-state="filled"]`, so every filled cell carries its own
   visible boundary and divisions read uniformly: across thin rules, major
   rules, the outer border and the gutter edges, with no neighbor-dependent
   CSS. `.is-hinted`'s inset box-shadow is the in-file precedent for drawing
   inside a cell without moving layout.
2. Alternatives to show beside it only if the hairline disappoints on the
   render: a filled-cell ink one step off the rule ink (two tokens instead of
   one), or neighbor-conditional borders via `:has()` (rejected by default:
   per-segment rules, and it dims the major rule itself between filled
   cells).
3. Whatever mechanism wins: values from tokens only, no layout shift (the
   cell's box must not change size), and the solved-flash animation and
   `prefers-reduced-motion` behaviour unchanged.

This is a stylesheet card: no JS change, no state change, no template change
expected. If the chosen mechanism turns out to need one, that is a finding to
surface, not to absorb silently.

## Acceptance criteria

- **AC-1** (happy): *Given* a board with two adjacent filled cells on either
  side of a fifth-line major rule (both axes), *then* the two cells are
  visually separated — the mechanism's marker (e.g. the inset hairline) is
  asserted present on filled cells, and a pixel sample across the shared edge
  of the rendered board finds a non-ink band between the two ink fills.
  (test: `TestSolverFifthRule_FilledCellsDivideAcrossMajorRules`)
- **AC-2** (edge, board edges): *Given* filled cells touching the board's
  outer border and the clue-gutter edge, *then* the division between fill and
  rule reads the same way there. (test:
  `TestSolverFifthRule_EdgesAndGuttersToo`)
- **AC-3** (edge, nothing else moves): *Given* the fix, *then* cell geometry
  is unchanged (same `--player-cell` sizes, no layout shift measured on a
  drawn board), the major rules against paper are exactly as before, and the
  empty-dot and "?" marks are untouched. (test:
  `TestSolverFifthRule_GeometryAndOtherMarksUnchanged`)
- **AC-4** (edge, tokens + motion): *Given* the shipped stylesheet, *then*
  every new value comes from tokens with a per-rule check, and
  `prefers-reduced-motion` still disables all board animation. (tests:
  `test_the_filled_cell_division_comes_from_tokens`,
  `TestSolverHint_ReducedMotion` unedited)

## Guardrails

- G-1: Player CSS only — no change under `src/nonogram/export/**` or to the
  book/print pipeline; the CON-019 byte-identity tripwires run unedited.
- G-2: Hand-written CSS, tokens only (ADR-0038/R1; test:
  `test_the_stylesheet_uses_tokens_not_literals`).
- G-3: No JS or state change: `solver.js` and `solver_state.js` are not
  edited; `data-state` values and all existing player tests run unedited.
- G-4: The owner sees a rendered board (a real puzzle with filled runs
  crossing fifth lines, edges and gutters) before merge and picks between the
  hairline and any alternative — a green suite does not close this card
  (standing practice: visual changes get an eyeball).

## System contract

- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check:
  review-lens)
- ADR-0038/R4 — state logic is a pure module, separate from rendering; this
  card touches rendering only (check: review-lens)
- CON-021 — interactive play only in the admin panel's player (check:
  review-lens)

## Architecture context

- **FR:** FR-044 (the player's board rendering; the every-fifth heavy rule is
  CARD-212/CARD-193-era rendering behaviour).
- **ADR:** ADR-0038/R1, R4.
- **CON:** CON-015/CON-016, CON-021.
- **Components:** COMP-009 (admin panel: static CSS).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Design context

- **Design system:** `static/tokens.css` + `static/admin.css`; the fix adds at
  most one token (the hairline) — reuse `--player-thin`/`--player-rule` where
  they already say the right thing.
- **UI components:** `.player-cell[data-state="filled"]` only.
- **Screens:** `/puzzles/<id>/solve` (and the editor's board, which shares the
  stylesheet — check it on the render too).
- **Standards:** no layout shift; both the division and the major rule must
  survive at the phone cell sizes (14 px cells — a hairline that rounds to
  0 px there is a miss, state what it measures at 14 px).

## Named tests resolved before the card started (drafting, 2026-10-22)

**Already exist** (run them, do not rewrite them):

| name | resolves to |
|------|-------------|
| `test_the_stylesheet_uses_tokens_not_literals` | `tests/test_admin_design_tokens.py:219` |
| `TestSolverHint_ReducedMotion` | `tests/test_puzzle_solver_hint.py:886` |

**To be written by this card** (in `tests/test_puzzle_solver_fifth_rule.py`,
new file, except the token check, which joins
`tests/test_admin_design_tokens.py`) — none exists yet; report them as
written, never as passing before they exist:
`TestSolverFifthRule_FilledCellsDivideAcrossMajorRules`,
`TestSolverFifthRule_EdgesAndGuttersToo`,
`TestSolverFifthRule_GeometryAndOtherMarksUnchanged`,
`test_the_filled_cell_division_comes_from_tokens`.

## Worktree notes

- **[Pixel assertion honesty]** AC-1's pixel sample must state its domain: a
  screenshot at a declared viewport and zoom, sampling a declared edge —
  not a general claim about every rendering. The mechanism assertion is the
  regression net; the pixel sample is the one check that the mechanism
  actually produces a visible band.
- **[Conflict note]** Touches overlap CARD-267/268/269 on `admin.css` and
  `tokens.css`; the dispatcher serializes same-wave overlaps. This card has
  no JS footprint, so it composes with any of them in either order.

### Implementation (2026-10-22)

- **Shipped mechanism — one declaration, no new token.** `admin.css:589` is
  now `.player-cell[data-state="filled"] { background: var(--grid-ink);
  box-shadow: inset 0 0 0 var(--player-rule) var(--player-thin); }`.
  `tokens.css` is **untouched** — `--player-thin` and `--player-rule` already
  said the right thing, so the card added no token after all.
- **Measured (re-derived against the shipped file; Chromium, dpr 1, zoom
  100 %).** Desktop 1440x900, 20x20 board: cell **24.88 CSS px**. Phone
  390x844: cell **14.39 CSS px**. The hairline renders as **1 device px at
  both** — it does NOT round to 0 at the phone cell size, which is the number
  the card asked for explicitly. Between two filled cells the scanline reads
  thin 1 / ink 2 / thin 1 across a fifth-line major rule (the rule's ink core
  is untouched) and 3 contiguous thin px across an ordinary rule.
- **Honest bound, for the owner's eye.** Between two *filled* cells a major
  rule now reads as a 4 px band with a 2 px dark core, against a 3 px all-grey
  band for an ordinary rule. The heavy rule is still distinguishable there,
  but by its core rather than by contrast — less emphatic than against paper,
  where nothing changed at all. If the fifth lines should stay as loud
  *inside* a black region, the card's alternative (a filled-cell ink one step
  off the rule ink) is the lever.
- **A new FILE in the browser family, and the registries that costs.**
  `tests/test_puzzle_solver_fifth_rule.py` is the thirteenth
  `tests/test_puzzle_solver_*.py` file and the first whole file any card has
  added since CARD-217 measured the family, so CARD-235's guards had to be fed
  on purpose: a `PAGE_ISOLATION` entry (`test_puzzle_solver_page.py`),
  thirteen `ADDED_SINCE_BEFORE` entries and one `ALONE_PROBES` entry
  (`test_browser_fixture_scope.py`). Two guards also changed shape, and both
  changes are narrowings rather than waivers:
  - `test_the_twelve_files_are_still_twelve` carried a hand-written `== 12`
    beside the registry it also checks. It is now
    `test_the_family_on_disk_is_the_family_the_registry_names` and derives the
    count from `PAGE_ISOLATION` — the lesson CARD-213's `assert len(ids) ==
    422` already taught one class up in the same file.
  - `test_the_record_reaches_every_file_in_the_family` required every family
    file to appear in CARD-235's out-of-band alone-record. A file added later
    cannot, and backdating a record is not a thing this board does, so it now
    requires the record **or** an `ALONE_PROBES` entry that really runs one of
    the file's tests alone. "Added later" is derived from the measured
    artefact, not hard-coded, so a file that drops out of the record still
    fails.
- **No JS, no state, no export.** `git diff --name-only` names neither
  `solver.js` nor `solver_state.js` nor anything under `src/nonogram/export/`;
  the CON-019 tripwires ran unedited and green.
- **Renders for G-4** (desktop and 390 px, before and after, full board plus a
  6x crop of the corner through the first fifth rules):
  `/Users/omelnikova/Documents/nonogram-reviews/CARD-270/`.


---

### [Implementation landed] `4f41bbb4` — one CSS declaration, and `tokens.css` was not needed at all

Verified by the orchestrator rather than taken on report: `git diff --numstat main...HEAD` is five files —
`admin.css` (+15/−1), `tests/test_puzzle_solver_fifth_rule.py` (new, 745), `test_admin_design_tokens.py`
(+78), `test_browser_fixture_scope.py` (+150/−5), `test_puzzle_solver_page.py` (+6). **G-1 and G-3 hold
structurally:** `git diff --name-only main...HEAD` names no `solver.js`, no `solver_state.js` and nothing
under `src/nonogram/export/`.

The fix is one declaration added to the **existing** filled-cell rule (not a new rule after it — `.is-hinted`
has equal specificity and has to stay later in the file to keep winning):

```css
.player-cell[data-state="filled"] { background: var(--grid-ink); box-shadow: inset 0 0 0 var(--player-rule) var(--player-thin); }
```

The card budgeted "at most one new token"; the answer was **zero** — `--player-thin` and `--player-rule`
already said the right thing, so `tokens.css` is untouched.

**The phone number the card asked for, answered:** the hairline is **1 device px at both 1440×900 (24.88 px
cells) and 390×844 (14.39 px cells)** — it does **not** round to 0 at the phone size. Across a fifth-line
major rule the band reads thin 1 / ink 2 / thin 1; across an ordinary rule, 3 contiguous thin px. Domain
stated: Chromium, dpr 1, zoom 100 %, `--player-zoom` 1, 20×20 board, one named scanline between two cell
centres, PIL over a `scale="css"` screenshot.

**Gate:** `make test-impact` → **2813 passed, 11 skipped, 0 failed**, exit 0, lock redirected to
`/tmp/card270-impl.lock` throughout, full suite never run. Beyond the impact set, because G-1/G-3 demand
it: the other eleven `test_puzzle_solver_*.py` files + `test_puzzle_editor_ui.py` → **491 passed unedited**;
the CON-019 tripwires → **66 passed, unedited**, and neither appears in the diff.

**Owner's render is on disk — 16 PNGs in `~/Documents/nonogram-reviews/CARD-270/`**, before/after ×
desktop/phone × all-filled/mixed, each with a 6× magnified crop through the first two fifth rules on both
axes. The orchestrator looked at `before-desktop-mixed-crop6x.png` against
`after-desktop-mixed-crop6x.png`: before, the filled region is one blob with no divisions; after, it reads
as distinct cells. **The fix does what the owner asked for.**

### [Open for the owner, and the implementer was right to raise it]

Inside a **black** region the fifth rule now reads as a 4 px band with a 2 px dark core against a 3 px
all-grey band for an ordinary rule — so it is distinguishable **by its core rather than by contrast**, and
on the render it is genuinely harder to pick out there than it is against paper, where nothing changed.
Before this card it was not distinguishable inside a black region *at all* (there were no divisions), so
this is strictly better and not a regression. But if the fifth lines must stay equally loud **inside** a
filled region, the lever is the card's own alternative: a filled-cell ink one step off the rule ink, i.e.
two tokens where there is now one. That is an owner's-taste call on a real render, not a defect, and it is
deliberately **not** being fixed on spec.

### [Flagged by the implementer as a judgement call — review must rule on it]

`tests/test_puzzle_solver_fifth_rule.py` is the **thirteenth** file in the browser family and the first
whole file added since CARD-235 measured it, so three CARD-235 guards red on it by design. They were **fed**
(a `PAGE_ISOLATION` entry, thirteen `ADDED_SINCE_BEFORE` entries each with card + reason, one `ALONE_PROBES`
entry) rather than loosened — but two guards also changed **shape**, and the implementer reads G-3 ("existing
player tests run unedited") as covering the player tests' assertions, not the fixture-scope registries that
exist to be updated when the family changes. The player tests did run unedited (491 passed). **Review owns
this call**, and both shape changes are narrowings to check on their merits:
`test_the_twelve_files_are_still_twelve` had a hand-written `== 12` beside the registry it also checks (the
CARD-213 snapshot anti-pattern) and now derives the count; `test_the_record_reaches_every_file_in_the_family`
demanded every family file appear in an out-of-band record a later file cannot be in, and now accepts the
record **or** an `ALONE_PROBES` entry, with "postdates the record" derived from the artefact so a file that
drops out still fails.

### [Two findings the kill instrument produced against the implementer's own work]

Both acted on rather than reported: `test_the_hairline_takes_no_part_in_layout` originally compared the board
against itself with `box-shadow: none` forced, and the MOVES-LAYOUT mutant **survived it** — forcing
`box-shadow: none` cannot undo a `min-width`, so the mutation sat in both readings and the arm was narrative.
It now measures every cell against the px `--player-cell` resolves to, which MOVES-LAYOUT kills, and the old
comparison is kept as a second arm whose docstring **says that arm alone would be narrative and names the
mutant that survives it**. And under the hairline-removing mutants, one test's in-test control arms report
NOT-REACHED because the test dies on an `IndexError` at an earlier arm — recorded rather than papered over.

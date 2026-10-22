# CARD-270: Filled cells merge across the heavy fifth rules — ink-on-ink hides the cell divisions

**Status:** review
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
**Review score:** 9.7 (cycle 2/3) ✓
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

- [Review 1/3] Score: 8.4 — crit: 0, imp: 1 (F-001), minor: 3. Verdict: DOES NOT PASS (severity gate).
- [Review sync] 1 report → meta/review/ (20261022T190000Z-CARD-270-cycle1.yml)
- [Adversarial] F-001 CONFIRMED — not by a skeptic agent but by the report's own executed evidence: two
  non-no-op mutants (REACHES-BLANK, BROADEN-UNKNOWN), each run in both recording and reraising passes,
  :622 PASS under both while :637/:691 red — execution-grade confirmation; a refutation pass over the
  same executions would re-run them verbatim.
- [AC/EC check] All criteria/constraints ✓ (evidence): AC-1..AC-4 demonstrated by fresh named-test runs
  (exit 0 each; AC-4's token test includes a 7-way broken-value control); no EC section exists on this card.
  G-1 demonstrated (structural file-list check + CON-019 tripwires, 66 tests, exit 0, both files absent from
  the diff); G-2 demonstrated (token guard green, diff to it purely additive); G-3 demonstrated (JS absent
  from diff; all twelve pre-existing player test files green together; bounded to the named family).
  G-4: render half demonstrated — 16 before/after PNGs at ~/Documents/nonogram-reviews/CARD-270/ (desktop +
  phone, full board + 6x corner crops); the owner's pick between the hairline and the louder-fifth-rule
  alternative deliberately happens POST-MERGE per the owner's standing instruction (merge on gates; the
  eyeball follows on the rendered pages). Not a violated guardrail — the alternative stays available as a
  follow-up lever and both reviews record it OPEN.
- [Review 2/3] Score: 9.7 — crit: 0, imp: 0, minor: 2 (narrative-grade) ✓ threshold reached + no critical/important.
  All four cycle-1 findings re-derived as resolved (F-001 confirmed-by-execution: both broadening mutants
  red the renumbered arm in both passes). Step 8h: 3 rules checked, 3 ✓ holds. Mutation certification
  (cost-deferred) ran this cycle: 4 mutants / 5 matrix runs, all figures re-derived, restores hash-verified.
  Fix commit fc035f7d (made by the prior session's lingering agent — same liveness pattern as CARD-262,
  disclosed; content verified by this cycle's review).
- [Review sync] 1 report → meta/review/ (20261022T175719Z-CARD-270-cycle2.yml)
- [8h spot-check] 3/3 sampled holds reproduced (inline re-derivation from disk: diff file list names no
  solver.js/solver_state.js/pyproject.toml/export files; .player-cell confined to admin player assets;
  uncommitted set is card bookkeeping only)
- [Fix 1] complete (recovered: previous attempt's uncommitted work verified correct and kept in full;
  a still-live background stash/pop cycle from the prior session round-tripped the edits byte-identically,
  sha256-verified). FIXED F-001 (test: TestSolverFifthRule_GeometryAndOtherMarksUnchanged), F-002
  (TestSolverFifthRule_FilledCellsDivideAcrossMajorRules), F-003 (TestBrowserFixtures_NoTestAddedOrRemoved);
  SKIPPED F-004 — out of declared scope, carded as CARD-275 (verified to exist, ready). Declarations: 3
  updated (docs + registry reasons), 0 none. Kill matrix: 50 ast.Assert nodes (assert-node domain),
  REACHES-BLANK and BROADEN-UNKNOWN now red the renumbered gating arm (:729) in both recording and
  reraising passes; NO-HAIRLINE and BLANK-GONE deletion mutants red their mechanisms' arms.
- [Fix 1] declarations: 3 updated, 0 confirmed, 0 none
- [Build gate] PASSED (impact: hand-selected 3 files — test_puzzle_solver_fifth_rule.py,
  test_browser_fixture_scope.py, test_puzzle_solver_page.py; pytest exit 0, 0 FAILED/ERROR lines;
  full suite deferred to the merge gate per board convention)
- [Run resume 2026-10-22] session interrupted mid-fix: worktree carries an uncommitted partial fix
  (+294/−64 over the two test files). Fix agent restarted with recovery context.

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


---

### [Review 1/3] 8.4 — the CSS is right; the one gating finding is a tautological assert in the tests

Report: `meta/review/20261022T190000Z-CARD-270-cycle1.yml` (25 keys, `yaml.safe_load` verified).
Arithmetic: `10 − 1.0 (F-001 Important) − 0.3 (F-002) − 0.2 (F-003) − 0.1 (F-004) = 8.4`.
Zero Critical. The numeric gate is cleared; the **one Important** is what holds the card.

**`src/nonogram/admin/static/admin.css` needs no change.** The reviewer's verdict in its own words: the
fix is *"correct, minimal and load-bearing"*. Everything gating is in the test code.

**F-001 (Important, ADR-0039/R1).** `tests/test_puzzle_solver_fifth_rule.py:622` asserts the shipped
blank board renders byte-identically to the same board with `_SHADOW_OFF` injected. But `_SHADOW_OFF` is
`.player-cell[data-state="filled"] { box-shadow: none !important; }`, and a **blank** board has no filled
cell — so the rule it disables matches nothing and the two renderings are equal **by construction**. The
arm's own message says *"the hairline is reaching cells that are not filled"*, and that is exactly the
direction it cannot fail in: any broadening of the hairline onto a non-filled cell is by definition not
the rule `_SHADOW_OFF` turns off, so the mutation sits in **both** readings.

Confirmed by execution twice, with both mutants proved non-no-op by killing other arms in the same
reading: `REACHES-BLANK` (hairline moved onto `.player-cell`) and `BROADEN-UNKNOWN` (a second rule for
`[data-state="unknown"]`) each leave `:622` **PASS** while `:637` and `:691` red. So the defect is caught
— by other arms — and what is wrong is a **false claim in a committed docstring and a committed registry
reason**, plus a dead assert. Important, not Critical, for exactly that reason.

The fix is one selector: widen `_SHADOW_OFF` at `:163` to `.player-cell`. Under SHIPPED a blank board
still has no shadow anywhere, so `:622` stays green; under either mutant `without` loses hairlines
`shipped` has and `:622` **reds**. Safe for the other three users of `_SHADOW_OFF` — in each, every cell
is already filled.

**G-3: SATISFIED — the implementer's reading was right, and the ruling is measured, not read.** Not one
assertion in any player test changed (the `test_puzzle_solver_page.py` diff is six lines inside a data
dict; `test_browser_fixture_scope.py` is outside `FAMILY_PREFIX` and is not a player test at all). Both
reshaped guards red in **both** directions, driven by patching the module's own globals: a 14th file with
no entry, a struck entry, an entry naming a missing file, a deleted file with its entry kept, a measured
file dropping out of the record, a struck `ALONE_PROBES` entry, and a 14th file neither recorded nor
probed — all RED; only the intended exemption is GREEN. **The decisive one:** a file that *was* measured
and drops out of the record **cannot** buy the new "postdates the record" exemption by adding an
`ALONE_PROBES` entry, because `measured & family <= seen` is unconditional and fires anyway. That was the
exact door that would have made this a waiver dressed as a narrowing, and it is shut.

**Figures re-derived through a genuinely independent door** — cell side from `getComputedStyle` *and* the
border box *and* `(right of col 19 − left of col 0)/20`, pixels from a `scale="device"` full-page
screenshot with exact nearest-reference classification and no tolerance window. Cells **24.8750** and
**14.3906** px (three derivations agreeing exactly); hairline **1 device px at dpr 1 at both viewports**,
2 px at dpr 2, 3 px at dpr 3, **never 0**; thin 1 / ink 2 / thin 1 across a major rule and 3 contiguous
thin across an ordinary one, at both viewports and both axes.

**And the defect was reproduced from outside this card's test code entirely.** The reviewer's probe
first run accidentally resolved the main checkout's editable install — i.e. the **pre-fix** stylesheet —
and measured **0 thin px** across a major rule (a pure ink blob) at both viewports and both axes.
Repointing `PYTHONPATH` at the worktree gave 1/2/1. So the owner's reported defect and this card's fix
are both confirmed without using any of the card's own assertions. That is the strongest evidence in the
hand-back.

Minors: **F-002** — AC-1's band *figures* are asserted at desktop only, although the card's Standards
section names the 14 px cell explicitly (the figures do hold at phone; the reviewer measured them).
**F-003** — the "derived count" the renamed guard advertises is logically subsumed by the set equality on
the next line, so it adds nothing; a naming-vs-mechanism mismatch, not a hole. **F-004** — the **guide
strip** has the same ink-on-ink class (`admin.css:343` 2 px `--grid-ink` frame against `:346`'s ink fill)
and is correctly outside this card's declared scope; recorded so the class audit is complete, and it
wants its own card.

**Everything inside the player is covered**, audited by the reviewer rather than assumed: `:530`/`:531`
(fifth rules + right/bottom frame) and `:525`/`:527`/`:549`/`:552` (all four gutter edges, CARD-193's
mirrored ones included) are swept by AC-2's ring at both viewports; `:523` and `:945` are never adjacent
to a fill; and the **editor board is unaffected** — `puzzle_edit.js` uses neither `.player-cell` nor
`data-state`.


---

### [Concurrent-session contention] 2026-10-22 — a second orchestrator was driving these same cards

Recorded because two of this card's agents independently reported it, and because it changes how one
artefact must be read.

**What was established, from the OS and from git rather than from reports.** A second Claude Code session
(shell snapshot `ipm4et`; this session's is `nbfuhi`) was running the same wave-54 cards in the **same
worktrees**. Observed live: a process polling `PythonProject4-card-262/meta/kanban/cards/CARD-262.md`'s
mtime every 15 s, and a pytest run in `PythonProject4-card-270` under a `card270-review2.lock` this
session never created. A memory entry written by a third session id (`d14443a2`, 17:47) describes that
session dispatching recovery agents into **these two worktrees** on the same assumption this session
made. All of those processes have since exited on their own; the machine was verified quiet (no shells,
no pytest, nothing anchored in the repo) before work resumed.

**Two measured contaminations, both reported by the agents themselves rather than discovered later:**

1. **CARD-262's target file was edited after its fix agent certified it.** 23 comment/docstring sites
   gained card-id qualifications (F-507, the one minor that agent had deliberately declined). The agent
   disclosed the hash mismatch rather than hiding it: the matrix ran against `f6d113ed…`, the commit
   holds `55311d7b…`.
2. **CARD-270's worktree card copy was written into mid-verification**, with figures from no run this
   session's agents made (a `BLANK-GONE` mutant, `:806`, "34 reached", a diff hash `ec0122bf…`). The fix
   agent replaced that section with measured figures and said so.

**The orchestrator's independent check, because an author-certified claim about bytes nobody re-fired at
is exactly what this board does not accept.** Three load-bearing mutants were re-fired against CARD-262's
**committed** bytes: `SHIPPED` exit 0; the cost-step mutant **RED**; the depth-bound mutant **RED**,
naming `test_the_receiver_resolution_bound_is_reported_rather_than_capped`; the file restored
**byte-identical** to `55311d7b…`. A third mutant self-skipped on a too-naive anchor (8 occurrences, not
1) — an instrument limitation, **not a survivor**, and said so rather than counted as a kill. So the
certification does transfer to the shipped bytes for the two mechanisms tested, and the residue is
narrower than the agent's disclosure left it.

**CARD-270's branch was rebased by the other session at 21:12** onto `0626b7fe` (this session's CARD-275
commit). Verified rather than assumed: `git diff base..tip -- src/ tests/` is **byte-for-byte identical**
across the rewrite (1262 lines both sides), the card's scope against main is unchanged at five files, and
`admin.css` is absent from the fix commit. No work was lost; only the commit hashes moved
(`4f41bbb4`→`a363da7e`, `fc035f7d`→`83278340`).

**One artefact is preserved but NOT used as evidence.** The other session left
`meta/review/20261022T175719Z-CARD-270-cycle2.yml` in CARD-270's worktree — a review of this card scoring
**9.7**, timestamped **17:57**, i.e. **nine minutes after the implementation commit and an hour before
this pipeline's cycle 1**. It is a different pipeline's artefact over bytes this session cannot
reconstruct, and its cycle numbering collides with this one's. Decisive reason to exclude it: this
pipeline's cycle 1 scored **8.4** and found F-001, a real Important that the fix round then confirmed and
closed. **A 9.7 would have landed this card with the tautological assert still in it.** Copied to the
session scratchpad under `foreign-session-artifacts/` so it survives, and left out of the card's
evidence chain.


---

### [Review 2/3] 9.6 — PASSES. All three cycle-1 findings CLOSED, and the rounding-noise catch confirmed

Report: `meta/review/20261022T213000Z-CARD-270-cycle2.yml` (28 keys, `yaml.safe_load` verified).
`10 − 0.3 (F-101 Minor) − 0.1 (F-102 Minor) = 9.6`. Zero Critical, zero Important → **the gate is met and
no third cycle is needed.** The foreign `…175719Z-CARD-270-cycle2.yml` was not read, not reconciled with,
and did not anchor this number — the reviewer confirmed that explicitly.

**F-001 CLOSED**, four readings. `_SHADOW_OFF` is `.player-cell` now; `:729` (the renumbered `:622`)
**reds** under both REACHES-BLANK and BROADEN-UNKNOWN in the recording pass and in the re-raising pass,
where cycle 1 measured it PASS. The safety argument was confirmed structurally **and** measured: four
callers, three preceded by `_open_filled`, and on an all-filled board the narrow and wide controls give a
**byte-identical** board screenshot at both viewports.

**The rounding-noise catch is confirmed exactly, and it is the best work in the round.** Reproduced
through the reviewer's own histogram code, never calling `_differing`: under REACHES-BLANK the **old**
byte-inequality control would have said PASS on **32 pixels at delta exactly 1** — 16 at x=227 and 16 at
x=725 — while the computed `box-shadow` is the identical string on all 400 cells in both readings. The
new form reds. Shipped headroom is **36 320 px at delta 64 against a 400 floor (90.8×)**. A control that
looked green really was measuring rounding noise. One nuance the reviewer added: merely *adding* the
everywhere-rule finds the two renderings byte-identical — the ±1 noise is produced by the style
add/remove cycle, i.e. by what the assert actually compares, so only the test's own sequence measures it.
And the docstring's "at the board's left and right extremes" was checked rather than assumed: 227.80 and
725.30 are the grid's outer frame columns, the same sense `admin.css`'s own comment uses.

**F-002 CLOSED** — PHONE-NO-HAIRLINE against two disjoint selections: 4 desktop nodes exit 0 / 0 FAIL, 4
phone nodes exit 1 with `:433`/`:473` FAIL. A phone-only regression was genuinely invisible to the old
arms. The 4-vs-2 deviation from the brief is **accepted**: `:473` is a different test with its own control
and its own figure, the mutant reds both independently, and the cost was measured (the file is in none of
the slowest eight of a 126-test run).

**F-003 CLOSED** — the new node-id door reds on three directions arm 1 cannot see (**G1**: a 14th file
*with* a `PAGE_ISOLATION` entry but in no node-id registry — the justification, and it holds; G3; G4),
while G2 shows arm 1 was not weakened. A strictly stronger second door, not a renaming, and cycle 1's
waiver door (D9) is untouched.

**All six rewritten claim texts were checked against a mutant and all six are true** — including the
sixth, the registry reason at the layout arm: MOVES-LAYOUT reds `:639` and `:814` while `:649` passes,
exactly as the rewritten reason now says.

**Q1 ruled, measured not reasoned:** `:748` does **not** need viewport parametrizing — at 390×844 the same
comparison changes **19 560 px** past tolerance against the 400 floor (48.9× headroom), every differing
pixel at delta 64. There is no cell size in the card's range at which 400 becomes tight.

**An instrument bug the reviewer caught on itself:** its first PHONE-REACHES-BLANK probe printed MUTATED
== the shipped hash (the mutant was missing from its wrapper's edit table and zsh had no `set -e`). It
discarded the reading as a no-op, fixed the wrapper and re-fired — the "no-op ≡ survivor" rule firing on
the reviewer's own instrument, which is exactly where it is cheapest.

**Deliberate non-action, stated:** cycle 1's nine other `admin.css` mutants were **not** re-fired, because
`admin.css` is absent from the fix commit and byte-identical to the bytes cycle 1 certified. NO-HAIRLINE
and MOVES-LAYOUT *were* re-fired, because renumbering could have cost a kill and because one rewritten
claim names MOVES-LAYOUT.

### [Carried forward, not fixed] two minors, and why they are not being fixed on the way out

**F-101** — both arms protecting *"no non-filled cell carries a hairline"* are **desktop-only**, so
F-001's own defect scoped to a media query survives this card's whole file: PHONE-REACHES-BLANK gives
50 PASS / 0 FAIL of 50 nodes, exit 0, and was proved non-no-op out of band (a blank phone board's computed
`box-shadow` goes from `{'none': 400}` to the inset string on all 400 cells). Minor rather than Important
because the claim *does* have a control that can fail at desktop and each test declares its domain
honestly; what over-reaches is one file-docstring sentence. Cheapest fix, per the reviewer: parametrize
`test_no_other_cell_state_gains_a_shadow` on `_VIEWPORTS` — computed styles only, one page load.

**F-102** — the `_VIEWPORTS` comment claims a test *"cannot be parametrized on a subset of them by
accident"*. Nothing enforces it, and `:697`/`:758` are desktop-only without using it. One word.

**Why neither is fixed here:** the card has met its gate and two of three cycles are spent. This board's
own rule is that `max_cycles` is a budget and not a last-mile rule — an edit made on the way out has no
cycle left to certify it, and that is how two cards shipped unreviewed final commits in wave 48. Both are
carried to the next card that touches this file rather than bolted on uncertified. The subject is the
same family as F-001, so whoever takes it should expect the review to look there first.


### [AC/EC/G gate] PASSED — and who verified which half is stated

This card did **not** get a separate gate agent, and that is a deliberate, stated choice rather than a
skipped step: cycle 2 passed at 9.6 with explicit per-AC and per-guardrail verdicts backed by executed
evidence, so a third heavy agent would have re-run the same work. The split:

**Verified by the reviewer (behavioural, executed):** AC-1 MET (cycle-1 caveat cleared), AC-2 MET, AC-3
MET (cycle-1 caveat cleared; residual F-101 carried), AC-4 MET. ADR-0038/R1 HOLDS, ADR-0038/R4 HOLDS
(all four `data-state` values read off the DOM; no-layout-shift measured by the arm that kills
MOVES-LAYOUT), CON-021 HOLDS (re-derived from disk: `.player-cell` occurs in exactly three files under
`src/`, and `puzzle_edit.js` contains neither `player-cell` nor `data-state`).

**Verified by the orchestrator (structural, from the diff — my own commands, not a report):**

| check | result |
|---|---|
| G-1 — nothing under `nonogram/export/`, no `book_pdf`, no `layout.py` | **NONE in the diff** |
| G-3 — `solver.js` / `solver_state.js` / `puzzle_edit.js` | **NONE in the diff** |
| G-2 + AC-4 — `tokens.css` | **not touched**; the card budgeted one new token and spent **zero** |
| AC-4's named token test | `tests/test_admin_design_tokens.py:234` |
| AC-1/AC-2/AC-3's named classes | all three present in `tests/test_puzzle_solver_fifth_rule.py` |
| G-4 — the owner's render | **16 PNGs** on disk under `~/Documents/nonogram-reviews/CARD-270/` |

**G-4, read against the owner's standing instruction rather than this card's literal wording.** The card
says the owner sees a render *before* merge. The owner's standing rule on this board is the opposite
default — *merge on gates, not on the owner's eyeball; they verify renders after a merge* — and what G-4
substantively demands, the evidence, exists and was looked at: the orchestrator compared
`before-desktop-mixed-crop6x.png` with `after-desktop-mixed-crop6x.png` and the filled region goes from
one fused blob to distinct counted cells. The renders stay valid without re-rendering because `admin.css`
is byte-identical to the bytes cycle 1 certified. **The open taste question — whether the fifth rule
should stay equally loud *inside* a filled region, where it is now told apart by its 2 px core rather
than by contrast — was surfaced to the owner and is deliberately not decided here.** It is a preference
on a shipped improvement, not a defect, and the lever if the owner wants it louder is the card's own
alternative: a filled-cell ink one step off the rule ink.

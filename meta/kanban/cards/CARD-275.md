# CARD-275: The guide strip's frame vanishes against filled cells — the same ink-on-ink class, in the second place it lives

**Status:** ready
**Priority:** P2
**Category:** ops
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/275-guide-strip-frame
**Worktree:** —
**Source:** CARD-270's review cycle 1, finding **F-004** (2026-10-22): the reviewer audited the whole ink-on-ink class and found the guide strip carries it too, correctly outside CARD-270's declared scope (`Design context: .player-cell[data-state="filled"] only`). Recorded so the class audit is complete; carded on the owner's instruction the same day.
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/tokens.css, tests/test_book_finalise_guide_preview.py, tests/test_admin_design_tokens.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The defect, with its mechanism verified in the code

**Where it shows.** The "How to Solve" guide preview on the book finalize page
(`src/nonogram/admin/templates/book_finalize.html`, five strips at lines 59, 68,
82, 105 and 157 — the basic rule, the single-cell legend, two technique
demonstrations and the worked example).

**Mechanism.** The same single-token collision CARD-270 fixed in the player:

- `.guide-strip` carries the frame — `border: calc(2 * var(--border-width)) solid var(--grid-ink)` (`admin.css:343`)
- `.guide-strip-cell[data-state="filled"]` carries the fill — `background: var(--grid-ink)` (`admin.css:346`)

Frame and fill are the **same ink**, so wherever a filled cell meets the frame
the boundary disappears.

**This is worse than "only at the two ends", and that is the part worth
knowing.** `.guide-strip` is an `inline-flex` row with no padding, so every
cell's **top and bottom** edges touch the frame directly — not just the first
and last cell's outer sides. A filled cell anywhere in a strip therefore loses
its top and bottom boundary, and a run of filled cells reads as a bar fused
into the frame rather than as *n* counted squares. On a page whose entire job
is teaching someone to count runs, that is the wrong thing to blur.

**But the defect is NARROWER than the player's was, and the card must not
over-reach.** Two neighbours are already correct and must stay untouched:

- **The cell-to-cell separator already reads.** `.guide-strip-cell + .guide-strip-cell`
  (`:345`) is `color-mix(in srgb, var(--grid-ink) 28%, var(--grid-paper))` — a
  light grey, the *same value* as the player's `--player-thin` (`:463`). A light
  grey line against an ink fill is visible, so adjacent filled cells inside the
  strip are already divided. **Only the frame is the defect.** Verify this on the
  render before changing anything: if the separator turns out to read poorly too,
  that is a finding to report, not an assumption to act on.
- **The `crossed` state is unaffected.** Its two ink diagonals (`:347`–`:349`)
  are drawn on a paper background and inset at `left: 18%` / `right: 18%`, so
  they never touch the frame.

## What to implement

1. **Give a filled guide cell its own boundary**, the same remedy CARD-270
   shipped for the player and for the same reason — it fixes frame-adjacency
   uniformly with no neighbour-dependent CSS. CARD-270's committed form is one
   declaration added to the existing filled-cell rule:
   `box-shadow: inset 0 0 0 <rule-width> <the 28% grey>`. Follow it unless the
   render says otherwise; the strip's rule width is `var(--border-width)`, not
   the player's `--player-rule`.
2. **Hoist the shared grey to a token** (the secondary finding, and the reason
   `tokens.css` is in `Touches`). `:345` writes
   `color-mix(in srgb, var(--grid-ink) 28%, var(--grid-paper))` **inline**, and
   `:463` defines `--player-thin` as byte-identically the same expression — but
   scoped inside the player block, so the guide strip cannot reach it. One grey,
   defined twice, in two scopes. Promote it to a shared token and have both use
   it. If promoting it turns out to change the player's computed value in any
   way, **stop and report** — CARD-270 just shipped pixel assertions over that
   exact colour and they must not be disturbed.
3. **Alternative, if the inset hairline disappoints on the render:** recolour the
   frame instead of the fill. Cheaper to reason about but less consistent with
   the player, and it changes the strip's outline everywhere rather than only
   where a fill meets it. Show both to the owner rather than choosing silently.
4. No JS, no template change, no state change expected. If the chosen mechanism
   needs one, that is a finding to surface, not to absorb.

## Acceptance criteria

- **AC-1** (happy, the reported defect): *Given* a guide strip whose cells
  include a filled one, *then* that cell's top and bottom boundaries against the
  frame are visible — a pixel sample across each finds a non-ink band between
  the ink fill and the ink frame. (test:
  `TestGuideStrip_FilledCellsKeepTheirFrameBoundary`)
- **AC-2** (edge, the ends): *Given* a filled cell first or last in its strip,
  *then* its outer side reads against the frame the same way. (test:
  `TestGuideStrip_FirstAndLastCellsToo`)
- **AC-3** (edge, what must NOT change): *Given* the fix, *then* the cell-to-cell
  separator, the `crossed` diagonals, the blank cells and the strip's geometry
  are unchanged — same cell size, no layout shift, and the existing
  `tests/test_book_finalise_guide_preview.py` classes pass **unedited**. (test:
  `TestGuideStrip_NothingElseMoves`, plus the existing file run unedited)
- **AC-4** (edge, the player is not disturbed): *Given* the token hoist, *then*
  `--player-thin` resolves to exactly the value it resolves to today, and
  CARD-270's pixel assertions pass unedited. (test:
  `TestGuideStrip_ThePlayersGreyIsUnchanged`; and CARD-270's
  `tests/test_puzzle_solver_fifth_rule.py` run unedited)
- **AC-5** (edge, tokens + no literal): *Given* the shipped stylesheet, *then*
  every new value comes from tokens with a per-rule check, and the inline
  `color-mix` at `:345` is gone in favour of the shared token. (tests:
  `test_the_guide_strip_division_comes_from_tokens`,
  `test_the_stylesheet_uses_tokens_not_literals`)

## Guardrails

- G-1: **Web preview only.** Nothing under `src/nonogram/export/**` and no change
  to the book/print pipeline. The printed guide page is a different pipeline
  entirely (`book_pdf_generator.py`, Pillow) — see the open question below. The
  CON-019 byte-identity tripwires run unedited.
- G-2: Hand-written CSS, tokens only (ADR-0038/R1; test:
  `test_the_stylesheet_uses_tokens_not_literals`).
- G-3: **CARD-270's work is not disturbed.** `.player-cell` rules,
  `--player-thin`'s computed value and `tests/test_puzzle_solver_fifth_rule.py`
  are untouched and pass unedited. This card may only *read* the grey CARD-270
  relies on, never redefine what it resolves to.
- G-4: No JS and no template change: `solver.js`, `solver_state.js`,
  `puzzle_edit.js` and `book_finalize.html` are not edited.
- G-5: The owner sees a render of the guide preview — a strip with filled cells
  at the ends and in the middle — before merge, and picks between the inset
  hairline and the recoloured frame. A green suite does not close this card.
- G-6: No new runtime dependency.

## System contract

- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check: review-lens)
- ADR-0038/R4 — state logic is a pure module, separate from rendering; this card
  touches rendering only (check: review-lens)
- CON-019 — the CLI/web export byte-identity tripwires stay green and unedited
  (check: `tests/test_export_a4_golden.py`, `tests/property/test_cli_exports_byte_identity.py`)

## Architecture context

- **FR:** the book finalize page's guide preview (CARD-201/CARD-229-era work
  built these strips; this card changes only how a filled cell is bounded).
- **ADR:** ADR-0038/R1, R4.
- **CON:** CON-015/CON-016 (the admin door), CON-019.
- **Components:** COMP-009 (admin panel: static CSS).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Design context

- **Design system:** `static/tokens.css` + `static/admin.css`. This card is
  expected to **remove** a literal (`:345`'s inline `color-mix`) and add a token,
  so the token count should go down by one duplication, not up.
- **UI components:** `.guide-strip` and `.guide-strip-cell` only.
- **Screens:** the book finalize page's "How to Solve" preview.
- **Standards:** no layout shift; the strip is `aria-hidden="true"` in every one
  of its five call sites, so this is purely visual and adds no ARIA.

## Named tests resolved before the card started (drafting, 2026-10-22)

**Already exist** (run them, do not rewrite them):

| name | resolves to |
|------|-------------|
| `tests/test_book_finalise_guide_preview.py` | 708 lines, 5 classes, `HTMLParser`-based — it parses rendered HTML and is **not** a browser/pixel test |
| `test_the_stylesheet_uses_tokens_not_literals` | `tests/test_admin_design_tokens.py:219` |
| CARD-270's pixel suite | `tests/test_puzzle_solver_fifth_rule.py` (must pass unedited — G-3) |

**To be written by this card** — none exists yet; report them as written, never
as passing before they exist:
`TestGuideStrip_FilledCellsKeepTheirFrameBoundary`,
`TestGuideStrip_FirstAndLastCellsToo`,
`TestGuideStrip_NothingElseMoves`,
`TestGuideStrip_ThePlayersGreyIsUnchanged`,
`test_the_guide_strip_division_comes_from_tokens`.

## Worktree notes

- **[Read CARD-270 first — it is the same defect and its review is the map]**
  Its committed fix is one declaration; its review re-derived the figures through
  an independent door and reproduced the defect from *outside* the card's own
  test code. Two lessons transfer directly: (1) a pixel assertion must state its
  **domain** — viewport, dpr, zoom, which scanline — and never generalise from
  one sampled edge; (2) CARD-270's gating finding was an assert that could not
  fail in the direction its own message named, because the stylesheet it injected
  to create the "without" state disabled a rule the test's board could not match.
  If you build a with/without comparison here, make sure the "without" really
  removes the thing under test.
- **[The browser-family registries will red, and feeding them is a judgement
  call CARD-270 already had ruled on]** A pixel test needs a browser, and
  `tests/test_browser_fixture_scope.py` holds registries over the browser test
  family. CARD-270 added the thirteenth file to the `tests/test_puzzle_solver_*`
  prefix family and had to feed three CARD-235 guards; its review **ruled that
  satisfies G-3** because no player-test assertion changed and both reshaped
  guards still red in both directions. A guide-preview file sits outside that
  prefix — **check whether the registries reach it at all before assuming they
  do**, and if they do, feed them rather than loosening them, and say so.
- **[Open question, not a claim: the PRINTED guide]** This card is the web
  preview. Whether the printed guide page has the same ink-on-ink collision is
  **unchecked** — it is drawn by `book_pdf_generator.py` with Pillow, a different
  pipeline with its own geometry, and CARD-201/CARD-229 own that page. Do not
  investigate it inside this card's scope; if a look is cheap, report what you
  see as a finding for a follow-up card.
- **[Conflict note]** `admin.css` and `tokens.css` are touched by CARD-270 (in
  review) and by the queued player cards CARD-267/268/269/271, so the dispatcher
  will serialize this against any of them in the same wave. CARD-270 should merge
  first — this card reads the grey that card's pixel assertions depend on.
  CARD-274 (the `admin/app.py` blueprint split) does not touch CSS, so it is
  independent.

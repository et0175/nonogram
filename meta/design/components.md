# Component inventory — Nonogram admin panel

Direction: Pressroom (see `brief.md`). Every component below is styled only
with tokens from `tokens.css`; the CSS lives in
`src/nonogram/admin/static/admin.css`, the markup in
`src/nonogram/admin/templates/`. Append new components at the end.

## AppShell
Used by: all screens (`base.html`).
Layout: ink top bar (brand, section crumb, database name) · 220px paper
side nav · main column on paper; no footer.
States: default · flash message (success / info / error) · narrow (< 820px:
side nav collapses to a horizontal strip).
Tokens: --color-bg, --color-topbar, --color-topbar-text, --side-w,
--topbar-h, --space-*.

## SideNav
Used by: all screens.
States: default · hover · current (`aria-current="page"`, derived from
`request.path`, accent rule on the left) · group label (small caps).
Tokens: --color-accent, --color-accent-tint, --color-surface-hover,
--text-sm, --font-ui.

## PageHeader
Used by: all screens.
Parts: italic serif h1 · lede (secondary text) · optional right-aligned
actions · optional status chip (books).
Tokens: --font-display, --text-2xl, --weight-display, --color-text-secondary.

## StatBlock
Used by: dashboard, re-grade.
States: default · zero (renders "0", never hidden) · emphasised (accent
number for the one figure that matters, e.g. drafts waiting).
Tokens: --font-num (tabular), --text-xl, --color-border (bottom rule).
Notes: figures are never coloured by inline style; one accent per row.

## FilterBar
Used by: puzzle review, book puzzle selection.
States: default · with active filters (Clear link visible) · error
(flash "Filter error").
Tokens: --color-surface, --color-border, --control-h, --shadow-inset-input.
Notes: labels are visible text above each control; no `&nbsp;` spacer labels.

## DataTable
Used by: puzzle review, books list, book detail, re-grade, batch summary.
States: default · row-hover · empty (EmptyState inside the table shell) ·
rejected row (name and thumbnail at 55% opacity) · sortable head (real
`<a>` links, current column marked with ↑/↓ and `aria-current="true"`,
its `<th>` carrying `aria-sort`; the arrow is `aria-hidden` and the
direction repeats in `visually-hidden` text) — that head treatment is
`books_list.html` only, and `_puzzle_table.html` has yet to follow: it
still sorts with `href="#"` plus script, carries no `aria-sort`, and
leaves its arrow unwrapped and its direction unsaid.
Two query-parameter names are in use: the puzzle review table sorts with
`sort_by` (`_puzzle_table.html`, the older name) and `/books` with `sort`
(`books_list.html`, CARD-132). `sort` is the convention going forward —
shorter, and it is the one the server-rendered link pattern uses; the
puzzle table keeps `sort_by` until a design-system card renames it, so
read the template before assuming which one a table takes.
Tokens: --row-h, --font-num for every numeric column (right-aligned,
tabular-nums), --color-surface-sunken for thead, --color-border for rules.

## Thumbnail
Used by: puzzle review, batch results, book selection, arrangement.
States: default · loading (paper square) · failed (paper square with
"No preview" text, via `onerror`) · hover (no scale; link underline only).
Tokens: --thumb, --grid-paper, --color-border, --radius-control.

## TierChip (`_tier.html` macro)
Used by: every surface that shows a difficulty.
States: easy · medium · hard · guess · ungraded (grey, "N/A").
Tokens: --color-tier-* via inline `--tier`, color-mix onto --color-surface
and --color-text.

## StatusChip
Used by: puzzle review (puzzle status), books (book status), batch status.
States: draft (outline) · approved (success tint) · rejected (danger tint) ·
in book / ready / published (accent tint) · generating (warning tint).
Markup: `<span class="badge" data-status="…">` — the class name and the bare
status text are pinned by tests.
Tokens: --color-success(-tint), --color-danger(-tint), --color-accent(-tint),
--color-warning(-tint), --radius-badge.

## RecognizabilityChip
Used by: puzzle review, batch results.
States: high (success text) · medium · low / N/A (secondary).
Tokens: --color-surface-hover, --color-success, --text-xs.

## Button
Variants: primary (accent) · quiet (outline, surface) · approve (success
outline → solid on hover) · reject (danger outline → solid on hover) ·
danger-quiet (text danger) · link.
States: default · hover · focus-visible (2px accent ring) · disabled (55%
opacity, not-allowed) · busy (spinner + label, via JS).
Tokens: --color-accent(-hover), --color-on-accent, --color-success,
--color-danger, --control-h, --radius-control, --duration-fast.
Notes: icon-only buttons carry `aria-label`; icons are inline SVG from
`_icons.html`, never emoji.

## FormField
Used by: batch create, book create *and* the book's general-info step (one
template, two modes), print setup, filters.
States: default · focus · invalid (danger border + hint) · disabled ·
with unit suffix (input-group) · file (native).
Tokens: --color-input, --color-border-strong, --shadow-inset-input,
--control-h, --text-sm for hints, --color-danger for the invalid border.
Notes: `invalid` marks **only the control the refusal named**, never the whole
form, and always as all three of `is-invalid`, `aria-invalid="true"` and an
`aria-describedby` pointing at a **page-local** error region (`#plan-error` on
print setup, `#general-info-error` on book general info) — base.html's shared
flash stack emits no stable id to point at. The field name comes from the
domain's own refusal (`InvalidPlan.fields`, `InvalidBookDetails.fields`), so
the page never re-derives which control failed. A refusal re-renders what the
owner submitted, not what storage still holds.

## Stepper
Used by: book scaffolding steps 1–5 — general info, print setup, puzzle
selection, arrangement, finalise & export — the book's detail page (which
renders the list with **no** step current), and the batch workflow.
States, on two axes. Progress: done · current (accent, `aria-current="step"`)
· upcoming (secondary). Reachability: a step renders as a **link** when the
page has a book to link to and the step is not the current one; plain text
otherwise — on New book, which has no book yet, and always for the current
step. A book's status enters neither axis: every step of a book that exists is
linked, draft through published.
Tokens: --color-accent, --color-text-secondary, --font-num for step numbers.
Notes: one macro (`_stepper.html`), never hand-copied per page. The step list
is stated once in that file, and every number and count a page prints comes
from it — `book_step_number(key)` for one step's number, `book_step_count()`
for how many there are, `book_step_of(key)` for the "Step 3 of 5" lede (it
asks `book_step_count()` for the total) — rather than being written into each
page's prose. That includes counts *about* the list: New book's "the 4 steps
that follow" is `book_step_count() - 1`. So adding a step renumbers the prose
with the list — Print setup included since CARD-159. (Route docstrings
**name** their step rather than numbering it, for the same reason.)

## PuzzleTile
Used by: book puzzle selection.
States: default · hover · selected (accent border + tint, checkbox checked) ·
no preview.
Tokens: --color-surface, --color-accent, --color-accent-tint, --thumb.

## ArrangeRow
Used by: book arrangement (step 4 of 5).
States: default · first **of its level** (up disabled, "First in the <Level>
level") · last **of its level** (down disabled, "Last in the <Level> level") ·
title editing (inline input) · position typed (inline FormField, see below) ·
position refused (that one box `is-invalid`, `#position-error` above the list) ·
page-break divider where the printed plan starts a page — a
`.page-break-divider` rule labelled with that interior page number, and a
divider page of its own at each level's head (CARD-140/CARD-128), not a rule
after every third row.
The rows sit under one level heading per non-empty level (TierChip + "<Level>
level" + count), easy then medium then hard: a move stays inside a level
(INV-009, CARD-126), so the disabled state is at each level's own ends rather
than the book's, while the row number still runs 1..n across the whole book.
Two numbers, and they are not the same number: `.item-order` is the row's place
in the **book**, and the position box in `.item-info` is its place in its own
**level** ("Position in <Level>" … "of <count>"), which is what a move is
confined to. Typing a position moves the puzzle there and shifts the rest of
its level along to make room — the same move as clicking the arrow that many
times — and the lede says so. The box is a `form-control form-control-sm num w-auto` sized by
`size="3"`, submitting on `change` as the title field does, and it introduces no
CSS of its own. Refusals follow FormField exactly: the range is named in prose
in one page-local `alert alert-danger` with `id="position-error"`, and only the
box the refusal named carries `is-invalid` + `aria-invalid="true"` +
`aria-describedby="position-error"` (CARD-143). Nothing is clamped: an
impossible position is refused and the order is unchanged.
Tokens: --color-surface, --color-border, --font-num (#order and the box).

## ProgressBar
Used by: batch status; books list (the `.plan-progress` variant — a
table-row-height bar under the count, no in-bar text, CARD-132).
States: pending · generating (accent fill, auto-refresh) · complete (success
fill) · failed / cancelled (danger fill, error text).
`.plan-progress` states: partial (accent fill, the default) · complete
(success fill). They are fill levels, not job lifecycle: a books-list bar
never says `generating`, so a rule written for a batch job in flight does
not reach it.
Tokens: --color-accent, --color-success, --color-danger, --color-surface-sunken.

## Flash / Alert
Used by: base (flashed messages), inline notes.
Variants: success · info · warning · danger; dismissible.
Tokens: --color-*-tint, --color-* (left rule), --radius-container.

## Modal (puzzle detail)
Used by: puzzle review.
States: closed · loading (spinner) · loaded · load-error (danger alert,
Close still works) · with assign-to-book form (only when unassigned).
Tokens: --shadow-modal, --color-surface, --radius-container, --duration-base.
- Actions: a "Solve" action (btn-outline-primary, first in the downloads row) links to /puzzle/<id>/solve — the puzzle player (CARD-160, FR-044).

## EmptyState
Used by: every list/table when there is nothing to show.
Copy is specific: "No puzzles match these filters", "No books yet — create
one", "No puzzles generated — check the quality threshold".
Tokens: --color-text-secondary, --space-8.

## ErrorPage (404 / 500)
Used by: `404.html`, `500.html`.
Parts: mono status code, serif title, one sentence, "Back to dashboard".
Tokens: --font-num, --text-2xl, --color-danger (500 only).

## Pagination
Used by: puzzle review.
Markup pinned by tests (`page-item`, `page-link`, `aria-current`).
Tokens: --color-accent, --color-on-accent, --radius-control.

## SolverBoard

Used by: the puzzle player (`puzzle_solve.html`, drawn by `static/solver.js`; CARD-160, FR-044, ADR-0038).
- Parts: column-clue boxes above, row-clue boxes left, W×H cells; a heavy rule after every 5th line on both axes and on the frame (the printed page's counting aid); the clue area carries the same rules.
- States: loading / no-script (fallback sentence "…the player script did not load") · error (danger alert, no board, when the payload is unreadable) · drawn — each cell `unknown` (bare --grid-paper), `filled` (--grid-ink) or `empty` (small --color-text-secondary dot).
- Sizing: cell side clamp(14px, fit, 28px) from the board size and clue depth; fits 1440×900 at 30×30; below the floor it scrolls inside `.player-stage`, and the page never scrolls sideways (1366×768 scroll for deep-clue 30×30 is owner-accepted for the admin POC).
- Tokens: --grid-paper, --grid-ink, --color-surface, --color-text-secondary, --border-width, --font-num, --topbar-h, --space-*. Candidate tokens still local custom properties in admin.css (CARD-160 F-004): --player-cell-min 14px, --player-cell-max 28px, thin rule = color-mix(--grid-ink 28%, --grid-paper).

## ClueBox

Used by: SolverBoard. One box per line (a row's to the left, a column's above), one numeral slot per clue number, cell-sized, --font-num tabular; an empty line shows the single number "0"; `aria-label` "Row N: …" / "Column N: …".
- States: default only (CARD-161/162 may add "line satisfied").
- Tokens: --color-surface, --font-num, --grid-ink.

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
`<a>` links carrying `sort_by`, current column marked with ↑/↓).
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
Used by: batch create, book create, print setup, filters.
States: default · focus · invalid (danger border + hint) · disabled ·
with unit suffix (input-group) · file (native).
Tokens: --color-input, --color-border-strong, --shadow-inset-input,
--control-h, --text-sm for hints.

## Stepper
Used by: book scaffolding steps 1–4, batch workflow.
States: done · current (accent) · upcoming (secondary).
Tokens: --color-accent, --color-text-secondary, --font-num for step numbers.
Notes: one macro (`_stepper.html`), never hand-copied per page.

## PuzzleTile
Used by: book puzzle selection.
States: default · hover · selected (accent border + tint, checkbox checked) ·
no preview.
Tokens: --color-surface, --color-accent, --color-accent-tint, --thumb.

## ArrangeRow
Used by: book arrangement (step 3).
States: default · first (up disabled) · last (down disabled) · title editing
(inline input) · page-break divider after every 3 rows.
Tokens: --color-surface, --color-border, --font-num (#order).

## ProgressBar
Used by: batch status.
States: pending · generating (accent fill, auto-refresh) · complete (success
fill) · failed / cancelled (danger fill, error text).
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

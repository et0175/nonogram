# Design brief — Nonogram admin panel

## Personality
Audience: one Puzzle Creator (the owner) at a desk, in focused review
sessions — approving image-derived nonogram grids, assembling them into
print books for KDP. The pictures under review are black-and-white pixel
grids; the finished product is a printed book. Nobody else looks at this UI.

Sliders (assumed from narrative — `mode: interactive` was used for the
direction choice, the sliders were derived, not elicited):
serious ●───○─ playful · dense ──●─○─ airy · classic ●──○── experimental · warm ●─○─── cool

Mood words: print-shop, calm, legible, made-by-hand, unhurried.
References liked: none named — the user chose from rendered previews.
References disliked: none named.
Hard constraints:
- Tier colours `#27ae60 / #f39c12 / #e74c3c / #8e44ad / #95a5a6` are pinned
  by `tests/test_admin_tier_surfaces.py` (the rendered badge must contain
  the hex). They are kept as the *hue source* of the tier chip
  (`--color-tier-*`) and tinted onto the paper via `color-mix`.
- Status badges in the puzzle table must render as `<span class="badge" …>`
  followed by the bare status word (`tests/test_card_066_status_filter.py`).
- No third-party runtime dependency may be added (ADR-0006); Bootstrap 5.3
  stays as the CDN grid/forms/JS layer and is re-themed through its CSS
  variables, never forked.
- Dark mode: **none** (derived). The content is black-ink-on-paper grids and
  the output is print; a dark surface would invert the very thing being
  judged. Revisit with `/forge:ui brief` if the panel ever runs on a shared
  screen.
- Accessibility target: WCAG 2.1 AA (text ≥ 4.5:1, control boundaries ≥ 3:1).

## Direction: Pressroom (chosen 2026-09-14)
Cream paper, ink-navy serif text, tabular monospace numerals, hairline rules
instead of card boxes, one bookcloth-green accent. It ties the panel to the
job — making printed puzzle books — and makes the grid thumbnails read as
proofs on paper rather than icons in a dashboard. Satisfies serious, classic
and warm; density is medium (64px table rows, 52px thumbnails: large enough
to judge whether a picture is recognisable, which is what review *is*).

Base direction(s): **Warm print / Retro** (structure, voice). The one period
cue is the serif; no texture, no ornament.

### Rejected candidates
- **Proof sheet (Swiss / International)** — was the recommendation and the
  first pick; the user reversed it in favour of the warmer, print-adjacent
  voice. Preview kept at `previews/direction-proof-sheet.html`.
- **Grid bench (Dense data / Terminal-pro)** — 34px thumbnails are too small
  to judge recognisability at a glance, and 100-row batches are rare here.
  Preview kept at `previews/direction-grid-bench.html`.

## Anti-patterns (this product must NOT look like)
- An AI demo: purple/indigo gradients (the old batch page had
  `#667eea → #764ba2`), emoji as icons, rounded-xl cards with soft shadows.
- A generic Bootstrap admin theme: red primary button that reads as
  "danger", coloured stat tiles, a "System status: ✅ Ready" card.
- A consumer app: no springy motion, no illustration, no mascots.
- Kitsch print: no paper-grain texture, no drop caps, no ornaments — the
  serif is the single period cue.
- The global Anti-defaults list in forge's `style-directions.md` applies.

## History
- 2026-09-14 — three directions rendered (proof-sheet, pressroom,
  grid-bench); "Proof sheet" selected, then reversed by the user in the
  same session; "Pressroom" chosen (interactive).

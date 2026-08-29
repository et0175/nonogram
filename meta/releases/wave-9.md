# Wave 9 — 2026-08-29   (tag: wave-9)

Single-card wave: CARD-015 ships COMP-003's third and final grid source. The handoff
called this "the last untested technical risk" (dithering quality unproven until real
images ran through it). Zero fix cycles — cleared cycle 1 at 9.5/10.

## Shipped
- CARD-015 (feature): Uploaded-image conversion via resize and Floyd-Steinberg
  dithering — `--mode image --image PATH` loads a user's file with Pillow, converts to
  greyscale, crops to its largest centred square, resizes to the exact target grid
  dimensions, and applies Floyd-Steinberg error-diffusion dithering to binarize each
  cell. Image mode deliberately bypasses POL-001's regenerate loop entirely — an
  uploaded image is fixed and cannot be re-drawn — failing cleanly on a non-unique
  conversion instead of silently retrying.   score 9.5 (cycle 1/3)   FR-003, INV-003,
  ADR-0006, ADR-0010, ADR-0012

## Requirements closed
- FR-003 (image-sourced grids) — closes Increment 3's last untested risk. All three
  grid sources named in the original spec (random, library, image) now ship.

## Design decision worth recording
AC-009 permitted either a stretch or a letterbox-then-crop policy for aspect-ratio
mismatch; the implementer chose a third option — centre-crop to the largest square,
then resize — and argued it in the module docstring on puzzle-quality grounds rather
than just picking one: stretch distorts the subject beyond what a 10-50-cell grid can
afford to lose (a nonogram's payoff is a recognisable solved picture), and letterbox
spends the grid's scarcest resource on blank padding, which is both a worse picture
*and* a worse puzzle (an empty padded row is a free `0` clue for the solver). The
reviewer independently re-implemented both rejected alternatives against the same test
fixtures and confirmed they genuinely fail the discriminating assertions (4 of 6 in
each case) rather than taking the implementer's word for it.

## Two carried follow-ups, both resolved and independently re-verified
- **CARD-007's note** (from its cycle-2 review): `cli.py`'s bare `except OSError`
  wrapped the *entire* command handler on the premise that an OSError could only come
  from export. This card reads a user file from disk, so an unreadable `--image` would
  have been misreported as "export rejected" instead of an input error. Fixed by
  narrowing the except to wrap only the export call, plus an independent domain error
  (`UnreadableImage`) that never lets a bare OSError reach that clause at all. The
  reviewer confirmed CARD-007's original repro (a bad `--out` path) still reports
  cleanly — the narrowing didn't undo what it was built for.
- **CARD-008's note** (from its cycle-1 review): `orchestrator._source_arguments`'s
  implicit else-fallback would have silently miswired image mode's arguments the
  moment it was registered — binding a file-path parameter to an integer size. Fixed
  with the exact explicit-branches-plus-`ValueError` shape the note suggested. The
  reviewer confirmed the hazard was real (not hypothetical) before confirming the fix.

## Review process notes
- Cleared cycle 1 outright (9.5, zero Critical/Important findings). The reviewer's
  independent verification was unusually deep for a LOW-risk/FAST-lane card: it traced
  the actual control-flow graph for G-4 (image mode must never enter the regenerate
  loop) rather than trusting test names — confirming `run_bounded` is reachable only
  through one call site the image branch's three exits all precede — and separately
  decoded and forensically verified all four test fixtures (including confirming
  `corrupt.png` really is a valid PNG signature followed by garbage, not an accident).
- Four files outside the predicted `Touches:` were flagged, not done silently: a new
  `UnreadableImage` error class (required by AC-008's own wording), and three
  pre-existing tests that used `"image"` as their unregistered-mode placeholder string
  (now `"webcam"`) — the same forced hand-on pattern every mode/format card has hit
  when it makes a placeholder real.

## A genuine judgment call, surfaced rather than decided
The reviewer found that EXIF orientation metadata is ignored during conversion — a
phone photo carrying rotation data converts cropped along its *stored* axis rather than
its displayed one. No AC or guardrail is technically violated (the output grid is still
exactly the right size), which is why this didn't block merge, but it directly affects
this feature's headline use case. A one-line fix is available
(`ImageOps.exif_transpose`, a no-op on files with no orientation tag) but wasn't in
CARD-015's contract, so it wasn't applied unilaterally. **Backlogged for a user
decision**, alongside CARD-014's non-ASCII-header question from Wave 8.

## Convergence
- FR-003 ✓ converged. Increment 3's grid-sourcing surface (random + library + image)
  is now fully shipped.

## Known gaps / escalations
- AC-037 — still tracked via `xfail`, CARD-018 unchanged, untouched this wave.
- **New, needs a decision:** EXIF orientation ignored on image conversion — see above,
  backlogged.
- Minor, backlogged: export metadata (JSON/CSV) doesn't record the source image path
  or library key, widening a pre-existing gap by one mode; one forward-referenced test
  name in CARD-015's System contract (`TestNudge_ReportsFailureAtCap`) that doesn't
  exist until CARD-016 ships — confirm it lands, not a defect in this diff.

## Migrations
- none

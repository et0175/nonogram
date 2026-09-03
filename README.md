# Nonogram Generator

A command-line tool that generates nonogram (picross) puzzles guaranteed to have
**exactly one, purely-logical solution** — the property a random black/white grid
usually lacks, and that hand-designing a puzzle around is tedious to get right. It
sources a solution grid (at random, from a built-in image library of named
shapes — `--mode library --library-key cat` — or from your own picture,
`--mode image --image photo.jpg`), derives its row/column clues, and verifies
uniqueness with a hand-rolled constraint-propagation solver before exporting it.

## Status

Under active development. `nonogram generate` now runs the full pipeline end to end
(source a grid → derive clues → verify uniqueness, auto-regenerating on an ambiguous
or unsolvable candidate up to a bounded retry cap) for both the random and library
grid sources, and exports to disk in json, png, svg, csv and pdf. There is no timeout
on the uniqueness check yet — a large `--size` can abandon the run rather than hang
forever (ADR-0011). See `meta/kanban/board.md` for what's shipped and what's next.

## Usage

```bash
python3.14 -m venv .venv
./.venv/bin/pip install -e '.[dev]'
./.venv/bin/python -m pytest         # run the test suite
./.venv/bin/nonogram --help          # inspect the CLI surface
```

### Grid extent — `--size`

A puzzle's grid is a rectangle, and one flag says how big it is:

```bash
nonogram generate --size 30x20     # 30 wide by 20 tall, exactly
nonogram generate --size 20        # 20 on the LONGER side; the other follows the source
```

`--size WxH` gives the two sides separately, width first, and the picture is
fitted to that shape. A bare `--size N` leaves the shape unsaid, so **N is the
grid's longer side and the other side is taken from the source's own
proportions** — `round(N * short/long)`:

| source | a bare `--size 25` gives |
| --- | --- |
| random (no shape of its own) | 25x25 |
| library (every built-in template is square today) | 25x25 |
| a 563x980 portrait silhouette | 14x25 |
| a 330x462 portrait silhouette | 18x25 |

For an uploaded picture the proportions read are the **drawing's**, not the
file's: blank margin is trimmed off first, so a portrait cat centred on a square
sheet gets a portrait grid and keeps its ears. Squaring it instead is a claim
about your picture that the tool has no basis for, and on this project's own 25
test pictures it discarded 24% of the average one. Ask for `--size 25x25` when
you actually want a square.

The derived side is never allowed below 10 cells, and that is the one place the
grid stops following the picture. Past `N/5 : 1` — 2:1 at `--size 10`, 4:1 at
`--size 20`, 6:1 at `--size 30` — holding it at 10 would throw away more than
half the picture, so the request is refused and the message names the smallest
`--size N` that would take it. Which has a genuinely counter-intuitive
consequence, so it is worth saying plainly: **asking for a smaller puzzle can
refuse a picture that a bigger one accepts.**

The separator is a lower-case `x`, not `*`: in zsh —
where this was reproduced — `--size 30*20` fails with `no matches found` before
the process starts, and if a file happens to match the glob it silently expands
to that filename instead. Other shells differ (bash passes an unmatched `30*20`
through literally), which is why the rule is "use `x`" rather than a claim about
what every shell does. **Each side must be 10 to 30 cells inclusive** —
30 is where a printed cell drops under about 6 mm and stops being comfortable to
mark with a pencil. A side outside that range is rejected by the tool with a
message naming which side is at fault, not by the argument parser.

### Generate a puzzle from a short description, and export it as a PDF

"A short description" here means one of the built-in library shapes rather than
free-text — the tool sources a grid from a named silhouette (`cat`, `heart`, `house`,
`moon`), derives its clues, and verifies the puzzle has exactly one solution before
writing it out.

```bash
./.venv/bin/nonogram generate \
  --mode library \
  --library-key cat \
  --size 20 \
  --seed 1 \
  --export pdf \
  --out ./puzzles
```

- `--mode library --library-key <name>` picks the shape. Valid names: `cat`, `heart`,
  `house`, `moon` (an unknown key lists these back to you in the error).
- `--size` is the grid extent, as described above: `30x20` means 30 wide by 20
  tall, a bare `20` means 20 on the longer side with the other derived from the
  source's shape (20x20 for every built-in template, which is square), and each
  side must be 10-30.
- `--seed` makes the run reproducible — the same seed, key and size always produce
  the same puzzle. Omit it for a random draw each time.
- `--export pdf` writes a print-ready PDF; repeat the flag (e.g.
  `--export pdf --export json`) to also get the raw grid/clue data.
- `--out ./puzzles` is the output directory (created if missing); it defaults to the
  current directory.

This writes `puzzles/cat-<difficulty>.pdf` — a printable page with the blank grid and
its row/column clues, ready to solve by hand.

To generate a puzzle from a *random* grid instead of a named shape, drop `--mode
library --library-key ...` and add `--density <percent>` (target share of filled
cells):

```bash
./.venv/bin/nonogram generate --size 20 --density 30 --seed 42 --export pdf --out ./puzzles
```

### Generate a puzzle from your own image

Point `--mode image` at a picture. JPEG and PNG both work (anything Pillow can open).
The image is cropped to its ink bounding box (blank margin is trimmed off first), then
fitted to the grid's shape by a centred crop, resized, dithered (Floyd–Steinberg) and
binarised — then put through the same uniqueness check as every other source.

```bash
./.venv/bin/nonogram generate \
  --mode image \
  --image pictures/wolf1.jpeg \
  --size 20 \
  --export pdf \
  --out ./puzzles
```

- `--image PATH` is the source picture. EXIF rotation is honoured, so a photo taken
  sideways converts the right way up.
- `--seed` does not change the puzzle in image mode — the conversion is deterministic,
  so the same image at the same `--size` always yields the same grid and clues. (It is
  still recorded in the JSON/CSV export, so a run stays reproducible on paper.)
- `--name` is worth adding here: image-sourced puzzles are otherwise named
  `image-<timestamp>`, so `--name wolf` gives you `puzzles/wolf-<difficulty>.pdf`.

**Not every image converts.** A photograph is a fixed input — the tool cannot re-draw
it the way it re-draws a random grid — so when the converted grid's clues turn out to
be ambiguous, it adjusts up to 5 pixels and then stops rather than silently editing
your picture further:

```
nonogram: error: abandoned after 5 pixel-nudge attempts (bound: 5) — the converted
image is not a uniquely-solvable puzzle ...
```

That is a normal outcome (exit code 4), not a crash. **The lever that works is
`--size`** — fewer cells usually means simpler, less ambiguous clues, though which sizes
a given picture converts at is not monotonic. Measured on the images in `pictures/`:

| image | 10 | 12 | 20 | 30 |
|---|---|---|---|---|
| `wolf1.jpeg` | ✓ 10x10 | ✓ 10x12 | ✓ 13x20 | ✓ 20x30 |
| `elephant1.jpg` | ✓ 10x10 | ✓ 11x12 | ✓ 19x20 | ✓ 29x30 |
| `eagle-silhouette1.jpg` | ✗ | ✓ 10x12 | ✗ | ✓ 17x30 |
| `dear1.jpg` | ✓ 10x10 | ✓ 10x12 | ✗ | ✓ 20x30 |
| `frog1.jpeg` | ✓ 10x10 | ✓ 12x10 | ✗ | ✗ |

(Re-measured at `--seed 1` on the current code, with a *bare* `--size`, so each
cell also shows the grid the picture's own shape derived — which is why the
verdicts differ from the square-grid edition of this table. `30` is the largest
grid the tool accepts; an earlier edition listed `35`, which is refused outright.)

So if a picture fails at one size, try another before giving up on it — and note that
smaller is a *usual* fix, not a reliable one: `eagle-silhouette1.jpg` converts at 12
and at 30 but not at 10 or 20, and `dear1.jpg` fails only at 20. High-contrast
silhouettes convert best; a busy photo with fine detail will fail at any size worth
solving.

## Web UI

A browser-based interface to the nonogram generator is available. Start the web server:

```bash
./.venv/bin/nonogram serve
```

The server listens on `http://127.0.0.1:5000` by default. Open that URL in your browser
to access the web UI.

### Features

- **Generate from library shapes** — select from built-in silhouettes (cat, heart, house, moon)
- **Generate from a random grid** — specify size and density
- **Upload your own image** — convert a picture to a nonogram puzzle
- **Preview and download** — view the generated puzzle and export as PDF, PNG, SVG, JSON, or CSV

The web UI runs the same generation pipeline as the CLI, including the uniqueness check
and automatic retry on ambiguous grids. All three source modes (random, library, image)
are supported.

## Documentation

- **[Architecture decisions](meta/architecture/decisions/adr/)** — the ADR log
- **[Kanban board](meta/kanban/board.md)** — current delivery status by card and wave
- **[Wave release notes](meta/releases/)** — what shipped in each completed wave

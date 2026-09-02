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
nonogram generate --size 20        # 20 wide by 20 tall
nonogram generate --size 30x20     # 30 wide by 20 tall
```

`--size N` is the square shorthand; `--size WxH` gives the two sides
separately, width first. The separator is a lower-case `x`, not `*`: in zsh —
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
- `--size` is the grid extent, as described above: `20` means 20x20, `30x20`
  means 30 wide by 20 tall, and each side must be 10-30.
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
The image is resized to the grid, dithered (Floyd–Steinberg), and binarised — then put
through the same uniqueness check as every other source.

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
`--size`, and smaller is usually the fix** — fewer cells means simpler, less ambiguous
clues. Measured on the images in `pictures/`:

| image | 10 | 12 | 20 | 35 |
|---|---|---|---|---|
| `wolf1.jpeg`, `elephant1.jpg`, `eagle-silhouette1.jpg` | ✓ | ✓ | ✓ | ✓ |
| `frog1.jpeg`, `dear1.jpg` | ✓ | ✓ | ✗ | ✗ |

So if a picture fails at 20, try 12 before giving up on it. High-contrast silhouettes
convert best; a busy photo with fine detail will fail at any size worth solving.

## Documentation

- **[Architecture decisions](meta/architecture/decisions/adr/)** — the ADR log
- **[Kanban board](meta/kanban/board.md)** — current delivery status by card and wave
- **[Wave release notes](meta/releases/)** — what shipped in each completed wave

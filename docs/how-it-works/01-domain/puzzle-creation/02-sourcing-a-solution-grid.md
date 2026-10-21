# 02 — Sourcing a solution grid (CAP-001 / COMP-003)

> Scope: `src/nonogram/sourcing/` — `random_grid.py`, `library.py`, `image.py`,
> `templates/`. Plus the extent resolution the orchestrator drives through them.

## Why there are three modes and two dispatch tables

A nonogram is built **backwards**: you start from the picture and derive the
clues, never the other way round. So the first question the pipeline asks is
"where does the solution grid come from?", and CAP-001 answers it three ways —
drawn at random (FR-001/FR-004), taken from a built-in library (FR-002), or
converted from an uploaded picture (FR-003).

`sourcing/__init__.py` does **not** collapse those three behind one signature.
`for_mode(mode)` returns the callable rather than calling it, because the three
modes genuinely do not share a parameter list: random takes a density, library
takes a key, image takes a path. Two things are nevertheless in the same place in
all three signatures — the `(width, height)` extent directly after the mode's own
leading argument (ADR-0022/R1: the pair travels together, no mode is ever handed
one number to square), and the injected `random.Random` last (ADR-0015).

Since FR-023 there is a **second** table beside the first.
`shape_for_mode(mode)` (`sourcing/__init__.py:123`) returns the callable that
reports a mode's *own* shape — `()` for random, `(key,)` for library, `(path,)`
for image. Two tables and not one wider row, because the questions are asked at
different moments with different arguments: a shape is a property of the source
alone, while a grid source takes the extent the shape helped decide.

| Mode | Source callable | Shape reporter |
|---|---|---|
| `random` | `random_grid.generate(width, height, density, rng)` | `random_grid.source_shape()` — a square; it has no shape of its own |
| `library` | `library.generate(key, width, height, rng)` | `library.source_shape(key)` |
| `image` | `image.generate(path, width, height, rng)` | `image.source_shape(path)` |

Both tables raise a plain `ValueError` for an unregistered mode, deliberately not
a `NonogramError`: argparse's `choices=` already refused an unknown `--mode`, so a
bad mode arriving here is a wiring bug inside the pipeline, not user input to be
mapped onto an exit code (`sourcing/__init__.py:107`).

## Extent: what the user said, and what the grid gets

The supported range is defined once, in `src/nonogram/limits.py`:
`MIN_SIZE = 10`, `MAX_SIZE = 30`. The bound is **per side, not per grid** —
a 30×12 grid is as legal as a 12×12 one — and the ceiling is set by print
legibility rather than solver cost (`limits.py:12`, ADR-0022): past about 30 cells
a side the printed cell drops under ~6 mm on a sheet of paper (NFR-005) and stops
being comfortable to mark by hand.

`limits.py` imports nothing, which is why every layer may depend on it. The import
guard puts it in the innermost shared rank alongside `errors.py`
(`tests/test_cli.py:749`).

The orchestrator resolves the extent exactly once per run, before the aggregate
exists (`orchestrator.py:1778`), through a two-branch decision at
`_resolved_extent` (`:1353`):

```python
if (width is None) == (height is None):
    return random_grid.validate_extent(width, height)
shape = sourcing.shape_for_mode(request.mode)(*_shape_arguments(request))
return random_grid.derive_extent(width, height, *shape)
```

- **Both sides stated** (`--size 30x20`) — an explicit extent says everything
  there is to say, so it is range-checked and used as given, and the source's
  shape is **never consulted** (AC-096). That is why an explicit request in image
  mode still decodes its file exactly once.
- **One side stated** (`--size 25`) — a bare N. This is the shape ADR-0022/R4
  introduced and the reason `cli._extent_token` returns `(25, None)` rather than
  `(25, 25)`: deciding what an unstated dimension should be is a domain question
  whose answer depends on the source, which the CLI cannot see.
- **Neither stated** (`--size` omitted) — falls through to the same shared
  validator, with the same message: `grid width must be between 10 and 30
  inclusive, got None`.

### The bare-N rule, and the refusal nobody expects

`random_grid.derive_extent` (`:265`) states the rule in one sentence: **N is the
grid's longer side, and the shorter one is `round(N * short/long)` of the source's
own ratio, floored at `MIN_SIZE` and never capped at the top.**

With N as the longer side the derived side is `<= N <= MAX_SIZE` by construction,
so nothing ever needs clamping at the top — and a top clamp would crop content,
which is the harm this whole line of work exists to prevent.

The bottom clamp is where the refusal lives, and the arithmetic is exact rather
than sampled. Holding the short side at `MIN_SIZE` while the source goes on
getting narrower means the grid stops tracking the source, and past some
elongation the fit discards more than half the picture (CON-012's line). At the
clamp the grid's ratio is `MIN_SIZE : N`, so half-retention against a source of
ratio `short : long` is `2 * N * short >= MIN_SIZE * long` — i.e. the breaking
point is exactly **N/5 : 1**: 2:1 at `--size 10`, 4:1 at `--size 20`, 6:1 at
`--size 30`.

Beyond it the request is refused, not silently clamped, as
`SizeTooSmallForSource`. The message carries the counter-intuitive remedy
explicitly (`random_grid.py:347`):

> "Ask for `--size {smallest}` or larger — counter-intuitively, a LARGER puzzle
> accepts a picture that a smaller one refuses, because its shorter side has
> further to fall before it reaches the 10-cell floor. Cropping the picture is
> not what fixes this."

`SizeTooSmallForSource` subclasses `SizeOutOfRange`, not `ImageNeedsManualCrop`,
and `errors.py:49` argues both halves of that: it *is* the requested size that is
wrong, and the remedy is emphatically not a manual crop. Inheriting also means the
CLI's exit-code table needed no new row — `exit_code_for`'s MRO walk finds
`INVALID_INPUT` through the base class.

`_smallest_workable_size` (`:242`) finds the remedy by **searching**
`MIN_SIZE..MAX_SIZE` with the same two helpers the real derivation uses, rather
than solving algebraically, on the stated grounds that the closed form
`ceil(MIN_SIZE * long / (2 * short))` "is one rearrangement away from being subtly
wrong at the boundary, and the search is obviously right."

## Random mode: an exact count, then a shuffle

`random_grid.generate` (`:420`) is four lines of mechanism:

```python
cells = width * height
filled = filled_target(width, height, density)
flat = [True] * filled + [False] * (cells - filled)
rng.shuffle(flat)
return [flat[offset : offset + width] for offset in range(0, cells, width)]
```

The filled total is fixed **before** any draw, so the only density error is the
rounding in `filled_target` = `round(width * height * density / 100)`. That is why
ADR-0003's `DENSITY_TOLERANCE_POINTS = 3` holds **by construction** rather than by
rejection: at the smallest supported grid, 10×10, one cell is one percentage
point, and the bound is looser than the error can be at every supported extent.

`random_grid.py:98` is explicit that nothing in the pipeline checks the tolerance
and nothing needs to — "CARD-005's regenerate loop discards candidates for
ambiguity alone and never looks at density." The constant is exported as the
sampler's *contract*, asserted from `tests/test_sourcing_random.py`, so ADR-0003's
promise is checked somewhere rather than merely asserted in a comment. The file
records that an earlier version of that very comment claimed the loop "is expected
to read it", and that the loop never has.

Density is validated at `1..99`, not `0..100` (`MIN_DENSITY = 1`,
`MAX_DENSITY = 99`, `random_grid.py:92`). ADR-0027 refuses both degenerate ends,
and the comment above the constants records why it has to be refused *here*: an
all-empty grid has exactly one solution, so every check downstream passes it and
the user is handed a blank page. "A rule stated in one place cannot rot into a
promise nobody keeps."

Both validations run **before anything is drawn**, so a rejected request consumes
no randomness: two invalid calls followed by a valid one produce the same grid a
single valid call would (`random_grid.py:443`).

## Library mode: one template, a jittered boundary

Four keys ship: `cat`, `heart`, `house`, `moon` — `library._TEMPLATES`
(`library.py:197`), and `KEYS` is derived from that dict so the list exists once.
`--library-key` deliberately carries **no** argparse `choices=`: key membership is
a domain rule (AC-006), so an unknown key must reach `template_for` and come back
as `UnknownLibraryImage`, not as a usage error.

Each template is a `TEMPLATE_EDGE = 16` cell square of ASCII art in its own module
under `sourcing/templates/`, `#` filled and `.` empty. Those are `.py` files
rather than `.txt`, and `templates/__init__.py` records the measurement behind
that: `pyproject.toml` declares no `package-data` for this directory and there is
no `MANIFEST.in`, so setuptools puts the `.py` files of a discovered package into
the wheel and drops every other extension — verified by building a wheel with a
probe `.txt` and finding only `__init__.py` inside it.

Rescaling is exact-integer, not a resampling library. `coverage` (`library.py:301`)
returns `(numerators, denominator)` where `numerators[row][col] / denominator` is
the fraction of the template area that target cell maps onto, integers throughout
because "whether a cell is *exactly* full or empty is the one judgement no
rounding may blur." `render` then fills a cell when its coverage reaches a
threshold.

That threshold is the one thing library mode draws from the rng
(`library.py:413`): `rng.uniform(MIN_EDGE_THRESHOLD, MAX_EDGE_THRESHOLD)` with the
band `(0.35, 0.65)`. Both ends are strictly inside `(0, 1)`, which guarantees a
fully covered cell is always filled and an untouched one always empty whatever the
draw — **only the boundary moves**. That is what gives POL-001 something to retry
with in library mode: "a different tie-break, same template". `CANONICAL_THRESHOLD
= 0.5` is the unjittered reference a caller renders against when it wants the
shape without the jitter.

## Image mode: the ink box decides, and the box is judged before it is applied

`image.generate` (`:923`) is a fixed order, and `:973` states that the order is
ADR-0022's rather than a local choice:

```
validate_extent → load_greyscale → ink_bounding_box → aspect guard
                → trim → binarize → to_grid
```

Two things in it are load-bearing:

- **The box is computed and judged before it is applied.** Finding a bounding box
  reads pixels and writes nothing, so a refused request is refused with *no* crop
  of any kind having run — not the trim, not the aspect crop, not the resize, not
  the dither. That is EC-007's guarantee, and guarding after the trim had been
  applied would break it.
- **The extent judged is the ink box, never the file** (CON-012, ADR-0022/R3 as
  revised 2026-09-01). Blank margin is not the user's picture, and measuring it
  "misstated what survives the crop by up to 45 points on this project's own
  corpus" (`image.py:984`).

`INK_THRESHOLD = 128` is what counts as ink: a greyscale value *strictly below* it
(`image.py:249`). A non-square request is served by **cropping** the source to that
aspect ratio, never by stretching it (ADR-0022/R3). More than a 2× ratio
difference — which would discard more than half the picture — is refused as
`ImageNeedsManualCrop`, named for what the user has to do rather than for where it
was raised, and deliberately **not** a subclass of `UnreadableImage` because "the
file read perfectly, and telling the user their picture is unreadable when it is
merely the wrong shape sends them to fix the wrong thing" (`errors.py:82`).

`rng` is accepted for the mode table's uniform calling convention and
**deliberately not drawn from** (`image.py:949`): the conversion of a given file at
a given extent is fully determined, and jittering it would hand the user back a
different picture per seed. This is the reason image mode has no regenerate loop
at all — see [04-uniqueness-and-recovery.md](04-uniqueness-and-recovery.md).

### Which way a picture becomes black and white (FR-027)

Two paths, named as boundary strings rather than an enum because the value is
recorded on the aggregate and exported (`image.py:251`): `THRESHOLD = "threshold"`
and `DITHER = "dither"`.

`DEFAULT_BINARISATION` (`image.py:300`) is the switch, and it has three states —
pinned `DITHER`, pinned `THRESHOLD`, or `None` meaning "ask
`classify_binarisation` per picture", which is what ADR-0026 and ADR-0028 together
describe. The comment records that it was **flipped to `None` on 2026-09-17 by the
owner** after a visual gate of 25 pictures rendered both ways at 25×25, and that
the flip was made conditional on the degenerate-ink guard below it. The constant is
pinned rather than defaulted because "a binarisation change alters every converted
picture and the owner validates image work by eye, not by test."

The classifier reads a mid-tone share. `MIDTONE_BAND = (64, 191)` — the quarter
and three-quarter points of the 8-bit range, and `image.py:259` says outright they
were "chosen for being obvious rather than measured". A picture with at least
`MIDTONE_SHARE_THRESHOLD = 0.10` of its pixels inside the band is treated as
genuinely greyscale and dithered; one mostly outside it is two-toned (a
silhouette, a logo, line art) and has a contour worth thresholding. **That 0.10 is
flagged provisional in the source**: "0.10 is a guess; CARD-079 records the
measured share of every corpus picture in its Worktree notes so the owner can set
this on data rather than on the guess."

`USABLE_INK_SHARE = (0.05, 0.95)` is the guard the owner attached to ADR-0026's
acceptance, and it is the best-measured constant in the module (`image.py:302`).
The failure it prevents is specific: a coverage threshold keeps *filled areas*,
and line art has none — every stroke thinner than a cell averages to more paper
than ink and is erased, producing not a bad puzzle but an **empty** one, whose
clues have exactly one solution, so every check downstream passes it and the user
gets a blank page. Under the threshold path `cat_Mouse.png` converts at 1.0–2.7%
ink at every size, while the emptiest *legitimate* conversion on hand,
`tests/fixtures/landscape.png`, is 9.0%. The floor is taken from the narrower gap
[2.7%, 9.0%] rather than the corpus gap [2.7%, 18.0%], because the corpus
midpoint (10%) would have bounced `landscape.png` for no reason — "found by a test,
which is the whole argument for having fixtures that are not corpus pictures."

The 0.95 ceiling is **untriggered by anything on hand** (the densest conversion is
82.0%) and the source says so: it is there because "all black" is the same defect
as "all white", the same symmetry ADR-0027 applies to density.

## Bounds and honest gaps

- `MIDTONE_SHARE_THRESHOLD = 0.10` is explicitly a guess owed a calibration
  (`image.py:271`). Nothing in the code treats it as measured.
- `sourcing/templates/` contains `dolphin.py` and `dog_in_house.py`, which are
  **not** registered in `library._TEMPLATES` and therefore not reachable through
  any `--library-key`. Adding a shape is two edits by decision
  (`templates/__init__.py`): drop the module and add the registry row, because
  "the registry is a literal dict of explicit imports, which is what makes the
  available keys knowable by reading the source rather than by running it."
  These two have had only the first edit.
- `random_grid.generate`'s own `Args` docstring still says density is `0..100`
  (`random_grid.py:110`) while `validate_density` enforces 1..99. The code is the
  authority; the docstring predates ADR-0027.

## Related

- [01-the-layered-pipeline.md](01-the-layered-pipeline.md) · [04-uniqueness-and-recovery.md](04-uniqueness-and-recovery.md)
- ADRs: [ADR-0003](../../../../meta/architecture/decisions/adr/0003-random-density-tolerance.md) · [ADR-0022](../../../../meta/architecture/decisions/adr/0022-grid-extent-and-size-range.md) · [ADR-0026](../../../../meta/architecture/decisions/adr/0026-silhouette-binarisation-threshold.md) · [ADR-0027](../../../../meta/architecture/decisions/adr/0027-refuse-degenerate-density.md) · [ADR-0028](../../../../meta/architecture/decisions/adr/0028-greyscale-input-recognition.md)

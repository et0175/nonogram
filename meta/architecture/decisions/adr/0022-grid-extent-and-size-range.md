# ADR-0022: Grid extent is a width/height pair, and each side is 10..30

**Status:** Accepted (revised 2026-09-01, twice)
**Date:** 2026-08-31
**Deciders:** Puzzle Creator (project owner)
**Revised:** 2026-09-01
**Migration:** rewrite
**Pattern:** —
**API-Posture:** no-http

## Context

Two things were true of every grid this tool has produced, and both were
assumptions rather than decisions.

**Grids were square.** `GenerationRequest` carried one integer, `size`, and
every source mode built an `n x n` grid from it. Nothing in the domain required
this. Verified empirically before writing this ADR: `clues.compute_clues`
already returns independent `rows` and `columns`, and `solver.solve(row_clues,
column_clues)` never assumed they were the same length — a 3x5 grid encodes
correct clues and an 8x14 grid solves uniquely and round-trips, today, with no
change. `export/layout.py` likewise derives its dimensions from the clue sets
rather than taking a size parameter (see its module docstring). Squareness was
enforced in exactly five narrow places: `random_grid.validate_size` and
`generate`, `library.render`'s `range(size)` x `range(size)`, `image.binarize`'s
resize to `(size, size)`, the CLI's `--size`, and the export metadata's single
`size` integer.

The cost of the assumption is concentrated in image sourcing, and it is
substantial. `image.square_crop_box` takes the largest **centred square** of the
source and discards the rest, so a portrait silhouette loses its top and bottom
before the solver ever sees it. Measured across this project's own test
pictures: `eagle-silhouette1.jpg` is 563x980, of which the square crop keeps
**57%** — the eagle's head and feet are what get thrown away. Most of the
collection is portrait (aspect ratios 0.57 to 0.77), so the square crop is
currently discarding 23-43% of nearly every silhouette in it. Fitting the same
eagle to a 15x30 grid keeps **87%**.

**The supported range was 10..50 per side**, set in ADR-0003/FR-001 when the
target was "a grid the solver can handle" rather than "a puzzle a person can
print and mark with a pencil". The print evidence now says 50 is far past
useful. `docs/cell_size.md` records the comfortable printed cell size per grid,
and it stops at 30 (6.5 mm); beyond that a cell is under 6 mm and a pencil mark
stops being meaningful. The two ends of the range were chosen against different
criteria, and the print criterion is the binding one for this tool's actual use.

## Decision

**Grid extent is a `(width, height)` pair throughout.** `GenerationRequest`,
all three source modes, and the export metadata carry both dimensions. The
solver and the clue encoder are unchanged, because they were never square-bound.

**The CLI expresses the pair through the existing `--size` flag**: `--size 30`
means 30x30, `--size 30x20` means 30 wide by 20 tall. One flag, not two, and
`--size N` keeps working exactly as before, so no existing script or documented
example breaks. Parsing the `NxM` form is an argparse-level concern; the range
and ratio rules are validated inward as pure domain functions, per ADR-0010.

**`x` is the separator, not `*`.** This was tested rather than assumed: in zsh —
the project owner's shell — `--size 30*20` fails with `zsh: no matches found`
before the process starts, and if a file happens to match the glob it silently
expands to that filename instead. `x` is also the conventional separator for
extents (screen resolutions, ImageMagick).

**Each side is 10..30 inclusive. `MAX_SIZE` becomes 30 project-wide**, for
every source mode. This supersedes FR-001's 10x10..50x50 range (FR-019
replaces it) and narrows NFR-001's performance ceiling from 50x50 to 30x30.

**The grid drives the picture, not the reverse.** A user asks for a grid shape;
an uploaded image is fitted to it by taking the largest centred crop *having the
grid's aspect ratio* and resizing that to `width x height`. `square_crop_box`
becomes the `width == height` special case of a general crop box, so the
existing crop-not-stretch, crop-not-letterbox policy is generalized rather than
replaced. That policy's own argument gets stronger for rectangles: the module
docstring rejects letterboxing partly because a blank row "is a `0` clue and a
free line for the solver", which is exactly as true of a padded rectangle.

**A request whose grid aspect ratio differs from the source image's by more
than 2x is refused**, with an error telling the user to crop the picture
themselves first. The centred crop retains
`min(r_src, r_tgt) / max(r_src, r_tgt)` of the source, where `r = width /
height`, so "discards more than half the image" is exactly "the ratios differ
by more than 2x". The boundary is inclusive: a square source into a 30x15 grid
retains exactly 50% and is accepted.

**The extent that comparison measures is the picture's INK BOUNDING BOX, not
the file as decoded** (revision 2026-09-01, resolving DEC-025). Once FR-022
trims blank margin before the fit, "the source's aspect ratio" has two possible
readings, and only one of them keeps CON-012 true. CON-012 promises never to
silently discard more than half *the user's picture*; blank margin is not the
user's picture, so measuring the untrimmed file measures the wrong thing.
Measured over the 25-image corpus at a 20x20 grid: on **15 of the 25** the
untrimmed reading overstates what survives the crop, worst at `img_2.png` and
`img_3.png` where it reports 100% retained while 55% of the actual content
survives — a 45-point misstatement, five points above the threshold the rule
exists to enforce. It errs both ways rather than conservatively: on
`cat_Mouse.png` and `cat_dog.png` the untrimmed reading is needlessly
pessimistic (67% claimed against 73% real), so it is not a safe approximation,
merely an inaccurate one.

**The guard measures the bounding box without applying it.** The order is
compute the ink box, judge the request on that box's dimensions, and only then
crop. Computing a bounding box reads pixels but writes nothing and discards
nothing, so EC-007's guarantee — refused *before any cropping, dithering or
solver work runs* — remains literally true, and the trim itself never runs for
a refused request. This ordering is the decision, not an implementation detail:
guarding after the trim had been applied would break EC-007 for the third time
in a week.

**"The grid drives the picture" holds for a FULLY SPECIFIED request; a bare
`--size N` is completed by the source** (revision 2026-09-01, second of the day,
resolving DEC-028). This narrows the principle above rather than reversing it.
`--size 30x20` still means exactly 30 by 20 and the picture is fitted to it —
the grid drives, as before. But `--size 30` leaves the second dimension
*unstated*, and the question is what fills the gap. Until now the answer was an
implicit "assume square", which is not a neutral default: it is a shape claim
about the user's picture that the tool has no basis for. The source's own shape
is the better answer, because the source is the only thing in the request that
actually knows.

So a bare N is the grid's **longer** side, and the shorter side is
`round(N * short/long)` of the source's own ratio (FR-023) — image mode uses
FR-022's ink bounding box, library mode the template's ratio, and random mode,
having no shape of its own, stays square. Measured over the committed 25-image
corpus at N=25: mean retained content rises from **76% to 99%**, and the number
of pictures keeping under 90% falls from **20 of 25 to zero**.

**Why the longer side, and not the shorter or the area.** This is the load-bearing
argument and it is structural, not aesthetic: with N as the longer side, the
derived side is `<= N <= MAX_SIZE` **by construction**, so nothing ever needs
clamping at the top. Reading N as the shorter side, or as an area budget, lets
the other dimension run past MAX_SIZE and require a top clamp — and a top clamp
crops content, which is the precise harm this whole line of work exists to
prevent. An earlier draft of this decision argued for the longer side on the
grounds that it would make N determine the printed cell size; **that argument was
measured and is false** — with the page turned to match the grid, a 20x10 prints
9.74mm and a 20x20 prints 6.43mm at the same N, because the short side still
consumes page through the clue gutter. It is retracted here so it cannot be
inherited by anything downstream; the structural argument is the one that holds.

**The bottom clamp is the one place the source cannot be followed, and it
refuses rather than lies.** The derived side is clamped to `MIN_SIZE` (10) at the
bottom, so the grid stops tracking the source at `N:10`. Combined with the >2x
rule this yields an exact ceiling: the most elongated source a given N can
accept is `N/5 : 1` — 2:1 at `--size 10`, 4:1 at `--size 20`, 6:1 at `--size 30`.
A consequence worth stating plainly because it is counter-intuitive: **asking for
a smaller puzzle refuses pictures a larger one would accept.** Such a request is
refused rather than silently clamped, and the message names the smallest `--size N`
that would accommodate the source unclamped — because FR-021's existing advice
("crop the picture yourself") is the wrong remedy here: cropping is not what fixes
it.

## Alternatives considered

### Leave "the grid drives the picture" unqualified (rejected 2026-09-01)
Keep the principle as written and let a bare `--size N` go on meaning N x N, with
shape-fitting available only through an explicit flag or an explicit `NxM`.
Nothing to revise, no sequencing pressure on CARD-027, and the rule stays a single
sentence. Rejected because "assume square" is not the neutral default it looks
like — it is an unfounded claim about the user's picture, made by the component
least equipped to make it, and it costs a measured 24 percentage points of the
picture on this project's own corpus. The principle was never really about
squareness; it was about the user's stated intent taking precedence over the
file's. A dimension the user did not state is not intent, and treating it as such
is what this revision corrects.

### Judge the untrimmed, as-decoded source extent (rejected 2026-09-01)
Leave the guard exactly where it sits today and let FR-022's trim run
afterward, only for requests already accepted. Nothing about CON-012, EC-007 or
the guard's position changes, and — the one real advantage — the cheap
pre-decode refusal that CARD-026 built is preserved: a clearly mismatched
request can still be rejected from the file header alone, without decoding.
Rejected because it makes the rule's own message false. The guard would report
what fraction of a *file* survives while the user cares about, and CON-012
protects, the fraction of a *picture* — a gap of up to 45 points on this
project's corpus, with `img_2.png` accepted at a claimed 100% while keeping 55%
of its content. A rule whose stated justification stops describing what it
measures is worse than a slower rule.

### Guard twice — early on the file, again on the trimmed box (rejected 2026-09-01)
Keep the fast header-only rejection for cases it can already prove, then
re-check against the ink box after decoding. It genuinely gets both properties.
Rejected on operational cost: CARD-026 made this guard two-stage and cycle 1's
critical finding (F-002) was precisely a fail-open hole between those stages,
where the header extent was judged while the conversion cropped a different
one. A third stage adds another such seam to the one mechanism in this codebase
that has already produced a fail-open defect, to save a decode on a local
single-puzzle CLI run that takes ~2s end to end.

### Two flags, `--width` and `--height`
Explicit and unambiguous, and it avoids putting any parsing in the CLI layer.
Rejected because it makes the common case (a square) two flags instead of one,
and because `--size` would then either linger as a third way to say the same
thing or break every existing script and README example. The single-flag form
keeps the square case unchanged and costs one small, well-tested parser.

### Keep `--size` square-only and add a separate `--shape` or `--aspect`
Would have avoided touching `--size`'s contract at all. Rejected as indirection:
the user is choosing an extent, and naming it twice (a size and a shape) is
harder to explain than naming it once.

### Bound total cells rather than each side
Constraining area (say 100..900 cells) targets solver cost more directly, which
is what a limit protecting NFR-001 arguably ought to do. Rejected because it is
not predictable from the flag a user types — `--size 45x20` being legal while
`--size 31x31` is not would be surprising — and because the binding constraint
here is print legibility per side, not total work.

### Cap the aspect ratio as well as each side
Considered as a way to prevent extreme strips (a 30x10 grid solves quite
differently from a 22x22 of similar area). Rejected as a *dimension* rule: with
the >2x source-vs-grid refusal already in place, an extreme grid can only be
requested deliberately and with a matching picture, which is a legitimate thing
to want. Revisit if difficulty scoring turns out to mis-rank extreme shapes.

### Keep 10..50 and treat 30 as advisory
Rejected because the limit exists to protect something physical. A 50x50 puzzle
at 45% density needs 75 cells across including its clue gutter; at that width
the cell is about 2 mm, which the layout module itself describes as "past the
point where a pencil mark is meaningless". A range whose upper half produces
unprintable output is not a range, it is a trap.

## Consequences

### Positive

- Silhouettes stop being mutilated by the square crop. On this project's own
  pictures the retained fraction goes from 57-77% to 87-100% when the grid is
  allowed to match the source's shape.
- The solver, the clue encoder and the export geometry need no change, which is
  unusual for a change to a core domain type and is the reason this is
  affordable at all.
- `--size N` is untouched, so every existing invocation, script and README
  example keeps working.
- The refusal rule turns a silent quality loss into a message. Today a badly
  shaped source is quietly cropped to a third of itself and the user finds out
  by looking at the puzzle.
- (2026-09-01, DEC-028) A bare `--size N` stops making an unfounded claim about
  the user's picture. On the 25-image corpus the mean retained content goes from
  76% to 99%, and no picture keeps under 90%.
- (2026-09-01, DEC-028) The >2x refusal becomes structurally unreachable on the
  derived path, since the grid matches the source's ratio by construction. It
  survives for explicit `NxM` — where the user genuinely asked for a shape the
  picture does not have — and for sources past the `N/5 : 1` ceiling.
- (2026-09-01) The refusal message becomes true rather than nominal. The
  percentage it quotes is now the fraction of the user's actual picture that
  would survive, which is what CON-012 always claimed to protect and what the
  user can verify by looking at the result.

### Negative

- (2026-09-01, DEC-028) `--size N` changes meaning for image sources: a script
  that passed `--size 20` and relied on getting 20x20 now gets a shape derived
  from its picture. Random and library modes are unaffected in practice (all four
  registered templates are 16x16), and `--size 20x20` still forces a square, but
  this is a behaviour change and not merely an addition.
- (2026-09-01, DEC-028) Asking for a smaller puzzle can now refuse a picture that
  a larger one accepts — the `N/5 : 1` ceiling. It is stated in FR-023 and carried
  in the refusal message rather than left for a user to deduce, but it remains a
  genuinely surprising shape of rule.
- (2026-09-01, DEC-028) This is the second revision of this ADR in one day
  (DEC-025 moved the aspect guard onto the ink bounding box that same morning).
  One ADR absorbing two decisions in a day concentrates review load and makes the
  History section, not the Decision section, the place a reader must go to
  understand the sequence.
- (2026-09-01) The aspect guard can no longer refuse before decoding. A trim
  can move a ratio in either direction, so no sound refusal is derivable from
  the file header alone, and every image request now pays for a full decode
  before it can be rejected. The cheap pre-decode path CARD-026 built for this
  guard is retired by this revision — deliberately, and this is the price of
  the decision.
- (2026-09-01) CON-012's wording and FR-021's statement both have to move with
  this: "the uploaded source image's" aspect ratio becomes the ink bounding
  box's. EC-007 does NOT need amending under the chosen ordering, which is why
  the ordering is part of the decision.

- **This breaks the AC-038 deadline fixture, and the replacement must be
  measured rather than assumed.** `tests/test_timeout.py` uses `size=50` in four
  places as its "the solver cannot finish in time" case. At `MAX_SIZE = 30`
  those become invalid requests and fail with `SizeOutOfRange` *before the
  solver runs*, so the deadline mechanism would appear broken when it is not.
  AC-038 is superseded by AC-084, which requires a 30x30 request "using a seed
  measured to drive the solver past the deadline". Finding that seed is
  implementation work with a measurement in it, not a substitution. CARD-006's
  review already flagged this fixture as fragile and CARD-018 re-checked it;
  this is its third disturbance.
- `tests/test_sourcing_image.py:312` asserts `random_grid.MAX_SIZE == 50`
  directly and must change with the constant.
- AC-003's boundary case ("60x60 rejected") stops being the boundary. It is
  superseded by AC-069 (31x30 rejected), because a test that rejects 60 while
  the limit is 30 no longer tests the edge.
- The export metadata's single `size` integer becomes a pair, which is a **file
  format change**. FR-012's whole point is that a JSON/CSV export reconstructs
  the puzzle exactly, so the compatibility question — whether older exports stay
  readable, and whether `size` survives as an alias for square puzzles — is real
  and is deliberately left to its own decision rather than settled here.
- Grids from 31 to 50 cells per side are no longer expressible. Nothing in the
  repository's history suggests they were used, but the capability is gone.

### Neutral

- The 2x ratio threshold is a judgement, not a derivation. It was chosen as
  "the crop may not discard more than half the picture" and then checked against
  the project's real images: it admits every sensible pairing of those pictures
  with a grid and refuses `30x10` for all of them except the one genuinely
  landscape image. If it proves wrong in use it can move without disturbing
  anything else in this ADR.
- Dropping to 30 shrinks the solver's worst case considerably, which is
  favourable for NFR-001 but is a side effect rather than a motivation.

## Rules
```yaml
- id: ADR-0022/R1
  statement: Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from one integer.
  scope: {code: ["src/nonogram/**"]}
  check: {kind: review-lens}
  severity: mandatory
- id: ADR-0022/R2
  statement: Each grid side is validated to 10..30 inclusive, as a pure domain function inward of the CLI adapter, for every source mode. The CLI parses the --size NxM form but never enforces the range itself.
  scope: {code: ["src/nonogram/sourcing/**", "src/nonogram/cli.py"]}
  check: {kind: test, ref: TestValidateExtent_RejectsSideAboveThirty}
  severity: mandatory
- id: ADR-0022/R4
  statement: A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the other side from the source's own aspect ratio, clamped to MIN_SIZE at the bottom only and never at the top. A source whose ratio exceeds N/5 is refused with a message naming the smallest N that would accommodate it, never silently clamped.
  scope: {code: ["src/nonogram/cli.py", "src/nonogram/orchestrator.py", "src/nonogram/sourcing/**"]}
  check: {kind: test, ref: PropertyTest_BareSize_DerivesShorterSideFromSourceShape}
  severity: mandatory
- id: ADR-0022/R3
  statement: An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by more than 2x from the source's INK BOUNDING BOX ratio — not from its as-decoded file ratio — is refused rather than cropped. The bounding box is computed and judged before any crop is applied, so a refused request is still refused before any cropping runs.
  scope: {code: ["src/nonogram/sourcing/image.py"]}
  check: {kind: test, ref: TestFitImage_RefusesRatioMismatchBeyondTwice}
  severity: mandatory
```

## References

- Supersedes the 10x10..50x50 range in FR-001 (superseded by FR-019) and
  narrows NFR-001's ceiling from 50x50 to 30x30 (AC-038 superseded by AC-084).
- Requirements: FR-018, FR-019, FR-020, FR-021, NFR-005, CON-011, CON-012,
  CON-013, EC-005..EC-008, AC-059..AC-084.
- Stories: US-016, US-017, US-018, US-019.
- `docs/cell_size.md` — the printed cell sizes that make 30 the useful ceiling.
- ADR-0010 (argparse parses, the domain validates) — why `NxM` parsing sits in
  the CLI while the range and ratio rules do not.
- ADR-0012 (`list[list[bool]]` grid boundary type) — unchanged; a rectangle is
  already expressible in it.
- NFR-005 records the print-geometry half of this work and is deliberately a
  separate requirement: it constrains how a grid is *drawn*, not how it is
  *shaped*.

## History

- 2026-08-31 — Accepted. Decided in elicitation with the project owner, with
  four sub-decisions taken in order: one flag rather than two; `x` rather than
  `*` after the glob failure was reproduced in zsh; 30 replacing 50 everywhere
  rather than only for image sourcing; and the >2x refusal rather than a silent
  crop. The empirical claims in Context (solver already rectangle-native, the
  57%-vs-87% eagle measurement, the portrait skew of the test collection) were
  measured during that session rather than assumed.

- 2026-09-01 — Revised — resolves DEC-025. Previous decision: the >2x aspect
  guard measured the source image's as-decoded extent. Reason: FR-022 now trims
  blank margin before the fit, which made "the source's aspect ratio"
  ambiguous, and the as-decoded reading stops measuring what CON-012 protects —
  on 15 of the 25 corpus pictures it overstates what survives the crop, by up
  to 45 points (`img_2.png`: 100% claimed, 55% real). The guard now measures
  the ink bounding box, computed before the crop is applied so EC-007's
  refuse-before-cropping guarantee is unaffected. The two rejected readings
  (keep the as-decoded extent; guard twice) are recorded above. Migration stays
  `rewrite`: the merged CARD-026 guard measures the old extent and must be
  brought to this decision by the card that implements FR-022.

- 2026-09-01 (second revision of the day) — Revised — resolves DEC-028. Previous
  decision: a bare `--size N` meant an N x N square for every source mode. Reason:
  "assume square" is not a neutral default but an unfounded shape claim about the
  user's picture, and it cost a measured 24 percentage points of retained content
  on the project's own 25-image corpus (76% square vs 99% derived; 20 of 25
  pictures under 90% vs none). The principle "the grid drives the picture" is
  narrowed, not reversed: it governs a fully specified `--size NxM`, while a bare
  `--size N` is completed from the source's own shape. Also RETRACTS, before it
  could be inherited, the argument that reading N as the longer side would make N
  determine printed cell size — measured false (20x10 prints 9.74mm against
  20x20's 6.43mm at the same N). The reading survives on the structural argument
  instead: only "longer side" guarantees both sides land in range without a top
  clamp, and a top clamp would crop content. Rejected alternative recorded above.
  New rule R4. Migration stays `rewrite`: CARD-027 (FR-018) is `Revision pending`
  and must be built against this reading, not the previous one.

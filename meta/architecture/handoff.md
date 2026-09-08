<!-- decomposed: 2026-08-30 — Increment 4 → CARD-019, CARD-020, CARD-021 (waves 12–14) -->
<!-- decomposed: 2026-08-31 — Increment 5 → CARD-023..CARD-029 (waves 16–19) -->
<!-- decomposed: 2026-09-01 — Increment 6 → CARD-030, CARD-031, CARD-032 (wave 19) -->
<!-- decomposed: 2026-09-01 — Increment 7 → CARD-033, CARD-034 (wave 20); CARD-027 gate cleared -->
# Nonogram Generator — Architecture Handoff

## Summary

- **Requirements:** 17 FR, 3 NFR, 8 CON (1 superseded: CON-001 → CON-007), 3 EC (all traced, 0 validator errors)
- **Domain:** 1 bounded context (CTX-001 Puzzle Creation), 1 aggregate (Puzzle, 3 invariants), 5 capabilities, 14 events, 13 commands, 5 policies, 2 actors
- **Decisions:** 21 ADRs, all Accepted, 0 open
- **C4:** 1 context diagram, 1 container, 8 components

**Platform baseline:**
`stack=Python 3.14 + Pillow + NumPy (ADR-0006, confirmed) · style=layered pipeline package (ADR-0007, confirmed) · runtime=installable pyproject package (ADR-0008, confirmed)`

The web UI delta did **not** reopen this baseline: ADR-0020 chose `http.server` from the
stdlib precisely so no fourth runtime dependency joins it.

## Known gaps (non-blocking)

- 29 WARN / 2 INFO from `architect-validate --phase all` — all expected pre-implementation noise (planned tests with no code yet) except one validator quirk: `EC-001` is flagged for undefined "clue" sameness even though `glossary.yml` TERM-009 now defines the exact relation CON-005/INV-002/EC-001 share — a keyword-matching artifact in the validator, not a real model gap.
- `BCON-0001` (web UI is localhost-only, no auth) is an active **hard** business constraint that no *checked* rule of the model references via `bcon_ref`. `NFR-003` carries the requirement and AC-052/AC-053 verify it, but the validator's `bcon_ref` scan reads CONs, invariants and ADR rules — not NFRs — so the constraint is not yet mechanically discharged. Worth a `check:` on a CON or an ADR rule if it should be gate-enforced rather than test-enforced.
- `FR-014` (nudge-count reporting) was added mid-pipeline via ADR-0004; already linked to CAP-005 and traced.
- `FR-015` (puzzle naming) and `FR-016` (PDF export with answer key) were added after the first synthesis pass via a second delta (ADR-0016/0017/0018 resolve the filename convention, collision handling, and auto-name precision); already linked to CAP-001/CAP-005 and traced.
- `FR-017`/`NFR-003` (local web UI) were added by a third delta on 2026-08-30 (ADR-0019/0020/0021); linked to CAP-001 and traced to the new COMP-008. Increment 4 below is not yet decomposed into cards.
- No design system (`meta/design/`) exists. CON-008 scopes the web UI's v1 to one form page, one POST and one result page with no in-browser preview, so a full `/forge:ui` pass is likely disproportionate — but `decompose` will re-warn on every UI card until one exists.

## Increment plan

Ordered by uncertainty collapsed, not by feature size — the riskiest and most foundational question (is the hand-rolled solver actually correct?) goes first.

### Increment 1: Core generation & solving skeleton

Random sourcing (FR-001, FR-004) → clue derivation (FR-005) → hand-rolled solver with fail-fast uniqueness check (FR-006, ADR-0009) → regenerate-on-failure loop (FR-007) → cooperative deadline/timeout (ADR-0011) → seed/reproducibility (ADR-0015) → minimal JSON export (FR-012, partial).

Components: COMP-001 (CLI Adapter, partial), COMP-002 (Pipeline Orchestrator), COMP-003 (Sourcing, random path only), COMP-004 (Clues), COMP-005 (Solver), COMP-007 (Export, JSON only).

**Checkpoint:** `nonogram generate --mode random --size 10 --seed 42 --export json` produces a valid, uniqueness-confirmed puzzle end-to-end. `PropertyTest_Solver_NeverFalsePositiveUniqueness` (ADR-0014's brute-force oracle) passes on ≥1000 random ≤8x8 grids. A 50x50 request either completes within 30s or fails cleanly with `SolverTimeout` (ADR-0011) — never hangs.
**Collapses:** CON-005 (the one mandatory correctness property), DEC-009/ADR-0009's solver-choice risk validated empirically instead of just argued, INV-002, INV-003 (retry bound), NFR-001's 50x50 timeout risk.
**Rollback:** No persisted state, no point of no return — revert the feature branch.

### Increment 2: Difficulty, naming & full export surface

Difficulty scoring formula (FR-009, ADR-0013) → tier selection and resample loop (FR-008, FR-010, ADR-0005) → remaining export formats (FR-011: PNG/SVG; FR-012: CSV + exact JSON round-trip) → built-in image library sourcing (FR-002 — low risk, reuses the increment-1 pipeline with a different grid source) → puzzle naming (FR-015, ADR-0018) → two-page PDF export with answer key (FR-016, ADR-0006/0016/0017; CON-006 keeps this Pillow-only, reusing the PNG raster path).

Components: COMP-003 (Sourcing, library path added), COMP-006 (Difficulty), COMP-002 (owns the new `name` attribute on AGG-001), COMP-007 (Export, all formats incl. PDF).

**Checkpoint:** Generating at each of Easy/Medium/Hard produces a puzzle whose score falls in that tier's tertile band. All five export formats (PNG/SVG/JSON/CSV/PDF) are produced for one puzzle; decoding the JSON export reproduces the exact original grid and clues (`EC-002`); the PDF has a puzzle page and an answer-key page, headered with name + difficulty, filed as `<name>-<difficulty>.pdf` (auto-suffixed on collision, ADR-0017). Library key `"cat"` produces the expected grid; an unknown key is rejected (AC-006).
**Collapses:** FR-008/009/010's difficulty-formula risk (untested until real puzzles are scored), EC-002 round-trip fidelity, FR-002, FR-015/016's naming and PDF-assembly risk.
**Rollback:** Export, scoring, and naming are additive on top of increment 1 — revert without touching the solver or orchestrator's core generation logic.

### Increment 3: Image upload mode

User image conversion via resize + Floyd-Steinberg dithering (FR-003, ADR-0006) → pixel-nudge recovery loop (FR-013, ADR-0002's 5-attempt cap) → nudge-count reporting at export (FR-014, ADR-0004).

Components: COMP-003 (Sourcing, image path added), COMP-002 (orchestrator's nudge-cap enforcement), COMP-001 (CLI, `--image` flag + nudge-count output line).

**Checkpoint:** A sample photo converted at 20x20 yields a puzzle. When conversion doesn't reach uniqueness immediately, the nudge loop resolves it within 5 attempts or reports failure with a retry-suggestion message (AC-036). When nudges were applied, CLI output states the count (AC-040); when zero nudges were needed, no line is printed (AC-041).
**Collapses:** FR-003/FR-013/FR-014 — the last untested technical risk (dithering quality and nudge-heuristic effectiveness are unproven until real images are run through it).
**Rollback:** Image sourcing is the last additive module — revert without touching random/library modes, the solver, or export.

### Increment 4: Local web UI (second inbound adapter)

_Added 2026-08-30 by the web-UI delta. Increments 1–3 have shipped (waves 1–11); this is the only undelivered increment._

A new component COMP-008 "Web UI Adapter" (`src/nonogram/web/`), sibling to COMP-001 and the second inbound adapter over the *existing* domain (FR-017, CON-007). It serves one form page exposing the same generation options as the CLI (source library key or uploaded image, size, density/difficulty, name override, export formats), one POST endpoint that maps the form onto `orchestrator.GenerationRequest` and calls the pipeline inline, and one result page reporting success plus written file paths, or a structured failure (EC-003). Launched as a `nonogram serve` subcommand under the existing argparse tree (ADR-0008's single console entry point kept). Served by `http.server.ThreadingHTTPServer` bound to `127.0.0.1` with hand-written routing and hand-rolled `email.parser` multipart for the upload path (ADR-0020 — no new dependency; `cgi` is gone as of PEP 594). Synchronous blocking request handling (ADR-0021) — ADR-0011's existing cooperative solver deadline is what bounds it, so no job store, no polling, no streaming.

Components: COMP-008 (new — HTTP concerns only, zero domain logic and zero validation, mirroring `cli.py`'s parsing-only rule), COMP-002 (driven unchanged — `GenerationRequest` is already adapter-agnostic). `tests/test_cli.py`'s structural import guard gains a narrow two-name adapter allowlist (`cli`, `web`) at the same rank (ADR-0019/R1).

**Checkpoint:** `nonogram serve` starts a server reachable at `127.0.0.1` and refusing every other interface (AC-052), requiring no credentials (AC-053). Submitting the form for library key `"cat"` at 20x20/Medium with png+json selected reports success and the written file paths, having run the same pipeline the CLI runs (AC-049). A 60x60 submission is rejected with the same size-range domain error the CLI raises, writing nothing (AC-050). A submission whose candidates exhaust the retry bound reports the abandonment and its reason without hanging or returning an unhandled server error (AC-051).
**Collapses:** FR-017, NFR-003, EC-003, CON-007/CON-008 — plus the one genuinely unproven technical risk in the increment: whether hand-rolled multipart parsing on `email.parser` handles a real browser's image upload correctly, which nothing before this increment has exercised.
**Rollback:** The web adapter is purely additive — no capability module, the orchestrator, or the CLI changes behavior. Revert the branch; the only non-additive edit is the import guard's allowlist, which reverts with it.

### Increment 5: Rectangular grids and print-legible cell sizes

_Added 2026-08-31 by the rectangular-grid delta (US-016..US-019, ADR-0022, ADR-0023). Increment 4 is in flight (CARD-019 merged; CARD-020/021/022 open)._

Grid extent stops being one scalar and becomes a `(width, height)` pair carried through the request, all three source modes, and both structured export formats (FR-018, ADR-0022). Each side narrows to 10..30, replacing the 10..50 range project-wide (FR-019 supersedes FR-001; CON-011). An uploaded silhouette is fitted to the REQUESTED grid shape by a centred crop of the grid's aspect ratio rather than to a square (FR-020) — today's `square_crop_box` becomes the `width == height` case — and a source whose ratio differs from the grid's by more than 2x is refused rather than silently cropped to a third of itself (FR-021, CON-012). Image sourcing is scoped to high-contrast black/white silhouettes for now (CON-013). Separately, printed cell size becomes `min(comfort cap, page fit)` where the cap is `docs/cell_size.md`'s chosen value for the grid's larger dimension (NFR-005, EC-008), replacing today's flat `MAX_CELL_MM = 6.5` that makes a 10x10 and a 25x25 print identically.

Components: COMP-003 (extent + ratio validation, the generalized crop, all three modes), COMP-001 (`--size NxM` parsing only), COMP-007 (the export metadata pair at schema v2 per ADR-0023, and the print-geometry rule), COMP-006 (span constants move with the range; its area-based normalizer is left as an open question), COMP-008 (the web form's size field). COMP-004 and COMP-005 need NO change — verified empirically: an 8x14 grid solves uniquely and round-trips today, and `layout.py` already derives extent from the clue sets rather than a size parameter.

**Checkpoint:** `nonogram generate --mode image --image pictures/eagle-silhouette1.jpg --size 15x30 --export pdf` produces a uniquely-solvable 15x30 puzzle retaining ~87% of the source (against 57% under today's square crop). `--size 30x10` against that same portrait source is REFUSED with the ratio message rather than cropped (AC boundary at exactly 2x accepted, just past it refused). `--size 31x30` is rejected by the range rule. A printed 10x10 measures 9.0mm per cell +/-0.2mm where today it measures 6.52mm, and a 30x30 still fits A4 by falling back to page-fit. Both export formats round-trip a rectangle exactly (EC-002) at schema version 2, and a version-1 document is refused with a version error naming both versions.
**Collapses:** FR-018..FR-021, NFR-005, CON-011..CON-013, EC-005..EC-008, ADR-0022, ADR-0023 — plus the one measurement this increment cannot avoid: a replacement AC-084 deadline fixture inside 30x30 that genuinely exceeds the budget, since AC-038's `size=50` case becomes an invalid request.
**Rollback:** Not purely additive. `MAX_SIZE` narrows (grids 31..50 become unrequestable) and both export schemas bump to version 2, after which version-1 files no longer load. Revert the branch to restore both; no data is rewritten in place, so nothing is lost that the branch did not create.


### Increment 6: Margin trim, image-mode naming, and Unicode PDF headers

_Added 2026-09-01 by the trim/naming delta (US-020, FR-022, AC-090, ADR-0022 and
ADR-0006 both revised). Increment 5 is in flight (CARD-023/025/026 merged;
CARD-024 in progress; CARD-027/028/029 open)._

Three independent pieces of work that share one trigger: making image-sourced
puzzles usable by a person who feeds the tool their own pictures.

**The trim (FR-022, AC-086..089, AC-091).** An uploaded picture is trimmed to its
ink bounding box (ink = a pixel below 128) before FR-020's aspect fit, so the grid
is spent on the picture rather than on its margin. Measured over the committed
25-image corpus at 20x20: 19 of 25 break the at-most-one-blank-line-per-edge rule
today, worst `img_2.png` at 6 lines deep — 300 of its 400 cells are border.
Trimming fixes 17 of those 19. It is **best-effort by explicit decision, not an
invariant**: `dear1.jpg` keeps 2 blank lines and `wolf1.jpeg` keeps 3, and
`wolf1.jpeg` measures 3 deep before trimming too, so no threshold helps it. AC-088
and AC-091 pin those residuals so they cannot drift unnoticed.

**The guard rewrite that comes with it (ADR-0022 revised, Migration: rewrite).**
The >2x aspect refusal must now measure the ink bounding box, not the as-decoded
file. This is not optional cleanup — the merged CARD-026 guard measures the old
extent and is non-conformant the moment FR-022 lands, and on 15 of the 25 corpus
pictures the old reading overstates what survives the crop, by up to 45 points
(`img_2.png`: 100% claimed, 55% real). **The order is prescribed by the ADR**:
compute the ink box, judge the request on its dimensions, and only then crop —
which is what keeps EC-007 ("refused before any cropping, dithering or solver work
runs") literally true. The known cost, already recorded as an ADR consequence: the
pre-decode refusal path CARD-026 built is retired, because a trim can move a ratio
either way and no sound refusal follows from the file header alone.

**Image-mode naming (FR-015, AC-090).** An image-sourced puzzle auto-names from the
source file's stem, exactly as a library-sourced one already names from its key
(AC-043), instead of falling through to `<mode>-<date>-<time>`. `cat.png` exports as
`cat-...` rather than `image-2026-09-01-1240-...`.

**Unicode PDF headers (ADR-0006 revised, Migration: rewrite).** A Unicode TTF ships
as package data — DejaVu Sans, Bitstream Vera-derived licence — so a non-ASCII name
prints instead of rendering as `.notdef` tofu. Verified: Pillow bundles no TTF and
`load_default()` returns an ASCII-only face, so `к`, `о`, `т` and `é` each produce a
bitmap identical to an unassigned codepoint. The runtime dependency set does not
change; ADR-0006/R1 holds the line at non-executable data. This is sequenced WITH the
naming change deliberately: auto-naming from filenames is what turns a Cyrillic
puzzle name from an opt-in edge case into the default path.

**Explicitly NOT in this increment: the `<name>-<WxH>-<difficulty>.pdf` filename
change.** DEC-026 is held open until FR-018/CARD-027 lands the `(width, height)`
pair on the export path — formalizing the filename against today's scalar `size`
would force an immediate rewrite. Resolve DEC-026 and cut that card after CARD-027
merges.

Components: COMP-003 (the trim, and the guard whose subject the ADR revision
changed), COMP-002 (the auto-name rule — `NameContext._auto_name`), COMP-007 (the
bundled font and the PDF header rendering that uses it).

**Checkpoint:** `nonogram generate --mode image --image pictures/img_2.png --size 20
--export pdf` produces a puzzle with at most one blank row/column at each edge, where
today it produces six deep and spends 300 of 400 cells on border; the exported file is
named `img_2-...` rather than `image-<date>-<time>-...`. A picture whose ink box
differs from the requested grid by more than 2x is refused, and the percentage the
message quotes is the fraction of the picture's CONTENT that would survive — verifiable
against `img_2.png`, which the old guard accepted at a claimed 100% while keeping 55%.
Instrumenting `fit_crop_box`/`binarize`/`to_grid` shows none of them is reached for a
refused request, so EC-007 still holds with the trim in the pipeline. `--name кот
--export pdf` prints Cyrillic in the PDF header instead of empty boxes.
**Collapses:** FR-022, AC-086..091, the ADR-0022 and ADR-0006 revisions' `Migration:
rewrite` debt (both leave existing code non-conformant until a card brings it over),
and the standing backlog item "Decision needed: non-ASCII `--name` renders as tofu"
open since 2026-08-29.
**Rollback:** The trim and the guard change are one revert (they must move together —
the guard's new subject only exists once the trim does). Naming and the font are
independently revertible and touch no solver, no export geometry, and no schema. No
point of no return: nothing persists, and no export format version changes.


### Increment 7: What a bare `--size N` means, and which way the page turns

_Added 2026-09-01 by the size-semantics delta (US-021, US-022, FR-023, NFR-006,
ADR-0022 revised twice). Increment 6 is cut but unstarted; CARD-032 shipped._

**The bare-N rule (FR-023, ADR-0022/R4).** `--size 30x20` keeps meaning exactly
30 by 20 — the grid drives and the picture is fitted to it. A bare `--size 30`
sets the grid's LONGER side to 30 and derives the other from the source's own
shape: `round(N * short/long)` over the image's ink bounding box, the library
template's ratio, or — for random, which has no shape — a square. Measured over
the committed 25-image corpus at N=25, mean retained content rises from 76% to
99% and no picture falls under 90%.

The derived side is clamped to MIN_SIZE at the bottom and never at the top —
`N <= MAX_SIZE` already keeps both sides in range, which is the structural reason
"longer side" is the right reading. The bottom clamp produces an exact ceiling:
a source more elongated than `N/5 : 1` cannot be reached by that N, so **asking
for a smaller puzzle refuses pictures a larger one accepts**. Such a request is
refused, and the message names the smallest `--size N` that would work — FR-021's
existing "crop the picture yourself" is the wrong remedy for this case.

**Page orientation (NFR-006).** The sheet turns to match the grid: wide grids
print landscape, tall and square grids portrait. Not separable from the rule
above — a landscape picture at `--size 30` becomes a 30x10 grid, which prints at
**4.49mm per cell on fixed portrait A4 and 6.43mm turned** (its landscape page fit is 6.60mm; NFR-005's cap then binds at 6.5mm). Deriving a shape
without turning the page actively harms exactly the pictures the derivation
exists to help. Measured: 40x20 3.39 -> 5.00mm (+47%), 45x25 3.05 -> 4.40 (+44%),
60x10 2.29 -> 3.39 (+48%); 20x40 keeps portrait (4.91 vs 3.22) and 30x30 keeps it
narrowly (4.40 vs 4.06).

**The correction that rides with it (NFR-005, EC-008).** Printed cell size is not
a declining function of `max(width, height)` — a 40x20 and a 20x40 share
`max() = 40` and print at 3.39mm and 4.91mm. EC-008's property was therefore
ill-posed, not merely imprecise, and is safe today only because every grid is
square. It is restated as a ceiling bound; deliberately NOT as monotonicity or
equality, because even with orientation applied those two measure 5.00mm and
4.91mm.

Components: COMP-001 (`--size` parsing only, ADR-0010), COMP-002 (the derivation
and the refusal), COMP-003 (each mode's source shape), COMP-007 (orientation and
the corrected cell-size rule). COMP-004/COMP-005 unchanged.

**Checkpoint:** `nonogram generate --mode image --image pictures/eagle-silhouette1.jpg
--size 25 --export pdf` produces a 14x25 grid retaining ~97% of the picture where
a square 25x25 retains 57%, and the PDF is portrait. The same command against a
landscape source produces a wide grid on a LANDSCAPE sheet, measurably larger
cells than the portrait equivalent. `--size 25x25` against that same source still
produces a square, unchanged. A 5:1 source at `--size 15` is refused with a
message naming 25 as the smallest size that would take it. `--size 30x20` and
`--size 20x30` both print, and neither is claimed by any test to have the same
cell size as the other.
**Collapses:** FR-023, NFR-006, AC-092..AC-104, EC-009, EC-010, the ADR-0022/R4
migration, and the NFR-005/EC-008 correction — which is the one that must not be
deferred, since EC-008's property cannot be honestly written for rectangles until
it lands.
**Rollback:** The bare-N derivation is additive over Increment 5's `(width,
height)` pair — reverting it restores `--size N` to N x N without touching the
pair. Orientation is independently revertible and touches only export layout. No
schema or format version changes.


## Next steps

Architecture complete. Consider `/forge:roadmap` before the next wave:
- 2 items were deferred to the backlog during brainstorm (color/multi-value nonograms, interactive playable output) — `meta/kanban/backlog.md`
- 3 further items were deferred by the web-UI brainstorm (in-browser preview, progress feedback for long generations, browse/list past puzzles) — the first is formalized as CON-008
- ADR-0019 establishes that a second inbound adapter is a cheap, expected extension of ADR-0007's shape — relevant if any future interface is scored

Run `/forge:kanban decompose` to turn **Increment 5** into cards. Increments 1–3 shipped as CARD-001..CARD-017; Increment 4 is decomposed and in flight as CARD-019..CARD-022. Decompose must leave all of those alone and cut new cards for Increment 5 only.

# CARD-388: A vendored single-file QR encoder and a vector QR the interior can draw — any URL in, a code a phone reads out

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d)
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner decision 2026-11-07 (one QR for the whole book; ADR-0041/R8), which keeps exactly one thing of CARD-210: the encoder. The encoder choice is the owner's ruling of 2026-11-06, "option 2, vendor one file", recorded in ADR-0006/R2 by the architect pass of 2026-11-07. CARD-210's text on the encoder, the test-side reader and the "longest URL at a readable module size" requirement moves here (CARD-210 is retired into CARD-388..393).
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/__init__.py, src/nonogram/admin/book_vector_draw.py, tests/test_vendored_qr_encoder.py, tests/test_qr_vector_draw.py, tests/helpers/qr_reader.py, tests/test_cli.py, meta/architecture/decisions/adr/0006-dependency-baseline.md, src/nonogram/admin/book_qr.py, src/nonogram/admin/_vendor/__init__.py, src/nonogram/admin/_vendor/qrcodegen.py, src/nonogram/admin/_vendor/LICENSE.qrcodegen, src/nonogram/admin/_vendor/PROVENANCE.qrcodegen
<!-- Touches also names the new files this card creates: the vendored encoder itself, its licence text and its provenance record, at a location the author chooses against the import walk (see item 2). They are not listed because the path is the author's decision; the author appends them to this line. src/nonogram/__init__.py is in because the component map is a test-held docstring (item 2). tests/test_cli.py is in only if the layering guard needs a deliberate, named allowance for the vendored file; the author states which. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The owner's 2026-11-07 decision puts exactly one QR code in each book (ADR-0041/R8): the book's landing page on the Play-online page (CARD-390). A printed code that looks right and does not scan is the worst failure this feature has, and nothing in the repository can make a QR code today: `QR_LINK_TEMPLATE` and the checkerboard `_draw_qr_placeholder` are deliberately fake. ADR-0006/R1 closes the runtime dependency set at stdlib + Pillow + NumPy, so the encoder is the one decision the owner already took (2026-11-06): ONE vendored third-party source file with its licence, no entry in `pyproject.toml`. ADR-0006/R2 (written 2026-11-07) states the conditions. This card is the capability and nothing more: any URL in, a vector code out, verified by an independent reader. It draws a QR on no page; CARD-390 places it.

## What to implement

1. **Choose the file and say why before writing code.** The candidate in mind is Project Nayuki's single-file Python QR Code generator (MIT, no dependencies). That is a recollection, NOT verified: read the actual licence text, version and size, and confirm its terms permit vendoring with attribution. If no single file with a permissive licence fits ADR-0006/R2, STOP and report.
2. **Place it where the guards accept it.** `tests/test_cli.py`'s import walk enumerates `src/nonogram/**/*.py` on disk and the `TestComponentMap_*` classes hold `src/nonogram/__init__.py`'s docstring to those modules: a module with no component row fails the suite. So the vendored file needs a row in the canonical map (or a sub-package the walk treats as one component), a flat import list (stdlib only) and no lateral import. The author decides the location, states the reason, and adds the row; CLAUDE.md says that docstring is the only place the component map lives.
3. **Provenance beside the file:** upstream URL, version or commit, licence name, the licence text itself, the sha256 of the vendored bytes. A test holds the bytes to that sha256 (a one-byte edit reds it, and a plant proves it). Then flip `ADR-0006/R2`'s `check:` from `review-lens` to `kind: test` naming that test, in the same delta (the rule says this card owes the flip).
4. **Our thin wrapper** (ours, tested, the only importer of the vendored file): `text -> module matrix` (`tuple[tuple[bool, ...], ...]`, the boundary type the codebase uses for grids). Fix and state the error-correction level and why, the QR version the real address needs, and the longest URL the wrapper accepts at that level. The real address is `https://nonogram.adverax.io/b/<10 hex>` (about 40 characters; the author computes the version, does not recall it).
5. **A vector drawer** in `book_vector_draw.py`: `draw_qr(stream, modules, box)` emits the modules as PDF fill operators in pure black inside a caller-given square, with the 4-module quiet zone INSIDE that square. Merging adjacent modules into runs is allowed; ink must be identical. It refuses a box whose module would fall under the minimum module size this card records (the author measures and states the minimum a phone camera resolves, with the evidence; a refusal, never a smaller code). Positions are the caller's (CARD-390 gets them from `export/layout.py`, ADR-0036/R2); this function chooses none.
6. **The test-side reader.** The acceptance below needs a decoder that is independent of the encoder. Survey and choose: (a) a pure-Python decoder vendored as a TEST helper under the same provenance rules, (b) a decoder already installed in the dev extra, (c) the encoder's published test vectors plus a render-and-sample reader of our own written from the spec, not from the encoder. If the only way is a NEW third-party dev dependency, STOP and ask the owner (their standing rule).

## Acceptance criteria

- **AC-1** (happy, round trip): *Given* a corpus of at least 200 URLs (the real landing shape with random 10-hex slugs, short and long hosts, ports), *when* each is encoded and its modules read back by the independent reader, *then* the decoded text equals the input exactly. The corpus size is asserted inside the test. (test: `TestQrEncoder_RoundTripsThroughAnIndependentReader`)
- **AC-2** (happy, rendered): *Given* a PDF page with the code drawn by `draw_qr` at the size CARD-390 will use, *when* the page is rendered with the repo's existing PDF reading helpers and the pixels are read, *then* the code decodes to the input. The draw call is read from rendered ink, not from the operator list. (test: `TestQrVectorDraw_RenderedCodeDecodes`)
- **AC-3** (guard, pinned bytes): *Given* the vendored file, its licence text and its provenance record, *then* the file's sha256 equals the recorded one, the licence text is present and names the licence the record names; a plant that edits one byte of a copy reds it. (test: `test_the_vendored_bytes_match_their_recorded_sha256`)
- **AC-4** (guard, dependency baseline): *Given* the tree, *then* `pyproject.toml`'s runtime dependencies are still exactly Pillow and NumPy, the vendored file imports only the standard library, and the layering guard and the component-map classes pass. (tests: `test_the_dependency_baseline_is_still_closed`, `tests/test_cli.py` import walk and `TestComponentMap_*`)
- **AC-5** (edge, capacity): *Given* a text longer than the wrapper's stated capacity, *then* a named error is raised and no matrix is returned. (test: `TestQrEncoder_RefusesWhatItCannotCarry`)
- **AC-6** (edge, size): *Given* a box whose module would fall under the recorded minimum, *then* `draw_qr` raises and writes nothing to the stream; *given* a box of exactly the minimum, the code is drawn and decodes. (test: `TestQrVectorDraw_RefusesAModuleTooSmallToRead`)
- **AC-7** (geometry): *Given* any admitted box, *then* every ink rectangle lies inside the box and the quiet zone is at least 4 modules on all four sides. (test: `TestQrVectorDraw_QuietZoneIsInsideTheBox`)
- **AC-8** (registry, the flip this card owes): *Given* this card merged, *then* `ADR-0006/R2` carries `check: {kind: test, ref: <the AC-3 test>}` and the ref resolves to a real `def` (`git grep -w <name> -- tests/`). (review-lens: the architect-validate run, ADR-level DEAD-ref count stays 0)

## Guardrails

- G-1: No new runtime dependency (ADR-0006/R1, R2). `pyproject.toml` changes only by the ONE package-data line that ships the licence and provenance sidecars in a built wheel (`"nonogram.admin._vendor" = ["LICENSE.qrcodegen", "PROVENANCE.qrcodegen"]`), allowed 2026-11-07 after review cycle 1 found the sidecars missing from a built wheel: package data is not a dependency, and the dependency-baseline test must stay green.
- G-2: One vendored file only. A second needs an ADR-0006 revision first.
- G-3: This card places a QR on NO page and changes no page geometry.
- G-4: The matrix never crosses a module boundary except as `tuple[tuple[bool, ...], ...]`; the vendored file's own types do not leak (CLAUDE.md boundary-type rule).
- G-5: Expected values in tests are literals or come from the independent reader, never from the encoder under test.

## System contract

- ADR-0006/R1 — runtime dependencies are exactly stdlib + Pillow + NumPy (check: `test_the_dependency_baseline_is_still_closed`)
- ADR-0006/R2 — one provenance-pinned vendored file (check: review-lens until this card flips it; the flip is AC-8)
- ADR-0036/R2 — only COMP-007's layout functions place things (check: review-lens)
- ADR-0042/R1 — interior pages are PDF operators (check: the rule's own ref in the ADR; this card adds operators only and no image XObject)

## Architecture context

- **ADR:** ADR-0006 (R1, R2), ADR-0041/R8, ADR-0042.
- **FR:** none new; the printed code is specified by CARD-390.
- **Retires from CARD-210:** items 2, 3 and the encoder/decoder paragraphs.

## Worktree notes

- **Encoder chosen and why (item 1).** Project Nayuki's `python/qrcodegen.py`, v1.8.0 (tag object 7ad95ced, commit 720f62bd), fetched 2026-11-07 from `https://raw.githubusercontent.com/nayuki/QR-Code-generator/v1.8.0/python/qrcodegen.py`: 39337 bytes, sha256 `b089855c...dcc84`, MIT, imports `__future__`, `collections`, `itertools`, `re`, `typing` only. Upstream has no separate LICENSE file; `LICENSE.qrcodegen` is the permission notice from the file's own header (which also travels in any copy of the file). Byte-identical to upstream, no patch. Full record: `src/nonogram/admin/_vendor/PROVENANCE.qrcodegen`.
- **Placement (item 2).** `src/nonogram/admin/_vendor/`, inside `admin/`: the import walk's component is the top-level name, so this is COMP-009's own subtree, needs NO new component row, and `tests/test_cli.py` needed no allowance (its walk only reads `nonogram.*` imports; the vendored file has none). `src/nonogram/__init__.py` is unchanged for the same reason. Packaging: the `.py` ships as part of the `nonogram.admin` package; LICENSE/PROVENANCE are not named in `[tool.setuptools.package-data]` because G-1 forbids a `pyproject.toml` change, but the licence notice is inside the shipped `.py` header.
- **Wrapper**: `admin/book_qr.py`. Level Q, byte mode, ASCII only, versions 1..6, `MAX_BYTES = 74`. The real address (40 bytes) is version 4 (33 modules, 41 with the quiet zone: 0.488 mm at 2 cm).
- **Minimum module: `MIN_MODULE_MM = 0.4`** (`book_vector_draw`). A rule of thumb, NOT a phone measurement. Indirect evidence: Apple's CoreImage `CIDetector` (an independent production decoder, run once by hand, not in the suite) decoded the poppler render of a code drawn at exactly 0.4 mm per module for version 4 and version 6 at 300, 150 and 100 dpi (100 dpi is about 1.6 px per module); the suite's own reader decodes at 150 dpi. A scan of a printed proof stays the owner's check.
- **Test-side reader (item 6)**: option (c), `tests/helpers/qr_reader.py`, written from ISO 18004 (versions 1..6), including a Reed-Solomon syndrome check per block so wrong error-correction bytes fail. No decoder is installed (no zbar/OpenCV/ZXing in the venv; `zbarimg` absent) and none was added.
- **ADR-0006/R2 flipped** to `kind: test`, ref `test_the_vendored_bytes_match_their_recorded_sha256`. The ref only resolves once the test file is TRACKED (`git grep`), so `tests/test_check_ref_resolution.py`'s frozen `HONEST_DEAD`/`CENSUS`/`TRACE_TESTS` census values were re-derived at the commit.

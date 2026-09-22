# CARD-105: Check the two metadata algorithms actually agree, by running both

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** test-only card; 6 mutants, 5 caught and 1 proven equivalent
**Branch:** card/105-metadata-parity-by-execution
**Worktree:** ../PythonProject4-CARD-105
**Source:** CARD-034's AC-137, which cannot be checked as written; deferred there
**Idea:** —
**Wave:** 1
**Depends on:** —
**Touches:** tests/test_web_metadata.py only — the re-cut settles on option (b), which needs no change to src/nonogram/web/static/metadata.js
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-22
**Closed:** 2026-09-22
**Actual:** 0.25d
**Merge commit:** 5344de8
**Blocked by:** —

## Why

CARD-034's **AC-137** says the client-side and server-side metadata
calculations are identical for the same image. Nothing checks that. What
`TestAlgorithmParity` does is exercise the **Python** implementation —
`gcd`, `simplifyRatio`, the decimal rounding, the suggestion bounds — and then
grep the JavaScript for function names. Two implementations of one algorithm
are kept in step by review, which is the arrangement every other drift in this
repository has started from.

The numbers matter: `suggest_dimensions` and `suggestDimensions` both
brute-force every `(w, h)` in 10..30, sort by relative ratio error and take
three. Two sorts over 441 candidates agreeing on the top three is exactly the
sort of claim that is true until a tie-break changes.

## What makes this newly worth doing

CARD-034's re-cut said no JS engine is available and none can be, because
ADR-0006's baseline is stdlib + Pillow + NumPy. **That was wrong**, and the
correction is the reason for this card: `test_metadata_js_has_no_syntax_errors`
already shells out to `node --check` and **skips** when node is absent. An
opportunistic tool costs the baseline nothing — nothing requires it to be
there — so the same pattern can run the algorithm, not merely parse it.

## The obstacle, and the choice it forces

`metadata.js` is an IIFE. Its functions are closed over, and it reads
`document.currentScript` and `document.readyState` as it loads, so it cannot
simply be `require`d. Two ways out, and the card should pick one and say why:

- **(a) An export hook in the script.** Three lines at the end of the IIFE —
  `if (typeof module !== "undefined") module.exports = {gcd, simplifyRatio,
  suggestDimensions};` — plus guarding the two `document` reads so loading
  outside a browser does not throw. Honest and small, but it is production code
  carrying a seam that exists only for tests.
- **(b) A harness that evaluates it with a stubbed `document`.** No production
  change, but it has to reach inside the IIFE, which means either transforming
  the source or duplicating the functions — and a test that copies the code it
  is testing proves nothing.

**(a) is recommended.** A named export is a smaller lie than a test that
reconstructs its subject, and the `typeof module` guard is inert in a browser.

## Re-cut 2026-09-22 — the answer is already known: they agree

Checked against `main` at `c244f46`, with node v24.15.0 present. Before
opening this card I ran the comparison it asks for, in the scratchpad, over 13
ratios (1:1, 4:3, 16:9, 3:4, 3:1, 1:3, 563:980, 640:480, 9:16, 2560:1440,
1234:4321, 100:101, 999:1000).

**0 mismatches of 13.** The two implementations return the same three pairs, in
the same order, for every ratio tried — including the pure tie-break cases.

That changes what this card is. It is **not** a bug hunt; it is converting an
agreement currently maintained by review into one maintained by execution. Worth
doing on that basis, and the card should say so rather than implying a defect is
waiting.

**What the card gets right.** `TestAlgorithmParity` really does test Python
against Python — `test_gcd_algorithm_matches_python` asserts `math.gcd` against
hardcoded expectations and never touches the JavaScript at all. And
`test_metadata_js_has_no_syntax_errors` really does shell out to `node --check`
and skip when node is absent, so the opportunistic pattern is established.

**AC-2's case is stronger than the card knew, and it passes.** At 1:1 every
square from 10x10 to 30x30 has a ratio error of exactly 0.0 — a 21-way tie. Both
sides return `[10,10], [11,11], [12,12]`: ascending, insertion order preserved.
That agreement rests on **both sorts being stable**, which is true of Python's
Timsort always and of `Array.prototype.sort` only since **ES2019**. Before that
V8 used an unstable sort for arrays over 10 elements, and this exact case would
have diverged. The test's docstring should say this, because it is the reason
the tie-break agrees rather than an accident.

**A trap the implementer will hit — I hit it.** `simplifyRatio` returns an
**array** `[w, h]`, while `suggestDimensions` reads `metadata.aspectRatio.width`
and `.height`. Production reconciles the two in `extractImageMetadata`, which
destructures the array and builds the object. A harness that passes
`simplifyRatio`'s result straight through gets `undefined`, hence `NaN`
ratio errors, hence a comparator returning `NaN`, hence **insertion order
unchanged** — every ratio then "returns" `[10,10], [10,11], [10,12]` and the
test reports a uniform 13-of-13 mismatch that is entirely the harness's fault.
My first run did exactly that, and the giveaway was that the JS answer was
identical for every input. The harness must construct the metadata object the
way `extractImageMetadata` does.

### The (a)/(b) recommendation is reversed

The card recommends **(a)**, an export hook in the script. Having now built
(b), I think that was wrong:

- **(a) costs more production change than three lines.** The IIFE reads
  `document.currentScript` **at load** to pick up the server-rendered
  `data-min-size`/`data-max-size` (CARD-063's mechanism for not repeating
  `nonogram.limits` in the client). Under node there is no `document`, so the
  load throws before any export runs. Making (a) work means guarding that read
  too — i.e. touching the code path that feeds the live page its grid bounds,
  to serve a test.
- **(b) works, and reads the shipped source.** Locate `function gcd(`,
  `function simplifyRatio(`, `function suggestDimensions(` in the real file and
  brace-match each one out. No copy of the algorithm exists in the test (G-3
  holds — the bytes come from `metadata.js` on every run), no production change
  at all, and if the file is restructured the extractor fails loudly rather than
  silently testing nothing.

**Recommended: (b), with the extractor asserting it found all three functions
and that each body is non-empty**, so "extracted nothing and compared nothing"
cannot pass. ~25 lines, demonstrated working before this card was opened.

## Acceptance criteria

- **AC-1** — for a corpus of aspect ratios (including 1:1, 4:3, 16:9, 3:4 and
  at least one extreme), the JavaScript's three suggestions equal the Python's,
  in order.
- **AC-2** — the comparison covers the tie-break, not only the winner: a ratio
  where several `(w, h)` share a ratio error must agree on which comes first.
- **AC-3** — the test skips, and says why, when node is unavailable; it never
  fails for node's absence, and never silently passes either.
- **AC-4** — if the two disagree, the failure names the ratio and both lists,
  so the report is the bug report.
- **AC-5** *(new, 2026-09-22)* — the harness cannot pass vacuously: it asserts
  it extracted all three functions with non-empty bodies, and the corpus size is
  asserted in the test the way this repo's property corpora are, so the
  comparison cannot silently shrink to nothing.
- **AC-6** *(new, 2026-09-22)* — the 1:1 case is in the corpus explicitly, and
  the test records **why** its 21-way tie agrees: both sorts are stable (ES2019
  for `Array.prototype.sort`). A reader must not have to rediscover that.

## Guardrails

- G-1: node stays undeclared. It is not added to `pyproject.toml`, not
  required by CI, and its absence skips rather than fails (ADR-0006's baseline
  is unchanged — that is the whole point of the opportunistic pattern).
- G-2: Do not change either algorithm to make them agree. A disagreement is a
  finding to report; which one is right is a separate decision.
- G-3: The test must not contain a third copy of the algorithm.
- G-4: Commit only your own files — explicit pathspecs.

## Architecture context

- **FR:** FR-017 (web UI)
- **ADR:** ADR-0006 (the baseline this deliberately does not touch)
- **Components:** COMP-008
- **Trace:** none

## Worktree notes

### Delivered 2026-09-22 — option (b), no production change

`tests/test_web_metadata.py` gains `TestAlgorithmParity_ByExecution`: three
tests, a brace-matching extractor that cuts `gcd`, `simplifyRatio` and
`suggestDimensions` out of the shipped `metadata.js`, and a node harness that
runs them over a 16-ratio corpus. **`src/` is untouched** — the Touches line
is one file.

**Suite: 3,673 passed, 26 skipped, 1 deselected** (3,670 + these 3).

**The two implementations agree** over every ratio in the corpus, including
1:1's 21-way tie. That was known before the card was opened; the value here is
that it is now checked by running both rather than by reading them.

### Mutation check — 6 mutants, 5 caught, 1 proven equivalent

| # | Mutant | Result |
|---|---|---|
| 1 | JS sort reversed (`b[0] - a[0]`) | caught |
| 2 | JS ratio error left unnormalised (`/ targetRatio` dropped) | **survived — equivalent** |
| 3 | JS returns 2 suggestions instead of 3 | caught |
| 4 | `suggestDimensions` renamed in the JS | extractor fails loudly, naming the function |
| 5 | Python sort reversed | caught |
| 6 | Python slice shifted by one | caught |

**Mutant 2 is equivalent, and that is worth stating rather than patching
around.** `ratio_error = |w/h − target| / target` divides every candidate's
error by the same positive constant within a call, which is a monotone
transform: it cannot reorder candidates and it cannot break or create a tie.
Checked exhaustively over all 441 `(w, h)` pairs for 11 ratios — the normalised
and unnormalised orderings are identical in every case. No test comparing the
*returned pairs* can catch that mutant, in either language; it would only be
observable if the error value itself were surfaced or thresholded, which it is
not. Adding a test to kill it would mean asserting something the algorithm does
not promise.

### Why the tie-break agrees, recorded in the test rather than rediscovered

At 1:1 every square from 10x10 to 30x30 scores a ratio error of exactly 0.0, so
the result is decided entirely by what each sort does with equal keys. Both
preserve insertion order — Python's `list.sort` by guarantee, and
`Array.prototype.sort` **since ES2019**; before that V8 used an unstable sort
above 10 elements and this case would have diverged. That is a property of the
two languages, not of the numbers, and neither source file says it, so the test
class docstring does (AC-6). `test_the_tie_break_agrees_where_every_candidate_
ties` asserts the concrete answer as well as the parity, so a future unstable
sort fails with a message that names the cause.

### The harness trap, and why the driver is shaped the way it is

`simplifyRatio` returns an **array**; `suggestDimensions` reads
`.width`/`.height`. Production reconciles them inside `extractImageMetadata`.
A harness that forwards the array directly gets `undefined`, so every ratio
error is `NaN`, so the comparator returns `NaN`, so `sort` leaves the array
alone — and every ratio "returns" `[10,10], [10,11], [10,12]`. That reads as a
total disagreement between the two implementations while being entirely the
harness's fault; I hit it during the card's reconnaissance, and the tell was
that the JavaScript's answer was identical for every input. The driver now
builds the metadata object the way `extractImageMetadata` does, and
`_parity_harness`'s docstring says why.

### Why (b) and not the card's original (a)

(a) would have needed more than the export line: the IIFE reads
`document.currentScript` **at load** for the server-rendered grid bounds
(CARD-063), so under node it throws before any export runs — making it work
means touching the path that feeds the live page its bounds, for a test's
benefit. (b) reads the shipped bytes on every run, so there is no second copy
of the algorithm (G-3) and no production seam (G-1's spirit). Its cost is a
dependency on the file's shape, which mutant 4 shows fails loudly.

`MIN_SIZE`/`MAX_SIZE` are passed into the harness from `nonogram.limits` rather
than hardcoded, so the comparison follows CON-011 if the range ever moves —
the same reason CARD-063 renders them onto the script tag instead of repeating
them in the client.

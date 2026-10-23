# CARD-218 — what sharing a render actually bought, and what it cost in memory (AC-2)

AC-2 asks this card to record "both wall-clocks and the per-file deltas for
every converted file". Two of its clauses are answered here and one is struck;
the review of cycle 1 ruled on the split and the reasoning is at the end.

**The headline, in the unit that is exact: the conversion removes 11 renders of
45, and the first shape of it retained 433.4 MiB of page bitmaps to the end of
the session.** The wall-clock gain is real and smaller than first reported;
the memory regression was found by review cycle 1 and is fixed in fix round 1.

## The runs

* worktree `card/218-render-once-per-module` at `4ae0d825`, based on `c7cca514`
* host: Mac15,6 Apple M3 Pro, 11 cores, 18 GB, macOS 26.7.1 (Darwin 25.6.0
  arm64), Python 3.14.3, pytest 9.1.1 — the same host as
  `suite-durations-20261015.txt`, `suite-durations-20261023.txt`,
  `card-241-render-check-cost.md` and `card-243-two-threshold-cost.md`
* load averages 4.3–5.2 throughout, recorded per run below
* the **base** column is this worktree with the two converted files replaced by
  `git show c7cca514:<path> > <path>` — never
  `git checkout <rev> -- <path>`, which **stages** the path and leaves the
  index holding the base file while the tree reads right — and restored with
  `git checkout -- <path>`, both files' sha256 re-verified after every restore
  (`4e1512828e…` / `959bdff36b…`)
* command, with `-o addopts=''` where output was the measurement, because
  `pyproject.toml:89` already supplies `-q` and a second one suppresses the
  count line:

```bash
/usr/bin/time -p ./.venv/bin/python -m pytest \
    tests/test_book_puzzle_frame.py tests/test_book_pdf_band.py
```

Nothing under `meta/profiling/` was re-measured or regenerated: the two frozen
duration artefacts are read-only inputs here, and the figures taken from them
were recomputed by parsing their own `<secs>s <phase> <nodeid>` records.

## 1. The renders — the measurement that is an integer

The claim this card makes is that a book is drawn once per module instead of
once per test. That is a **count**, so it was counted, by a pytest plugin
wrapping each render entry point. The plugin was kept **outside `tests/`** on
purpose: `rank_durations.py`'s render set is defined by grepping eight idioms
over `tests/**/*.py` and `tests/test_suite_profile.py` asserts that set as an
equality, so a probe file in `tests/` naming `interior(` reds the suite.

| render entry point | base | HEAD | removed |
|---|---|---|---|
| `test_book_pdf_band._interior` | 40 calls, 4.451 s | 33 calls, 3.534 s | **7 calls, 0.917 s** |
| `test_book_puzzle_frame._book_pages` | 5 calls, 0.811 s | 1 call, 0.176 s | **4 calls, 0.635 s** |
| **total** | **45, 5.262 s** | **34, 3.710 s** | **11 calls, 1.552 s** |

**11 of 45 renders, 24 %.** Corroborated by a second instrument that is also a
pure call counter and immune to machine load: the `datetime.utcnow()`
`DeprecationWarning` each document build emits falls **274 → 252** across the
two files, i.e. 11 fewer builds. The same integer, reached two ways.

## 2. The wall clock — three interleaved pairs, and the figure is softer than first reported

The implementation round reported `8.79 s → 7.80 s`, **−0.99 s / −11.3 %**,
from three runs of each arm taken as two blocks. Re-measured as three
**interleaved** pairs (base, head, base, head, base, head — which controls for
drift *within* the measurement instead of between two blocks of it), plus three
more unpaired runs of each arm:

| | runs (pytest wall) | min | median |
|---|---|---|---|
| base | 9.30 8.53 8.54 9.15 8.89 8.91 | 8.53 | **8.90** |
| HEAD | 7.96 8.82 7.94 8.04 8.27 8.57 | 7.94 | **8.16** |

Paired deltas **−1.11, −0.62, −0.34 s**; median delta **−0.74 s (−8.3 %)**; on
user time −0.79 s. The five controls the conversion adds cost **0.10–0.15 s**
of that (HEAD with them deselected: 8.44 / 8.01 / 7.84 s), so the shortfall
against the 1.552 s of rendering removed is run-to-run variance, not the
controls.

**The spread is the point.** Six base runs span 8.53–9.30 s on an 8.90 s
median — **8.7 %**. A −0.74 s effect is roughly one spread wide, which is why
clause 3 of AC-2 is struck below and why §1's integer is what this card's claim
rests on.

## 3. The memory, which is why review cycle 1 scored this 6.0

Read at `pytest_sessionfinish`, after every fixture is finalised. Both test
modules are still in `sys.modules` — pytest keeps them there — so a
module-level list outlives the module-scoped fixture that filled it.

| accumulator | entries | retained |
|---|---|---|
| `test_book_puzzle_frame._SHARED_DIGEST` | 10 | 252,450,000 B (240.8 MiB) |
| `test_book_pdf_band._SHARED_SNOWFLAKE_DIGEST` | 8 | 201,960,000 B (192.6 MiB) |
| `test_book_pdf_band._FIFTH_RULE_RENDERS` | 1 | 0 B |
| **total at `4ae0d825`** | | **454,410,000 B = 433.4 MiB** |

`tests/test_book_pdf_memory.py:210` defines
`PAGE_BITMAP_BYTES = 2550 * 3300 * 3` = 25,245,000, and each entry is that
figure **exactly** — so this is **18.0 page bitmaps** in the project's own
unit, held for the rest of the session, in a repo whose memory module exists
because a page alive while the next was built was a real defect (CARD-145).
Both fixture docstrings justified module scope over session scope by saying a
session fixture "would hold this book's page bitmaps alive for the rest of the
run"; the module-level list they populate did exactly that, by the same volume.

Fix round 1 stores `hashlib.sha256(page.tobytes()).digest()` instead. Verified
as a reverted trial before the round was authorised: **454,410,000 B → 576 B**,
134 passed unchanged, and the controls still kill — the "digest never taken"
mutant still reds both frame controls and the "a consumer draws on the shared
page" mutant still reds the consumer and the band control.

### Peak RSS is the wrong instrument for this, and here is the measurement that says so

| `/usr/bin/time -l` max RSS | base | `4ae0d825` | delta | under the sha256 trial |
|---|---|---|---|---|
| `test_book_puzzle_frame.py` | 669.1 MB | 965.9 MB | **+296.7 MB** | 729.1 MB |
| `test_book_pdf_band.py` | 1320.2 MB | 1396.3 MB | **+76.1 MB** | **1491.9 MB** |
| both files, one run | 1294.3 MB | 1661.0 MB | **+366.7 MB** | 1516.9 MB |

Band's base peak is already 1320 MB, set by its own 40 renders, so its
192.6 MiB digest largely fits under an existing high-water mark — and under the
fix that removes the retention entirely, band's measured peak went **up**. Peak
RSS here is allocation-order dependent. **The retention is exact and the peak
is a stopwatch**, which is the same lesson as §1 and §2 in a third guise, and
it is why fix round 1 is certified on the retention.

(For the record: review cycle 1 reported band at +353.2 MB. That figure did not
reproduce on this host; its +300.6 MB for the frame file and ≈+400 MB combined
did, within 4 MB and 33 MB. The retention figures reproduced exactly, twice.)

## 4. The premise, recomputed — why this card converts two files and closes

Recomputed from `suite-durations-20261023.txt` by parsing its own records:

* attributed total **1426.16 s**; phase split **setup 6.79 % / call 91.79 % /
  teardown 1.42 %**;
* the card's nine `Touches:` files: **69.79 s over 529 tests = 4.89 %**, at
  **131.9 ms/test** — *below* the suite's own per-test mean;
* the two files this card converted: **8.86 s** of that.

So the subject is 4.89 % of the suite and the mechanism's measured ceiling
across all nine files is **4.90 s** — 0.34 %. The card's body also counts
"110 `interior(...)` call sites"; re-counted 2026-10-24, the tree's idiom is
`_interior(` at **120** sites (bare `interior(` is 2), so that count was
approximately right and is **irrelevant in either direction**: the three files
holding **77 of the tree's 151** render call sites —
`tests/test_book_pdf.py` (30), `tests/test_book_pdf_two_up.py` (24),
`tests/test_book_cell_size.py` (23), none of them in this card's `Touches:` —
cost **13.73 s together, 0.96 % of the suite**, at 100 ms/test. Size a curation
card on measured duplication, never on a census of call sites.

## 5. What a cycle on this card costs to gate, which is not this card's fault

`review.test_scope` is `impact`, and `scripts/impact_set.py` for these two
files returns **24 files = 448.77 s = 31.47 % of the suite** (priced against
the committed artefact; review cycle 1 measured 526.21 s on a busier box). Of
that, **344.29 s — 77 % — is `tests/test_book_export_interior_cover.py`**, a
file this diff has nothing to do with. That is CARD-287's subject and, for the
derivation's part in it, CARD-286's.

## 6. What was NOT measured here, stated so no successor treats it as settled

* **The nine-file recoverable-duplicate table (the 4.90 s ceiling) is
  single-instrument.** The implementation round produced it by digesting
  `(method, book, args)` per render; it has not been re-derived by a second
  method. The one cross-checked subset suggests it reads about **18 % low** —
  it predicted 1.32 s for the two files where the independent call counter in
  §1 measured 1.552 s removed. Immaterial to the decision (at three times the
  ceiling this card's whole subject is ~1 % of the suite), but it is a single
  reading and the card's closure rests on it.
* **No full suite was run for this card.** AC-2's suite-total clause asked for
  one before and after; see below.
* `tests/test_book_solved_answer_key.py`'s declined 0.86 s was accepted on the
  round's measurement, not re-derived.

## AC-2 as ruled by review cycle 1

AC-2 had three clauses. **This document satisfies the artefact and per-file
clauses.** The third — *"and the total is lower"*, meaning the suite total —
is **struck**: measuring a ~1.5 s effect in a 1433 s suite needs two solo full
runs at 1433 s each, and a full suite's run-to-run spread is tens of seconds,
two orders of magnitude above the effect. (The implementation round struck it
for a different and wrong reason — it cited a "0.20 s solo-run
reproducibility", which is a *full-suite* figure, against a 0.99 s gain that is
five times larger than it; the orchestrator's pre-gate repeated that figure
without checking the argument it was supporting. The conclusion survives, the
stated reason did not.)

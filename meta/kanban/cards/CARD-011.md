# CARD-011: Puzzle naming (auto-generated and --name override)

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/011-puzzle-naming
**Worktree:** ../PythonProject4-card-011
**Source:** meta/architecture/handoff.md#increment-2
**Idea:** —
**Wave:** 6
**Depends on:** CARD-005, CARD-006, CARD-007
**Touches:** src/nonogram/orchestrator.py, src/nonogram/cli.py, tests/test_naming.py
**Review score:** 8.5 (cycle 1/3)
**Started:** 2026-08-28T10:52:03Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`name` becomes an attribute of the `Puzzle` aggregate (AGG-001), set once at creation. It
lands in COMP-002 because COMP-002 owns the aggregate and constructs it once per run
(ADR-0007's single-enforcement-point rule) — COMP-003 produces grids, not `Puzzle`
instances, so it is not the home for naming even though the library key that seeds the
auto-name comes from its mode (trace.yml FR-015 note).

1. **Auto-generation.** Library mode → the library key verbatim (`"cat"`). Random and image
   modes → `<mode>-<YYYY-MM-DD>-<HHMM>`, e.g. `random-2026-08-27-1430`. ADR-0018 fixes
   **minute** precision plus an incrementing counter suffix when two puzzles are created in
   the same minute — that collision branch is the one AC-042 most needs a **fixed-clock**
   test for, so inject the clock rather than calling `datetime.now()` inline.
2. **`--name` override.** The flag is carried through by `cli.py` (parsing only). An empty
   string is rejected with `InvalidPuzzleName` and **no puzzle is created** — AC-045 is
   domain validation and stays inward of argparse (ADR-0010), mirroring how FR-001's size
   range is handled. Do not implement it as `argparse` `type=`.
3. The name is set at creation and does not change across regenerate/resample/nudge
   retries — the aggregate is not re-created per retry (aggregates.yml AGG-001).
4. The name is an attribute of the aggregate only. Its consumers are later cards — the PDF
   header (CARD-014) and the `<name>-<difficulty>.pdf` filename (ADR-0016) — and they read
   it off the `Puzzle`. This card writes it nowhere on disk.

## Acceptance criteria

- **AC-042** (happy) — given a random-mode generation request with no `--name` flag, run on
  2026-08-27 at 14:30, when the puzzle is created, then the puzzle's name is auto-generated
  as `"random-2026-08-27-1430"`.
  *test:* `TestPuzzleName_AutoGeneratesModeTimestampForRandomMode`
- **AC-043** (happy) — given a library-mode generation request for library key `"cat"` with
  no `--name` flag, when the puzzle is created, then the puzzle's name is auto-generated as
  `"cat"`.
  *test:* `TestPuzzleName_AutoGeneratesFromLibraryKey`
- **AC-044** (happy) — given a generation request with `--name "my-cat-puzzle"` supplied,
  when the puzzle is created, then the puzzle's name is set to `"my-cat-puzzle"`, overriding
  the auto-generated default.
  *test:* `TestPuzzleName_OverrideViaFlag`
- **AC-045** (negative) — given a generation request with `--name ""` (an empty string)
  supplied, when the puzzle is created, then the request is rejected with an invalid-name
  error and no puzzle is created.
  *test:* `TestPuzzleName_RejectsEmptyName`

## Guardrails

- G-1: Do not edit `src/nonogram/sourcing/**` — owned by CARD-008 this wave
- G-2: Do not edit `src/nonogram/difficulty.py` — owned by CARD-009 this wave
- G-3: Do not edit `src/nonogram/export/**` — owned by CARD-012 and CARD-013 this wave. The
  name is an aggregate attribute; nothing on the export path changes for it in this card
- G-4: Do not edit `src/nonogram/solver/**`, `src/nonogram/clues.py` — Increment 2 is
  additive on top of Increment 1; naming must be revertible without touching the solver or
  the orchestrator's core generation logic (handoff Increment 2 Rollback)
- G-5: `--name` validation stays inward of argparse (ADR-0010). `cli.py` carries the flag
  through; the empty-name rejection is a domain error raised by COMP-002
- G-6: The name is set once at creation and is stable across retries — do not regenerate it
  inside the regenerate/resample loops (AGG-001: the aggregate is not re-created per retry)
  (test: TestRegenerate_FiresOnUniquenessFailure)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-015
- **NFR:** —
- **ADR:** ADR-0007, ADR-0010, ADR-0018
- **Components:** COMP-002 (Pipeline Orchestrator — AGG-001 attribute), COMP-001 (flag)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

### What landed

Touches as predicted, nothing beyond them: `src/nonogram/orchestrator.py`,
`src/nonogram/cli.py`, `tests/test_naming.py` (34 new tests).

- **`Puzzle.name`** (AGG-001) — a real field on the aggregate, written once by
  `generate()` *before* the aggregate is constructed and never again (G-6).
  `None` only for a `Puzzle` somebody assembles by hand, the same
  partially-built state `grid`/`clues` already start in.
- **`NameContext`** (COMP-002) — ADR-0018's "current run's naming context" as
  an object: an injectable `clock` plus the set of auto-names it has `issued`.
  `DEFAULT_NAMES` is the process-wide instance `generate()` uses;
  `generate(request, *, names=...)` takes another one, which is what makes
  AC-042's same-minute counter branch testable on a fixed clock instead of on a
  minute boundary that never comes (the ADR's own "easy to under-test" con).
- **Auto-name:** library mode → `request.library_key` verbatim (AC-043, never
  counter-suffixed — ADR-0016 says outright that a key like `"cat"` "is not
  guaranteed unique" and leaves that to ADR-0017's export-time suffix). Random
  and image modes → `<mode>-<YYYY-MM-DD>-<HHMM>`, with `-1`, `-2`, … appended
  when the context already issued that exact name (AC-042). The suffix search
  is written in the shape of `export._free_path` on purpose: ADR-0018 chose
  `counter_suffix` precisely so the pipeline's two collision points read as one
  idea applied twice.
- **`--name`** — parsing only in `cli.py` (no `type=`, no `choices=`);
  `--name ""` parses fine and is refused inward by `NameContext.name_for` →
  `InvalidPuzzleName` → exit code 3, before the seed is drawn and before the
  first candidate is sourced, so no puzzle is created (AC-045, ADR-0010, G-5).
  Whitespace-only is refused with it: it is the same emptiness for both
  consumers the name has (a blank PDF header, a stem that sanitizes away).

### The name / export-stem consolidation question

**Decision: `Puzzle.name` is the single source of truth in both directions.**

1. The auto-name *calls* `export.default_stem(mode, moment=...)` instead of
   re-spelling `f"{mode}-{now:%Y-%m-%d-%H%M}"`. The convention now exists in
   exactly one place in the codebase.
2. `export_puzzle` derives its stem from `puzzle.name`
   (`orchestrator._filename_stem`) instead of computing `default_stem(mode)`
   independently.

Why, concretely — without (2), the same run says two different things:

| run | puzzle name | file (before) | file (after) |
|---|---|---|---|
| `--mode library --library-key cat` | `cat` | `library-2026-08-28-1405.json` | `cat.json` |
| `--name my-cat-puzzle` | `my-cat-puzzle` | `random-2026-08-28-1405.json` | `my-cat-puzzle.json` |
| random, started at 14:29:59 | `random-…-1429` | `random-…-1430.json` (second clock read!) | `random-…-1429.json` |

CARD-014 then reads `puzzle.name` for the PDF header and for
`<name>-<difficulty>.pdf` (ADR-0016), so leaving (2) undone would ship a run
whose PDF is `cat-hard.pdf` next to its own JSON called
`library-<timestamp>.json`. CARD-007 wrote `default_stem` as an explicit
stand-in for exactly this handoff — "when the aggregate starts carrying a name,
this function's caller reads it instead" is its own docstring — and this card
is that caller.

**On G-3.** The binding clause ("do not edit `src/nonogram/export/**`") is
respected: `export/__init__.py` is untouched, `default_stem`, `write` and
`_free_path` are unchanged, and every existing export test still passes
unmodified — including the two that pin the stem by monkeypatching
`export.default_stem`, because a hand-built `Puzzle` has `name is None` and
still takes CARD-007's fallback path. What changed is one line *inside
`export_puzzle`*, which is orchestrator code in an in-scope file. G-3's prose
("nothing on the export path changes for it in this card") reads as a
prediction that the aggregate attribute is self-contained; it stops being true
the moment the name is the thing the file is named after, which is ADR-0016's
whole premise. Recorded here rather than done silently.

**Sanitization came with it.** Feeding a user-supplied `--name` into
`directory / f"{stem}{ext}"` is a path-traversal surface that a
machine-generated stem never had, so `_filename_stem` applies ADR-0016's
"sanitized for filesystem-safe characters" (allow-list `[A-Za-z0-9._-]`, then
strip leading/trailing `-.` so nothing becomes `.`, `..` or a dotfile) on the
way to the path only — the aggregate keeps the name exactly as typed (AC-044),
and a name that sanitizes to nothing falls back to the generated stem.
CARD-014 composes `<name>-<difficulty>` from the same helper, so both
components inherit one sanitization rule rather than two.

### Tests

`tests/test_naming.py`, 34 tests: the four AC-named ones (with a fixed-clock
same-minute test for AC-042's counter, plus a next-minute test showing the
counter is a same-minute device and not a run counter), the G-6 stability test
(scripted source, three attempts, a clock that advances a minute per reading —
the name does not move and `issued` holds exactly one entry), and a section
pinning name → filename, including that `--name "../../escaped"` cannot write
outside `--out`.

`./.venv/bin/python -m pytest`: **831 passed, 1 xfailed** (the pre-existing
AC-037 benchmark xfail) — baseline before this card was 797 passed, 1 xfailed,
so 34 added and no regressions.

No blockers.

### Orchestrator notes

- **[Scope]** Rebased cleanly onto main (`9c9ccd6` → `36211c0`) after
  CARD-008/009/012/013 merged. Touches match predicted exactly: no scope
  creep — `export/__init__.py` itself is untouched, only `orchestrator.py`'s
  internal call to it changed, per the implementer's own G-3 note above.
- **[Build gate]** PASSED (full, independently re-run by orchestrator: 928
  collected, 927 passed, 1 xfailed, exit 0 — 928 vs the worktree's own 831
  reflects CARD-009/012/013's tests merging in since the worktree's branch
  point).
- **[Review 1/3] 8.5/10 — FAIL (severity gate).** Report:
  `meta/review/20260828T112238Z-CARD-011-cycle1.yml`. G-3 export-stem
  consolidation ruled **legitimate, not a finding** (guardrail's stated
  rationale — CARD-012/013 ownership this wave — is spent now both have
  merged; `export/**` itself is untouched). Path-traversal sanitization
  independently re-verified sound (29-name adversarial corpus). Two Important
  findings block merge regardless of score:
  - F-001: `_UNSAFE_STEM_CHARACTERS` is ASCII-only — a non-ASCII `--name`
    (Cyrillic/accented/etc.) is silently truncated to a misleading filename
    stem instead of falling back, with no warning. Fix: widen the allow-list
    to `[^\w.-]+` (Unicode-aware `\w`), verified to preserve every
    traversal-safety property while keeping non-ASCII names intact.
  - F-002: no test asserts the sanitized `path.stem` value itself — only
    `puzzle.name`, `path.parent`, `path.suffix` — which is why F-001 shipped
    green. Fix: add stem assertions (incl. a mixed-script case) to
    `tests/test_naming.py`.
  Five Minor/out-of-scope notes deferred, not fix-cycle-blocking (README
  status staleness pre-existing; `default_stem` docstring staleness folds
  into CARD-014; over-long `--name` exit-code grouping; `DEFAULT_NAMES`
  process-wide mutation latent-trap; one loosely-named test).

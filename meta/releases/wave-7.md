# Wave 7 — 2026-08-29   (tag: wave-7)

Single-card wave: CARD-010 closes the loop CARD-009 opened, turning a raw difficulty
score into the user-facing tier selector. Zero fix cycles — cleared cycle 1 at 9.5/10.

## Shipped
- CARD-010 (feature): Difficulty tier selection and resample loop — `--difficulty
  {easy,medium,hard}` maps CARD-009's 0-100 score to ADR-0005's tertile bands (named
  cutoffs in `difficulty.py`, band table and classifier both derived from them so they
  can't disagree at a boundary). POL-004: a candidate scoring outside the requested tier
  is discarded and resampled, sharing CARD-005's existing 20-attempt retry budget rather
  than adding a second independent counter.   score 9.5 (cycle 1/3)   FR-008, FR-010,
  NFR-002, INV-003, CON-004, POL-004, POL-005, ADR-0002, ADR-0005

## Requirements closed
- FR-008 (difficulty tier selector) and FR-010 (resample-on-out-of-range) — both closed
  by the same card, since POL-004 only makes sense once a tier exists to check a score
  against.

## Design decision worth recording
CARD-005's own review had left a note in this card requiring the resample loop to reuse
the existing 20-attempt bound rather than declare a second literal `20`. The implementer
took the strongest available form of that: `MAX_REGENERATE_ATTEMPTS = MAX_RESAMPLE_ATTEMPTS
= MAX_RETRY_ATTEMPTS`, a chained assignment binding all three names to one object, pinned
by an identity test (not just `==`, since two independently-declared `20`s would satisfy
that too and diverge on the first retune). The loops compose resample-outer/regenerate-
inner, and — because the regenerate counter is never reset between resample rounds — a
run that keeps missing its tier abandons on the shared budget of 20 *sourced grids per
request*, not 20 resample rounds each getting their own 20-grid regenerate budget. This
is the ADR-0002-conformant reading (the ADR justifies its cap entirely by bounding solver
invocations), and both directions of it — the reused constant and the shared budget — are
now pinned by tests rather than left as reasoning.

## Review process notes
- Cleared cycle 1 outright (9.5, zero Critical/Important findings) — the reviewer
  independently re-derived the loop-composition claims by tracing the code (not just
  reading the tests) and reproduced the score-distribution claim below by running the
  shipped pipeline on 16 real requests.
- Two files outside the card's predicted `Touches:` were added and explicitly flagged by
  the implementer rather than done silently (the pattern established by CARD-011 last
  wave): a new `UnsupportedDifficulty` exception in `errors.py` (required by the
  architecture's one-flat-hierarchy rule — it couldn't legally live in `difficulty.py`),
  and one line in `tests/test_cli.py` satisfying an existing reflection-based test that
  requires every domain error to have a mapped exit code. Both ruled legitimate and
  minimal, not scope creep.
- G-6 (must not regress the already-`xfail(strict=True)` AC-037 benchmark) verified two
  ways: the benchmark file itself is untouched and still fails for the same pre-existing
  reason (CARD-018's tracked solver-strength gap), and scoring is proven to run only
  after a candidate's uniqueness check passes — so a run with no `--difficulty` (the
  benchmark's own request shape) does exactly the same solver work as before this card.

## A real, user-visible gap surfaced — not this card's to fix
Both the implementer and the reviewer independently measured real score distributions
across a range of sizes/densities and found the same thing: nothing lands anywhere near
the Hard tier's floor (66). `--difficulty hard` is, as shipped, a flag that always
resamples to the retry bound and abandons. This is exactly the risk ADR-0005's own
Consequences section predicted ("equal tertile bands could leave one tier — most likely
Hard — under-populated") and explicitly deferred pending real distributions. These are
the first real distributions. The fix is a weights/cutoffs retune (an ADR-0005/ADR-0013
revision), not a code change, and squarely out of CARD-010's authority — its job was to
implement the tertiles as ADR-0005 currently defines them, which it did. **Flagging this
to the user as worth a backlog card now, rather than waiting for retrospective.**

## Convergence
- FR-008, FR-010 ✓ converged.
- Increment 2's difficulty-tier surface (CARD-009 + CARD-010) is now fully shipped;
  Increment 2's remaining unscheduled item is CARD-014 (PDF export), which reads both
  the tier and the name off the aggregate.

## Known gaps / escalations
- AC-037 — still tracked via `xfail`, CARD-018 unchanged, untouched this wave.
- **New:** `--difficulty hard` (and, at some sizes, `medium`) is unreachable with the
  current score formula/cutoffs — needs a backlog card for an ADR-0005/ADR-0013 retune.
- Minor doc drift noted, not blocking: `trace.yml` still marks every FR `partial` project-
  wide (pre-existing, not this wave's regression); `src/nonogram/__init__.py`'s package
  map still says `difficulty.py` is a "(later card)"; `README.md`'s Status paragraph
  remains stale and silent about `--difficulty` (flagged again this wave, unowned).

## Migrations
- none

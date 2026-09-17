"""COMP-002 — the pipeline orchestrator: one generation run, end to end.

ADR-0007 gives this module three jobs and nothing else:

* own the Puzzle aggregate (AGG-001) for the whole of one generation run;
* be the single enforcement point for INV-002 (a puzzle is exportable only
  after its uniqueness check confirmed exactly one solution) and INV-003 (the
  regenerate / resample / pixel-nudge counter never exceeds its bound);
* drive the generation policies POL-001..POL-005 by composing the capability
  modules (sourcing, clues, solver, difficulty, export), which never call each
  other laterally.

The pipeline (FR-007, FR-010)
-----------------------------
``source a grid -> compute its clues -> count its solutions -> score it ->
mark ready``. A candidate that is not uniquely solvable is repaired in place
and re-judged, up to :data:`MAX_CONSECUTIVE_REPAIRS` times, before it is
discarded for a fresh grid (POL-006 then POL-001 — random mode only, ADR-0024;
library mode goes straight to the redraw); a candidate that *is*
unique but whose difficulty score misses the requested tier is discarded and
resampled the same way (POL-004). Both are bounded by the same ADR-0002 number
(:data:`MAX_RETRY_ATTEMPTS`), after which the run is abandoned (POL-005).

Neither verdict is this module's to form: it compares ``solution_count``
against 1 and asks COMP-006 which band a score is in, and does nothing else
with either (guardrail G-3, CON-005, CON-004). In particular a requested tier
never reaches the *sourcing* of a grid — POL-004 discards and re-draws
candidates, it does not steer construction toward a tier.

Why the loops are a primitive, not a ``while`` (INV-003)
-------------------------------------------------------
Three bounded loops exist in the model — regenerate (POL-001), difficulty
resample (POL-004) and pixel nudge (POL-002, CARD-016) — and INV-003
constrains all three with one sentence. So the counting lives in one place,
:class:`RetryCounter` plus :func:`run_bounded`, and a loop *kind* is just a
counter with its own bound plus a callable that produces a candidate or
rejects it. The resample loop added by CARD-010 is that and nothing more: a
second counter field on :class:`Puzzle` and a second attempt callable wrapped
around the first, with no second way to count and no second bound literal
(guardrail G-2). CARD-016's nudge loop is expected to land the same way.

What counts as a retry, and what does not
-----------------------------------------
Only a candidate the *uniqueness check answered about* can be retried: the
attempt callable turns ``solution_count != 1`` into a rejection and nothing
else. Every exception — invalid input (SizeOutOfRange, InvalidDensity),
``SolverTimeout`` (ADR-0011), a wiring bug — travels straight
out of the loop and ends the run. Conflating a timeout with a non-unique
verdict would let one infeasible request spend ``MAX_RETRY_ATTEMPTS`` full solver
deadlines, which
is exactly the worst case ADR-0002's bound and ADR-0001's time budget exist to
prevent; the two bounds are meant to "operate together but independently"
(ADR-0002, Neutral).

A source that cannot be re-drawn (image mode, POL-002)
------------------------------------------------------
POL-001's whole premise is that a rejected candidate can be replaced by a
*different* one. That holds for the random source (a fresh draw) and for the
library source (the same template at a different boundary tie-break); it does
not hold for an uploaded image, whose conversion at a given extent is fully
determined. Asking ``sourcing.image`` for another grid returns the grid it just
returned, so running image mode through the regenerate loop would spend the
whole retry budget re-confirming one verdict and then report an "abandoned after
``MAX_RETRY_ATTEMPTS`` attempts" that never had more than one attempt in it.

So image mode does not enter either of those bounded loops: :func:`generate`
converts once, and the regenerate and resample counters stay at zero, which is
the observable form of "this mode is not in POL-001/POL-004".

Its recovery path is POL-002's bounded pixel nudge (FR-013, CARD-016) instead,
and it is a third :class:`RetryCounter` next to the two below rather than a
different mechanism — the one place INV-003 counts anything. What it retries is
not the *source* but the grid the source already returned: each round asks
``sourcing.image`` to flip one more cell of the conversion and re-runs the
whole judgement on the result, so at most :data:`MAX_NUDGE_ATTEMPTS` pixels of
the user's picture are ever altered and every one of those grids is a real
solver verdict, not an assumption (CON-005). At the cap the loop reports and
stops (POL-003) — there is no unbounded "one more try" behind it. A conversion
that misses the requested *tier* still ends the run immediately: POL-004 cannot
help a fixed source either, and nudging is a uniqueness remedy, not a
difficulty dial.

The split of POL-002 across two components is trace.yml's FR-013 note: the
policy (when, how often, what to say at the cap) is here, the mechanism (which
cell to flip) is in ``sourcing.image.next_nudge_cell`` and
``sourcing.image.nudge``, which own the grid the image produced and count
nothing. Since CARD-075 the mechanism reads the solver's verdict on the
previous attempt's candidate, so this loop carries the cells chosen so far in
its closure — the same shape as ADR-0024's repair lineage, and for the same
reason: ``run_bounded`` counts, the callable decides what to try next.

Naming (FR-015, ADR-0018)
-------------------------
Every puzzle carries a :attr:`Puzzle.name`, resolved *once* by :func:`generate`
before the aggregate exists and never touched again — not by a regenerate, a
resample or a pixel nudge (guardrail G-6, AGG-001). Naming lands here and not
in a capability module for the same reason the invariants do: COMP-002 is what
owns the aggregate and constructs it once per run (ADR-0007), whereas COMP-003
produces grids, not :class:`Puzzle` instances, even though the library key that
seeds a library puzzle's name comes from its mode.

The name is also the *only* source of a run's export filename stem
(:func:`export_puzzle`), so the name a user reads and the file they get cannot
drift apart — see :func:`_filename_stem`.

Dependency direction: this module imports the capability modules and never the
adapter; nothing inward of it imports back (ADR-0007, enforced for every
module in the package by ``tests/test_cli.py``).

No persistence (CON-003, guardrail G-4): the aggregate below lives in memory
for the duration of one call and is dropped when it returns or raises. The
export file, written by COMP-007 out of :func:`export_puzzle`, is the only
durable artifact — and :func:`generate` itself still writes nothing, so a run
that is abandoned or never asked for an export leaves no trace on disk.
"""

from __future__ import annotations

import itertools
import random
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from nonogram import clues as clue_derivation
from nonogram import difficulty, export, solver, sourcing
from nonogram.errors import ExportRejected, GenerationAbandoned, InvalidPuzzleName
from nonogram.sourcing import image as image_source
from nonogram.sourcing import random_grid

__all__ = [
    "BATCH_BUDGET_SECONDS",
    "BatchResult",
    "MAX_BATCH_COUNT",
    "DEFAULT_NAMES",
    "GENERATION_BUDGET_SECONDS",
    "MAX_CONSECUTIVE_ABANDONMENTS",
    "MAX_CONSECUTIVE_REPAIRS",
    "MAX_NUDGE_ATTEMPTS",
    "MAX_REGENERATE_ATTEMPTS",
    "MAX_RESAMPLE_ATTEMPTS",
    "MAX_RETRY_ATTEMPTS",
    "UNDECIDED_MASK_REGION",
    "WITNESS_DISAGREEMENT_REGION",
    "GenerationRequest",
    "NameContext",
    "Puzzle",
    "RecoveryLog",
    "Repair",
    "RetryCounter",
    "export_puzzle",
    "generate",
    "repair_candidate",
    "run_bounded",
]

#: The ADR-0012 boundary representation of a solution grid, row-major,
#: ``True`` for a filled cell — the same type the sourcing modules return and
#: the clue derivation consumes.
Grid = list[list[bool]]

#: ADR-0002/R1: the regenerate/resample loop is capped at 30 attempts. **One**
#: number for both loop kinds, and deliberately one *constant* — ADR-0002 gives
#: regenerate and resample the same bound, so two literals could silently drift
#: apart under a retune that only found one of them. The aliases below are the
#: names the two counters are constructed under; they exist so a reader of
#: ``RetryCounter("resample", MAX_RESAMPLE_ATTEMPTS)`` sees which policy's bound
#: is meant, without that reading being a second, independent number.
#:
#: Named here because INV-003's bound is the orchestrator's business (the
#: pixel-nudge cap of 5 lands with CARD-016's counter, same way — a *different*
#: number, from the same ADR, and so genuinely its own constant).
#:
#: 30 rather than ADR-0002's original 20 since CARD-090, and the difference is
#: measured rather than argued. At 30x30, density 50, over 100 seeded requests
#: through this function: bound 20 abandoned 14, bound 30 abandons 4, bound 40
#: abandons 3, bound 60 abandons 1. Ten of the fourteen were *false* negatives —
#: the same seeds produce a puzzle once the budget allows it — and 30 is where
#: the curve knees, capturing ten of the eleven conversions bound 40 offers.
#:
#: Raising it costs nothing, which is the counter-intuitive part and the reason
#: ADR-0002 originally argued the other way: an abandonment is the *expensive*
#: outcome, since it spends the whole budget and returns nothing, while a
#: success usually lands early. Total wall clock over those 100 requests fell
#: as the bound rose. A single request's worst case is set by
#: :data:`GENERATION_BUDGET_SECONDS`, not by this number — one deadline per
#: request, shared by every attempt in it — so this bound cannot extend it.
MAX_RETRY_ATTEMPTS = 30
MAX_REGENERATE_ATTEMPTS = MAX_RESAMPLE_ATTEMPTS = MAX_RETRY_ATTEMPTS

#: ADR-0024's K: how many times in a row random-mode recovery may REPAIR one
#: candidate (POL-006) before that lineage is abandoned and POL-001 draws a
#: fresh grid instead.
#:
#: Deliberately **not** a second bound, and that distinction is the whole of
#: ADR-0024/R2 (guardrail G-2). Every repair and every redraw advances the one
#: :attr:`Puzzle.regenerate` counter bounded by :data:`MAX_RETRY_ATTEMPTS`; K
#: only says how that single budget is *split* between the two reactions — how
#: long one correlated lineage may run before the loop goes back to drawing
#: independent samples. A run can no more exceed that bound with repairs than
#: without them, which is why K is a plain constant here and not a
#: :class:`RetryCounter`: it bounds nothing, it interleaves.
#:
#: 5 since CARD-091 (ADR-0024, revised), measured rather than guessed. ADR-0024 chose
#: 3 as "a guess about how often a repair lineage converges rather than wanders"
#: and scheduled the recalibration. Swept at 30x30, density 50, bound 30, over
#: 100 seeded requests per value: K=0 (pure redraw) 38%, K=3 95%, K=5 99%,
#: K=8 98%, K=12 98%. The tell was where acceptances landed: at K=3, 45 of the
#: 95 accepted puzzles were found on the *last* repair K allowed — lineages
#: still converging were being thrown away for a fresh grid that is unique 2.7%
#: of the time. 5 is the smallest value within one request of the best, and it
#: is cheaper, not dearer: total wall clock fell from 329 s to 226 s, and the
#: one request that ran into the 30 s deadline at K=3 finished inside 10 s.
#: Smallest rather than fastest (K=8 took 193 s) because a larger K costs more
#: on the rare lineage that flips a pair back and forth, and a 100-request
#: corpus under-samples those. Setting it to ``0`` disables POL-006 and
#: restores the pure-redraw loop it replaced exactly, down to the rng draws:
#: that is ADR-0024's rollback switch, and it is a property of how the branch
#: in :func:`generate` is written rather than a flag anything consults.
MAX_CONSECUTIVE_REPAIRS = 5

#: How many candidates in a row a *batch* may abandon before it stops trying.
#:
#: Not a second per-puzzle bound — INV-003's counters are untouched and still
#: end one candidate's life after :data:`MAX_RETRY_ATTEMPTS` draws. This one
#: ends the *batch*, and it exists because skipping an abandoned candidate
#: (CARD-083) removed the thing that used to stop a hopeless request: the first
#: failure. Without it, ``generate_batch(count=50)`` against parameters that
#: can never produce a puzzle would spend 50 x 30 = 1500 solves discovering
#: that, where it used to spend 30. (The example was written as ``count=200``
#: against a bound of 20; CARD-088 capped a batch at :data:`MAX_BATCH_COUNT`
#: and CARD-090 moved the bound, so both numbers are restated here rather than
#: left describing a call this module no longer accepts.)
#:
#: Three — which once matched :data:`MAX_CONSECUTIVE_REPAIRS` next door; that
#: one moved to 5 in CARD-091 on its own measurement, and nothing about this
#: argument depended on the match — because three in
#: a row is not bad luck at any rate this function can actually reach. Measured
#: over 200 draws per size at the density ``generate_batch`` hardcodes (50):
#: 0/200 abandoned at 10x10, 15x15 and 20x20, and 4/200 at 25x25. At the worst
#: of those, p = 0.02, the chance of three consecutive abandonments is 8 in a
#: million; a batch that hits it has parameters that are wrong, not unlucky.
MAX_CONSECUTIVE_ABANDONMENTS = 3

#: ADR-0002's *other* number: POL-002's pixel-nudge cap is 5, and this is
#: deliberately **not** written as a fraction or an alias of
#: :data:`MAX_RETRY_ATTEMPTS` (CARD-016 guardrail G-2). The 30 above and the 5
#: here are two independent judgements from the same ADR about two different
#: things — how many *fresh* candidates it is worth drawing before a request is
#: called infeasible, versus how much of the user's own picture it is
#: acceptable to alter behind their back. Chaining them would say the two move
#: together, and they do not: a retune of the retry bound must not silently
#: license twenty edits to an uploaded photograph.
#:
#: The bound lives here, next to the other one, because INV-003 has exactly one
#: home — COMP-002. ``sourcing.image`` applies the nudge and counts nothing.
MAX_NUDGE_ATTEMPTS = 5
#: How long a whole *batch* may work before it stops starting candidates.
#:
#: The third bound of this shape, and the last request-bound loop to get one.
#: :data:`MAX_CONSECUTIVE_ABANDONMENTS` answers "when is this batch hopeless?";
#: :data:`GENERATION_BUDGET_SECONDS` answers "how long may one request take?";
#: neither answers "when will this outlive the worker?" — which became a real
#: question the moment CARD-086 put gunicorn in front of the admin, because
#: ``generate_batch`` runs synchronously inside the request and a worker killed
#: mid-batch loses everything it had produced.
#:
#: Chosen against measurement, not taste. At density 50 — the value the admin
#: hardcodes — a puzzle costs about 0.06 s at 20x20, 0.55 s at 25x25 and
#: **3.90 s** at 30x30, so a 50-puzzle batch is 3 s at the small end and 195 s
#: at the large one. A flat count cannot be right at both; 75 s is what makes
#: the *same* request safe at every extent, returning about 19 puzzles of a
#: 50-puzzle 30x30 batch instead of dying at 120 s with nothing.
#:
#: Checked **before** each candidate, so one that starts always finishes: the
#: true ceiling is ``BATCH_BUDGET_SECONDS + GENERATION_BUDGET_SECONDS`` = 105 s,
#: which is what has to clear the server's request timeout.
#: ``tests/test_admin_serving.py`` reads ``--timeout`` out of ``start.sh`` and
#: asserts it, the same way it does for the re-grade route — a comment claiming
#: the relationship is exactly what drifts.
BATCH_BUDGET_SECONDS = 75.0
#: The largest batch that may be asked for in one request.
#:
#: Down from 200 (CARD-088, at the owner's proposal). 200 was never reachable
#: at the top of the supported range — a 200-puzzle 30x30 batch needs about 13
#: minutes and the server waits two — so the old ceiling described nothing real.
#:
#: A sanity bound, not the mechanism. :data:`BATCH_BUDGET_SECONDS` is what
#: actually keeps a request inside the worker's patience at every extent; this
#: just stops a caller asking for an obviously unservable number, and gives the
#: form a range to render.
MAX_BATCH_COUNT = 50

#: ADR-0001's hard time bound for one generation *request*, in seconds: 30s up
#: to the largest grid CON-011 supports, 30x30 (ADR-0022 narrowed that ceiling
#: from the 50x50 this constant was originally written against, and CARD-023
#: moved the constant it was stated in without owning this file). Enforced as
#: ADR-0011's cooperative deadline —
#: :func:`generate` turns it into an absolute monotonic instant once per
#: request and hands that same instant to every solver call the request makes,
#: retries included. Deliberately not a per-solve budget: 30 attempts
#: (:data:`MAX_RETRY_ATTEMPTS`) times a per-solve 30s would be a fifteen-minute
#: "timeout", and ADR-0002's attempt bound
#: and this time bound are meant to operate together but independently.
#:
#: ADR-0001's other number, the 5s p95 for grids up to 20x20, is *not* here:
#: that one is a benchmark gate (AC-037, ``tests/bench_generate.py``), not a
#: failure boundary, and ADR-0001's "Neutral" section asks that the asymmetry
#: stay explicit rather than collapsing the two into one enforced constant.
GENERATION_BUDGET_SECONDS = 30.0

#: The ``solution_count`` a candidate must have to pass the uniqueness check.
#: Written as a constant so the one comparison this module makes against the
#: solver's verdict is impossible to misread as a re-derivation of it (G-3).
UNIQUE_SOLUTION_COUNT = 1


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """One generation run as the caller asked for it — an unvalidated intent.

    This is the CLI/domain boundary type: the adapter fills it straight from
    the parsed argv and hands it inward. Its fields are therefore *syntactically*
    typed and widely optional on purpose — ``width``, ``height`` and ``density``
    are plain integers in whatever range the user typed, and ``mode`` is a plain
    string. Nothing here has been checked against a domain rule yet; resolving
    defaults and rejecting out-of-range values is the domain's job, inward of
    COMP-001 (ADR-0010, guardrail G-3).

    Later cards extend this record alongside the parser it mirrors
    (``difficulty``, ``name``, ``image``, further export formats).
    """

    mode: str
    #: ``--size`` (FR-018, ADR-0022/R1), as the two numbers the user stated.
    #: Never one scalar: a grid is a rectangle, and the ``NxM`` token the CLI
    #: parses is what fills these two fields.
    #:
    #: **A bare ``--size 30`` fills exactly one of them** (FR-023,
    #: ADR-0022/R4): the token states one number and says nothing about shape,
    #: so the adapter passes on what was typed rather than inventing a square —
    #: an unstated dimension is not a user intent, and "assume square" is a
    #: claim about the picture that the CLI is the component least equipped to
    #: make. :func:`_resolved_extent` completes it from the source's own shape,
    #: and :attr:`Puzzle.extent` is where the finished pair lives. Both fields
    #: ``None`` still means ``--size`` was omitted altogether.
    #:
    #: Unvalidated like the rest: each side's 10..30 range is a domain rule
    #: (CON-011), checked by ``random_grid.validate_extent`` in whichever source
    #: mode runs — never by an argparse ``type=``/``choices=`` (ADR-0022/R2).
    #: A request may carry ``width=40`` all the way inward and be refused there.
    width: int | None = None
    height: int | None = None
    density: int | None = None
    #: ``--library-key`` (FR-002, CARD-008): which built-in image ``library``
    #: mode draws. Unvalidated like the rest — key membership is a domain rule
    #: (AC-006, ADR-0010), checked by the sourcing module, not here and not by
    #: argparse. Meaningless in the other modes, where it stays ``None``.
    library_key: str | None = None
    #: ``--image`` (FR-003, CARD-015): the picture ``image`` mode converts.
    #: Unvalidated like the rest — whether the path exists and decodes is a
    #: domain concern, checked by the sourcing module and reported as
    #: ``UnreadableImage``, not by an argparse ``type=`` (AC-008, ADR-0010,
    #: guardrail G-5). Meaningless in the other modes, where it stays ``None``.
    image: Path | None = None
    #: AC-139: The original filename of the uploaded image, if available. Used
    #: as a hint for puzzle naming (FR-015). ``None`` when the file was not
    #: uploaded or the filename is unavailable. Unvalidated like the rest —
    #: sanitization happens at the export filename stage (ADR-0016).
    image_filename: str | None = None
    #: ``--name`` (FR-015): the user's name for the puzzle, overriding the
    #: auto-generated one. Unvalidated like the rest — ``--name ""`` parses
    #: fine and is rejected inward, by :meth:`NameContext.name_for`, before any
    #: puzzle exists (AC-045, ADR-0010, guardrail G-5). ``None`` means "no
    #: ``--name`` was given", which is what selects the auto-generated name;
    #: it is *not* the same as the empty string.
    name: str | None = None
    #: ``--difficulty`` (FR-008, CARD-010): the tier the user asked for, as a
    #: plain string — ``"medium"``, ``"Medium"``, ``"extreme"``, whatever was
    #: typed. Which tiers exist is a domain rule, so this is *not* a
    #: :class:`nonogram.difficulty.Tier` yet: ``difficulty.parse_tier`` turns it
    #: into one inward of the CLI and rejects an unsupported tier there
    #: (AC-021, ADR-0010, guardrail G-4). ``None`` means "no tier requested",
    #: which switches POL-004's resample check off — not "Easy".
    difficulty: str | None = None
    seed: int | None = None
    export_formats: tuple[str, ...] = ()
    out: Path | None = None


@dataclass(slots=True)
class NameContext:
    """ADR-0018's *naming context*: what a same-minute collision is judged against.

    FR-015 gives an unnamed puzzle a default name, and ADR-0018 fixes its
    precision at the minute — ``"random-2026-08-27-1430"`` — plus "a small
    disambiguating counter ('-1', '-2', ...) appended only when a same-minute
    auto-generated name already exists in the current run's naming context".
    "The current run's naming context" is this object: the set of auto-names
    already issued through it. :data:`DEFAULT_NAMES` is the process-wide one
    :func:`generate` uses, which for the single-user, single-process CLI of
    CON-001 means "the names this invocation has handed out" — one, normally.

    It exists as an injectable object rather than a module-level counter for
    the reason ADR-0018 anticipates in its own Consequences: the counter branch
    "only executes when two or more same-mode generations land in the same
    clock minute ... which makes it easy to under-test". A test hands
    :func:`generate` a context with a frozen :attr:`clock` and gets that branch
    on demand, without waiting for a minute boundary or monkeypatching
    ``datetime``.

    The disambiguation deliberately mirrors ``export._free_path``'s shape:
    ADR-0018 adopted the counter suffix precisely so that the pipeline's two
    collision points — name generation here, file collision at export — read as
    one idea applied twice rather than two different ones.

    Attributes:
        clock: Reads the wall clock the timestamp is taken from. An argument so
            the convention is testable without freezing real time (AC-042).
        issued: Every auto-generated name this context has handed out. An
            explicit ``--name`` is not recorded here and is never counter-
            suffixed: it is the user's word for the puzzle, and AC-044 asks for
            it back verbatim.
    """

    clock: Callable[[], datetime] = datetime.now
    issued: set[str] = field(default_factory=set)

    def name_for(self, request: GenerationRequest) -> str:
        """The name a puzzle for ``request`` is created with (FR-015).

        Args:
            request: The run as the caller asked for it. Its ``name`` decides
                between the override and the auto-generated default; its
                ``mode`` and ``library_key`` shape the latter.

        Returns:
            ``request.name`` verbatim when one was given, else the
            auto-generated name for the request's mode.

        Raises:
            InvalidPuzzleName: ``request.name`` was given but is empty
                (AC-045). Raised here, inward of argparse, because name
                validity is a domain rule and not argument syntax (ADR-0010,
                guardrail G-5) — and raised *before* :func:`generate` builds
                anything, so a rejected name leaves no puzzle behind.
        """
        if request.name is not None:
            return _validated_name(request.name)
        return self._auto_name(request)

    def _auto_name(self, request: GenerationRequest) -> str:
        """FR-015's default: the library key, the image's file stem, or mode
        plus timestamp."""
        if request.mode == sourcing.LIBRARY and request.library_key:
            # AC-043: the key verbatim, and *not* disambiguated. A library key
            # is not a timestamp, so two "cat" puzzles are two renderings of
            # the same picture rather than a same-minute accident; ADR-0016
            # states outright that an auto-generated key like "cat" "is not
            # guaranteed unique" and leaves that collision to ADR-0017's
            # export-time suffix. A missing key falls through to the timestamp
            # name — the run then fails in sourcing with UnknownLibraryImage,
            # which is the error that request deserves, not a naming one.
            return request.library_key
        if request.mode == sourcing.IMAGE:
            # AC-090/AC-139: Use the uploaded image filename as a hint for the
            # puzzle name. The priority order is: image_filename (uploaded
            # filename with path components removed), then request.image.stem
            # (for testing/CLI), then fall through to timestamp.
            filename_stem = None
            if request.image_filename:
                # AC-139: Extract just the filename without path separators
                # (browsers may send full paths in some edge cases).
                filename_stem = Path(request.image_filename).stem
            elif request.image and request.image.stem:
                filename_stem = request.image.stem
            if filename_stem:
                # AC-090: mirrors the library arm above rather than inventing a
                # parallel mechanism — same collision posture and all. Two "cat"
                # puzzles converted from the same picture are two renderings of
                # one picture, not a same-minute accident, so this is not
                # disambiguated either; ADR-0017's export-time suffix resolves an
                # actual collision, exactly as it does for the library key.
                return filename_stem
        # AC-042. The format itself comes from ``export.default_stem`` rather
        # than being written out a second time here — see :func:`_filename_stem`
        # for why the two must not drift.
        base = export.default_stem(request.mode, moment=self.clock())
        return self._disambiguated(base)

    def _disambiguated(self, base: str) -> str:
        """ADR-0018's counter: ``base``, or the first free ``base-N``."""
        candidates = itertools.chain(
            (base,), (f"{base}-{suffix}" for suffix in itertools.count(1))
        )
        for candidate in candidates:
            if candidate not in self.issued:
                self.issued.add(candidate)
                return candidate
        raise AssertionError("unreachable: count() is infinite")  # pragma: no cover


#: The naming context :func:`generate` uses when the caller does not supply
#: one: one per process, which is ADR-0018's "current run" for a CLI that
#: generates a single puzzle per invocation (CON-001).
DEFAULT_NAMES = NameContext()


def _validated_name(name: str) -> str:
    """AC-045: an explicit name has to be a name.

    Whitespace-only is rejected alongside the empty string the criterion names:
    the two are the same thing to every consumer the name has — a PDF header
    that renders as blank (FR-016) and a filename stem that sanitizes away to
    nothing (ADR-0016). Nothing else is refused and nothing is rewritten: the
    name is the user's, and ADR-0016's filesystem sanitization applies to the
    *filename* derived from it, not to the name itself (:func:`_filename_stem`).
    """
    if not name.strip():
        raise InvalidPuzzleName(
            "puzzle name must not be empty; pass a name to --name or omit the "
            "flag to get the auto-generated one"
        )
    return name


@dataclass(slots=True)
class RetryCounter:
    """INV-003's counter for one bounded loop kind (NFR-002, ADR-0002).

    The invariant — "a puzzle's automatic-retry counter never exceeds its
    configured maximum bound" — is a property of *this type*, which is how it
    stays one invariant with one home across the three loop kinds that will
    eventually exist. :meth:`record_attempt` is the only way to advance a
    counter and it refuses to advance past :attr:`bound`, so a caller cannot
    overshoot even by ignoring :attr:`exhausted`.

    Attributes:
        kind: What is being retried — ``"regenerate"`` here, ``"resample"``
            and ``"pixel-nudge"`` in the later cards. Appears in the
            abandonment message, so it is the user's word for the loop.
        bound: The maximum number of attempts, from ADR-0002.
        attempts: How many attempts have been started. Counted at the *start*
            of an attempt, so an attempt that raises part-way through is still
            counted — a retry budget must not be refunded by a crash.
    """

    kind: str
    bound: int
    attempts: int = 0

    @property
    def exhausted(self) -> bool:
        """Has the bound been reached? (POL-005's condition.)"""
        return self.attempts >= self.bound

    def record_attempt(self) -> int:
        """Start one attempt and return its 1-based number.

        Raises:
            RuntimeError: the counter is already exhausted. Not a
                ``nonogram.errors`` type and not ``GenerationAbandoned``:
                abandonment is a domain outcome the *loop* reports, whereas
                reaching this line means a caller drove the counter past its
                bound by hand, which is a programming error in the pipeline.
        """
        if self.exhausted:
            raise RuntimeError(
                f"{self.kind} counter is exhausted "
                f"({self.attempts}/{self.bound}); INV-003 forbids another attempt"
            )
        self.attempts += 1
        return self.attempts


def run_bounded[T](
    counter: RetryCounter,
    attempt: Callable[[], T | None],
    *,
    reason: str,
) -> T:
    """Run ``attempt`` until it produces a candidate, or abandon (POL-005).

    The shared counted-loop primitive behind every bounded retry in the
    pipeline. ``attempt`` is called with no arguments and returns the accepted
    candidate, or ``None`` to say "this one is no good, try another" — the
    single sentinel is why the callable's success type must not itself be
    ``None``.

    Args:
        counter: The loop's INV-003 counter. It is advanced here and nowhere
            else, and it is *not* reset — a counter carried on the aggregate
            keeps the whole run's history, which is what makes the bound apply
            per generation request rather than per call to this function.
        attempt: Produces one candidate or ``None``. Anything it raises
            propagates unchanged: only a rejected candidate is a retry.
        reason: The domain-level explanation for the abandonment message —
            what the candidates kept failing, in the user's terms. The
            primitive owns the counting; the caller owns the wording.

    Returns:
        Whatever ``attempt`` returned on the first non-``None`` call.

    Raises:
        GenerationAbandoned: the bound was reached with every attempt
            rejected (POL-005, CMD-011, EVT-012). The message names the count
            and the bound so the failure reads as "infeasible request", not
            "internal error".
    """
    while not counter.exhausted:
        counter.record_attempt()
        candidate = attempt()
        if candidate is not None:
            return candidate
    raise GenerationAbandoned(
        f"abandoned after {counter.attempts} {counter.kind} "
        f"attempt{'s' if counter.attempts != 1 else ''} "
        f"(bound: {counter.bound}) — {reason}"
    )


#: The region a repair took its pair from: the cells the solver's two
#: witnesses disagree on (ADR-0024's primary rule).
WITNESS_DISAGREEMENT_REGION = "witness-disagreement"
#: The region a repair took its pair from when the disagreement set held no
#: filled/empty pair of the parent grid: the first-fixed-point undecided mask
#: (ADR-0024's fallback rule — measured to fire, see :func:`repair_candidate`).
UNDECIDED_MASK_REGION = "undecided-mask"


@dataclass(frozen=True, slots=True)
class Repair:
    """One POL-006 repair of a candidate grid: what changed, and from where.

    A value, not an action: :func:`repair_candidate` computes it and nothing
    is judged until the orchestrator hands :attr:`grid` to the one
    ``judge_candidate`` path like any other candidate (ADR-0024/R1).

    Attributes:
        grid: The repaired grid — the parent with exactly two cells swapped.
        region: Which rule chose the pair, :data:`WITNESS_DISAGREEMENT_REGION`
            or :data:`UNDECIDED_MASK_REGION`. Carried for the run summary the
            K recalibration reads, so that the fallback's share of repairs is
            an observed number rather than an assumption.
        emptied: ``(row, column)`` of the parent's filled cell that became
            empty.
        filled: ``(row, column)`` of the parent's empty cell that became
            filled. Exactly one of each, which is what makes the repaired
            grid's filled count its parent's (ADR-0024/R3, AC-114).
    """

    grid: Grid
    region: str
    emptied: tuple[int, int]
    filled: tuple[int, int]


def _region_cells(mask: list[list[bool]] | None) -> list[tuple[int, int]]:
    """The ``True`` cells of a grid-shaped mask, ranked by (row, column).

    The ranking is ADR-0024/R4's and comes for free from reading the mask in
    row-major order — there is no sort, no rng and no host state anywhere in
    the choice, so the pair a repair flips is a pure function of the grid and
    the solver's report.
    """
    if not mask:
        return []
    return [
        (row_index, column_index)
        for row_index, row in enumerate(mask)
        for column_index, cell in enumerate(row)
        if cell
    ]


def _disagreement_mask(witnesses: tuple[Grid, ...] | None) -> list[list[bool]]:
    """The cells the solver's two witnesses differ on, grid-shaped.

    Empty when the solve had fewer than two solutions in hand — a candidate
    the solver did not report ``MANY`` for has no ambiguity to locate, and in
    random mode there is no such rejected candidate (the clues come from a
    real grid, so a count of 0 cannot occur). The pair is read positionally:
    the witnesses are two solutions of the same clue set and therefore the
    same shape.
    """
    if witnesses is None or len(witnesses) < 2:
        return []
    first, second = witnesses[0], witnesses[1]
    return [
        [left != right for left, right in zip(first_row, second_row, strict=True)]
        for first_row, second_row in zip(first, second, strict=True)
    ]


def _first_pair_in_region(
    grid: Grid, cells: list[tuple[int, int]]
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """The region's first filled and first empty cell *of the parent grid*.

    ``cells`` arrives ranked by (row, column), so "first" is ADR-0024/R4's
    rank and this walk is the whole of the pair choice. Returns ``None`` when
    the region holds no cell of one of the two kinds — which is exactly the
    condition ADR-0024 falls back to the wider mask on, and which the
    CARD-073 review measured firing in 9 of 241 real MANY verdicts (~3.7%),
    every one of them a disagreement set that was entirely empty in the
    parent. Cells outside the grid are skipped rather than trusted.
    """
    emptied: tuple[int, int] | None = None
    filled: tuple[int, int] | None = None
    for row_index, column_index in cells:
        if row_index >= len(grid) or column_index >= len(grid[row_index]):
            continue
        if grid[row_index][column_index]:
            if emptied is None:
                emptied = (row_index, column_index)
        elif filled is None:
            filled = (row_index, column_index)
        if emptied is not None and filled is not None:
            break
    if emptied is None or filled is None:
        return None
    return emptied, filled


def _lineage_key(grid: Grid) -> tuple[tuple[bool, ...], ...]:
    """A hashable identity for a candidate grid, for repeat detection only.

    Used by :func:`generate` to notice that a repair has handed back a grid its
    own lineage already judged. Nothing decides anything on this — the pair
    choice is still ADR-0024/R4's first-by-(row, column) rule and is untouched
    — so building one tuple per attempt (at most :data:`MAX_RETRY_ATTEMPTS` of
    them, against a solve
    that costs orders of magnitude more) buys the calibration number for free.
    """
    return tuple(tuple(row) for row in grid)


def repair_candidate(
    grid: Grid,
    *,
    witnesses: tuple[Grid, ...] | None,
    undecided_mask: list[list[bool]] | None,
) -> Repair | None:
    """POL-006 / CMD-014: flip one filled and one empty cell inside the region.

    ADR-0024's repair, as a pure function of the candidate grid and what the
    solver reported about it — no rng draw, no clock, no host state, so the
    same seed replays the same repair lineage on every machine (ADR-0024/R4,
    ADR-0015, guardrail G-5).

    The region is the witness-disagreement set; the undecided mask is the
    fallback, used only when the disagreement set holds no filled/empty pair
    of the parent. That fallback is a live path, not a defensive branch: the
    per-row filled-count argument in ADR-0024's Context only applies when the
    candidate is itself one of the two witnesses, and CARD-073's measurement
    found 9 of 241 real MANY verdicts where it does not hold. Both rules are
    written as one loop over two candidate regions so neither can be dead.

    Cells outside the chosen region are never touched, and the flip is one of
    each kind, so the repaired grid has its parent's filled count exactly and
    the requested density holds by construction rather than by ADR-0003's
    tolerance (ADR-0024/R3, AC-132, AC-114).

    Returns:
        The :class:`Repair`, or ``None`` when neither region holds a
        filled/empty pair — there is then nothing this rule can flip, and the
        caller ends the lineage and redraws (POL-001).
    """
    for region, cells in (
        (WITNESS_DISAGREEMENT_REGION, _region_cells(_disagreement_mask(witnesses))),
        (UNDECIDED_MASK_REGION, _region_cells(undecided_mask)),
    ):
        pair = _first_pair_in_region(grid, cells)
        if pair is None:
            continue
        emptied, filled = pair
        repaired = [list(row) for row in grid]
        repaired[emptied[0]][emptied[1]] = False
        repaired[filled[0]][filled[1]] = True
        return Repair(grid=repaired, region=region, emptied=emptied, filled=filled)
    return None


@dataclass(slots=True)
class RecoveryLog:
    """ADR-0024's per-run recovery tally — observability, and nothing else.

    Not a counter in INV-003's sense and deliberately not a
    :class:`RetryCounter`: nothing reads these numbers to decide anything, no
    bound is checked against them, and deleting the field would change no
    verdict. They exist because ADR-0024 names the K recalibration as owed and
    says what data it needs — repairs versus redraws, and how many lineages
    ran to the K cap. Additive; no export schema changes (ADR-0023 untouched).

    Attributes:
        redraws: Fresh grids drawn from the source (POL-001).
        repairs: Candidates produced by flipping a pair (POL-006). With
            :attr:`redraws` this sums to the attempts the one
            :attr:`Puzzle.regenerate` counter recorded.
        repairs_from_fallback_region: How many of :attr:`repairs` had to take
            their pair from the undecided mask because the witness
            disagreement set held no filled/empty pair.
        lineages_at_repair_cap: Lineages that made :data:`MAX_CONSECUTIVE_REPAIRS`
            repairs without a unique verdict and were discarded for a redraw —
            the "K was too tight / too loose" signal.
        lineages_without_repairable_region: Lineages ended early because
            neither region held a pair to flip. Distinct from the above: it
            says the repair rule had nothing to say, not that it was tried K
            times and failed.
        repeated_attempts: Repairs that re-judged a grid their own lineage had
            already judged — the rule flipped a pair back and the lineage
            began to cycle. Counted because it is the one number that tells
            :attr:`lineages_at_repair_cap` apart into its two populations: a
            lineage still reaching new grids when K stopped it might convert
            with a larger K, and a lineage cycling between two grids provably
            will not, however large K grows. Without this field the
            recalibration ADR-0024 defers would read one number for both.
    """

    redraws: int = 0
    repairs: int = 0
    repairs_from_fallback_region: int = 0
    lineages_at_repair_cap: int = 0
    lineages_without_repairable_region: int = 0
    repeated_attempts: int = 0

    @property
    def attempts(self) -> int:
        """Redraws plus repairs — what the one ADR-0002 bound counted."""
        return self.redraws + self.repairs

    def describe(self) -> str:
        """One line for a run summary, in the user's terms."""
        return (
            f"{self.attempts} recovery attempt"
            f"{'s' if self.attempts != 1 else ''}: "
            f"{self.redraws} redraw{'s' if self.redraws != 1 else ''}, "
            f"{self.repairs} repair{'s' if self.repairs != 1 else ''} "
            f"({self.repairs_from_fallback_region} from the undecided mask); "
            f"{self.lineages_at_repair_cap} lineage"
            f"{'s' if self.lineages_at_repair_cap != 1 else ''} reached the "
            f"repair cap of {MAX_CONSECUTIVE_REPAIRS}"
            f", {self.repeated_attempts} of the repairs re-judged a grid the "
            f"lineage had already seen"
        )


@dataclass(slots=True)
class Puzzle:
    """AGG-001 — one generation request's puzzle, across all of its retries.

    Created once per :func:`generate` call and **not** re-created per retry:
    the candidate grid and its clues are replaced in place while the counters
    and the request they were made for stay. That is precisely why INV-003's
    retry counter is one invariant on one aggregate rather than a
    cross-aggregate concern (aggregates.yml, AGG-001).

    Three invariants constrain it, and each has exactly one enforcement point
    here:

    INV-001  grid and clues are only ever written together, by
             :meth:`record_candidate`, so the clues can never be stale with
             respect to the grid.
    INV-002  :attr:`ready_for_export` is written only by
             :meth:`confirm_uniqueness`, only when the solver reported exactly
             one solution. :meth:`require_ready_for_export` is the gate the
             export cards call before writing anything.
    INV-003  every counter is a :class:`RetryCounter`, advanced only by
             :func:`run_bounded`. :attr:`regenerate` (POL-001),
             :attr:`resample` (POL-004) and :attr:`nudge` (POL-002) are all
             three of them, and no other field counts anything a bound is
             checked against. :attr:`recovery` is a tally rather than a
             counter: it records how the regenerate counter's attempts divided
             between redraws and repairs (ADR-0024), and nothing is ever
             compared to it.
    """

    #: The request this puzzle is being generated for. Held whole rather than
    #: copied field by field: the aggregate's mode/extent/density *are* the
    #: request's, and a later export (FR-012, ADR-0015) has to record the
    #: parameters the run was asked for anyway.
    request: GenerationRequest
    #: The run's effective seed — the requested one, or the one drawn for the
    #: user when ``--seed`` was absent (ADR-0015). Always concrete, so a run
    #: is reproducible after the fact even when nobody asked for a seed.
    seed: int
    #: The grid's *resolved* ``(width, height)`` — what :func:`_resolved_extent`
    #: made of the request's extent and the source's own shape (FR-023).
    #:
    #: The effective counterpart of the request's own pair, in the same way
    #: :attr:`seed` is the effective counterpart of ``request.seed``: a bare
    #: ``--size N`` arrives with one side unstated, and this is where the pair
    #: the run actually produced — and exports (FR-012) — is recorded. Written
    #: once by :func:`generate`, before the first candidate, and never again;
    #: the derivation depends on the request and the source, neither of which a
    #: retry changes.
    #:
    #: A pair and not two fields, for ADR-0022/R1's reason: extent crosses a
    #: boundary whole, and an aggregate attribute is a boundary.
    #:
    #: ``None`` only for an aggregate assembled by hand rather than by
    #: :func:`generate`, exactly like :attr:`name` — :attr:`width` and
    #: :attr:`height` then fall back to the request's unvalidated pair, which is
    #: what such an aggregate was carrying before this field existed.
    extent: tuple[int, int] | None = None
    #: FR-015's name, as :meth:`NameContext.name_for` resolved it — the library
    #: key, ``"<mode>-<YYYY-MM-DD>-<HHMM>"`` or whatever ``--name`` said.
    #:
    #: Written once, by :func:`generate`, *before* the first attempt, and never
    #: again: a regenerate replaces the candidate grid, not the puzzle, so the
    #: name a run reports is the name it started with (guardrail G-6, AGG-001).
    #:
    #: ``None`` only for an aggregate assembled by hand rather than by
    #: :func:`generate` — the same partially-built state :attr:`grid` and
    #: :attr:`clues` start in. :func:`export_puzzle` falls back to
    #: ``export.default_stem`` for one of those; nothing produced by the
    #: pipeline ever takes that path.
    name: str | None = None
    #: FR-008's requested tier, resolved once by :func:`generate` *before* the
    #: first candidate exists and never re-read from the request afterwards —
    #: the tier a run is judged against is fixed for the run, exactly like
    #: :attr:`name` (AC-020).
    #:
    #: ``None`` when the user asked for no particular difficulty, which is what
    #: makes POL-004's check vacuous rather than absent: the loop still runs,
    #: every candidate is still scored, and the first unique one is accepted.
    requested_tier: difficulty.Tier | None = None
    #: POL-001's counter (INV-003). Bound from ADR-0002.
    regenerate: RetryCounter = field(
        default_factory=lambda: RetryCounter("regenerate", MAX_REGENERATE_ATTEMPTS)
    )
    #: POL-004's counter (INV-003) — one per aggregate, alongside
    #: :attr:`regenerate` and :attr:`nudge`, sharing ADR-0002's bound with the
    #: former through :data:`MAX_RETRY_ATTEMPTS` rather than restating it.
    resample: RetryCounter = field(
        default_factory=lambda: RetryCounter("resample", MAX_RESAMPLE_ATTEMPTS)
    )
    #: POL-002's counter (INV-003, FR-013, CARD-016): how many pixel nudges
    #: this run has applied to an uploaded image's conversion. The third and
    #: last of the model's bounded loops, and the only one with its own bound
    #: — :data:`MAX_NUDGE_ATTEMPTS`, 5 rather than 20.
    #:
    #: Zero for every run that is not in image mode, and zero for an image run
    #: whose conversion was uniquely solvable first time: the loop is entered
    #: only by the branch that needs it. CARD-017 reports this number to the
    #: user; this card only carries it (guardrail G-5).
    nudge: RetryCounter = field(
        default_factory=lambda: RetryCounter("pixel-nudge", MAX_NUDGE_ATTEMPTS)
    )
    #: ADR-0024's run summary: how this run's recovery attempts divided
    #: between POL-001 redraws and POL-006 repairs, and how the repair rule
    #: fared. A *tally*, not a counter — it bounds nothing and INV-003 does not
    #: reach it, which is why it is a log object beside the three
    #: :class:`RetryCounter` fields rather than a fourth one (see
    #: :class:`RecoveryLog`). Zero everywhere for a run that never had a
    #: candidate rejected, and ``repairs == 0`` for every mode but random
    #: (ADR-0024/R5).
    recovery: RecoveryLog = field(default_factory=RecoveryLog)
    #: The current candidate's solution grid, or ``None`` before the first one
    #: is sourced.
    grid: Grid | None = None
    #: The current candidate's clues — always the run-length encoding of
    #: :attr:`grid` (INV-001).
    clues: clue_derivation.Clues | None = None
    #: The solver's verdict on the current candidate: ``0``, ``1`` or
    #: ``solver.MANY``. The solver's number, stored as given (G-3).
    solution_count: int | None = None
    #: COMP-006's score for the current candidate on ADR-0029's 0..100 scale,
    #: or ``None`` while the candidate is unscored — which is every candidate
    #: that has not yet passed the uniqueness check, since the score of a
    #: non-unique clue set means nothing (ADR-0029 reports no rung attribution
    #: for one at all). Dropped by :meth:`record_candidate` along with the rest
    #: of the previous candidate's verdict, so a resampled candidate cannot be
    #: checked against its predecessor's score (AC-026).
    difficulty_score: float | None = None
    #: The branch count of the solve that produced :attr:`difficulty_score`, or
    #: ``None`` while the candidate is unscored. Recorded *beside* the score and
    #: never folded into it, because ADR-0025 makes them two different kinds of
    #: fact: the score grades line reasoning, and this one number decides
    #: ``Tier.GUESS`` on its own (EC-015). :attr:`difficulty_tier` needs both,
    #: which is exactly why ``difficulty.classify`` takes both.
    #:
    #: Stored as the solver reported it, like :attr:`solution_count` and
    #: :attr:`difficulty_score` (guardrail G-3) — this module composes
    #: capabilities, it does not second-guess them, and in particular it does
    #: not compare this number against anything itself (ADR-0025/R2).
    branch_nodes: int | None = None
    #: The cells line logic left undecided at the current candidate's **first**
    #: propagation fixed point, grid-shaped (FR-024), or ``None`` while the
    #: candidate is unjudged. Stored exactly as the solver reported it, the way
    #: :attr:`solution_count` and :attr:`difficulty_score` are (guardrail G-3):
    #: this module composes capabilities, it does not second-guess them.
    #:
    #: Carried, not consumed (CARD-073 guardrail G-4). POL-002's nudge reads it
    #: in CARD-075.
    undecided_mask: list[list[bool]] | None = None
    #: The solutions the current candidate's solve had in hand: empty for a
    #: candidate with no solution, one grid for a unique one, and the two
    #: distinct witnesses for a candidate the solver reported ``solver.MANY``
    #: for — the pair ADR-0024's repair draws its cells from in CARD-074.
    #:
    #: ``None`` while the candidate is unjudged, which is a different statement
    #: from the empty tuple ("judged, and there was nothing to find").
    witnesses: tuple[Grid, ...] | None = None
    #: The ADR-0029 ladder rung that settled each cell of the current candidate
    #: in the one verifying solve, grid-shaped, with ``None`` per cell for a
    #: cell no forced deduction settled; ``None`` as a whole while the
    #: candidate is unjudged.
    #:
    #: Also carried and not consumed: CARD-076 grades from these and CARD-072
    #: persists the rung list beside them. They come off the solve that already
    #: happened — nothing here re-solves to classify (ADR-0029/R2).
    rung_tags: list[list[str | None]] | None = None
    #: Which way an uploaded picture was reduced to black and white —
    #: ``sourcing.image.THRESHOLD`` or ``sourcing.image.DITHER`` (FR-027,
    #: ADR-0026/ADR-0028). ``None`` for random and library mode, which have no
    #: picture and so nothing to record.
    #:
    #: Recorded rather than inferred, and set once per request before the
    #: first candidate: two pictures that differ only in mid-tone content take
    #: different paths, so "which one did this puzzle get" cannot be recovered
    #: from the grid afterwards. CARD-072 carries it into the export metadata;
    #: until then it is read by CARD-079's review render and by nothing else.
    binarisation: str | None = None
    #: INV-002's gate. Only :meth:`confirm_uniqueness` writes it.
    ready_for_export: bool = False

    @property
    def mode(self) -> str:
        """How the grid is sourced (AGG-001 attribute)."""
        return self.request.mode

    @property
    def width(self) -> int | None:
        """The grid's width — resolved when :attr:`extent` is set (AGG-001).

        Reads :attr:`extent` first and the request only as a fallback, because
        since FR-023 the request's own pair may be half-stated: a bare
        ``--size 25`` on a portrait picture is ``width=25, height=None`` in the
        request and ``(18, 25)`` in :attr:`extent`, and 18 is the width the run
        produced, exported and printed. Falling back keeps a hand-assembled
        aggregate reading exactly as it did before this field existed.
        """
        return self.extent[0] if self.extent is not None else self.request.width

    @property
    def height(self) -> int | None:
        """The grid's height — resolved when :attr:`extent` is set (AGG-001).

        Two accessors rather than one ``size``: ADR-0022/R1 puts extent across
        every boundary as a pair, and an aggregate attribute is a boundary.
        """
        return self.extent[1] if self.extent is not None else self.request.height

    @property
    def density(self) -> int | None:
        """Requested fill percentage, still unvalidated (AGG-001 attribute)."""
        return self.request.density

    def record_candidate(self, grid: Grid) -> clue_derivation.Clues:
        """Adopt ``grid`` as the current candidate and derive its clues.

        The two writes are one operation because INV-001 relates them: a
        caller that could set the grid alone could leave the previous
        candidate's clues attached to it. Returns the fresh clues so the
        caller can hand them to the solver without reading them back.

        Replacing a candidate also drops the verdict about the *previous* one:
        an unverified candidate carries no ``solution_count`` and is not
        exportable, which keeps INV-002 true between the moment a candidate is
        discarded and the moment its replacement is judged.
        """
        self.grid = grid
        self.clues = clue_derivation.compute_clues(grid)
        self.solution_count = None
        self.difficulty_score = None
        # The score's companion (ADR-0025) goes with the score: a branch count
        # left behind would classify the replacement candidate Guess on the
        # strength of its predecessor's solve, which is AC-026 the other way up.
        self.branch_nodes = None
        # Everything the previous candidate's solve reported goes with it, for
        # the same reason its score does: a mask, a witness pair or a rung map
        # left attached to a replacement grid would describe the wrong puzzle.
        self.undecided_mask = None
        self.witnesses = None
        self.rung_tags = None
        self.ready_for_export = False
        return self.clues

    def confirm_uniqueness(self, solution_count: int) -> bool:
        """Record the solver's verdict and open the export gate iff it is 1.

        INV-002's single enforcement point (ADR-0007). ``solution_count``
        arrives from ``solver.solve`` and is stored as given: the orchestrator
        compares it against 1 and never recomputes, second-guesses or
        short-circuits it (guardrail G-3, CON-005).

        Returns:
            Whether the candidate passed — i.e. whether the caller may stop
            retrying (POL-001's condition, inverted).
        """
        self.solution_count = solution_count
        self.ready_for_export = solution_count == UNIQUE_SOLUTION_COUNT
        return self.ready_for_export

    @property
    def difficulty_tier(self) -> difficulty.Tier | None:
        """Which tier the current candidate actually classified into (ADR-0025).

        The counterpart of :attr:`requested_tier`: what the puzzle turned out
        to be, rather than what was asked for. ``None`` until the candidate has
        been scored.

        Classified through ``difficulty.classify`` on every read instead of
        being stored alongside the score, so the tier and the rule it comes from
        cannot fall out of step with each other — and through *that* function
        rather than a comparison here, because ADR-0025/R2 allows exactly one
        tier classifier in the package and it is COMP-006's. This module hands
        it the two facts the one verifying solve reported and takes the answer.
        """
        if self.difficulty_score is None or self.branch_nodes is None:
            return None
        return difficulty.classify(self.difficulty_score, self.branch_nodes)

    @property
    def difficulty_in_requested_tier(self) -> bool:
        """POL-004's condition: does the current candidate match the request?

        One tier comparison, as it always was — ADR-0025 keeps the predicate a
        single test and makes ``guess`` a legitimate thing to ask for, so a run
        requesting it keeps branching candidates and a run requesting anything
        else discards them by this same line.

        ``True`` when no tier was requested — there is nothing to miss — and
        ``False`` for a candidate that has not been scored yet, so "in tier" is
        never claimed on the strength of a previous candidate's solve (AC-026).
        """
        if self.requested_tier is None:
            return True
        return self.difficulty_tier is self.requested_tier

    def record_difficulty(self, score: float, branch_nodes: int) -> bool:
        """Record COMP-006's grade for the current candidate and judge it.

        POL-004's decision point. Both numbers are stored as they were given —
        the score unrounded and un-bucketed, the branch count untouched — for
        the same reason the solver's count is (guardrail G-3): this module
        composes capabilities, it does not second-guess them.

        Args:
            score: ``difficulty.score_difficulty``'s number for the solve that
                just judged this candidate.
            branch_nodes: the *same* solve's branch count. Taken as a second
                argument rather than derived from the score, because it cannot
                be: EC-015 makes ``Tier.GUESS`` a fact about the solve, and no
                threshold on the score can recover it.

        Returns:
            :attr:`difficulty_in_requested_tier` for the grade just recorded:
            ``True`` when the candidate may be kept (AC-024), ``False`` when
            POL-004's resample must fire (AC-025).
        """
        self.difficulty_score = score
        self.branch_nodes = branch_nodes
        return self.difficulty_in_requested_tier

    def require_ready_for_export(self) -> None:
        """The INV-002 gate: raise unless the uniqueness check has passed.

        Lives here and not in COMP-007 (ADR-0007's single-enforcement-point
        rule): the export renderers call this before writing anything, so
        there is one place that decides what "exportable" means.

        Raises:
            ExportRejected: the puzzle has not been confirmed unique.
        """
        if not self.ready_for_export:
            raise ExportRejected(
                "puzzle is not ready for export: its uniqueness check has not "
                f"confirmed exactly one solution (solution_count="
                f"{self.solution_count!r})"
            )


def _shape_arguments(request: GenerationRequest) -> tuple[object, ...]:
    """The mode-specific arguments of ``request``'s *source-shape* reporter.

    The counterpart of :func:`_source_arguments` for ``sourcing.shape_for_mode``
    (FR-023), and shorter for a reason that is part of the rule rather than an
    accident of the signatures: a source's own shape depends on the source and
    on nothing else, so each mode's reporter takes the mode's own leading
    argument and no extent. The random source, having no shape of its own, takes
    nothing at all.

    Every registered mode gets a branch and the ``else`` raises, for the same
    reason :func:`_source_arguments` does: a mode in the dispatch table but not
    here would otherwise bind the wrong argument several frames from the cause.

    Raises:
        ValueError: ``request.mode`` has a registered shape reporter but no
            argument list here — a wiring bug inside the pipeline.
    """
    mode = request.mode
    if mode == sourcing.RANDOM:
        return ()
    if mode == sourcing.LIBRARY:
        return (request.library_key,)
    if mode == sourcing.IMAGE:
        return (request.image,)
    raise ValueError(f"no shape argument list for mode {mode!r}")


def _resolved_extent(request: GenerationRequest) -> tuple[int, int]:
    """The ``(width, height)`` the grid actually gets (FR-018, FR-023).

    The composing layer's part of ADR-0022/R4, and the whole of it: the *rule*
    is ``random_grid``'s two pure functions, the *shape* is the mode's own, and
    what happens here is deciding which of the two questions this request asks.

    An extent with **both** sides stated is an explicit ``--size WxH``: it says
    everything there is to say about the grid, so it is range-checked and used
    as given, and the source's shape is never even consulted (AC-096). That is
    also why an explicit request in image mode still decodes its file exactly
    once — the derived path is the only one that pays for a shape.

    An extent with **one** side stated is a bare ``--size N``, and it is
    completed from the source's own shape (AC-092, AC-094, AC-095).

    An extent with **neither** side stated is ``--size`` omitted, and falls
    through to the same shared validator that has always refused it, with the
    same message (``grid width must be between 10 and 30 inclusive, got None``).

    Raises:
        SizeOutOfRange: the extent is out of range, absent, or — as
            ``SizeTooSmallForSource`` — is a bare N too small to follow this
            source's shape (AC-098).
        UnknownLibraryImage, UnreadableImage: the shape could not be read
            because the source itself is unusable. Raised here rather than in
            sourcing only because the derivation asks first; the message is the
            source module's own either way.
    """
    width, height = request.width, request.height
    if (width is None) == (height is None):
        return random_grid.validate_extent(width, height)
    shape = sourcing.shape_for_mode(request.mode)(*_shape_arguments(request))
    return random_grid.derive_extent(width, height, *shape)


def _source_arguments(
    request: GenerationRequest, extent: tuple[int, int]
) -> tuple[object, ...]:
    """The mode-specific leading arguments of ``request``'s grid source.

    ``sourcing.for_mode`` hands back a callable without collapsing the modes
    behind one signature, because they do not share a parameter list — random
    takes a density, library takes a key, image takes a path. What they *do*
    share is the grid's ``(width, height)`` extent, which sits in the same
    place in all three: straight after the mode's own leading argument
    (ADR-0022/R1 — the pair travels together, and no mode is handed one number
    to square). Assembling that list is the composing layer's job, and this is
    the one place it happens (ADR-0007: the orchestrator composes, the
    capability modules do not know about each other).

    ``extent`` is :func:`_resolved_extent`'s answer and **not**
    ``request.width``/``request.height``. Since FR-023 those two are not the
    same thing: a bare ``--size N`` reaches the domain with one side unstated,
    and what the source must be handed is the pair that survived resolution.
    Taking it as an argument rather than reading it back off the request is what
    makes that impossible to get wrong — there is no field here to read the
    half-stated pair out of.

    The run's ``random.Random`` is *not* included: every source takes it last
    and :func:`generate` appends it at the call site, so a mode cannot
    accidentally be wired up without it (ADR-0015).

    Every registered mode gets its own branch, and the ``else`` raises
    (CARD-008 review follow-up). Until CARD-015 the random shape was an
    implicit fallback, on the reasoning that ``sourcing.for_mode`` has already
    rejected an unknown mode — true only of a mode that is not *registered* at
    all. The moment ``image`` was registered, that fallback would have called
    ``image.generate(size, density, rng)`` and bound a file path to an integer,
    turning a one-line wiring omission into a confusing failure several frames
    away. A mode registered in the dispatch table but not here is now a loud,
    local ``ValueError`` instead.

    Raises:
        ValueError: ``request.mode`` has a registered source but no argument
            list here. A wiring bug inside the pipeline, deliberately not a
            ``nonogram.errors`` type — the same reasoning ``sourcing.for_mode``
            gives for its own ``ValueError``.
    """
    mode = request.mode
    width, height = extent
    if mode == sourcing.RANDOM:
        return (width, height, request.density)
    if mode == sourcing.LIBRARY:
        return (request.library_key, width, height)
    if mode == sourcing.IMAGE:
        return (request.image, width, height)
    raise ValueError(f"no source argument list for mode {mode!r}")


#: POL-001's abandonment wording when no tier was requested: what 20 discarded
#: candidates were all failing, in the user's terms, plus the levers that
#: change the answer. Unchanged from CARD-005 — a run with no ``--difficulty``
#: is the run CARD-005 shipped, message included (guardrail G-5).
_UNIQUENESS_REASON = (
    "no candidate grid had exactly one solution; try a different "
    "--size/--density combination, or another --seed"
)


def _band_text(tier: difficulty.Tier) -> str:
    """``"Hard band (66-100) of the 0-100 difficulty scale"`` — a tier named
    *and* placed.

    The band is spelled out rather than left as a bare tier name because the
    user cannot see the 0..100 scale from the outside; saying where the tier
    sits on it is what makes an abandonment message actionable rather than
    merely truthful (AC-027's "clear error").

    ``Tier.GUESS`` has no band to spell out (ADR-0025: it is keyed on the
    solve's branch count, not on a score), so it is described by the fact that
    defines it instead — and the mention of the scale goes with the band, since
    telling a user to look for that tier on a scale it does not live on is the
    opposite of actionable. That is why the whole phrase is built here rather
    than assembled by each caller around a bare band.
    """
    band = tier.band
    if band is None:
        return f"{tier.label} tier (puzzles whose one verifying solve had to branch)"
    low, high = band
    return f"{tier.label} band ({low:g}-{high:g}) of the 0-100 difficulty scale"


def _uniqueness_reason(tier: difficulty.Tier | None) -> str:
    """POL-001's abandonment wording, in the presence of a requested tier.

    The two loops share one attempt budget (see :func:`generate`), so when a
    tier is requested the regenerate loop can be the one that exhausts it even
    though candidates *were* found unique and discarded for their difficulty.
    Reporting only the uniqueness failure there would name the wrong cause, so
    this message names both checks and says outright that they share a budget —
    which is also the fact a user needs to make sense of the attempt count when
    they can see the tool rejected candidates for two different reasons.
    """
    if tier is None:
        return _UNIQUENESS_REASON
    return (
        "no candidate grid was both uniquely solvable and classified into the "
        f"{_band_text(tier)} — the two checks "
        f"share one {MAX_RETRY_ATTEMPTS}-attempt budget; try another "
        "--difficulty, a different --size/--density combination, or another "
        "--seed"
    )


def _image_uniqueness_reason(solution_count: int | None) -> str:
    """POL-003's wording when the nudge cap is reached (AC-035, AC-036).

    Image mode's counterpart of :func:`_uniqueness_reason`, and it has to be a
    different sentence rather than a reused one: what ran here was not POL-001.
    The image was *never re-drawn* — an uploaded picture converts to the same
    grid every time — and what the cap counts is edits to that one conversion,
    so a message about :data:`MAX_RETRY_ATTEMPTS` discarded candidate grids would
    describe a loop that
    never ran (CARD-015 guardrail G-4).

    Three things it has to say, and each is an acceptance criterion rather than
    a courtesy:

    * what failed — the conversion is not a puzzle, and why (the count);
    * that the tool has **stopped** (POL-003, AC-035). A user who has watched
      the tool silently repair other runs needs to be told that the repair was
      tried, was bounded, and is over — otherwise "failed" reads as either
      "gave up immediately" or "may still be editing my picture";
    * what to do next (AC-036) — a different image, or a different ``--size``.

    ``--seed`` is deliberately absent from those levers: the conversion does not
    draw from the RNG and neither does the nudge, so re-seeding an image run
    reproduces exactly the same grid and exactly the same five edits.

    Args:
        solution_count: The solver's verdict on the conversion, as recorded.
            The *initial* one — this string is built before the nudge loop
            starts, because :func:`run_bounded` takes its reason up front, and
            the initial conversion is the thing the user actually handed over.

    Returns:
        The reason clause; :func:`run_bounded` prefixes the attempt count and
        the bound, so the user reads both how far the tool went and why.
    """
    detail = (
        "its clues have more than one solution"
        if solution_count is not None and solution_count >= solver.MANY
        else "its clues have no solution at all"
    )
    return (
        f"the converted image is not a uniquely-solvable puzzle ({detail}); an "
        "uploaded image is fixed and is never re-drawn automatically, so the "
        f"tool adjusted up to {MAX_NUDGE_ATTEMPTS} pixels of the converted grid "
        "instead and has now stopped altering it — retry with a different "
        "image, or a different --size (an image with larger, more clearly "
        "separated areas of light and dark converts best)"
    )


def _image_tier_reason(tier: difficulty.Tier | None) -> str:
    """POL-005's wording for an image whose puzzle missed the requested tier.

    The same shape of statement as :func:`_image_uniqueness_reason` for the
    same reason: POL-004's resample cannot help a source that returns the
    identical grid every time, so the run ends here and says so.
    """
    band = _band_text(tier) if tier is not None else "requested band"
    return (
        f"the converted image classified outside the {band}, and an uploaded "
        "image is fixed — a resample would convert the same picture again; try "
        "another --difficulty, a different --size, or another image"
    )


def _resample_reason(tier: difficulty.Tier | None) -> str:
    """POL-004's abandonment wording — the band that kept being missed.

    Narrower than :func:`_uniqueness_reason` because the resample loop rejects
    for exactly one cause: every round it discarded *was* a uniquely-solvable
    candidate, and only its score was wrong.

    A run that requested no tier cannot reach POL-004's abandonment at all —
    its resample check is vacuous, so the first round returns — but the
    primitive takes the reason up front, and a message that asserted its own
    unreachability would be a worse failure than one that simply says what
    happened.
    """
    if tier is None:  # pragma: no cover - the vacuous check never abandons
        return "no candidate grid was usable"
    return (
        f"no candidate classified into the {_band_text(tier)}; try another "
        "--difficulty, a different --size/--density combination, or another "
        "--seed"
    )


def generate(
    request: GenerationRequest, *, names: NameContext | None = None
) -> Puzzle:
    """Run one generation request end to end and return the finished puzzle.

    Sources a candidate grid for ``request.mode``, derives its clues, asks the
    solver how many solutions they have, scores the ones that are uniquely
    solvable, and returns the puzzle the moment a candidate is both unique and
    in the requested difficulty tier. A candidate that fails either test is
    discarded and a fresh one sourced automatically, with no user interaction
    (POL-001 and POL-004, FR-007 and FR-010), within the bounds INV-003 fixes
    (ADR-0002) — see "The two loops" below.

    All randomness comes from a single ``random.Random`` built here and
    injected into every stochastic call (ADR-0015), so the same seed replays
    the same run — including *which* candidates were discarded. When the
    request carries no seed one is drawn from the OS entropy pool and recorded
    on the returned puzzle, which is what lets the adapter echo it.

    The puzzle's name (FR-015), its requested tier (FR-008) and its grid extent
    (FR-018/FR-023) are resolved first, before the seed is drawn and before the
    aggregate exists: an unusable one of the three must leave nothing behind
    (AC-045, AC-021, AC-098), and a usable one must be fixed for the whole run —
    every retry below replaces the *candidate*, never the puzzle, so all three
    are written exactly once here and read thereafter (guardrail G-6, AC-020).

    Resolving the extent is where a bare ``--size N`` becomes two numbers
    (:func:`_resolved_extent`): N is the grid's longer side and the other is
    derived from the source's own shape — the ink bounding box in image mode,
    the template's extent in library mode, a square for random, which has no
    shape of its own. An explicit ``--size WxH`` is used exactly as given and
    never consults the source at all (AC-096).

    The two loops (POL-001 inside POL-004)
    --------------------------------------
    POL-004's resample loop *wraps* POL-001's regenerate loop rather than
    replacing it (guardrail G-5): one resample round runs the whole regenerate
    loop to get a uniquely-solvable candidate, then keeps it only if its score
    is in tier. Two consequences are deliberate, and both follow from
    ``run_bounded`` being one primitive used twice (guardrail G-2):

    *The retry budget is the request's, not the round's.* Neither counter is
    reset between rounds, so the regenerate budget spans the whole request: a
    resample round does **not** get a fresh :data:`MAX_RETRY_ATTEMPTS`
    candidates to find a unique one in. Across a run at most :data:`MAX_RETRY_ATTEMPTS` grids are ever sourced,
    however the two rejection causes divide them up, which is what keeps
    scoring inside the loop from multiplying the work NFR-001 budgets
    (guardrail G-6). It also means a request that keeps missing its tier ends
    on whichever bound it exhausts first — POL-005 abandons either way, and
    both messages name what the candidates kept failing, the shared budget
    included (:func:`_uniqueness_reason`).

    Random-mode recovery inside POL-001's loop (ADR-0024)
    -----------------------------------------------------
    A random-mode candidate the solver rejects is always rejected for
    *ambiguity* — its clues came from a real grid, so a count of 0 cannot
    happen — and the solver says where: the cells its two witnesses disagree
    on. POL-006 acts on that before POL-001 gives up on the grid. The next
    attempt is the same grid with one filled and one empty cell inside that
    region swapped (:func:`repair_candidate`), re-judged in full; after
    :data:`MAX_CONSECUTIVE_REPAIRS` such attempts on one lineage the grid is
    discarded and a fresh one drawn, and recovery continues from there.

    Both kinds of attempt are attempts of the same ``regenerate`` counter, so
    ADR-0002's one bound, :data:`MAX_RETRY_ATTEMPTS`, covers them together and
    nothing new can overshoot it (INV-003, ADR-0024/R2, AC-113).
    :attr:`Puzzle.recovery` records how that budget divided — the data CARD-091
    recalibrated K from.

    *An exhausted inner loop ends the outer one.* ``GenerationAbandoned`` from
    the regenerate loop travels straight out through the resample attempt
    (``run_bounded`` re-raises whatever an attempt raises), so a run that
    cannot produce a unique candidate at all reports that — it is not caught
    and re-tried as though it were a tier miss.

    Args:
        request: The run as the caller asked for it.
        names: ADR-0018's naming context, for the same-minute counter and the
            clock the auto-name's timestamp is read from. Defaults to the
            process-wide :data:`DEFAULT_NAMES`; a caller passes its own to make
            the timestamp deterministic (AC-042).

    Returns:
        The :class:`Puzzle` aggregate, with ``ready_for_export`` set — the one
        object the whole run mutated, retries included.

    Image mode (FR-003) takes a third loop of its own
    -------------------------------------------------
    An uploaded image cannot be re-drawn, so ``--mode image`` converts exactly
    once and leaves the regenerate and resample counters at zero — see "A
    source that cannot be re-drawn" in the module docstring, and
    ``sourcing.image`` for why the conversion is deterministic.

    When that single conversion is not uniquely solvable, POL-002's bounded
    pixel nudge runs instead (FR-013): up to :data:`MAX_NUDGE_ATTEMPTS` rounds,
    each flipping one more cell of the *original* conversion and re-solving the
    result in full. The first uniquely-solvable nudge is the run's puzzle; at
    the cap the run is abandoned with a message that says the tool has stopped
    altering the image and what to try instead (POL-003, AC-035/AC-036). A
    conversion that is unique but misses the requested tier is not nudged — the
    nudge is a uniqueness remedy — and ends the run as it did before.

    Raises:
        GenerationAbandoned: the run gave up (POL-005) — the retry bound was
            exhausted with no candidate uniquely solvable (AC-019) or none
            scored inside the requested tier (AC-027); or, in image mode, the
            conversion missed the requested tier, or neither it nor any of its
            :data:`MAX_NUDGE_ATTEMPTS` nudges was uniquely solvable (AC-035).
            The message says which, and in image mode says that the picture was
            never re-drawn and is no longer being altered.
        UnreadableImage: ``--mode image`` was given no readable picture to
            convert (AC-008). Raised by the sourcing module on the one attempt
            and, like the other invalid-request errors, not retried.
        InvalidPuzzleName: ``--name`` was given as an empty name (AC-045).
            Raised before anything is sourced or constructed, so the run leaves
            no puzzle behind.
        UnsupportedDifficulty: ``--difficulty`` named no supported tier
            (AC-021). Raised alongside the name check, before anything is
            sourced or constructed.
        SizeOutOfRange, InvalidDensity, UnknownLibraryImage: the request is not
            valid for its mode. Raised while the extent is resolved, or by the
            sourcing module on the first attempt, and *not* retried — an invalid
            request does not become valid by being asked again, and POL-001
            forbids a library retry from switching to a key that would be.
        SizeTooSmallForSource: a bare ``--size N`` whose source is more
            elongated than ``N/5 : 1``, so following its shape would put the
            grid's short side under 10 cells and discard more than half the
            picture (AC-098, FR-023). A ``SizeOutOfRange``, and its message
            names the smallest ``--size N`` that would take this source.
        SolverTimeout: the request ran out of time (ADR-0011). Raised by the
            solver and *not* caught here: a timeout says nothing about the
            candidate, so retrying it would spend the rest of a budget that has
            already expired. It is EVT-012 abandonment by another name — the
            CLI maps it to the same GENERATION_FAILED exit code as
            ``GenerationAbandoned`` — and because ``confirm_uniqueness`` is
            never reached on this path, the puzzle is left unexportable
            (INV-002, guardrail G-4).
        ValueError: ``request.mode`` has no registered source, or has one but
            no argument list in :func:`_source_arguments`. Both are raised
            before the loop starts, so a wiring bug cannot be mistaken for a
            run of infeasible candidates.
    """
    # FR-015, first and once: an invalid name must abort before a puzzle
    # exists (AC-045), and a valid one is the run's for good (G-6).
    name = (names if names is not None else DEFAULT_NAMES).name_for(request)
    # FR-008, same shape and for the same reason: an unsupported tier is the
    # request being wrong (AC-021), so it is refused here — before a seed is
    # drawn, before the aggregate exists and long before a solver runs.
    requested_tier = (
        difficulty.parse_tier(request.difficulty)
        if request.difficulty is not None
        else None
    )

    # FR-023, third and for the same reason: an extent that cannot be resolved
    # — out of range, or a bare N too small to follow this source's shape
    # (AC-098) — must abort before a puzzle exists. Resolved *once*, here: the
    # derivation reads the request and the source's own shape, neither of which
    # a retry changes, so re-deriving per attempt could only differ by being
    # wrong (and, in image mode, would decode the file again for every nudge).
    extent = _resolved_extent(request)

    seed = request.seed if request.seed is not None else secrets.randbits(64)
    rng = random.Random(seed)
    puzzle = Puzzle(
        request=request,
        seed=seed,
        extent=extent,
        name=name,
        requested_tier=requested_tier,
    )

    # ADR-0011: one absolute instant for the whole request, fixed here before
    # the first attempt and shared by every solve below, so the retry loop
    # cannot extend the budget by taking another turn.
    deadline = time.monotonic() + GENERATION_BUDGET_SECONDS

    # Resolved once, outside the loop: the mode does not change between
    # attempts, and an unknown mode must fail immediately rather than after
    # burning the retry budget.
    source = sourcing.for_mode(request.mode)
    source_arguments = _source_arguments(request, extent)

    # FR-027: resolved once, here, for the same reason the extent and the
    # deadline are — it cannot change between attempts, and a nudge must not
    # be able to move a picture onto the other path halfway through a run.
    # Costs nothing while `DEFAULT_BINARISATION` is pinned (see
    # `image_source.binarisation_for`).
    if request.mode == sourcing.IMAGE:
        puzzle.binarisation = image_source.binarisation_for(request.image)

    def judge_candidate(grid: Grid) -> Puzzle | None:
        """Judge one already-sourced grid: clues -> uniqueness -> score.

        The tail of the pipeline, shared by every loop in this function so that
        *where a candidate grid came from* — a fresh draw, a library
        re-rendering, an uploaded image, a nudged uploaded image — cannot
        change how it is judged. That is CON-005 and CARD-016's guardrail G-4
        made structural rather than repeated: there is exactly one
        ``solver.solve`` call in the module, so a nudged grid is genuinely
        re-solved and can no more be assumed unique than a random one.

        A candidate that survives the uniqueness check is scored before it is
        returned, so every candidate the resample loop above ever sees is
        already carrying its own score — which is what makes AC-026 ("the new
        candidate is re-scored automatically before any further check")
        structural rather than a step somebody has to remember to repeat.
        Scoring a *rejected* candidate would be meaningless (COMP-006 scores
        the solve of a uniquely-solvable clue set) and is skipped, so POL-001's
        path costs exactly what it did before this card.
        """
        candidate_clues = puzzle.record_candidate(grid)
        verdict = solver.solve(
            candidate_clues.rows, candidate_clues.columns, deadline=deadline
        )
        # Stored before the uniqueness gate, not after it: the mask and the
        # witness pair are precisely what a *rejected* candidate carries for
        # ADR-0024's repair and POL-002's nudge to work from (CARD-074,
        # CARD-075), and a solve whose verdict was MANY is the only solve that
        # ever produces two witnesses. Stored as reported, nothing derived
        # here (guardrail G-3).
        puzzle.undecided_mask = verdict.undecided_mask
        puzzle.witnesses = verdict.witnesses
        puzzle.rung_tags = verdict.rung_tags
        if not puzzle.confirm_uniqueness(verdict.solution_count):
            return None
        # COMP-006, off the signals of the solve that just happened — no second
        # solve, and no re-derivation of anything the solver reported
        # (FR-026, ADR-0029/R2, guardrail G-1). Both of ADR-0025's classifier
        # inputs come from this one `verdict.signals`: the rung counts the score
        # is built from and the branch count the Guess tier is keyed on. The
        # clues are no longer passed — ADR-0029 took density out of the score.
        puzzle.record_difficulty(
            difficulty.score_difficulty(verdict.signals),
            verdict.signals.branch_nodes,
        )
        return puzzle

    # ADR-0024's recovery state, for random mode only (ADR-0024/R5): the
    # repair the *next* attempt will judge, and how many repairs the current
    # lineage has already made. Both live here, in the closure the attempt
    # callable shares with the loop, because they are per-request state and
    # `run_bounded` is deliberately stateless — the primitive counts, the
    # callable decides what to try next (guardrail G-2).
    repairs_enabled = request.mode == sourcing.RANDOM and MAX_CONSECUTIVE_REPAIRS > 0
    pending_repair: Repair | None = None
    consecutive_repairs = 0
    # The grids the current lineage has already judged, for the repeat tally
    # only (ADR-0024's deferred K calibration). Never consulted by a decision:
    # kept under `repairs_enabled` so that K = 0 does not merely behave like
    # the pre-ADR-0024 loop but performs exactly its work.
    lineage_grids: set[tuple[tuple[bool, ...], ...]] = set()

    def attempt_candidate() -> Puzzle | None:
        """One pass of the pipeline: source -> clues -> uniqueness -> score.

        The single ``rng`` is threaded in here, which is what makes the
        *sequence* of discarded candidates reproducible and not merely the
        first one (ADR-0015).

        Recovery (POL-001 and, since ADR-0024, POL-006)
        ----------------------------------------------
        Every call is one attempt against the one ``regenerate`` counter,
        whichever kind it is — that is ADR-0024/R2 and it is structural here:
        ``run_bounded`` advanced the counter before calling this, and this
        function has no way to ask for an unpaid attempt.

        What the attempt *is* depends on what the previous one left behind. In
        random mode a rejected candidate is not thrown away immediately: the
        solver reported which cells its two witnesses disagree on, so the
        ambiguity is located, and :func:`repair_candidate` flips one filled and
        one empty cell inside that region to make the next candidate. Up to
        :data:`MAX_CONSECUTIVE_REPAIRS` of those run on one lineage; then the
        lineage is dropped and the next attempt draws a fresh grid from the
        same ``rng``, exactly as it always did. A repair draws nothing from the
        ``rng``, so a run's repairs do not perturb the stream its redraws come
        from (ADR-0024/R4).

        Library mode keeps POL-001's redraw and image mode never reaches here
        twice — ``repairs_enabled`` is the single place that is decided
        (ADR-0024/R5, guardrail G-3).
        """
        nonlocal pending_repair, consecutive_repairs

        if pending_repair is not None:
            # POL-006 / CMD-014 -> EVT-015: judge the repaired grid. Consumed
            # here rather than recomputed, so the grid that is judged is the
            # one whose parent's witnesses chose the pair.
            grid = pending_repair.grid
            if pending_repair.region == UNDECIDED_MASK_REGION:
                puzzle.recovery.repairs_from_fallback_region += 1
            if _lineage_key(grid) in lineage_grids:
                # The lineage has come back to a grid it already judged — the
                # rule flipped a pair back. Recorded, not acted on: choosing a
                # different pair here would be a different rule from
                # ADR-0024/R4's, which this card does not have the mandate to
                # change. Measured at ~7% of lineages, and ~99% of those are an
                # immediate reversal of the previous flip.
                puzzle.recovery.repeated_attempts += 1
            pending_repair = None
            consecutive_repairs += 1
            puzzle.recovery.repairs += 1
        else:
            # POL-001, unchanged. The argument list is the mode's, not the
            # dispatcher's (see sourcing.for_mode and _source_arguments): the
            # random mode's density and the library mode's key are assembled
            # per mode around the shared (width, height) pair, and CARD-015's
            # image path joins them there. The RNG is appended here for every
            # mode alike — including library's, whose only draw is POL-001's
            # boundary tie-break, which is what makes a library retry a
            # different rendering of the same template rather than a repeat.
            consecutive_repairs = 0
            lineage_grids.clear()
            grid = source(*source_arguments, rng)
            puzzle.recovery.redraws += 1

        if repairs_enabled:
            lineage_grids.add(_lineage_key(grid))

        # One judge path for both kinds (CON-005, INV-002, ADR-0024/R1): a
        # repaired grid is re-solved on its own re-derived clues and is no more
        # assumed unique than a freshly drawn one.
        candidate = judge_candidate(grid)
        if candidate is not None or not repairs_enabled:
            return candidate

        if consecutive_repairs >= MAX_CONSECUTIVE_REPAIRS:
            # ADR-0024's escape: K consecutive repairs without a unique
            # verdict end the lineage. Leaving ``pending_repair`` unset is what
            # "discard and redraw" is in code.
            puzzle.recovery.lineages_at_repair_cap += 1
            return None

        # The rejected candidate's own witnesses and mask — still on the
        # aggregate, because judge_candidate records them before the uniqueness
        # gate and the next record_candidate has not happened yet.
        pending_repair = repair_candidate(
            grid,
            witnesses=puzzle.witnesses,
            undecided_mask=puzzle.undecided_mask,
        )
        if pending_repair is None:
            # Neither region held a filled/empty pair, so there is nothing to
            # flip: the lineage ends here and the next attempt redraws.
            puzzle.recovery.lineages_without_repairable_region += 1
        return None

    def attempt_candidate_in_tier() -> Puzzle | None:
        """One resample round: a unique candidate, kept only if it is in tier.

        POL-004. The inner :func:`run_bounded` is POL-001's loop verbatim — a
        resample does not replace regeneration, it composes with it (guardrail
        G-5) — and the tier check is applied to what that loop produced, which
        is by construction a scored candidate.
        """
        candidate = run_bounded(
            puzzle.regenerate,
            attempt_candidate,
            reason=_uniqueness_reason(requested_tier),
        )
        return candidate if candidate.difficulty_in_requested_tier else None

    if request.mode == sourcing.IMAGE:
        # POL-002, not POL-001/POL-004. See "A source that cannot be re-drawn"
        # in the module docstring: the conversion runs exactly once — the
        # regenerate and resample counters stay at zero, because asking for a
        # second candidate would return the first one — and recovery is
        # POL-002's bounded nudge instead.
        candidate = attempt_candidate()
        if candidate is None:
            converted = puzzle.grid
            if converted is None:  # pragma: no cover - a judged candidate has a grid
                raise RuntimeError(
                    "image conversion was judged but recorded no grid to nudge"
                )

            # POL-002's state, in this closure for the reason ADR-0024's
            # repair lineage is in the one above: it is per-request, and
            # `run_bounded` is deliberately stateless — the primitive counts,
            # the callable decides what to try next (guardrail G-2). The cells
            # chosen so far, and the grid the last attempt was judged on.
            nudged_cells: list[tuple[int, int]] = []
            last_judged = converted

            def attempt_nudged_candidate() -> Puzzle | None:
                """One POL-002 round: add a cell, nudge the conversion, judge.

                CARD-075's loop, and the only part of POL-002 that changed:
                each round asks ``sourcing.image`` for *one more* cell, read
                off what the solver reported about the grid the **previous**
                round was judged on — the cells its two witnesses disagreed on,
                or its undecided mask when those are used up. Those are still
                on the aggregate here: :func:`judge_candidate` records them
                before the uniqueness gate and the next ``record_candidate``
                has not happened yet, exactly as ADR-0024's repair reads them.

                Every round nudges ``converted`` — the original conversion —
                and not the previous round's grid, so attempt *n* differs from
                the user's picture by exactly *n* pixels and no earlier edit
                can be undone by a later one (see ``sourcing.image.nudge``).
                The result then goes through :func:`judge_candidate` like any
                other candidate: the solver's verdict on the nudged grid is the
                only thing that ends this loop successfully (CON-005, G-4).

                When neither region holds an unflipped cell there is nothing to
                add and the round returns no candidate. The counter has already
                advanced — :func:`run_bounded` advances it before calling this
                — so the cap and POL-003's report are reached exactly as they
                are when a nudged grid is simply still ambiguous.
                """
                nonlocal last_judged
                cell = image_source.next_nudge_cell(
                    last_judged,
                    nudged_cells,
                    witnesses=puzzle.witnesses,
                    undecided_mask=puzzle.undecided_mask,
                )
                if cell is None:
                    return None
                nudged_cells.append(cell)
                last_judged = image_source.nudge(converted, nudged_cells)
                return judge_candidate(last_judged)

            # POL-003 lives in run_bounded's exhaustion branch: at the bound it
            # raises instead of nudging again, which is what "stops altering
            # the image" is in code (AC-035, guardrail G-3). There is no
            # fallback attempt after it and nothing catches it here.
            candidate = run_bounded(
                puzzle.nudge,
                attempt_nudged_candidate,
                reason=_image_uniqueness_reason(puzzle.solution_count),
            )
        if not candidate.difficulty_in_requested_tier:
            raise GenerationAbandoned(_image_tier_reason(requested_tier))
        return candidate

    return run_bounded(
        puzzle.resample,
        attempt_candidate_in_tier,
        reason=_resample_reason(requested_tier),
    )


class BatchResult(list):
    """The puzzles a batch produced, and why it has as many as it has.

    A ``list`` subclass rather than a new dataclass, deliberately. CARD-083
    decided the shortfall *is* the return value — the caller compares
    ``len(result)`` against ``count`` — and that was right while there was one
    fact to carry. There are two now: candidates the generator had to abandon,
    and candidates never attempted because the batch ran out of time. They mean
    opposite things to whoever re-runs the batch (one is bad luck, the other
    will happen again), so a caller has to be able to tell them apart.

    Subclassing keeps every existing use working untouched — ``len``,
    iteration, indexing, ``==`` against a plain list, the ten test modules that
    treat the return as a sequence — while the two counts ride along as
    attributes. A dataclass would have been cleaner in isolation and would have
    rewritten every one of those call sites to reach through a ``.puzzles``.

    One caveat, stated because it is the usual cost of this pattern: slicing or
    concatenating a ``BatchResult`` gives a plain ``list``, so the counts are
    read at the call site, not carried onward.
    """

    #: Candidates the generator abandoned — :data:`MAX_RETRY_ATTEMPTS` attempts
    #: each, redraws and repairs, none uniquely solvable. Bad luck, and re-running may well do better.
    abandoned: int = 0
    #: Candidates never attempted, because :data:`BATCH_BUDGET_SECONDS` ran out
    #: first. Not bad luck: the same request will stop in the same place.
    not_attempted: int = 0

    @property
    def stopped_early(self) -> bool:
        """Did the clock end this batch, rather than the count?"""
        return self.not_attempted > 0


def generate_batch(
    count: int,
    sizes: list[int],
    source: str = "random",
    difficulty_tier: str | None = None,
    budget_seconds: float = BATCH_BUDGET_SECONDS,
    monotonic: Callable[[], float] = time.monotonic,
    on_puzzle: Callable[[Puzzle], None] | None = None,
) -> BatchResult:
    """Generate multiple puzzles using the standard generation pipeline.

    Generates ``count`` puzzles, each using the exact same pipeline as
    :func:`generate`: source grid → clues → uniqueness check → difficulty score.
    Uses the same real generation, solving, and difficulty-scoring logic as the
    CLI, ensuring consistency across batch and interactive generation.

    Args:
        count: Number of puzzles to generate (subject to retry budget limits)
        sizes: List of grid sizes to randomly choose from (each can be int for
            square or (width, height) tuple)
        source: Generation source mode ("random", "library", or "image")
        difficulty_tier: Target difficulty tier, in any spelling
            :func:`nonogram.difficulty.parse_tier` accepts — ``"Easy"``,
            ``"easy"``, ``"EASY"`` are the same tier — or ``None`` to accept
            any difficulty. ``None`` is the only way to say "any": an empty
            string is a tier name that does not exist and is refused, the same
            answer :func:`generate` gives it.
        on_puzzle: Called once with each puzzle as soon as it is made, before
            the next candidate starts (CARD-093). A caller that stores puzzles
            should store them here rather than from the return value: both
            stopping exits below *raise*, so a batch that stops early never
            returns, and a worker killed mid-batch never returns either. With
            this callable the work done before any of those is already the
            caller's. It is a plain callable so this module stays ignorant of
            where puzzles go (ADR-0007); an exception it raises propagates and
            ends the batch, because a store that is failing is the caller's
            to handle, not a candidate to skip.

    Returns:
        Successfully generated Puzzle objects, with full metadata (difficulty
        scores, solution counts, export-ready).

        **May be shorter than ``count``.** A candidate that cannot be made
        uniquely solvable within its retry budget is skipped and the batch
        continues (CARD-083); the length of this list against ``count`` is how
        a caller learns it happened. One bad draw used to end the whole batch,
        which at a measured 1-in-50 abandon rate at 25x25 meant a 50-puzzle
        request lost everything about a third of the time.

    Raises:
        ValueError: If parameters are invalid (out-of-range count/sizes, unknown source)
        UnsupportedDifficulty: ``difficulty_tier`` names no tier that exists.
            This is ``parse_tier``'s own error rather than a second
            ``ValueError``, because which tiers exist is a domain rule with a
            domain error already defined for it, already mapped to an exit code
            by COMP-001, and already carrying a message that lists the tiers
            read off the enum. Raising ``ValueError`` here would mean catching
            that answer and restating it less well (CARD-070, item 1).
        GenerationAbandoned: Only when the *batch* fails, which is now a
            narrower thing than one puzzle failing. Two cases: no puzzle at all
            was produced, or :data:`MAX_CONSECUTIVE_ABANDONMENTS` candidates
            were abandoned back-to-back, which says the parameters are
            infeasible rather than unlucky. Both carry the counts, and the
            consecutive case chains the candidate's own abandonment as its
            cause so a caller logging with ``exc_info`` keeps it.
        SolverTimeout: A candidate spent ADR-0011's whole 30s deadline without
            a verdict. **Not** skipped, deliberately — see the comment at the
            call site; a batch that swallowed timeouts would have no time bound
            at all.
    """
    if not 1 <= count <= MAX_BATCH_COUNT:
        raise ValueError(
            f"Count must be 1-{MAX_BATCH_COUNT}, got {count}. The ceiling came "
            f"down from 200 with CARD-088: a batch runs inside one request, and "
            f"at 30x30 even {MAX_BATCH_COUNT} candidates cost more than the "
            f"server will wait — which is why the run also stops on "
            f"BATCH_BUDGET_SECONDS rather than trusting a count to be safe at "
            f"every extent."
        )
    if not sizes or not all(isinstance(s, (int, tuple, list)) for s in sizes):
        raise ValueError(f"Sizes must be a list of ints or (width, height) tuples, got {sizes}")
    if source not in sourcing.MODES:
        raise ValueError(f"Unknown source mode {source!r}; known modes: {', '.join(sourcing.MODES)}")
    # One tier vocabulary for the whole system: ``parse_tier`` is the function
    # the CLI already validates ``--difficulty`` through, so a batch and an
    # interactive run now accept and refuse exactly the same spellings. It also
    # keeps ADR-0025's property that CARD-076 pinned — the vocabulary is read
    # off the enum, so a fifth tier would reach this gate without an edit.
    #
    # Until CARD-070 this compared enum *names*, which meant the batch refused
    # ``"Easy"`` — the spelling this function's own docstring advertised — and
    # accepted only ``"EASY"``. Nobody noticed because every caller passes
    # ``None`` (``docs/GENERATION_ALGORITHM.md`` §10.2 finding 1).
    #
    # The parsed tier's *value* goes into the request, not the caller's string:
    # ``GenerationRequest.difficulty`` is parsed again downstream, and handing
    # it the canonical spelling means the second parse cannot disagree with the
    # first.
    #
    # ``is not None`` rather than a falsy test, because ``""`` is a spelling
    # like any other and :func:`generate` refuses it — measured, the old falsy
    # guard made the empty string mean "any tier" here and
    # ``UnsupportedDifficulty`` one frame down, which is precisely the
    # disagreement this item exists to remove (CARD-070 review cycle 1, F-001).
    #
    # This gate is a **boundary convenience, not the enforcement point**.
    # :func:`generate` parses the tier itself at the top of every call, before
    # a seed is drawn and before the aggregate exists, so a bad tier already
    # aborts on the first iteration with no work done; removing this check
    # would change nothing a caller can observe except *where* the traceback
    # starts. It is kept so a whole batch fails at the call rather than inside
    # the loop, and it must stay a delegation to ``parse_tier`` — the moment it
    # re-states the rule instead of asking for it, the two copies can drift,
    # which is the bug this whole item is repairing (review cycle 1, F-004).
    tier = difficulty.parse_tier(difficulty_tier) if difficulty_tier is not None else None

    puzzles = BatchResult()
    #: Candidates skipped so far, and how many of those ran back-to-back.
    abandoned = 0
    #: Candidates never started, because the batch's own clock ran out
    #: first. A different fact from `abandoned`, and the reason
    #: BatchResult carries both (CARD-088).
    not_attempted = 0
    consecutive_abandonments = 0
    #: The most recent candidate-level abandonment, so *both* exits below can
    #: chain it. Chaining only the consecutive one left a count<=2 caller with
    #: __cause__ None — CARD-080's F-008 defect, reproduced on the other branch
    #: of the function whose commit message cited that lesson (review cycle 1,
    #: F-001).
    last_abandonment: GenerationAbandoned | None = None
    rng = random.Random()  # Batch uses unseeded RNG; each puzzle draws its own seed

    # The batch's own clock. Started before the first candidate and never
    # reset, so the bound is one number read in one place (INV-003).
    deadline = monotonic() + budget_seconds

    for index in range(count):
        # Before the candidate, not during it: a candidate that starts always
        # finishes, so a puzzle is never half-made and the ceiling is a sum we
        # can state (BATCH_BUDGET_SECONDS + GENERATION_BUDGET_SECONDS) rather
        # than a race. It also keeps the clock out of GenerationAbandoned's
        # vocabulary — a candidate is abandoned because its attempts ran out, never
        # because the batch was in a hurry.
        if monotonic() >= deadline:
            not_attempted = count - index
            break

        size_spec = rng.choice(sizes)
        # Handle both int (square) and (width, height) tuple formats
        if isinstance(size_spec, (tuple, list)):
            width, height = size_spec
        else:
            width = height = size_spec

        # Generate one puzzle through the full pipeline
        request = GenerationRequest(
            mode=source,
            width=width,
            height=height,
            density=50,  # Default to 50% density for random generation
            difficulty=tier.value if tier is not None else None,
        )

        # One candidate that cannot be made unique is a bad draw, not a broken
        # batch (CARD-083). It is skipped and the batch carries on; the
        # shortfall is visible to the caller as a list shorter than ``count``,
        # which ``admin/batch_generator`` reports on the batch record the same
        # way CARD-080 reports a store refusal.
        #
        # Deliberately only ``GenerationAbandoned``. A ``SolverTimeout`` is not
        # a bad draw — it is ADR-0011's 30s bound being spent on one grid — and
        # swallowing it per candidate would let one undecidable size spend the
        # batch's whole clock thirty seconds at a time. Before CARD-088 gave the
        # batch that clock it was worse — no time bound at all, 200 candidates x
        # 30s. Timeouts are rare at today's bounds (CARD-091 measured 0 in 100
        # 30x30 requests at K=5), but rare is not impossible. Whether a batch
        # should survive a timeout too is a separate decision, recorded as
        # CARD-083's open question; CARD-093 made sure the puzzles before one
        # are kept either way.
        try:
            puzzle = generate(request)
        except GenerationAbandoned as abandonment:
            abandoned += 1
            consecutive_abandonments += 1
            last_abandonment = abandonment
            if consecutive_abandonments >= MAX_CONSECUTIVE_ABANDONMENTS:
                raise GenerationAbandoned(
                    f"abandoned the batch after {consecutive_abandonments} "
                    f"consecutive candidates could not be made uniquely "
                    f"solvable ({len(puzzles)} of {count} produced before "
                    f"that): at this rate the request is infeasible rather "
                    f"than unlucky, so the remaining "
                    f"{count - len(puzzles) - abandoned} were not attempted"
                ) from abandonment
            continue

        consecutive_abandonments = 0
        puzzles.append(puzzle)
        if on_puzzle is not None:
            on_puzzle(puzzle)

    puzzles.abandoned = abandoned
    puzzles.not_attempted = not_attempted

    if not puzzles:
        # Reachable only when ``count`` is below
        # :data:`MAX_CONSECUTIVE_ABANDONMENTS`: with no successes the
        # consecutive counter never resets, so for count >= 3 the bound above
        # fires on the third candidate and this line is never reached. It is
        # the tail case, not the general "everything failed" exit — measured,
        # count 1 and 2 arrive here and count 3 and up do not. Said out loud
        # because the message reads like the general one otherwise, and
        # somebody debugging a failed 50-puzzle batch would hunt for it in
        # vain (CARD-083 review cycle 1, F-003).
        if not_attempted and last_abandonment is None:
            # The clock stopped it before anything was even tried, which is a
            # configuration problem rather than a generation one: saying
            # "every candidate was abandoned" would name a cause that never
            # happened.
            raise GenerationAbandoned(
                f"this batch of {count} ran out of its {budget_seconds:.0f}s "
                f"budget before producing a puzzle, with {not_attempted} never "
                f"attempted. At the largest supported extent one puzzle can "
                f"cost several seconds, so ask for fewer, or for a smaller size"
            )
        raise GenerationAbandoned(
            f"no puzzle in this batch of {count} could be made uniquely "
            f"solvable; every candidate was abandoned after "
            f"{MAX_RETRY_ATTEMPTS} attempts. A batch that produced nothing is "
            f"not a short batch, it is a failed one — try a different size, or "
            f"another run"
        ) from last_abandonment

    return puzzles


def export_puzzle(puzzle: Puzzle) -> tuple[Path, ...]:
    """Write ``puzzle`` in every format its request asked for (FR-011, FR-012).

    A separate step from :func:`generate`, not a tail of it, for two reasons.
    Generation is pure — CON-003's "no persistence beyond file export" reads,
    in code, as "the only function that touches the filesystem is this one" —
    and a caller that wants a puzzle without a file (every test in this
    package, and any future non-CLI caller) should not have to opt out of I/O.

    This is INV-002's enforcement point in the export direction: the gate is
    :meth:`Puzzle.require_ready_for_export`, called here, once, before any
    payload is built. The renderers in ``nonogram.export`` do not re-check it
    and must not — ADR-0007 gives a cross-capability invariant exactly one home
    so that all five formats inherit the same answer (guardrail G-3). The
    payload they receive carries no readiness flag at all, which is what makes
    that structural rather than a convention.

    Nothing is written when no format was requested, and the gate is not
    consulted either: a run that asked for no export cannot be "refused" one.

    Repeated formats (``--export json --export json``) are collapsed to the
    first occurrence — the user asked for JSON, not for two copies of it.

    All formats of one run share one *base* filename stem, and that stem is the
    puzzle's FR-015 name rather than a second, independently computed
    convention (:func:`_filename_stem`). What each format actually writes under
    is :func:`_stem_for_format`'s answer for it — the base name for four of the
    five, and ADR-0016's ``<name>-<difficulty>`` for the PDF.

    Args:
        puzzle: The finished aggregate from :func:`generate`. Its request
            supplies both the formats and the destination directory.

    Returns:
        The paths written, in the order the formats were requested — the
        adapter's material for reporting the run's output. Empty when the
        request asked for no export.

    Raises:
        ExportRejected: the puzzle's uniqueness check has not confirmed
            exactly one solution (INV-002, AC-030/AC-048).
        OSError: the destination could not be created or written.
    """
    formats = tuple(dict.fromkeys(puzzle.request.export_formats))
    if not formats:
        return ()

    puzzle.require_ready_for_export()

    grid, puzzle_clues = puzzle.grid, puzzle.clues
    if grid is None or puzzle_clues is None:  # pragma: no cover - INV-002 implies both
        raise RuntimeError(
            "puzzle is ready for export but carries no candidate; "
            "ready_for_export is only ever set for a recorded candidate"
        )

    tier = puzzle.difficulty_tier
    payload = export.ExportPayload(
        grid=grid,
        row_clues=puzzle_clues.rows,
        column_clues=puzzle_clues.columns,
        seed=puzzle.seed,
        mode=puzzle.mode,
        # ADR-0023's extent pair, read off :attr:`Puzzle.extent` through the
        # aggregate's two accessors — the pair the run actually produced, which
        # since FR-023 is not the request's own pair whenever a bare
        # ``--size N`` left one side unstated. Nothing here reshapes it: the
        # two export formats write and read the two numbers independently, and
        # a square puzzle is simply the case where they are equal.
        width=puzzle.width,
        height=puzzle.height,
        density=puzzle.density,
        # FR-016's header, as values rather than as domain objects: the tier's
        # display spelling is resolved here, through ``Tier.label``, because
        # COMP-007 may not import COMP-006 to ask (ADR-0007).
        name=puzzle.name,
        difficulty=tier.label if tier is not None else None,
    )
    # One *base* stem for the whole run — the puzzle's name — so a multi-format
    # export produces one named puzzle in several formats rather than several
    # differently-named files. Resolved once and passed down rather than
    # recomputed per format: the unnamed-aggregate fallback reads the clock
    # (``export.default_stem``), and a run that straddled a minute boundary
    # would otherwise write ``...-1429.json`` next to ``...-1430.png``.
    stem = _filename_stem(puzzle)
    directory = puzzle.request.out if puzzle.request.out is not None else Path.cwd()

    return tuple(
        export.write(
            payload,
            name,
            directory=directory,
            stem=_stem_for_format(name, base=stem, tier=tier),
        )
        for name in formats
    )


#: Everything a filename stem may not contain, as runs (ADR-0016's
#: "sanitized for filesystem-safe characters"). Deliberately an allow-list:
#: a name is user input, and ``--name "../../secrets"`` must become a file in
#: ``--out`` and not a write outside it.
#:
#: ``\w`` on a ``str`` pattern is Unicode-aware (re.UNICODE is the default),
#: so this keeps non-ASCII letters (Cyrillic, accented Latin, CJK, ...) intact
#: instead of silently truncating them, while still excluding "/", "\\", ":",
#: NUL and lookalike/format separators such as U+202E, U+2044 and U+FF0F —
#: none of those are ever matched by \w.
_UNSAFE_STEM_CHARACTERS = re.compile(r"[^\w.-]+")


def _filename_stem(puzzle: Puzzle) -> str:
    """The run's export filename stem — the puzzle's own name, made safe.

    Why the name and not a separately-computed timestamp (FR-015, ADR-0016)
    ----------------------------------------------------------------------
    ``export.default_stem`` was written by CARD-007 as a stand-in — "when the
    aggregate starts carrying a name, this function's caller reads it instead"
    is its own docstring — and this is that caller. Reading the name here is
    what keeps one run's answer to "what is this puzzle called?" identical on
    screen, in the file name and (CARD-014) in the PDF header. Computing a
    second timestamp at export time instead would let a run started at 14:29:59
    be named ``random-...-1429`` and written to ``random-...-1430.json``, and
    would name a library run's file ``library-<timestamp>`` while the puzzle
    itself is called ``cat``.

    The reverse duplication is avoided too: the auto-name is not a re-spelling
    of ``default_stem``'s format but a *call* to it
    (:meth:`NameContext._auto_name`), so the ``"<mode>-<YYYY-MM-DD>-<HHMM>"``
    convention exists in exactly one place for both purposes.

    Sanitization is ADR-0016's rule ("both components sanitized for
    filesystem-safe characters"), applied to the name on its way to a path and
    never to the name itself: ``--name`` is a display name, and AC-044 asks for
    it back verbatim from the aggregate. CARD-014's ``<name>-<difficulty>.pdf``
    is composed from this same stem (:func:`_stem_for_format`) and its tier
    goes through the same :func:`_sanitized_component`, so ADR-0016's two
    components are sanitized by one rule rather than by two.

    A puzzle with no name at all is an aggregate somebody assembled by hand
    rather than one :func:`generate` produced; it falls back to CARD-007's
    stand-in, which is the same convention by construction.
    """
    if puzzle.name is None:
        return export.default_stem(puzzle.mode)
    return _sanitized_component(puzzle.name) or export.default_stem(puzzle.mode)


def _sanitized_component(text: str) -> str:
    """One filename component, made filesystem-safe (ADR-0016).

    The rule itself, factored out of :func:`_filename_stem` so that ADR-0016's
    *both* components — the puzzle's name and the difficulty tier joined to it
    for the PDF — are sanitized by one function rather than by two that can
    drift. ``strip`` takes the leading and trailing dots with it, so no
    component can sanitize into ``.``, ``..`` or a dotfile, and a component
    that sanitizes away entirely comes back as ``""`` for the caller to decide
    about.
    """
    return _UNSAFE_STEM_CHARACTERS.sub("-", text).strip("-.")


def _stem_for_format(
    format_name: str, *, base: str, tier: difficulty.Tier | None
) -> str:
    """The filename stem one format writes under.

    Four of the five formats are the puzzle's name and nothing else. The PDF is
    the exception ADR-0016 carves out: ``<name>-<difficulty>.pdf``, so that the
    file on disk says both what the puzzle is called and how hard it turned out
    to be — the same two facts FR-016 puts in the page header — and so that two
    same-named puzzles at different tiers do not collide before ADR-0017's
    suffix search has to run. ADR-0016 scopes that convention to the PDF alone
    and explicitly leaves FR-011/FR-012's filenames as they are, which is why
    this is one named exception rather than a per-format naming policy.

    The tier is joined in its own lowercase spelling (``cat-hard.pdf``, ADR-0016's
    own example) — ``Tier``'s value, not its display :attr:`~difficulty.Tier.label`,
    the two being one string apart precisely so a filename and a header can
    each take the form they need without a lookup table between them.

    Args:
        format_name: The registered format about to be written.
        base: The run's base stem — :func:`_filename_stem`'s answer, computed
            once for the whole run.
        tier: The tier the puzzle scored into, or ``None`` if it was never
            scored (a hand-assembled aggregate). An untiered puzzle keeps the
            bare name: half of the convention is not a filename, and a
            ``cat-.pdf`` or ``cat-None.pdf`` would be worse than a ``cat.pdf``
            that merely omits what nobody measured.

    Returns:
        The stem to hand ``export.write``.
    """
    if format_name != export.PDF or tier is None:
        return base
    suffix = _sanitized_component(tier.value)
    return f"{base}-{suffix}" if suffix else base

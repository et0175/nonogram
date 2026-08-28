"""COMP-002 — the pipeline orchestrator: one generation run, end to end.

ADR-0007 gives this module three jobs and nothing else:

* own the Puzzle aggregate (AGG-001) for the whole of one generation run;
* be the single enforcement point for INV-002 (a puzzle is exportable only
  after its uniqueness check confirmed exactly one solution) and INV-003 (the
  regenerate / resample / pixel-nudge counter never exceeds its bound);
* drive the generation policies POL-001..POL-005 by composing the capability
  modules (sourcing, clues, solver, difficulty, export), which never call each
  other laterally.

The pipeline (FR-007)
---------------------
``source a grid -> compute its clues -> count its solutions -> mark ready``.
A candidate that is not uniquely solvable is discarded and the whole thing is
tried again on a fresh grid (POL-001), up to :data:`MAX_REGENERATE_ATTEMPTS`
times, after which the run is abandoned (POL-005). The check is the solver's
alone: this module compares ``solution_count`` against 1 and does nothing else
with it (guardrail G-3, CON-005).

Why the loop is a primitive, not a ``while`` (INV-003)
-----------------------------------------------------
Three bounded loops exist in the model — regenerate (POL-001, this card),
difficulty resample (POL-004, CARD-010) and pixel nudge (POL-002, CARD-016) —
and INV-003 constrains all three with one sentence. So the counting lives in
one place, :class:`RetryCounter` plus :func:`run_bounded`, and a loop *kind* is
just a counter with its own bound plus a callable that produces a candidate or
rejects it. A later card adds a counter field to :class:`Puzzle` and an attempt
callable; it does not add a second loop, and it cannot add a second way to
count (guardrail G-2).

What counts as a retry, and what does not
-----------------------------------------
Only a candidate the *uniqueness check answered about* can be retried: the
attempt callable turns ``solution_count != 1`` into a rejection and nothing
else. Every exception — invalid input (SizeOutOfRange, InvalidDensity),
``SolverTimeout`` (ADR-0011), a wiring bug — travels straight
out of the loop and ends the run. Conflating a timeout with a non-unique
verdict would let one infeasible request spend 20 full solver deadlines, which
is exactly the worst case ADR-0002's bound and ADR-0001's time budget exist to
prevent; the two bounds are meant to "operate together but independently"
(ADR-0002, Neutral).

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
from nonogram import export, solver, sourcing
from nonogram.errors import ExportRejected, GenerationAbandoned, InvalidPuzzleName

__all__ = [
    "DEFAULT_NAMES",
    "GENERATION_BUDGET_SECONDS",
    "MAX_REGENERATE_ATTEMPTS",
    "GenerationRequest",
    "NameContext",
    "Puzzle",
    "RetryCounter",
    "export_puzzle",
    "generate",
    "run_bounded",
]

#: The ADR-0012 boundary representation of a solution grid, row-major,
#: ``True`` for a filled cell — the same type the sourcing modules return and
#: the clue derivation consumes.
Grid = list[list[bool]]

#: ADR-0002: the regenerate/resample loop is capped at 20 attempts. One
#: constant, named here because INV-003's bound is the orchestrator's business
#: (the pixel-nudge cap of 5 lands with CARD-016's counter, same way).
MAX_REGENERATE_ATTEMPTS = 20

#: ADR-0001's hard time bound for one generation *request*, in seconds: 30s up
#: to the 50x50 maximum size. Enforced as ADR-0011's cooperative deadline —
#: :func:`generate` turns it into an absolute monotonic instant once per
#: request and hands that same instant to every solver call the request makes,
#: retries included. Deliberately not a per-solve budget: 20 retries times a
#: per-solve 30s would be a ten-minute "timeout", and ADR-0002's attempt bound
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
    typed and widely optional on purpose — ``size`` and ``density`` are plain
    integers in whatever range the user typed, and ``mode`` is a plain string.
    Nothing here has been checked against a domain rule yet; resolving defaults
    and rejecting out-of-range values is the domain's job, inward of COMP-001
    (ADR-0010, guardrail G-3).

    Later cards extend this record alongside the parser it mirrors
    (``difficulty``, ``name``, ``image``, further export formats).
    """

    mode: str
    size: int | None = None
    density: int | None = None
    #: ``--library-key`` (FR-002, CARD-008): which built-in image ``library``
    #: mode draws. Unvalidated like the rest — key membership is a domain rule
    #: (AC-006, ADR-0010), checked by the sourcing module, not here and not by
    #: argparse. Meaningless in the other modes, where it stays ``None``.
    library_key: str | None = None
    #: ``--name`` (FR-015): the user's name for the puzzle, overriding the
    #: auto-generated one. Unvalidated like the rest — ``--name ""`` parses
    #: fine and is rejected inward, by :meth:`NameContext.name_for`, before any
    #: puzzle exists (AC-045, ADR-0010, guardrail G-5). ``None`` means "no
    #: ``--name`` was given", which is what selects the auto-generated name;
    #: it is *not* the same as the empty string.
    name: str | None = None
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
        """FR-015's default: the library key, or mode plus timestamp."""
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
             :func:`run_bounded`. CARD-010 and CARD-016 add ``resample`` and
             ``nudge`` fields next to :attr:`regenerate`.
    """

    #: The request this puzzle is being generated for. Held whole rather than
    #: copied field by field: the aggregate's mode/size/density *are* the
    #: request's, and a later export (FR-012, ADR-0015) has to record the
    #: parameters the run was asked for anyway.
    request: GenerationRequest
    #: The run's effective seed — the requested one, or the one drawn for the
    #: user when ``--seed`` was absent (ADR-0015). Always concrete, so a run
    #: is reproducible after the fact even when nobody asked for a seed.
    seed: int
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
    #: POL-001's counter (INV-003). Bound from ADR-0002.
    regenerate: RetryCounter = field(
        default_factory=lambda: RetryCounter("regenerate", MAX_REGENERATE_ATTEMPTS)
    )
    #: The current candidate's solution grid, or ``None`` before the first one
    #: is sourced.
    grid: Grid | None = None
    #: The current candidate's clues — always the run-length encoding of
    #: :attr:`grid` (INV-001).
    clues: clue_derivation.Clues | None = None
    #: The solver's verdict on the current candidate: ``0``, ``1`` or
    #: ``solver.MANY``. The solver's number, stored as given (G-3).
    solution_count: int | None = None
    #: INV-002's gate. Only :meth:`confirm_uniqueness` writes it.
    ready_for_export: bool = False

    @property
    def mode(self) -> str:
        """How the grid is sourced (AGG-001 attribute)."""
        return self.request.mode

    @property
    def size(self) -> int | None:
        """Requested edge length, still unvalidated (AGG-001 attribute)."""
        return self.request.size

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


def _source_arguments(request: GenerationRequest) -> tuple[object, ...]:
    """The mode-specific leading arguments of ``request``'s grid source.

    ``sourcing.for_mode`` hands back a callable without collapsing the modes
    behind one signature, because they do not share a parameter list — random
    takes size and density, library takes a key and a size, CARD-015's image
    mode will take a path. Assembling that list is therefore the composing
    layer's job, and this is the one place it happens (ADR-0007: the
    orchestrator composes, the capability modules do not know about each
    other).

    The run's ``random.Random`` is *not* included: every source takes it last
    and :func:`generate` appends it at the call site, so a mode cannot
    accidentally be wired up without it (ADR-0015).

    An unknown mode does not reach here — ``sourcing.for_mode`` has already
    raised — so the fallback is the random shape rather than a second error
    path saying the same thing.
    """
    if request.mode == sourcing.LIBRARY:
        return (request.library_key, request.size)
    return (request.size, request.density)


def generate(
    request: GenerationRequest, *, names: NameContext | None = None
) -> Puzzle:
    """Run one generation request end to end and return the finished puzzle.

    Sources a candidate grid for ``request.mode``, derives its clues, asks the
    solver how many solutions they have, and returns the puzzle the moment the
    answer is exactly one. A candidate that fails is discarded and a fresh one
    sourced automatically, with no user interaction (POL-001, FR-007), up to
    :data:`MAX_REGENERATE_ATTEMPTS` attempts (INV-003, ADR-0002).

    All randomness comes from a single ``random.Random`` built here and
    injected into every stochastic call (ADR-0015), so the same seed replays
    the same run — including *which* candidates were discarded. When the
    request carries no seed one is drawn from the OS entropy pool and recorded
    on the returned puzzle, which is what lets the adapter echo it.

    The puzzle's name (FR-015) is resolved first, before the seed is drawn and
    before the aggregate exists: an unusable one must leave nothing behind
    (AC-045), and a usable one must be fixed for the whole run — every retry
    below replaces the *candidate*, never the puzzle, so the name is written
    exactly once here and read thereafter (guardrail G-6).

    Args:
        request: The run as the caller asked for it.
        names: ADR-0018's naming context, for the same-minute counter and the
            clock the auto-name's timestamp is read from. Defaults to the
            process-wide :data:`DEFAULT_NAMES`; a caller passes its own to make
            the timestamp deterministic (AC-042).

    Returns:
        The :class:`Puzzle` aggregate, with ``ready_for_export`` set — the one
        object the whole run mutated, retries included.

    Raises:
        GenerationAbandoned: no candidate was uniquely solvable within the
            retry bound (POL-005).
        InvalidPuzzleName: ``--name`` was given as an empty name (AC-045).
            Raised before anything is sourced or constructed, so the run leaves
            no puzzle behind.
        SizeOutOfRange, InvalidDensity, UnknownLibraryImage: the request is not
            valid for its mode. Raised by the sourcing module on the first
            attempt and *not* retried — an invalid request does not become
            valid by being asked again, and POL-001 forbids a library retry
            from switching to a key that would be.
        SolverTimeout: the request ran out of time (ADR-0011). Raised by the
            solver and *not* caught here: a timeout says nothing about the
            candidate, so retrying it would spend the rest of a budget that has
            already expired. It is EVT-012 abandonment by another name — the
            CLI maps it to the same GENERATION_FAILED exit code as
            ``GenerationAbandoned`` — and because ``confirm_uniqueness`` is
            never reached on this path, the puzzle is left unexportable
            (INV-002, guardrail G-4).
        ValueError: ``request.mode`` has no registered source. Raised before
            the loop starts, so a wiring bug cannot be mistaken for 20
            infeasible candidates.
    """
    # FR-015, first and once: an invalid name must abort before a puzzle
    # exists (AC-045), and a valid one is the run's for good (G-6).
    name = (names if names is not None else DEFAULT_NAMES).name_for(request)

    seed = request.seed if request.seed is not None else secrets.randbits(64)
    rng = random.Random(seed)
    puzzle = Puzzle(request=request, seed=seed, name=name)

    # ADR-0011: one absolute instant for the whole request, fixed here before
    # the first attempt and shared by every solve below, so the retry loop
    # cannot extend the budget by taking another turn.
    deadline = time.monotonic() + GENERATION_BUDGET_SECONDS

    # Resolved once, outside the loop: the mode does not change between
    # attempts, and an unknown mode must fail immediately rather than after
    # burning the retry budget.
    source = sourcing.for_mode(request.mode)
    source_arguments = _source_arguments(request)

    def attempt_candidate() -> Puzzle | None:
        """One pass of the pipeline: source -> clues -> uniqueness -> verdict.

        The single ``rng`` is threaded in here, which is what makes the
        *sequence* of discarded candidates reproducible and not merely the
        first one (ADR-0015).
        """
        # The argument list is the mode's, not the dispatcher's (see
        # sourcing.for_mode and _source_arguments): the random mode's
        # size/density and the library mode's key/size are assembled per mode,
        # and CARD-015's image path joins them there. The RNG is appended here
        # for every mode alike — including library's, whose only draw is
        # POL-001's boundary tie-break, which is what makes a library retry a
        # different rendering of the same template rather than a repeat.
        grid = source(*source_arguments, rng)
        candidate_clues = puzzle.record_candidate(grid)
        verdict = solver.solve(
            candidate_clues.rows, candidate_clues.columns, deadline=deadline
        )
        if puzzle.confirm_uniqueness(verdict.solution_count):
            return puzzle
        return None

    return run_bounded(
        puzzle.regenerate,
        attempt_candidate,
        reason=(
            "no candidate grid had exactly one solution; try a different "
            "--size/--density combination, or another --seed"
        ),
    )


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

    All formats of one run share one filename stem, and that stem is the
    puzzle's FR-015 name rather than a second, independently computed
    convention (:func:`_filename_stem`).

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

    payload = export.ExportPayload(
        grid=grid,
        row_clues=puzzle_clues.rows,
        column_clues=puzzle_clues.columns,
        seed=puzzle.seed,
        mode=puzzle.mode,
        size=puzzle.size,
        density=puzzle.density,
    )
    # One stem for the whole run, so a multi-format export produces one named
    # puzzle in several formats rather than several differently-named files.
    stem = _filename_stem(puzzle)
    directory = puzzle.request.out if puzzle.request.out is not None else Path.cwd()

    return tuple(
        export.write(payload, name, directory=directory, stem=stem) for name in formats
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
    it back verbatim from the aggregate. CARD-014 composes its
    ``<name>-<difficulty>.pdf`` from this same helper, so the two components
    are sanitized by one rule rather than two.

    A puzzle with no name at all is an aggregate somebody assembled by hand
    rather than one :func:`generate` produced; it falls back to CARD-007's
    stand-in, which is the same convention by construction.
    """
    if puzzle.name is None:
        return export.default_stem(puzzle.mode)
    # ``strip`` takes the leading and trailing dots with it, so no name can
    # sanitize into ``.``, ``..`` or a dotfile.
    stem = _UNSAFE_STEM_CHARACTERS.sub("-", puzzle.name).strip("-.")
    return stem or export.default_stem(puzzle.mode)

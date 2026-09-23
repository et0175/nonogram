"""Batch puzzle generation service for admin panel.

Generates multiple nonograms with metrics, stores in database,
and tracks progress for async operations.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
import uuid
from datetime import datetime, timedelta
import asyncio
import random

import logging

from nonogram import difficulty, orchestrator
from nonogram.orchestrator import MAX_BATCH_COUNT
from nonogram.errors import GenerationAbandoned, NotUniquelySolvable, SolverTimeout
from nonogram.limits import MAX_SIZE, MIN_SIZE

#: CARD-080: a refused candidate is logged here at error level. It means
#: the generation path produced something orchestrator.generate should
#: have made impossible, so it must be visible rather than counted away.
logger = logging.getLogger(__name__)

#: The floor on a *random* batch: fewer than ten puzzles is not a batch, it is
#: a handful, and a book wants variety (the panel's own sidebar says so). It
#: lives here rather than beside :data:`MAX_BATCH_COUNT` because it is this
#: layer's rule — ``orchestrator.generate_batch`` accepts a count of one and
#: the image path below still does.
#:
#: Named rather than written out, for exactly the reason the ceiling is: it was
#: a bare 10 here *and* a bare ``min="10"`` in ``batch_create.html``, which is
#: the shape the comment at the validation site records as a past defect — two
#: copies of a bound is the bug, one is the fix. ``admin/app.py`` publishes it
#: to the templates beside ``MAX_BATCH_COUNT``.
MIN_RANDOM_BATCH_COUNT = 10


class BatchStatus(Enum):
    """Status of a batch generation job."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class PuzzleMetrics:
    """Metrics for a generated puzzle."""

    difficulty_score: int  # 1-100
    difficulty_tier: str  # Easy/Medium/Hard
    # None for random-mode puzzles (CARD-050, AC-2, option 3b): there is no
    # source picture to measure fidelity against, so these are not a real
    # measurement there. Populated (1-100 / high|medium|low) for image mode.
    quality_score: Optional[int]
    recognizability: Optional[str]
    strategies_used: List[str]
    backtracking_depth: int


@dataclass
class GeneratedPuzzle:
    """A generated puzzle ready to store."""

    puzzle_id: str
    grid: list  # List[List[bool]]
    clues_rows: list  # List[List[int]]
    clues_cols: list  # List[List[int]]
    width: int
    height: int
    theme: str
    metrics: PuzzleMetrics
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BatchJob:
    """Represents a batch generation job."""

    batch_id: str
    status: BatchStatus
    total_count: int
    completed_count: int = 0
    puzzles: List[GeneratedPuzzle] = field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None  # When batch completed
    count: Optional[int] = None  # Alias for total_count for test compatibility
    sizes: Optional[List[int]] = None  # Store sizes for retry
    theme: Optional[str] = None  # Store theme for retry
    puzzle_count: int = 0  # Number of puzzles actually stored
    source: Optional[str] = None  # "random" | "images"

    def __post_init__(self):
        """Set count alias after initialization."""
        if self.count is None:
            self.count = self.total_count

    def get_progress_percent(self) -> int:
        """Get progress as percentage 0-100."""
        if self.total_count == 0:
            return 0
        return int((self.completed_count / self.total_count) * 100)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "batch_id": self.batch_id,
            "status": self.status.value,
            "total_count": self.total_count,
            "completed_count": self.completed_count,
            "progress_percent": self.get_progress_percent(),
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class BatchGenerator:
    """Service for generating batches of nonogram puzzles.

    Supports both in-memory storage (legacy, for backward compatibility) and
    database-backed storage (when session_factory is provided).
    """

    def __init__(self, puzzle_review_service=None, session_factory=None):
        """Initialize batch generator.

        Args:
            puzzle_review_service: PuzzleReviewService instance for storing puzzles
            session_factory: Optional callable that yields a DB session.
                           If None, uses in-memory dict storage (legacy mode).
                           If provided, uses database backend.
        """
        self._session_factory = session_factory
        # In-memory job tracking (used only in legacy mode when session_factory is None)
        self.jobs: dict[str, BatchJob] = {}
        self.puzzle_review_service = puzzle_review_service

    def _update_batch_status(self, batch_id: str, status: Optional[BatchStatus] = None, **fields) -> None:
        """Update batch status in legacy or DB mode.

        Args:
            batch_id: ID of the batch
            status: New BatchStatus, or None to keep current
            **fields: Additional fields to update (completed_count, error_message, etc.)
        """
        if self._session_factory is None:
            # Legacy mode: update in-memory job
            job = self.jobs.get(batch_id)
            if job:
                if status:
                    job.status = status
                for key, value in fields.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
                job.updated_at = datetime.utcnow()
        else:
            # DB mode: update Batch row
            import uuid as uuid_module
            from nonogram.db.models import Batch

            with self._session_factory() as db:
                batch_uuid = uuid_module.UUID(batch_id) if isinstance(batch_id, str) else batch_id
                batch = db.query(Batch).filter(Batch.id == batch_uuid).first()
                if batch:
                    if status:
                        batch.status = status.value if isinstance(status, BatchStatus) else status
                    for key, value in fields.items():
                        if key == "completed_count":
                            batch.completed_count = value
                        elif key == "error_message":
                            batch.error_message = value
                        elif key == "puzzle_count":
                            batch.puzzle_count = value
                        elif key == "completed_at":
                            batch.completed_at = value
                    batch.updated_at = datetime.utcnow()

    def create_batch(
        self,
        count: int,
        sizes: List[int],
        theme: str = "christmas",
        source: str = "random",
        quality_filter: int = 0,
        difficulty_tier: Optional[str] = None,
    ) -> str:
        """Create and start a batch generation job (legacy in-memory or DB-backed).

        Args:
            count: Number of puzzles to generate (1 to ``MAX_BATCH_COUNT`` for images,
                ``MIN_RANDOM_BATCH_COUNT`` to ``MAX_BATCH_COUNT`` for random)
            sizes: List of sizes to use (e.g., [10, 20, 30])
            theme: Puzzle theme (e.g., 'christmas')
            source: Generation source ('random' or 'images')
            quality_filter: Minimum quality score (0-100)
            difficulty_tier: The tier every puzzle in a random batch must grade
                into, in any spelling ``nonogram.difficulty.parse_tier``
                accepts — or ``None`` to accept any difficulty, which is what
                every batch did before CARD-138. ``None`` is the *only* way to
                say "any": an empty string names no tier and is refused, the
                same answer the CLI and ``orchestrator.generate_batch`` give
                it. Ignored by image-mode batches, which do not run POL-004's
                resample loop.

        Returns:
            batch_id for tracking progress

        Raises:
            ValueError: If parameters invalid
            UnsupportedDifficulty: ``difficulty_tier`` names no tier that
                exists. COMP-006's own error rather than a second
                ``ValueError``: which tiers exist is a domain rule with a
                domain error already defined for it, and the admin route maps
                it to a form error.
        """
        # Validate count based on source.
        # Images: allow 1..MAX (count = number of images)
        # Random: require 10..MAX (count = number to generate)
        #
        # The ceiling is read from the orchestrator rather than repeated. It was
        # 200 written out here *and* 200 written out there, and CARD-088 lowered
        # one of them — which is how this layer came to accept a count the layer
        # below refused, turning a validation error into a generation crash.
        # Two copies of a bound is the bug; one is the fix.
        if source == "images":
            if not 1 <= count <= MAX_BATCH_COUNT:
                raise ValueError(
                    f"Image batch count must be 1-{MAX_BATCH_COUNT}, got {count}"
                )
        else:
            if not MIN_RANDOM_BATCH_COUNT <= count <= MAX_BATCH_COUNT:
                raise ValueError(
                    f"Random batch count must be {MIN_RANDOM_BATCH_COUNT}-"
                    f"{MAX_BATCH_COUNT}, got {count}"
                )
        if not sizes or not all(MIN_SIZE <= s <= MAX_SIZE for s in sizes):
            raise ValueError(f"Sizes must be {MIN_SIZE}-{MAX_SIZE}, got {sizes}")
        if source not in ("random", "images"):
            raise ValueError(f"Source must be 'random' or 'images', got {source}")
        if not 0 <= quality_filter <= 100:
            raise ValueError(f"Quality filter must be 0-100, got {quality_filter}")
        # One tier vocabulary for the whole system (ADR-0031/R1): the requested
        # tier is resolved by COMP-006's own parser, so this module has no
        # easy/medium/hard mapping of its own and compares no score to
        # anything. The canonical spelling goes on from here, not the
        # operator's, so the second parse inside the orchestrator cannot
        # disagree with this one.
        #
        # `is not None` rather than a falsy test, because "" is a spelling like
        # any other and parse_tier refuses it — "any" is the *absence* of a
        # tier, and the form's Any option sends nothing rather than a word.
        requested_tier = (
            difficulty.parse_tier(difficulty_tier).value
            if difficulty_tier is not None
            else None
        )

        batch_uuid = uuid.uuid4()
        batch_id = str(batch_uuid)  # Keep string version for legacy mode + return value

        if self._session_factory is None:
            # Legacy mode: in-memory BatchJob
            job = BatchJob(
                batch_id=batch_id,
                status=BatchStatus.GENERATING,
                total_count=count,
                count=count,
                sizes=sizes,
                theme=theme,
                source=source,
            )
            self.jobs[batch_id] = job

            # Generate puzzles synchronously
            try:
                if source == "random":
                    self._generate_random_batch(batch_id, requested_tier)
                # TODO: else if source == "images": self._generate_from_images(...)

                job.status = BatchStatus.COMPLETE
                job.updated_at = datetime.utcnow()
                job.completed_at = datetime.utcnow()
            except Exception as e:
                job.status = BatchStatus.ERROR
                job.error_message = str(e)
                job.updated_at = datetime.utcnow()
                raise
        else:
            # DB mode: create Batch row with status=generating
            from nonogram.db.models import Batch

            try:
                # 1. Insert Batch row with status=generating before generation starts
                with self._session_factory() as db:
                    batch = Batch(
                        id=batch_uuid,  # Use UUID object, not string
                        status=BatchStatus.GENERATING.value,
                        source=source,
                        total_count=count,
                        completed_count=0,
                        puzzle_count=0,
                        sizes=sizes,
                        theme=theme,
                        quality_filter=quality_filter,
                    )
                    db.add(batch)
                    db.flush()

                # 2. Generate puzzles (each one commits individually)
                #
                # The requested tier travels as an argument rather than on the
                # Batch row: it is a property of this request, the row has no
                # column for it, and inventing one would mean a migration
                # against a database this card is not allowed to touch.
                if source == "random":
                    self._generate_random_batch(batch_id, requested_tier)
                # TODO: else if source == "images": self._generate_from_images(...)

                # 3. Mark batch complete
                self._update_batch_status(
                    batch_id,
                    BatchStatus.COMPLETE,
                    completed_at=datetime.utcnow(),
                )
            except Exception as e:
                self._update_batch_status(
                    batch_id,
                    BatchStatus.ERROR,
                    error_message=str(e),
                )
                raise

        return batch_id

    def _generate_random_batch(
        self, batch_id: str, difficulty_tier: Optional[str] = None
    ) -> None:
        """Generate random puzzles using the real pipeline and store.

        Uses orchestrator.generate_batch() to generate real, uniquely-solvable
        puzzles with calculated difficulty scores — the same pipeline as the CLI.

        The returned list may be shorter than the requested count: since
        CARD-083 a candidate the generator had to abandon is skipped rather
        than ending the batch. The shortfall is reported on the batch record
        below, beside the store-refusal note CARD-080 added, and the two are
        kept as separate sentences because they mean opposite things.

        With a tier requested (CARD-138) a candidate has a second way to fail:
        it can come out uniquely solvable and still grade outside the tier, in
        which case POL-004 discards and redraws it, and a candidate whose
        resamples all miss is abandoned like any other. The counts below cannot
        tell the two apart — the generator reports one `abandoned` number — so
        the note says which tier was asked for and that the shortfall is the
        tier, rather than claiming uniqueness was the problem.

        The same holds for the batch's clock (CARD-088): every discarded
        candidate is redrawn out of the one batch budget, so a targeted batch
        runs out of it *sooner* than an untargeted one, and its note has to
        offer Any difficulty beside "fewer puzzles" and "a smaller size". The
        store-refusal sentence stays un-tiered on purpose — it reports a bug in
        the generation path (CARD-080), which the requested tier has nothing to
        do with.

        Works in both legacy and DB-backed modes.

        Args:
            batch_id: ID of batch job to generate for
            difficulty_tier: The tier every puzzle must grade into, already in
                COMP-006's canonical spelling (``create_batch`` parsed it), or
                ``None`` to accept any difficulty.
        """
        if self._session_factory is None:
            # Legacy mode: read from in-memory job
            job = self.jobs[batch_id]
            count = job.total_count
            sizes = job.sizes or [15, 20, 25]
            theme = job.theme or "christmas"
        else:
            # DB mode: fetch from database
            import uuid as uuid_module
            from nonogram.db.models import Batch

            with self._session_factory() as db:
                batch_uuid = uuid_module.UUID(batch_id) if isinstance(batch_id, str) else batch_id
                batch = db.query(Batch).filter(Batch.id == batch_uuid).first()
                if not batch:
                    raise ValueError(f"Batch {batch_id} not found")
                count = batch.total_count
                sizes = batch.sizes or [15, 20, 25]
                theme = batch.theme or "christmas"
                # batch.quality_filter is still accepted/stored on the Batch
                # row (create_batch validates 0-100), but CARD-050 (AC-2,
                # option 3b) no longer applies it here — see the comment
                # below on why random-mode quality_score is None rather
                # than a fabricated number.

        # Store each puzzle
        puzzle_count = 0
        # CARD-080: candidates the store refused. Should always be 0; when it
        # is not, it is carried onto the batch record below so somebody sees it.
        refused_count = 0
        # Puzzles the generator has handed over so far, stored or refused.
        made = 0

        def store(puzzle) -> None:
            """Store one puzzle the moment the generator has made it (CARD-093).

            Called from inside ``orchestrator.generate_batch`` rather than over
            its return value, because the batch does not always return: three
            abandonments in a row and a solver timeout both raise, and a worker
            killed mid-batch never gets that far either. Storing here means the
            work done before any of those is already in the store.
            """
            nonlocal puzzle_count, refused_count, made
            made += 1
            # CARD-050 (AC-2, option 3b): random-mode puzzles have no source
            # picture to measure fidelity against, so quality_metric.measure_
            # quality() (an image-comparison metric) does not apply here —
            # unlike the old `puzzle.quality_score if hasattr(...) else 75`
            # fallback, which was unconditionally 75 for every puzzle
            # (orchestrator.Puzzle never had a quality_score attribute) and
            # indistinguishable from a real measurement. quality_score/
            # recognizability are explicitly None rather than a fabricated
            # number; see CARD-050 Worktree notes for the full reasoning.
            #
            # quality_filter is therefore meaningless for random-mode
            # batches and is not applied here — every candidate the
            # orchestrator returns is stored (the UI never exposes this
            # filter for random-mode batches either; see batch_create.html).
            if self.puzzle_review_service:
                # CARD-080: the store refuses a grid the solver will not
                # certify. Reaching that is a bug, not a data condition — every
                # candidate here came through orchestrator.generate, which
                # enforces INV-002 — so it is logged at error level rather than
                # swallowed, and counted as refused rather than stored. The
                # batch continues: one bad candidate is no reason to lose the
                # rest. What tells the owner is the note written onto the batch
                # record at the end of this method — not the log, which nobody
                # is tailing on a localhost admin panel.
                try:
                    self.puzzle_review_service.add_puzzle(
                        grid=puzzle.grid,
                        clues_rows=puzzle.clues.rows,
                        clues_cols=puzzle.clues.columns,
                        width=puzzle.width,
                        height=puzzle.height,
                        theme=theme,
                        difficulty_score=puzzle.difficulty_score,
                        difficulty_tier=puzzle.difficulty_tier,
                        quality_score=None,
                        recognizability=None,
                        # FR-029: the generation path now has the deciding
                        # solve's ladder on the aggregate (CARD-072), so the
                        # store no longer has to fall back to deriving it from
                        # its own uniqueness proof.
                        strategies_used=list(puzzle.strategies),
                        batch_id=batch_id,
                    )
                except NotUniquelySolvable:
                    logger.error(
                        "batch %s: the store refused a candidate as not "
                        "uniquely solvable. This should be unreachable — every "
                        "candidate came through orchestrator.generate, which "
                        "enforces INV-002 — so treat it as a bug in the "
                        "generation path, not as a rejected puzzle.",
                        batch_id,
                        exc_info=True,
                    )
                    refused_count += 1
                else:
                    puzzle_count += 1

            # Update progress
            if self._session_factory is None:
                # Legacy mode
                job = self.jobs[batch_id]
                job.completed_count += 1
                job.updated_at = datetime.utcnow()
            else:
                # DB mode: update completed_count after each puzzle
                self._update_batch_status(batch_id, completed_count=made)

        # Generate real puzzles using the orchestrator pipeline, storing each as
        # it arrives.
        #
        # A batch that stops early is not a failed batch once it has made
        # something (CARD-093, owner Q-2): the puzzles are real and already
        # stored, so it completes, and a note says why it stopped and how far it
        # got. CARD-083's stopping rule still stops it — this only decides what
        # happens to the work before the stop. With nothing made, the exception
        # propagates and create_batch marks the batch ERROR exactly as before.
        stopped_by: Exception | None = None
        try:
            puzzles = orchestrator.generate_batch(
                count=count,
                sizes=sizes,
                source="random",
                # None accepts any difficulty — today's behaviour for a batch
                # nobody targeted. A tier here puts POL-004's resample loop
                # behind every candidate (CARD-138); the bound on it is the
                # generator's and is not touched from this side.
                difficulty_tier=difficulty_tier,
                on_puzzle=store,
            )
        except (GenerationAbandoned, SolverTimeout) as stop:
            if made == 0:
                raise
            stopped_by = stop
            puzzles = None

        # Final update with puzzle count, plus — when the store refused
        # anything — a note saying so on the batch record itself.
        #
        # CARD-080 review, F-003: `refused_count` was written, incremented and
        # never read, under a comment claiming it was the owner's signal. It
        # now is one. `error_message` is an existing column that
        # batch_status.html already renders as an alert, so the refusal lands
        # on the page an owner looks at after a batch, without a migration.
        # The batch is not marked failed: the puzzles that did store are real
        # and keeping them is right — what failed is a candidate, and the note
        # says which kind of failure it was.
        # Two different shortfalls, and they mean opposite things. A candidate
        # the *generator* abandoned is ordinary bad luck at a measured rate
        # (CARD-083); a candidate the *store* refused should be unreachable and
        # is a bug. They are reported as separate sentences rather than one
        # "missing puzzles" number, because an owner who cannot tell them apart
        # learns nothing from either.
        #
        # A batch that asked for a tier says so in every sentence below that
        # reports a *shortfall against the tier* (CARD-138): the early stop,
        # the abandoned candidates, and the candidates the clock never reached.
        # Not decoration: "17 of 40 puzzles made" and "17 of 40 medium puzzles
        # made" are different facts, and an owner filling a book's medium quota
        # is reading these notes to find out how many of the 40 they actually
        # have — and which lever (fewer puzzles, a smaller size, or Any
        # difficulty) buys them the rest.
        #
        # The store-refusal sentence is the one exception, and deliberately so.
        # It reports a candidate the *store* rejected as not uniquely solvable,
        # which CARD-080 established is a bug in the generation path rather
        # than a property of this batch; it means the same thing whatever tier
        # was asked for, and naming the tier there would invite an owner to
        # change their request to work around a defect that is not theirs.
        #
        # `target` is the short form, built once from the tier the request
        # carried and empty for an untargeted batch — which is what keeps the
        # untargeted notes worded exactly as they were. The sentences that need
        # the tier as a noun rather than an adjective spell it out instead, and
        # branch, because their untargeted wording is not a substring of their
        # targeted one.
        target = f" {difficulty_tier}" if difficulty_tier is not None else ""
        notes = []
        if stopped_by is not None:
            reason = (
                "a candidate timed out in the solver"
                if isinstance(stopped_by, SolverTimeout)
                else f"{stopped_by}"
            )
            notes.append(
                f"This batch stopped early with {made} of {count}{target} puzzles made: "
                f"{reason}. The {made} it made are kept (CARD-093); re-run for "
                f"the rest, and if it stops again the size or the request is "
                f"the problem rather than luck."
            )
            if difficulty_tier is not None:
                notes.append(
                    f"It was asked for {difficulty_tier} puzzles, so "
                    f"\"the request\" includes the tier: a candidate that came "
                    f"out uniquely solvable but graded outside {difficulty_tier} "
                    f"is discarded and redrawn (POL-004), and candidates that "
                    f"run out of redraws stop the batch the same way an "
                    f"unsolvable draw does. Asking for Any difficulty is the "
                    f"way to tell the two apart."
                )
        # Two different shortfalls, and they mean opposite things to whoever
        # reads this: an abandoned candidate is bad luck and a re-run may do
        # better, while a batch stopped by its own clock will stop in the same
        # place every time. Read off the result rather than inferred from
        # `count - len(puzzles)`, which cannot tell them apart (CARD-088).
        # A stopped batch has no result to read these from; its note above
        # already carries the counts the generator's message gives.
        abandoned_count = (
            0 if puzzles is None else getattr(puzzles, "abandoned", count - len(puzzles))
        )
        not_attempted = 0 if puzzles is None else getattr(puzzles, "not_attempted", 0)
        if abandoned_count and difficulty_tier is not None:
            # The untargeted sentence would be a lie here: with a tier asked
            # for, a skipped candidate was far more often a perfectly good
            # puzzle of the wrong grade than an unsolvable draw, and the
            # generator reports one `abandoned` number that cannot tell them
            # apart. So this says what is certain — how many are missing, and
            # that the tier is what they were measured against.
            notes.append(
                f"{abandoned_count} of {count} candidates could not be made "
                f"{difficulty_tier} within the retry budget and were skipped, "
                f"so this batch has {made} {difficulty_tier} puzzles rather "
                f"than {count}. The shortfall is the tier, not uniqueness: a "
                f"candidate that came out uniquely solvable but graded outside "
                f"{difficulty_tier} is discarded and redrawn (POL-004), and one "
                f"whose redraws all missed the tier is skipped. The batch was "
                f"kept rather than discarded (CARD-083). Re-run for the rest, "
                f"or ask for Any difficulty if you need the count more than "
                f"the tier."
            )
        elif abandoned_count:
            notes.append(
                f"{abandoned_count} of {count} candidates could not be made "
                f"uniquely solvable within the retry budget and were skipped, "
                f"so this batch has {made} puzzles rather than {count}. "
                f"That is expected occasionally — it is how a random grid can "
                f"come out — and the batch was kept rather than discarded "
                f"(CARD-083). Re-run if you need the full count."
            )
        if not_attempted and difficulty_tier is not None:
            # The give-up mode a tier makes *more* likely, not less: every
            # off-tier candidate is discarded and redrawn out of this same
            # budget (POL-004), so a targeted batch reaches the clock sooner
            # than the untargeted one the sentence below was written for. An
            # owner told only "ask for fewer, or for a smaller size" would be
            # missing the lever that dominates the cost here, so this names the
            # tier and offers Any as the third way out.
            notes.append(
                f"{not_attempted} of the {count} {difficulty_tier} puzzles "
                f"were never attempted: the batch reached its time budget "
                f"first. This is not bad luck — the same request will stop in "
                f"the same place — so ask for fewer puzzles, for a smaller "
                f"size, or for Any difficulty. The tier is part of the cost: "
                f"a candidate that came out uniquely solvable but graded "
                f"outside {difficulty_tier} is discarded and redrawn "
                f"(POL-004), and those redraws are spent out of this same "
                f"budget. A puzzle costs about 0.06s at 20x20 and about 3.9s "
                f"at 30x30 before any redraw, which is the whole of the "
                f"difference."
            )
        elif not_attempted:
            notes.append(
                f"{not_attempted} of {count} were never attempted: the batch "
                f"reached its time budget first. This is not bad luck — the "
                f"same request will stop in the same place — so ask for fewer "
                f"puzzles, or for a smaller size. A puzzle costs about 0.06s at "
                f"20x20 and about 3.9s at 30x30, which is the whole of the "
                f"difference."
            )
        if refused_count:
            notes.append(
                f"{refused_count} of {made} generated candidates were refused "
                "by the store as not uniquely solvable and are not in this batch. "
                "Every candidate came through orchestrator.generate, which enforces "
                "INV-002, so this is a bug in the generation path rather than a "
                "property of this batch; the admin log carries the per-candidate "
                "reasons."
            )
        refusal_note = " ".join(notes) if notes else None

        if self._session_factory is None:
            job = self.jobs[batch_id]
            job.puzzle_count = puzzle_count
            if refusal_note is not None:
                job.error_message = refusal_note
        else:
            final_fields = {"puzzle_count": puzzle_count}
            if refusal_note is not None:
                final_fields["error_message"] = refusal_note
            self._update_batch_status(batch_id, **final_fields)

    def get_batch_status(self, batch_id: str) -> Optional[BatchJob]:
        """Get status of a batch generation job (legacy or DB-backed).

        Args:
            batch_id: ID of the batch job

        Returns:
            BatchJob with current status, or None if not found
        """
        if self._session_factory is None:
            # Legacy mode: check in-memory jobs
            return self.jobs.get(batch_id)
        else:
            # DB mode: query database
            import uuid as uuid_module
            from nonogram.db.models import Batch

            with self._session_factory() as db:
                batch_uuid = uuid_module.UUID(batch_id) if isinstance(batch_id, str) else batch_id
                batch = db.query(Batch).filter(Batch.id == batch_uuid).first()
                if not batch:
                    return None

                # Convert Batch row to BatchJob for backward compatibility
                return BatchJob(
                    batch_id=str(batch.id),
                    status=BatchStatus(batch.status),
                    total_count=batch.total_count,
                    completed_count=batch.completed_count,
                    puzzle_count=batch.puzzle_count,
                    error_message=batch.error_message,
                    created_at=batch.created_at,
                    updated_at=batch.updated_at,
                    completed_at=batch.completed_at,
                    sizes=batch.sizes,
                    theme=batch.theme,
                    source=batch.source,
                )

    @staticmethod
    def _date_bounds(date_from: Optional[str], date_to: Optional[str]):
        """``(first datetime, datetime after the last day)``, either ``None``.

        Both ends are whole days and inclusive, the way the review list's
        date filter reads them.

        Raises:
            ValueError: a date is not YYYY-MM-DD, or the range is inverted.
        """
        def parse(value):
            if not value:
                return None
            try:
                return datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid date {value!r} (use YYYY-MM-DD)") from None

        start, end = parse(date_from), parse(date_to)
        if start and end and start > end:
            raise ValueError("Date from must be on or before date to")
        return start, (end + timedelta(days=1)) if end else None

    def list_batches(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> List[BatchJob]:
        """Every batch created within the date range, newest first.

        Args:
            date_from: First day included (YYYY-MM-DD), or None for no bound.
            date_to: Last day included (YYYY-MM-DD), or None for no bound.

        Raises:
            ValueError: a date is not YYYY-MM-DD, or the range is inverted.
        """
        start, end = self._date_bounds(date_from, date_to)

        if self._session_factory is None:
            jobs = [
                job for job in self.jobs.values()
                if (start is None or job.created_at >= start)
                and (end is None or job.created_at < end)
            ]
            return sorted(jobs, key=lambda job: job.created_at, reverse=True)

        from nonogram.db.models import Batch

        with self._session_factory() as db:
            query = db.query(Batch)
            if start is not None:
                query = query.filter(Batch.created_at >= start)
            if end is not None:
                query = query.filter(Batch.created_at < end)
            return [
                BatchJob(
                    batch_id=str(batch.id),
                    status=BatchStatus(batch.status),
                    total_count=batch.total_count,
                    completed_count=batch.completed_count,
                    puzzle_count=batch.puzzle_count,
                    error_message=batch.error_message,
                    created_at=batch.created_at,
                    updated_at=batch.updated_at,
                    completed_at=batch.completed_at,
                    sizes=batch.sizes,
                    theme=batch.theme,
                    source=batch.source,
                )
                for batch in query.order_by(Batch.created_at.desc()).all()
            ]

    def get_batch_puzzles(self, batch_id: str, offset: int = 0, limit: int = 25) -> Optional[List[dict]]:
        """Get puzzles from a completed batch (legacy or DB-backed).

        Args:
            batch_id: ID of the batch
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            List of puzzle dicts, or empty list if batch not found
        """
        if not self.puzzle_review_service:
            return []

        # Check if batch exists (legacy or DB mode)
        job = self.get_batch_status(batch_id)
        if not job:
            return []

        # Get puzzles from this specific batch
        from nonogram.admin.puzzle_review import PuzzleFilter
        filter_opts = PuzzleFilter(batch_id=batch_id, limit=100)  # Max limit is 100
        result = self.puzzle_review_service.filter_puzzles(filter_opts)

        # Return paginated results
        start = offset
        end = start + limit
        return result.puzzles[start:end] if result.puzzles else []

    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a batch generation job.

        Args:
            batch_id: ID of the batch

        Returns:
            True if cancelled, False if not found or already complete
        """
        job = self.jobs.get(batch_id)
        if not job:
            return False

        # Can only cancel if still generating
        if job.status in (BatchStatus.GENERATING, BatchStatus.PENDING):
            job.status = BatchStatus.CANCELLED
            job.updated_at = datetime.utcnow()
            return True

        return False


# Global batch generator instance
_batch_generator = None


def get_batch_generator(puzzle_review_service=None) -> BatchGenerator:
    """Get the singleton batch generator."""
    global _batch_generator
    if _batch_generator is None:
        _batch_generator = BatchGenerator(puzzle_review_service)
    elif puzzle_review_service and not _batch_generator.puzzle_review_service:
        _batch_generator.puzzle_review_service = puzzle_review_service
    return _batch_generator

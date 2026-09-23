"""Book management service for admin panel.

Handles book creation, puzzle curation, PDF generation setup, and KDP metadata.
Supports both in-memory storage (legacy) and database-backed storage (when session_factory provided).
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import json
import logging
import uuid as uuid_module

from nonogram.admin.book_page_spec import (
    BOOK1_PROFILE,
    FLOOR_MM,
    book_cell_mm,
    book_page_spec,
)
from nonogram.admin.book_plan import (
    BUCKETS,
    DEFAULT_PLAN,
    TIERS,
    UNGROUPED_ORDER_REFUSAL,
    DistributionPlan,
    InvalidPlan,
    LevelBoundary,
    LongestSideBucket,
    Split,
    book_levels,
    is_level_order,
    moved_within_level,
    place_in_level,
    planned_cells,
    prefill,
    selection_cells,
    with_split,
)
from nonogram.difficulty import Tier, tier_of_record

logger = logging.getLogger(__name__)


class BookStatus(Enum):
    """Status of a book in the publishing workflow."""

    DRAFT = "draft"
    READY_FOR_PDF = "ready_for_pdf"
    PDF_GENERATED = "pdf_generated"
    READY_FOR_KDP = "ready_for_kdp"
    PUBLISHED = "published"


@dataclass
class BookMetadata:
    """Metadata for KDP book submission."""

    title: str
    description: str
    theme: str
    target_audience: str
    size: str  # e.g., "8x10" (trim size)
    page_count: int
    cover_image_url: Optional[str] = None
    pdf_url: Optional[str] = None
    kdp_asin: Optional[str] = None


@dataclass
class Book:
    """Represents a book with puzzles and metadata."""

    book_id: str
    metadata: BookMetadata
    puzzle_ids: List[str] = field(default_factory=list)
    puzzle_titles: Dict[str, str] = field(default_factory=dict)  # {puzzle_id: "custom title"}
    status: str = BookStatus.DRAFT.value
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    # The stored print specification (the ``books`` print columns, cm as
    # strings). ``None`` is an empty column: ``book_page_spec`` falls back to
    # CON-018's Book 1 profile for it. create_book stores the profile (AC-181).
    trim_width_cm: Optional[str] = None
    trim_height_cm: Optional[str] = None
    gutter_margin_cm: Optional[str] = None
    outside_margin_cm: Optional[str] = None
    outside_margin_bleed_cm: Optional[str] = None
    # CARD-121 (FR-031, INV-006): the ids this book admitted below the 4.8 mm
    # floor (TERM-025). Read it through :meth:`BookManager.floor_overrides`
    # rather than off the book, so both storage modes answer the same way.
    floor_overrides: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "book_id": self.book_id,
            "metadata": {
                "title": self.metadata.title,
                "description": self.metadata.description,
                "theme": self.metadata.theme,
                "target_audience": self.metadata.target_audience,
                "size": self.metadata.size,
                "page_count": self.metadata.page_count,
                "cover_image_url": self.metadata.cover_image_url,
                "pdf_url": self.metadata.pdf_url,
                "kdp_asin": self.metadata.kdp_asin,
            },
            "puzzle_count": len(self.puzzle_ids),
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# --------------------------------------------------------------------------
# The readiness gate (CARD-124; FR-037, INV-007, ADR-0035)
# --------------------------------------------------------------------------
#
# A book leaves draft only as the book its stored plan describes: every one of
# the 12 cells within the tolerance of its share of the planned total (see
# :func:`off_plan_cells` for exactly how far that guarantee reaches). The
# verdict is a pure function of the stored plan and the selection's records, so
# it is the same verdict in both storage modes and can be read on its own.

#: How far one longest-side x tier cell may sit from its planned share and
#: still leave draft, in percentage points. The bound is **inclusive**: a cell
#: exactly 3 points out passes (AC-219), one 4 points out does not (AC-220).
READY_TOLERANCE_POINTS = 3

#: What a book with no stored plan is told at the gate (ADR-0035 (c)). Every
#: book created since ADR-0034 starts on the default plan, so this is the
#: pre-migration row's remedy, and it is one save on Print setup. A stored
#: document too damaged to decode says the same thing, for the same remedy
#: (:meth:`BookManager._refuse_unless_the_planned_book`).
NO_PLAN_REFUSAL = (
    "This book has no stored plan, so it cannot leave draft. "
    "Store one on Print setup first."
)

#: What the gate says when the selection cannot be read at all — a manager
#: wired without a puzzle store, holding a book that does list puzzles. The
#: gate refuses rather than judging a selection it could not see (F-004);
#: unlike the two refusals above this is a wiring fault, not the owner's, so
#: it names the cause instead of offering a remedy on a screen.
UNREADABLE_SELECTION_REFUSAL = (
    "This book's selection cannot be read (the panel has no puzzle store), so it "
    "cannot be checked against its plan and cannot leave draft."
)


def off_plan_cells(plan: DistributionPlan, puzzles) -> List[tuple]:
    """The cells whose count is further from the plan than the tolerance.

    ``(bucket, tier, actual_count, planned_count)`` per offending cell, in
    :data:`BUCKETS` x :data:`TIERS` order; empty when the selection matches
    the plan. ``puzzles`` are the selection's stored records, counted by
    CARD-119's :func:`~nonogram.admin.book_plan.selection_cells` — the one
    bucketing function (EC-024), never re-derived here.

    Both shares are taken over the **planned** total (ADR-0035 (b)): a cell's
    actual share is its count divided by ``plan.count``, and its planned share
    is the plan's own cell divided by the same number. Measuring the mix
    against the stated total rather than against the selection's own size is
    what makes an under-filled selection fail even when its proportions are
    right (CK-1): 50 puzzles at exactly half of every planned cell are each
    half a planned share short, not on target.

    That is as far as the guarantee goes, and it is worth stating precisely
    (review cycle 2, F-004). "Ready means the planned book, not merely the
    planned mix" holds **exactly when the matrix sums to ``plan.count``** —
    every plan Print setup prefills does, and so does every hand edit that
    keeps the column totals on the tier counts. A hand-edited matrix that
    disagrees with its split (:attr:`DistributionPlan.disagrees_with_split`,
    warned about but never refused, FR-034) is still measured cell by cell
    against the stated total, and nothing here re-reads ``count`` from the
    matrix — so a plan of 100 whose cells sum to 5 is passed by a selection of
    5, every cell 0 points out. That is the plan the owner stored, spent to
    the letter; it is not an INV-007 hole, because INV-007 is a per-cell rule
    and every cell is on its plan. The matrix, not the count, is the thing a
    disagreeing plan under-fills, and Print setup already tells the owner so.

    The plan's ``count`` is the denominator, not the matrix's sum: the two
    differ only for such a hand-edited matrix, and the total the owner planned
    is the book ADR-0035 measures against. It is also never zero (INV-005), so
    the comparison has no degenerate case.

    The comparison is exact integer arithmetic — ``|actual - planned| * 100 <=
    tolerance * total`` rather than a difference of two floats against 3.0 —
    because the bound is inclusive and AC-219 and AC-220 sit either side of
    exactly that boundary.
    """
    planned = planned_cells(plan)
    actual = selection_cells(puzzles)
    return [
        (bucket, tier, actual[(bucket, tier)], planned[(bucket, tier)])
        for bucket in BUCKETS
        for tier in TIERS
        if abs(actual[(bucket, tier)] - planned[(bucket, tier)]) * 100
        > READY_TOLERANCE_POINTS * plan.count
    ]


def _whole_percent(count: int, total: int) -> int:
    """``count`` as a whole percent of ``total``, rounded half up, in integers."""
    return (2 * 100 * count + total) // (2 * total)


def ready_refusal(plan: Optional[DistributionPlan], puzzles) -> Optional[str]:
    """Why this selection may not leave draft, or ``None`` when it may.

    ADR-0035/R1 in one place: no stored plan is a refusal with its remedy, and
    otherwise every cell must be within :data:`READY_TOLERANCE_POINTS` of its
    planned share. A refusal names **every** offending cell with its actual and
    planned share, so the owner sees the whole of what is wrong at once
    (AC-221).

    ``plan`` is ``None`` both for a book that has no stored plan and for one
    whose stored document cannot be decoded — the caller has already collapsed
    the two (see :meth:`BookManager._refuse_unless_the_planned_book`), because
    the owner's remedy is the same save either way.
    """
    if plan is None:
        return NO_PLAN_REFUSAL
    offenders = off_plan_cells(plan, puzzles)
    if not offenders:
        return None
    named = "; ".join(
        f"{bucket.label} x {tier.value}:"
        f" {_whole_percent(actual, plan.count)}%"
        f" against {_whole_percent(planned, plan.count)}%"
        for bucket, tier, actual, planned in offenders
    )
    return (
        "This book does not match its plan, so it cannot leave draft. "
        f"More than {READY_TOLERANCE_POINTS} percentage points out: {named}."
    )


# --------------------------------------------------------------------------
# The 4.8 mm printed-cell floor (CARD-121; FR-031, NFR-008, INV-006, EC-021)
# --------------------------------------------------------------------------
#
# A puzzle whose cell on the book's trim falls below FLOOR_MM joins the book
# only together with an override stored for its id. The rule is enforced
# **here**, where membership is written, and not at either route: FR-031 names
# two add routes today (the selection step and the detail page's paste-IDs
# form) and EC-021 extends the obligation to "any future route ending in the
# book store", which a route-level check could not keep.
#
# The cell itself is never estimated here. It is
# ``book_cell_mm(book_page_spec(book), ...)`` — CARD-115's one door onto
# COMP-007's geometry, the same call FR-030's PDF makes, so the tile, this
# refusal and the finalise count cannot disagree about a puzzle (G-1,
# ADR-0036/R2).


@dataclass(frozen=True)
class FloorRefusal:
    """One puzzle this book may not take: its cell, against the floor.

    Carries the two figures AC-183 asks the owner to be shown — the puzzle's
    own cell and the floor it missed — rather than a pre-baked sentence, so
    that a caller which wants them apart (a tile, a count, a log line) is not
    forced to parse them back out of prose. :meth:`message` is the sentence.
    """

    puzzle_id: str
    #: The puzzle's printed cell in millimetres, or ``None`` when it could not
    #: be computed at all — a stored record whose clues cannot be read. That is
    #: a refusal too (see :meth:`BookManager.floor_refusals`): a cell nobody can
    #: compute is not a cell known to clear the floor.
    cell_mm: Optional[float]
    #: Why the cell could not be computed, for the ``cell_mm is None`` case.
    reason: Optional[str] = None

    def message(self) -> str:
        """The refusal as the owner reads it, naming both figures (AC-183)."""
        if self.cell_mm is None:
            return (
                f"Puzzle {self.puzzle_id} was not added: its cell on this book "
                f"cannot be measured against the {FLOOR_MM:g} mm floor "
                f"({self.reason})."
            )
        return (
            f"Puzzle {self.puzzle_id} was not added: {self.cell_mm:.2f} mm "
            f"against the {FLOOR_MM:g} mm floor. Tick the override for it to "
            f"add it anyway."
        )


@dataclass(frozen=True)
class AddOutcome:
    """What one submission did at the book store: what joined, and what did not.

    Returned by :meth:`BookManager.add_puzzles_reporting_refusals`, so a route
    can word its refusal from the **same** measurement the store enforced
    rather than asking for a second one (EC-021: no two of them can disagree
    about a puzzle, and a second pass is a second chance to). The two lists
    partition the submission's *distinct* ids — a duplicate inside one
    submission is one decision, not two.
    """

    #: The submitted ids the floor let through, in submission order. These
    #: are the ids the add applied; one already in the book is among them (it
    #: was admitted, it simply changed nothing), which is the count the two
    #: routes have always shown.
    admitted: List[str]
    #: One :class:`FloorRefusal` per submitted id the floor kept out.
    refusals: List[FloorRefusal]


#: What an add is told when the book moved underneath it between the
#: measurement and the write (review cycle 1, F-001). The verdict is decided on
#: a snapshot of the row — the published refusal, the stored overrides and the
#: trim and margins every cell is measured on — and DB mode writes in a second
#: session; a publish, a Print-setup save or a concurrent remove landing in
#: between would otherwise be overwritten by a decision made before it. Nothing
#: is committed, so the remedy is to look at the book as it now is and submit
#: again.
CONCURRENT_CHANGE_REFUSAL = (
    "This book changed while its puzzles were being measured (its status, its "
    "trim and margins, or its stored overrides), so nothing was added. Reload "
    "the book and submit again."
)

#: The row columns an add's verdict is a function of: the status the published
#: refusal reads, the four print columns :func:`book_page_spec` measures every
#: cell on, and the stored overrides that decide which below-floor ids may
#: join. Not ``puzzle_ids``: membership is a union written from the live row
#: inside the writing session, so another puzzle arriving or leaving does not
#: change what this submission decided — but a *removal* takes that puzzle's
#: override with it, which the overrides comparison catches.
_VERDICT_COLUMNS = (
    "status",
    "trim_width_cm",
    "trim_height_cm",
    "gutter_margin_cm",
    "outside_margin_cm",
)


def _verdict_state(source) -> tuple:
    """The state of ``source`` an add's floor verdict rests on (F-001).

    Read off a :class:`Book` snapshot before the measurement and off the live
    ``books`` row inside the writing session; the write lands only when the two
    are equal, so a verdict is never committed against a row that has moved
    since it was made. Works on either because both carry the same attribute
    names.
    """
    return (
        tuple(getattr(source, column, None) for column in _VERDICT_COLUMNS),
        tuple(str(pid) for pid in (getattr(source, "floor_overrides", None) or [])),
    )


def _clue_lines(record: Dict[str, Any], field_name: str) -> tuple:
    """One stored clue field as ``compute_layout`` wants it.

    The store keeps ``clues_rows``/``clues_cols`` as lists of lists of ints;
    the layout takes a tuple of tuples. The same conversion the book PDF does
    (``book_pdf_generator``), so both measure the same puzzle.

    Raises:
        ValueError: the field is missing, empty, or not a sequence of
            sequences of whole numbers. An unreadable clue set is not an
            absent one: it means this record has no measurable cell, and the
            caller turns that into a refusal rather than a silent pass.
    """
    lines = record.get(field_name)
    if not lines:
        raise ValueError(f"{field_name} is empty")
    try:
        return tuple(tuple(int(run) for run in line) for line in lines)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} is not a clue set ({error})") from None


def _merged_overrides(stored, added) -> List[str]:
    """``stored`` with ``added`` folded in, as a **new** list of id strings.

    Order is stored-then-new with duplicates dropped, which keeps the document
    stable across repeated adds instead of reshuffling on every write. Always a
    new list, never the stored one mutated: a JSON column compares by identity
    (CARD-100/CARD-101), and this is the pattern that cannot be got wrong.
    """
    return list(dict.fromkeys([str(pid) for pid in (stored or [])] + [str(pid) for pid in added]))


class BookManager:
    """Service for managing books and their puzzles.

    Supports both in-memory storage (legacy, for backward compatibility) and
    database-backed storage (when session_factory is provided).
    """

    def __init__(self, session_factory=None, puzzle_store=None):
        """Initialize book manager.

        Args:
            session_factory: Optional callable that yields a DB session.
                           If None, uses in-memory dict storage (legacy mode).
                           If provided, uses database backend.
            puzzle_store: The :class:`PuzzleReviewService` that owns the puzzle
                           rows (CARD-100). Membership is two facts that must be
                           written together — this book's list, and each
                           puzzle's ``book_id`` — and puzzle rows are not this
                           module's to write, so it asks the store. A manager
                           built without one keeps its books correctly and says
                           so in the log rather than pretending; every manager
                           ``create_app`` builds has one.
        """
        self._session_factory = session_factory
        self.puzzle_store = puzzle_store
        # In-memory book storage (used only in legacy mode when session_factory is None)
        self.books: Dict[str, Book] = {}
        # In-memory plans, keyed by book id (CARD-120). Kept beside the books
        # rather than on the Book dataclass so that saving a plan has nothing
        # of the selection within reach (G-2), exactly as in DB mode where
        # save_plan writes one column.
        self._plans: Dict[str, DistributionPlan] = {}
        self._next_id = 1

    def create_book(
        self,
        title: str,
        description: str,
        theme: str,
        target_audience: str,
        size: str = "8x10",
        cover_image_url: Optional[str] = None,
    ) -> str:
        """Create a new book.

        Args:
            title: Book title
            description: Book description
            theme: Book theme (e.g., 'christmas')
            target_audience: Target audience (e.g., 'seniors')
            size: Trim size for KDP (default "8x10")
            cover_image_url: URL to cover image

        Returns:
            book_id

        Raises:
            ValueError: If parameters invalid
        """
        if not title or len(title.strip()) == 0:
            raise ValueError("Title cannot be empty")
        if not description or len(description.strip()) == 0:
            raise ValueError("Description cannot be empty")
        if theme not in ("christmas", "halloween", "easter", "valentine", "generic"):
            raise ValueError(f"Invalid theme: {theme}")
        if not target_audience or len(target_audience.strip()) == 0:
            raise ValueError("Target audience cannot be empty")

        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book_id = f"book_{self._next_id:06d}"
            self._next_id += 1

            metadata = BookMetadata(
                title=title,
                description=description,
                theme=theme,
                target_audience=target_audience,
                size=size,
                page_count=0,  # Updated when puzzles added
                cover_image_url=cover_image_url,
            )

            # AC-181 (CON-018): a new book stores the Book 1 print profile.
            book = Book(book_id=book_id, metadata=metadata, **BOOK1_PROFILE.stored_columns())
            self.books[book_id] = book
            # ADR-0034: every new book starts on the default plan.
            self._plans[book_id] = DEFAULT_PLAN

            return book_id
        else:
            # DB mode: insert Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                metadata = {
                    'size': size,
                    'cover_image_url': cover_image_url,
                    'pdf_url': None,
                    'kdp_asin': None,
                }

                book = DBBook(
                    title=title,
                    description=description,
                    theme=theme,
                    target_audience=target_audience,
                    puzzle_ids=[],
                    puzzle_titles={},
                    book_metadata=metadata,
                    status=BookStatus.DRAFT.value,
                    # ADR-0034: every new book starts on the default plan.
                    distribution_plan=plan_to_json(DEFAULT_PLAN),
                    # AC-181 (CON-018): a new book stores the Book 1 print
                    # profile, explicitly rather than through column defaults.
                    **BOOK1_PROFILE.stored_columns(),
                )
                db.add(book)
                db.flush()  # get the auto-generated UUID
                return str(book.id)

    def _row_to_book(self, book_row) -> Book:
        """Convert SQLAlchemy Book ORM row to Book dataclass.

        Args:
            book_row: SQLAlchemy Book ORM instance

        Returns:
            Book dataclass instance
        """
        # Parse metadata JSON (stored in book_metadata database column)
        metadata_dict = book_row.book_metadata or {}

        # Build BookMetadata object
        metadata = BookMetadata(
            title=book_row.title,
            description=book_row.description,
            theme=book_row.theme,
            target_audience=book_row.target_audience,
            size=metadata_dict.get('size', '8x10'),
            page_count=metadata_dict.get('page_count', max(1, len(book_row.puzzle_ids) // 2)),
            cover_image_url=metadata_dict.get('cover_image_url'),
            pdf_url=metadata_dict.get('pdf_url'),
            kdp_asin=metadata_dict.get('kdp_asin'),
        )

        puzzle_titles = book_row.puzzle_titles or {}

        return Book(
            book_id=str(book_row.id),
            metadata=metadata,
            puzzle_ids=book_row.puzzle_ids or [],
            puzzle_titles=puzzle_titles,
            status=book_row.status,
            created_at=book_row.created_at,
            updated_at=book_row.updated_at or book_row.created_at,
            trim_width_cm=book_row.trim_width_cm,
            trim_height_cm=book_row.trim_height_cm,
            gutter_margin_cm=book_row.gutter_margin_cm,
            outside_margin_cm=book_row.outside_margin_cm,
            outside_margin_bleed_cm=book_row.outside_margin_bleed_cm,
            # NULL is a row from before migration 012: no override was ever
            # given, which is the reading that keeps the floor closed.
            floor_overrides=list(book_row.floor_overrides or []),
        )

    def get_book(self, book_id: str) -> Optional[Book]:
        """Get a book by ID.

        Args:
            book_id: ID of book

        Returns:
            Book object, or None if not found
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            return self.books.get(book_id)
        else:
            # DB mode: query database
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if book_row:
                    return self._row_to_book(book_row)
                return None

    def get_plan(self, book_id: str) -> Optional[DistributionPlan]:
        """The book's stored distribution plan (FR-034), read back from storage.

        ``None`` for a book that has no plan — one created before migration 010
        and never set up since (no backfill, G-3) — and for an unknown book.

        Raises:
            InvalidPlan: DB mode only — a stored document
                :func:`plan_from_json` refuses (INV-005). A *damaged* plan is
                not the same fact as *no* plan, so this reports it rather than
                returning ``None``; the two callers that would show the owner
                a screen (``app._readable_plan`` and the readiness gate,
                :meth:`_refuse_unless_the_planned_book`) each collapse it to
                "no plan" themselves, with their own log line.
        """
        if self._session_factory is None:
            return self._plans.get(book_id)

        from nonogram.db.models import Book as DBBook

        with self._session_factory() as db:
            book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
            if book_row is None or book_row.distribution_plan is None:
                return None
            return plan_from_json(book_row.distribution_plan)

    def save_plan(self, book_id: str, plan: DistributionPlan) -> bool:
        """Store ``plan`` as the book's distribution plan (FR-034, FR-035).

        ``plan`` must be a :class:`DistributionPlan`: the aggregate has already
        refused a split that does not sum to 100 and any negative or fractional
        cell (INV-005), so nothing reaches storage that it would not accept.

        Writes the plan and nothing else of the book's content — never the
        selection, its order or its custom titles (G-2, FR-038).

        A plan edit on a book that has **left draft returns it to draft**
        (owner's decision, CARD-124; the same rule ADR-0035's "Membership
        change after draft" gives a membership edit, INV-012). The plan is what
        :meth:`set_book_status` measures the selection against, so changing it
        changes the verdict that let the book out — and a book whose verdict is
        no longer known must be judged again before a PDF or a KDP upload is
        built from it. A book already in draft is left where it is.

        Returns:
            True if stored, False if the book does not exist.

        Raises:
            InvalidPlan: ``plan`` is not a DistributionPlan.
        """
        if not isinstance(plan, DistributionPlan):
            raise InvalidPlan(f"a book's plan must be a DistributionPlan, got {type(plan).__name__}")

        if self._session_factory is None:
            book = self.books.get(book_id)
            if not book:
                return False
            self._plans[book_id] = plan
            book.status = BookStatus.DRAFT.value
            book.updated_at = datetime.utcnow()
            return True

        from nonogram.db.models import Book as DBBook

        with self._session_factory() as db:
            book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
            if not book_row:
                return False
            book_row.distribution_plan = plan_to_json(plan)
            book_row.status = BookStatus.DRAFT.value
            book_row.updated_at = datetime.utcnow()
            db.commit()
            return True

    def floor_overrides(self, book_id: str) -> List[str]:
        """The ids this book has stored an under-floor override for (TERM-025).

        Both storage modes answer from the same place the override was
        written, so "is there a stored override for this id" is one question
        with one answer (INV-006). An unknown book, and a DB row from before
        migration 012, both answer with the empty list: no override was ever
        given, which is the reading that keeps the floor closed.
        """
        book = self.get_book(book_id)
        return list(book.floor_overrides) if book else []

    def below_floor(self, book_id: str, puzzle_ids) -> List[FloorRefusal]:
        """Which of these puzzles this book cannot print at or above the floor.

        The measurement, with no override rule applied: every id whose cell on
        **this book's** trim and margins is below :data:`FLOOR_MM`, plus every
        id whose cell cannot be computed although the store holds a record for
        it. :meth:`floor_refusals` is this, minus the ids an override covers.

        The cell is ``book_cell_mm(book_page_spec(book), ...)`` and nothing
        else — the one computation FR-030's PDF uses (G-1, EC-021). The clue
        fields are converted exactly as the book PDF converts them, so the two
        measure the same puzzle.

        Four postures, each decided deliberately (CARD-121):

        * **A record whose cell computes** — the verdict, below vs at-or-above
          :data:`FLOOR_MM`. Exactly at the floor passes (AC-186 reads it as
          "at or above").
        * **A record whose clues cannot be read** — refused, with the reason
          (``cell_mm`` is ``None``). Fail closed: the store *has* this puzzle,
          so it is one the floor has jurisdiction over, and a cell nobody can
          compute is not a cell known to clear the floor.
        * **An id no record matches** — not refused. This is not fail-open: a
          phantom id is not a puzzle at all, it has no grid, no clues and
          nothing to print, and whether a book's list holds ids no row matches
          is referential integrity — ``puzzles.book_id``'s constraint
          (CARD-103) and ``book_membership``'s repair (CARD-100) — not the
          printed-cell floor. It is the same verdict
          :meth:`_selection_records` makes on such an id ("contributes to no
          cell"), and a book carrying one still cannot leave draft, because
          ADR-0035's gate measures the same selection.
        * **No puzzle store at all** — nothing can be resolved, so nothing is
          refused, and an error is logged. ``create_app`` wires a store on
          both branches, so this is a wiring error rather than a reachable
          state of the panel; the readiness gate refuses such a manager's
          books outright (:meth:`_selection_records`), so a book assembled by
          one can never leave draft however the floor answered here. The
          alternative — refusing every add — would have made
          ``BookManager(session_factory=None)`` unable to hold a book at all,
          which is the arrangement CARD-100 deliberately kept working ("says
          so rather than pretending").

        Raises:
            ValueError: the book's stored print specification cannot be read —
                :func:`book_page_spec`'s message, which names the column at
                fault. The whole add is refused, because *no* puzzle's cell can
                be computed for such a book; fail closed, and the owner's
                remedy is one save on Print setup. A manager with **no store**
                does not reach this: its posture (nothing refused, an error
                logged) is decided first, so an unreadable trim cannot turn it
                into a raise (review cycle 1, F-005).
        """
        book = self.get_book(book_id)
        return [] if book is None else self._below_floor_for(book, puzzle_ids)

    def _below_floor_for(self, book: Book, puzzle_ids, *, tiers=None) -> List[FloorRefusal]:
        """:meth:`below_floor` against a book already read (see it for the rules).

        ``tiers``, when given, is a dict this fills with the stored tier of
        every id it resolves — ``None`` for one it cannot. It is not part of
        the floor's job; it is here because this loop is the one place the add
        already holds each submitted record in its hand, and EC-021's
        "one store read per distinct id" (F-004) is a promise about the whole
        submission, not about the floor alone. The add hands its dict in and
        :meth:`_tier_of` reads nothing twice.
        """
        puzzle_ids = [str(pid) for pid in puzzle_ids]
        if tiers is not None:
            # Everything asked about is answered, including the ids the loop
            # below skips: an id no row matches has no tier, and recording that
            # is what stops it being looked up a second time.
            tiers.update({puzzle_id: None for puzzle_id in puzzle_ids})
        if not puzzle_ids:
            return []

        # First of all: a manager with no store resolves nothing, so it has
        # nothing to refuse and says so (the posture above). This precedes the
        # sheet deliberately (review cycle 1, F-005) — building it first made
        # such a manager *raise* on a book whose trim is also unreadable, which
        # is the one posture the docstring promises it will not take.
        if self.puzzle_store is None:
            logger.error(
                "No puzzle store: the printed cell of %d puzzle(s) cannot be measured, "
                "so the %s mm floor (INV-006) is not enforced on this add. Every "
                "manager create_app builds has a store; this is a wiring error.",
                len(puzzle_ids),
                f"{FLOOR_MM:g}",
            )
            return []

        # Before the store is consulted: a book whose sheet cannot be built has
        # no cell for any puzzle, and that is the whole add's refusal.
        spec = book_page_spec(book)

        refusals: List[FloorRefusal] = []
        for puzzle_id in puzzle_ids:
            try:
                record = self.puzzle_store.get_puzzle(puzzle_id)
            except (ValueError, TypeError) as error:
                logger.warning(
                    "Puzzle id %r that no row can match (%s); the floor has no "
                    "cell to measure for it.",
                    puzzle_id,
                    error,
                )
                continue
            if record is None:
                logger.warning(
                    "Puzzle id %r matches no stored puzzle; the floor has no cell "
                    "to measure for it.",
                    puzzle_id,
                )
                continue
            if tiers is not None:
                # Read, never re-graded (ADR-0033/R1, ADR-0031).
                tiers[puzzle_id] = tier_of_record(record.get("difficulty_tier"))
            try:
                cell_mm = book_cell_mm(
                    spec,
                    _clue_lines(record, "clues_rows"),
                    _clue_lines(record, "clues_cols"),
                )
            except ValueError as error:
                logger.warning(
                    "Puzzle %s is stored but its cell cannot be measured (%s); "
                    "refused rather than admitted unmeasured.",
                    puzzle_id,
                    error,
                )
                refusals.append(FloorRefusal(puzzle_id, None, str(error)))
                continue
            if cell_mm < FLOOR_MM:
                refusals.append(FloorRefusal(puzzle_id, cell_mm))
        return refusals

    def floor_refusals(
        self, book_id: str, puzzle_ids, overrides=()
    ) -> List[FloorRefusal]:
        """Why these puzzles may not join this book — the floor's verdict (INV-006).

        :meth:`below_floor`, minus every id an override covers: one given in
        this submission (``overrides``) or one already stored with the book
        (:meth:`floor_overrides`), because INV-006 asks for a *stored* override
        and one stored earlier is still stored.

        The measurement :meth:`add_puzzles_reporting_refusals` makes to decide
        what it admits, asked **without** adding anything: this is the read-only
        door for a screen that shows the verdict before a submission (CARD-123's
        tile and finalise count). A route that is *about* to add asks the add
        itself, which hands back the refusals it enforced, so the wording and
        the enforcement are one measurement and cannot disagree (EC-021, review
        cycle 1, F-004). The store remains the gate either way: a route that
        skips this still cannot get a below-floor puzzle in.

        Raises:
            ValueError: as :meth:`below_floor` — the book's stored print
                specification cannot be read.
        """
        allowed = set(self.floor_overrides(book_id)) | {str(pid) for pid in overrides}
        return [r for r in self.below_floor(book_id, puzzle_ids) if r.puzzle_id not in allowed]

    def add_puzzles_to_book(
        self, book_id: str, puzzle_ids: List[str], overrides=()
    ) -> bool:
        """Add puzzles to a book, holding the 4.8 mm floor (FR-031, INV-006).

        :meth:`add_puzzles_reporting_refusals` — the whole rule is there — read
        as the yes/no every caller but the two add routes wants.

        Args:
            book_id: ID of book
            puzzle_ids: IDs of puzzles to add
            overrides: The ids the owner explicitly admitted below the floor in
                *this* submission (TERM-025).

        Returns:
            True if the book was found and the add was processed — which
            includes the case where every puzzle was refused by the floor.
            False if the book does not exist. A caller that needs to *name* the
            refusals asks :meth:`add_puzzles_reporting_refusals` instead; this
            contract is unchanged.

        Raises:
            ValueError: as :meth:`add_puzzles_reporting_refusals`.
        """
        return self.add_puzzles_reporting_refusals(book_id, puzzle_ids, overrides) is not None

    def add_puzzles_reporting_refusals(
        self, book_id: str, puzzle_ids: List[str], overrides=()
    ) -> Optional[AddOutcome]:
        """Add puzzles to a book, holding the 4.8 mm floor (FR-031, INV-006).

        The floor is enforced here rather than at either route, because this is
        where membership is written and EC-021 covers "any future route ending
        in the book store" as well as today's two. A puzzle whose cell on this
        book is below :data:`FLOOR_MM` is:

        * **refused**, when no override covers its id — and the other puzzles
          in the same submission are still added. Refusal is per puzzle, not
          per batch (FR-031): a submission of fifty tiles with one small
          picture among them is a corrected selection, not a lost one, and
          whole-batch refusal would make the owner find the offender by
          bisection. The refusals come back in the :class:`AddOutcome`, so the
          caller names them from the measurement that was enforced rather than
          repeating it (review cycle 1, F-004);
        * **admitted**, when one does, and the override is then **stored with
          the book** for that id, so the membership and the reason it was
          allowed live together and survive the request that granted it
          (AC-184).

        An override is stored only for a puzzle that is actually below the
        floor. Granting one for a puzzle that clears it stores nothing: an
        override that no rule needs is exactly the orphan record item 4 of the
        card removes on the other side.

        A **repeated id inside one submission is one decision**, not two
        (review cycle 1, F-006): ``[p, p]`` below the floor is refused once and
        named once, and ``[p, p]`` above it joins once — which is what the book
        already did with membership, and now what the refusal does too.

        Consistency of the verdict with the write
        -----------------------------------------
        The published refusal, the stored overrides and every cell measured
        against the floor are read off **one** snapshot of the book taken here,
        and DB mode then writes in a second session (the per-puzzle store reads
        in between open their own, and this module does not nest sessions —
        :meth:`set_book_status` records why). So the writing session re-reads
        the live row and commits only if :func:`_verdict_state` still matches
        the snapshot the verdict was made on; a publish, a Print-setup save or
        a concurrent remove landing in between refuses the add with
        :data:`CONCURRENT_CHANGE_REFUSAL` instead of committing a decision made
        on state that has gone (review cycle 1, F-001). Membership and its
        override remain two columns of one row assigned and committed together,
        so INV-006's pair still cannot land half-written. The in-memory branch
        has one live object throughout and needs no such check.

        Args:
            book_id: ID of book
            puzzle_ids: IDs of puzzles to add
            overrides: The ids the owner explicitly admitted below the floor in
                *this* submission (TERM-025). The selection step passes the
                ticked ones; the paste-IDs form passes none, so a below-floor
                id pasted there is named and refused.

        Returns:
            The :class:`AddOutcome` — the submission's distinct ids split into
            what the floor admitted and what it refused — when the book was
            found and the add was processed, which includes the case where
            every puzzle was refused. ``None`` if the book does not exist.

        Raises:
            ValueError: ``puzzle_ids`` is empty, the book is already published
                (unchanged here — turning that into a confirmation is
                CARD-131), the book's stored print specification cannot be read
                (:meth:`below_floor`), or the book changed under the add
                between the measurement and the write
                (:data:`CONCURRENT_CHANGE_REFUSAL`). Nothing is written in any
                of these cases.
        """
        if not puzzle_ids:
            raise ValueError("Must provide at least one puzzle")

        # One submission, one decision per id (F-006). Order-preserving, and
        # keyed on the id's string form because that is the form the floor,
        # the store and the book's own list all speak.
        submitted = list({str(pid): pid for pid in puzzle_ids}.values())

        # Read once, before the storage branch: the published refusal and the
        # floor both need the book, and both must answer the same in either
        # mode. The published refusal stays first, exactly as it was (G-4).
        book = self.get_book(book_id)
        if not book:
            return None
        if book.status == BookStatus.PUBLISHED.value:
            raise ValueError("Cannot add puzzles to published book")

        # The truth this add's verdict rests on, as it stood when it was made.
        measured_on = _verdict_state(book)

        allowed = set(book.floor_overrides) | {str(pid) for pid in overrides}
        # The floor's pass over the submission is also the add's tier reading
        # (FR-041 below): one store read per distinct submitted id, still
        # (EC-021, F-004).
        submitted_tiers: Dict[str, Optional[Tier]] = {}
        below_floor = self._below_floor_for(book, submitted, tiers=submitted_tiers)
        refusals = [r for r in below_floor if r.puzzle_id not in allowed]
        refused = {r.puzzle_id for r in refusals}
        # Stored for the ids an override actually had to cover, and no others.
        newly_overridden = [r.puzzle_id for r in below_floor if r.puzzle_id in allowed]
        puzzle_ids = [pid for pid in submitted if str(pid) not in refused]
        outcome = AddOutcome([str(pid) for pid in puzzle_ids], refusals)
        if refused:
            logger.info(
                "Book %s: %d puzzle(s) refused by the %s mm floor with no override "
                "(INV-006): %s",
                book_id,
                len(refused),
                f"{FLOOR_MM:g}",
                ", ".join(sorted(refused)),
            )
        # A submission the floor refused entirely changes no membership, so it
        # is not a membership change. CARD-131 (INV-012): the return-to-draft
        # write belongs *after* this line, not before it — a fully refused
        # submission must not demote a book whose selection did not move.
        if not puzzle_ids:
            return outcome

        # FR-041/INV-009: a new puzzle joins the end of **its own level**, not
        # the end of the book (CARD-126). The lookup runs here, before either
        # storage branch, for the reason the paragraph above gives: the store
        # opens its own sessions and this module does not nest them. The
        # submission's tiers are already in hand from the floor's pass; only
        # the book's existing members are read here, once each.
        tier_of = self._tier_of(book.puzzle_ids, known=submitted_tiers)

        if self._session_factory is None:
            # Legacy mode: in-memory dict
            # Add unique puzzle IDs (avoid duplicates)
            existing = set(book.puzzle_ids)
            new_puzzles = [pid for pid in puzzle_ids if pid not in existing]
            book.puzzle_ids = place_in_level(book.puzzle_ids, new_puzzles, tier_of)
            if newly_overridden:
                book.floor_overrides = _merged_overrides(book.floor_overrides, newly_overridden)

            # Update page count (rough estimate: ~2 puzzles per page)
            book.metadata.page_count = max(1, len(book.puzzle_ids) // 2)
            book.updated_at = datetime.utcnow()

            self._mirror_onto_puzzles(new_puzzles, book_id)
            return outcome
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return None

                # The verdict above was decided on a snapshot; this session
                # holds the live row. Nothing is written unless the state that
                # verdict rests on is still the state here (F-001) — the
                # published refusal included, which is why no separate status
                # re-check is needed beside this one.
                if _verdict_state(book_row) != measured_on:
                    logger.warning(
                        "Book %s changed between the floor measurement and the write "
                        "(status, print columns or stored overrides); nothing was "
                        "added.",
                        book_id,
                    )
                    raise ValueError(CONCURRENT_CHANGE_REFUSAL)

                # Add unique puzzle IDs (avoid duplicates)
                existing_puzzles = book_row.puzzle_ids or []
                existing = set(existing_puzzles)
                new_puzzles = [pid for pid in puzzle_ids if pid not in existing]
                # A NEW list, for CARD-101's reason, and grouped by level for
                # FR-041's (INV-009): each new id at the end of its own level.
                book_row.puzzle_ids = place_in_level(existing_puzzles, new_puzzles, tier_of)
                if newly_overridden:
                    # A NEW list, assigned whole (CARD-100/CARD-101's lesson).
                    book_row.floor_overrides = _merged_overrides(
                        book_row.floor_overrides, newly_overridden
                    )

                # Update page count in metadata
                if book_row.book_metadata is None:
                    book_row.book_metadata = {}
                book_row.book_metadata['page_count'] = max(1, len(book_row.puzzle_ids) // 2)
                book_row.updated_at = datetime.utcnow()

                db.commit()

            self._mirror_onto_puzzles(new_puzzles, book_id)
            return outcome

    def remove_puzzle_from_book(self, book_id: str, puzzle_id: str) -> bool:
        """Remove a puzzle from a book, and with it its under-floor override.

        CARD-121 item 4: an override is a fact about a **member** — "this
        puzzle may be in this book although it prints below the floor". A
        puzzle that is no longer a member leaves none behind, so re-adding it
        asks the owner again rather than letting a decision they made months
        ago pass silently on a book whose trim may have changed since.

        Args:
            book_id: ID of book
            puzzle_id: ID of puzzle to remove

        Returns:
            True if removed, False if book/puzzle not found
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book or puzzle_id not in book.puzzle_ids:
                return False

            book.puzzle_ids.remove(puzzle_id)
            if puzzle_id in book.floor_overrides:
                book.floor_overrides = [p for p in book.floor_overrides if p != puzzle_id]
            book.metadata.page_count = max(1, len(book.puzzle_ids) // 2)
            book.updated_at = datetime.utcnow()

            self._mirror_onto_puzzles([puzzle_id], None)
            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                puzzle_ids = book_row.puzzle_ids or []
                if puzzle_id not in puzzle_ids:
                    return False

                # A NEW list, not the same one mutated and assigned back
                # (CARD-100). `puzzle_ids` is a plain JSON column: SQLAlchemy
                # compares identity to decide what is dirty, so removing from
                # the list in place and reassigning it changed nothing at all —
                # in DB mode, which is production, taking a puzzle out of a book
                # silently did not happen. `add_puzzles_to_book` was never
                # affected because it builds a new list by concatenation.
                book_row.puzzle_ids = [p for p in puzzle_ids if p != puzzle_id]

                # Update page count in metadata
                book_row.book_metadata = {
                    **(book_row.book_metadata or {}),
                    'page_count': max(1, len(book_row.puzzle_ids) // 2),
                }
                book_row.updated_at = datetime.utcnow()

                # Also remove custom title if it exists — a new dict, same reason
                if book_row.puzzle_titles and puzzle_id in book_row.puzzle_titles:
                    book_row.puzzle_titles = {
                        k: v for k, v in book_row.puzzle_titles.items() if k != puzzle_id
                    }

                # ... and its under-floor override, for the same reason and in
                # the same way — a new list (CARD-121 item 4).
                if book_row.floor_overrides and puzzle_id in book_row.floor_overrides:
                    book_row.floor_overrides = [
                        p for p in book_row.floor_overrides if p != puzzle_id
                    ]

                db.commit()

            self._mirror_onto_puzzles([puzzle_id], None)
            return True

    def reorder_puzzles(self, book_id: str, puzzle_ids: List[str], tier_of=None) -> bool:
        """Reorder puzzles in a book, inside INV-009's grouping.

        The stored order is grouped easy, then medium, then hard (FR-041,
        TERM-032): a submitted order that is not is **refused and nothing is
        written**, which is what makes this the aggregate's own invariant
        rather than a rule the arrange page is trusted to obey. The order the
        page submits is already grouped, and so is the one a move computes
        (:meth:`_move_within_level`), so no honest caller is turned away.

        Args:
            book_id: ID of book
            puzzle_ids: Ordered list of puzzle IDs
            tier_of: the id -> tier lookup, when the caller has already made
                one over these ids (:meth:`_move_within_level` has). Omitted,
                it is made here. Passing one never changes the verdict — it
                only saves reading the same rows twice.

        Returns:
            True if reordered, False if book not found — and that answer comes
            first, so a call naming no book still returns False however the
            order it carries is grouped.

        Raises:
            ValueError: If puzzle IDs don't match book's puzzles. Reported
                *before* the grouping, so a submission that is wrong in both
                ways is named by the complaint the caller can act on.
            LevelBoundary: the order is this book's own membership but is not
                grouped by level (INV-009). A :class:`ValueError`, so a caller
                that only knows about those is unaffected.
        """
        # The three verdicts in this order, and not another (review cycle 1,
        # F-004): "no such book" and "those are not this book's puzzles" are
        # facts about the *call*, and answering them first is what keeps the
        # contract above true and the message the more actionable one. INV-009
        # is asked last, of an order that was otherwise about to be stored.
        book = self.get_book(book_id)
        if not book:
            return False

        if set(puzzle_ids) != set(book.puzzle_ids):
            raise ValueError("Puzzle IDs must match book's current puzzles")

        # Still outside either storage branch: the tier lookup reads the
        # puzzle store, which opens sessions of its own, and this module does
        # not nest sessions (:meth:`add_puzzles_reporting_refusals` records
        # why).
        if not is_level_order(puzzle_ids, tier_of or self._tier_of(puzzle_ids)):
            raise LevelBoundary(UNGROUPED_ORDER_REFUSAL)

        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            if set(puzzle_ids) != set(book.puzzle_ids):
                raise ValueError("Puzzle IDs must match book's current puzzles")

            book.puzzle_ids = puzzle_ids
            book.updated_at = datetime.utcnow()

            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                if set(puzzle_ids) != set(book_row.puzzle_ids or []):
                    raise ValueError("Puzzle IDs must match book's current puzzles")

                book_row.puzzle_ids = puzzle_ids
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def move_puzzle_up(self, book_id: str, puzzle_id: str) -> bool:
        """Move a puzzle up one position **inside its own level** (FR-041, INV-009).

        Args:
            book_id: ID of book
            puzzle_id: ID of puzzle to move

        Returns:
            True if moved, False if already at the top of the book

        Raises:
            LevelBoundary: the puzzle above belongs to another level, so the
                move would break the easy/medium/hard grouping. Nothing is
                written (AC-258).
            ValueError: If book not found or puzzle not in book
        """
        return self._move_within_level(book_id, puzzle_id, -1)

    def move_puzzle_down(self, book_id: str, puzzle_id: str) -> bool:
        """Move a puzzle down one position **inside its own level** (FR-041, INV-009).

        Args:
            book_id: ID of book
            puzzle_id: ID of puzzle to move

        Returns:
            True if moved, False if already at the bottom of the book

        Raises:
            LevelBoundary: the puzzle below belongs to another level, so the
                move would break the easy/medium/hard grouping. Nothing is
                written (AC-258).
            ValueError: If book not found or puzzle not in book
        """
        return self._move_within_level(book_id, puzzle_id, +1)

    def _move_within_level(self, book_id: str, puzzle_id: str, offset: int) -> bool:
        """One step of CMD-022 -> EVT-023: the swap both move buttons make.

        The two directions were the same forty lines twice over, once per
        storage mode, and the rule they now share is not a swap of adjacent
        *stored* positions any more but a swap of adjacent positions in the
        **level order** (:func:`~nonogram.admin.book_plan.moved_within_level`).
        On a book that is already grouped those are the same two positions; on
        a legacy mixed one they are not, and the move is the one place where
        the grouped order is written back (the card's item 2).

        The new order goes through :meth:`reorder_puzzles`, so the membership
        check and the storage branch stay in one place and the write is a
        fresh list in both modes (CARD-101). The tier lookup runs here, outside
        any writing session.
        """
        book = self.get_book(book_id)
        if not book:
            raise ValueError("Book not found")
        if puzzle_id not in book.puzzle_ids:
            raise ValueError("Puzzle not in book")

        tier_of = self._tier_of(book.puzzle_ids)
        moved = moved_within_level(book.puzzle_ids, puzzle_id, offset, tier_of)
        if moved is None:
            return False  # Already at the end of the book
        return self.reorder_puzzles(book_id, moved, tier_of)

    def _tier_of(self, puzzle_ids, known=None):
        """A total id -> stored tier lookup over ``puzzle_ids``, read once each.

        The seam between the level order (pure, in ``book_plan``) and storage.
        The tier is **read** from what the row holds, through
        :func:`~nonogram.difficulty.tier_of_record`, and never re-derived from
        a grid or a size (ADR-0033/R1, ADR-0031): book assembly grades nothing.

        Total on purpose, and quiet on purpose. A manager with no puzzle store,
        an id no row matches, an id that is not even a UUID — each answers
        ``None``, which ranks after every graded level rather than raising.
        The readiness gate's :meth:`_selection_records` refuses in that
        situation because a plan verdict on a selection it cannot see would be
        a false "ready"; an *order* has no such failure mode — it stays a
        permutation of the membership either way — and refusing here would
        break every book held in memory without a store, which is what the
        panel's own tests and its legacy mode are.

        Args:
            puzzle_ids: the ids to resolve.
            known: tiers a caller has already read, keyed the same way. Ids in
                it are not read again, and it is carried into the result, so a
                lookup built over the book's members still answers for the
                submission the caller measured alongside them.

        Returns:
            A callable taking a puzzle id (in any form that ``str()`` renders
            the same way the book's list does) and returning a
            :class:`~nonogram.difficulty.Tier` or ``None``.
        """
        tiers: Dict[str, Optional[Tier]] = dict(known or {})
        for puzzle_id in puzzle_ids:
            key = str(puzzle_id)
            if key not in tiers:
                tiers[key] = self._stored_tier(key)
        return lambda puzzle_id: tiers.get(str(puzzle_id))

    def _stored_tier(self, puzzle_id: str) -> Optional[Tier]:
        """One row's stored tier, or ``None`` when there is nothing to read."""
        if self.puzzle_store is None:
            return None
        try:
            record = self.puzzle_store.get_puzzle(puzzle_id)
        except (ValueError, TypeError) as error:
            logger.debug(
                "Book order: puzzle id %r resolves to no row (%s); it has no level "
                "and sorts after the graded ones.",
                puzzle_id,
                error,
            )
            return None
        if not record:
            return None
        return tier_of_record(record.get("difficulty_tier"))

    def puzzle_levels(self, book_id: str) -> List[tuple]:
        """The book's order cut into its levels — the arrange page's view.

        ``[(Tier | None, [puzzle_id, ...]), ...]`` in book order, one entry per
        non-empty level (see
        :func:`~nonogram.admin.book_plan.book_levels`). The route renders this
        and nothing else, so the page cannot group the book differently from
        the way it is stored, moved and printed — there is one grouping
        (FR-041).

        A legacy mixed arrangement reads grouped here **without** being
        rewritten; the first move the owner makes on it writes the grouped
        order back.

        Returns:
            The levels, or ``[]`` for an unknown book.
        """
        book = self.get_book(book_id)
        if not book:
            return []
        return book_levels(book.puzzle_ids, self._tier_of(book.puzzle_ids))

    def set_puzzle_title(self, book_id: str, puzzle_id: str, title: str) -> bool:
        """Set custom title for a puzzle in the book.

        Args:
            book_id: ID of book
            puzzle_id: ID of puzzle
            title: Custom title for this puzzle in the book

        Returns:
            True if updated, False if not found

        Raises:
            ValueError: If puzzle not in book
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            if puzzle_id not in book.puzzle_ids:
                raise ValueError("Puzzle not in book")

            if title.strip():
                book.puzzle_titles[puzzle_id] = title.strip()
            elif puzzle_id in book.puzzle_titles:
                del book.puzzle_titles[puzzle_id]  # Remove custom title

            book.updated_at = datetime.utcnow()
            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                if puzzle_id not in (book_row.puzzle_ids or []):
                    raise ValueError("Puzzle not in book")

                puzzle_titles = book_row.puzzle_titles or {}
                if title.strip():
                    puzzle_titles[puzzle_id] = title.strip()
                elif puzzle_id in puzzle_titles:
                    del puzzle_titles[puzzle_id]

                book_row.puzzle_titles = puzzle_titles
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def get_puzzle_title(self, book_id: str, puzzle_id: str) -> Optional[str]:
        """Get custom title for a puzzle in the book.

        Args:
            book_id: ID of book
            puzzle_id: ID of puzzle

        Returns:
            Custom title if set, None otherwise
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return None

            return book.puzzle_titles.get(puzzle_id)
        else:
            # DB mode: query database
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return None

                puzzle_titles = book_row.puzzle_titles or {}
                return puzzle_titles.get(puzzle_id)

    def _selection_records(self, puzzle_ids) -> List[Dict[str, Any]]:
        """The stored record of each puzzle in a selection, for the gate.

        A puzzle id no row matches contributes to no cell — the same verdict
        :func:`~nonogram.admin.book_plan.selection_cells` makes on a record
        with no recognisable tier or a side outside the supported range.

        A manager built without a puzzle store cannot see the selection at
        all. A book that *holds* ids is then unreadable rather than empty, and
        the gate must not conclude anything about it: this raises, so the
        transition is refused whatever the plan says. Reading it as an empty
        selection — what this did until review cycle 1 — was not fail-closed,
        because an empty selection matches any plan whose every cell is within
        the tolerance of zero (F-004). No selection to read at all is a
        different fact: a book with no ids is genuinely empty, is refused a
        step earlier by :meth:`set_book_status`'s "Must have puzzles" rule,
        and needs no store to be judged. Every manager ``create_app`` builds
        has a store (app.py wires ``puzzle_review`` on both branches), so this
        is a wiring error, not a reachable state of the panel.

        Raises:
            ValueError: the book holds puzzle ids and there is no store to
                resolve them through.
        """
        puzzle_ids = list(puzzle_ids)
        if self.puzzle_store is None:
            if not puzzle_ids:
                return []
            logger.error(
                "No puzzle store: the selection of %d puzzle(s) cannot be read, so "
                "the plan check (ADR-0035) refuses the transition — it has nothing "
                "to judge, and an unread selection is not an empty one.",
                len(puzzle_ids),
            )
            raise ValueError(UNREADABLE_SELECTION_REFUSAL)

        records: List[Dict[str, Any]] = []
        for puzzle_id in puzzle_ids:
            try:
                record = self.puzzle_store.get_puzzle(str(puzzle_id))
            except (ValueError, TypeError) as error:
                logger.warning(
                    "Book holds puzzle id %r that no row can match (%s); it counts "
                    "towards no plan cell.",
                    puzzle_id,
                    error,
                )
                continue
            if record is not None:
                records.append(record)
        return records

    def _refuse_unless_the_planned_book(
        self, book_id: str, current_status: str, new_status: str, puzzle_ids
    ) -> None:
        """ADR-0035/R1: an exit from draft that does not match the plan is refused.

        The gate runs **at the exit from draft only** — every target status,
        including a direct ``draft -> ready_for_kdp`` or ``draft -> published``
        jump, which is the status-jump bypass ADR-0035 (a) closes. ``draft ->
        draft`` is not an exit, and a move between two non-draft statuses is
        past the gate already.

        A stored document :func:`plan_from_json` refuses to decode is read as
        **no plan** rather than allowed to escape as ``InvalidPlan`` (review
        cycle 2, F-001): a damaged plan is functionally a plan-less book, and
        the owner needs ADR-0035 (c)'s remedy — store one on Print setup —
        not a decode message. ``app._readable_plan`` reads it the same way,
        which is what lets Print setup repair the document. Only DB mode can
        hold such a document; the in-memory branch stores plan objects the
        aggregate has already accepted.

        Raises:
            ValueError: no stored plan (a damaged one included), a cell out of
                tolerance, or a selection that cannot be read at all
                (:meth:`_selection_records`). The message is the refusal the
                owner is shown. No :class:`InvalidPlan` leaves here.
        """
        if current_status != BookStatus.DRAFT.value or new_status == BookStatus.DRAFT.value:
            return
        try:
            plan = self.get_plan(book_id)
        except InvalidPlan as error:
            logger.error(
                "Stored distribution plan of book %s is unreadable (%s); the gate "
                "(ADR-0035) treats it as no plan, so the refusal carries the "
                "Print-setup remedy.",
                book_id,
                error,
            )
            plan = None
        refusal = ready_refusal(plan, self._selection_records(puzzle_ids))
        if refusal is not None:
            raise ValueError(refusal)

    def set_book_status(self, book_id: str, status: str) -> bool:
        """Update book status.

        Every transition **out of draft** — to ``ready_for_pdf`` or to any
        later status — is gated on the book's stored plan (ADR-0035/R1,
        FR-037, INV-007): the book must have a plan — a stored document that
        cannot be decoded counts as none — and every longest-side x
        tier cell of its selection must be within
        :data:`READY_TOLERANCE_POINTS` percentage points of that cell's share
        of the planned total. A refusal leaves the status unchanged and names
        every offending cell (see :func:`ready_refusal`).

        Membership outside draft
        ------------------------
        The gate runs at the exit from draft, not continuously. Adding or
        removing a puzzle on a book that has **left** draft returns the book to
        draft (INV-012, ADR-0035's "Membership change after draft"), so it
        passes this gate again before it can leave — a KDP upload is never
        built from a book that no longer matches its plan. Editing the plan
        does the same (:meth:`save_plan`). CARD-131 implements the return to
        draft on the membership paths; there is no bypass either way, because a
        book back in draft leaves it only through this gate, like any other
        draft book.

        What the guarantee is worth under concurrency
        ---------------------------------------------
        Sequentially. In DB mode the check and the write are **not atomic**:
        the row is read (and the rules applied) in one session and written in
        another, so between them another request could change the status or
        the selection and this write would still land. The single-session
        shape this replaced was no better — SQLAlchemy's pysqlite dialect runs
        the SELECT outside any transaction and only opens one at the first
        write, and a Postgres READ COMMITTED session behaves the same way — so
        the exposure is the whole DB layer's, not this method's. It is
        accepted here because the panel is a single-user loopback tool
        (CON-015): one owner, one browser, no concurrent writers. Making the
        verdict atomic (a compare-and-swap on status + selection, or a row
        lock) is a change to the storage layer as a whole and belongs in its
        own card.

        Args:
            book_id: ID of book
            status: New status (draft, ready_for_pdf, pdf_generated, ready_for_kdp, published)

        Returns:
            True if updated, False if not found

        Raises:
            ValueError: If invalid status, or the transition is refused. Every
                refusal this method makes is a ``ValueError`` carrying the text
                the owner is shown: a damaged stored plan is turned into the
                plan-less refusal rather than surfacing as ``InvalidPlan``
                (:meth:`_refuse_unless_the_planned_book`), so a caller needs no
                second except clause to keep the refusal on the screen.
        """
        valid_statuses = {s.value for s in BookStatus}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            # Status progression rules
            current_status = book.status
            if current_status == BookStatus.PUBLISHED.value:
                raise ValueError("Cannot change status of published book")

            if len(book.puzzle_ids) == 0 and status != BookStatus.DRAFT.value:
                raise ValueError("Must have puzzles before advancing status")

            self._refuse_unless_the_planned_book(
                book_id, current_status, status, list(book.puzzle_ids)
            )

            book.status = status
            book.updated_at = datetime.utcnow()

            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                # Status progression rules
                if book_row.status == BookStatus.PUBLISHED.value:
                    raise ValueError("Cannot change status of published book")

                if len(book_row.puzzle_ids or []) == 0 and status != BookStatus.DRAFT.value:
                    raise ValueError("Must have puzzles before advancing status")

                current_status = book_row.status
                selection = list(book_row.puzzle_ids or [])

            # Judged with no session of this method's open, exactly as
            # `_mirror_onto_puzzles` is called outside one: the plan and the
            # selection's records are each read through their own.
            self._refuse_unless_the_planned_book(book_id, current_status, status, selection)

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                book_row.status = status
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def delete_book(self, book_id: str) -> bool:
        """Delete a book (only draft books).

        Args:
            book_id: ID of book to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If book is not in draft status
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            if book.status != BookStatus.DRAFT.value:
                raise ValueError(f"Cannot delete {book.status} book. Only draft books can be deleted.")

            # CARD-108: let go of the puzzles before the book that held them
            # disappears. In DB mode the foreign key does this on its own
            # (`ON DELETE SET NULL`, CARD-103); in memory mode nothing did, so
            # a deleted book left its puzzles naming it for ever — and since
            # CARD-100 every in-book guard reads that column, they could no
            # longer be rejected, restored, approved or deleted by anything.
            # Done explicitly in both branches so the two modes cannot disagree
            # about what deleting a book means.
            self._mirror_onto_puzzles(list(book.puzzle_ids or []), None)
            del self.books[book_id]
            self._plans.pop(book_id, None)
            return True
        else:
            # DB mode: delete Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                if book_row.status != BookStatus.DRAFT.value:
                    raise ValueError(f"Cannot delete {book_row.status} book. Only draft books can be deleted.")

                held = list(book_row.puzzle_ids or [])
                db.delete(book_row)
                db.commit()

            # CARD-108: belt to the foreign key's braces. `ON DELETE SET NULL`
            # has already cleared these; saying so here keeps the two storage
            # modes doing the same thing for the same stated reason, rather
            # than one relying on a constraint the other does not have.
            self._mirror_onto_puzzles(held, None)
            return True

    def set_cover_image(self, book_id: str, cover_url: str) -> bool:
        """Set cover image URL.

        Args:
            book_id: ID of book
            cover_url: URL to cover image

        Returns:
            True if updated, False if not found
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            book.metadata.cover_image_url = cover_url
            book.updated_at = datetime.utcnow()

            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                if book_row.metadata is None:
                    book_row.book_metadata = {}
                book_row.metadata['cover_image_url'] = cover_url
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def set_pdf_url(self, book_id: str, pdf_url: str) -> bool:
        """Set generated PDF URL.

        Args:
            book_id: ID of book
            pdf_url: URL to generated PDF

        Returns:
            True if updated, False if not found
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            book.metadata.pdf_url = pdf_url
            book.updated_at = datetime.utcnow()

            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                if book_row.metadata is None:
                    book_row.book_metadata = {}
                book_row.metadata['pdf_url'] = pdf_url
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def set_kdp_asin(self, book_id: str, asin: str) -> bool:
        """Set KDP ASIN (Amazon product ID).

        Args:
            book_id: ID of book
            asin: Amazon ASIN

        Returns:
            True if updated, False if not found
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            book.metadata.kdp_asin = asin
            book.updated_at = datetime.utcnow()

            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                if book_row.metadata is None:
                    book_row.book_metadata = {}
                book_row.metadata['kdp_asin'] = asin
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def get_books_by_status(self, status: str) -> List[Book]:
        """Get all books with a given status.

        Args:
            status: Status to filter by

        Returns:
            List of books
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            return [b for b in self.books.values() if b.status == status]
        else:
            # DB mode: query database
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                rows = db.query(DBBook).filter(DBBook.status == status).order_by(DBBook.created_at.desc()).all()
                return [self._row_to_book(row) for row in rows]

    def get_all_books(self) -> List[Book]:
        """Get all books sorted by creation date (newest first).

        Returns:
            List of all books
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            return sorted(self.books.values(), key=lambda b: b.created_at, reverse=True)
        else:
            # DB mode: query database
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                rows = db.query(DBBook).order_by(DBBook.created_at.desc()).all()
                return [self._row_to_book(row) for row in rows]

    def _mirror_onto_puzzles(self, puzzle_ids, book_id) -> None:
        """Write this membership change onto the puzzle rows too (CARD-100).

        ``Book.puzzle_ids`` and ``Puzzle.book_id`` are two halves of one fact.
        Until this card only the first half was ever written, so every guard in
        the panel — which reads the second — waved through puzzles a book was
        built on, and "Delete rejected" removed them outright.

        A manager with no store keeps its own half correctly and says so, which
        is the honest failure: the alternative is a book whose puzzles are
        unprotected and nothing anywhere saying why. The backfill repairs a
        history of exactly that.
        """
        if not puzzle_ids:
            return
        if self.puzzle_store is None:
            logger.warning(
                "No puzzle store: book membership for %d puzzle(s) was recorded "
                "on the book only, so the puzzles are not protected from bulk "
                "actions (CARD-100). Run the membership backfill.",
                len(list(puzzle_ids)),
            )
            return
        if book_id is None:
            self.puzzle_store.release_from_book(puzzle_ids)
        else:
            self.puzzle_store.assign_to_book(puzzle_ids, book_id)

    def book_listing(self, puzzle_id: str) -> Optional[str]:
        """The id of a book that lists this puzzle, or ``None`` (CARD-068).

        Asks the side that actually records membership. Every other in-book
        check in the panel reads ``Puzzle.book_id``, which nothing in
        production writes — a puzzle a book is built on carries ``None``
        there, so those checks wave through a puzzle they were meant to stop
        (CARD-100). Until that is repaired, a caller that would *destroy* a
        booked puzzle asks here instead.

        A scan, because ``Book.puzzle_ids`` is a JSON list that can be neither
        indexed nor joined. Affordable for one puzzle at a time — a Delete the
        owner clicked — and precisely why it is not the answer for the bulk
        paths, which is CARD-100's problem to solve properly.
        """
        for book in self.get_all_books():
            if puzzle_id in (book.puzzle_ids or []):
                return book.book_id
        return None


# --------------------------------------------------------------------------
# The stored shape of a distribution plan (CARD-120)
# --------------------------------------------------------------------------
#
#     {"count": 150,
#      "split": {"easy": 40, "medium": 40, "hard": 20},
#      "cells": [[e, m, h], ...4 rows, one per bucket in BUCKETS order],
#      "edited": [["<=15", "easy"], ...]}
#
# Buckets and tiers are stored by their labels/values, not by position in
# BUCKETS/TIERS, so reordering either tuple can never silently move an edited
# mark to a different cell. Decoding goes back through DistributionPlan, so a
# stored document the aggregate would not accept is refused on the way out too.


def plan_to_json(plan: DistributionPlan) -> dict:
    """The JSON document ``books.distribution_plan`` holds for ``plan``."""
    return {
        "count": plan.count,
        "split": {"easy": plan.split.easy, "medium": plan.split.medium, "hard": plan.split.hard},
        "cells": [list(row) for row in plan.cells],
        "edited": sorted([bucket.value, tier.value] for bucket, tier in plan.edited),
    }


def plan_from_json(document: Dict[str, Any]) -> DistributionPlan:
    """The :class:`DistributionPlan` a stored document describes.

    Raises:
        InvalidPlan: the document is not a plan INV-005 allows.
    """
    try:
        split = document["split"]
        return DistributionPlan(
            count=document["count"],
            split=Split(split["easy"], split["medium"], split["hard"]),
            cells=tuple(tuple(row) for row in document["cells"]),
            edited=frozenset(
                (LongestSideBucket(bucket), Tier(tier)) for bucket, tier in document.get("edited", [])
            ),
        )
    except InvalidPlan:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise InvalidPlan(f"stored distribution plan is malformed: {error}") from error


def revise_plan(
    current: Optional[DistributionPlan],
    count: int,
    split: Split,
    submitted_cells,
) -> DistributionPlan:
    """The plan a Print setup submission asks for (FR-034, POL-007).

    ``current`` is the stored plan (``None`` for a plan-less book, which the
    form shows as :data:`DEFAULT_PLAN`). ``submitted_cells`` is the 4 x 3
    matrix as the owner submitted it.

    Whether a cell is hand-edited is decided per cell against the plan the
    page showed (``shown``). The form cannot tell "left alone" from "retyped
    the same value", so only a *changed* value counts as an owner action:

    * submitted value **equal to the shown value** — the owner left it alone,
      so it keeps the mark it had: a stored hand edit stays edited (even when
      its value happens to equal a prefill), an unedited cell stays unedited;
    * submitted value **different from the shown value** — the owner typed
      into it: it becomes hand-edited, unless the new value is the shown
      plan's prefill for that cell, which is the owner deliberately putting
      it back (the edit mark is cleared).

    Hand-edited cells keep their values; every other cell is re-derived from
    ``count`` and ``split`` (POL-007 via :func:`with_split`), so a changed
    split re-derives an un-edited matrix. A value is never made edited or
    un-edited just by coinciding with a prefill: an edit survives any number
    of unchanged resubmissions and split changes (CARD-120 review F-001).

    Raises:
        InvalidPlan: ``count`` or a submitted cell is not one INV-005 allows.
    """
    shown = current if current is not None else DEFAULT_PLAN
    reference = prefill(shown.count, shown.split)
    typed = DistributionPlan(count=count, split=shown.split, cells=submitted_cells)

    def is_edited(bucket, tier) -> bool:
        value = typed.cell(bucket, tier)
        if value == shown.cell(bucket, tier):
            return (bucket, tier) in shown.edited
        return value != reference.cell(bucket, tier)

    edited = frozenset(
        (bucket, tier) for bucket in BUCKETS for tier in TIERS if is_edited(bucket, tier)
    )
    return with_split(
        DistributionPlan(count=count, split=shown.split, cells=typed.cells, edited=edited), split
    )


# Global book manager instance (legacy in-memory mode)
_book_manager = BookManager(session_factory=None)


def get_book_manager(session_factory=None, puzzle_store=None) -> BookManager:
    """Get the book manager.

    Args:
        session_factory: Optional DB session factory. If provided, uses DB mode.
                        If None, returns the singleton in-memory instance.

    Returns:
        BookManager instance (either singleton or new DB-backed instance)
    """
    if session_factory is None:
        # Return the singleton in-memory instance, wiring its store on first
        # use if the caller brought one (CARD-100).
        if puzzle_store is not None:
            _book_manager.puzzle_store = puzzle_store
        return _book_manager
    else:
        # Return a new DB-backed instance
        return BookManager(session_factory=session_factory, puzzle_store=puzzle_store)

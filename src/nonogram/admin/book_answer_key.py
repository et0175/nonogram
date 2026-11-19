"""The book's answer key: which answers share a page, and what each says (FR-042).

The rule (owner ruling 2026-11-07, built by CARD-202 and CARD-232)
------------------------------------------------------------------
**Every solution is a tile**, up to four to a page in a 2 x 2 grid, each tile
carrying its own clues, its header and its caption. :func:`plan_small_answer_pages`
walks the book's answers in puzzle-number order and cuts each level's run into
pages of four; the last page of a run holds the one to three left over in the
same 2 x 2 positions (CARD-232 AC-4). A page never holds two levels. Every size
the book supports qualifies (:data:`PACKED_MAX_WIDTH`, :data:`PACKED_MAX_HEIGHT`
are :data:`~nonogram.limits.MAX_SIZE` since 2026-11-09).

This walk is extent-only, so it cannot see clue depth. A page whose four tiles
cannot reach :data:`~nonogram.export.layout.MIN_CELL_MM` is degraded after it,
by ``book_pdf_generator._degrade_infeasible_packed_pages``: to two 2-up pages,
and a pair that still cannot fit to one answer per page. The rule is written
down once, with its constants and its size-by-trim tables generated from the
code, in ``docs/BOOK_PAGE_PACKING.md`` (held by
``tests/test_book_page_packing_doc.py``).

The split with COMP-007 (ADR-0036/R2, G-1)
------------------------------------------
This module is **pure**: value objects in, value objects out. It measures no
tile, fits no cell, places no rule and draws nothing — there is no ``PIL``
import here and no ``PageSpec``. It decides only *which answers land on which
page* and *what a caption says*; the geometry of the page is
:func:`~nonogram.export.layout.compute_packed_solved_layout`'s and the ink is
``book_answer_vector``'s. That is why the walk can be swept over thousands of
book orders without a page being rendered.

Retired, kept only for their own tests
--------------------------------------
:func:`pack_answer_pages`, :class:`AnswerPage`, :func:`page_capacity`,
:attr:`Answer.needs_four_up` and the constants :data:`SIX_UP` and
:data:`SIX_UP_LONGEST_SIDE` are the first packed key's walk (CARD-134), which
CARD-198 replaced and the owner's 2026-11-07 ruling withdrew. No production
code calls them (``src/`` names them only in this module and in history
notes); ``tests/test_book_answer_key.py`` and
``tests/property/test_book_answer_key.py`` still exercise them, so they are
marked here rather than deleted, and deleting them with those tests is a
change of its own. They state no rule the book follows. :data:`FOUR_UP` is not
retired: :data:`PACKED_FOUR_UP` is it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union

from nonogram.difficulty import Tier
from nonogram.limits import MAX_SIZE

__all__ = [
    "Answer",
    "AnswerPage",
    "CAPTION_SEPARATOR",
    "FOUR_UP",
    "PACKED_MAX_HEIGHT",
    "PACKED_MAX_WIDTH",
    "PackedAnswerPage",
    "SIX_UP",
    "SIX_UP_LONGEST_SIDE",
    "answer_caption",
    "answer_title",
    "level_heading",
    "pack_answer_pages",
    "page_capacity",
    "qualifies_for_packing",
    "plan_small_answer_pages",
]

# ---------------------------------------------------------------------------
# RETIRED: the first packed key (CARD-134), replaced by CARD-198 and withdrawn
# by the owner's ruling of 2026-11-07. Kept only for its own tests; no
# production caller. See the module docstring, "Retired, kept only for their
# own tests". Nothing from here to `pack_answer_pages` is a rule the book follows.
# ---------------------------------------------------------------------------

#: The longest side, in cells, an answer may have and still leave its page
#: six-up (INV-011, FR-042). Exactly 20 keeps the page six-up; 21 makes it
#: four-up (AC-266). This is the project's own threshold, not a grid-size
#: bound — :data:`nonogram.limits.MIN_SIZE`/``MAX_SIZE`` state what a grid may
#: be (10..30), and this states where the key changes tiling inside that range.
SIX_UP_LONGEST_SIDE = 20

#: A page of six answers, 2 columns x 3 rows (FR-042).
SIX_UP = 6

#: A page of four answers, 2 x 2 — what a page becomes once it holds an answer
#: longer than :data:`SIX_UP_LONGEST_SIDE`.
FOUR_UP = 4

#: What stands between a puzzle's number and its title in an answer caption:
#: an em dash (U+2014) with a space either side, as FR-042 writes it
#: ("Puzzle 7 — Snowflake").
#:
#: Deliberately **not** the middle dot the puzzle page's band uses
#: (``book_pdf_generator.BAND_SEPARATOR``, "Puzzle 12 · Easy"): the dot joins a
#: number to its tier inside one identity, while this rule joins that identity
#: to the picture's name — two different joins, and a reader flicking between a
#: puzzle page and the key should not have to read the mark to tell which is
#: which.
CAPTION_SEPARATOR = " — "


@dataclass(frozen=True, slots=True)
class Answer:
    """One puzzle's answer as the key's walk sees it (FR-042).

    Not the grid: the walk needs the puzzle's **number**, its extent and its
    level and nothing else, and an :class:`Answer` carrying a grid would invite
    this module to look at one. The grid reaches the page from the generator,
    by the number below.

    A value object, valid by construction: a number that is not a print
    position, or an extent that is not two positive whole cell counts, is
    refused here rather than three calls later inside a layout.

    Attributes:
        number: The puzzle's 1-based number in the book — the same N its
            page's band shows (ADR-0037/R1, CARD-117), which is what makes the
            key usable at all.
        width: Its grid's width in cells (columns), ADR-0022's boundary pair
            with ``height``.
        height: Its grid's height in cells (rows).
        level: The puzzle's tier, or ``None`` when its row states none that
            :func:`~nonogram.difficulty.tier_of_record` can read. ``None`` is a
            level of its own — see :func:`level_heading`.
    """

    number: int
    width: int
    height: int
    level: Optional[Tier]

    def __post_init__(self) -> None:
        if not isinstance(self.number, int) or isinstance(self.number, bool):
            raise ValueError(f"an answer's number is a print position, got {self.number!r}")
        if self.number < 1:
            raise ValueError(f"puzzles are numbered from 1, got {self.number}")
        for side, value in (("width", self.width), ("height", self.height)):
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(
                    f"answer {self.number}'s {side} must be a positive whole "
                    f"number of cells, got {value!r}"
                )
        if self.level is not None and not isinstance(self.level, Tier):
            raise ValueError(
                f"answer {self.number}'s level must be a Tier or None, got {self.level!r}"
            )

    @property
    def longest_side(self) -> int:
        """The larger of the answer's two extents, in cells."""
        return max(self.width, self.height)

    @property
    def needs_four_up(self) -> bool:
        """Whether this answer takes its page down to :data:`FOUR_UP` (INV-011)."""
        return self.longest_side > SIX_UP_LONGEST_SIDE


def page_capacity(answers: Sequence[Answer]) -> int:
    """How many answers a page holding ``answers`` may hold (INV-011).

    :data:`SIX_UP` while every answer on it is at most
    :data:`SIX_UP_LONGEST_SIDE` on its longest side, :data:`FOUR_UP` once one
    of them is longer. A function of the answers alone, which is why
    :attr:`AnswerPage.capacity` is derived rather than stored: a page whose
    stored tiling disagreed with the answers on it would print a 30x30 at
    2.6 mm and nothing would say so.
    """
    return FOUR_UP if any(answer.needs_four_up for answer in answers) else SIX_UP


def level_heading(level: Optional[Tier]) -> Optional[str]:
    """The heading a level's first answer page carries: "Easy", "Medium", "Hard".

    ``None`` in gives ``None`` out — a run of puzzles whose rows carry no tier
    anyone can read has no name to print, and the three honest options are the
    same three
    :func:`~nonogram.admin.book_pdf_generator.band_identity` weighs for a band:
    print the raw stored text, invent a fourth label, or say only what is
    known. This says only what is known, for the same reason and so that the
    two surfaces agree. Such a run is still a level of its own, so it still
    starts its own page — it simply starts it unheaded.
    """
    return None if level is None else level.label


def answer_title(custom_title: object, puzzle_name: object) -> Optional[str]:
    """The title an answer's caption prints, or ``None`` when there is none.

    FR-042 as the owner confirmed it on 2026-09-22 (d): the **per-book title**
    set on the Arrangement step (``books.puzzle_titles``) when one is set, and
    otherwise the puzzle's own name. This is the only place either prints
    (ADR-0037/R1) — a puzzle page's band gives no title away.

    Both are read defensively, because both come from a database column that
    may hold anything: a value that is not a string, or is blank or only
    spaces, is no title. A title is printed with its surrounding space
    stripped, as the Arrangement step already stores it.
    """
    for candidate in (custom_title, puzzle_name):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def answer_caption(number: int, title: Optional[str]) -> str:
    """One answer's caption: ``"Puzzle 7 — Snowflake"`` (FR-042, AC-268).

    ``number`` is the puzzle's number in the book, the same one its puzzle
    page's band shows, so an answer is found by the number printed on the
    puzzle and recognised by the name once it is found.

    **A puzzle with neither a custom title nor a name is captioned "Puzzle 7"
    and stops.** An em dash with nothing after it is a caption that looks
    broken rather than one that says less, and the number alone is still the
    whole of what the key is *used* by. The same decision, for the same reason,
    as an ungraded puzzle's band (:func:`band_identity`).

    Raises:
        ValueError: ``number`` is not a print position (below 1).
    """
    if number < 1:
        raise ValueError(f"puzzles are numbered from 1, got {number}")
    if not title:
        return f"Puzzle {number}"
    return f"Puzzle {number}{CAPTION_SEPARATOR}{title}"


@dataclass(frozen=True, slots=True)
class AnswerPage:
    """One page of the packed key: the answers on it, and its heading (FR-042).

    A value object, valid by construction: a page holding two levels, more
    answers than its tiling allows, or none at all is refused here, so a caller
    holding one never re-checks INV-011.

    :attr:`capacity` is **derived** from the answers rather than stored — see
    :func:`page_capacity`.

    Attributes:
        answers: The answers on the page, in fill order — which is
            puzzle-number order, left to right then top to bottom.
        heading: The level's name on the first page of its run, ``None`` on
            every later page of the same run (AC-291) and on a run of answers
            whose level has no name (:func:`level_heading`).
    """

    answers: Tuple[Answer, ...]
    heading: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.answers:
            raise ValueError("an answer page holds at least one answer")
        if len(set(answer.level for answer in self.answers)) != 1:
            raise ValueError(
                "an answer page holds one level, not "
                f"{sorted(str(answer.level) for answer in self.answers)}"
            )
        if len(self.answers) > self.capacity:
            raise ValueError(
                f"{len(self.answers)} answers on a page that holds {self.capacity}"
            )

    @property
    def capacity(self) -> int:
        """The tiling this page is laid out at: :data:`SIX_UP` or :data:`FOUR_UP`."""
        return page_capacity(self.answers)

    @property
    def level(self) -> Optional[Tier]:
        """The one level every answer on the page belongs to."""
        return self.answers[0].level

    @property
    def numbers(self) -> Tuple[int, ...]:
        """The puzzle numbers on the page, in fill order."""
        return tuple(answer.number for answer in self.answers)


def pack_answer_pages(answers: Sequence[Answer]) -> List[AnswerPage]:
    """Walk ``answers`` into answer pages (FR-042, INV-011, EC-030).

    ``answers`` is the book's answers in **puzzle-number order**, which is the
    order they are printed in and the order the numbers themselves run. The
    walk is forward-only and never reorders: concatenating the pages' answers
    front to back gives ``answers`` back exactly.

    The rule, in one sentence: the next answer joins the current page when it
    belongs to the same level *and* the page with it on would still be within
    the capacity it would then have; otherwise it starts a new page. See the
    module docstring for why that closes a five-answer page in front of a
    25x25 and a four-answer page behind one.

    A **level's run** is a maximal stretch of consecutive answers sharing a
    level. Its first page carries :func:`level_heading`; its later pages carry
    none. A book whose order is INV-009-grouped has one run per level, which is
    the case AC-291 measures; a legacy order that returns to a level it has
    already left gets a second heading for it, because an unheaded run in the
    middle of the key would read as a continuation of the level above it.

    Args:
        answers: The book's answers in puzzle-number order.

    Returns:
        One :class:`AnswerPage` per page, in print order. Empty for an empty
        book — a book with no puzzles has no answer key and no divider.

    Raises:
        ValueError: ``answers`` is not in strictly increasing puzzle-number
            order. INV-011 is an order as much as a capacity, and a key whose
            walk silently accepted 3, 1, 2 would print the answers in an order
            no page number points at.
    """
    numbers = [answer.number for answer in answers]
    if any(later <= earlier for earlier, later in zip(numbers, numbers[1:])):
        raise ValueError(
            f"answers reach the key in puzzle-number order, not {numbers}"
        )

    pages: List[AnswerPage] = []
    current: List[Answer] = []
    previous_level: Optional[Tier] = None

    def close() -> None:
        """Turn the answers gathered so far into a page, with its heading."""
        nonlocal previous_level
        level = current[0].level
        heading = level_heading(level) if not pages or level != previous_level else None
        pages.append(AnswerPage(answers=tuple(current), heading=heading))
        previous_level = level

    for answer in answers:
        if current:
            joined = current + [answer]
            if answer.level == current[0].level and len(joined) <= page_capacity(joined):
                current = joined
                continue
            close()
        current = [answer]
    if current:
        close()
    return pages


# ---------------------------------------------------------------------------
# Small answers pack 2-or-4 to a page, with clues (CARD-202, owner decisions
# resolved 2026-10-08 via AskUserQuestion)
# ---------------------------------------------------------------------------
#
# CARD-198 took every answer, large or small, to one full solved page with
# clues. CARD-202 let answers up to 15 wide and 20 tall pack instead, keeping
# their clues and their band (``export.layout.compute_packed_solved_layout``);
# the owner's ruling of 2026-11-07 and the decision of 2026-11-09 widened that
# to every size the book supports, four to a page (CARD-232). An answer that
# does not qualify still plans as a page of its own, but today none exists in
# the supported range; the degrade pass in ``book_pdf_generator`` is what still
# prints an answer alone.
#
# The walk below decides only which answers land on which page and in what
# grouping — the same split from COMP-007 this module already keeps for the
# old packed key (see the module docstring): no PIL, no PageSpec, nothing
# drawn.

#: Was the owner's threshold (Google Doc "Nonograms - Print layout1", item 4,
#: 2026-10-08), until 2026-11-09: an answer this size or smaller packed; anything wider than 15
#: cells OR taller than 20 keeps CARD-198's one-full-page treatment, even if
#: the other side is small. Both sides are checked separately — this is not
#: :data:`SIX_UP_LONGEST_SIDE`'s single longest-side bound.
#: Owner decision 2026-11-09: up to 30x30 packs four to a page (the
#: previews of 25x30 and 30x30 tiles read well), so every size the book can
#: hold now packs; the bound is :data:`nonogram.limits.MAX_SIZE` itself.
PACKED_MAX_WIDTH = MAX_SIZE
PACKED_MAX_HEIGHT = MAX_SIZE

#: The only two packed-page capacities: 4, every page the walk plans, and 2,
#: used only by the degrade pass. There is no larger one — a with-clues tile
#: has no clue-gutter room to spare beyond four to a page (see
#: ``export.layout.SOLVED_TILE_MAX_CELL_MM``'s own docstring).
PACKED_FOUR_UP = FOUR_UP
PACKED_TWO_UP = 2


def qualifies_for_packing(answer: Answer) -> bool:
    """Whether ``answer`` packs: both sides within :data:`PACKED_MAX_WIDTH` x :data:`PACKED_MAX_HEIGHT`.

    Both sides, checked separately. Since 2026-11-09 the bounds are
    :data:`~nonogram.limits.MAX_SIZE`, so every supported size qualifies
    (CARD-232); the check stays because :class:`PackedAnswerPage` is valid by
    construction against it.
    """
    return answer.width <= PACKED_MAX_WIDTH and answer.height <= PACKED_MAX_HEIGHT


@dataclass(frozen=True, slots=True)
class PackedAnswerPage:
    """One packed page of CARD-202's key: 2 or 4 small answers, one tier.

    A value object, valid by construction: :meth:`__post_init__` refuses a
    page holding two levels, more answers than its tiling allows, an answer
    that does not qualify for packing, or none at all — so a caller holding
    one never re-checks those.

    :attr:`capacity` is the tiling, 4 (a 2x2) unless stated. Owner decision
    2026-11-09 (CARD-232 AC-4): a level's last page of one to three answers
    keeps the same 2x2 positions as its full pages rather than switching to a
    larger 2-up tiling. 2 is used only by the degrade path, when four tiles
    cannot reach the minimum cell (``_degrade_infeasible_packed_pages``).

    Attributes:
        answers: The answers on the page, in fill order — puzzle-number
            order, left to right then top to bottom (2 columns always).
        capacity: The tiling the page is laid out at: 4, or 2 when degraded.
    """

    answers: Tuple[Answer, ...]
    capacity: int = 4

    def __post_init__(self) -> None:
        if not self.answers:
            raise ValueError("a packed answer page holds at least one answer")
        if self.capacity not in (PACKED_TWO_UP, PACKED_FOUR_UP):
            raise ValueError(
                f"a packed page is laid out at {PACKED_TWO_UP} or "
                f"{PACKED_FOUR_UP}, not {self.capacity}"
            )
        if len(self.answers) > self.capacity:
            raise ValueError(
                f"{len(self.answers)} answers on a packed page that holds "
                f"at most {self.capacity}"
            )
        if len(set(answer.level for answer in self.answers)) != 1:
            raise ValueError(
                "a packed answer page holds one level, not "
                f"{sorted(str(answer.level) for answer in self.answers)}"
            )
        for answer in self.answers:
            if not qualifies_for_packing(answer):
                raise ValueError(
                    f"answer {answer.number} is {answer.width}x{answer.height}, "
                    f"too large to pack (width<={PACKED_MAX_WIDTH} and "
                    f"height<={PACKED_MAX_HEIGHT} only)"
                )

    @property
    def level(self) -> Optional[Tier]:
        """The one level every answer on the page belongs to."""
        return self.answers[0].level

    @property
    def numbers(self) -> Tuple[int, ...]:
        """The puzzle numbers on the page, in fill order."""
        return tuple(answer.number for answer in self.answers)


#: One planned page of CARD-202's answer section: a packed page of 2 or 4
#: small answers, or a single large answer still printing on a page of its
#: own (CARD-198's unchanged rule). ``book_pdf_generator`` turns each of these
#: into an actual page at whatever interior position the walk has reached.
AnswerSectionPage = Union[Answer, PackedAnswerPage]


def plan_small_answer_pages(answers: Sequence[Answer]) -> List[AnswerSectionPage]:
    """Plan the book's answer section in book order (CARD-202, FR-042 narrowed).

    ``answers`` is the book's answers in **puzzle-number order**, exactly as
    :func:`pack_answer_pages` requires of its own input. The walk is
    forward-only and never reorders: concatenating the plan's answers front to
    back (reading a :class:`PackedAnswerPage`'s :attr:`~PackedAnswerPage.numbers`
    in order) gives ``answers`` back exactly, so a large answer's own page and
    a run of small ones' packed pages interleave in book order, never out of
    it (AC-2).

    **The rule, walked forward.** A large answer (:func:`qualifies_for_packing`
    is ``False``) always closes whatever packed run came before it and prints
    on a page of its own — CARD-198's unchanged treatment. A run of
    consecutive small answers *of one level* is cut into pages of 4, and the
    last one to three answers share one more page in the same 2x2 positions
    (owner decision 2026-11-09, CARD-232 AC-4; it replaced 2026-10-08's
    "2-up only for leftovers"). A run ends,
    the same way :func:`pack_answer_pages`'s own one-level-per-page rule ends
    one, the moment either the level changes **or** the next answer does not
    qualify for packing — both are a tier boundary in the sense that matters
    here: neither ever lets two different levels, or a small and a large
    answer, share one packed page (G-6).

    Args:
        answers: The book's answers in puzzle-number order.

    Returns:
        One :class:`Answer` (unpacked) or :class:`PackedAnswerPage` per
        planned page, in print order. Empty for an empty book.

    Raises:
        ValueError: ``answers`` is not in strictly increasing puzzle-number
            order (the same precondition :func:`pack_answer_pages` checks, for
            the same reason).
    """
    numbers = [answer.number for answer in answers]
    if any(later <= earlier for earlier, later in zip(numbers, numbers[1:])):
        raise ValueError(
            f"answers reach the key in puzzle-number order, not {numbers}"
        )

    plan: List[AnswerSectionPage] = []
    run: List[Answer] = []

    def flush() -> None:
        index = 0
        while index < len(run):
            take = min(len(run) - index, PACKED_FOUR_UP)
            plan.append(PackedAnswerPage(tuple(run[index : index + take])))
            index += take
        run.clear()

    for answer in answers:
        if not qualifies_for_packing(answer):
            flush()
            plan.append(answer)
            continue
        if run and answer.level != run[0].level:
            flush()
        run.append(answer)
    flush()
    return plan

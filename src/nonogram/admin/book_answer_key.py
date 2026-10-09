"""The book's packed answer key: which answers share a page, and what each says.

FR-042 (owner decision BK-8) replaced one full answer page per puzzle — a
150-puzzle book passing 300 pages — with a **packed** key: six answers to a
page (2 columns x 3 rows) while every answer on the page is small, four (2 x 2)
once one of them is large. This module owns that walk and the caption text.
It owns nothing else.

The split with COMP-007 (ADR-0036/R2, G-1)
------------------------------------------
This module is **pure**: value objects in, value objects out. It measures no
tile, fits no cell, places no rule and draws nothing — there is no ``PIL``
import here and no ``PageSpec``. It decides only *which answers land on which
page*, *which page carries a level heading* and *what a caption says*; the
geometry of the page those decisions describe is
:func:`~nonogram.export.layout.compute_answer_page_layout`'s
(CARD-133), and the ink is :func:`~nonogram.export.png.render_answer_page`'s.

That is also why this is a module of its own rather than three more methods on
:class:`~nonogram.admin.book_pdf_generator.BookPDFGenerator`: the walk is
decided entirely by the answers' numbers, extents and levels, so it can be
swept over thousands of book orders (EC-030) without a page being rendered.

The capacity rule is this module's, not the layout's (INV-011)
--------------------------------------------------------------
CARD-133's handover is explicit that the 3.19 mm answer-cell floor (EC-031) is
**not** enforced by the layout type: a 25x25 laid out six-up comes back at
3.178 mm and a 30x30 six-up at 2.648 mm, with no error raised. What keeps every
answer above that floor is the rule here — a six-up page holds nothing above
:data:`SIX_UP_LONGEST_SIDE` cells on its longest side — so it is a rule, with
its own tests, and not a preference.

Neither number is measured by this module's own tests, which count pages and
read captions. The floor is swept over every extent INV-011 admits by CARD-133's
``tests/property/test_book_answer_tiles.py``, and the *link* between it and the
threshold above — 20 six-up clears the floor, 25 six-up does not, and the layout
raises nothing either way — is pinned by
``tests/test_book_answer_key.py::TestBookAnswerKey_SixUpRuleKeepsTheAnswerCellAboveTheFloor``.
The threshold is deliberately clear of the edge: on the Book 1 profile every
side up to 24 still clears the floor six-up, 25 is the first that does not.

A page is closed late, never early
----------------------------------
The next answer joins the current page when the page **with it** is still
within the capacity that page *would then have*. So five small answers followed
by a 25x25 close a six-up page of five (AC-263): the sixth answer would make
the page four-up, and six on a four-up page is not a page. Three small answers
plus a 25x25 make a four-up page of four, and the small answer after it starts
a new page (AC-264). The page's capacity is therefore never stored: it is
:attr:`AnswerPage.capacity`, read off the answers on it, so a page and its
tiling cannot drift apart.

**Every level starts a new answer page** (FR-042 amended 2026-09-22 (d)): an
answer whose level differs from the current page's opens a new one even when
the page has room, so no page holds two levels (INV-011 amended). The first
page of a level's run carries that level's name as its heading; later pages of
the same run carry none (AC-291).

Because every page that is closed *by the capacity rule* holds at least four
answers (a page is closed only when the next answer would make it too many, and
the smaller capacity is four), only the last page of a level can hold fewer.
That is the whole of EC-030's page-count bound: ``ceil(n / 6)`` at best, and at
worst ``ceil(n / 4) + (L - 1)`` for ``L`` non-empty levels — at most two pages
more than an unlevelled key would take on the default plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union

from nonogram.difficulty import Tier

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
# clues (``book_pdf_generator.solved_puzzle_page``). This narrows that rule:
# an answer small enough to shrink and still read clearly — width<=15 **and**
# height<=20 — packs 2 or 4 to a page instead, keeping its clues and its
# title band (``export.layout.compute_packed_solved_layout``, CARD-202). A
# large answer (anything over either bound) is unaffected and still prints
# alone: CARD-198's rule narrows, it does not disappear.
#
# The walk below decides only which answers land on which page and in what
# grouping — the same split from COMP-007 this module already keeps for the
# old packed key (see the module docstring): no PIL, no PageSpec, nothing
# drawn.

#: The owner's threshold (Google Doc "Nonograms - Print layout1", item 4,
#: 2026-10-08): an answer this size or smaller packs; anything wider than 15
#: cells OR taller than 20 keeps CARD-198's one-full-page treatment, even if
#: the other side is small. Both sides are checked separately — this is not
#: :data:`SIX_UP_LONGEST_SIDE`'s single longest-side bound.
PACKED_MAX_WIDTH = 15
PACKED_MAX_HEIGHT = 20

#: The only two packed-page capacities this rule uses (owner decision,
#: resolved 2026-10-08): never :data:`SIX_UP` — a with-clues tile has no
#: clue-gutter room to spare at six to a page (see
#: ``export.layout.SOLVED_TILE_MAX_CELL_MM``'s own docstring).
PACKED_FOUR_UP = FOUR_UP
PACKED_TWO_UP = 2


def qualifies_for_packing(answer: Answer) -> bool:
    """Whether ``answer`` is small enough to pack (CARD-202): width<=15 and height<=20.

    Both sides, checked separately — an answer 21 cells tall and 1 cell wide
    does not qualify, however narrow it is, and neither does one 16 wide and
    1 tall. This is the one check every page in the walk below is sorted by.
    """
    return answer.width <= PACKED_MAX_WIDTH and answer.height <= PACKED_MAX_HEIGHT


@dataclass(frozen=True, slots=True)
class PackedAnswerPage:
    """One packed page of CARD-202's key: 2 or 4 small answers, one tier.

    A value object, valid by construction: :meth:`__post_init__` refuses a
    page holding two levels, more answers than its tiling allows, an answer
    that does not qualify for packing, or none at all — so a caller holding
    one never re-checks those.

    Unlike the old six-up/four-up :class:`AnswerPage`, :attr:`capacity` here
    is **not** derived from the answers' own extents (there is no analogue of
    :data:`SIX_UP_LONGEST_SIDE` gating 2 vs 4): it is 4 whenever the page
    holds more than :data:`PACKED_TWO_UP` answers, 2 otherwise — the owner's
    "always 4-up, 2-up only for a leftover" rule, read off the page's own
    answer count because that count *is* the rule's only input.

    Attributes:
        answers: The answers on the page, in fill order — puzzle-number
            order, left to right then top to bottom (2 columns always).
    """

    answers: Tuple[Answer, ...]

    def __post_init__(self) -> None:
        if not self.answers:
            raise ValueError("a packed answer page holds at least one answer")
        if len(self.answers) > PACKED_FOUR_UP:
            raise ValueError(
                f"{len(self.answers)} answers on a packed page that holds "
                f"at most {PACKED_FOUR_UP}"
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
    def capacity(self) -> int:
        """The tiling this page is laid out at: 2 or 4 (never 6, unlike :data:`SIX_UP`)."""
        return PACKED_FOUR_UP if len(self.answers) > PACKED_TWO_UP else PACKED_TWO_UP

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
    consecutive small answers *of one level* is cut into pages of 4 while at
    least 4 remain, then a page of 2 while at least 2 remain, then a page
    holding the last 1 if one is left over — never a page of 3, never a 4-up
    page with an empty slot (owner decision, resolved 2026-10-08: "always
    4-up, 2-up only for leftovers", no secondary size threshold). A run ends,
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
            remaining = len(run) - index
            take = PACKED_FOUR_UP if remaining >= PACKED_FOUR_UP else min(
                remaining, PACKED_TWO_UP
            )
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

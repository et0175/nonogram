"""Amazon KDP's gutter-margin table, and the finalise check against it.

FR-030 / CON-018 / ADR-0036's clarification ("Gutter margin and page count").

KDP asks for a wider inside (gutter) margin once a book passes 150 pages. A
book laid out with a 0.375 in gutter that then runs to 180 pages is **rejected
at upload** — after everything else about it already looked finished. That is
one page count too late to find out, so the check is made at finalise instead.

**Why this refuses instead of adjusting.** The page count depends on the
layout and, through this table, the layout's gutter depends on the page count.
ADR-0036's clarification breaks that circularity by *refusing rather than
iterating*: the book always lays out with its **stored** gutter (G-2), the
interior's page count is read off that one layout, and finalise compares the
two. Nothing here raises the stored gutter, and nothing here lays a book out a
second time at a wider one to see whether it would then fit — that would be
the iteration the ADR exists to avoid, and its fixed point is not even
guaranteed to exist (a wider gutter makes fewer two-up pages fit, which makes
the book longer, which can ask for a wider gutter again).

**The table, and where it stops.** Four bands, stated in inches because KDP
states them in inches (CON-018; CARD-199 added the last two):

* up to 150 pages — 0.375 in (0.9525 cm);
* 151 to 300 pages — 0.5 in (1.27 cm);
* 301 to 500 pages — 0.625 in (1.5875 cm);
* 501 to 590 pages — 0.75 in (1.905 cm).

**Why 590 and not KDP's general 828.** KDP's own published table
("Set Trim Size, Bleed, and Margins",
https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6, retrieved
2026-10-07; cross-checked against three independent secondary guides —
scribecount.com, vappingo.com, kdpbuilder.com — that all state the same
figures) continues past the 590 pages recorded above: 501-700 pages asks for
0.75 in and 701-828 pages asks for 0.875 in, and 828 pages is the general
ceiling KDP states for a black-ink, white-paper paperback. That 828-page
figure, though, is what KDP states for the 5"x8", 5.5"x8.5" and 6"x9" trims.
This module has no trim parameter, and the one trim this project's books
actually ship on — CON-018's Book 1 profile, 8.5"x11" — has its own, *lower*
absolute page-count ceiling for the same black-ink, white-paper case: **590
pages**, stated both by the help topic above and by "Paperback Submission
Guidelines" (https://kdp.amazon.com/en_US/help/topic/G201857950, retrieved
2026-10-07). (Cream paper's ceiling is lower still, but this project has no
paper-type column — `grep`ping the whole of ``src/nonogram`` for
"cream"/"paper_type"/"paper_color" finds nothing — so every book is treated
as the more permissive white-paper case, as this module already implicitly
does for every other KDP figure it models.)

590 falls *inside* the general table's 501-700 band, not at a band boundary,
so stopping at the trim-accurate 590 rather than the general 828 means the
701-828 range (and the 591-700 tail of the 501-700 band) is never modelled
here at all — not because the numbers are unknown, but because they are
*unreachable*: an 8.5"x11" book that long is rejected at KDP upload purely
for exceeding the page-count cap on that trim, regardless of what gutter it
stores. Modelling a minimum for that range would let such a book pass this
check and still fail at upload — the exact "looked finished, rejected at
upload" failure CON-018/ADR-0036 already exist to prevent, just moved from
the old 300-page boundary to a new one. (A different ceiling per stored trim
is a bigger change, out of scope for this table — see ``book_page_spec``'s
own trim support for a future card.)

**Above 590 pages the requirements are silent, and so is this module.**
*Which* numbers KDP's table continues with past 590 is recorded above, but
they describe pages this project's one real trim cannot legally reach, so
recording them as a minimum here would be inventing a rule for a page count
that is never real. :func:`kdp_min_gutter_cm` therefore raises
:class:`KdpPageCountNotModelled` for such a page count, and finalise turns
that into a refusal naming what is missing. A book of over 590 pages is also
far outside the ~120-190-page model the answer key exists to keep books inside
(FR-042), so this is a boundary a curated book is not expected to reach; if
the project ever ships a different trim with its own, higher real ceiling,
the remedy is to make this table trim-aware, not to widen it by hand.

**Centimetres, at the precision the column stores — and rounded in the safe
direction.** The ``books`` table keeps margins as centimetre strings with two
decimals, so the 0.375 in band is stored as ``"0.95"`` — 0.9525 cm rounded,
and the only way that value can be written. CON-018 writes the band down that
way itself. A comparison against the exact 0.9525 cm would therefore refuse
every book that is *on* the profile, so the comparison is made at the column's
own precision (:data:`STORED_PRECISION`): "0.95" is 0.375 in, because in that
column it is the same number.

The two sides of that comparison are quantized **differently**, and on
purpose. A band minimum is rounded half-up (:func:`_rounded`), because that is
CON-018's own spelling of it. A book's stored gutter is floored
(:func:`_floored`), because it is the value under test and may only ever read
narrower than it is. Rounding the stored value up would admit a gutter that is
genuinely below KDP's minimum — 0.945 cm would read as "0.95" and pass here,
then be rejected at upload — which is exactly the failure this check exists to
prevent. So "0.95" passes and "0.945" does not, and no value is ever rounded
*into* compliance.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_FLOOR, ROUND_HALF_UP
from typing import Any, List, Optional, Sequence, Tuple

from nonogram.admin.book_answer_key import Answer, pack_answer_pages
from nonogram.admin.book_page_spec import BOOK1_PROFILE
from nonogram.admin.book_pdf_generator import interior_page_count, print_order
from nonogram.difficulty import tier_of_record

__all__ = [
    "KDP_GUTTER_BANDS",
    "MAX_MODELLED_PAGE_COUNT",
    "STORED_PRECISION",
    "KdpPageCountNotModelled",
    "gutter_refusal",
    "kdp_min_gutter_cm",
    "kdp_page_band",
    "stored_gutter_cm",
    "unpaired_interior_page_count",
]

_CM_PER_INCH = Decimal("2.54")

#: KDP's gutter table (FR-030, CON-018): ``(the band's last page, its gutter in
#: inches)``, in ascending page order. Stated in inches, once, because that is
#: how KDP states it; every centimetre figure in this module is derived from
#: these entries and none is written out a second time.
#:
#: The first two entries are CON-018's own (unchanged by CARD-199, which only
#: appends after them). The last two were added by CARD-199, from KDP's own
#: help topic ("Set Trim Size, Bleed, and Margins",
#: https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6, retrieved
#: 2026-10-07; cross-checked against three independent secondary guides —
#: scribecount.com, vappingo.com, kdpbuilder.com — that state the same
#: figures). The table stops at 590 rather than KDP's general 828-page
#: ceiling for one reason: this module has no trim parameter, and this
#: project's one real trim (CON-018's Book 1, 8.5"x11") has its own lower,
#: trim-accurate absolute page-count ceiling of 590 pages — stated by the
#: topic above and by "Paperback Submission Guidelines"
#: (https://kdp.amazon.com/en_US/help/topic/G201857950, retrieved
#: 2026-10-07) — not the 828 KDP states for the 5"x8"/5.5"x8.5"/6"x9" trims.
#: 590 falls inside the general table's 501-700 band, so a 591-700/701-828
#: entry here would model a gutter minimum for page counts this trim can
#: never legally reach, letting such a book pass this check and still be
#: rejected at KDP upload purely for exceeding the page-count cap — see the
#: module docstring.
KDP_GUTTER_BANDS: Tuple[Tuple[int, Decimal], ...] = (
    (150, Decimal("0.375")),
    (300, Decimal("0.5")),
    (500, Decimal("0.625")),
    (590, Decimal("0.75")),
)

#: The largest page count the table above models. A book longer than this has
#: no modelled minimum — see the module docstring.
MAX_MODELLED_PAGE_COUNT: int = KDP_GUTTER_BANDS[-1][0]

#: How many decimals of a centimetre the ``books`` margin columns hold, and
#: therefore the precision every comparison in this module is made at.
STORED_PRECISION = Decimal("0.01")


class KdpPageCountNotModelled(ValueError):
    """The interior's page count is outside KDP's recorded gutter table.

    A domain refusal and not a bug: the page count is perfectly well known,
    and it is the *requirement* that stops. Raised by
    :func:`kdp_page_band` and :func:`kdp_min_gutter_cm` above
    :data:`MAX_MODELLED_PAGE_COUNT`, so that the one thing this module will
    not do — guess a band — is impossible to do by accident.

    A ``ValueError``, and deliberately **not** a
    :class:`~nonogram.errors.NonogramError`, for the reason
    :class:`~nonogram.admin.app.AdminConfigurationError` gives: that hierarchy
    is the puzzle domain's, and every member of it is something ``cli.py``
    maps onto a process exit code for a user who asked for a puzzle — a rule
    ``tests/test_web_submission.py``'s
    ``test_the_walked_corpus_is_the_whole_hierarchy`` enforces by refusing any
    subclass the CLI's table does not deliberately classify. A book's KDP
    gutter band is not something the CLI can be asked for. It is a
    ``ValueError`` because that is what the book domain's own refusals are
    (``set_book_status``, ``book_page_spec``, ``InvalidBookDetails``), so
    every caller that already guards a book operation keeps catching it.
    """


def _as_cm(inches: Decimal) -> Decimal:
    """One band's gutter in centimetres, exactly (0.375 in -> 0.9525 cm)."""
    return inches * _CM_PER_INCH


def _rounded(centimetres: Decimal) -> Decimal:
    """A **minimum** at the precision the ``books`` columns store.

    Half-up, and only ever applied to one of KDP's own band minima, because
    that is the arithmetic CON-018 itself performed when it wrote 0.9525 cm
    down as "0.95 cm" and 1.27 cm as "1.27 cm". Rounding a minimum up would
    invent a rule stricter than KDP's and refuse every book created on the
    profile.
    """
    return centimetres.quantize(STORED_PRECISION, rounding=ROUND_HALF_UP)


def _floored(centimetres: Decimal) -> Decimal:
    """A **stored** gutter at the precision the ``books`` columns store.

    Towards zero, never up: this is the value under test, and a gutter is only
    ever read as narrower than it is, never wider. Half-up here would round a
    genuinely short gutter *into* compliance — 0.945 cm would read as "0.95"
    and pass, then be rejected at upload, which is the one failure this module
    exists to catch. The 0.0075 cm window that opens is small and reachable
    only by a hand-edited or legacy row, but the error would point the unsafe
    way, so the two quantizations are deliberately asymmetric.
    """
    return centimetres.quantize(STORED_PRECISION, rounding=ROUND_FLOOR)


def _page_count(page_count: object) -> int:
    if isinstance(page_count, bool) or not isinstance(page_count, int):
        raise ValueError(
            f"a page count is a whole number of pages, not {page_count!r}"
        )
    if page_count < 1:
        raise ValueError(f"a book's interior holds at least one page, got {page_count}")
    return page_count


def kdp_page_band(page_count: int) -> Tuple[int, int]:
    """The band ``page_count`` falls in, as ``(first page, last page)``.

    ``(1, 150)``, ``(151, 300)``, ``(301, 500)`` or ``(501, 590)`` — the pair
    the refusal names, so that the owner is told which rule was applied and
    not only what it asked for.

    Raises:
        ValueError: ``page_count`` is not a whole number of at least 1.
        KdpPageCountNotModelled: it is above :data:`MAX_MODELLED_PAGE_COUNT`.
    """
    count = _page_count(page_count)
    first = 1
    for last, _ in KDP_GUTTER_BANDS:
        if count <= last:
            return (first, last)
        first = last + 1
    raise KdpPageCountNotModelled(
        f"KDP gutter table not modelled above {MAX_MODELLED_PAGE_COUNT} pages: "
        f"this interior runs to {count}. The recorded table stops at "
        f"{MAX_MODELLED_PAGE_COUNT} pages, so there is no minimum to check "
        f"this book's gutter margin against."
    )


def kdp_min_gutter_cm(page_count: int) -> float:
    """KDP's smallest acceptable gutter margin for ``page_count`` pages, in cm.

    0.9525 cm (0.375 in) up to 150 pages, 1.27 cm (0.5 in) for 151 to 300
    (FR-030, CON-018), 1.5875 cm (0.625 in) for 301 to 500 and 1.905 cm
    (0.75 in) for 501 to 590 (CARD-199 — see the module docstring for why the
    table stops at 590). The page count is the **interior**'s: the cover is
    a separate file and is never counted (FR-043).

    Raises:
        ValueError: ``page_count`` is not a whole number of at least 1.
        KdpPageCountNotModelled: it is above :data:`MAX_MODELLED_PAGE_COUNT`.
            Deliberately not a fourth band invented here — see the module
            docstring.
    """
    _first, last = kdp_page_band(page_count)
    for band_last, inches in KDP_GUTTER_BANDS:
        if band_last == last:
            return float(_as_cm(inches))
    raise AssertionError(f"no band ends at page {last}")  # pragma: no cover


def kdp_min_gutter_inches(page_count: int) -> float:
    """:func:`kdp_min_gutter_cm`'s band, in the inches KDP states it in."""
    _first, last = kdp_page_band(page_count)
    for band_last, inches in KDP_GUTTER_BANDS:
        if band_last == last:
            return float(inches)
    raise AssertionError(f"no band ends at page {last}")  # pragma: no cover


def stored_gutter_cm(book: object) -> float:
    """The gutter margin ``book`` **stores**, in centimetres.

    Read straight off the ``books`` print column, exactly as
    :func:`~nonogram.admin.book_page_spec.book_page_spec` reads it, and never
    written: a missing or empty column is CON-018's Book 1 profile (0.5 in),
    which is what the sheet would be laid out on.

    Raises:
        ValueError: the column holds something that is not a finite number of
            centimetres. The message names the column, as the sheet builder's
            does.
    """
    raw = getattr(book, "gutter_margin_cm", None)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return float(Decimal(BOOK1_PROFILE.gutter_margin_cm))
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float, Decimal)):
        raise ValueError(
            f"book gutter_margin_cm must be a number of cm, not {raw!r}"
        )
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation:
        raise ValueError(
            f"book gutter_margin_cm must be a number of cm, not {raw!r}"
        ) from None
    if not value.is_finite():
        raise ValueError(
            f"book gutter_margin_cm must be a finite number of cm, not {raw!r}"
        )
    return float(value)


def gutter_refusal(page_count: int, gutter_cm: float) -> Optional[str]:
    """Why finalise must refuse this book, or ``None`` when it need not.

    The whole of the check, as a pure function of the two numbers it is about:
    the **interior**'s page count (the cover excluded, FR-043) and the gutter
    the book **stores**. It reads no book, writes nothing, and in particular
    never adjusts the gutter (G-1) — the caller's only options are to pass the
    text on or to carry on.

    ``None`` means the stored gutter meets KDP's minimum for that page band.
    Otherwise the returned text names, in the order the owner needs them: the
    page count, the band it falls in, the minimum KDP asks for there in both
    centimetres and inches, and the value this book stores.

    Both numbers are read at the column's two-decimal precision, but not with
    the same rounding: the minimum half-up (CON-018's own "0.95 cm" for
    0.375 in), the stored gutter floored. A stored gutter is therefore never
    rounded *up* into compliance — "0.95" passes, "0.945" is refused and named
    as the "0.94 cm" it is at that precision. See the module docstring.

    Raises:
        ValueError: ``page_count`` is not a whole number of at least 1.
        KdpPageCountNotModelled: it is above :data:`MAX_MODELLED_PAGE_COUNT`.
    """
    first, last = kdp_page_band(page_count)
    minimum_cm = Decimal(str(kdp_min_gutter_cm(page_count)))
    minimum_in = kdp_min_gutter_inches(page_count)
    stored = Decimal(str(gutter_cm))
    if _floored(stored) >= _rounded(minimum_cm):
        return None
    return (
        f"This book's interior runs to {page_count} pages, and KDP asks for a "
        f"gutter margin of at least {_rounded(minimum_cm)} cm ({minimum_in:g} in) "
        f"for {first}-{last} pages. This book stores "
        f"{_floored(stored)} cm. Nothing was changed: widen the gutter margin "
        f"to at least {_rounded(minimum_cm)} cm, or shorten the book, and "
        f"finalise again."
    )


# ---------------------------------------------------------------------------
# The page count when the book has no sheet at all
# ---------------------------------------------------------------------------


def unpaired_interior_page_count(puzzles: Sequence[Any]) -> int:
    """The interior's page count with every puzzle on a page of its own.

    The page count :class:`~nonogram.admin.book_pdf_generator.InteriorStream`
    reports as ``unpaired_page_count`` — one guide page, one divider per
    non-empty named level, one page per puzzle, the SOLUTIONS divider and the
    **packed** answer key (FR-042) — computed from the book's rows **without a
    sheet**.

    It exists for one case, and it is the case the check would otherwise have
    no answer for: a book whose stored print specification cannot be laid out
    at all (a margin below
    :data:`~nonogram.admin.book_page_spec.MIN_SIDE_MARGIN_MM`, say) has no
    interior to count, and so no page count to name a KDP band from — yet a
    gutter that narrow is below *every* band of :data:`KDP_GUTTER_BANDS`, so
    the refusal is certain and only the wording needs a number. Two-up pairing
    is the one term of the interior's make-up that needs a sheet
    (:func:`~nonogram.export.layout.compute_pair_layout` fits the shared cell
    on the page); the guide page, the level dividers, the SOLUTIONS divider and
    the packed key do not, so all of those are the book's real ones here and
    only the pairing term is replaced by its upper bound, one page per puzzle.

    That makes this an **upper bound** on such a book's interior, never an
    under-count, so it can only ever name a band at or above the true one — and
    it is exact for any book whose puzzles are too large to share a page, which
    a real curated book of 20x20s and 30x30s largely is. It is the same figure
    the Finalise screen shows as "before pairing", and it is cross-checked
    against the generator's own ``unpaired_page_count`` over the property
    corpus (EC-034), so the two cannot drift apart.

    Nothing here is new arithmetic: the make-up is
    :func:`~nonogram.admin.book_pdf_generator.interior_page_count`, the order
    is :func:`~nonogram.admin.book_pdf_generator.print_order`, the levels are
    :func:`~nonogram.difficulty.tier_of_record`'s and the key is
    :func:`~nonogram.admin.book_answer_key.pack_answer_pages`'s — the same four
    calls the generator makes.

    Raises:
        ValueError: a row's solution grid is not a non-empty rectangle, so its
            answer cannot be packed and the book has no page count at all.
    """
    ordered = print_order(list(puzzles))
    levels = [
        tier_of_record(row.get("difficulty_tier")) if hasattr(row, "get") else None
        for row in ordered
    ]
    answers: List[Answer] = []
    for index, (row, level) in enumerate(zip(ordered, levels)):
        columns, rows = _grid_extent(row, index + 1)
        answers.append(
            Answer(number=index + 1, width=columns, height=rows, level=level)
        )
    dividers = len({level for level in levels if level is not None})
    key = pack_answer_pages(answers) if answers else []
    return interior_page_count(
        len(ordered),
        puzzle_pages=len(ordered),
        answer_pages=len(key),
        level_dividers=dividers,
    )


def _grid_extent(row: Any, number: int) -> Tuple[int, int]:
    """One row's answer extent in cells, read off its solution grid.

    The same two numbers the packed key is tiled by, taken from the grid and
    not from the row's ``width``/``height`` columns, for the reason
    ``book_pdf_generator`` takes them from there: the grid is what the key
    prints, and a row whose columns disagree with its grid would otherwise land
    a 25-cell answer on a six-up page.
    """
    grid = row.get("grid") if hasattr(row, "get") else None
    if not isinstance(grid, (list, tuple)) or not all(
        isinstance(line, (list, tuple)) for line in grid
    ):
        raise ValueError(
            f"puzzle {number}'s answer must be rows of cells, not "
            f"{type(grid).__name__}"
        )
    rows = len(grid)
    columns = len(grid[0]) if rows else 0
    if not rows or not columns or any(len(line) != columns for line in grid):
        raise ValueError(
            f"puzzle {number}'s answer must be a non-empty rectangular grid"
        )
    return columns, rows

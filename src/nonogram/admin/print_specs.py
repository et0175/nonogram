"""Print specification service for book scaffolding.

Handles validation, conversion, and storage of print parameters for book PDFs.

Since CARD-147 a print specification also carries **how the interior is
printed** — black-and-white or colour (:class:`~nonogram.admin.book_page_spec.InkMode`)
— because it is the same kind of fact as the trim: something the owner chooses
on Print setup, stores on the book, and the export obeys. Carrying it here is
what lets one submission of that form store the trim and the mode in one write,
so a refused plan stores neither (AC-197's posture, extended to the mode).

And since CARD-332 it carries the **player domain** — the base of the public
player a reader of the printed book would open (``https://nonogram.adverax.io``).
It is the same kind of fact again: chosen on Print setup, stored on the book,
and read by what the book shows and prints. It is stored **with the book**
rather than read from the deploy page at print time because a printed run
records what was printed: a book printed before a domain change cannot be
fixed, so the base belongs beside the trim it was printed on (the decision
CARD-332 was told not to duck; see that card's worktree notes for the rule
about which source wins where).
"""

import math
import re
from dataclasses import dataclass
from typing import Literal, Optional, Tuple
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation

from nonogram.admin.book_page_spec import (
    BOOK1_PROFILE,
    DEFAULT_INK_MODE,
    MAX_TRIM_HEIGHT_CM,
    MAX_TRIM_WIDTH_CM,
    MIN_TRIM_CM,
    InkMode,
)


@dataclass
class PrintSpec:
    """Print specification for a book."""

    trim_width_cm: str
    trim_height_cm: str
    gutter_margin_cm: Optional[str] = None
    outside_margin_cm: Optional[str] = None
    outside_margin_bleed_cm: Optional[str] = None
    #: How the interior is printed (CARD-147): the stored form of an
    #: :class:`~nonogram.admin.book_page_spec.InkMode`, or ``None`` for "the
    #: caller named none", which :meth:`PrintSpecValidator.create_spec` fills
    #: with :data:`~nonogram.admin.book_page_spec.DEFAULT_INK_MODE`.
    interior_ink_mode: Optional[str] = None
    #: Whether the interior prints its four divider pages (CARD-305), or
    #: ``None`` for "the caller named none", which leaves the stored choice
    #: unchanged — the same posture :attr:`interior_ink_mode` takes, and for
    #: the same reason: a caller built before this field must not silently
    #: turn a book's dividers off.
    interior_divider_pages: Optional[bool] = None
    #: The base of the public player this book's puzzles are read at
    #: (CARD-332), as stored: an absolute ``https://`` origin with no trailing
    #: slash, or ``None`` for "the caller named none", which leaves the
    #: stored value unchanged — the posture :attr:`interior_divider_pages`
    #: takes, and for the same reason. The **empty string** is the third
    #: state and the one a text input makes necessary: "the owner cleared the
    #: field", which stores no domain at all. A checkbox cannot say that, so
    #: CARD-305 needed a hidden companion field; a text input always posts
    #: its name, so the field's presence in the submission is its own marker
    #: and ``""`` can mean "cleared" without ambiguity.
    player_domain: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "trim_width_cm": self.trim_width_cm,
            "trim_height_cm": self.trim_height_cm,
            "gutter_margin_cm": self.gutter_margin_cm,
            "outside_margin_cm": self.outside_margin_cm,
            "outside_margin_bleed_cm": self.outside_margin_bleed_cm,
            "interior_ink_mode": self.interior_ink_mode,
            "interior_divider_pages": self.interior_divider_pages,
            "player_domain": self.player_domain,
        }


#: The ``books`` column the player domain is stored in (CARD-332). Named once
#: so a test and a migration can say which column they mean without spelling
#: it, as ``book_page_spec.DIVIDER_PAGES_COLUMN`` is named for its own.
PLAYER_DOMAIN_COLUMN = "player_domain"

#: The only scheme a player domain may carry. Not a preference: the public
#: player is served over TLS and a printed ``http://`` base would be a printed
#: downgrade nobody can correct (ADR-0041's printed-asset posture — a base in
#: a book is as permanent as the key beside it).
PLAYER_DOMAIN_SCHEME = "https://"

#: One label of a host name: alphanumerics and inner hyphens.
_HOST_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"

#: What may follow :data:`PLAYER_DOMAIN_SCHEME`: a host name and an optional
#: port, and **nothing else**. No path, query, fragment, credentials or
#: whitespace, because the stored value is joined to ``/play/<key>`` and a
#: base carrying any of those makes a URL that is not the player's door.
_PLAYER_ORIGIN = re.compile(
    rf"(?P<host>{_HOST_LABEL}(?:\.{_HOST_LABEL})*)(?::(?P<port>[0-9]{{1,5}}))?"
)

#: The highest port number there is. A refusal rather than a silent store: a
#: printed base nobody can reach is the failure this whole family guards.
_MAX_PORT = 65535


def stored_player_domain(book) -> Optional[str]:
    """``book``'s stored player domain, or ``None`` when it has none (CARD-332).

    The one door onto the column, so Print setup and the arrangement screen
    cannot disagree about whether a book has a base. A row from before the
    column, a NULL, and a column holding only whitespace all answer ``None``
    — "no domain set" — which is what every book that existed before CARD-332
    is, and what the arrangement screen says plainly rather than building a
    URL from (AC-3).

    Takes a :class:`~nonogram.admin.book_manager.Book` or a ``books`` row:
    both carry the attribute and neither is imported here (``print_specs``
    sits inward of both).
    """
    value = getattr(book, PLAYER_DOMAIN_COLUMN, None)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


@dataclass(frozen=True)
class TrimLimits:
    """KDP's trim bounds in cm, and in the inches that are always accepted (CARD-174).

    The cm figures are ``book_page_spec``'s constants as they are. Each inch
    figure is the cm bound divided by 2.54 and cut to two decimals **inward**
    — a maximum rounded down, the minimum rounded up — so that typing the
    stated figure back in passes :meth:`PrintSpecValidator.validate_trim_size`
    (48 cm is 18.898 in: 18.90 in would convert to 48.01 cm and be refused,
    18.89 in converts to 47.98 cm). That guarantee is shown only for cm bounds
    that are whole hundredths of a cm, as KDP's 10 / 30 / 48 are: for a bound
    such as 15.875 cm the stated 6.25 in converts to 15.88 cm and is refused.
    The inch refusals and Print setup's
    Limits box both read these, so the page and the server cannot state
    different limits.
    """

    min_cm: float
    max_width_cm: float
    max_height_cm: float
    min_in: str
    max_width_in: str
    max_height_in: str


def _inches_inward(cm: float, rounding: str) -> str:
    """``cm`` in inches, to two decimals, rounded by ``rounding`` (floor or ceiling)."""
    inches = Decimal(str(cm)) / Decimal("2.54")
    return str(inches.quantize(Decimal("0.01"), rounding=rounding))


class PrintSpecValidator:
    """Validates and converts print specifications."""

    # Amazon KDP trim size bounds (in cm), stated once in book_page_spec
    MIN_TRIM_CM = MIN_TRIM_CM
    MAX_TRIM_WIDTH_CM = MAX_TRIM_WIDTH_CM
    MAX_TRIM_HEIGHT_CM = MAX_TRIM_HEIGHT_CM

    # Defaults (cm): CON-018's Book 1 print profile (CARD-115) — US Letter,
    # 8.5 × 11 in, gutter 0.5 in, outside 0.5 in (0.375 in until the
    # 2026-10-17 amendment, CARD-222). Read from BOOK1_PROFILE, never
    # restated here.
    DEFAULT_TRIM_WIDTH_CM = BOOK1_PROFILE.trim_width_cm
    DEFAULT_TRIM_HEIGHT_CM = BOOK1_PROFILE.trim_height_cm
    DEFAULT_GUTTER_MARGIN_CM = BOOK1_PROFILE.gutter_margin_cm
    DEFAULT_OUTSIDE_MARGIN_CM = BOOK1_PROFILE.outside_margin_cm

    #: CARD-147: a book nobody has chosen an interior ink mode for is
    #: black-and-white. Read from book_page_spec, never restated here.
    DEFAULT_INTERIOR_INK_MODE = DEFAULT_INK_MODE.value

    @staticmethod
    def cm_to_inches(cm: str) -> str:
        """Convert centimeters to inches (1 in = 2.54 cm).

        Args:
            cm: Value in centimeters (as string)

        Returns:
            Value in inches (as string, rounded to 2 decimals)

        Raises:
            ValueError: If input is not a valid number
        """
        try:
            cm_float = float(cm)
            inches = cm_float / 2.54
            return f"{inches:.2f}"
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid centimeter value: {cm}") from e

    @staticmethod
    def inches_to_cm(inches: str) -> str:
        """Convert inches to centimeters (1 in = 2.54 cm).

        Args:
            inches: Value in inches (as string)

        Returns:
            Value in centimeters (as string, rounded to 2 decimals)

        Raises:
            ValueError: If input is not a valid number
        """
        try:
            inches_float = float(inches)
            cm = inches_float * 2.54
            return f"{cm:.2f}"
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid inch value: {inches}") from e

    @staticmethod
    def trim_limits() -> TrimLimits:
        """The one statement of the trim limits Print setup shows and refuses with."""
        return TrimLimits(
            min_cm=PrintSpecValidator.MIN_TRIM_CM,
            max_width_cm=PrintSpecValidator.MAX_TRIM_WIDTH_CM,
            max_height_cm=PrintSpecValidator.MAX_TRIM_HEIGHT_CM,
            min_in=_inches_inward(PrintSpecValidator.MIN_TRIM_CM, ROUND_CEILING),
            max_width_in=_inches_inward(PrintSpecValidator.MAX_TRIM_WIDTH_CM, ROUND_FLOOR),
            max_height_in=_inches_inward(PrintSpecValidator.MAX_TRIM_HEIGHT_CM, ROUND_FLOOR),
        )

    @staticmethod
    def trim_inches_shown(cm: str, axis: Literal["width", "height"]) -> str:
        """The inch figure Print setup shows for one stored trim side (CARD-178).

        ``cm_to_inches(cm)``, except for a stored value at or inside ``axis``'s
        cm limits whose nearest-hundredth figure lies outside the matching
        :meth:`trim_limits` inch figure: that limit figure is shown instead.
        On KDP's bounds this changes one value, 48.00 cm high, from 18.90 in
        to the 18.89 in the Limits box states. A stored value outside the cm
        limits keeps the plain ``cm_to_inches`` figure, so a bad stored trim is
        not shown as a valid one.

        Raises:
            ValueError: As ``cm_to_inches``, for a value that is not a number.
        """
        shown = PrintSpecValidator.cm_to_inches(cm)
        limits = PrintSpecValidator.trim_limits()
        max_cm, max_in = {
            "width": (limits.max_width_cm, limits.max_width_in),
            "height": (limits.max_height_cm, limits.max_height_in),
        }[axis]
        if not limits.min_cm <= float(cm) <= max_cm:
            return shown
        if Decimal(shown) > Decimal(max_in):
            return max_in
        if Decimal(shown) < Decimal(limits.min_in):
            return limits.min_in
        return shown

    @staticmethod
    def validate_interior_ink_mode(mode: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Validate one submitted interior ink mode (CARD-147).

        ``None`` and the empty string are valid and mean "the caller named
        none": :meth:`create_spec` fills them with
        :data:`DEFAULT_INTERIOR_INK_MODE`. Anything else must be one of
        :class:`~nonogram.admin.book_page_spec.InkMode`'s two values, because
        a value the reader would then refuse must never reach the column
        (the posture ``BookManager.set_print_spec`` takes for the trim).

        Returns:
            Tuple of (is_valid, error_message).
        """
        if mode is None or (isinstance(mode, str) and not mode.strip()):
            return True, None
        if not isinstance(mode, str):
            return False, "Interior ink mode must be text"
        if mode.strip().lower() not in {member.value for member in InkMode}:
            offered = " or ".join(f"'{member.value}'" for member in InkMode)
            return False, f"Interior ink mode must be {offered}, not '{mode}'"
        return True, None

    @staticmethod
    def validate_player_domain(domain: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Validate one submitted player domain (CARD-332, AC-1).

        ``None`` and a blank string are valid. They are **not** the same
        thing, and only the caller can tell them apart: ``None`` is "the
        submission did not carry the field" (leave the stored value alone) and
        ``""`` is "the owner cleared it" (store no domain). Neither is a
        refusal, so neither is this method's business — see
        :attr:`PrintSpec.player_domain`.

        Anything else must be an absolute ``https://`` origin: the scheme,
        a host name, an optional port, and nothing after it. A path, a query,
        a fragment, credentials, a space, a bare host or an ``http://`` base
        are all refused, because the stored value is joined to ``/play/<key>``
        and printed into a book: a base that is wrong is wrong in every copy
        and cannot be corrected after the run.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if domain is None or (isinstance(domain, str) and not domain.strip()):
            return True, None
        if not isinstance(domain, str):
            return False, "Player domain must be text"

        text = domain.strip()
        if not text.lower().startswith(PLAYER_DOMAIN_SCHEME):
            return (
                False,
                f"Player domain must start with {PLAYER_DOMAIN_SCHEME} and name the "
                f"player's address, like https://nonogram.adverax.io — not '{text}'",
            )

        rest = text[len(PLAYER_DOMAIN_SCHEME):]
        # One trailing slash is the shape a browser's address bar hands over,
        # so it is accepted and dropped rather than refused; a second slash,
        # or anything after it, is a path and is not a base.
        if rest.endswith("/"):
            rest = rest[:-1]
        match = _PLAYER_ORIGIN.fullmatch(rest)
        if not match:
            return (
                False,
                f"Player domain must be {PLAYER_DOMAIN_SCHEME} followed by a host name "
                "and an optional port, with nothing after it — no path, query, "
                f"fragment, credentials or spaces: '{text}'",
            )
        port = match.group("port")
        if port is not None and not 1 <= int(port) <= _MAX_PORT:
            return (
                False,
                f"Player domain's port must be between 1 and {_MAX_PORT}: '{text}'",
            )
        return True, None

    @staticmethod
    def player_domain_as_stored(domain: Optional[str]) -> Optional[str]:
        """``domain`` in the one form the column holds (CARD-332).

        The scheme and host lower-cased (a host name is case-insensitive and
        two spellings of one domain must not become two stored bases), the
        port as typed, and no trailing slash — so ``{base}/play/{key}`` is one
        join with exactly one slash in it, wherever the base came from.

        ``None`` for both "named none" and "cleared": the caller has already
        told those apart (:attr:`PrintSpec.player_domain`), and from here on
        they are one column value.

        Raises:
            ValueError: ``domain`` is a value
                :meth:`validate_player_domain` refuses. Normalising is not a
                second verdict and has no way to express one, so it refuses
                rather than returning something plausible: a base nobody
                checked is exactly what must not reach a printed book.
        """
        if domain is None or not str(domain).strip():
            return None
        is_valid, refusal = PrintSpecValidator.validate_player_domain(domain)
        if not is_valid:
            raise ValueError(refusal)
        text = str(domain).strip()
        rest = text[len(PLAYER_DOMAIN_SCHEME):]
        if rest.endswith("/"):
            rest = rest[:-1]
        match = _PLAYER_ORIGIN.fullmatch(rest)
        host = match.group("host").lower()
        port = match.group("port")
        return f"{PLAYER_DOMAIN_SCHEME}{host}" + (f":{port}" if port else "")

    @staticmethod
    def validate_trim_size(
        width_cm: str,
        height_cm: str,
        *,
        entered_inches: Optional[Tuple[str, str]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate trim size bounds.

        The verdict is always made on the cm values. Only the wording of a
        bound refusal depends on ``entered_inches``.

        Args:
            width_cm: Trim width in cm
            height_cm: Trim height in cm
            entered_inches: The (width, height) the owner typed, when they
                typed inches (CARD-174). A bound refusal then states the limit
                in inches (:meth:`trim_limits`) and quotes the failing entry.
                ``None`` (the default) keeps the cm wording.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            width = float(width_cm)
            height = float(height_cm)
        except (ValueError, TypeError):
            return False, "Trim size must be numeric values"

        # CARD-154: "nan" fails every comparison below, so it would pass both
        # bounds; "inf" and "1e999" parse too. None of them is a measurement,
        # so they earn the same refusal as "abc" — before anything is stored.
        if not (math.isfinite(width) and math.isfinite(height)):
            return False, "Trim size must be numeric values"

        # The verdict is made here, once, by these three comparisons on the cm
        # values. ``entered_inches`` only chooses the wording of the branch
        # that failed (CARD-174 review F-001: no second set of comparisons).
        inches = (
            None
            if entered_inches is None
            else tuple(str(value).strip() for value in entered_inches)
        )

        # Check minimums
        width_too_small = width < PrintSpecValidator.MIN_TRIM_CM
        height_too_small = height < PrintSpecValidator.MIN_TRIM_CM
        if width_too_small or height_too_small:
            if inches is None:
                return (
                    False,
                    f"Trim size must be at least {PrintSpecValidator.MIN_TRIM_CM} cm in both dimensions",
                )
            return False, PrintSpecValidator._inch_min_refusal(
                inches, width_too_small, height_too_small
            )

        # Check maximums
        if width > PrintSpecValidator.MAX_TRIM_WIDTH_CM:
            if inches is None:
                return (
                    False,
                    f"Trim width cannot exceed {PrintSpecValidator.MAX_TRIM_WIDTH_CM} cm (Amazon KDP limit)",
                )
            return (
                False,
                f"Trim width cannot exceed {PrintSpecValidator.trim_limits().max_width_in} in "
                f"(Amazon KDP limit); you entered {inches[0]} in",
            )

        if height > PrintSpecValidator.MAX_TRIM_HEIGHT_CM:
            if inches is None:
                return (
                    False,
                    f"Trim height cannot exceed {PrintSpecValidator.MAX_TRIM_HEIGHT_CM} cm (Amazon KDP limit)",
                )
            return (
                False,
                f"Trim height cannot exceed {PrintSpecValidator.trim_limits().max_height_in} in "
                f"(Amazon KDP limit); you entered {inches[1]} in",
            )

        return True, None

    @staticmethod
    def _inch_min_refusal(
        inches: Tuple[str, str], width_too_small: bool, height_too_small: bool
    ) -> str:
        """The minimum refusal worded in inches, quoting only the side(s) that failed.

        Wording only: which sides failed is decided by the caller's cm
        comparisons. ``inches`` is the (width, height) as typed, stripped.
        """
        too_small = [
            f"{entry} in for the {label}"
            for label, entry, failed in (
                ("width", inches[0], width_too_small),
                ("height", inches[1], height_too_small),
            )
            if failed
        ]
        return (
            f"Trim size must be at least {PrintSpecValidator.trim_limits().min_in} in on both sides; "
            f"you entered {' and '.join(too_small)}"
        )

    @staticmethod
    def validate_margins(
        gutter_margin_cm: Optional[str],
        outside_margin_cm: Optional[str],
        outside_margin_bleed_cm: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate that each given margin is a finite number of cm (CARD-154).

        ``None`` and the empty string are "the caller named none" and are
        valid (:meth:`create_spec` fills the gutter and outside margins with
        the profile's). Anything else must parse to a finite number:
        ``"nan"``, ``"inf"`` and ``"1e999"`` are refused like ``"abc"``. The
        side-margin minimum is not restated here — it is
        :func:`~nonogram.admin.book_page_spec.book_page_spec`'s verdict on a
        stored margin, which already refuses a non-finite one on the way out.

        Returns:
            Tuple of (is_valid, error_message).
        """
        for label, value in (
            ("Gutter margin", gutter_margin_cm),
            ("Outside margin", outside_margin_cm),
            ("Outside margin with bleed", outside_margin_bleed_cm),
        ):
            if value is None or (isinstance(value, str) and not value.strip()):
                continue
            try:
                number = float(value)
            except (ValueError, TypeError):
                return False, f"{label} must be a numeric value"
            if not math.isfinite(number):
                return False, f"{label} must be a numeric value"
        return True, None

    @staticmethod
    def create_spec(
        width_cm: Optional[str] = None,
        height_cm: Optional[str] = None,
        gutter_margin_cm: Optional[str] = None,
        outside_margin_cm: Optional[str] = None,
        outside_margin_bleed_cm: Optional[str] = None,
        interior_ink_mode: Optional[str] = None,
        *,
        entered_inches: Optional[Tuple[str, str]] = None,
        interior_divider_pages: Optional[bool] = None,
        player_domain: Optional[str] = None,
    ) -> Tuple[Optional[PrintSpec], Optional[str]]:
        """Create a print spec with validation.

        Args:
            width_cm: Trim width in cm (defaults to 8.5 in, 21.59 cm)
            height_cm: Trim height in cm (defaults to 11 in, 27.94 cm)
            gutter_margin_cm: Inside gutter margin in cm (defaults to 0.5 in, 1.27 cm)
            outside_margin_cm: Outside margin in cm (defaults to 0.5 in, 1.27 cm)
            outside_margin_bleed_cm: Outside margin with bleed in cm (optional)
            interior_ink_mode: How the interior is printed (CARD-147) —
                ``'bw'`` or ``'colour'``; defaults to black-and-white, which is
                what every book that exists today is in content.
            entered_inches: The (width, height) the owner typed in inches, if
                they did; passed to :meth:`validate_trim_size` so a bound
                refusal is worded in inches (CARD-174). Defaults to cm wording.
            interior_divider_pages: Whether the interior prints its four
                divider pages (CARD-305), or ``None`` for "the caller named
                none", which carries through to the spec and leaves the
                stored choice unchanged. Unlike the ink mode this is **not**
                defaulted here: a form that omits the field must not be read
                as "turn them off", and the book's own stored value is the
                only thing that may answer for it.
            player_domain: The base of the public player (CARD-332), or
                ``None`` for "the caller named none", which leaves the stored
                value unchanged, or ``""`` for "the owner cleared it", which
                stores no domain. Like ``interior_divider_pages`` it is
                **not** defaulted here: there is no base a book can be given
                that nobody chose, and inventing one is how a wrong domain
                gets printed.

        Returns:
            Tuple of (PrintSpec or None, error_message or None)
        """
        # Use defaults if not provided
        width_cm = width_cm or PrintSpecValidator.DEFAULT_TRIM_WIDTH_CM
        height_cm = height_cm or PrintSpecValidator.DEFAULT_TRIM_HEIGHT_CM
        gutter_margin_cm = gutter_margin_cm or PrintSpecValidator.DEFAULT_GUTTER_MARGIN_CM
        outside_margin_cm = outside_margin_cm or PrintSpecValidator.DEFAULT_OUTSIDE_MARGIN_CM

        # Validate trim size
        is_valid, error = PrintSpecValidator.validate_trim_size(
            width_cm, height_cm, entered_inches=entered_inches
        )
        if not is_valid:
            return None, error

        # CARD-154: and the margins, which until now were not checked at all,
        # so "nan" or "inf" went into the spec as given.
        is_valid, error = PrintSpecValidator.validate_margins(
            gutter_margin_cm, outside_margin_cm, outside_margin_bleed_cm
        )
        if not is_valid:
            return None, error

        # CARD-147: and the interior's ink mode, before anything is built, so
        # a spec never carries a value the storage boundary would refuse.
        is_valid, error = PrintSpecValidator.validate_interior_ink_mode(interior_ink_mode)
        if not is_valid:
            return None, error
        ink_mode = (interior_ink_mode or "").strip().lower() or (
            PrintSpecValidator.DEFAULT_INTERIOR_INK_MODE
        )

        # CARD-332: and the player domain, for the same reason — a value the
        # column's reader would refuse must not reach it. The verdict is made
        # here; the normalisation below is what the column holds.
        is_valid, error = PrintSpecValidator.validate_player_domain(player_domain)
        if not is_valid:
            return None, error

        spec = PrintSpec(
            trim_width_cm=f"{float(width_cm):.2f}",
            trim_height_cm=f"{float(height_cm):.2f}",
            gutter_margin_cm=gutter_margin_cm,
            outside_margin_cm=outside_margin_cm,
            outside_margin_bleed_cm=outside_margin_bleed_cm,
            interior_ink_mode=ink_mode,
            # CARD-305: carried through as given, including ``None``. There is
            # deliberately no default: see the ``Args`` note above.
            interior_divider_pages=(
                None
                if interior_divider_pages is None
                else bool(interior_divider_pages)
            ),
            # CARD-332: ``None`` ("named none") is carried through as given,
            # and so is ``""`` ("cleared") — the two are told apart by the
            # storage boundary, not here. A real base is normalised, so the
            # column holds one spelling of one domain.
            player_domain=(
                None
                if player_domain is None
                else (
                    PrintSpecValidator.player_domain_as_stored(player_domain) or ""
                )
            ),
        )

        return spec, None

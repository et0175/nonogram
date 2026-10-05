"""Print specification service for book scaffolding.

Handles validation, conversion, and storage of print parameters for book PDFs.

Since CARD-147 a print specification also carries **how the interior is
printed** — black-and-white or colour (:class:`~nonogram.admin.book_page_spec.InkMode`)
— because it is the same kind of fact as the trim: something the owner chooses
on Print setup, stores on the book, and the export obeys. Carrying it here is
what lets one submission of that form store the trim and the mode in one write,
so a refused plan stores neither (AC-197's posture, extended to the mode).
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple
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

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "trim_width_cm": self.trim_width_cm,
            "trim_height_cm": self.trim_height_cm,
            "gutter_margin_cm": self.gutter_margin_cm,
            "outside_margin_cm": self.outside_margin_cm,
            "outside_margin_bleed_cm": self.outside_margin_bleed_cm,
            "interior_ink_mode": self.interior_ink_mode,
        }


@dataclass(frozen=True)
class TrimLimits:
    """KDP's trim bounds in cm, and in the inches that are always accepted (CARD-174).

    The cm figures are ``book_page_spec``'s constants as they are. Each inch
    figure is the cm bound divided by 2.54 and cut to two decimals **inward**
    — a maximum rounded down, the minimum rounded up — so that typing the
    stated figure back in passes :meth:`PrintSpecValidator.validate_trim_size`
    (48 cm is 18.898 in: 18.90 in would convert to 48.01 cm and be refused,
    18.89 in converts to 47.98 cm). The inch refusals and Print setup's
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
    # 8.5 × 11 in, gutter 0.5 in, outside 0.375 in. Read from BOOK1_PROFILE,
    # never restated here.
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

        if entered_inches is not None:
            return PrintSpecValidator._inch_bounds_verdict(
                width, height, *(str(value).strip() for value in entered_inches)
            )

        # Check minimums
        if width < PrintSpecValidator.MIN_TRIM_CM or height < PrintSpecValidator.MIN_TRIM_CM:
            return (
                False,
                f"Trim size must be at least {PrintSpecValidator.MIN_TRIM_CM} cm in both dimensions",
            )

        # Check maximums
        if width > PrintSpecValidator.MAX_TRIM_WIDTH_CM:
            return (
                False,
                f"Trim width cannot exceed {PrintSpecValidator.MAX_TRIM_WIDTH_CM} cm (Amazon KDP limit)",
            )

        if height > PrintSpecValidator.MAX_TRIM_HEIGHT_CM:
            return (
                False,
                f"Trim height cannot exceed {PrintSpecValidator.MAX_TRIM_HEIGHT_CM} cm (Amazon KDP limit)",
            )

        return True, None

    @staticmethod
    def _inch_bounds_verdict(
        width: float, height: float, width_in: str, height_in: str
    ) -> Tuple[bool, Optional[str]]:
        """The bound checks of :meth:`validate_trim_size`, worded in inches.

        Same comparisons, same order, on the same cm values; only the message
        differs. ``width_in``/``height_in`` are the entries as typed, stripped.
        """
        limits = PrintSpecValidator.trim_limits()

        too_small = [
            f"{entry} in for the {label}"
            for label, value, entry in (("width", width, width_in), ("height", height, height_in))
            if value < limits.min_cm
        ]
        if too_small:
            return (
                False,
                f"Trim size must be at least {limits.min_in} in on both sides; "
                f"you entered {' and '.join(too_small)}",
            )

        if width > limits.max_width_cm:
            return (
                False,
                f"Trim width cannot exceed {limits.max_width_in} in (Amazon KDP limit); "
                f"you entered {width_in} in",
            )

        if height > limits.max_height_cm:
            return (
                False,
                f"Trim height cannot exceed {limits.max_height_in} in (Amazon KDP limit); "
                f"you entered {height_in} in",
            )

        return True, None

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
    ) -> Tuple[Optional[PrintSpec], Optional[str]]:
        """Create a print spec with validation.

        Args:
            width_cm: Trim width in cm (defaults to 8.5 in, 21.59 cm)
            height_cm: Trim height in cm (defaults to 11 in, 27.94 cm)
            gutter_margin_cm: Inside gutter margin in cm (defaults to 0.5 in, 1.27 cm)
            outside_margin_cm: Outside margin in cm (defaults to 0.375 in, 0.95 cm)
            outside_margin_bleed_cm: Outside margin with bleed in cm (optional)
            interior_ink_mode: How the interior is printed (CARD-147) —
                ``'bw'`` or ``'colour'``; defaults to black-and-white, which is
                what every book that exists today is in content.
            entered_inches: The (width, height) the owner typed in inches, if
                they did; passed to :meth:`validate_trim_size` so a bound
                refusal is worded in inches (CARD-174). Defaults to cm wording.

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

        spec = PrintSpec(
            trim_width_cm=f"{float(width_cm):.2f}",
            trim_height_cm=f"{float(height_cm):.2f}",
            gutter_margin_cm=gutter_margin_cm,
            outside_margin_cm=outside_margin_cm,
            outside_margin_bleed_cm=outside_margin_bleed_cm,
            interior_ink_mode=ink_mode,
        )

        return spec, None

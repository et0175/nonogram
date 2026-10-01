"""Print specification service for book scaffolding.

Handles validation, conversion, and storage of print parameters for book PDFs.

Since CARD-147 a print specification also carries **how the interior is
printed** — black-and-white or colour (:class:`~nonogram.admin.book_page_spec.InkMode`)
— because it is the same kind of fact as the trim: something the owner chooses
on Print setup, stores on the book, and the export obeys. Carrying it here is
what lets one submission of that form store the trim and the mode in one write,
so a refused plan stores neither (AC-197's posture, extended to the mode).
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from decimal import Decimal, InvalidOperation

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
    def validate_trim_size(width_cm: str, height_cm: str) -> Tuple[bool, Optional[str]]:
        """Validate trim size bounds.

        Args:
            width_cm: Trim width in cm
            height_cm: Trim height in cm

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            width = float(width_cm)
            height = float(height_cm)
        except (ValueError, TypeError):
            return False, "Trim size must be numeric values"

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
    def create_spec(
        width_cm: Optional[str] = None,
        height_cm: Optional[str] = None,
        gutter_margin_cm: Optional[str] = None,
        outside_margin_cm: Optional[str] = None,
        outside_margin_bleed_cm: Optional[str] = None,
        interior_ink_mode: Optional[str] = None,
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

        Returns:
            Tuple of (PrintSpec or None, error_message or None)
        """
        # Use defaults if not provided
        width_cm = width_cm or PrintSpecValidator.DEFAULT_TRIM_WIDTH_CM
        height_cm = height_cm or PrintSpecValidator.DEFAULT_TRIM_HEIGHT_CM
        gutter_margin_cm = gutter_margin_cm or PrintSpecValidator.DEFAULT_GUTTER_MARGIN_CM
        outside_margin_cm = outside_margin_cm or PrintSpecValidator.DEFAULT_OUTSIDE_MARGIN_CM

        # Validate trim size
        is_valid, error = PrintSpecValidator.validate_trim_size(width_cm, height_cm)
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

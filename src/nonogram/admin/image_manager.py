"""Image management service for batch image-to-puzzle generation.

Handles image upload, storage, validation, and thumbnail generation.
"""

import os
import uuid
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from nonogram.limits import MAX_SIZE, MIN_SIZE

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None


#: A grid must keep at least this share of the picture's ink bounding box;
#: below it the aspect-preserving crop cuts off the picture's ends, and the
#: batch moves the picture up to Large or skips it (CARD-064). A product
#: choice, not a range bound.
MIN_KEPT_SHARE = 0.9

#: The batch form's size presets, ``name -> (size_value, size_mode)`` — one
#: table for the batch route and for :meth:`ImageFile.size_fit`'s "Large".
SIZE_PRESETS = {
    "small": (10, "short"),  # 10 on the short side; long side follows the picture (CARD-061)
    "medium": (20, "fixed"),
    "large": (30, "fixed"),  # 30 on the long side
    "auto": (20, "max"),
}

#: The modes a size option can be in, in the order the page offers them.
#: One option per mode, so this is also the cap on how many a picture can
#: carry (CARD-069). ``short`` is here because the **small** preset sets it
#: (CARD-061) — the card's first draft listed three modes and would have made
#: a preset's own default unreachable.
SIZE_MODES: tuple = ("fixed", "short", "min", "max")


@dataclass
class SizeOption:
    """One size a picture is to be made at: a mode and, where the mode needs
    one, a number (CARD-069).

    ``min`` and ``max`` carry a value too — the batch preset's — because the
    page keeps the box populated when a user ticks between modes, and because
    ``_own_extent`` has always taken one. It is simply not read for them.
    """

    mode: str
    value: int = 20


#: How each mode is written on the preview page.
SIZE_MODE_LABELS = {
    "fixed": "Fixed size",
    "short": "Short side",
    "min": "Minimum size",
    "max": "Maximum size",
}


@dataclass
class SizeChoice:
    """One of the extra sizes a picture could also be made at, for the page."""

    mode: str
    label: str
    selected: bool
    fit: "SizeFit"


@dataclass
class OptionFit:
    """A size option and what it would produce — :class:`SizeFit` per option."""

    option: SizeOption
    fit: "SizeFit"

    @property
    def mode(self) -> str:
        return self.option.mode

    @property
    def value(self) -> int:
        return self.option.value


FITS = "fits"
MOVED_TO_LARGE = "moved_to_large"
CANNOT_FIT = "cannot_fit"


@dataclass(frozen=True)
class SizeFit:
    """How a picture fits its chosen size (:meth:`ImageFile.size_fit`)."""

    extent: tuple  # the grid to generate: the chosen size's, or Large's
    status: str  # FITS, MOVED_TO_LARGE or CANNOT_FIT
    kept: float  # share of the picture ``extent`` keeps
    chosen: Optional[tuple]  # the chosen size's own grid; None if it has none
    chosen_kept: Optional[float]  # share ``chosen`` keeps; None if no grid


def _kept_share(source: tuple, extent: tuple) -> float:
    """Share of the picture an aspect-preserving crop to ``extent`` keeps.

    Compared as integer cross-products, so a picture and its transpose get
    the same share to the last bit. A ratio of ratios does not: 100x90 at
    10x10 came out 0.8999999999999999 one way and 0.9 the other, flipping
    the status at exactly MIN_KEPT_SHARE.
    """
    a = source[0] * extent[1]
    b = extent[0] * source[1]
    return min(a, b) / max(a, b)


def floor_percent(share: float) -> str:
    """A share as a whole percentage, rounded DOWN: 0.897 → ``"89%"``.

    Rounding to nearest would print "90%" for a grid keeping less than
    MIN_KEPT_SHARE — on a line that only appears *below* it (CARD-065).

    The epsilon absorbs binary floating point, not a real fraction of a
    percent: ``0.58 * 100`` is 57.99999999999999, which would otherwise
    print an exact 58% as "57%".
    """
    return f"{int(share * 100 + 1e-9)}%"


@dataclass
class ImageFile:
    """Represents an uploaded image file."""

    file_id: str
    filename: str
    original_filename: str
    file_path: str  # Temporary storage path
    file_size: int  # Bytes
    dimensions: tuple  # (width, height)
    format: str  # PNG, JPG, GIF
    uploaded_at: datetime
    puzzle_name: str = ""  # Name for generated puzzle (default: filename without ext)
    size_mode: str = "fixed"  # fixed, short, min, max
    size_value: int = 20  # long side for "fixed", short side for "short"
    #: The sizes this picture is to be made at, one per mode, in the order
    #: they were added (CARD-069). One puzzle per option.
    #:
    #: A freshly uploaded picture carries exactly one — the batch preset's —
    #: so a user who never opens the size controls gets the batch they got
    #: before this field existed. ``size_mode``/``size_value`` above remain
    #: the *first* option's, in both directions: every caller that predates
    #: this card keeps working and keeps meaning what it meant.
    size_options: list = field(default_factory=list)

    def __post_init__(self):
        """Set default puzzle name from filename, and the one default option."""
        if not self.puzzle_name:
            # Use filename without extension
            self.puzzle_name = Path(self.original_filename).stem
        if not self.size_options:
            self.size_options = [SizeOption(self.size_mode, self.size_value)]

    def _source_shape(self) -> tuple:
        """The picture's own shape for sizing purposes: its ink bounding box.

        The same extent :mod:`nonogram.sourcing.image` measures the picture by
        (FR-022) and then actually crops to — using the raw file's dimensions
        here, as this used to, can disagree with that box on images with real
        blank margin, e.g. a full-bleed silhouette with a lot of paper around
        it. Falls back to the raw file dimensions if the file can't be
        re-read (e.g. already removed), so this stays a pure computation in
        that case rather than raising out of what used to be one.

        Cached on the instance: callers (``predict_size`` via ``to_dict`` and
        the batch-generation routes) call this several times per request.
        """
        cached = getattr(self, "_cached_source_shape", None)
        if cached is not None:
            return cached
        try:
            from nonogram.sourcing.image import source_shape

            shape = source_shape(self.file_path)
        except Exception:
            shape = self.dimensions
        self._cached_source_shape = shape
        return shape

    def predict_size(self) -> tuple:
        """Predict puzzle (width, height) the way the CLI/web image pipeline
        derives one from a bare ``--size N`` (FR-023, ADR-0022/R4): ``N``
        lands on the picture's own longer axis, the shorter axis follows the
        picture's ratio and is floored at 10 cells — **never capped at 30**.

        Capping the derived axis at the top (this method's previous
        behaviour) silently discards real content once the puzzle is
        actually generated: the aspect-preserving crop then has to fit a
        squarer box than the picture's own shape, cutting into it on the
        long axis — legs, a beak, a tail — exactly the harm ADR-0022/R4
        exists to prevent, and exactly what CLI/web's ``nonogram.sourcing
        .image`` pipeline (which this admin panel's own conversion now
        shares, see :func:`nonogram.admin.image_to_puzzle.image_to_grid`)
        never does.

        The three size modes choose ``N`` differently; all three then share
        the same aspect-fit so a picture is treated identically regardless of
        which mode picked the number:
          * "fixed": ``size_value`` itself.
          * "max": the largest ``N`` that keeps at least 2 source pixels per
            cell (quality), capped at 30.
          * "min": about 5 cells smaller than "max", floored at 10.

        "short" (the batch form's "small" preset, CARD-061) is the exception:
        ``size_value`` is the grid's *short* side and the long side follows
        the picture's ratio, handed on as a full pair — see
        :meth:`_own_extent`.

        When the chosen size would cut the picture, the grid is the Large
        preset's instead (also for a picture that will be skipped) —
        :meth:`size_fit` says which (CARD-064).

        Returns:
            (width, height) tuple
        """
        return self.size_fit().extent

    def ink_ratio(self) -> str:
        """The picture's ink bounding box as a ratio, e.g. ``"1.54:1"``.

        The box, not the file: it is the shape the sizing follows
        (:meth:`_source_shape`, FR-022), so the card explains the predicted
        size instead of contradicting it on a picture with real margin. A
        600x450 sheet carrying a 400x200 drawing is 1.33:1 as a file and
        2.00:1 as a picture, and the second is the one the predicted extent
        comes from.

        Always long side first, so the number reads as "how elongated" rather
        than "which way up" — the orientation is already visible in the
        thumbnail beside it.

        ``"—"`` when the shape is degenerate: an em dash rather than
        ``"0.00:1"``, because there is nothing to measure and saying so is
        more honest than dividing by it.
        """
        source = self._source_shape()
        if min(source) <= 0:
            return "—"
        return f"{max(source) / min(source):.2f}:1"

    def ink_box(self) -> str:
        """The ink bounding box itself, e.g. ``"400×200 px"`` — the ratio's
        working, shown as the card's tooltip so the number can be checked
        rather than taken."""
        source = self._source_shape()
        if min(source) <= 0:
            return "unreadable"
        return f"{source[0]}×{source[1]} px"

    def extra_size_choices(self) -> list:
        """The modes besides this picture's first, for the preview page.

        One entry per *other* mode, each carrying whether it is currently
        ticked, its label, and what it would produce. The first option keeps
        the page's existing mode select and cells box (CARD-069): every
        control that predates this card still means what it meant, and these
        are additions beside it rather than a replacement for it.

        The fit is computed here, server-side, for the same reason the
        prediction partial is: a size rule copied into the browser drifts
        from this one (CARD-063/064's lesson, CARD-067 AC-6).
        """
        primary = self.size_options[0].mode if self.size_options else self.size_mode
        selected = {option.mode: option for option in self.size_options}
        choices = []
        for mode in SIZE_MODES:
            if mode == primary:
                continue
            option = selected.get(mode) or SizeOption(mode, self.size_value)
            choices.append(
                SizeChoice(
                    mode=mode,
                    label=SIZE_MODE_LABELS[mode],
                    selected=mode in selected,
                    fit=self._size_fit_for(option.mode, option.value),
                )
            )
        return choices

    def size_fits(self) -> list:
        """Each option's own :class:`SizeFit` — one entry per size to be made.

        The per-picture :meth:`size_fit` is this list's first entry, and stays
        the answer every caller that predates CARD-069 receives. Nothing here
        re-implements the fit: each option is judged by the same
        :meth:`_size_fit_for` the single-size path uses, so a per-option
        verdict cannot drift from the one the page used to show (G-1).
        """
        return [
            OptionFit(option, self._size_fit_for(option.mode, option.value))
            for option in self.size_options
        ]

    def size_fit(self) -> SizeFit:
        """Whether the chosen size keeps this picture's shape, and what the
        batch does when it doesn't (CARD-064).

        The chosen size's own grid (:meth:`_own_extent`) is used when it keeps
        at least :data:`MIN_KEPT_SHARE` of the picture's ink bounding box.
        Otherwise the picture moves up to the Large preset's grid, if that
        keeps enough, or is skipped (``CANNOT_FIT``). Squeezing is not an
        option: ADR-0022/R3 fits a picture by crop, never by stretching.

        Replaces CARD-058's silent upward search and CARD-061's over-the-cap
        note: every size change, and every skip, is a status the preview and
        the batch results show.
        """
        return self._size_fit_for(self.size_mode, self.size_value)

    def _size_fit_for(self, size_mode: str, size_value: int) -> SizeFit:
        """:meth:`size_fit`'s rule, for one (mode, value) rather than for the
        picture's own. Split out by CARD-069 so that a picture's several
        options share one implementation; the rule itself is untouched."""
        src_width, src_height = self._source_shape()
        if min(src_width, src_height) <= 0:
            # Degenerate shape (CARD-045): no ratio to judge, so the smallest
            # square, with nothing to report.
            square = (MIN_SIZE, MIN_SIZE)
            return SizeFit(square, FITS, 1.0, square, 1.0)

        source = (src_width, src_height)
        chosen = self._own_extent(size_mode, size_value, source)
        chosen_kept = _kept_share(source, chosen) if chosen is not None else None
        if chosen is not None and chosen_kept >= MIN_KEPT_SHARE:
            return SizeFit(chosen, FITS, chosen_kept, chosen, chosen_kept)

        large_value, large_mode = SIZE_PRESETS["large"]
        large = self._own_extent(large_mode, large_value, source)
        if large is None:
            # Beyond N/5:1 even at MAX_SIZE (SizeTooSmallForSource): Large's
            # grid is the longest supported one, and it will not fit.
            large = (MAX_SIZE, MIN_SIZE) if src_width >= src_height else (MIN_SIZE, MAX_SIZE)
        large_kept = _kept_share(source, large)
        status = MOVED_TO_LARGE if large_kept >= MIN_KEPT_SHARE else CANNOT_FIT
        return SizeFit(large, status, large_kept, chosen, chosen_kept)

    def kept_share(self, extent: tuple) -> float:
        """Share of this picture a grid of ``extent`` keeps (1.0 when the
        shape is degenerate and there is nothing to judge)."""
        source = self._source_shape()
        if min(source) <= 0:
            return 1.0
        return _kept_share(source, extent)

    def keeps_enough(self, extent: tuple) -> bool:
        """Whether ``extent`` keeps at least :data:`MIN_KEPT_SHARE` of this
        picture."""
        return self.kept_share(extent) >= MIN_KEPT_SHARE

    def _own_extent(self, mode: str, value: int, source: tuple) -> Optional[tuple]:
        """The grid a size setting asks for on this picture, or ``None`` when
        it has none.

        * "short" (the batch form's "small" preset, CARD-061): ``value`` is
          the grid's short side and the long side follows the picture's
          ratio, as a full pair. A bare ``N`` cannot do this at the bottom of
          the range, because ``derive_extent`` floors the derived side at
          ``MIN_SIZE``, which is also the smallest ``N``. ``None`` when the
          long side would pass ``MAX_SIZE``.
        * "fixed", "max", "min": a bare ``N`` — ``value`` itself; the largest
          ``N`` keeping two source pixels per cell; about 5 less — derived by
          ``derive_extent``. ``None`` when the picture is too elongated for
          that ``N`` (``SizeTooSmallForSource``).

        ``source`` must have positive sides; :meth:`size_fit` handles a
        degenerate one before calling this.
        """
        from nonogram.errors import SizeTooSmallForSource
        from nonogram.sourcing.random_grid import derive_extent

        src_width, src_height = source
        short_edge, long_edge = min(source), max(source)
        if mode == "short":
            short_side = max(MIN_SIZE, min(value, MAX_SIZE))
            long_side = round(short_side * long_edge / short_edge)
            if long_side > MAX_SIZE:
                return None
            if src_width >= src_height:
                return (long_side, short_side)
            return (short_side, long_side)

        if mode == "fixed":
            stated = value
        else:
            quality_cap = min(long_edge // 2, MAX_SIZE)
            stated = quality_cap if mode == "max" else quality_cap - 5
        stated = max(MIN_SIZE, min(stated, MAX_SIZE))
        try:
            return derive_extent(stated, None, src_width, src_height)
        except SizeTooSmallForSource:
            return None

    def neighbour_extents(self, extent: tuple) -> List[tuple]:
        """The extents one cell shorter and one cell longer than ``extent`` on
        its long side, short side unchanged — what the batch retries when
        ``extent`` itself was abandoned (CARD-062).

        Ordered by how much of the picture each keeps (closest to the ink
        bounding box's ratio first; ties go to the smaller extent). A side
        outside ``MIN_SIZE..MAX_SIZE`` drops its candidate, so a 30-long
        extent has only its -1 neighbour.

        A square extent has no long side of its own, so it only moves toward
        the picture's shape: the picture's longer axis grows by one, or its
        shorter axis shrinks by one (width counts as longer for a square
        picture). Moving the other way would turn a landscape picture's grid
        portrait — at 30x30, where only shrinking is possible, that is the
        difference between 30x29 and 29x30.
        """
        from nonogram.sourcing.random_grid import MAX_SIZE, MIN_SIZE

        width, height = extent
        src_width, src_height = self._source_shape()
        if width != height:
            long_is_width = width > height
            moves = [(long_is_width, -1), (long_is_width, 1)]
        else:
            picture_wide = src_width >= src_height
            moves = [(not picture_wide, -1), (picture_wide, 1)]

        candidates = []
        for move_width, delta in moves:
            w, h = (width + delta, height) if move_width else (width, height + delta)
            if MIN_SIZE <= w <= MAX_SIZE and MIN_SIZE <= h <= MAX_SIZE:
                candidates.append((w, h))

        if min(src_width, src_height) <= 0:
            return candidates
        source_ratio = src_width / src_height

        def kept(candidate: tuple) -> float:
            grid_ratio = candidate[0] / candidate[1]
            return min(source_ratio, grid_ratio) / max(source_ratio, grid_ratio)

        return sorted(candidates, key=lambda c: (-kept(c), c[0] * c[1]))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        fit = self.size_fit()
        width, height = fit.extent
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "dimensions": self.dimensions,
            "format": self.format,
            "uploaded_at": self.uploaded_at.isoformat(),
            "puzzle_name": self.puzzle_name,
            "size_mode": self.size_mode,
            "size_value": self.size_value,
            "predicted_width": width,
            "predicted_height": height,
            "size_status": fit.status,
        }


class ImageManager:
    """Manages image upload, storage, and validation for batch generation."""

    # Supported formats
    ALLOWED_FORMATS = {"png", "jpg", "jpeg", "gif"}

    # Max file size: 2MB
    MAX_FILE_SIZE = 2 * 1024 * 1024

    # Max image dimensions
    MAX_DIMENSIONS = 2000

    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize image manager.

        Args:
            temp_dir: Directory for temporary image storage. Defaults to system temp.
        """
        if temp_dir:
            self.temp_dir = Path(temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            import tempfile
            self.temp_dir = Path(tempfile.gettempdir()) / "nonogram_batch_images"
            self.temp_dir.mkdir(parents=True, exist_ok=True)

        # In-memory storage of images during workflow
        self.images: Dict[str, ImageFile] = {}

    def validate_image(self, file_path: str, filename: str) -> tuple[bool, str]:
        """Validate image file.

        Args:
            file_path: Path to the image file
            filename: Original filename

        Returns:
            Tuple of (is_valid, error_message)
        """
        path = Path(file_path)

        # Check file exists
        if not path.exists():
            return False, "File not found"

        # Check file size
        file_size = path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            return False, f"File exceeds 2MB limit ({file_size / 1024 / 1024:.1f}MB)"

        # Check format
        ext = path.suffix.lower().lstrip(".")
        if ext not in self.ALLOWED_FORMATS:
            return False, f"Format not supported. Use: PNG, JPG, GIF"

        # Check dimensions (if PIL available)
        if PILImage:
            try:
                img = PILImage.open(path)
                width, height = img.size
                if width > self.MAX_DIMENSIONS or height > self.MAX_DIMENSIONS:
                    return False, f"Image too large ({width}×{height}). Max: 2000×2000"
            except Exception as e:
                return False, f"Invalid image file: {str(e)}"

        return True, ""

    def add_image(self, file_path: str, filename: str) -> Optional[ImageFile]:
        """Add an image to the batch.

        Args:
            file_path: Path to the image file
            filename: Original filename

        Returns:
            ImageFile object if successful, None otherwise
        """
        # Validate
        is_valid, error = self.validate_image(file_path, filename)
        if not is_valid:
            print(f"Image validation failed: {error}")
            return None

        # Generate unique ID
        file_id = str(uuid.uuid4())[:8]

        # Store file with unique name
        ext = Path(file_path).suffix.lower()
        stored_filename = f"{file_id}{ext}"
        stored_path = self.temp_dir / stored_filename

        try:
            # Copy file to temp storage
            with open(file_path, "rb") as src:
                with open(stored_path, "wb") as dst:
                    dst.write(src.read())

            # Get dimensions
            dimensions = (0, 0)
            if PILImage:
                try:
                    img = PILImage.open(stored_path)
                    dimensions = img.size
                except Exception:
                    pass

            # Create image record
            image = ImageFile(
                file_id=file_id,
                filename=stored_filename,
                original_filename=filename,
                file_path=str(stored_path),
                file_size=Path(stored_path).stat().st_size,
                dimensions=dimensions,
                format=ext.lstrip(".").upper(),
                uploaded_at=datetime.utcnow(),
            )

            # Prime the ink-bounding-box cache now, while this upload
            # request is already paying for one synchronous full decode of
            # this file (the copy above) - not later, inside a per-batch
            # template render loop (CARD-047). _source_shape() never
            # raises (it falls back to `dimensions` on any decode failure),
            # so this can't turn a successful upload into a failed one.
            image._source_shape()

            # Store in memory
            self.images[file_id] = image
            return image

        except Exception as e:
            print(f"Error storing image: {str(e)}")
            return None

    def get_image(self, file_id: str) -> Optional[ImageFile]:
        """Get image by ID."""
        return self.images.get(file_id)

    def get_all_images(self) -> List[ImageFile]:
        """Get all images in current batch."""
        return list(self.images.values())

    def remove_image(self, file_id: str) -> bool:
        """Remove image from batch and delete file.

        Args:
            file_id: Image ID to remove

        Returns:
            True if removed, False if not found
        """
        if file_id not in self.images:
            return False

        image = self.images[file_id]

        # Delete file
        try:
            Path(image.file_path).unlink()
        except Exception:
            pass  # File may have been deleted already

        # Remove from memory
        del self.images[file_id]
        return True

    def clear_all(self) -> None:
        """Clear all images and delete temporary files."""
        for file_id in list(self.images.keys()):
            self.remove_image(file_id)

    def get_total_size(self) -> int:
        """Get total size of all images in bytes."""
        return sum(img.file_size for img in self.images.values())

    def get_total_size_mb(self) -> float:
        """Get total size of all images in MB."""
        return self.get_total_size() / 1024 / 1024

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about current batch."""
        return {
            "count": len(self.images),
            "total_size_bytes": self.get_total_size(),
            "total_size_mb": self.get_total_size_mb(),
            "images": [img.to_dict() for img in self.get_all_images()],
        }

    def update_image_size(self, file_id: str, size_mode: str, size_value: int = 20) -> bool:
        """Update size configuration for an image.

        Args:
            file_id: Image ID
            size_mode: "fixed", "short", "min", or "max"
            size_value: long side for "fixed", short side for "short"
                (MIN_SIZE..MAX_SIZE)

        Returns:
            True if updated, False if not found
        """
        if file_id not in self.images:
            return False

        image = self.images[file_id]
        image.size_mode = size_mode
        if size_mode in ("fixed", "short"):
            # Validate size_value
            if MIN_SIZE <= size_value <= MAX_SIZE:
                image.size_value = size_value
        # The first option is this picture's own size, in both directions
        # (CARD-069): setting it here is what a page that knows nothing about
        # options still does, and it must not leave the list disagreeing.
        image.size_options[0] = SizeOption(image.size_mode, image.size_value)
        return True

    def add_size_option(self, file_id: str, size_mode: str, size_value: int = 20) -> bool:
        """Tick a size for this picture, or change the value of one already on.

        At most one option per mode (AC-5): adding a mode that is already
        there **replaces its value** rather than refusing. The control is a
        tick per mode with its own box, so "fixed 25 when fixed 20 is on" is
        somebody editing a number, and an error would be pedantry.

        Returns:
            ``True`` when the picture now carries that option; ``False`` for
            an unknown picture, an unknown mode, or a value outside the
            supported range for a mode that needs one.
        """
        if file_id not in self.images or size_mode not in SIZE_MODES:
            return False
        if size_mode in ("fixed", "short") and not MIN_SIZE <= size_value <= MAX_SIZE:
            return False

        image = self.images[file_id]
        for existing in image.size_options:
            if existing.mode == size_mode:
                existing.value = size_value
                break
        else:
            image.size_options.append(SizeOption(size_mode, size_value))
        image.size_mode = image.size_options[0].mode
        image.size_value = image.size_options[0].value
        return True

    def remove_size_option(self, file_id: str, size_mode: str) -> bool:
        """Untick a size, unless it is the last one.

        The last is refused (CARD-069's recorded decision): a picture with no
        sizes would contribute nothing to the batch while still sitting on the
        page, and treating the gesture as "remove the picture" would make a
        sizing tweak delete an uploaded file. The Remove button next to it
        does that, explicitly.

        Returns:
            ``True`` when the option was removed; ``False`` for an unknown
            picture, a mode this picture does not carry, or the last option.
        """
        if file_id not in self.images:
            return False

        image = self.images[file_id]
        if len(image.size_options) <= 1:
            return False
        remaining = [o for o in image.size_options if o.mode != size_mode]
        if len(remaining) == len(image.size_options):
            return False

        image.size_options = remaining
        image.size_mode = remaining[0].mode
        image.size_value = remaining[0].value
        return True

    def update_image_name(self, file_id: str, puzzle_name: str) -> bool:
        """Update puzzle name for an image.

        Args:
            file_id: Image ID
            puzzle_name: New puzzle name

        Returns:
            True if updated, False if not found
        """
        if file_id not in self.images:
            return False

        image = self.images[file_id]
        image.puzzle_name = puzzle_name
        return True

    def apply_size_to_all(self, size_mode: str, size_value: int = 20) -> int:
        """Apply same size configuration to all images.

        Args:
            size_mode: "fixed", "short", "min", or "max"
            size_value: long side for "fixed", short side for "short"

        Returns:
            Number of images updated
        """
        count = 0
        for file_id in self.images.keys():
            if self.update_image_size(file_id, size_mode, size_value):
                count += 1
        return count


# Global image manager instance for session
_image_manager = None


def get_image_manager(temp_dir: Optional[str] = None) -> ImageManager:
    """Get the image manager instance."""
    global _image_manager
    if _image_manager is None:
        _image_manager = ImageManager(temp_dir=temp_dir)
    return _image_manager

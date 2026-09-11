"""Image management service for batch image-to-puzzle generation.

Handles image upload, storage, validation, and thumbnail generation.
"""

import os
import uuid
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None


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
    size_mode: str = "fixed"  # fixed, min, max
    size_value: int = 20  # For fixed mode

    def __post_init__(self):
        """Set default puzzle name from filename."""
        if not self.puzzle_name:
            # Use filename without extension
            self.puzzle_name = Path(self.original_filename).stem

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

        Returns:
            (width, height) tuple
        """
        return self._predict_size_detailed()[0]

    def size_substitution(self) -> Optional[Dict[str, int]]:
        """Whether `predict_size()` silently substituted a workable size
        (CARD-058), and if so, what was requested versus what is actually
        used.

        Admin's `SizeTooSmallForSource` handling (see `predict_size()`'s
        docstring) deliberately does the opposite of ADR-0022/R4's CLI-side
        refusal-and-message clause: instead of refusing the request and
        telling the user the smallest `--size N` that would work, it
        silently searches upward for one and uses that. That divergence is
        intentional UX for this interactive, preview-driven workflow (a
        hard refusal would be a dead end requiring the whole batch form to
        be resubmitted) - but leaving it invisible means a user has no way
        to know their puzzle came out at a different size than requested
        short of comparing numbers by eye. This method exposes exactly that
        comparison, without changing what `predict_size()` returns (G-2).

        Returns:
            `None` when no substitution happened (the common case, and the
            degenerate-image `ValueError` fallback - see `predict_size()` -
            which is not itself a substitution). Otherwise
            `{"requested": int, "used": int}`, the longer-side values before
            and after the substitution.
        """
        _, substitution = self._predict_size_detailed()
        return substitution

    def _predict_size_detailed(
        self,
    ) -> tuple[tuple[int, int], Optional[Dict[str, int]]]:
        """Shared implementation behind `predict_size()`/`size_substitution()`
        - computed once so the two can never silently disagree with each
        other the way the ADR-0006/R1 dependency baseline and its own check
        once did (CARD-057).

        Returns:
            `((width, height), substitution_info)` - see `predict_size()`
            and `size_substitution()` for what each half means.
        """
        from nonogram.errors import SizeTooSmallForSource
        from nonogram.sourcing.random_grid import MAX_SIZE, MIN_SIZE, derive_extent

        src_width, src_height = self._source_shape()
        long_edge = max(src_width, src_height)

        if self.size_mode == "fixed":
            stated = self.size_value
        else:
            quality_cap = min(long_edge // 2, MAX_SIZE)
            stated = quality_cap if self.size_mode == "max" else quality_cap - 5
        stated = max(MIN_SIZE, min(stated, MAX_SIZE))

        try:
            return derive_extent(stated, None, src_width, src_height), None
        except SizeTooSmallForSource:
            # The picture is too elongated for `stated` to follow without
            # discarding over half of it (CON-012) - ask for the smallest N
            # that can, rather than surface a CLI-style refusal in this UI.
            for candidate in range(stated, MAX_SIZE + 1):
                try:
                    extent = derive_extent(candidate, None, src_width, src_height)
                    return extent, {"requested": stated, "used": candidate}
                except SizeTooSmallForSource:
                    continue
            extent = (
                (MAX_SIZE, MIN_SIZE) if src_width >= src_height else (MIN_SIZE, MAX_SIZE)
            )
            return extent, {"requested": stated, "used": MAX_SIZE}
        except ValueError:
            # `derive_extent` raises a plain ValueError (not a NonogramError)
            # when the reported source shape has a non-positive axis - a
            # degenerate `_source_shape()`/`dimensions` such as (0, 0) from a
            # failed second decode in `ImageManager.add_image` (CARD-045),
            # not a domain refusal. There is no picture to follow the ratio
            # of, so fall back to the smallest supported square rather than
            # let this propagate into the batch-preview render loops. Not a
            # substitution (there was never a real "requested" N to compare
            # against a degenerate image) - reported as None, not a false
            # positive for `size_substitution()`.
            return (MIN_SIZE, MIN_SIZE), None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        width, height = self.predict_size()
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
            size_mode: "fixed", "min", or "max"
            size_value: Size value for "fixed" mode (10-30)

        Returns:
            True if updated, False if not found
        """
        if file_id not in self.images:
            return False

        image = self.images[file_id]
        image.size_mode = size_mode
        if size_mode == "fixed":
            # Validate size_value
            if 10 <= size_value <= 30:
                image.size_value = size_value
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
            size_mode: "fixed", "min", or "max"
            size_value: Size value for "fixed" mode

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

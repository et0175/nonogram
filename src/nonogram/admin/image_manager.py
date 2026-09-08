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

    def predict_size(self) -> int:
        """Predict puzzle size based on mode and image dimensions."""
        width, height = self.dimensions

        # Min size: smallest readable (constraint: at least 10)
        min_size = 10

        # Max size: largest that preserves quality
        # Rule: at least 2 pixels per cell (pixel_per_cell >= 2)
        max_pixel_per_cell = 2
        max_size = min(
            width // max_pixel_per_cell,
            height // max_pixel_per_cell,
            30,  # Absolute max
        )

        if self.size_mode == "min":
            return max(min_size, max_size - 5)  # Slightly smaller than max
        elif self.size_mode == "max":
            return max_size
        else:  # fixed
            return self.size_value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
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
            "predicted_size": self.predict_size(),
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

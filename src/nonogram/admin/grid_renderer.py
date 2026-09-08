"""Render puzzle grids as SVG for preview and download."""

from typing import List, Tuple
from io import BytesIO


def grid_to_svg(
    grid: List[List[bool]],
    cell_size: int = 20,
    filled_color: str = "#000000",
    empty_color: str = "#ffffff",
    border_color: str = "#cccccc",
) -> str:
    """Convert boolean grid to SVG string.

    Args:
        grid: List[List[bool]] where True = filled cell
        cell_size: Size of each cell in pixels
        filled_color: Color for filled cells (hex)
        empty_color: Color for empty cells (hex)
        border_color: Color for grid borders (hex)

    Returns:
        SVG string ready to display or save
    """
    if not grid or not grid[0]:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0"></svg>'

    height = len(grid)
    width = len(grid[0])

    # Calculate SVG dimensions (add padding for borders)
    svg_width = width * cell_size + 2
    svg_height = height * cell_size + 2

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}">',
        f'<rect width="{svg_width}" height="{svg_height}" fill="{empty_color}"/>',
    ]

    # Draw cells
    for y, row in enumerate(grid):
        for x, filled in enumerate(row):
            rect_x = x * cell_size + 1
            rect_y = y * cell_size + 1

            color = filled_color if filled else empty_color
            svg_parts.append(
                f'<rect x="{rect_x}" y="{rect_y}" width="{cell_size}" height="{cell_size}" '
                f'fill="{color}" stroke="{border_color}" stroke-width="0.5"/>'
            )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def grid_to_svg_bytes(
    grid: List[List[bool]],
    cell_size: int = 20,
) -> bytes:
    """Convert grid to SVG bytes for serving as file download.

    Args:
        grid: List[List[bool]] puzzle grid
        cell_size: Cell size in pixels

    Returns:
        SVG as bytes
    """
    svg_string = grid_to_svg(grid, cell_size=cell_size)
    return svg_string.encode("utf-8")


def get_svg_filename(image_name: str) -> str:
    """Generate SVG filename from image name.

    Args:
        image_name: Original image filename (e.g., "landscape.png")

    Returns:
        SVG filename (e.g., "landscape.svg")
    """
    # Remove extension and add .svg
    base_name = image_name.rsplit(".", 1)[0] if "." in image_name else image_name
    return f"{base_name}.svg"

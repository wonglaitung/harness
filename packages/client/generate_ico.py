#!/usr/bin/env python
"""
Generate Windows ICO file from SVG icon.

Usage:
    python generate_ico.py
"""

from pathlib import Path

import cairosvg
from PIL import Image


def svg_to_ico(svg_path: Path, ico_path: Path, sizes: list[int] | None = None):
    """Convert SVG to multi-size ICO file.

    Args:
        svg_path: Path to input SVG file
        ico_path: Path to output ICO file
        sizes: List of icon sizes (default: 16, 24, 32, 48, 64, 128, 256)
    """
    if sizes is None:
        sizes = [16, 24, 32, 48, 64, 128, 256]

    # Generate PNG at largest size (256x256)
    png_bytes = cairosvg.svg2png(
        url=str(svg_path),
        output_width=256,
        output_height=256,
    )

    # Load the PNG
    base_image = Image.open(__import__("io").BytesIO(png_bytes))

    # Create list of images at different sizes
    images = []
    for size in sizes:
        if size <= 256:
            resized = base_image.resize((size, size), Image.Resampling.LANCZOS)
            images.append(resized)

    # Save as ICO with multiple sizes
    base_image.save(
        ico_path,
        format="ICO",
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:],
    )
    print(f"Generated: {ico_path} (sizes: {sizes})")


def main():
    script_dir = Path(__file__).parent
    svg_path = script_dir / "resources" / "icons" / "icon.svg"
    ico_path = script_dir / "resources" / "icons" / "app.ico"

    if not svg_path.exists():
        print(f"Error: SVG file not found: {svg_path}")
        return 1

    svg_to_ico(svg_path, ico_path)
    return 0


if __name__ == "__main__":
    exit(main())

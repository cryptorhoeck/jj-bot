#!/usr/bin/env python3
"""Generate PWA icons for JJ-Bot Dashboard"""

import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "Pillow"])
    from PIL import Image, ImageDraw, ImageFont

# Icon sizes needed for PWA
SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

# Colors
BG_COLOR = "#1a1a2e"  # Dark background
PRIMARY_COLOR = "#4f46e5"  # Indigo
ACCENT_COLOR = "#22c55e"  # Green for the chart line
TEXT_COLOR = "#ffffff"

def create_icon(size: int, output_path: Path):
    """Create a single icon at the specified size"""
    # Create image with background
    img = Image.new('RGBA', (size, size), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw a stylized "JJ" with a chart line
    padding = size // 8
    center = size // 2

    # Draw circular background
    circle_radius = size // 2 - padding
    draw.ellipse(
        [center - circle_radius, center - circle_radius,
         center + circle_radius, center + circle_radius],
        fill=PRIMARY_COLOR
    )

    # Draw a simple chart line (upward trend)
    chart_points = [
        (padding * 2, size - padding * 3),
        (center - padding // 2, center + padding),
        (center + padding // 2, center - padding),
        (size - padding * 2, padding * 2.5)
    ]

    # Scale points
    line_width = max(2, size // 32)
    draw.line(chart_points, fill=ACCENT_COLOR, width=line_width)

    # Draw dots at chart points
    dot_radius = max(2, size // 48)
    for point in chart_points:
        draw.ellipse(
            [point[0] - dot_radius, point[1] - dot_radius,
             point[0] + dot_radius, point[1] + dot_radius],
            fill=ACCENT_COLOR
        )

    # Try to add "JJ" text
    try:
        font_size = size // 3
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("Arial Bold", font_size)
            except:
                font = ImageFont.load_default()

        text = "JJ"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = (size - text_width) // 2
        text_y = (size - text_height) // 2 + size // 10

        draw.text((text_x, text_y), text, fill=TEXT_COLOR, font=font)
    except Exception as e:
        # If font fails, just use the chart icon
        pass

    # Save
    img.save(output_path, 'PNG')
    print(f"Created: {output_path}")

def main():
    script_dir = Path(__file__).parent.parent
    icons_dir = script_dir / "public" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    print("Generating PWA icons...")
    for size in SIZES:
        output_path = icons_dir / f"icon-{size}.png"
        create_icon(size, output_path)

    # Also create favicon
    favicon_path = script_dir / "public" / "favicon.ico"
    img = Image.new('RGBA', (32, 32), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Simple favicon with circle and line
    draw.ellipse([2, 2, 30, 30], fill=PRIMARY_COLOR)
    draw.line([(6, 22), (14, 14), (18, 18), (26, 8)], fill=ACCENT_COLOR, width=2)

    img.save(favicon_path, 'ICO')
    print(f"Created: {favicon_path}")

    print("\nDone! Icons generated successfully.")

if __name__ == "__main__":
    main()

"""
Generate JJ-Bot gorilla icon
Creates a professional gorilla side-profile icon for the application
"""
from PIL import Image, ImageDraw
from pathlib import Path
import math

PROJECT_ROOT = Path(__file__).parent


def draw_gorilla_icon(size):
    """Draw a stylized gorilla side profile icon"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Scale factor
    s = size / 256

    # Draw circular gradient background (blue to purple)
    cx, cy = size // 2, size // 2
    radius = size // 2 - 1

    for y in range(size):
        for x in range(size):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist <= radius:
                # Gradient from blue (59, 130, 246) to purple (139, 92, 246)
                t = (x + y) / (2 * size)
                r = int(59 + (139 - 59) * t)
                g = int(130 + (92 - 130) * t)
                b = 246
                img.putpixel((x, y), (r, g, b, 255))

    if size >= 32:
        # Draw gorilla silhouette in white
        white = (255, 255, 255, 255)
        light_gray = (220, 220, 220, 255)
        dark = (30, 30, 46, 255)

        # Main head shape - ellipse tilted forward
        head_cx = int(125 * s)
        head_cy = int(115 * s)
        head_rx = int(55 * s)
        head_ry = int(60 * s)

        # Draw head
        draw.ellipse([head_cx - head_rx, head_cy - head_ry,
                     head_cx + head_rx, head_cy + head_ry], fill=white)

        # Prominent brow ridge
        brow_y = int(85 * s)
        draw.ellipse([int(85 * s), brow_y - int(15*s),
                     int(165 * s), brow_y + int(15*s)], fill=light_gray)

        # Snout/muzzle protruding forward
        snout_x = int(155 * s)
        snout_y = int(130 * s)
        draw.ellipse([snout_x - int(25*s), snout_y - int(20*s),
                     snout_x + int(25*s), snout_y + int(20*s)], fill=white)

        # Ear on the left side
        ear_x = int(75 * s)
        ear_y = int(100 * s)
        draw.ellipse([ear_x - int(12*s), ear_y - int(18*s),
                     ear_x + int(12*s), ear_y + int(18*s)], fill=light_gray)

        # Eye - positioned under brow
        if size >= 48:
            eye_x = int(130 * s)
            eye_y = int(105 * s)
            eye_r = max(int(8 * s), 2)
            draw.ellipse([eye_x - eye_r, eye_y - eye_r,
                         eye_x + eye_r, eye_y + eye_r], fill=dark)
            # Eye highlight
            highlight_r = max(int(3 * s), 1)
            draw.ellipse([eye_x + int(2*s) - highlight_r, eye_y - int(2*s) - highlight_r,
                         eye_x + int(2*s) + highlight_r, eye_y - int(2*s) + highlight_r],
                        fill=(255, 255, 255, 200))

        # Nostril
        if size >= 48:
            nostril_x = int(168 * s)
            nostril_y = int(130 * s)
            nostril_r = max(int(4 * s), 1)
            draw.ellipse([nostril_x - nostril_r, nostril_y - int(6*s),
                         nostril_x + nostril_r, nostril_y + int(6*s)], fill=dark)

        # Shoulder/neck area
        shoulder_points = [
            (int(80 * s), int(175 * s)),
            (int(70 * s), int(200 * s)),
            (int(65 * s), int(230 * s)),
            (int(190 * s), int(230 * s)),
            (int(180 * s), int(200 * s)),
            (int(160 * s), int(175 * s)),
        ]
        if size >= 64:
            draw.polygon(shoulder_points, fill=(255, 255, 255, 180))

        # Subtle chart line (trading theme)
        if size >= 64:
            chart_points = [
                (int(35 * s), int(195 * s)),
                (int(75 * s), int(175 * s)),
                (int(115 * s), int(185 * s)),
                (int(155 * s), int(155 * s)),
                (int(195 * s), int(165 * s)),
                (int(225 * s), int(135 * s)),
            ]
            line_width = max(int(3 * s), 1)
            for i in range(len(chart_points) - 1):
                draw.line([chart_points[i], chart_points[i + 1]],
                         fill=(255, 255, 255, 80), width=line_width)

    return img


def main():
    print("Generating JJ-Bot gorilla icon...")

    # Generate icons at multiple sizes
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        print(f"  Creating {size}x{size}...")
        img = draw_gorilla_icon(size)
        images.append(img)

    # Save as ICO
    ico_path = PROJECT_ROOT / "assets" / "jjbot.ico"
    ico_path.parent.mkdir(parents=True, exist_ok=True)

    images[-1].save(
        str(ico_path),
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1]
    )

    print(f"\nIcon saved to: {ico_path}")

    # Also save a PNG preview
    png_path = PROJECT_ROOT / "assets" / "jjbot_icon.png"
    images[-1].save(str(png_path), format='PNG')
    print(f"PNG preview saved to: {png_path}")

    print("\nDone! Now run create_shortcut.bat to create the desktop shortcut.")


if __name__ == "__main__":
    main()

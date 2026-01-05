"""
Create JJ-Bot desktop shortcut with gorilla icon
Run this script once to create the shortcut and icon
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

def create_ico_from_svg():
    """Convert SVG to ICO using available libraries"""
    svg_path = PROJECT_ROOT / "assets" / "gorilla.svg"
    ico_path = PROJECT_ROOT / "assets" / "jjbot.ico"

    # Try using cairosvg + Pillow
    try:
        import cairosvg
        from PIL import Image
        from io import BytesIO

        # Convert SVG to PNG at multiple sizes
        sizes = [16, 32, 48, 64, 128, 256]
        images = []

        for size in sizes:
            png_data = cairosvg.svg2png(url=str(svg_path), output_width=size, output_height=size)
            img = Image.open(BytesIO(png_data))
            # Convert to RGBA if needed
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            images.append(img)

        # Save as ICO with multiple sizes
        images[0].save(
            str(ico_path),
            format='ICO',
            sizes=[(s, s) for s in sizes],
            append_images=images[1:]
        )
        print(f"Created icon: {ico_path}")
        return True

    except ImportError:
        print("cairosvg not available, trying alternative method...")

    # Fallback: Create a simple colored icon using just Pillow
    try:
        from PIL import Image, ImageDraw

        sizes = [16, 32, 48, 64, 128, 256]
        images = []

        for size in sizes:
            # Create gradient background
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Draw circular gradient background (blue to purple)
            for i in range(size):
                for j in range(size):
                    # Check if inside circle
                    cx, cy = size // 2, size // 2
                    r = size // 2 - 2
                    dist = ((i - cx) ** 2 + (j - cy) ** 2) ** 0.5
                    if dist <= r:
                        # Gradient from blue (59, 130, 246) to purple (139, 92, 246)
                        t = (i + j) / (2 * size)
                        red = int(59 + (139 - 59) * t)
                        green = int(130 + (92 - 130) * t)
                        blue = int(246)
                        img.putpixel((i, j), (red, green, blue, 255))

            # Draw a simple "JJ" text or gorilla shape
            if size >= 32:
                # Draw simplified gorilla head silhouette (white)
                scale = size / 256
                # Head circle
                head_r = int(50 * scale)
                head_cx = int(128 * scale)
                head_cy = int(110 * scale)
                draw.ellipse([head_cx - head_r, head_cy - head_r,
                             head_cx + head_r, head_cy + head_r], fill='white')
                # Snout
                snout_w = int(25 * scale)
                snout_h = int(20 * scale)
                draw.ellipse([head_cx + int(15*scale), head_cy + int(10*scale),
                             head_cx + int(15*scale) + snout_w, head_cy + int(10*scale) + snout_h], fill='white')
                # Brow
                draw.ellipse([head_cx - int(30*scale), head_cy - int(25*scale),
                             head_cx + int(30*scale), head_cy - int(5*scale)], fill=(200, 200, 200, 255))

            images.append(img)

        # Save as ICO
        images[0].save(
            str(ico_path),
            format='ICO',
            sizes=[(s, s) for s in sizes],
            append_images=images[1:]
        )
        print(f"Created simplified icon: {ico_path}")
        return True

    except Exception as e:
        print(f"Failed to create icon: {e}")
        return False


def create_windows_shortcut():
    """Create a Windows shortcut (.lnk) file"""
    if sys.platform != "win32":
        print("Shortcut creation only works on Windows")
        print("Icon file created - you can manually create a shortcut")
        return False

    try:
        import winshell
        from win32com.client import Dispatch

        shortcut_path = PROJECT_ROOT / "JJ-Bot.lnk"
        target = PROJECT_ROOT / "start_all.bat"
        icon = PROJECT_ROOT / "assets" / "jjbot.ico"

        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.Targetpath = str(target)
        shortcut.WorkingDirectory = str(PROJECT_ROOT)
        shortcut.IconLocation = str(icon)
        shortcut.Description = "JJ-Bot Trading System"
        shortcut.save()

        print(f"Created shortcut: {shortcut_path}")
        return True

    except ImportError:
        print("winshell/pywin32 not available")
        # Create a VBS script to make the shortcut instead
        create_shortcut_vbs()
        return True


def create_shortcut_vbs():
    """Create a VBS script that creates the shortcut (works without extra deps)"""
    vbs_content = '''Set WshShell = WScript.CreateObject("WScript.Shell")
Set shortcut = WshShell.CreateShortcut("{project_root}\\JJ-Bot.lnk")
shortcut.TargetPath = "{project_root}\\start_all.bat"
shortcut.WorkingDirectory = "{project_root}"
shortcut.IconLocation = "{project_root}\\assets\\jjbot.ico"
shortcut.Description = "JJ-Bot Trading System"
shortcut.WindowStyle = 7
shortcut.Save
WScript.Echo "Shortcut created successfully!"
'''

    vbs_path = PROJECT_ROOT / "create_shortcut.vbs"
    vbs_content = vbs_content.replace("{project_root}", str(PROJECT_ROOT).replace("/", "\\"))

    with open(vbs_path, 'w') as f:
        f.write(vbs_content)

    print(f"Created VBS script: {vbs_path}")
    print("Run 'cscript create_shortcut.vbs' to create the shortcut")


if __name__ == "__main__":
    print("=" * 50)
    print("JJ-Bot Shortcut Creator")
    print("=" * 50)

    # Create the icon
    print("\n[1/2] Creating icon...")
    create_ico_from_svg()

    # Create the shortcut
    print("\n[2/2] Creating shortcut...")
    create_windows_shortcut()

    print("\nDone!")

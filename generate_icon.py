"""
Generate JJ-Bot gorilla icon from source image
Converts the gorilla side profile image to a multi-size ICO file
"""
from PIL import Image
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent


def main():
    print("Generating JJ-Bot gorilla icon...")

    # Find the source image
    assets_dir = PROJECT_ROOT / "assets"
    source_image = assets_dir / "gorilla side profile.jpg"

    if not source_image.exists():
        print(f"Error: Source image not found at {source_image}")
        return False

    # Load the source image
    print(f"Loading: {source_image.name}")
    img = Image.open(source_image)

    # Convert to RGBA if needed
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # Generate icons at multiple sizes for Windows
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        print(f"  Creating {size}x{size}...")
        # Use LANCZOS for high-quality downscaling
        resized = img.resize((size, size), Image.LANCZOS)
        images.append(resized)

    # Save as ICO with multiple sizes
    ico_path = assets_dir / "jjbot.ico"

    # Save largest first, then append smaller sizes
    images[-1].save(
        str(ico_path),
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1]
    )

    print(f"\nIcon saved to: {ico_path}")
    print(f"Icon contains sizes: {', '.join(f'{s}x{s}' for s in sizes)}")

    print("\nDone! Now run create_shortcut.bat to create the desktop shortcut.")
    return True


if __name__ == "__main__":
    main()

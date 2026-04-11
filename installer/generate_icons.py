#!/usr/bin/env python3
"""
Generate placeholder icons for Metadelphi
This creates simple placeholder icons that can be replaced with custom designs
"""

import sys
from pathlib import Path


def create_placeholder_icons():
    """Create placeholder icon files"""
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Create a simple icon with gradient background
        icon_size = 256
        img = Image.new('RGB', (icon_size, icon_size), color='white')
        draw = ImageDraw.Draw(img)

        # Draw a gradient background (simple two-color gradient)
        for y in range(icon_size):
            # Gradient from blue to purple
            r = int(100 + (150 * y / icon_size))
            g = int(50 + (100 * y / icon_size))
            b = int(200 - (50 * y / icon_size))
            draw.rectangle([(0, y), (icon_size, y + 1)], fill=(r, g, b))

        # Draw a simple "U" letter in the center
        try:
            # Try to use a default font
            font = ImageFont.truetype("Arial.ttf", 120)
        except:
            # Fallback to default font
            font = ImageFont.load_default()

        # Draw text
        text = "U"
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center the text
        x = (icon_size - text_width) // 2
        y = (icon_size - text_height) // 2

        # Draw text with shadow
        draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 128))  # Shadow
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))  # Text

        # Save PNG icon
        icon_dir = Path(__file__).parent
        png_path = icon_dir / "icon.png"
        img.save(png_path, 'PNG')
        print(f"✓ Created PNG icon: {png_path}")

        # Save ICO icon (multiple sizes)
        ico_path = icon_dir / "icon.ico"
        # Create multiple sizes for ICO
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        icons = []
        for size in sizes:
            icons.append(img.resize(size, Image.LANCZOS))

        icons[0].save(ico_path, format='ICO', sizes=[(s.width, s.height) for s in icons])
        print(f"✓ Created ICO icon: {ico_path}")

        return True

    except ImportError:
        print("Note: PIL/Pillow not available, creating placeholder files")
        return create_placeholder_files()
    except Exception as e:
        print(f"Warning: Could not create icons with PIL: {e}")
        return create_placeholder_files()


def create_placeholder_files():
    """Create placeholder text files as fallback"""
    icon_dir = Path(__file__).parent

    # Create placeholder for PNG
    png_path = icon_dir / "icon.png.txt"
    with open(png_path, 'w') as f:
        f.write("""PLACEHOLDER: icon.png

To add a custom icon:
1. Create or obtain a 256x256 PNG image for your icon
2. Save it as 'icon.png' in this directory
3. Delete this placeholder file

For now, the application will work without a custom icon.
""")
    print(f"Created placeholder: {png_path}")

    # Create placeholder for ICO
    ico_path = icon_dir / "icon.ico.txt"
    with open(ico_path, 'w') as f:
        f.write("""PLACEHOLDER: icon.ico

To add a custom icon:
1. Create or obtain an ICO file (Windows icon format)
2. Save it as 'icon.ico' in this directory
3. Delete this placeholder file

You can convert PNG to ICO using online tools like:
- https://convertio.co/png-ico/
- https://www.icoconverter.com/

For now, the application will work without a custom icon.
""")
    print(f"Created placeholder: {ico_path}")

    return False


def main():
    """Main entry point"""
    print("Generating Metadelphi icons...")
    result = create_placeholder_icons()

    if result:
        print("\n✓ Icons created successfully!")
        print("\nYou can replace these with custom icons anytime.")
    else:
        print("\n⚠ Placeholder files created.")
        print("Install Pillow (pip install Pillow) and run this script again to generate icons,")
        print("or manually add icon.png and icon.ico files to the installer/ directory.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

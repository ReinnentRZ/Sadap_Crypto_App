from PIL import Image, ImageDraw
from pathlib import Path

def generate_aerospace_icon(output_ico_path: Path, output_png_path: Path):
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Dark Slate Blue Rounded Shield Background
    # Draw rounded shield background
    bg_color = (15, 23, 42, 255)       # Slate 900
    border_color = (2, 132, 199, 255)  # Cyan / Sky 600
    glow_color = (56, 189, 248, 255)   # Light Sky 400

    draw.rounded_rectangle([12, 12, size - 12, size - 12], radius=48, fill=bg_color, outline=border_color, width=6)

    # 2. Orbital Ring (Ellipse)
    draw.arc([36, 60, size - 36, size - 60], start=20, end=340, fill=glow_color, width=4)

    # 3. Satellite Center Emblem
    center = size // 2
    # Solar Panels Left & Right
    panel_color = (2, 132, 199, 255)
    panel_grid = (56, 189, 248, 255)
    # Left Wing
    draw.rectangle([center - 90, center - 18, center - 38, center + 18], fill=panel_color, outline=panel_grid, width=2)
    # Right Wing
    draw.rectangle([center + 38, center - 18, center + 90, center + 18], fill=panel_color, outline=panel_grid, width=2)

    # Central Satellite Bus Body
    draw.rounded_rectangle([center - 30, center - 30, center + 30, center + 30], radius=8, fill=(241, 245, 249, 255), outline=glow_color, width=3)

    # Dish / Core Sensor Eye
    draw.ellipse([center - 14, center - 14, center + 14, center + 14], fill=(2, 132, 199, 255))
    draw.ellipse([center - 6, center - 6, center + 6, center + 6], fill=(16, 185, 129, 255)) # Green sensor lock

    # Small Antenna Spire
    draw.line([center, center - 30, center, center - 54], fill=glow_color, width=4)
    draw.ellipse([center - 5, center - 58, center + 5, center - 48], fill=(239, 68, 68, 255)) # Red blinking beacon

    output_ico_path.parent.mkdir(parents=True, exist_ok=True)
    # Save PNG
    img.save(output_png_path, format="PNG")

    # Save Multi-resolution ICO (16, 32, 48, 64, 128, 256)
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(output_ico_path, format="ICO", sizes=icon_sizes)
    print(f"Icon successfully generated at {output_ico_path} and {output_png_path}")

if __name__ == "__main__":
    ico_p = Path("assets/icons/app_icon.ico")
    png_p = Path("assets/icons/app_icon.png")
    generate_aerospace_icon(ico_p, png_p)

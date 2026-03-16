"""
generate_sample_images.py
=========================
Creates simple PNG sample images for the demo so participants
don't need to source their own images.

Generates:
  - circle_01.png  through circle_03.png
  - rectangle_01.png through rectangle_03.png
  - triangle_01.png through triangle_03.png
  - text_sample_01.png (contains readable text for OCR demo)

Run: python scripts/generate_sample_images.py
"""
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).parent.parent / "sample-images"
OUTPUT_DIR.mkdir(exist_ok=True)

IMG_SIZE = (400, 400)
BG_COLOR = (255, 255, 255)


def make_circle_image(filename: str, color=(70, 130, 180)):
    img = Image.new("RGB", IMG_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(img)
    margin = 60
    draw.ellipse([margin, margin, IMG_SIZE[0]-margin, IMG_SIZE[1]-margin],
                 fill=color, outline=(30, 30, 30), width=3)
    img.save(OUTPUT_DIR / filename)
    print(f"  ✅  {filename}")


def make_rectangle_image(filename: str, color=(220, 100, 60)):
    img = Image.new("RGB", IMG_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(img)
    margin = 60
    draw.rectangle([margin, margin+40, IMG_SIZE[0]-margin, IMG_SIZE[1]-margin-40],
                   fill=color, outline=(30, 30, 30), width=3)
    img.save(OUTPUT_DIR / filename)
    print(f"  ✅  {filename}")


def make_triangle_image(filename: str, color=(80, 160, 80)):
    img = Image.new("RGB", IMG_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(img)
    points = [(IMG_SIZE[0]//2, 50), (40, 360), (IMG_SIZE[0]-40, 360)]
    draw.polygon(points, fill=color, outline=(30, 30, 30))
    img.save(OUTPUT_DIR / filename)
    print(f"  ✅  {filename}")


def make_text_image(filename: str):
    img = Image.new("RGB", (600, 400), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Try to use a system font; fall back to default
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_body  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except (IOError, OSError):
        font_large = ImageFont.load_default()
        font_body  = font_large

    lines = [
        ("Azure AI Document Intelligence Demo", font_large, (0, 78, 140)),
        ("", font_body, (0, 0, 0)),
        ("Invoice #: INV-2025-0042", font_body, (40, 40, 40)),
        ("Date: December 1, 2025",  font_body, (40, 40, 40)),
        ("Amount Due: $1,250.00",   font_body, (40, 40, 40)),
        ("",                        font_body, (0, 0, 0)),
        ("This is sample text for OCR extraction.", font_body, (80, 80, 80)),
        ("Document Intelligence reads printed text.", font_body, (80, 80, 80)),
        ("It works on invoices, forms, and images.", font_body, (80, 80, 80)),
    ]

    y = 30
    for text, font, color in lines:
        draw.text((30, y), text, fill=color, font=font)
        y += 40

    img.save(OUTPUT_DIR / filename)
    print(f"  ✅  {filename}")


def make_mixed_image(filename: str):
    """Image with both shapes AND text — exercises both services simultaneously."""
    img = Image.new("RGB", (600, 500), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # A circle
    draw.ellipse([30, 30, 180, 180], fill=(70, 130, 180), outline=(20, 20, 20), width=2)

    # A rectangle
    draw.rectangle([220, 50, 400, 160], fill=(220, 100, 60), outline=(20, 20, 20), width=2)

    # A triangle
    draw.polygon([(450, 30), (380, 180), (540, 180)], fill=(80, 160, 80), outline=(20, 20, 20))

    # Text labels
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except (IOError, OSError):
        font = ImageFont.load_default()
        font_title = font

    draw.text((30, 200),  "Shape Detection + OCR Demo", fill=(0, 0, 0), font=font_title)
    draw.text((30, 240),  "Circle: Blue filled ellipse (left)", fill=(40, 40, 40), font=font)
    draw.text((30, 270),  "Rectangle: Orange filled rect (centre)", fill=(40, 40, 40), font=font)
    draw.text((30, 300),  "Triangle: Green polygon (right)", fill=(40, 40, 40), font=font)
    draw.text((30, 350),  "This text will be extracted by", fill=(80, 80, 80), font=font)
    draw.text((30, 380),  "Azure Document Intelligence OCR.", fill=(80, 80, 80), font=font)
    draw.text((30, 430),  "Session 4 & 5 — QA Azure AI Programme", fill=(120, 120, 120), font=font)

    img.save(OUTPUT_DIR / filename)
    print(f"  ✅  {filename}")


def main():
    print("Generating sample images...")
    make_circle_image("circle_01.png", color=(70, 130, 180))
    make_circle_image("circle_02.png", color=(30, 80, 160))
    make_circle_image("circle_03.png", color=(100, 180, 220))
    make_rectangle_image("rectangle_01.png", color=(220, 100, 60))
    make_rectangle_image("rectangle_02.png", color=(180, 60, 40))
    make_rectangle_image("rectangle_03.png", color=(240, 150, 80))
    make_triangle_image("triangle_01.png", color=(80, 160, 80))
    make_triangle_image("triangle_02.png", color=(40, 120, 40))
    make_triangle_image("triangle_03.png", color=(120, 200, 100))
    make_text_image("text_sample_01.png")
    make_mixed_image("mixed_shapes_and_text.png")
    print(f"\n✅  {len(list(OUTPUT_DIR.glob('*.png')))} images written to sample-images/")
    print("\nNext: run  python scripts/setup_custom_vision.py  to train the model.")


if __name__ == "__main__":
    main()

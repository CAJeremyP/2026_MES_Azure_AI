"""
generate_sample_images.py
=========================
Generates 20 training images per tag for Custom Vision Object Detection.

IMPORTANT: Object Detection requires bounding box annotations, not just
image-level tags. This script returns the normalised bounding box
(left, top, width, height as fractions of image size) for every shape
drawn, and saves them to sample-images/annotations.json so that
setup_custom_vision.py can upload them alongside the images.

Tags: circle, rectangle, triangle, text
Inference image (not for training): mixed_shapes_and_text.png

Usage:
    python scripts/generate_sample_images.py
"""
import sys
import json
import random
import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).parent.parent / "sample-images"
OUTPUT_DIR.mkdir(exist_ok=True)

IMAGES_PER_TAG = 20
W, H = 400, 400
TRAINING_EXCLUDES = {"mixed_shapes_and_text.png"}

BLUES   = [(70,130,180),(30,80,160),(100,180,220),(0,105,148),(173,216,230),
           (0,150,199),(52,152,219),(21,67,96),(135,206,235),(0,191,255),
           (70,100,200),(10,60,120),(0,120,180),(80,160,200),(50,90,150),
           (20,70,140),(90,140,190),(0,80,160),(110,170,220),(40,110,170)]
ORANGES = [(220,100,60),(180,60,40),(240,150,80),(204,85,0),(255,140,0),
           (210,105,30),(165,70,15),(230,120,50),(200,80,20),(255,160,50),
           (190,90,40),(240,100,30),(160,60,10),(220,130,60),(200,110,40),
           (250,120,20),(170,80,30),(210,90,50),(185,75,25),(235,145,70)]
GREENS  = [(80,160,80),(40,120,40),(120,200,100),(34,139,34),(0,128,0),
           (60,179,113),(0,100,0),(144,238,144),(50,150,50),(0,160,80),
           (70,140,70),(100,180,60),(30,110,30),(90,170,90),(110,190,80),
           (20,90,20),(130,200,90),(60,130,60),(80,150,40),(45,125,45)]
GRAYS   = [(245,245,245),(240,240,245),(248,245,240),(242,248,242),(245,242,248)]


def _font(size=20, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf".format("-Bold" if bold else ""),
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


def _base(i):
    return Image.new("RGB", (W, H), GRAYS[i % len(GRAYS)])


def _add_noise(img, amount=6):
    pixels = img.load()
    for _ in range(W * H // 6):
        x = random.randint(0, W - 1)
        y = random.randint(0, H - 1)
        p = pixels[x, y]
        d = random.randint(-amount, amount)
        pixels[x, y] = tuple(max(0, min(255, c + d)) for c in p)
    return img


def _norm_box(left_px, top_px, right_px, bottom_px):
    """
    Convert pixel bounding box to normalised (0-1) Custom Vision format.
    Returns (left, top, width, height) all as fractions of image size.
    Clamps to [0, 1] to handle any edge shapes.
    """
    l = max(0.0, left_px  / W)
    t = max(0.0, top_px   / H)
    r = min(1.0, right_px / W)
    b = min(1.0, bottom_px / H)
    return {"left": l, "top": t, "width": r - l, "height": b - t}


# ── CIRCLE ────────────────────────────────────────────────────
def make_circles(n):
    positions = [(200,200),(120,130),(290,280),(150,250),(260,150),
                 (100,100),(300,300),(200,150),(170,270),(230,200),
                 (140,200),(250,180),(180,300),(220,130),(160,180),
                 (200,250),(130,160),(280,220),(190,140),(240,260)]
    radii     = [130,70,85,100,90,65,110,75,95,80,
                 120,60,105,88,115,72,98,82,68,92]
    entries = []
    for i in range(n):
        img  = _base(i)
        draw = ImageDraw.Draw(img)
        cx, cy = positions[i]
        r      = radii[i]
        col    = BLUES[i]
        draw.ellipse([cx-r, cy-r, cx+r, cy+r],
                     fill=col, outline=(20,20,20), width=[2,3,4][i%3])
        img = _add_noise(img)
        fname = f"circle_{i+1:02d}.png"
        img.save(OUTPUT_DIR / fname)
        entries.append({
            "file": fname, "tag": "circle",
            "box": _norm_box(cx-r, cy-r, cx+r, cy+r)
        })
    return entries


# ── RECTANGLE ─────────────────────────────────────────────────
def make_rectangles(n):
    boxes_px = [
        (60,  60,  340, 340),(100, 80,  360, 320),(40,  100, 300, 360),
        (80,  40,  370, 330),(20,  120, 310, 380),(120, 120, 380, 380),
        (40,  40,  320, 240),(20,  160, 380, 360),(80,  20,  320, 220),
        (60,  160, 340, 380),(100, 100, 300, 300),(40,  60,  360, 340),
        (20,  80,  260, 320),(120, 40,  380, 260),(80,  120, 320, 280),
        (40,  20,  360, 200),(60,  200, 340, 380),(20,  40,  300, 260),
        (100, 140, 360, 360),(40,  80,  280, 320),
    ]
    entries = []
    for i in range(n):
        img  = _base(i)
        draw = ImageDraw.Draw(img)
        l, t, r, b = boxes_px[i]
        col = ORANGES[i]

        if i % 3 == 2:
            # Rotated rectangle — compute tight axis-aligned bounding box
            angle = math.radians([15, 30, 45, -15, -30, -45][i % 6])
            cx_r  = (l + r) / 2
            cy_r  = (t + b) / 2
            hw    = (r - l) / 2
            hh    = (b - t) / 2
            corners = [(-hw,-hh),(hw,-hh),(hw,hh),(-hw,hh)]
            pts = [(cx_r + x*math.cos(angle) - y*math.sin(angle),
                    cy_r + x*math.sin(angle) + y*math.cos(angle))
                   for x, y in corners]
            draw.polygon(pts, fill=col, outline=(20,20,20))
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            box = _norm_box(min(xs), min(ys), max(xs), max(ys))
        else:
            draw.rectangle([l, t, r, b], fill=col, outline=(20,20,20),
                           width=[2,3,4][i%3])
            box = _norm_box(l, t, r, b)

        img = _add_noise(img)
        fname = f"rectangle_{i+1:02d}.png"
        img.save(OUTPUT_DIR / fname)
        entries.append({"file": fname, "tag": "rectangle", "box": box})
    return entries


# ── TRIANGLE ──────────────────────────────────────────────────
def make_triangles(n):
    # (apex_x, apex_y, base_y, half_width, inverted)
    configs = [
        (200,40, 360,130,False),(150,60, 340,100,False),(270,50, 350,120,False),
        (200,80, 320, 90,False),(180,30, 370,150,False),(220,70, 330,110,False),
        (160,50, 360,140,False),(240,40, 350,100,False),(190,60, 340,120,False),
        (210,45, 370,130,False),
        (200,370,40, 130,True),(150,360,60, 100,True),(270,350,50, 120,True),
        (200,320,80,  90,True),(180,370,30, 150,True),(220,330,70, 110,True),
        (160,360,50, 140,True),(240,350,40, 100,True),(190,340,60, 120,True),
        (210,370,45, 130,True),
    ]
    entries = []
    for i in range(n):
        img  = _base(i)
        draw = ImageDraw.Draw(img)
        col  = GREENS[i]
        cx, ay, by, hw, inv = configs[i]

        if inv:
            pts = [(cx-hw, ay), (cx+hw, ay), (cx, by)]
        else:
            pts = [(cx, ay), (cx-hw, by), (cx+hw, by)]

        draw.polygon(pts, fill=col, outline=(20,20,20))

        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        box = _norm_box(min(xs), min(ys), max(xs), max(ys))

        img = _add_noise(img)
        fname = f"triangle_{i+1:02d}.png"
        img.save(OUTPUT_DIR / fname)
        entries.append({"file": fname, "tag": "triangle", "box": box})
    return entries


# ── TEXT ──────────────────────────────────────────────────────
def make_text_images(n):
    samples = [
        ["Azure AI Document Intelligence","Invoice #: INV-2025-001","Date: 2025-12-01","Total: $1,250.00","Status: Approved"],
        ["Purchase Order","PO Number: PO-98765","Vendor: Contoso Ltd","Amount: $4,500.00","Terms: Net 30"],
        ["Meeting Notes","Date: December 1 2025","Attendees: Alice Bob Carol","Action: Deploy by Friday","Owner: DevOps"],
        ["Product Specification","Model: AZ-2000","Version: 3.1.4","Status: Approved","Region: East US"],
        ["Azure Subscription","ID: a5aa4093-4fc8","Plan: Pay-As-You-Go","Region: East US","Tier: Standard"],
        ["Lab Report","Sample ID: LAB-042","Result: Pass","Confidence: 98.7%","Reviewed By: Dr Smith"],
        ["Shipping Label","From: New York NY 10036","To: Los Angeles CA 90001","Weight: 2.4 kg","Tracking: 1Z999AA1"],
        ["Receipt","Store: Azure Marketplace","Items: 3","Subtotal: $89.99","Tax: $7.20","Total: $97.19"],
        ["Contract Summary","Party A: MES Inc","Party B: QA Ltd","Value: $22,145","Start: Dec 1 2025"],
        ["Service Agreement","SLA: 99.9% uptime","Support: 24/7","Tier: Enterprise","Renewal: Annual"],
        ["Bank Statement","Account: 4521-XXXX","Balance: $12,450.00","Date: Dec 2025","Currency: USD"],
        ["Medical Record","Patient ID: P-00492","DOB: 1985-03-15","Diagnosis: Code A1","Visit: 2025-11-30"],
        ["Inventory List","SKU: PRD-001","Qty: 250 units","Location: Shelf B3","Reorder: Yes"],
        ["Travel Itinerary","Flight: AA 2301","Depart: JFK 08:30","Arrive: LAX 11:45","Seat: 14A"],
        ["Job Application","Name: Jane Doe","Role: Azure Engineer","Ref: REF-2025-099","Status: Interview"],
        ["Lease Agreement","Unit: 4B","Rent: $2,800/mo","Start: Jan 1 2026","Term: 12 months"],
        ["Insurance Policy","Policy #: POL-88123","Coverage: $500,000","Premium: $1,200/yr","Deductible: $500"],
        ["Tax Form","Year: 2025","Income: $95,000","Deductions: $14,400","Refund: $3,200"],
        ["Project Charter","Project: AI Demo","Budget: $50,000","Timeline: Q4 2025","Sponsor: CTO"],
        ["Certificate","Awarded to: J Price","Course: Azure AI","Date: Dec 2025","Issuer: QA Ltd"],
    ]
    font_sizes = [16,18,20,22,24,16,18,20,22,24,
                  16,18,20,22,24,16,18,20,22,24]
    entries = []
    for i in range(n):
        img  = _base(i)
        draw = ImageDraw.Draw(img)
        lines = samples[i]
        fs    = font_sizes[i]
        font  = _font(fs)
        font_bold = _font(fs+2, bold=True)
        mx = 20 + (i % 4) * 10
        y  = 30 + (i % 3) * 15

        # Track text bounds for the bounding box annotation
        x_min, y_min = mx, y
        x_max, y_max = mx, y

        for j, line in enumerate(lines):
            f = font_bold if j == 0 else font
            try:
                bbox = draw.textbbox((mx, y), line, font=f)
                x_max = max(x_max, bbox[2])
                y_max = max(y_max, bbox[3])
            except AttributeError:
                # Older Pillow fallback
                tw, th = draw.textsize(line, font=f)
                x_max = max(x_max, mx + tw)
                y_max = max(y_max, y + th)
            draw.text((mx, y), line, fill=(30,30,30), font=f)
            y += fs + 12

        box = _norm_box(x_min - 5, y_min - 5, x_max + 5, y_max + 5)
        img = _add_noise(img, 4)
        fname = f"text_{i+1:02d}.png"
        img.save(OUTPUT_DIR / fname)
        entries.append({"file": fname, "tag": "text", "box": box})
    return entries


# ── MIXED INFERENCE IMAGE ─────────────────────────────────────
def make_mixed_image():
    img  = Image.new("RGB", (600, 480), (255,255,255))
    draw = ImageDraw.Draw(img)
    draw.ellipse([30,30,180,180],    fill=(70,130,180), outline=(20,20,20), width=2)
    draw.rectangle([220,50,400,160], fill=(220,100,60),  outline=(20,20,20), width=2)
    draw.polygon([(490,30),(420,180),(560,180)], fill=(80,160,80), outline=(20,20,20))
    ft = _font(22, bold=True)
    fb = _font(18)
    draw.text((30,210), "Shape Detection + OCR Demo", fill=(0,0,0),     font=ft)
    draw.text((30,250), "Circle  •  Rectangle  •  Triangle",fill=(40,40,40),font=fb)
    draw.text((30,285), "Invoice #: INV-2025-0042",          fill=(60,60,60),font=fb)
    draw.text((30,315), "Amount Due: $1,250.00",              fill=(60,60,60),font=fb)
    draw.text((30,345), "Extracted by Document Intelligence.",fill=(80,80,80),font=fb)
    draw.text((30,375), "Sessions 4 & 5 — QA Azure AI Programme",fill=(120,120,120),font=_font(16))
    img.save(OUTPUT_DIR / "mixed_shapes_and_text.png")


def main():
    random.seed(42)

    # Clean old training images
    deleted = 0
    for old in OUTPUT_DIR.glob("*.png"):
        if old.name not in TRAINING_EXCLUDES:
            old.unlink()
            deleted += 1
    if deleted:
        print(f"🗑️   Removed {deleted} old training image(s).")

    print(f"Generating {IMAGES_PER_TAG} Object Detection training images per tag...")
    print("(Bounding box annotations computed from shape geometry)")
    print()

    all_annotations = []
    all_annotations += make_circles(IMAGES_PER_TAG)
    print(f"  ✅  circle      : {IMAGES_PER_TAG} images")
    all_annotations += make_rectangles(IMAGES_PER_TAG)
    print(f"  ✅  rectangle   : {IMAGES_PER_TAG} images")
    all_annotations += make_triangles(IMAGES_PER_TAG)
    print(f"  ✅  triangle    : {IMAGES_PER_TAG} images")
    all_annotations += make_text_images(IMAGES_PER_TAG)
    print(f"  ✅  text        : {IMAGES_PER_TAG} images")

    make_mixed_image()
    print(f"  ✅  mixed_shapes_and_text.png  (inference image)")

    # Save annotations for setup_custom_vision.py to consume
    ann_path = OUTPUT_DIR / "annotations.json"
    with open(ann_path, "w") as f:
        json.dump(all_annotations, f, indent=2)
    print()
    print(f"✅  {len(all_annotations)} annotations saved to sample-images/annotations.json")
    print(f"   Format: {{file, tag, box: {{left, top, width, height}}}} (normalised 0-1)")
    print()
    print("Next: python scripts/setup_custom_vision.py")


if __name__ == "__main__":
    main()

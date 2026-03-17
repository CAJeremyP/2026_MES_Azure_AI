"""
main.py — Azure AI End-to-End Demo
====================================
Orchestrates the full pipeline from Sessions 4 & 5:

  Session 4:
    1. Select an image
    2. Upload to Azure Blob Storage
    3. Run Custom Vision (shape detection)
    4. Run Document Intelligence (OCR)
    5. Create / connect SQL database tables

  Session 5:
    6. Extract and display results
    7. Save results to SQL
    8. Display output in terminal + generate HTML report
    9. Review Azure costs

Usage:
    python main.py [--image path/to/image.png]
    python main.py --demo   (uses bundled sample images)
"""
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

# Local modules
from uploader import upload_image
from vision import run_custom_vision
from document_intel import run_document_intelligence
from database import DatabaseClient
from cost_review import get_cost_summary
from report import generate_html_report

BANNER = """
╔══════════════════════════════════════════════════════╗
║       Azure AI End-to-End Demo  |  Sessions 4 & 5    ║
╚══════════════════════════════════════════════════════╝
"""

def run_pipeline(image_path: Path):
    print(BANNER)
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    results = {"run_id": run_id, "image_path": str(image_path)}

    # ── Step 1: Upload image to Blob Storage ─────────────────
    print("━" * 54)
    print("  STEP 1 ▶  Upload image to Azure Blob Storage")
    print("━" * 54)
    blob_url = upload_image(image_path)
    results["blob_url"] = blob_url
    print(f"  ✅  Uploaded: {blob_url}\n")

    # ── Step 2: Custom Vision — shape detection ───────────────
    print("━" * 54)
    print("  STEP 2 ▶  Custom Vision — Shape Detection")
    print("━" * 54)
    vision_results = run_custom_vision(blob_url, image_path)
    results["vision"] = vision_results
    if vision_results:
        for r in vision_results:
            bb = r.get("bounding_box", {})
            print(f"  🔷  {r['tag']:15s}  confidence={r['probability']:.1%}  "
                  f"box=(left={bb.get('left',0):.3f}, top={bb.get('top',0):.3f}, "
                  f"w={bb.get('width',0):.3f}, h={bb.get('height',0):.3f})")
    else:
        print("  ℹ️   No objects detected above threshold (check model is trained and published)")
    print()

    # ── Step 3: Document Intelligence — OCR ───────────────────
    print("━" * 54)
    print("  STEP 3 ▶  Document Intelligence — OCR / Text Extraction")
    print("━" * 54)
    doc_results = run_document_intelligence(image_path)
    results["document_intelligence"] = doc_results
    if doc_results.get("lines"):
        for line in doc_results["lines"][:10]:   # Show first 10 lines
            conf = line.get("confidence")
            conf_str = f"{conf:.1%}" if conf is not None else "n/a"
            print(f"  📄  \"{line['content']}\"  (confidence={conf_str})")
        if len(doc_results["lines"]) > 10:
            print(f"  ... and {len(doc_results['lines'])-10} more lines")
    else:
        print("  ℹ️   No text detected in image")
    print()

    # ── Step 4: Database — save results ───────────────────────
    print("━" * 54)
    print("  STEP 4 ▶  Save Results to Azure SQL Database")
    print("━" * 54)
    db = DatabaseClient()
    db.ensure_tables()
    db.insert_run(run_id, str(image_path), blob_url)
    db.insert_vision_results(run_id, vision_results)
    db.insert_doc_results(run_id, doc_results.get("lines", []))
    print(f"  ✅  Saved run {run_id} to database\n")

    # ── Step 5: Display summary ───────────────────────────────
    print("━" * 54)
    print("  STEP 5 ▶  Results Summary")
    print("━" * 54)
    db.print_run_summary(run_id)
    print()

    # ── Step 6: Cost review ───────────────────────────────────
    print("━" * 54)
    print("  STEP 6 ▶  Azure Cost Review")
    print("━" * 54)
    costs = get_cost_summary()
    results["costs"] = costs
    print()

    # ── Step 7: Generate HTML report ─────────────────────────
    print("━" * 54)
    print("  STEP 7 ▶  HTML Report")
    print("━" * 54)
    report_path = ROOT / "app" / "output" / f"report_{run_id}.html"
    report_path.parent.mkdir(exist_ok=True)
    generate_html_report(results, report_path)
    print(f"  ✅  Report saved: {report_path}")
    print()

    print("╔══════════════════════════════════════════════════════╗")
    print("║  ✅  Pipeline complete!                               ║")
    print("╚══════════════════════════════════════════════════════╝")
    return results


def main():
    parser = argparse.ArgumentParser(description="Azure AI End-to-End Demo")
    parser.add_argument("--image", type=Path, help="Path to image file")
    parser.add_argument("--demo", action="store_true", help="Use bundled sample images")
    args = parser.parse_args()

    sample_dir = ROOT / "sample-images"

    if args.demo:
        images = list(sample_dir.glob("*.png"))
        if not images:
            print("❌  No sample images found in sample-images/")
            print("   Add some PNG files to that directory.")
            sys.exit(1)
        # Run pipeline on first two images for the demo
        for img in images[:2]:
            print(f"\n▶  Processing: {img.name}")
            run_pipeline(img)
    elif args.image:
        if not args.image.exists():
            print(f"❌  File not found: {args.image}")
            sys.exit(1)
        run_pipeline(args.image)
    else:
        # Interactive mode
        print(BANNER)
        print("Available sample images:")
        samples = list(sample_dir.glob("*.png"))
        for i, p in enumerate(samples):
            print(f"  [{i+1}] {p.name}")
        print(f"  [0] Enter a custom path")
        print()
        choice = input("Select image (number): ").strip()
        if choice == "0":
            custom = input("Enter image path: ").strip()
            image_path = Path(custom)
        elif choice.isdigit() and 1 <= int(choice) <= len(samples):
            image_path = samples[int(choice) - 1]
        else:
            print("Invalid choice.")
            sys.exit(1)
        run_pipeline(image_path)


if __name__ == "__main__":
    main()

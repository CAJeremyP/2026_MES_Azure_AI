"""
setup_custom_vision.py
======================
Creates a Custom Vision project, uploads sample images with tags,
trains the model, and publishes it for prediction.

Run once after deploy.sh has populated .env.
Takes ~5-15 minutes (training time).

Usage:
    python scripts/setup_custom_vision.py
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

try:
    from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
    from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateBatch, ImageFileCreateEntry, Region
    from msrest.authentication import ApiKeyCredentials
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install",
        "azure-cognitiveservices-vision-customvision", "msrest", "python-dotenv"])
    from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
    from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateBatch, ImageFileCreateEntry
    from msrest.authentication import ApiKeyCredentials

TRAINING_ENDPOINT = os.environ["CUSTOM_VISION_TRAINING_ENDPOINT"]
TRAINING_KEY      = os.environ["CUSTOM_VISION_TRAINING_KEY"]
PUBLISH_NAME      = os.environ.get("CUSTOM_VISION_PUBLISH_NAME", "demov1")
PREDICTION_RESOURCE_ID = os.environ.get("CUSTOM_VISION_PREDICTION_RESOURCE_ID", "")
PROJECT_NAME      = "AzureAIDemo-ShapeDetector"

SAMPLE_IMAGES_DIR = ROOT / "sample-images"

def main():
    print("=" * 50)
    print("  Custom Vision — Project Setup")
    print("=" * 50)

    credentials = ApiKeyCredentials(in_headers={"Training-key": TRAINING_KEY})
    trainer = CustomVisionTrainingClient(TRAINING_ENDPOINT, credentials)

    # ── Check for existing project ───────────────────────────
    existing = [p for p in trainer.get_projects() if p.name == PROJECT_NAME]
    if existing:
        project = existing[0]
        print(f"✅  Found existing project: {project.id}")
    else:
        print(f"📁  Creating project '{PROJECT_NAME}'...")
        # Object detection domain — best for shape detection
        domains = trainer.get_domains()
        od_domain = next(d for d in domains if d.type == "ObjectDetection" and "General" in d.name)
        project = trainer.create_project(
            PROJECT_NAME,
            domain_id=od_domain.id,
            classification_type="Multiclass"
        )
        print(f"✅  Project created: {project.id}")

    # ── Create tags ──────────────────────────────────────────
    print("🏷️   Creating tags...")
    existing_tags = {t.name: t for t in trainer.get_tags(project.id)}
    tag_names = ["circle", "rectangle", "triangle", "text"]
    tags = {}
    for name in tag_names:
        if name in existing_tags:
            tags[name] = existing_tags[name]
        else:
            tags[name] = trainer.create_tag(project.id, name)
        print(f"   - {name}: {tags[name].id}")

    # ── Upload sample images ──────────────────────────────────
    print("🖼️   Uploading sample images...")
    upload_count = 0
    image_entries = []

    for img_path in SAMPLE_IMAGES_DIR.glob("*.png"):
        # Determine tag from filename prefix (e.g. circle_01.png → circle)
        stem = img_path.stem.lower()
        matched_tag = None
        for tag_name in tag_names:
            if stem.startswith(tag_name):
                matched_tag = tags[tag_name]
                break

        if matched_tag is None:
            print(f"   ⚠️  Skipping {img_path.name} — no matching tag")
            continue

        with open(img_path, "rb") as f:
            image_entries.append(ImageFileCreateEntry(
                name=img_path.name,
                contents=f.read(),
                tag_ids=[matched_tag.id]
            ))
        upload_count += 1

    if image_entries:
        batch = ImageFileCreateBatch(images=image_entries)
        result = trainer.create_images_from_files(project.id, batch)
        if result.is_batch_successful:
            print(f"   ✅  Uploaded {upload_count} images.")
        else:
            print("   ⚠️  Some images failed to upload:")
            for img in result.images:
                if img.status != "OK":
                    print(f"      {img.source_url}: {img.status}")
    else:
        print("   ℹ️  No sample images found. Add PNG files to sample-images/")
        print("      Named like: circle_01.png, rectangle_01.png, etc.")
        print("   Skipping training — add images and re-run this script.")
        _write_project_id(project.id)
        return

    # ── Train ─────────────────────────────────────────────────
    print("🧠  Starting training (this may take 5-15 minutes)...")
    iteration = trainer.train_project(project.id)
    while iteration.status not in ["Completed", "Failed"]:
        print(f"   Status: {iteration.status} — waiting 15s...")
        time.sleep(15)
        iteration = trainer.get_iteration(project.id, iteration.id)

    if iteration.status == "Failed":
        print("❌  Training failed. Check that you have enough tagged images (min 5 per tag).")
        sys.exit(1)

    print("✅  Training complete!")

    # ── Publish ───────────────────────────────────────────────
    if PREDICTION_RESOURCE_ID:
        print(f"📢  Publishing as '{PUBLISH_NAME}'...")
        trainer.publish_iteration(project.id, iteration.id, PUBLISH_NAME, PREDICTION_RESOURCE_ID)
        print("✅  Published!")
    else:
        print("ℹ️  CUSTOM_VISION_PREDICTION_RESOURCE_ID not set in .env — skipping publish.")
        print("   Set it and re-run, or publish manually in the Custom Vision portal.")

    _write_project_id(project.id)
    print()
    print("=" * 50)
    print("  Done! Project ID written to .env")
    print("=" * 50)


def _write_project_id(project_id: str):
    env_path = ROOT / ".env"
    content = env_path.read_text()
    if "CUSTOM_VISION_PROJECT_ID=" in content:
        import re
        content = re.sub(r"^CUSTOM_VISION_PROJECT_ID=.*$",
                         f"CUSTOM_VISION_PROJECT_ID={project_id}",
                         content, flags=re.MULTILINE)
    else:
        content += f"\nCUSTOM_VISION_PROJECT_ID={project_id}\n"
    env_path.write_text(content)
    print(f"   Project ID: {project_id}")


if __name__ == "__main__":
    main()

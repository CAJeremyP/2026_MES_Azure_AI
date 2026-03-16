"""
setup_custom_vision.py
======================
Creates an Object Detection Custom Vision project, uploads
training images with bounding box annotations, trains, and publishes.

Requires annotations.json produced by generate_sample_images.py.

Usage:
    python scripts/setup_custom_vision.py
"""
import os
import sys
import re
import json
import time
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

try:
    from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
    from azure.cognitiveservices.vision.customvision.training.models import (
        ImageFileCreateBatch, ImageFileCreateEntry, Region
    )
    from msrest.authentication import ApiKeyCredentials
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install",
        "azure-cognitiveservices-vision-customvision", "msrest", "python-dotenv"])
    from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
    from azure.cognitiveservices.vision.customvision.training.models import (
        ImageFileCreateBatch, ImageFileCreateEntry, Region
    )
    from msrest.authentication import ApiKeyCredentials

TRAINING_ENDPOINT  = os.environ["CUSTOM_VISION_TRAINING_ENDPOINT"]
TRAINING_KEY       = os.environ["CUSTOM_VISION_TRAINING_KEY"]
PUBLISH_NAME       = os.environ.get("CUSTOM_VISION_PUBLISH_NAME", "demov1")
PROJECT_NAME       = "AzureAIDemo-ShapeDetector"
SAMPLE_IMAGES_DIR  = ROOT / "sample-images"
ANNOTATIONS_FILE   = SAMPLE_IMAGES_DIR / "annotations.json"
MIN_IMAGES_PER_TAG = 5


def main():
    print("=" * 50)
    print("  Custom Vision — Object Detection Setup")
    print("=" * 50)

    # ── Check annotations exist ───────────────────────────────
    if not ANNOTATIONS_FILE.exists():
        print("❌  annotations.json not found.")
        print("   Run: python scripts/generate_sample_images.py")
        sys.exit(1)

    with open(ANNOTATIONS_FILE) as f:
        annotations = json.load(f)
    print(f"✅  Loaded {len(annotations)} annotations from annotations.json")

    credentials = ApiKeyCredentials(in_headers={"Training-key": TRAINING_KEY})
    trainer = CustomVisionTrainingClient(TRAINING_ENDPOINT, credentials)

    # ── Project — must be Object Detection domain ─────────────
    existing = [p for p in trainer.get_projects() if p.name == PROJECT_NAME]
    if existing:
        project = existing[0]
        # Check it really is an object detection project
        domain = next(
            (d for d in trainer.get_domains() if str(d.id) == str(project.domain_id)),
            None
        )
        if domain and domain.type != "ObjectDetection":
            print(f"⚠️   Existing project is type '{domain.type}', not ObjectDetection.")
            print(f"    Deleting and recreating as Object Detection...")
            trainer.delete_project(project.id)
            existing = []
        else:
            print(f"✅  Using existing Object Detection project: {project.id}")

    if not existing:
        print(f"📁  Creating Object Detection project '{PROJECT_NAME}'...")
        domains = trainer.get_domains()
        od_domain = next(
            (d for d in domains
             if d.type == "ObjectDetection" and "General" in d.name),
            None
        )
        if not od_domain:
            print("❌  No ObjectDetection domain found. Available domains:")
            for d in domains:
                print(f"    {d.name} ({d.type})")
            sys.exit(1)
        project = trainer.create_project(
            PROJECT_NAME,
            domain_id=od_domain.id,
        )
        print(f"✅  Project created: {project.id}")

    # ── Tags ──────────────────────────────────────────────────
    print("🏷️   Creating tags...")
    existing_tags = {t.name: t for t in trainer.get_tags(project.id)}
    tag_names = sorted({a["tag"] for a in annotations})
    tags = {}
    for name in tag_names:
        if name in existing_tags:
            tags[name] = existing_tags[name]
        else:
            tags[name] = trainer.create_tag(project.id, name)
        print(f"   - {name}: {tags[name].id}")

    # ── Count check ───────────────────────────────────────────
    counts = {}
    for a in annotations:
        counts[a["tag"]] = counts.get(a["tag"], 0) + 1
    print()
    print("  Annotation counts:")
    short = []
    for tag_name, count in sorted(counts.items()):
        ok = "✅" if count >= MIN_IMAGES_PER_TAG else "❌"
        print(f"    {ok}  {tag_name:12s}: {count}")
        if count < MIN_IMAGES_PER_TAG:
            short.append(tag_name)
    if short:
        print(f"\n❌  Not enough images for: {', '.join(short)}")
        print("   Run: python scripts/generate_sample_images.py")
        sys.exit(1)

    # ── Upload — count-based dedup per tag ────────────────────
    print()
    print("🖼️   Checking uploaded image counts per tag...")

    tags_to_upload = {}
    for tag_name in tag_names:
        target = counts[tag_name]
        uploaded_count = trainer.get_tagged_image_count(
            project.id, tag_ids=[tags[tag_name].id]
        )
        if uploaded_count == target:
            print(f"   ✅  {tag_name:12s}: {uploaded_count}/{target} — already complete")
        else:
            print(f"   ⬆️   {tag_name:12s}: {uploaded_count}/{target} — queued for upload")
            tags_to_upload[tag_name] = True

    if not tags_to_upload:
        print("   ✅  All tags fully uploaded — skipping upload step.")
    else:
        # Delete existing images for tags being re-uploaded
        for tag_name in tags_to_upload:
            existing_count = trainer.get_tagged_image_count(
                project.id, tag_ids=[tags[tag_name].id]
            )
            if existing_count > 0:
                print(f"   🗑️   Deleting {existing_count} existing '{tag_name}' image(s)...")
                existing_imgs = trainer.get_tagged_images(
                    project.id, tag_ids=[tags[tag_name].id], take=256
                )
                img_ids = [img.id for img in existing_imgs]
                if img_ids:
                    trainer.delete_images(project.id, image_ids=img_ids)

        # Build ImageFileCreateEntry list with Region annotations
        entries = []
        for ann in annotations:
            if ann["tag"] not in tags_to_upload:
                continue
            img_path = SAMPLE_IMAGES_DIR / ann["file"]
            if not img_path.exists():
                print(f"   ⚠️   {ann['file']} not found — skipping")
                continue
            b = ann["box"]
            region = Region(
                tag_id=tags[ann["tag"]].id,
                left=b["left"],
                top=b["top"],
                width=b["width"],
                height=b["height"],
            )
            with open(img_path, "rb") as f:
                entries.append(ImageFileCreateEntry(
                    name=ann["file"],
                    contents=f.read(),
                    regions=[region],
                ))

        print()
        print(f"   Uploading {len(entries)} annotated image(s) in batches of 64...")
        uploaded = 0
        for i in range(0, len(entries), 64):
            batch = ImageFileCreateBatch(images=entries[i:i+64])
            result = trainer.create_images_from_files(project.id, batch)
            if not result.is_batch_successful:
                failed = [img for img in result.images
                          if img.status not in ("OK", "OKDuplicate")]
                if failed:
                    print(f"   ⚠️   {len(failed)} image(s) failed:")
                    for img in failed:
                        print(f"        {img.source_url}: {img.status}")
            uploaded += len(entries[i:i+64])
            print(f"   ✅  Batch {i//64+1} done — {uploaded}/{len(entries)}")
        print(f"   ✅  Upload complete.")

    # ── Confirm counts ────────────────────────────────────────
    print()
    print("  Final uploaded counts:")
    for tag_name in tag_names:
        count = trainer.get_tagged_image_count(project.id, tag_ids=[tags[tag_name].id])
        ok = "✅" if count >= MIN_IMAGES_PER_TAG else "❌"
        print(f"    {ok}  {tag_name:12s}: {count}")

    # ── Train ─────────────────────────────────────────────────
    print()
    print("🧠  Starting training...")
    print("    Object Detection training typically takes 5-15 minutes.")

    iterations = trainer.get_iterations(project.id)
    try:
        iteration = trainer.train_project(project.id)
    except Exception as e:
        err = str(e)
        if "Not enough images" in err:
            print(f"❌  Not enough images: {err}")
            sys.exit(1)
        elif "Nothing changed since last training" in err or \
             "already" in err.lower() or "up-to-date" in err.lower():
            completed = sorted(
                [it for it in iterations if it.status == "Completed"],
                key=lambda it: it.last_modified or "", reverse=True
            )
            if completed:
                iteration = completed[0]
                print(f"   ℹ️   Nothing changed — using existing iteration: {iteration.id}")
            else:
                print("❌  No completed iterations and training is up-to-date.")
                sys.exit(1)
        else:
            raise

    # Poll
    while iteration.status not in ("Completed", "Failed"):
        hint = ""
        if getattr(iteration, "training_error_details", None):
            hint = f"  ⚠️  {iteration.training_error_details}"
        print(f"   Status: {iteration.status} — waiting 15s...{hint}")
        time.sleep(15)
        iteration = trainer.get_iteration(project.id, iteration.id)

    if iteration.status == "Failed":
        print("❌  Training failed.")
        if getattr(iteration, "training_error_details", None):
            print(f"  Reason : {iteration.training_error_details}")
        print()
        print("  Full iteration diagnostics:")
        for attr in sorted(vars(iteration)):
            if not attr.startswith("_"):
                val = getattr(iteration, attr, None)
                if val is not None:
                    print(f"    {attr}: {val}")
        print()
        print("  Uploaded counts at failure:")
        for tag_name in tag_names:
            count = trainer.get_tagged_image_count(project.id, tag_ids=[tags[tag_name].id])
            print(f"    {'✅' if count >= MIN_IMAGES_PER_TAG else '❌'}  {tag_name}: {count}")
        sys.exit(1)

    print(f"✅  Training complete!")

    # ── Publish ───────────────────────────────────────────────
    print(f"📢  Publishing as '{PUBLISH_NAME}'...")

    prediction_endpoint = os.environ.get("CUSTOM_VISION_PREDICTION_ENDPOINT", "")
    subscription_id     = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
    resource_group      = os.environ.get("AZURE_RESOURCE_GROUP", "")
    resource_prefix     = os.environ.get("RESOURCE_PREFIX", "")

    if not subscription_id or not resource_group:
        print("⚠️   Missing AZURE_SUBSCRIPTION_ID or AZURE_RESOURCE_GROUP — skipping publish.")
        print("    Publish manually at https://customvision.ai")
        _write_project_id(project.id)
        return

    match = re.search(r"https://(.+?)\.cognitiveservices", prediction_endpoint)
    if match:
        pred_resource_name = match.group(1)
    elif resource_prefix:
        pred_resource_name = f"{resource_prefix}-vision-pred"
        print(f"   ℹ️   Using resource name from prefix: {pred_resource_name}")
    else:
        print("⚠️   Cannot determine prediction resource name. Publish manually.")
        _write_project_id(project.id)
        return

    pred_resource_id = (
        f"/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group}"
        f"/providers/Microsoft.CognitiveServices/accounts/{pred_resource_name}"
    )

    try:
        trainer.publish_iteration(project.id, iteration.id, PUBLISH_NAME, pred_resource_id)
        print(f"✅  Published as '{PUBLISH_NAME}'")
    except Exception as e:
        if "already published" in str(e).lower():
            print(f"✅  Already published as '{PUBLISH_NAME}'")
        else:
            print(f"⚠️   Publish failed: {e}")
            print("    Publish manually at https://customvision.ai")

    _write_project_id(project.id)
    print()
    print("=" * 50)
    print("  Done! Object Detection model ready.")
    print()
    print("  Next: python app/main.py --demo")
    print("=" * 50)


def _write_project_id(project_id: str):
    env_path = ROOT / ".env"
    content  = env_path.read_text()
    if "CUSTOM_VISION_PROJECT_ID=" in content:
        content = re.sub(
            r"^CUSTOM_VISION_PROJECT_ID=.*$",
            f"CUSTOM_VISION_PROJECT_ID={project_id}",
            content, flags=re.MULTILINE
        )
    else:
        content += f"\nCUSTOM_VISION_PROJECT_ID={project_id}\n"
    env_path.write_text(content)
    print(f"   Project ID: {project_id}")


if __name__ == "__main__":
    main()

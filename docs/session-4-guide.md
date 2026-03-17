# Session 4 Facilitator Guide
## Full Example — Part 1: Building the Pipeline

**Duration:** 1 hour  
**Format:** Virtual Instructor-Led (vILT), up to 50 participants  
**Prerequisites:** Sessions 1–3 complete; Azure resources deployed via `deploy.sh`

---

## Learning Objectives

By the end of this session, participants will be able to:
- Build a Python program that selects and uploads an image to Azure Blob Storage
- Connect Azure Custom Vision Object Detection to a local application via API
- Run Custom Vision and Document Intelligence models in sequence
- Save results to a database and understand the document schema

---

## Pre-Session Checklist (Instructor)

- [ ] `deploy.sh` run successfully — `.env` fully populated
- [ ] `generate_sample_images.py` run — `sample-images/` has 80 PNGs + `annotations.json`
- [ ] `setup_custom_vision.py` run — model trained and published as `demov1`
- [ ] `pip install -r app/requirements.txt` complete
- [ ] Smoke test: `python app/main.py --image sample-images/mixed_shapes_and_text.png` — no errors
- [ ] Azure Portal open — resource group visible with all 5 resources

> **Important:** Custom Vision Object Detection training takes 5–20 minutes. Run `setup_custom_vision.py` at least 30 minutes before the session, not during it.

---

## Session Outline

### 00:00 – 00:05 | Recap & Context (5 min)

Briefly recap Session 3 (API access, deployment patterns). Today we build the complete end-to-end workflow that ties everything together — each step hands its output to the next.

---

### 00:05 – 00:15 | Step 1: Selecting and Uploading an Image (10 min)

**Open:** `app/uploader.py`

Walk through the upload:

```python
client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
container = client.get_container_client("demo-images")

with open(image_path, "rb") as data:
    blob_client.upload_blob(data, overwrite=True)
```

**Key teaching points:**
- Connection strings vs managed identity — connection strings are fine for demos; production should use managed identity
- `overwrite=True` — important for re-running without errors
- Blob names use a timestamp prefix so each run produces a uniquely named blob

**Live demo:** Show the `demo-images` container in Azure Portal before and after running Step 1.

---

### 00:15 – 00:35 | Step 2: Custom Vision Object Detection (20 min)

**Open:** `app/vision.py`

```python
predictor = CustomVisionPredictionClient(PREDICTION_ENDPOINT, credentials)
results = predictor.detect_image(PROJECT_ID, PUBLISH_NAME, img_data)
```

Explain the response — each prediction has:
- `tag_name` — what was detected (`circle`, `rectangle`, `triangle`, `text`)
- `probability` — confidence score (0.0–1.0); filtered to ≥ 0.4 in `vision.py`
- `bounding_box` — normalised coordinates: `left`, `top`, `width`, `height` as fractions of image size (0–1)

**Key teaching points:**

*Object Detection vs Classification:*
- Classification answers "what is this image?" — one tag per whole image
- Object Detection answers "what is in this image, and where?" — bounding box per object
- We use Object Detection because we want to locate shapes, not just name them

*Normalised coordinates:*

```
left=0.175, top=0.175, width=0.650, height=0.650
```

These are fractions of the image dimensions — a circle centred at (200,200) with radius 130 in a 400×400 image gives `left = (200-130)/400 = 0.175`. This makes the model resolution-independent.

*Training data:*  
Show `sample-images/annotations.json` — the bounding boxes in this file were computed from the exact pixel coordinates used when drawing each shape in `generate_sample_images.py`. The model learns from precisely labelled data.

**Discussion question:** *Why does the model return results above a threshold rather than just the top-1 prediction?*  
Answer: Object Detection can find multiple objects in the same image. The `mixed_shapes_and_text.png` demo image contains a circle, rectangle, and triangle simultaneously — all three should be returned.

**Live demo:** Run `python app/main.py --image sample-images/mixed_shapes_and_text.png` and show the bounding box output.

---

### 00:35 – 00:45 | Step 3: Document Intelligence OCR (10 min)

**Open:** `app/document_intel.py`

```python
poller = client.begin_analyze_document("prebuilt-read", f)
result = poller.result()
```

Show the async polling pattern — the service processes in the background and we poll for completion. Walk through `result.pages`, `page.lines`, `line.content`.

**Key teaching points:**
- `prebuilt-read` is a general OCR model — works on any printed text
- Line-level confidence is not returned by this model (the code shows `n/a`) — word-level confidence is available in `result["words"]`
- The polygon coordinates per line allow precise text location on the image

**Discussion question:** *What's the difference between `prebuilt-read` and `prebuilt-document`?*  
Answer: `read` = general OCR for any text. `document` = structured extraction (key-value pairs, tables) optimised for forms, invoices, and structured documents.

---

### 00:45 – 00:55 | Step 4: Saving Results to Cosmos DB (10 min)

**Open:** `app/database.py`

The database stores everything as a single JSON document per run:

```json
{
  "id": "20251201_103045",
  "run_id": "20251201_103045",
  "image_name": "mixed_shapes_and_text.png",
  "blob_url": "https://...",
  "created_at": "2025-12-01T10:30:45Z",
  "vision": [
    { "tag": "circle", "probability": 0.97,
      "bounding_box": { "left": 0.175, "top": 0.175, "width": 0.65, "height": 0.65 } }
  ],
  "ocr_lines": [
    { "line_number": 1, "content": "Shape Detection + OCR Demo", "page": 1 }
  ]
}
```

**Key teaching points:**
- Cosmos DB uses a document model — all related data for a run lives in one document, no joins needed
- `run_id` is both the document `id` and the partition key — this is required for Cosmos DB point reads
- The three `insert_*` methods use read-modify-write: fetch the doc, add the new data, replace it

**Why Cosmos DB instead of Azure SQL?**  
Azure SQL has subscription-level provisioning restrictions (`ProvisioningDisabled`) on MSDN and many EA subscription types. The restriction applies in all regions and cannot be worked around — it requires a Microsoft support request to lift. Cosmos DB has no such restrictions, deploys everywhere, and has a genuine $0/month free tier.

**Show in Azure Portal:** Navigate to the Cosmos DB account → Data Explorer → `aidemodb` → `pipeline_runs` → Items. The document from the current run should be visible.

---

### 00:55 – 01:00 | Wrap-Up & Preview (5 min)

**What we built:**
- Image upload → Blob Storage ✅
- Object detection with bounding boxes → Custom Vision ✅
- OCR text extraction → Document Intelligence ✅
- Results persisted → Cosmos DB ✅

**Session 5 preview:** Extract the results back out of the database, display them in a formatted terminal table, generate an HTML report, and review what the solution actually costs in Azure.

---

## Troubleshooting Reference

| Issue | Likely cause | Fix |
|-------|-------------|-----|
| `CUSTOM_VISION_PROJECT_ID not set` | Setup script not run | Run `python scripts/setup_custom_vision.py` |
| `Invalid project type for operation` | Old Classification project still exists | Re-run `setup_custom_vision.py` — it detects and recreates as Object Detection |
| No shapes detected (empty results) | Model below 0.4 threshold, or not published | Check `.env` `CUSTOM_VISION_PUBLISH_NAME` = `demov1`; lower `CONFIDENCE_THRESHOLD` in `vision.py` if needed |
| `CosmosResourceNotFoundError` | Container doesn't exist | Re-run `deploy.sh` or `db.ensure_tables()` creates it |
| `KeyError: COSMOS_ENDPOINT` | Deploy script didn't write to `.env` | Check `.env` — re-run `deploy.sh` |

# Session 4 Facilitator Guide
## Full Example — Part 1: Building the Pipeline

**Duration:** 1 hour  
**Format:** Virtual Instructor-Led (vILT), up to 50 participants  
**Prerequisites:** Sessions 1–3 complete; Azure resources deployed via `deploy.sh`

---

## Learning Objectives

By the end of this session, participants will be able to:
- Build a small Python program that selects and uploads an image to Azure Blob Storage
- Configure Azure Storage for use as model input
- Run Custom Vision and Document Intelligence models in sequence
- Create and connect an Azure SQL database for storing results

---

## Pre-Session Checklist (Instructor)

- [ ] Run `./scripts/deploy.sh` — all resources provisioned and `.env` populated
- [ ] Run `python scripts/setup_custom_vision.py` — model trained and published
- [ ] Run `cd app && pip install -r requirements.txt`
- [ ] Verify `.env` has all keys populated (no blank values)
- [ ] Test the pipeline with `python app/main.py --demo` — no errors
- [ ] Open Azure Portal — have the resource group visible on screen
- [ ] Have `sample-images/` open in file explorer for image selection demo

---

## Session Outline

### 00:00 – 00:05 | Recap & Context (5 min)

Briefly recap Session 3 (API access, deployment). Today we start building the complete end-to-end example that ties everything together.

**Key message:** We're not learning isolated services today — we're building a *system*. Each component hands off to the next.

---

### 00:05 – 00:15 | Step 1: Selecting and Uploading an Image (10 min)

**Open:** `app/uploader.py`

Walk through the upload flow:

```python
# 1. Connect to storage using the connection string
client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)

# 2. Get a reference to the container
container = client.get_container_client("demo-images")

# 3. Upload the file
with open(image_path, "rb") as data:
    blob_client.upload_blob(data, overwrite=True)
```

**Key teaching points:**
- Connection strings vs. managed identity (connection strings are fine for demos; use managed identity in production)
- `overwrite=True` — important for re-running the demo without errors
- Blob naming strategy: we prefix with a timestamp to keep runs separate

**Live demo:** Show the container in Azure Portal before and after running the upload step.

---

### 00:15 – 00:30 | Step 2: Connecting to Azure AI Models (15 min)

**Open:** `app/vision.py` and `app/document_intel.py`

**Custom Vision — Shape Detection**

```python
predictor = CustomVisionPredictionClient(PREDICTION_ENDPOINT, credentials)
results = predictor.detect_image(PROJECT_ID, PUBLISH_NAME, img_data)
```

Show the response structure — each prediction has:
- `tag_name` — what was detected
- `probability` — confidence score (0.0–1.0)
- `bounding_box` — normalized coordinates (left, top, width, height)

**Discussion question:** *Why are bounding box coordinates normalized (0–1) rather than pixels?*  
Answer: Resolution-independent — same model works on 100×100 and 4000×3000 images.

**Document Intelligence — OCR**

```python
poller = client.begin_analyze_document("prebuilt-read", f)
result = poller.result()
```

Explain the async polling pattern — the service processes asynchronously and we poll for completion. Show `result.pages`, `page.lines`, `line.content`.

**Discussion question:** *What's the difference between `prebuilt-read` and `prebuilt-document`?*  
Answer: `read` = general OCR for any text. `document` = structured extraction (key-value pairs, tables) optimized for forms.

---

### 00:30 – 00:45 | Step 3: Database Setup (15 min)

**Open:** `app/database.py`

Walk through the three tables:

| Table | Purpose |
|-------|---------|
| `pipeline_runs` | One row per execution — image name, blob URL, timestamp |
| `vision_detections` | One row per detected shape — tag, confidence, bounding box |
| `doc_intel_lines` | One row per OCR line — text content, page number |

Show the DDL:

```sql
-- Idempotent — safe to run multiple times
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pipeline_runs')
CREATE TABLE pipeline_runs (
    id         INT IDENTITY(1,1) PRIMARY KEY,
    run_id     NVARCHAR(50),
    image_name NVARCHAR(500),
    blob_url   NVARCHAR(2000),
    created_at DATETIME2 DEFAULT GETUTCDATE()
);
```

**Key teaching points:**
- `IF NOT EXISTS` guard — idempotent schema migrations
- `IDENTITY(1,1)` — auto-increment primary key
- Foreign key from `vision_detections.run_id` → `pipeline_runs.id`
- `GETUTCDATE()` default — always store UTC in the database

**Cost note:** Azure SQL Serverless autopause — first query after idle warms up in ~60 seconds. Warn participants before the demo so the pause doesn't cause confusion.

---

### 00:45 – 00:55 | Step 4: Running the Full Session 4 Pipeline (10 min)

**Live demo — run together:**

```bash
cd app
python main.py
```

Select a sample image from the menu. Walk through the terminal output step by step:
1. ✅ Upload confirmation + blob URL
2. 🔷 Vision detections printed
3. 📄 OCR lines printed
4. ✅ Database save confirmation

**Show in Azure Portal:**
- Blob container — new file appears
- SQL Database — query `SELECT * FROM pipeline_runs` via Query Editor

---

### 00:55 – 01:00 | Wrap-Up & Preview (5 min)

**What we built today:**
- Image upload → Blob Storage ✅
- Shape detection via Custom Vision ✅
- Text extraction via Document Intelligence ✅
- Database tables created and results saved ✅

**Session 5 preview:** We'll extract the results back out, display them in the program interface, generate the HTML report, and review what this solution actually costs in Azure.

**Homework (optional):** Add a second sample image to `sample-images/` and run the pipeline again. Look at the database — do you see both runs?

---

## Troubleshooting Reference

| Issue | Likely cause | Fix |
|-------|-------------|-----|
| `CUSTOM_VISION_PROJECT_ID not set` | Setup script not run | Run `python scripts/setup_custom_vision.py` |
| `No shapes detected` | Model not published or wrong `PUBLISH_NAME` | Check `.env` `CUSTOM_VISION_PUBLISH_NAME` matches what was published |
| SQL connection timeout (~60s) | Serverless cold start | Wait — this is expected on first connect |
| `pyodbc.Error: Data source name not found` | ODBC driver not installed | Install [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) |
| `ResourceNotFound` on vision call | Wrong project ID or endpoint | Re-run `setup_custom_vision.py` and check `.env` |

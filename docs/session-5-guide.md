# Session 5 Facilitator Guide
## Full Example — Part 2: Completing the Workflow

**Duration:** 1 hour  
**Format:** Virtual Instructor-Led (vILT), up to 50 participants  
**Prerequisites:** Session 4 complete; at least one successful pipeline run in Cosmos DB

---

## Learning Objectives

By the end of this session, participants will be able to:
- Extract detected shape locations and recognised text from Cosmos DB
- Display results in the program interface (terminal table + HTML report)
- Evaluate the cost of the Azure AI solution
- Understand the complete end-to-end workflow from image to output

---

## Pre-Session Checklist (Instructor)

- [ ] At least one run from Session 4 exists in Cosmos DB
- [ ] `app/output/` directory exists (created automatically on first run)
- [ ] An HTML report from Session 4 is ready to open in a browser
- [ ] Azure Portal open — Cosmos DB Data Explorer visible

---

## Session Outline

### 00:00 – 00:05 | Recap (5 min)

Briefly recap Session 4. Show the Cosmos DB Data Explorer with the stored document — participants can see their Session 4 data is persisted and queryable.

**Show in Azure Portal:**
```
Cosmos DB → Data Explorer → aidemodb → pipeline_runs → Items
```

Click a document to show its full JSON — the `vision` array with bounding boxes and the `ocr_lines` array with extracted text.

---

### 00:05 – 00:20 | Step 1: Extracting & Displaying Results (15 min)

**Open:** `app/database.py` — `print_run_summary()` method

Walk through the two display blocks:

**Vision detections:**
```python
rows = [
    (d["tag"], f"{d['probability']:.1%}",
     f"{d.get('bounding_box',{}).get('left',0):.3f}",
     f"{d.get('bounding_box',{}).get('top',0):.3f}",
     f"{d.get('bounding_box',{}).get('width',0):.3f}",
     f"{d.get('bounding_box',{}).get('height',0):.3f}")
    for d in vision
]
```

**OCR lines:**
```python
rows = [(l["line_number"], l["content"], l.get("page", 1)) for l in lines]
```

**Key teaching point — the bounding box values:**  
The coordinates are normalised (0–1 fractions of image size). Walk through what they mean:

```
circle  97.2%  left=0.175  top=0.175  width=0.650  height=0.650
```

This means: the circle starts 17.5% from the left edge, 17.5% from the top, and occupies 65% of the image width and height. On a 400×400 image: starts at pixel (70, 70), ends at pixel (330, 330).

**Discussion:** How would you use these coordinates in a real application?  
Examples: draw bounding boxes on the image in the UI, crop the detected region for further processing, calculate centre points for spatial analysis.

**Live demo:** Run `python app/main.py --image sample-images/mixed_shapes_and_text.png` and walk through the formatted terminal tables.

---

### 00:20 – 00:35 | Step 2: The HTML Report (15 min)

**Open** the report from `app/output/report_{run_id}.html` in a browser.

Walk through each section:
1. **Header** — run ID and UTC timestamp for traceability
2. **Blob Storage card** — exact URL of the uploaded image
3. **Custom Vision table** — all detections with confidence and all four bounding box coordinates
4. **Document Intelligence table** — every extracted line with page number
5. **Cost Review card** — per-service breakdown

**Open:** `app/report.py` — show how the report is assembled from the `results` dict.

**Key teaching point — the pipeline data flow:**

```python
results = {"run_id": run_id, "image_path": str(image_path)}
results["blob_url"]               = upload_image(image_path)
results["vision"]                 = run_custom_vision(blob_url, image_path)
results["document_intelligence"]  = run_document_intelligence(image_path)
results["costs"]                  = get_cost_summary()
generate_html_report(results, report_path)
```

Each step adds to the same `results` dict. The report reads from the completed dict at the end. This makes each module independently testable and the pipeline easy to extend — add a new service, add a key to `results`, add a card to the report.

**Discussion:** How would you extend this report? Ideas: embed a thumbnail of the image, draw bounding box overlays with canvas/SVG, export as PDF, send by email.

---

### 00:35 – 00:50 | Step 3: Azure Cost Review (15 min)

**Open:** `app/cost_review.py`

Walk through the cost reference table and what the `az consumption usage list` query does.

**Actual cost breakdown for this demo:**

| Service | Free Tier | Projected Cost |
|---------|-----------|----------------|
| Custom Vision (Training) | 5,000 tx/month F0 | **$0** |
| Custom Vision (Prediction) | 10,000 tx/month F0 | **$0** |
| Document Intelligence | 500 pages/month F0 | **$0** |
| Cosmos DB | 1,000 RU/s + 25 GB free | **$0** |
| Blob Storage | < 1 MB | **< $0.01** |
| **Total** | | **~$0** |

**Key message:** When using free tiers and serverless services, a 5-session demo programme with ~50 image runs costs effectively nothing. Production workloads at scale are a very different story — understanding pricing models is essential before you go live.

**Show teardown:**
```bash
./scripts/teardown.sh
```

Explain: after this runs, all resources are deleted and there are **zero ongoing charges**. This is the recommended practice after any short-lived demo or training environment.

---

### 00:50 – 01:00 | Programme Wrap-Up (10 min)

#### Complete File Map

```
azure-ai-demo/
├── app/
│   ├── main.py              ← orchestrates all 7 steps
│   ├── uploader.py          ← Step 1: Blob Storage
│   ├── vision.py            ← Step 2: Custom Vision Object Detection
│   ├── document_intel.py    ← Step 3: Document Intelligence OCR
│   ├── database.py          ← Step 4 & 5: Cosmos DB read/write
│   ├── cost_review.py       ← Step 6: Cost estimation
│   └── report.py            ← Step 7: HTML output
├── infra/
│   └── main.bicep           ← all Azure resources as code
└── scripts/
    ├── deploy.sh            ← one-command deploy
    ├── teardown.sh          ← one-command cleanup
    ├── generate_sample_images.py  ← 80 OD training images + annotations
    └── setup_custom_vision.py     ← train + publish the OD model
```

#### Key Takeaways

**Infrastructure as Code** — Every Azure resource is declared in `main.bicep`. The environment is reproducible, version-controlled, and deployable in under 5 minutes.

**Choose services without provisioning restrictions** — Azure SQL has regional provisioning blocks on many subscription types. Cosmos DB, Cognitive Services, and Blob Storage deploy without issue everywhere. Know your subscription type before designing an architecture.

**Serverless and free tiers** — Cosmos DB serverless costs $0 when idle and cents per million operations when active. F0 Cognitive Services tiers are generous enough for demo and low-volume use.

**Separation of concerns** — Each `app/` module does exactly one thing. The orchestrator connects them. This makes the pipeline easy to test, debug, and extend.

**Object Detection vs Classification** — Classification labels a whole image. Object Detection finds *what* is in an image and *where*, returning normalised bounding box coordinates for each detected object.

#### Suggestions for Further Exploration

- Swap `prebuilt-read` for `prebuilt-invoice` in `document_intel.py` — observe the structured key-value output
- Add a fifth tag to the Custom Vision model (e.g. `ellipse`) and retrain
- Extend `database.py` to also store word-level OCR confidence scores
- Add bounding box overlay drawing to `report.py` using an SVG or canvas element

---

## Troubleshooting Reference

| Issue | Likely cause | Fix |
|-------|-------------|-----|
| HTML report not opening | Pipeline didn't reach Step 7 | Check terminal for errors in earlier steps |
| Cosmos DB results empty | `insert_*` methods didn't run | Ensure no errors in Step 4; check `db.ensure_tables()` ran |
| Cost data shows "unavailable" | Missing Cost Management Reader role | View costs in Azure Portal → Cost Management |
| Vision results all below threshold | Confidence threshold 0.4 is too high for this image | Lower `CONFIDENCE_THRESHOLD` in `vision.py` to `0.2` for testing |
| `KeyError: 'content'` in OCR | Unexpected response structure | Print `doc_results["lines"]` to inspect the raw output |

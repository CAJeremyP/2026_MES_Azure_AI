# Session 5 Facilitator Guide
## Full Example — Part 2: Completing the Workflow

**Duration:** 1 hour  
**Format:** Virtual Instructor-Led (vILT), up to 50 participants  
**Prerequisites:** Session 4 complete; pipeline has run at least once successfully

---

## Learning Objectives

By the end of this session, participants will be able to:
- Extract detected shape locations and recognized text from Azure AI results
- Save structured results into Azure Storage and a SQL database
- Display processed results in the program interface
- Evaluate the cost implications of the Azure AI solution

---

## Pre-Session Checklist (Instructor)

- [ ] At least one successful pipeline run from Session 4 exists in the database
- [ ] `app/output/` directory exists (created automatically on first run)
- [ ] Confirm HTML report was generated in `app/output/` from Session 4
- [ ] Azure Portal open — Cost Management + resource group visible
- [ ] Prepared to open the HTML report in a browser during the demo

---

## Session Outline

### 00:00 – 00:05 | Recap (5 min)

Quickly recap Session 4. We have data flowing in — today we complete the loop: get data *out*, display it meaningfully, and understand what it cost.

**Show the database** in Azure Portal Query Editor:
```sql
SELECT r.run_id, r.image_name, r.created_at,
       COUNT(v.id) AS shapes_detected,
       COUNT(d.id) AS ocr_lines
FROM pipeline_runs r
LEFT JOIN vision_detections v ON v.run_id = r.id
LEFT JOIN doc_intel_lines d   ON d.run_id = r.id
GROUP BY r.run_id, r.image_name, r.created_at
ORDER BY r.created_at DESC;
```

This sets the stage — participants can see their Session 4 data is persisted and queryable.

---

### 00:05 – 00:20 | Step 1: Extracting & Displaying Results (15 min)

**Open:** `app/database.py` — `print_run_summary()` method

Walk through the two queries:

**Query 1 — Vision detections:**
```sql
SELECT tag,
       ROUND(probability * 100, 1) AS pct,
       ROUND(bbox_left, 3), ROUND(bbox_top, 3),
       ROUND(bbox_width, 3), ROUND(bbox_height, 3)
FROM vision_detections
WHERE run_id = ?
ORDER BY probability DESC
```

**Key teaching points:**
- Parameterised queries (`?` placeholder) — never string-concatenate user input into SQL
- `ROUND()` for readable output — raw floats like `0.9872634` aren't presentation-friendly
- `ORDER BY probability DESC` — surface highest-confidence results first

**Query 2 — OCR lines:**
```sql
SELECT line_number, content
FROM doc_intel_lines
WHERE run_id = ?
ORDER BY line_number
```

**Discussion question:** *If we stored `polygon_json` for each OCR line, how could we use that data?*  
Answer: Draw bounding boxes on the image, highlight matched text regions, calculate line spacing to detect columns/tables, etc.

**Live demo:** Run `python main.py` again. Show the `tabulate`-formatted terminal tables — this is the "display in the program interface" outcome from the session objectives.

---

### 00:20 – 00:35 | Step 2: The HTML Report (15 min)

**Open** the generated HTML file from `app/output/` in a browser.

Walk through each section:
1. **Header** — run ID and timestamp for traceability
2. **Blob Storage card** — shows the exact URL of the uploaded image
3. **Custom Vision table** — all detections with confidence and bounding box
4. **Document Intelligence table** — every OCR line with page number
5. **Cost Review card** — service-by-service breakdown

**Open:** `app/report.py` — show how the report is generated from the `results` dict.

**Key teaching point:** The pipeline passes a single `results` dict through every step. Each module adds its output to that dict. The report reads from the completed dict at the end. This is a simple but powerful pattern — it makes the pipeline easy to test and extend.

```python
results = {"run_id": run_id, "image_path": str(image_path)}
# ... each step adds to results ...
results["vision"] = vision_results
results["document_intelligence"] = doc_results
results["costs"] = costs
generate_html_report(results, report_path)
```

**Discussion:** How would you extend this report? Add a thumbnail of the image? Draw the bounding boxes on a canvas overlay? Export to PDF?

---

### 00:35 – 00:50 | Step 3: Azure Cost Review (15 min)

This is a crucial real-world skill — understanding what an AI solution actually costs before it goes to production.

**Open:** `app/cost_review.py` — walk through the free tier limits table.

**Reference the printed cost output from the terminal run.**

#### Free Tier Limits (F0)

| Service | Free Allowance | Overage Price |
|---------|---------------|---------------|
| Custom Vision (Training) | 5,000 transactions/month | $2.00/1,000 |
| Custom Vision (Prediction) | 10,000 transactions/month | $2.00/1,000 |
| Document Intelligence | 500 pages/month | $1.50/1,000 pages |

> ⚠️ F0 tiers are **per Azure subscription**, not per resource. If the subscription already uses Custom Vision F0 elsewhere, deployment will fail. See [docs/risks.md](risks.md).

#### SQL Serverless Pricing (demo SKU: GP_S_Gen5_1)

- Active: ~$0.000145 per vCore-second (~$0.52/hour at 1 vCore)
- Paused: **$0.00** (auto-pauses after 60 minutes idle)
- Storage: $0.115/GB/month (we provisioned 1 GB max → $0.12/month max)

**Discussion question:** *For this demo (5 sessions × 1 hour, ~10 images per session), what would the total cost be?*

Walk through the estimation:
- Custom Vision: ~50 prediction calls → well within free tier → **$0**
- Document Intelligence: ~50 pages → well within free tier → **$0**
- SQL: ~5 hours active + storage → ~**$2.60–3.00**
- Blob Storage: <1 MB data → **< $0.01**

**Total estimated cost: ~$3 for the entire 5-session programme.**

**Key message:** Azure's free tiers and serverless options make AI demos extremely affordable. Production workloads at scale are a different story — always size for expected volume.

**Show teardown command:**
```bash
./scripts/teardown.sh
```

Explain: after running this, there are **zero ongoing charges**. The resource group and everything in it is deleted. This is the recommended practice after any short-lived demo.

---

### 00:50 – 01:00 | Programme Wrap-Up (10 min)

#### What We Built — End to End

```
Local Python App
      │
      ├── app/main.py         ← orchestrator
      ├── app/uploader.py     ← Blob Storage
      ├── app/vision.py       ← Custom Vision
      ├── app/document_intel.py ← Document Intelligence
      ├── app/database.py     ← Azure SQL
      ├── app/cost_review.py  ← Cost Management
      └── app/report.py       ← HTML output
              │
              └── infra/main.bicep  ← all Azure resources as code
```

#### Key Takeaways

1. **Infrastructure as Code** — every Azure resource is defined in `main.bicep`. Reproducible, version-controlled, one-command deploy and teardown.
2. **Serverless where possible** — SQL serverless + F0 tiers = near-zero cost for demos and low-volume workloads.
3. **Separation of concerns** — each module does one thing. The orchestrator (`main.py`) connects them.
4. **Results persistence** — SQL gives us queryable history of every run, not just the last one.
5. **Cost awareness** — understanding the free tier limits and serverless pricing prevents surprise bills.

#### Next Steps for Participants

- Fork the GitHub repo and experiment with different images
- Swap `prebuilt-read` for `prebuilt-invoice` in `document_intel.py` — see what changes
- Add a new table to store full OCR word-level data (the `words` array is already captured)
- Try deploying to a different Azure region and compare latency

---

## Troubleshooting Reference

| Issue | Likely cause | Fix |
|-------|-------------|-----|
| Empty HTML report | Pipeline run didn't complete | Check terminal for errors; re-run `python main.py` |
| SQL results empty | Tables not populated | Ensure `ensure_tables()` and `insert_*()` ran without error |
| Cost data shows "unavailable" | Missing Cost Management Reader role | View costs directly in Azure Portal → Cost Management |
| Report opens but shows "No detections" | Model below confidence threshold (0.4) | Lower `CONFIDENCE_THRESHOLD` in `vision.py` or retrain with more images |

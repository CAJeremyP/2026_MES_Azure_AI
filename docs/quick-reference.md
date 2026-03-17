# Quick Reference — Azure AI Demo

## All Commands At A Glance

```bash
# ── First-time setup ──────────────────────────────────────────
cp .env.example .env
# Edit .env: set AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP,
#            AZURE_LOCATION, RESOURCE_PREFIX

./scripts/deploy.sh                         # Deploy all Azure resources (~3-5 min)

python scripts/generate_sample_images.py   # Generate 80 training images + annotations.json
python scripts/setup_custom_vision.py      # Upload images, train OD model, publish (~5-15 min)

pip install -r app/requirements.txt        # Install Python dependencies

# ── Run the demo ──────────────────────────────────────────────
python app/main.py                         # Interactive — pick an image from the menu
python app/main.py --demo                  # Auto-run first two sample images
python app/main.py --image path/to/img.png # Run on a specific image

# ── Teardown (run after every session!) ──────────────────────
./scripts/teardown.sh                      # Delete all Azure resources
```

---

## Key Files

| File | Purpose |
|------|---------|
| `.env` | All secrets and config — **never commit this** |
| `infra/main.bicep` | All Azure resources as code |
| `app/main.py` | Pipeline orchestrator — 7-step workflow |
| `app/uploader.py` | Blob Storage upload |
| `app/vision.py` | Custom Vision object detection |
| `app/document_intel.py` | Document Intelligence OCR |
| `app/database.py` | Cosmos DB — read/write pipeline results |
| `app/cost_review.py` | Azure cost estimation |
| `app/report.py` | HTML report generator |
| `app/output/` | Generated HTML reports (gitignored) |
| `sample-images/annotations.json` | Bounding box annotations for OD training |

---

## Azure Resources Deployed

| Resource | Type | SKU | Purpose |
|----------|------|-----|---------|
| `{prefix}stor...` | Storage Account | Standard LRS | Blob container for uploaded images |
| `{prefix}-vision-train` | Cognitive Services | F0 (free) | Custom Vision training |
| `{prefix}-vision-pred` | Cognitive Services | F0 (free) | Custom Vision object detection |
| `{prefix}-docintel` | Cognitive Services | F0 (free) | Document Intelligence OCR |
| `{prefix}-cosmos-...` | Cosmos DB | Serverless + free tier | Pipeline results storage |

> **Note:** Cosmos DB replaced Azure SQL due to regional provisioning restrictions on many subscription types. See [risks.md](risks.md) for details.

---

## Pipeline Steps

| Step | Module | What it does |
|------|--------|-------------|
| 1 | `uploader.py` | Upload image to Azure Blob Storage |
| 2 | `vision.py` | Detect shapes with bounding boxes (Custom Vision OD) |
| 3 | `document_intel.py` | Extract text lines and words (prebuilt-read) |
| 4 | `database.py` | Save run + all results to Cosmos DB |
| 5 | `database.py` | Print results summary to terminal |
| 6 | `cost_review.py` | Show Azure cost breakdown |
| 7 | `report.py` | Generate HTML report in `app/output/` |

---

## .env Variables Reference

| Variable | Set by | Description |
|----------|--------|-------------|
| `AZURE_SUBSCRIPTION_ID` | You | Your Azure subscription GUID |
| `AZURE_RESOURCE_GROUP` | You | Resource group name |
| `AZURE_LOCATION` | You | Azure region (e.g. `eastus`) |
| `RESOURCE_PREFIX` | You | 3–8 lowercase letters, no hyphens |
| `STORAGE_ACCOUNT_NAME` | `deploy.sh` | Auto-populated |
| `STORAGE_CONNECTION_STRING` | `deploy.sh` | Auto-populated |
| `CUSTOM_VISION_TRAINING_KEY` | `deploy.sh` | Auto-populated |
| `CUSTOM_VISION_PREDICTION_KEY` | `deploy.sh` | Auto-populated |
| `CUSTOM_VISION_PROJECT_ID` | `setup_custom_vision.py` | Auto-populated after training |
| `CUSTOM_VISION_PUBLISH_NAME` | You (default: `demov1`) | Published iteration name |
| `DOCUMENT_INTELLIGENCE_KEY` | `deploy.sh` | Auto-populated |
| `COSMOS_ENDPOINT` | `deploy.sh` | Auto-populated |
| `COSMOS_KEY` | `deploy.sh` | Auto-populated |
| `COSMOS_DATABASE_NAME` | `deploy.sh` | Auto-populated (default: `aidemodb`) |

---

## Cosmos DB Document Schema

Each pipeline run is stored as a single JSON document in the `pipeline_runs` container:

```json
{
  "id": "20251201_103045",
  "run_id": "20251201_103045",
  "image_name": "/path/to/circle_01.png",
  "blob_url": "https://{account}.blob.core.windows.net/demo-images/...",
  "created_at": "2025-12-01T10:30:45Z",
  "vision": [
    {
      "tag": "circle",
      "probability": 0.9721,
      "bounding_box": { "left": 0.175, "top": 0.175, "width": 0.65, "height": 0.65 }
    }
  ],
  "ocr_lines": [
    { "line_number": 1, "content": "Azure AI Demo", "page": 1 }
  ]
}
```

---

## Useful Azure CLI Commands

```bash
# Check all resources are deployed
az resource list --resource-group rg-ai-demo -o table

# View Cosmos DB documents (Azure Portal → Data Explorer is easier)
az cosmosdb sql query \
  --account-name {cosmos-account} \
  --resource-group rg-ai-demo \
  --database-name aidemodb \
  --container-name pipeline_runs \
  --query-text "SELECT * FROM c ORDER BY c.created_at DESC OFFSET 0 LIMIT 5"

# Verify teardown complete
az group show --name rg-ai-demo
# Should return: ResourceGroupNotFound
```

---

## Estimated Costs

| Scenario | Estimated Total |
|----------|----------------|
| 5-session programme (all F0 free tiers + free Cosmos) | ~$0.00 |
| If Cosmos free tier already used (serverless billing) | ~$0.50–2.00 |
| After teardown | **$0.00** |

See [cost-estimate.md](cost-estimate.md) for full breakdown.

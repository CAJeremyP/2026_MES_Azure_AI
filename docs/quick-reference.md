# Quick Reference — Azure AI Demo

## All Commands At A Glance

```bash
# ── First-time setup ──────────────────────────────────────────
cp .env.example .env              # 1. Copy config template
# (edit .env — set AZURE_SUBSCRIPTION_ID and RESOURCE_PREFIX)

./scripts/deploy.sh               # 2. Deploy all Azure resources
                                  #    (~3-5 min, populates .env)

pip install Pillow                # 3a. Generate sample images
python scripts/generate_sample_images.py

python scripts/setup_custom_vision.py  # 3b. Train Custom Vision model
                                       #     (~5-15 min)

cd app && pip install -r requirements.txt  # 4. Install app dependencies

# ── Run the demo ──────────────────────────────────────────────
python app/main.py                # Interactive — pick an image
python app/main.py --demo         # Auto-run all sample images
python app/main.py --image path/to/image.png  # Specific image

# ── Teardown (run after every session!) ──────────────────────
./scripts/teardown.sh             # Delete all Azure resources
```

---

## Key Files

| File | Purpose |
|------|---------|
| `.env` | All secrets and config — **never commit this** |
| `infra/main.bicep` | All Azure resources defined as code |
| `app/main.py` | Pipeline orchestrator — start here |
| `app/uploader.py` | Blob Storage upload |
| `app/vision.py` | Custom Vision shape detection |
| `app/document_intel.py` | Document Intelligence OCR |
| `app/database.py` | Azure SQL — schema + queries |
| `app/cost_review.py` | Azure cost estimation |
| `app/report.py` | HTML report generator |
| `app/output/` | Generated HTML reports (gitignored) |

---

## Key Azure Resources

| Resource | Type | Purpose |
|----------|------|---------|
| `{prefix}stor...` | Storage Account | Blob container for images |
| `{prefix}-vision-train` | Cognitive Services | Custom Vision training |
| `{prefix}-vision-pred` | Cognitive Services | Custom Vision prediction |
| `{prefix}-docintel` | Cognitive Services | Document Intelligence OCR |
| `{prefix}-sql-...` | SQL Server | Database host |
| `aidemodb` | SQL Database (Serverless) | Results storage |

---

## .env Variables Reference

| Variable | Set by | Description |
|----------|--------|-------------|
| `AZURE_SUBSCRIPTION_ID` | You | Your Azure subscription GUID |
| `AZURE_RESOURCE_GROUP` | You | Resource group name (default: `rg-ai-demo`) |
| `RESOURCE_PREFIX` | You | 3–8 lowercase letters |
| `STORAGE_ACCOUNT_NAME` | `deploy.sh` | Auto-populated |
| `STORAGE_CONNECTION_STRING` | `deploy.sh` | Auto-populated |
| `CUSTOM_VISION_TRAINING_KEY` | `deploy.sh` | Auto-populated |
| `CUSTOM_VISION_PREDICTION_KEY` | `deploy.sh` | Auto-populated |
| `CUSTOM_VISION_PROJECT_ID` | `setup_custom_vision.py` | Auto-populated after training |
| `DOCUMENT_INTELLIGENCE_KEY` | `deploy.sh` | Auto-populated |
| `SQL_CONNECTION_STRING` | `deploy.sh` | Auto-populated |

---

## Useful Azure CLI Commands

```bash
# Check deployment status
az deployment group show --resource-group rg-ai-demo --name main

# List all resources in the group
az resource list --resource-group rg-ai-demo -o table

# View SQL tables (Azure Portal → SQL Database → Query Editor)
SELECT * FROM pipeline_runs ORDER BY created_at DESC;
SELECT * FROM vision_detections WHERE run_id = 1;
SELECT * FROM doc_intel_lines WHERE run_id = 1;

# Check Custom Vision projects
az cognitiveservices account list --resource-group rg-ai-demo -o table

# Verify teardown complete
az group show --name rg-ai-demo   # Should return ResourceGroupNotFound
```

---

## Estimated Costs

| Scenario | Estimated Cost |
|----------|---------------|
| 5-session programme (all F0 free tiers) | ~$1.50–$3.00 total |
| If F0 tiers already used (S0 pricing) | ~$2.00–$5.00 total |
| Per hour of SQL active time | ~$0.26 (0.5 vCore serverless) |
| After teardown | **$0.00** |

See [docs/cost-estimate.md](docs/cost-estimate.md) for full breakdown.

# Cost Estimate

Breakdown of Azure services used, their pricing tiers, and projected cost for the 5-session QA programme.

---

## Services & Tiers

| Service | SKU | Reason |
|---------|-----|--------|
| Azure Blob Storage | Standard LRS | Cheapest redundancy; demo images only |
| Custom Vision Training | F0 (free) | 5,000 transactions/month — well within demo use |
| Custom Vision Prediction | F0 (free) | 10,000 transactions/month — well within demo use |
| Document Intelligence | F0 (free) | 500 pages/month — well within demo use |
| Azure Cosmos DB | Serverless + free tier | No regional restrictions; free tier = $0/month |

> **Note:** Azure SQL was evaluated and removed. It has provisioning restrictions (`ProvisioningDisabled`) on MSDN, Visual Studio, and many EA subscription types that cannot be worked around by switching regions. Cosmos DB was chosen as the replacement — it has no such restrictions, no ODBC driver requirement, and a genuine free tier.

---

## Free Tier Limits

> F0 tiers are **per Azure subscription**. If the subscription already uses these services at F0, use S0 paid tiers. Cost impact for demo volumes is under $1. See [risks.md](risks.md).

| Service | Free Tier Limit | Overage Rate |
|---------|----------------|-------------|
| Custom Vision Training | 5,000 transactions/month | $2.00 / 1,000 |
| Custom Vision Prediction | 10,000 transactions/month | $2.00 / 1,000 |
| Document Intelligence | 500 pages/month | $1.50 / 1,000 pages |
| Cosmos DB | 1,000 RU/s + 25 GB | Serverless: ~$0.25 / 1M RUs |
| Blob Storage | 5 GB (new accounts, 12 months) | $0.018/GB/month |

---

## Cost Projection — 5-Session Programme

Assumptions: 5 sessions × 1 hour, ~10 image runs per session, up to 50 participants observing.

| Service | Usage | Cost |
|---------|-------|------|
| Custom Vision Prediction | ~50 `detect_image` calls | **$0** (F0 free tier) |
| Custom Vision Training | 1 training run, ~80 images | **$0** (F0 free tier) |
| Document Intelligence | ~50 pages | **$0** (F0 free tier) |
| Cosmos DB | ~80 documents written + read | **$0** (free tier RUs) |
| Blob Storage | <5 MB images | **< $0.01** |
| **Total** | | **~$0.00** |

If Cosmos DB free tier is already used by another resource in the subscription, serverless billing applies instead:

| Service | Usage | Cost |
|---------|-------|------|
| Cosmos DB (serverless) | ~80 document ops at ~10 RUs each | **< $0.01** |
| **Total with serverless Cosmos** | | **~$0.01** |

---

## Cost Control Measures

All cost control is built into the deployed resources and does not require manual intervention:

**Cosmos DB** — Serverless mode means zero cost when idle. The `deploy.sh` script automatically checks whether your subscription already has a free-tier Cosmos account and sets `enableFreeTier=false` if so, falling back to serverless.

**Custom Vision F0** — Hard rate limit of 10 TPS on the prediction endpoint. Appropriate for a live demo; cannot accidentally generate large bills.

**Blob Storage LRS** — No geo-replication; cheapest storage tier. Demo images are small PNGs, so storage cost is negligible regardless.

**One-command teardown** — `teardown.sh` deletes the entire resource group, stopping all charges immediately after the session.

---

## Post-Demo Teardown

```bash
./scripts/teardown.sh
```

Verify deletion:
```bash
az group show --name rg-ai-demo
# Expected: ResourceGroupNotFound error
```

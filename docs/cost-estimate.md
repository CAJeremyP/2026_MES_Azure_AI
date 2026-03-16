# Cost Estimate

This document explains the pricing for all Azure services used in the demo and gives a realistic cost projection for the 5-session QA programme.

---

## Services Used & Tier Selection

| Service | SKU Chosen | Reason |
|---------|-----------|--------|
| Azure Blob Storage | Standard LRS | Cheapest redundancy; demo data has no DR requirement |
| Custom Vision (Training) | F0 | Free tier — 5,000 tx/month; ample for demo training |
| Custom Vision (Prediction) | F0 | Free tier — 10,000 tx/month |
| Document Intelligence | F0 | Free tier — 500 pages/month |
| Azure SQL Database | GP_S_Gen5_1 Serverless | Auto-pauses when idle; pay-per-second when active |

---

## Free Tier Limits

> Free tiers (F0) are **per Azure subscription**. If the org's subscription already uses these services at F0, you'll need to use S0 paid tiers. See [risks.md](risks.md).

| Service | Free Tier Limit | Overage |
|---------|----------------|---------|
| Custom Vision Training | 5,000 transactions/month | $2.00 / 1,000 |
| Custom Vision Prediction | 10,000 transactions/month | $2.00 / 1,000 |
| Document Intelligence | 500 pages/month | $1.50 / 1,000 pages |
| Blob Storage | 5 GB free (new accounts, 12 months) | $0.018/GB/month |

---

## Cost Projection — 5-Session Programme

Assumptions: 5 sessions × 1 hour, ~10 image runs per session, ~50 participants observing.

| Service | Usage | Cost |
|---------|-------|------|
| Custom Vision Prediction | ~50 prediction calls | **$0** (within F0 free tier) |
| Custom Vision Training | 1 training run | **$0** (within F0 free tier) |
| Document Intelligence | ~50 pages | **$0** (within F0 free tier) |
| Azure SQL Serverless | ~5 hours active @ 0.5 vCore avg | **~$1.30** |
| SQL Storage | 1 GB provisioned × ~2 months | **~$0.23** |
| Blob Storage | <5 MB images | **~$0.01** |
| **Total** | | **~$1.50 – $3.00** |

---

## If Free Tiers Are Unavailable

If F0 is already in use on the subscription, the next tier is S0 (paid):

| Service | S0 Price |
|---------|---------|
| Custom Vision Training | $2.00 / 1,000 transactions |
| Custom Vision Prediction | $2.00 / 1,000 transactions |
| Document Intelligence | $1.50 / 1,000 pages |

Even at S0, the 5-session demo would cost under **$1.00 additional** at the volumes above.

---

## Cost Control Measures Built Into This Demo

1. **SQL Serverless autopause** — database pauses after 60 minutes idle. Zero compute charges while paused.
2. **SQL min capacity 0.5 vCore** — scales down to 0.5 vCore when lightly loaded (half the cost of minimum fixed tier).
3. **1 GB SQL max size** — prevents unexpected storage growth.
4. **LRS blob storage** — locally redundant only; no geo-replication charges.
5. **One-command teardown** — `teardown.sh` deletes the entire resource group, stopping all charges immediately.

---

## Post-Demo Teardown Reminder

```bash
# Run this immediately after the last session
./scripts/teardown.sh
```

Verify deletion:
```bash
az group show --name rg-ai-demo
# Should return: "error": {"code": "ResourceGroupNotFound", ...}
```

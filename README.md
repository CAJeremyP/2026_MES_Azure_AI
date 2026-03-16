# Azure AI End-to-End Solution Demo
### Sessions 4 & 5 — QA Learning Program

A working end-to-end Azure AI pipeline that:
1. Uploads an image via a local Python app
2. Stores it in Azure Blob Storage
3. Runs **Custom Vision** (object/shape detection) and **Azure Document Intelligence** (OCR/text extraction) in sequence
4. Saves results to an **Azure SQL Database**
5. Displays results back in the app UI
6. Includes a **cost review** of the deployed solution

This project is designed for **short-lived demo use only** — all services are sized to minimize cost, and one-command teardown is provided.

---

## 📋 Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.10+ | [python.org](https://python.org) |
| Azure CLI | Latest | `winget install Microsoft.AzureCLI` |
| Azure subscription | — | [portal.azure.com](https://portal.azure.com) |

> **Cost estimate for demo:** ~$1–5 USD total for a few hours of use. See [docs/cost-estimate.md](docs/cost-estimate.md).

---

## 🚀 Quick Start (5 minutes)

### 1. Clone & configure
```bash
git clone https://github.com/CAJeremyP/2026_MES_Azure_AI.git
cd 2026_MES_Azure_AI
cp .env.example .env
# Edit .env — set your Azure subscription ID and a unique prefix
```

### 2. Deploy all Azure resources
```bash
./scripts/deploy.sh        # Linux/macOS
scripts\deploy.bat         # Windows
```

### 3. Run the app
```bash
cd app
pip install -r requirements.txt
python main.py
```

### 4. Tear down everything (stop Azure charges)
```bash
./scripts/teardown.sh      # Linux/macOS
scripts\teardown.bat       # Windows
```

---

## 🏗️ Architecture

```
Local Python App
      │
      ├──► Azure Blob Storage (image upload)
      │
      ├──► Azure Custom Vision  ──► shape detection results
      │
      ├──► Azure Document Intelligence ──► OCR text results
      │
      ├──► Azure SQL (serverless) ──► persist all results
      │
      └──► Display results in terminal / HTML report
```

---

## 📁 Project Structure

```
2026_MES_Azure_AI/
├── app/                    # Python application (Sessions 4 & 5)
│   ├── main.py             # Entry point — orchestrates the full workflow
│   ├── uploader.py         # Blob Storage upload logic
│   ├── vision.py           # Custom Vision API integration
│   ├── document_intel.py   # Document Intelligence API integration
│   ├── database.py         # Azure SQL connection & queries
│   ├── cost_review.py      # Azure Cost Management API query
│   ├── report.py           # HTML results report generator
│   └── requirements.txt
├── infra/
│   ├── main.bicep          # Main Bicep template (all resources)
│   ├── main.bicepparam     # Parameter file
│   └── modules/
│       ├── storage.bicep
│       ├── cognitiveservices.bicep
│       └── sql.bicep
├── scripts/
│   ├── deploy.sh           # Linux/macOS deploy
│   ├── deploy.bat          # Windows deploy
│   ├── teardown.sh         # Linux/macOS teardown
│   ├── teardown.bat        # Windows teardown
│   └── setup_custom_vision.py  # Train/publish a Custom Vision model
├── docs/
│   ├── session-4-guide.md  # Step-by-step facilitator guide
│   ├── session-5-guide.md
│   └── cost-estimate.md
├── sample-images/          # Test images for the demo
│   ├── shapes_sample.png
│   └── text_sample.png
├── .env.example
├── .gitignore
└── README.md
```

---

## ⚠️ Known Risks & Challenges

See [docs/risks.md](docs/risks.md) for full details. Key items:

- **Custom Vision training time** — model must be trained before demo; allow 15–30 min for training
- **SQL serverless cold start** — first query after idle period may take ~60 seconds
- **Subscription quotas** — some Azure subscriptions have low Cognitive Services quotas; verify before the session
- **Credentials in `.env`** — never commit `.env` to Git; `.gitignore` handles this

---

## 📚 Session Guides

- [Session 4 Guide](docs/session-4-guide.md) — Building the pipeline (upload → vision → database setup)
- [Session 5 Guide](docs/session-5-guide.md) — Completing the workflow (results → display → cost review)

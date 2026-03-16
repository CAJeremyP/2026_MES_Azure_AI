# Risks & Project Challenges

This document catalogues known risks, their likelihood, impact, and mitigations. Review before each session.

---

## Risk Register

### R1 — Custom Vision Model Not Ready
**Likelihood:** Medium  
**Impact:** High — Session 4 demo fails completely  

**Description:** Custom Vision model must be trained and *published* before the prediction API can be called. Training takes 5–30 minutes depending on image count. Publishing requires the prediction resource ID in `.env`.

**Mitigation:**
- Run `scripts/setup_custom_vision.py` at least 1 hour before Session 4
- Add minimum 5 images per tag to `sample-images/` before running setup
- The script writes `CUSTOM_VISION_PROJECT_ID` to `.env` automatically
- Verify with: `python -c "from app.vision import run_custom_vision; print('vision OK')"`

**Fallback:** If model isn't ready, demonstrate the Document Intelligence (OCR) steps first. Vision detections will show empty but won't crash the app.

---

### R2 — F0 (Free Tier) Already In Use On Subscription
**Likelihood:** Medium (common in shared enterprise subscriptions)  
**Impact:** Medium — deployment fails with `QuotaExceeded` error  

**Description:** Azure allows only one F0 instance per Cognitive Services type per subscription. If the org's Azure subscription already has Custom Vision F0 or Document Intelligence F0 resources in any region, the Bicep deployment will fail.

**Mitigation:**
- Before deploying, check: `az cognitiveservices account list --query "[?sku.name=='F0']" -o table`
- If F0 is in use, change the SKU in `infra/main.bicep` from `F0` to `S0` for affected resources
- S0 cost for the demo volume is under $1 total — still negligible

---

### R3 — SQL Serverless Cold Start Delay
**Likelihood:** High (will happen on first connection after any idle period)  
**Impact:** Low — causes a 30–90 second apparent hang  

**Description:** Azure SQL Serverless auto-pauses after 60 minutes of inactivity. The first connection after a pause triggers a resume, which takes 30–90 seconds. This is normal behaviour but can alarm participants if unexpected.

**Mitigation:**
- Warn participants explicitly before running the database step: *"First connection may take up to 60 seconds — this is the serverless database waking up."*
- Optionally run a warm-up query before the session: `az sql db show --resource-group rg-ai-demo --server <server> --name aidemodb`
- The `database.py` code already prints a warning message about cold starts

---

### R4 — ODBC Driver Not Installed on Participant Machines
**Likelihood:** Medium (Windows machines without ODBC Driver 18)  
**Impact:** Medium — `pyodbc` import succeeds but connection fails  

**Description:** `pyodbc` requires Microsoft ODBC Driver 18 for SQL Server to be installed separately from Python. This is not installed by default on most machines.

**Mitigation:**
- Include ODBC driver installation in pre-session setup instructions
- Download link: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
- For macOS: `brew install msodbcsql18`
- For Ubuntu/Debian: See Microsoft's apt repo instructions
- Error to look for: `pyodbc.Error: ('01000', "[01000] [unixODBC][Driver Manager]Can't open lib...`

---

### R5 — Azure SQL Regional Provisioning Restriction *(Known — already encountered)*
**Likelihood:** High (common on MSDN, Visual Studio, and many EA subscriptions)  
**Impact:** High — deployment fails with `ProvisioningDisabled` error  

**Description:** Azure SQL Server provisioning is restricted in `eastus` (and some other regions) on certain subscription types. The Bicep deployment fails with:  
`"Provisioning is restricted in this region. Please choose a different region."`

**Fix (already implemented in this repo):**
- `infra/main.bicep` has a separate `sqlLocation` parameter (defaults to `eastus2`) independent of the main `location` parameter
- `scripts/deploy.sh` auto-probes a priority list of regions using `az deployment group what-if` and picks the first available one
- Probe order: `eastus2 → westus2 → westus3 → centralus → southcentralus → northcentralus → westeurope → northeurope → uksouth → australiaeast → japaneast`
- If `SQL_LOCATION` is already set in `.env`, that region is tried first (skips the full probe)

**Manual override (fastest fix):** Add `SQL_LOCATION=eastus2` to `.env` before running `deploy.sh`.

**Verified safe regions:** `eastus2`, `westus2`, `westus3`, `centralus`

---

### R5b — Azure Subscription Quota Limits
**Likelihood:** Low–Medium  
**Impact:** High — services may not deploy or may throttle during demo  

**Description:** Some Azure subscriptions (especially free/trial accounts) have limits on the number of Cognitive Services resources, total regions, or compute cores.

**Mitigation:**
- Use a paid (PAYG or EA) Azure subscription for the demo
- Verify subscription type: `az account show --query "[name, state, tenantId]"`
- Check cognitive services quota: `az cognitiveservices usage list --location eastus`

---

### R6 — Secrets Accidentally Committed to Git
**Likelihood:** Low (with `.gitignore` in place)  
**Impact:** Critical — Azure keys exposed publicly  

**Description:** The `.env` file contains Azure storage connection strings, Cognitive Services keys, and SQL passwords. If committed to a public GitHub repository, these credentials are compromised immediately.

**Mitigation:**
- `.gitignore` already excludes `.env` — verify it's working: `git status` should not show `.env`
- Add pre-commit hook to double-check: `scripts/install-hooks.sh` (provided below)
- Rotate all keys immediately if `.env` is ever accidentally pushed: `az cognitiveservices account keys regenerate ...`
- Consider Azure Key Vault for any production adaptation of this demo

---

### R7 — Network/Firewall Blocks Azure Endpoints
**Likelihood:** Low–Medium (varies by org)  
**Impact:** High — all Azure API calls fail  

**Description:** Corporate networks may block outbound HTTPS to `*.cognitiveservices.azure.com`, `*.blob.core.windows.net`, or `*.database.windows.net`.

**Mitigation:**
- Test endpoints before the session from the participant network
- Quick test: `curl -I https://eastus.api.cognitive.microsoft.com/`
- If blocked, coordinate with IT to whitelist the required domains
- Alternative: run the demo from Azure Cloud Shell (browser-based, no firewall issues)

---

### R8 — Contract / MSA Not Finalised
**Likelihood:** Known (per order form — terms superseded by SCAN's MSA)  
**Impact:** Medium — order terminates if agreement not reached  

**Description:** The order form notes: *"These Terms and conditions will be superseded by SCANs MSA when completed. This order will terminate should agreement on terms not be reached."*

**Mitigation:**
- Prioritise MSA finalisation before deploying production resources
- For the demo/training context, this does not affect the technical implementation
- Flag to QA account executive (Brandon Barry) if MSA is not signed before Session 1

---

## Pre-Session Verification Checklist

Run this before each session to catch issues early:

```bash
# 1. Azure login
az account show

# 2. Resource group exists
az group show --name rg-ai-demo

# 3. Storage accessible
az storage container list --account-name <STORAGE_ACCOUNT_NAME> --auth-mode login

# 4. Custom Vision project exists
python -c "
from dotenv import load_dotenv; load_dotenv('.env')
from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from msrest.authentication import ApiKeyCredentials
import os
creds = ApiKeyCredentials(in_headers={'Training-key': os.environ['CUSTOM_VISION_TRAINING_KEY']})
client = CustomVisionTrainingClient(os.environ['CUSTOM_VISION_TRAINING_ENDPOINT'], creds)
print([p.name for p in client.get_projects()])
"

# 5. SQL reachable (allows for cold start)
python -c "
from dotenv import load_dotenv; load_dotenv('.env')
from app.database import DatabaseClient
db = DatabaseClient(); db.close(); print('SQL OK')
"
```

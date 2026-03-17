# Risks & Project Challenges

Known risks encountered during development, with mitigations and current status.

---

### R1 — Custom Vision Model Not Ready Before Session
**Likelihood:** Medium  
**Impact:** High — Step 2 of the pipeline returns no results

**Description:** The Object Detection model must be trained and published before `detect_image` can be called. Training takes 5–20 minutes. Publishing requires the prediction resource ARM ID, which is derived automatically from `RESOURCE_PREFIX` in `.env`.

**Mitigation (implemented):**
- `setup_custom_vision.py` validates image counts before attempting training and prints a clear fix message
- The script handles "Nothing changed since last training" gracefully — reuses the existing completed iteration rather than crashing
- Run the full setup sequence at least 30 minutes before the session:
  ```bash
  python scripts/generate_sample_images.py
  python scripts/setup_custom_vision.py
  ```

**Fallback:** If the model isn't ready, Document Intelligence (Step 3) still runs and produces OCR output. Step 2 prints a warning and returns an empty list without crashing.

---

### R2 — F0 (Free Tier) Already In Use On Subscription
**Likelihood:** Medium (common in shared enterprise subscriptions)  
**Impact:** Medium — deployment fails with `QuotaExceeded`

**Description:** Azure allows only one F0 instance per Cognitive Services type per subscription. If Custom Vision or Document Intelligence F0 is already provisioned elsewhere in the subscription, the Bicep deployment fails.

**Mitigation:**
- Check before deploying: `az cognitiveservices account list --query "[?sku.name=='F0']" -o table`
- If F0 is in use, change the relevant SKU in `infra/main.bicep` from `F0` to `S0`
- S0 cost for demo volumes is under $1 total

---

### R3 — Azure SQL Regional Provisioning Restriction *(Encountered and resolved)*
**Likelihood:** High on MSDN / Visual Studio / some EA subscriptions  
**Impact:** Was High — deployment failed with `ProvisioningDisabled` in all regions

**Description:** Azure SQL has subscription-level provisioning restrictions that cannot be bypassed by switching regions. The error `"Provisioning is restricted in this region"` appeared in every tested region including `eastus`, `eastus2`, `westus2`, and `centralus`.

**Resolution:** Azure SQL was removed from the project entirely and replaced with **Azure Cosmos DB**. Cosmos DB has no regional provisioning restrictions, no ODBC driver requirement, a genuine free tier ($0/month), and serverless billing when idle. All pipeline results are stored as JSON documents in a `pipeline_runs` container. See [cost-estimate.md](cost-estimate.md) for pricing details.

> **Note for the workshop:** Session 2 covers Azure SQL concepts. The demo infrastructure uses Cosmos DB, but the SQL session content (Azure SQL options, security, architectures, hands-on exercises) is delivered using the Azure Portal and documentation rather than a live deployment. Instructors should clarify this distinction at the start of Session 2.

---

### R4 — Custom Vision Project Type Mismatch
**Likelihood:** Low (once — fixed in v13)  
**Impact:** High — `detect_image` throws `Invalid project type for operation`

**Description:** Custom Vision has two distinct project types: **Classification** (image-level labels) and **Object Detection** (bounding box regions per object). Calling `detect_image` on a Classification project, or `classify_image` on an Object Detection project, throws this error.

**Resolution (implemented):**
- `setup_custom_vision.py` now explicitly creates a **General (Object Detection)** domain project
- If it finds an existing Classification project with the same name, it deletes and recreates it as Object Detection
- `generate_sample_images.py` computes precise bounding boxes from shape geometry and saves them to `sample-images/annotations.json`
- Images are uploaded with `Region` annotations (not just tag IDs) so the training data is correctly labelled for object detection

---

### R5 — Training Image Count Too Low
**Likelihood:** Low (once — fixed in v7)  
**Impact:** High — training throws `Not enough images for training`

**Description:** Custom Vision F0 requires a minimum of 5 tagged images per class. The original generator produced only 3 per tag. For Object Detection, the quality of bounding box annotations matters as much as quantity.

**Resolution (implemented):**
- `generate_sample_images.py` produces 20 images per tag (80 training images total)
- Each set has genuine variation: different sizes, positions, colours, and orientations
- Pre-flight count validation in `setup_custom_vision.py` prints a per-tag summary before attempting training and exits early with a clear fix message if counts are insufficient

---

### R6 — Duplicate Image Uploads on Re-run
**Likelihood:** High (once — fixed in v9)  
**Impact:** Low — wasted API calls, confusing output

**Description:** The initial dedup logic compared filenames against `original_image_uri` values from the API. These URIs are GUID-based storage paths with no connection to the original filename, so every re-run uploaded all 80 images again.

**Resolution (implemented):**
- `setup_custom_vision.py` uses `get_tagged_image_count()` per tag and compares against the local count
- If counts match: skip upload entirely
- If counts differ: delete existing images for that tag and re-upload clean
- This is idempotent — safe to run multiple times

---

### R7 — macOS BSD `sed` Incompatibility
**Likelihood:** High on macOS (once — fixed in v3)  
**Impact:** High — deploy script failed to write values to `.env`

**Description:** BSD `sed` (macOS default) handles `-i` differently from GNU `sed` (Linux). File paths containing `@` or `.` characters — present in the QA OneDrive path — caused `sed: invalid command code J`.

**Resolution (implemented):**
- `update_env()` in `deploy.sh` uses an inline Python heredoc instead of `sed -i`
- Python's file I/O is immune to special characters in paths or values (including `@`, `.`, `+`, `/`, `=` in connection strings)

---

### R8 — Document Intelligence Line-level Confidence is None
**Likelihood:** High (encountered — fixed in v14)  
**Impact:** Medium — `TypeError: unsupported format string passed to NoneType`

**Description:** The `prebuilt-read` model returns confidence at the **word** level only. The `lines` array returns `None` for confidence. Formatting `None` with `:.1%` throws a TypeError.

**Resolution (implemented):**
- `main.py` and `report.py` both check `if conf is not None` before formatting
- Line display shows `(confidence=n/a)` when the field is absent
- Word-level confidence is still captured in `document_intel.py` under `result["words"]`

---

### R9 — Secrets Accidentally Committed to Git
**Likelihood:** Low (with `.gitignore` in place)  
**Impact:** Critical — Azure keys exposed publicly

**Description:** `.env` contains storage connection strings, Cognitive Services keys, and Cosmos DB primary keys.

**Mitigation:**
- `.gitignore` excludes `.env` — verify: `git status` should not list `.env`
- CI workflow (`.github/workflows/ci.yml`) includes a TruffleHog secret scan on every push
- If `.env` is accidentally pushed: rotate all keys immediately via the Azure Portal

---

## Pre-Session Verification Checklist

Run these before each session:

```bash
# 1. Azure resources exist
az resource list --resource-group rg-ai-demo -o table

# 2. Custom Vision project is trained and published
python -c "
from dotenv import load_dotenv; load_dotenv('.env')
from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from msrest.authentication import ApiKeyCredentials
import os
creds = ApiKeyCredentials(in_headers={'Training-key': os.environ['CUSTOM_VISION_TRAINING_KEY']})
client = CustomVisionTrainingClient(os.environ['CUSTOM_VISION_TRAINING_ENDPOINT'], creds)
import os; pid = os.environ['CUSTOM_VISION_PROJECT_ID']
its = client.get_iterations(pid)
for it in its:
    print(f'{it.name}: {it.status}, published={it.publish_name}')
"

# 3. Full pipeline smoke test
python app/main.py --image sample-images/mixed_shapes_and_text.png
```

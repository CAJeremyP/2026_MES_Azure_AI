#!/usr/bin/env bash
# =============================================================
# deploy.sh — Deploy all Azure resources for the AI demo
# Usage: ./scripts/deploy.sh
#
# Database: Azure Cosmos DB (free tier) — no regional
# provisioning restrictions, no ODBC driver required.
# =============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# ── Load .env ─────────────────────────────────────────────────
if [ ! -f "$ROOT_DIR/.env" ]; then
  echo "❌  .env file not found. Copy .env.example to .env and fill in your values."
  exit 1
fi
set -a; source "$ROOT_DIR/.env"; set +a

echo "=================================================="
echo "  Azure AI Demo — Deployment"
echo "  Subscription : $AZURE_SUBSCRIPTION_ID"
echo "  Resource Group: $AZURE_RESOURCE_GROUP"
echo "  Location      : $AZURE_LOCATION"
echo "  Prefix        : $RESOURCE_PREFIX"
echo "=================================================="

# ── Login check ───────────────────────────────────────────────
echo "🔐  Checking Azure login..."
az account show &>/dev/null || { echo "❌  Run: az login"; exit 1; }
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
echo "✅  Logged in."

# ── Create resource group ─────────────────────────────────────
echo "📁  Creating resource group '$AZURE_RESOURCE_GROUP'..."
az group create \
  --name "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --output none
echo "✅  Resource group ready."

# ── update_env — Python-based, safe on macOS and Linux ────────
# Avoids BSD sed -i issues with paths containing @ . spaces etc.
update_env() {
  local key="$1"
  local val="$2"
  python3 - "$ROOT_DIR/.env" "$key" "$val" << 'PYEOF'
import sys, re
env_file, key, val = sys.argv[1], sys.argv[2], sys.argv[3]
with open(env_file, 'r') as f:
    lines = f.readlines()
pattern = re.compile(r'^' + re.escape(key) + r'=.*')
found = False
new_lines = []
for line in lines:
    if pattern.match(line):
        new_lines.append(f'{key}={val}\n')
        found = True
    else:
        new_lines.append(line)
if not found:
    new_lines.append(f'{key}={val}\n')
with open(env_file, 'w') as f:
    f.writelines(new_lines)
PYEOF
}

# ── Check Cosmos DB free tier availability ────────────────────
# One free-tier Cosmos DB account is allowed per subscription.
# If one already exists, we set enableFreeTier=false and use
# serverless mode (~$0.008/hour at light load) instead.
echo "🔍  Checking Cosmos DB free tier availability..."
EXISTING_FREE=$(az cosmosdb list \
  --query "[?properties.enableFreeTier==\`true\`].name" \
  --output tsv 2>/dev/null || echo "")

COSMOS_FREE_TIER="true"
if [ -n "$EXISTING_FREE" ]; then
  echo "  ⚠️   Free tier already used by: $EXISTING_FREE"
  echo "      Deploying Cosmos DB without free tier (~\$0.008/hr serverless)."
  COSMOS_FREE_TIER="false"
else
  echo "  ✅  Free tier available."
fi

# ── Deploy Bicep ──────────────────────────────────────────────
echo ""
echo "🏗️   Deploying Bicep template (this takes ~3-5 minutes)..."

DEPLOY_OUTPUT=$(az deployment group create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --template-file "$ROOT_DIR/infra/main.bicep" \
  --parameters "$ROOT_DIR/infra/main.bicepparam" \
  --parameters resourcePrefix="$RESOURCE_PREFIX" \
               cosmosEnableFreeTier="$COSMOS_FREE_TIER" \
  --query properties.outputs \
  --output json)

echo "✅  Bicep deployment complete."

# ── Parse outputs ─────────────────────────────────────────────
parse() { echo "$DEPLOY_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['$1']['value'])"; }

STORAGE_ACCOUNT_NAME=$(parse storageAccountName)
CV_TRAIN_ENDPOINT=$(parse customVisionTrainingEndpoint)
CV_PRED_ENDPOINT=$(parse customVisionPredictionEndpoint)
DOCINTEL_ENDPOINT=$(parse documentIntelligenceEndpoint)
COSMOS_ENDPOINT=$(parse cosmosEndpoint)
COSMOS_ACCOUNT_NAME=$(parse cosmosAccountName)
COSMOS_DB_NAME=$(parse cosmosDatabaseName)

# ── Retrieve secrets from Azure ───────────────────────────────
echo "🔑  Retrieving keys..."

STORAGE_CONN=$(az storage account show-connection-string \
  --name "$STORAGE_ACCOUNT_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --query connectionString -o tsv)

CV_TRAIN_KEY=$(az cognitiveservices account keys list \
  --name "${RESOURCE_PREFIX}-vision-train" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --query key1 -o tsv)

CV_PRED_KEY=$(az cognitiveservices account keys list \
  --name "${RESOURCE_PREFIX}-vision-pred" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --query key1 -o tsv)

DOCINTEL_KEY=$(az cognitiveservices account keys list \
  --name "${RESOURCE_PREFIX}-docintel" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --query key1 -o tsv)

COSMOS_KEY=$(az cosmosdb keys list \
  --name "$COSMOS_ACCOUNT_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --query primaryMasterKey -o tsv)

# ── Write all values back to .env ─────────────────────────────
echo "💾  Writing values to .env..."

update_env "STORAGE_ACCOUNT_NAME"              "$STORAGE_ACCOUNT_NAME"
update_env "STORAGE_CONNECTION_STRING"         "$STORAGE_CONN"
update_env "CUSTOM_VISION_TRAINING_ENDPOINT"   "$CV_TRAIN_ENDPOINT"
update_env "CUSTOM_VISION_TRAINING_KEY"        "$CV_TRAIN_KEY"
update_env "CUSTOM_VISION_PREDICTION_ENDPOINT" "$CV_PRED_ENDPOINT"
update_env "CUSTOM_VISION_PREDICTION_KEY"      "$CV_PRED_KEY"
update_env "DOCUMENT_INTELLIGENCE_ENDPOINT"    "$DOCINTEL_ENDPOINT"
update_env "DOCUMENT_INTELLIGENCE_KEY"         "$DOCINTEL_KEY"
update_env "COSMOS_ENDPOINT"                   "$COSMOS_ENDPOINT"
update_env "COSMOS_KEY"                        "$COSMOS_KEY"
update_env "COSMOS_ACCOUNT_NAME"               "$COSMOS_ACCOUNT_NAME"
update_env "COSMOS_DATABASE_NAME"              "$COSMOS_DB_NAME"

echo ""
echo "=================================================="
echo "✅  Deployment complete!"
echo ""
echo "Next steps:"
echo "  1. python3 scripts/setup_custom_vision.py"
echo "  2. pip install -r app/requirements.txt"
echo "  3. python3 app/main.py"
echo ""
echo "⚠️  Remember: run ./scripts/teardown.sh when done"
echo "=================================================="

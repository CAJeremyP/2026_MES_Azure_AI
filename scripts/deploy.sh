#!/usr/bin/env bash
# =============================================================
# deploy.sh — Deploy all Azure resources for the AI demo
# Usage: ./scripts/deploy.sh
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
az account show &>/dev/null || { echo "Run: az login"; exit 1; }
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
echo "✅  Logged in."

# ── Create resource group ─────────────────────────────────────
echo "📁  Creating resource group '$AZURE_RESOURCE_GROUP'..."
az group create \
  --name "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --output none
echo "✅  Resource group ready."

# ── Deploy Bicep ──────────────────────────────────────────────
echo "🏗️   Deploying Bicep template (this takes ~3-5 minutes)..."
DEPLOY_OUTPUT=$(az deployment group create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --template-file "$ROOT_DIR/infra/main.bicep" \
  --parameters "$ROOT_DIR/infra/main.bicepparam" \
  --parameters resourcePrefix="$RESOURCE_PREFIX" \
  --query properties.outputs \
  --output json)

echo "✅  Bicep deployment complete."

# ── Parse outputs ─────────────────────────────────────────────
STORAGE_ACCOUNT_NAME=$(echo "$DEPLOY_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['storageAccountName']['value'])")
SQL_SERVER_FQDN=$(echo "$DEPLOY_OUTPUT"       | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['sqlServerFqdn']['value'])")
SQL_DATABASE_NAME=$(echo "$DEPLOY_OUTPUT"     | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['sqlDatabaseName']['value'])")
CV_TRAIN_ENDPOINT=$(echo "$DEPLOY_OUTPUT"     | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['customVisionTrainingEndpoint']['value'])")
CV_PRED_ENDPOINT=$(echo "$DEPLOY_OUTPUT"      | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['customVisionPredictionEndpoint']['value'])")
DOCINTEL_ENDPOINT=$(echo "$DEPLOY_OUTPUT"     | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['documentIntelligenceEndpoint']['value'])")

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

SQL_CONN="Driver={ODBC Driver 18 for SQL Server};Server=tcp:${SQL_SERVER_FQDN},1433;Database=${SQL_DATABASE_NAME};Uid=${SQL_ADMIN_USER:-demoadmin};Pwd=${SQL_ADMIN_PASSWORD:-Demo@Pass123!};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

# ── Write back to .env ────────────────────────────────────────
echo "💾  Writing values to .env..."

update_env() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ROOT_DIR/.env"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ROOT_DIR/.env"
  else
    echo "${key}=${val}" >> "$ROOT_DIR/.env"
  fi
}

update_env "STORAGE_ACCOUNT_NAME"              "$STORAGE_ACCOUNT_NAME"
update_env "STORAGE_CONNECTION_STRING"         "$STORAGE_CONN"
update_env "CUSTOM_VISION_TRAINING_ENDPOINT"   "$CV_TRAIN_ENDPOINT"
update_env "CUSTOM_VISION_TRAINING_KEY"        "$CV_TRAIN_KEY"
update_env "CUSTOM_VISION_PREDICTION_ENDPOINT" "$CV_PRED_ENDPOINT"
update_env "CUSTOM_VISION_PREDICTION_KEY"      "$CV_PRED_KEY"
update_env "DOCUMENT_INTELLIGENCE_ENDPOINT"    "$DOCINTEL_ENDPOINT"
update_env "DOCUMENT_INTELLIGENCE_KEY"         "$DOCINTEL_KEY"
update_env "SQL_SERVER_NAME"                   "$SQL_SERVER_FQDN"
update_env "SQL_DATABASE_NAME"                 "$SQL_DATABASE_NAME"
update_env "SQL_CONNECTION_STRING"             "$SQL_CONN"

echo ""
echo "=================================================="
echo "✅  Deployment complete!"
echo ""
echo "Next steps:"
echo "  1. Run: python3 scripts/setup_custom_vision.py"
echo "     (trains a Custom Vision model on the sample images)"
echo "  2. Run: cd app && pip install -r requirements.txt"
echo "  3. Run: python3 app/main.py"
echo ""
echo "⚠️  Remember: run ./scripts/teardown.sh when done"
echo "   to avoid ongoing Azure charges."
echo "=================================================="

#!/usr/bin/env bash
# =============================================================
# teardown.sh — Delete ALL Azure resources for the demo
# This permanently deletes the resource group and all contents.
# =============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

if [ ! -f "$ROOT_DIR/.env" ]; then
  echo "❌  .env not found."
  exit 1
fi
set -a; source "$ROOT_DIR/.env"; set +a

echo ""
echo "⚠️  WARNING: This will PERMANENTLY DELETE resource group:"
echo "   '$AZURE_RESOURCE_GROUP' in subscription '$AZURE_SUBSCRIPTION_ID'"
echo "   All resources (Storage, SQL, Cognitive Services) will be removed."
echo ""
read -rp "Type the resource group name to confirm: " CONFIRM

if [ "$CONFIRM" != "$AZURE_RESOURCE_GROUP" ]; then
  echo "❌  Name did not match. Aborting."
  exit 1
fi

echo "🗑️   Deleting resource group '$AZURE_RESOURCE_GROUP'..."
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
az group delete \
  --name "$AZURE_RESOURCE_GROUP" \
  --yes \
  --no-wait

echo ""
echo "✅  Deletion initiated (runs in background, takes ~2-3 minutes)."
echo "   You can verify in the Azure Portal."
echo ""
echo "💡  To confirm deletion:"
echo "   az group show --name $AZURE_RESOURCE_GROUP"

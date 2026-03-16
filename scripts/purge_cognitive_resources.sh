#!/usr/bin/env bash
# ==============================================================
# purge_cognitive_resources.sh — Purge Azure cognitive resources
# This permanently deletes the cognitive resources for the demo
# ==============================================================
set -euo pipefail

echo "Fetching deleted Cognitive Services accounts..."
deleted_accounts=$(az cognitiveservices account list-deleted --output json)

if [ -z "$deleted_accounts" ] || [ "$deleted_accounts" == "[]" ]; then
  echo "No deleted Cognitive Services accounts found."
  exit 0
fi

echo "Purging deleted accounts..."
az cognitiveservices account list-deleted --output json | \
  jq -c '.[]' | \
while read -r account; do
  name=$(echo "$account" | jq -r '.name')
  location=$(echo "$account" | jq -r '.location')
  id=$(echo "$account" | jq -r '.id')

  # Extract resource group from ARM ID
  resource_group=$(echo "$id" | awk -F'/' '{print $9}')

  echo "Purging: $name | RG: $resource_group | Location: $location"

  az cognitiveservices account purge \
    --name "$name" \
    --resource-group "$resource_group" \
    --location "$location"

  echo "Done: $name"
done
echo "All accounts purged."
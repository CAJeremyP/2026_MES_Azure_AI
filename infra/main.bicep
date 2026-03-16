// ============================================================
// main.bicep — Azure AI Demo (Sessions 4 & 5)
// All resources sized for SHORT-LIVED DEMO use (cost-optimized)
//
// Database: Azure Cosmos DB (free tier)
//   - No regional provisioning restrictions
//   - Free tier: 1000 RU/s + 25 GB storage at no cost
//   - One free-tier account allowed per Azure subscription
//   - No drivers needed — pure HTTPS/SDK access
// ============================================================

@description('Unique prefix for all resource names (3-8 lowercase chars)')
@minLength(3)
@maxLength(8)
param resourcePrefix string

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Enable Cosmos DB free tier (only one allowed per subscription). Set false if already in use.')
param cosmosEnableFreeTier bool = true

// ── Storage Account ─────────────────────────────────────────
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: '${resourcePrefix}stor${uniqueString(resourceGroup().id)}'
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource imagesContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'demo-images'
  properties: { publicAccess: 'None' }
}

// ── Custom Vision (Training) — F0 free tier ──────────────────
resource customVisionTraining 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${resourcePrefix}-vision-train'
  location: location
  kind: 'CustomVision.Training'
  sku: { name: 'F0' }
  properties: { publicNetworkAccess: 'Enabled' }
}

// ── Custom Vision (Prediction) — F0 free tier ────────────────
resource customVisionPrediction 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${resourcePrefix}-vision-pred'
  location: location
  kind: 'CustomVision.Prediction'
  sku: { name: 'F0' }
  properties: { publicNetworkAccess: 'Enabled' }
}

// ── Document Intelligence — F0 free tier ─────────────────────
resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${resourcePrefix}-docintel'
  location: location
  kind: 'FormRecognizer'
  sku: { name: 'F0' }
  properties: { publicNetworkAccess: 'Enabled' }
}

// ── Cosmos DB (NoSQL) — free tier ────────────────────────────
// Free tier: 1000 RU/s throughput + 25 GB storage = $0/month
// Available in all regions, no quota/provisioning restrictions.
// NOTE: Only ONE free-tier Cosmos DB account is allowed per
// Azure subscription. If one already exists, set
// enableFreeTier: false — cost will be ~$0.008/hour at 400 RU/s.
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-02-15-preview' = {
  name: '${resourcePrefix}-cosmos-${uniqueString(resourceGroup().id)}'
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    enableFreeTier: cosmosEnableFreeTier
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      { name: 'EnableServerless' }   // Serverless = pay-per-request, $0 when idle
    ]
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-02-15-preview' = {
  parent: cosmosAccount
  name: 'aidemodb'
  properties: {
    resource: { id: 'aidemodb' }
  }
}

resource cosmosRunsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-02-15-preview' = {
  parent: cosmosDatabase
  name: 'pipeline_runs'
  properties: {
    resource: {
      id: 'pipeline_runs'
      partitionKey: { paths: ['/run_id'], kind: 'Hash' }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [{ path: '/*' }]
      }
    }
  }
}

// ── Outputs ──────────────────────────────────────────────────
output storageAccountName string = storageAccount.name
output storageContainerName string = imagesContainer.name
output customVisionTrainingEndpoint string = customVisionTraining.properties.endpoint
output customVisionPredictionEndpoint string = customVisionPrediction.properties.endpoint
output documentIntelligenceEndpoint string = documentIntelligence.properties.endpoint
output cosmosEndpoint string = cosmosAccount.properties.documentEndpoint
output cosmosAccountName string = cosmosAccount.name
output cosmosDatabaseName string = cosmosDatabase.name

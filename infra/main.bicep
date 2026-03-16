// ============================================================
// main.bicep — Azure AI Demo (Sessions 4 & 5)
// All resources sized for SHORT-LIVED DEMO use (cost-optimized)
// ============================================================

@description('Unique prefix for all resource names (3-8 lowercase chars)')
@minLength(3)
@maxLength(8)
param resourcePrefix string

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('SQL admin username')
param sqlAdminUser string = 'demoadmin'

@description('SQL admin password')
@secure()
param sqlAdminPassword string

// ── Storage Account ─────────────────────────────────────────
// Locally Redundant (LRS) — cheapest option, fine for demo
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: '${resourcePrefix}stor${uniqueString(resourceGroup().id)}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
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
  properties: {
    publicAccess: 'None'
  }
}

// ── Custom Vision (Training) ─────────────────────────────────
// F0 = free tier (2 TPS, 5000 transactions/month) — perfect for demo
resource customVisionTraining 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${resourcePrefix}-vision-train'
  location: location
  kind: 'CustomVision.Training'
  sku: {
    name: 'F0'   // Free tier
  }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

// ── Custom Vision (Prediction) ───────────────────────────────
resource customVisionPrediction 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${resourcePrefix}-vision-pred'
  location: location
  kind: 'CustomVision.Prediction'
  sku: {
    name: 'F0'   // Free tier
  }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

// ── Document Intelligence (Form Recognizer) ──────────────────
// F0 = free tier (500 pages/month) — fine for demo
resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${resourcePrefix}-docintel'
  location: location
  kind: 'FormRecognizer'
  sku: {
    name: 'F0'   // Free tier
  }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

// ── Azure SQL Server ─────────────────────────────────────────
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: '${resourcePrefix}-sql-${uniqueString(resourceGroup().id)}'
  location: location
  properties: {
    administratorLogin: sqlAdminUser
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
    publicNetworkAccess: 'Enabled'
  }
}

// Allow Azure services to connect (needed for the demo app)
resource sqlFirewallAzure 'Microsoft.Sql/servers/firewallRules@2023-05-01-preview' = {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Allow all IPs — DEMO ONLY. Remove for any real deployment.
resource sqlFirewallAll 'Microsoft.Sql/servers/firewallRules@2023-05-01-preview' = {
  parent: sqlServer
  name: 'AllowAll-DemoOnly'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '255.255.255.255'
  }
}

// ── Azure SQL Database (Serverless) ──────────────────────────
// Serverless + autopause after 1 hour = near-zero cost when idle
resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  parent: sqlServer
  name: 'aidemodb'
  location: location
  sku: {
    name: 'GP_S_Gen5_1'   // General Purpose Serverless, 1 vCore
    tier: 'GeneralPurpose'
    family: 'Gen5'
    capacity: 1
  }
  properties: {
    autoPauseDelay: 60           // Pause after 60 minutes idle (cost saving)
    minCapacity: '0.5'           // Minimum 0.5 vCores when running
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: 1073741824     // 1 GB max
    zoneRedundant: false
  }
}

// ── Outputs (consumed by deploy scripts) ────────────────────
output storageAccountName string = storageAccount.name
output storageContainerName string = imagesContainer.name
output customVisionTrainingEndpoint string = customVisionTraining.properties.endpoint
output customVisionPredictionEndpoint string = customVisionPrediction.properties.endpoint
output documentIntelligenceEndpoint string = documentIntelligence.properties.endpoint
output sqlServerFqdn string = sqlServer.properties.fullyQualifiedDomainName
output sqlDatabaseName string = sqlDatabase.name

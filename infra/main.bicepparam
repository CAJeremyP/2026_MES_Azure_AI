using './main.bicep'

// Edit these values before deploying
// resourcePrefix must be 3-8 lowercase letters, no hyphens or numbers
param resourcePrefix = 'aidemo'

// Location — eastus has broadest Cognitive Services availability
// Other good options: westus2, westeurope
param location = 'eastus'

param sqlAdminUser = 'demoadmin'

// IMPORTANT: Change this password before deploying
// Must meet Azure complexity: uppercase, lowercase, digit, special char
param sqlAdminPassword = 'Demo@Pass123!'

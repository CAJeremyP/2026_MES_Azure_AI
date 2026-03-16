@echo off
REM =============================================================
REM deploy.bat — Deploy all Azure resources for the AI demo
REM Usage: scripts\deploy.bat
REM =============================================================
setlocal enabledelayedexpansion

set "ROOT_DIR=%~dp0.."

REM ── Load .env ─────────────────────────────────────────────────
if not exist "%ROOT_DIR%\.env" (
    echo ERROR: .env file not found. Copy .env.example to .env and fill in your values.
    exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT_DIR%\.env") do (
    if not "%%A"=="" if not "%%A:~0,1%"=="#" set "%%A=%%B"
)

echo ==================================================
echo   Azure AI Demo - Deployment
echo   Subscription : %AZURE_SUBSCRIPTION_ID%
echo   Resource Group: %AZURE_RESOURCE_GROUP%
echo   Location      : %AZURE_LOCATION%
echo   Prefix        : %RESOURCE_PREFIX%
echo ==================================================

REM ── Login check ───────────────────────────────────────────────
echo Checking Azure login...
az account show >nul 2>&1
if errorlevel 1 (
    echo Run: az login
    exit /b 1
)
az account set --subscription "%AZURE_SUBSCRIPTION_ID%"
echo Logged in.

REM ── Create resource group ─────────────────────────────────────
echo Creating resource group...
az group create --name "%AZURE_RESOURCE_GROUP%" --location "%AZURE_LOCATION%" --output none

REM ── Deploy Bicep ──────────────────────────────────────────────
echo Deploying Bicep template (3-5 minutes)...
az deployment group create ^
  --resource-group "%AZURE_RESOURCE_GROUP%" ^
  --template-file "%ROOT_DIR%\infra\main.bicep" ^
  --parameters "%ROOT_DIR%\infra\main.bicepparam" ^
  --parameters resourcePrefix="%RESOURCE_PREFIX%" ^
  --output none

echo Bicep deployment complete.
echo.
echo ==================================================
echo Deployment complete!
echo.
echo Next steps:
echo   1. python scripts\setup_custom_vision.py
echo   2. cd app ^&^& pip install -r requirements.txt
echo   3. python app\main.py
echo.
echo REMINDER: run scripts\teardown.bat when done!
echo ==================================================
echo.
echo NOTE: On Windows, please manually copy the resource keys
echo from the Azure Portal into your .env file, or run the
echo deploy.sh script in WSL / Git Bash for auto-population.

@echo off
REM =============================================================
REM teardown.bat — Delete ALL Azure resources for the demo
REM =============================================================
setlocal enabledelayedexpansion

set "ROOT_DIR=%~dp0.."

for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT_DIR%\.env") do (
    if not "%%A"=="" if not "%%A:~0,1%"=="#" set "%%A=%%B"
)

echo.
echo WARNING: This will PERMANENTLY DELETE resource group:
echo   %AZURE_RESOURCE_GROUP% in subscription %AZURE_SUBSCRIPTION_ID%
echo.
set /p CONFIRM=Type the resource group name to confirm: 

if not "%CONFIRM%"=="%AZURE_RESOURCE_GROUP%" (
    echo Name did not match. Aborting.
    exit /b 1
)

echo Deleting resource group %AZURE_RESOURCE_GROUP%...
az account set --subscription "%AZURE_SUBSCRIPTION_ID%"
az group delete --name "%AZURE_RESOURCE_GROUP%" --yes --no-wait

echo.
echo Deletion initiated. Check Azure Portal to confirm.

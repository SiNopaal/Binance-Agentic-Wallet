@echo off
setlocal enabledelayedexpansion

echo ====================================================================
echo  Binance Agentic Wallet (BAW) Multi-Profile CLI Setup
echo ====================================================================
echo.

set BAW_DIR=%USERPROFILE%\.baw
if not exist "%BAW_DIR%" mkdir "%BAW_DIR%"
if not exist "%BAW_DIR%\profiles\acc1" mkdir "%BAW_DIR%\profiles\acc1"
if not exist "%BAW_DIR%\profiles\acc2" mkdir "%BAW_DIR%\profiles\acc2"
if not exist "%BAW_DIR%\profiles\acc3" mkdir "%BAW_DIR%\profiles\acc3"

copy /Y "%~dp0preload.cjs" "%BAW_DIR%\preload.cjs" >nul
copy /Y "%~dp0baw-multi.mjs" "%BAW_DIR%\baw-multi.mjs" >nul

set TARGET_DIR=%APPDATA%\npm
if not exist "%TARGET_DIR%" (
    set TARGET_DIR=%~dp0
)

echo Generating CLI wrappers in %TARGET_DIR%...

:: Generate baw1.cmd
(
echo @echo off
echo set BINANCE_BAW_DIR=%BAW_DIR%\profiles\acc1
echo set BINANCE_KEYTAR_SERVICE=baw_acc1
echo set BINANCE_DEVICE_NAME=Agent-Node-Acc1
echo set NODE_OPTIONS=--require "%BAW_DIR%\preload.cjs"
echo baw %%*
) > "%TARGET_DIR%\baw1.cmd"

:: Generate baw2.cmd
(
echo @echo off
echo set BINANCE_BAW_DIR=%BAW_DIR%\profiles\acc2
echo set BINANCE_KEYTAR_SERVICE=baw_acc2
echo set BINANCE_DEVICE_NAME=Agent-Node-Acc2
echo set NODE_OPTIONS=--require "%BAW_DIR%\preload.cjs"
echo baw %%*
) > "%TARGET_DIR%\baw2.cmd"

:: Generate baw3.cmd
(
echo @echo off
echo set BINANCE_BAW_DIR=%BAW_DIR%\profiles\acc3
echo set BINANCE_KEYTAR_SERVICE=baw_acc3
echo set BINANCE_DEVICE_NAME=Agent-Node-Acc3
echo set NODE_OPTIONS=--require "%BAW_DIR%\preload.cjs"
echo baw %%*
) > "%TARGET_DIR%\baw3.cmd"

echo.
echo [SUCCESS] Multi-profile wrappers installed:
echo   - baw1  -^> Profile 1 (baw_acc1 / Agent-Node-Acc1)
echo   - baw2  -^> Profile 2 (baw_acc2 / Agent-Node-Acc2)
echo   - baw3  -^> Profile 3 (baw_acc3 / Agent-Node-Acc3)
echo.
pause

@echo off
setlocal enabledelayedexpansion

echo ====================================================================
echo  BINANCE AGENTIC WALLET (BAW) - PROFILE SHORTCUT GENERATOR (WINDOWS)
echo ====================================================================
echo.

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..
set PRELOAD_FILE=%ROOT_DIR%\core\preload.cjs
set /p NUM_ACCOUNTS="Enter total number of accounts to generate (e.g. 5, 7, 10): "

if "%NUM_ACCOUNTS%"=="" set NUM_ACCOUNTS=5

echo [*] Generating baw1.cmd through baw%NUM_ACCOUNTS%.cmd in user directory...

for /L %%i in (1,1,%NUM_ACCOUNTS%) do (
    set CMD_FILE=%USERPROFILE%\baw%%i.cmd
    (
        echo @echo off
        echo set BINANCE_BAW_DIR=%USERPROFILE%\.baw\profiles\acc%%i
        echo set BINANCE_KEYTAR_SERVICE=baw_acc%%i
        echo set BINANCE_DEVICE_NAME=Agent-Node-Acc%%i
        echo set NODE_OPTIONS=--require "%PRELOAD_FILE:\=/%"
        echo baw %%*
    ) > "!CMD_FILE!"
    echo   [+] Created: !CMD_FILE!
)

echo.
echo ====================================================================
echo  SUCCESS! You can now use baw1, baw2, ..., baw%NUM_ACCOUNTS% anywhere in CMD/PowerShell!
echo  Example: baw1 wallet status
echo ====================================================================
pause

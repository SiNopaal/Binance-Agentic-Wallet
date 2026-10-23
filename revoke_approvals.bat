@echo off
title Revoke All Approvals - Audit Keamanan Wallets
cd /d "%~dp0"
python executor.py --revoke-all
pause

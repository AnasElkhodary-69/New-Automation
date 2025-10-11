@echo off
REM Odoo Incremental Sync - Windows Batch Script
REM Run this script to sync new/modified products and customers from Odoo

cd /d "%~dp0"
python incremental_sync_odoo.py
pause

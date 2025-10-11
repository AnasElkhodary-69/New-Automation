#!/bin/bash
# Odoo Incremental Sync - Linux/Mac Script
# Run this script to sync new/modified products and customers from Odoo

cd "$(dirname "$0")"
python3 incremental_sync_odoo.py

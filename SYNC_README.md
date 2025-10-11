# Odoo Incremental Sync

## Overview
This tool automatically syncs new and modified products and customers from Odoo to local JSON files. It only fetches records that have been created or updated since the last sync, making it fast and efficient.

## Files
- `incremental_sync_odoo.py` - Main sync script
- `sync_odoo.bat` - Windows shortcut (double-click to sync)
- `sync_odoo.sh` - Linux/Mac shortcut
- `odoo_database/last_sync.json` - Tracks last sync timestamp
- `odoo_database/odoo_customers.json` - Customer database
- `odoo_database/odoo_products.json` - Product database

## How It Works

### First Run (Full Sync)
```bash
python incremental_sync_odoo.py
```
- Exports all 805 customers and 2075 products
- Creates timestamp file with current time
- Takes ~30 seconds

### Subsequent Runs (Incremental)
```bash
python incremental_sync_odoo.py
```
- Only fetches records created/modified since last sync
- Merges new data with existing JSON files
- Updates existing records by ID
- Takes ~2-5 seconds (if few changes)

### Example Output
```
================================================================================
ODOO INCREMENTAL SYNC
================================================================================
Odoo URL: https://whlvm14063.wawihost.de
Database: Test1
Time: 2025-10-11 14:35:00

[INFO] Last sync: 2025-10-11T14:30:00+00:00

Connecting to Odoo...
[OK] Connected (UID: 2)

================================================================================
SYNCING CUSTOMERS
================================================================================
Last sync: 2025-10-11T14:30:00+00:00
Fetching only NEW or MODIFIED customers...
Found 3 customer(s) to sync
Fetching customer details...
Existing customers in JSON: 805
Total customers after merge: 808
[OK] Synced 3 customer(s)

================================================================================
SYNCING PRODUCTS
================================================================================
Last sync: 2025-10-11T14:30:00+00:00
Fetching only NEW or MODIFIED products...
Found 1 product(s) to sync
Fetching product details...
Existing products in JSON: 2075
Total products after merge: 2076
[OK] Synced 1 product(s)

================================================================================
SYNC SUMMARY
================================================================================
Customers synced: 3
Products synced:  1
Next sync will fetch records modified after: 2025-10-11T14:35:00+00:00

[OK] SYNC COMPLETE!
================================================================================
```

## Usage

### Manual Sync (On-Demand)

**Windows:**
```bash
# Option 1: Double-click
sync_odoo.bat

# Option 2: Command line
python incremental_sync_odoo.py
```

**Linux/Mac:**
```bash
# Option 1: Run script
./sync_odoo.sh

# Option 2: Command line
python3 incremental_sync_odoo.py
```

### Automated Sync (Scheduled)

#### Windows Task Scheduler
```powershell
# Run every 5 minutes
schtasks /create /tn "OdooSync" /tr "python D:\Projects\RAG-SDS\before-bert\incremental_sync_odoo.py" /sc minute /mo 5

# Run every 15 minutes
schtasks /create /tn "OdooSync" /tr "python D:\Projects\RAG-SDS\before-bert\incremental_sync_odoo.py" /sc minute /mo 15

# Run every hour
schtasks /create /tn "OdooSync" /tr "python D:\Projects\RAG-SDS\before-bert\incremental_sync_odoo.py" /sc hourly

# Delete task
schtasks /delete /tn "OdooSync" /f
```

#### Linux/Mac Cron
```bash
# Edit crontab
crontab -e

# Add one of these lines:
# Every 5 minutes
*/5 * * * * cd /path/to/before-bert && python3 incremental_sync_odoo.py >> logs/sync.log 2>&1

# Every 15 minutes
*/15 * * * * cd /path/to/before-bert && python3 incremental_sync_odoo.py >> logs/sync.log 2>&1

# Every hour
0 * * * * cd /path/to/before-bert && python3 incremental_sync_odoo.py >> logs/sync.log 2>&1
```

#### Python Background Service (Advanced)
```python
# create background_sync.py
import time
from incremental_sync_odoo import main

while True:
    try:
        main()
    except Exception as e:
        print(f"Sync error: {e}")
    time.sleep(300)  # 5 minutes
```

## Features

### Intelligent Merging
- Updates existing records if they've changed
- Adds new records
- Keeps all existing records
- Merges by Odoo record ID

### Timestamp Tracking
- Saves last sync time in `odoo_database/last_sync.json`
- Uses UTC timezone to avoid issues
- Only fetches records modified after last sync

### Error Handling
- Continues if one sync fails
- Provides clear error messages
- Safe to run multiple times

### Performance
- Batch processing for large datasets
- Only fetches changed records
- Typical sync takes 2-5 seconds

## Troubleshooting

### "No previous sync found. Performing FULL sync"
- Normal on first run
- Will take longer (~30 seconds)
- Creates timestamp file for future runs

### "Database is up-to-date!"
- No new/modified records since last sync
- JSON files are current
- Normal if Odoo hasn't changed

### Connection errors
- Check `.env` file has correct credentials
- Verify Odoo URL is accessible
- Run `python tests/unit/test_odoo_connection.py` to diagnose

### Force full resync
```bash
# Delete timestamp file to force full sync
rm odoo_database/last_sync.json
python incremental_sync_odoo.py
```

## Production Deployment

### Recommended Settings
- **Small business**: Every 15 minutes
- **Medium business**: Every 5 minutes
- **High volume**: Every 1-2 minutes (or use webhooks)

### Monitoring
```bash
# Add logging to cron job
*/5 * * * * cd /path/to/project && python3 incremental_sync_odoo.py >> logs/odoo_sync.log 2>&1

# Check logs
tail -f logs/odoo_sync.log

# Check last sync time
cat odoo_database/last_sync.json
```

## Integration with Email System
The email processing system automatically reads from the JSON files:
- `odoo_database/odoo_customers.json` - Customer matching
- `odoo_database/odoo_products.json` - Product matching

No configuration needed - just keep the JSON files updated with this sync script!

"""
Quick script to test Odoo connection and find database name
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import xmlrpc.client
from dotenv import load_dotenv

# Load environment variables from root directory
root_dir = os.path.join(os.path.dirname(__file__), '../..')
load_dotenv(os.path.join(root_dir, '.env'))

# Odoo credentials from .env
url = os.getenv('ODOO_URL')
username = os.getenv('ODOO_USERNAME')
password = os.getenv('ODOO_PASSWORD')
db_name = os.getenv('ODOO_DB_NAME')

print("Testing Odoo Connection...")
print(f"URL: {url}")
print(f"Username: {username}")
print(f"Database: {db_name}")
print("=" * 60)

# If database name is configured in .env, use it directly
if db_name and db_name != 'odoo_db_placeholder':
    print(f"\nTesting configured database: '{db_name}'...\n")
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db_name, username, password, {})

        if uid:
            print(f"[SUCCESS] Connected to database '{db_name}'!")
            print(f"User ID: {uid}")

            # Test a simple query
            print(f"\nTesting a simple query...")
            models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
            partner_count = models.execute_kw(
                db_name, uid, password,
                'res.partner', 'search_count',
                [[]]
            )
            print(f"[OK] Found {partner_count} contacts in database")

            print(f"\n{'=' * 60}")
            print("CONNECTION SUCCESSFUL!")
            print(f"{'=' * 60}")
            exit(0)
        else:
            print("[FAIL] Authentication failed")
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        print("\nTrying to discover database name...\n")

# Common database names to try
possible_db_names = [
    'odoo',
    'SDS',
    'sds',
    'SDS-Print',
    'sds-print',
    'sdsprint',
    'sds_print',
    'whlvm14063',
    'odoo18',
    'odoo_18',
    'main',
    'production',
]

print("\nTrying to discover database name...\n")

for db_name_test in possible_db_names:
    try:
        print(f"Trying database: '{db_name_test}'... ", end='')

        # Try to authenticate
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db_name_test, username, password, {})

        if uid:
            print(f"[OK] SUCCESS!")
            print(f"\n{'=' * 60}")
            print(f"[SUCCESS] FOUND IT!")
            print(f"{'=' * 60}")
            print(f"Database Name: {db_name_test}")
            print(f"User ID: {uid}")
            print(f"\nTesting a simple query...")

            # Test a simple query
            models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
            partner_count = models.execute_kw(
                db_name_test, uid, password,
                'res.partner', 'search_count',
                [[]]
            )
            print(f"[OK] Found {partner_count} contacts in database")

            print(f"\n{'=' * 60}")
            print("CONNECTION SUCCESSFUL!")
            print(f"{'=' * 60}")
            print("\nUse these credentials in your .env file:")
            print(f"ODOO_URL={url}")
            print(f"ODOO_DB_NAME={db_name_test}")
            print(f"ODOO_USERNAME={username}")
            print(f"ODOO_PASSWORD={password}")

            break
        else:
            print("[FAIL] Authentication failed")

    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg:
            print("[FAIL] Database does not exist")
        else:
            print(f"[FAIL] {error_msg[:80]}")
        continue
else:
    print("\n" + "=" * 60)
    print("[ERROR] Could not find database name")
    print("=" * 60)
    print("\nPlease contact your Odoo administrator or hosting provider")
    print("to get the correct database name.")

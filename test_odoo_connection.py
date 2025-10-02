"""
Quick script to test Odoo connection and find database name
"""

import xmlrpc.client

# Odoo credentials
url = 'https://whlvm14063.wawihost.de'
username = 'k.el@sds-print.com'
password = 'Test123'

print("Testing Odoo Connection...")
print(f"URL: {url}")
print(f"Username: {username}")
print("=" * 60)

# Common database names to try
possible_db_names = [
    'SDS',
    'sds',
    'SDS-Print',
    'sds-print',
    'sdsprint',
    'sds_print',
    'whlvm14063',
    'odoo18',
    'odoo_18',
    'odoo',
    'main',
    'production',
]

print("\nTrying to discover database name...\n")

for db_name in possible_db_names:
    try:
        print(f"Trying database: '{db_name}'... ", end='')

        # Try to authenticate
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db_name, username, password, {})

        if uid:
            print(f"[OK] SUCCESS!")
            print(f"\n{'=' * 60}")
            print(f"[SUCCESS] FOUND IT!")
            print(f"{'=' * 60}")
            print(f"Database Name: {db_name}")
            print(f"User ID: {uid}")
            print(f"\nTesting a simple query...")

            # Test a simple query
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
            print("\nUse these credentials in your .env file:")
            print(f"ODOO_URL={url}")
            print(f"ODOO_DB_NAME={db_name}")
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

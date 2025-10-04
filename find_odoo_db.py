"""
Test script to find Odoo database name
"""
import xmlrpc.client
from dotenv import load_dotenv
import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

url = os.getenv('ODOO_URL')
username = os.getenv('ODOO_USERNAME')
password = os.getenv('ODOO_PASSWORD')

print("="*80)
print("ODOO DATABASE FINDER")
print("="*80)
print(f"URL: {url}")
print(f"Username: {username}")
print(f"Password: {'*' * len(password)}")
print()

# Method 1: Try to get database list
print("Method 1: Trying to get database list...")
try:
    db = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/db')
    databases = db.list()
    print(f"[OK] Found {len(databases)} database(s):")
    for i, db_name in enumerate(databases, 1):
        print(f"   {i}. {db_name}")
    print()
except Exception as e:
    print(f"[ERROR] Error getting database list: {e}")
    print()

# Method 2: Try common database names
print("Method 2: Testing common database names...")
common_names = [
    'odoo',
    'production',
    'main',
    'ai2go',
    'odoo_ai2go',
    'odoo18',
    'odoo17',
    'odoo16'
]

for db_name in common_names:
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db_name, username, password, {})
        if uid:
            print(f"[SUCCESS] Database name is: '{db_name}'")
            print(f"   User ID: {uid}")
            print()
            print("="*80)
            print("UPDATE YOUR .env FILE WITH:")
            print(f"ODOO_DB_NAME={db_name}")
            print("="*80)
            break
    except Exception as e:
        print(f"[FAIL] '{db_name}' - {str(e)[:80]}")

print("\nDone!")

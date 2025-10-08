"""
Import customers from JSON file to Odoo database

This script imports customer data from odoo_customers.json into the Odoo database.
It checks for existing customers by name to avoid duplicates.
"""

import json
import sys
from pathlib import Path
from retriever_module.odoo_connector import OdooConnector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def load_customers_from_json(json_path: str) -> list:
    """Load customers from JSON file"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            customers = json.load(f)
        print(f"[OK] Loaded {len(customers)} customers from {json_path}")
        return customers
    except Exception as e:
        print(f"[ERROR] Failed to load JSON: {e}")
        return []

def customer_exists(odoo: OdooConnector, customer_name: str) -> bool:
    """Check if customer already exists in Odoo"""
    try:
        result = odoo.query_customer_info(company_name=customer_name)
        return result is not None
    except:
        return False

def import_customer(odoo: OdooConnector, customer_data: dict, dry_run: bool = False) -> dict:
    """
    Import a single customer to Odoo

    Args:
        odoo: OdooConnector instance
        customer_data: Customer data from JSON
        dry_run: If True, don't actually create, just validate

    Returns:
        Dict with success status and info
    """
    customer_name = customer_data.get('name', 'Unknown')

    # Check if already exists
    if customer_exists(odoo, customer_name):
        return {
            'success': False,
            'reason': 'already_exists',
            'name': customer_name
        }

    if dry_run:
        return {
            'success': True,
            'reason': 'dry_run',
            'name': customer_name
        }

    # Prepare customer values for Odoo
    customer_vals = {
        'name': customer_name,
        'is_company': True,  # Assuming all are companies
    }

    # Add optional fields
    if customer_data.get('ref'):
        customer_vals['ref'] = customer_data['ref']

    if customer_data.get('email') and customer_data['email'] != False:
        customer_vals['email'] = customer_data['email']

    if customer_data.get('phone') and customer_data['phone'] != False:
        customer_vals['phone'] = customer_data['phone']

    if customer_data.get('website') and customer_data['website'] != False:
        customer_vals['website'] = customer_data['website']

    if customer_data.get('street'):
        customer_vals['street'] = customer_data['street']

    if customer_data.get('zip'):
        customer_vals['zip'] = customer_data['zip']

    if customer_data.get('city'):
        customer_vals['city'] = customer_data['city']

    if customer_data.get('vat'):
        customer_vals['vat'] = customer_data['vat']

    # Country handling - JSON has [id, name], Odoo needs just ID
    # We'll skip country for now since we don't have country mapping
    # if customer_data.get('country_id') and isinstance(customer_data['country_id'], list):
    #     customer_vals['country_id'] = customer_data['country_id'][0]

    # Create customer in Odoo
    try:
        customer_id = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'res.partner', 'create',
            [customer_vals]
        )

        return {
            'success': True,
            'reason': 'created',
            'name': customer_name,
            'id': customer_id
        }
    except Exception as e:
        return {
            'success': False,
            'reason': 'error',
            'name': customer_name,
            'error': str(e)
        }

def main():
    print("="*80)
    print("CUSTOMER IMPORT TOOL - JSON to Odoo")
    print("="*80)
    print()

    # Configuration
    json_file = "odoo_database/odoo_customers.json"
    dry_run = False  # Set to True to test without creating

    # Check for --yes flag to skip confirmation
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv

    # Ask user for confirmation
    print(f"JSON File: {json_file}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will create customers)'}")
    print()

    if not auto_confirm:
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Import cancelled.")
            return
    else:
        print("Auto-confirmed with --yes flag")

    print()

    # Load customers from JSON
    customers = load_customers_from_json(json_file)
    if not customers:
        print("[ERROR] No customers to import")
        return

    # Connect to Odoo
    print("[ODOO] Connecting to Odoo...")
    try:
        odoo = OdooConnector()
        print(f"[OK] Connected to Odoo (User ID: {odoo.uid})")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Odoo: {e}")
        return

    print()
    print("="*80)
    print("IMPORTING CUSTOMERS")
    print("="*80)
    print()

    # Import customers
    stats = {
        'total': len(customers),
        'created': 0,
        'skipped': 0,
        'errors': 0
    }

    for idx, customer_data in enumerate(customers, 1):
        customer_name = customer_data.get('name', 'Unknown')
        # Handle case where name might be False or not a string
        if not customer_name or customer_name is False:
            customer_name = 'Unknown'
        display_name = str(customer_name)[:50] + ('...' if len(str(customer_name)) > 50 else '')
        print(f"[{idx}/{len(customers)}] {display_name}", end=' ')

        result = import_customer(odoo, customer_data, dry_run=dry_run)

        if result['success']:
            if result['reason'] == 'created':
                print(f"[CREATED] ID: {result['id']}")
                stats['created'] += 1
            elif result['reason'] == 'dry_run':
                print(f"[DRY RUN] Would create")
                stats['created'] += 1
        else:
            if result['reason'] == 'already_exists':
                print(f"[SKIPPED] Already exists")
                stats['skipped'] += 1
            else:
                print(f"[ERROR] {result.get('error', 'Unknown error')}")
                stats['errors'] += 1

    print()
    print("="*80)
    print("IMPORT SUMMARY")
    print("="*80)
    print(f"Total customers in JSON: {stats['total']}")
    print(f"Created in Odoo:         {stats['created']}")
    print(f"Skipped (duplicates):    {stats['skipped']}")
    print(f"Errors:                  {stats['errors']}")
    print("="*80)
    print()

    if dry_run:
        print("[INFO] This was a DRY RUN. No customers were actually created.")
        print("[INFO] Set dry_run=False in the script to create customers.")
    else:
        print("[SUCCESS] Customer import complete!")

if __name__ == "__main__":
    main()

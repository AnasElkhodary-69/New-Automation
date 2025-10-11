"""
Incremental Odoo Sync - Export only new/modified records
Syncs products and customers from Odoo to JSON files incrementally
"""

import json
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from retriever_module.odoo_connector import OdooConnector

# Load environment variables
load_dotenv()

# Paths
TIMESTAMP_FILE = "odoo_database/last_sync.json"
CUSTOMERS_FILE = "odoo_database/odoo_customers.json"
PRODUCTS_FILE = "odoo_database/odoo_products.json"


def load_timestamp():
    """Load the last sync timestamp"""
    if os.path.exists(TIMESTAMP_FILE):
        with open(TIMESTAMP_FILE, 'r') as f:
            data = json.load(f)
            return data.get('last_sync')
    return None


def save_timestamp(timestamp):
    """Save the current sync timestamp"""
    os.makedirs(os.path.dirname(TIMESTAMP_FILE), exist_ok=True)
    with open(TIMESTAMP_FILE, 'w') as f:
        json.dump({
            'last_sync': timestamp,
            'last_sync_readable': datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        }, f, indent=2)


def load_existing_json(file_path):
    """Load existing JSON data"""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_json(file_path, data):
    """Save JSON data to file"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def merge_records(existing_records, new_records):
    """
    Merge new records into existing ones
    Updates existing records by ID and adds new ones
    """
    # Create a dictionary for quick lookup
    existing_dict = {record['id']: record for record in existing_records}

    # Update or add new records
    for new_record in new_records:
        existing_dict[new_record['id']] = new_record

    # Convert back to list
    return list(existing_dict.values())


def sync_customers_incremental(odoo, last_sync):
    """
    Sync customers incrementally

    Args:
        odoo: OdooConnector instance
        last_sync: ISO format timestamp string or None for full sync
    """
    print("="*80)
    print("SYNCING CUSTOMERS")
    print("="*80)

    try:
        # Build search domain
        if last_sync:
            # Fetch records modified after last sync
            domain = [
                '|',
                ('create_date', '>', last_sync),
                ('write_date', '>', last_sync)
            ]
            print(f"Last sync: {last_sync}")
            print("Fetching only NEW or MODIFIED customers...")
        else:
            domain = []
            print("No previous sync found. Performing FULL sync...")

        # Search for customers
        partner_ids = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'res.partner', 'search',
            [domain],
            {'limit': 10000}
        )

        print(f"Found {len(partner_ids)} customer(s) to sync")

        if len(partner_ids) == 0:
            print("[OK] No new customers to sync")
            return 0

        # Read customer details
        print("Fetching customer details...")
        customers = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'res.partner', 'read',
            [partner_ids],
            {'fields': ['id', 'name', 'ref', 'email', 'phone', 'street', 'street2',
                       'city', 'zip', 'country_id', 'state_id', 'vat', 'website',
                       'create_date', 'write_date']}
        )

        # Format customers
        formatted_customers = []
        for customer in customers:
            formatted_customers.append({
                'id': customer['id'],
                'name': customer['name'],
                'ref': customer.get('ref') or '',
                'email': customer.get('email') or '',
                'phone': customer.get('phone') or '',
                'address': {
                    'street': customer.get('street') or '',
                    'street2': customer.get('street2') or '',
                    'city': customer.get('city') or '',
                    'zip': customer.get('zip') or '',
                    'country': customer['country_id'][1] if customer.get('country_id') else '',
                    'state': customer['state_id'][1] if customer.get('state_id') else ''
                },
                'vat': customer.get('vat') or '',
                'website': customer.get('website') or '',
                'create_date': customer.get('create_date', ''),
                'write_date': customer.get('write_date', '')
            })

        # Load existing customers
        existing_customers = load_existing_json(CUSTOMERS_FILE)
        print(f"Existing customers in JSON: {len(existing_customers)}")

        # Merge with existing
        merged_customers = merge_records(existing_customers, formatted_customers)
        print(f"Total customers after merge: {len(merged_customers)}")

        # Save merged data
        save_json(CUSTOMERS_FILE, merged_customers)

        print(f"[OK] Synced {len(formatted_customers)} customer(s)")
        return len(formatted_customers)

    except Exception as e:
        print(f"[ERROR] Failed to sync customers: {e}")
        raise


def sync_products_incremental(odoo, last_sync):
    """
    Sync products incrementally

    Args:
        odoo: OdooConnector instance
        last_sync: ISO format timestamp string or None for full sync
    """
    print("\n" + "="*80)
    print("SYNCING PRODUCTS")
    print("="*80)

    try:
        # Build search domain
        if last_sync:
            # Fetch records modified after last sync
            domain = [
                '|',
                ('create_date', '>', last_sync),
                ('write_date', '>', last_sync)
            ]
            print(f"Last sync: {last_sync}")
            print("Fetching only NEW or MODIFIED products...")
        else:
            domain = []
            print("No previous sync found. Performing FULL sync...")

        # Search for products
        product_ids = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'product.template', 'search',
            [domain],
            {'limit': 20000}
        )

        print(f"Found {len(product_ids)} product(s) to sync")

        if len(product_ids) == 0:
            print("[OK] No new products to sync")
            return 0

        # Read product details (in batches for performance)
        print("Fetching product details...")
        batch_size = 500
        all_products = []

        for i in range(0, len(product_ids), batch_size):
            batch_ids = product_ids[i:i+batch_size]
            if len(product_ids) > batch_size:
                print(f"  Batch {i//batch_size + 1}/{(len(product_ids)-1)//batch_size + 1}...")

            products = odoo.models.execute_kw(
                odoo.db, odoo.uid, odoo.password,
                'product.template', 'read',
                [batch_ids],
                {'fields': ['id', 'name', 'default_code', 'list_price', 'standard_price',
                           'type', 'categ_id', 'description', 'create_date', 'write_date']}
            )
            all_products.extend(products)

        # Format products
        formatted_products = []
        for product in all_products:
            formatted_products.append({
                'id': product['id'],
                'name': product['name'],
                'default_code': product.get('default_code') or '',
                'list_price': product.get('list_price', 0.0),
                'standard_price': product.get('standard_price', 0.0),
                'type': product.get('type', ''),
                'category': product['categ_id'][1] if product.get('categ_id') else '',
                'description': product.get('description') or '',
                'create_date': product.get('create_date', ''),
                'write_date': product.get('write_date', '')
            })

        # Load existing products
        existing_products = load_existing_json(PRODUCTS_FILE)
        print(f"Existing products in JSON: {len(existing_products)}")

        # Merge with existing
        merged_products = merge_records(existing_products, formatted_products)
        print(f"Total products after merge: {len(merged_products)}")

        # Save merged data
        save_json(PRODUCTS_FILE, merged_products)

        print(f"[OK] Synced {len(formatted_products)} product(s)")
        return len(formatted_products)

    except Exception as e:
        print(f"[ERROR] Failed to sync products: {e}")
        raise


def main():
    """Main incremental sync function"""
    print("="*80)
    print("ODOO INCREMENTAL SYNC")
    print("="*80)
    print(f"Odoo URL: {os.getenv('ODOO_URL')}")
    print(f"Database: {os.getenv('ODOO_DB_NAME')}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Load last sync timestamp
    last_sync = load_timestamp()

    if last_sync:
        print(f"[INFO] Last sync: {last_sync}")
    else:
        print("[INFO] First run - will perform full sync")
    print()

    # Connect to Odoo
    print("Connecting to Odoo...")
    odoo = OdooConnector()
    print(f"[OK] Connected (UID: {odoo.uid})")
    print()

    # Get current timestamp BEFORE syncing (to avoid missing records)
    # Odoo expects datetime WITHOUT timezone (naive datetime)
    current_sync = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    # Sync customers
    customers_synced = sync_customers_incremental(odoo, last_sync)

    # Sync products
    products_synced = sync_products_incremental(odoo, last_sync)

    # Save timestamp
    save_timestamp(current_sync)

    # Summary
    print("\n" + "="*80)
    print("SYNC SUMMARY")
    print("="*80)
    print(f"Customers synced: {customers_synced}")
    print(f"Products synced:  {products_synced}")
    print(f"Next sync will fetch records modified after: {current_sync}")
    print()

    if customers_synced == 0 and products_synced == 0:
        print("[OK] Database is up-to-date!")
    else:
        print("[OK] SYNC COMPLETE!")

    print("="*80)


if __name__ == "__main__":
    main()

"""
Export Odoo Database to JSON Files

This script exports customers and products from Odoo to JSON files
for use by the RAG system's fuzzy matching.
"""

import json
import os
from dotenv import load_dotenv
from retriever_module.odoo_connector import OdooConnector

# Load environment variables
load_dotenv()

def export_customers(odoo: OdooConnector, output_path: str = "odoo_database/odoo_customers.json"):
    """
    Export customers from Odoo to JSON

    Args:
        odoo: OdooConnector instance
        output_path: Path to save JSON file
    """
    print("="*80)
    print("EXPORTING CUSTOMERS FROM ODOO")
    print("="*80)

    try:
        # Search for all contacts (both companies and individuals)
        print("\nSearching for customers in Odoo...")
        partner_ids = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'res.partner', 'search',
            [[]],  # No filter - get all contacts
            {'limit': 10000}
        )

        print(f"Found {len(partner_ids)} customer IDs")

        # Read customer details
        print("Fetching customer details...")
        customers = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'res.partner', 'read',
            [partner_ids],
            {'fields': ['id', 'name', 'ref', 'email', 'phone', 'street', 'street2',
                       'city', 'zip', 'country_id', 'state_id', 'vat', 'website']}
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
                'website': customer.get('website') or ''
            })

        # Save to JSON
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(formatted_customers, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] SUCCESS: Exported {len(formatted_customers)} customers to {output_path}")
        return formatted_customers

    except Exception as e:
        print(f"\n[ERROR] Failed to export customers: {e}")
        raise


def export_products(odoo: OdooConnector, output_path: str = "odoo_database/odoo_products.json"):
    """
    Export products from Odoo to JSON

    Args:
        odoo: OdooConnector instance
        output_path: Path to save JSON file
    """
    print("\n" + "="*80)
    print("EXPORTING PRODUCTS FROM ODOO")
    print("="*80)

    try:
        # Search for all products (using product.template for Odoo 19)
        print("\nSearching for products in Odoo...")
        product_ids = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'product.template', 'search',
            [[]],
            {'limit': 20000}
        )

        print(f"Found {len(product_ids)} product IDs")

        # Read product details (in batches for performance)
        print("Fetching product details...")
        batch_size = 500
        all_products = []

        for i in range(0, len(product_ids), batch_size):
            batch_ids = product_ids[i:i+batch_size]
            print(f"  Batch {i//batch_size + 1}/{(len(product_ids)-1)//batch_size + 1}...")

            products = odoo.models.execute_kw(
                odoo.db, odoo.uid, odoo.password,
                'product.template', 'read',
                [batch_ids],
                {'fields': ['id', 'name', 'default_code', 'list_price', 'standard_price',
                           'type', 'categ_id', 'description']}
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
                'description': product.get('description') or ''
            })

        # Save to JSON
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(formatted_products, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] SUCCESS: Exported {len(formatted_products)} products to {output_path}")
        return formatted_products

    except Exception as e:
        print(f"\n[ERROR] Failed to export products: {e}")
        raise


def main():
    """Main export function"""
    print("="*80)
    print("ODOO TO JSON EXPORT TOOL")
    print("="*80)
    print(f"Odoo URL: {os.getenv('ODOO_URL')}")
    print(f"Database: {os.getenv('ODOO_DB_NAME')}")
    print()

    # Connect to Odoo
    print("Connecting to Odoo...")
    odoo = OdooConnector()
    print(f"[OK] Connected (UID: {odoo.uid})")
    print()

    # Export customers
    customers = export_customers(odoo)

    # Export products
    products = export_products(odoo)

    # Summary
    print("\n" + "="*80)
    print("EXPORT SUMMARY")
    print("="*80)
    print(f"[OK] Customers: {len(customers)} exported")
    print(f"[OK] Products:  {len(products)} exported")
    print()
    print("Files saved:")
    print("  - odoo_database/odoo_customers.json")
    print("  - odoo_database/odoo_products.json")
    print()
    print("[OK] EXPORT COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    main()

"""
Database Synchronization Script
Exports current Odoo database to JSON files for accurate matching
"""

import json
import logging
from pathlib import Path
from retriever_module.odoo_connector import OdooConnector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def export_odoo_to_json():
    """Export current Odoo database to JSON files"""

    logger.info("Starting Odoo database export...")

    # Initialize Odoo connector
    odoo = OdooConnector()

    # Export customers
    logger.info("Exporting customers...")
    customers = []

    try:
        # Search all customers (companies)
        customer_ids = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'res.partner', 'search',
            [[('is_company', '=', True)]],
            {'limit': 5000}
        )

        # Read customer data
        if customer_ids:
            customers = odoo.models.execute_kw(
                odoo.db, odoo.uid, odoo.password,
                'res.partner', 'read',
                [customer_ids],
                {'fields': ['name', 'ref', 'email', 'phone',
                           'street', 'city', 'zip', 'country_id',
                           'vat', 'website', 'comment']}
            )

        logger.info(f"Exported {len(customers)} customers")

        # Save to JSON
        output_path = Path("odoo_database/odoo_customers_new.json")
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(customers, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved customers to {output_path}")

    except Exception as e:
        logger.error(f"Error exporting customers: {e}")

    # Export products
    logger.info("Exporting products...")
    products = []

    try:
        # Search all products (using product.template for Odoo 19)
        product_ids = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'product.template', 'search',
            [[('sale_ok', '=', True)]],
            {'limit': 10000}
        )

        # Read product data
        if product_ids:
            products = odoo.models.execute_kw(
                odoo.db, odoo.uid, odoo.password,
                'product.template', 'read',
                [product_ids],
                {'fields': ['name', 'default_code', 'barcode',
                           'list_price', 'standard_price', 'description',
                           'description_sale', 'categ_id', 'product_variant_id']}
            )

        logger.info(f"Exported {len(products)} products")

        # Save to JSON
        output_path = Path("odoo_database/odoo_products_new.json")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved products to {output_path}")

    except Exception as e:
        logger.error(f"Error exporting products: {e}")

    # Create backup of old files
    logger.info("Creating backups of old JSON files...")

    for filename in ['odoo_customers.json', 'odoo_products.json']:
        old_path = Path(f"odoo_database/{filename}")
        if old_path.exists():
            backup_path = Path(f"odoo_database/{filename}.backup")
            # Remove existing backup if it exists
            if backup_path.exists():
                backup_path.unlink()
            old_path.rename(backup_path)
            logger.info(f"Backed up {filename} to {filename}.backup")

    # Rename new files to replace old ones
    for filetype in ['customers', 'products']:
        new_path = Path(f"odoo_database/odoo_{filetype}_new.json")
        final_path = Path(f"odoo_database/odoo_{filetype}.json")
        if new_path.exists():
            new_path.rename(final_path)
            logger.info(f"Activated new {filetype} database")

    logger.info("Database synchronization complete!")

    # Display summary
    print("\n" + "="*60)
    print("DATABASE SYNCHRONIZATION SUMMARY")
    print("="*60)
    print(f"Customers exported: {len(customers)}")
    print(f"Products exported: {len(products)}")
    print("\nNew JSON files are now active:")
    print("- odoo_database/odoo_customers.json")
    print("- odoo_database/odoo_products.json")
    print("\nOld files backed up as:")
    print("- odoo_database/odoo_customers.json.backup")
    print("- odoo_database/odoo_products.json.backup")
    print("="*60)


if __name__ == "__main__":
    export_odoo_to_json()
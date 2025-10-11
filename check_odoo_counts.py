"""
Check Odoo Database Counts and Export Options
"""

import os
from dotenv import load_dotenv
from retriever_module.odoo_connector import OdooConnector

load_dotenv()

def check_counts():
    """Check actual counts in Odoo database"""
    print("="*80)
    print("ODOO DATABASE COUNT CHECKER")
    print("="*80)
    print(f"URL: {os.getenv('ODOO_URL')}")
    print(f"Database: {os.getenv('ODOO_DB_NAME')}")
    print()

    # Connect to Odoo
    print("Connecting to Odoo...")
    odoo = OdooConnector()
    print(f"[OK] Connected (UID: {odoo.uid})\n")

    # Check contacts/partners
    print("="*80)
    print("PARTNERS/CONTACTS ANALYSIS")
    print("="*80)

    # All contacts
    all_contacts = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'res.partner', 'search',
        [[]],
        {'limit': 10000}
    )
    print(f"Total contacts (all):          {len(all_contacts)}")

    # Companies only
    companies = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'res.partner', 'search',
        [[('is_company', '=', True)]],
        {'limit': 10000}
    )
    print(f"Companies only (is_company=True): {len(companies)}")

    # Customers only (customer_rank > 0)
    customers = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'res.partner', 'search',
        [[('customer_rank', '>', 0)]],
        {'limit': 10000}
    )
    print(f"Customers (customer_rank > 0):    {len(customers)}")

    # Customers AND companies
    customer_companies = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'res.partner', 'search',
        [[('is_company', '=', True), ('customer_rank', '>', 0)]],
        {'limit': 10000}
    )
    print(f"Customer companies (both filters): {len(customer_companies)}")

    # Check products
    print("\n" + "="*80)
    print("PRODUCTS ANALYSIS")
    print("="*80)

    # All products
    all_products = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'product.template', 'search',
        [[]],
        {'limit': 20000}
    )
    print(f"Total products (product.template): {len(all_products)}")

    # Products that can be sold
    sale_products = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'product.template', 'search',
        [[('sale_ok', '=', True)]],
        {'limit': 20000}
    )
    print(f"Saleable products (sale_ok=True):  {len(sale_products)}")

    # Active products only
    active_products = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'product.template', 'search',
        [[('active', '=', True)]],
        {'limit': 20000}
    )
    print(f"Active products (active=True):      {len(active_products)}")

    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    print("For EMAIL PROCESSING, you probably want:")
    print(f"  - Contacts: ALL ({len(all_contacts)}) or CUSTOMER COMPANIES ({len(customer_companies)})")
    print(f"  - Products: ACTIVE SALEABLE ({len(active_products)})")
    print()

if __name__ == "__main__":
    check_counts()

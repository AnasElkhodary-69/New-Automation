"""
Test script to search for specific product in Odoo
"""
from retriever_module.odoo_connector import OdooConnector
from dotenv import load_dotenv

load_dotenv()

print("="*80)
print("TESTING ODOO PRODUCT SEARCH")
print("="*80)

# Initialize Odoo connector
odoo = OdooConnector()

# Test searching for the product
product_code = "G-25-20-125-17"
product_name = "Doctor Blade Gold 25x0,20x0,125x1,7 mm"

print(f"\nTest 1: Search by product code: '{product_code}'")
print("-" * 80)
results = odoo.query_products(product_code=product_code)
if results:
    print(f"✓ Found {len(results)} result(s):")
    for prod in results:
        print(f"  - ID: {prod.get('id')}")
        print(f"  - Code: {prod.get('default_code')}")
        print(f"  - Name: {prod.get('name')}")
        print(f"  - Price: {prod.get('list_price')}")
        print()
else:
    print("✗ No results found")

print("\nTest 2: Search by product name: '{product_name}'")
print("-" * 80)
results = odoo.query_products(product_name=product_name)
if results:
    print(f"✓ Found {len(results)} result(s):")
    for prod in results:
        print(f"  - ID: {prod.get('id')}")
        print(f"  - Code: {prod.get('default_code')}")
        print(f"  - Name: {prod.get('name')}")
        print(f"  - Price: {prod.get('list_price')}")
        print()
else:
    print("✗ No results found")

print("\nTest 3: Search for customer 'Aldemkimya'")
print("-" * 80)
customer = odoo.query_customer_info(company_name="Aldemkimya")
if customer:
    print(f"✓ Found customer:")
    print(f"  - ID: {customer.get('id')}")
    print(f"  - Name: {customer.get('name')}")
    print(f"  - Email: {customer.get('email')}")
else:
    print("✗ Customer not found")

print("\n" + "="*80)
print("Test complete!")

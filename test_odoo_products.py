"""
Test script to explore products in Odoo database
"""

from retriever_module.odoo_connector import OdooConnector

print("="*60)
print("ODOO PRODUCTS EXPLORER")
print("="*60)

# Connect to Odoo
print("\nConnecting to Odoo...")
odoo = OdooConnector()
print(f"Connected! (UID: {odoo.uid})")

# Query all products
print("\n" + "="*60)
print("Querying Products...")
print("="*60)

try:
    # Get all products (limit 50)
    products = odoo.execute_custom_query(
        model='product.product',
        domain=[],  # No filter - get all
        fields=['id', 'name', 'list_price', 'standard_price', 'qty_available', 'type', 'categ_id'],
        limit=50
    )

    print(f"\nFound {len(products)} products (showing first 50):\n")

    # Display products in a nice format
    print(f"{'ID':<8} {'Name':<40} {'Price':<12} {'Stock':<10} {'Type':<15}")
    print("-" * 95)

    for product in products:
        product_id = product.get('id', 'N/A')
        name = str(product.get('name', 'Unnamed'))[:38]
        price = f"€{product.get('list_price', 0):.2f}"
        qty = product.get('qty_available', 0)
        prod_type = product.get('type', 'N/A')

        print(f"{product_id:<8} {name:<40} {price:<12} {qty:<10.0f} {prod_type:<15}")

    # Get product categories
    print("\n" + "="*60)
    print("Product Categories:")
    print("="*60)

    categories = odoo.execute_custom_query(
        model='product.category',
        domain=[],
        fields=['id', 'name', 'parent_id'],
        limit=30
    )

    print(f"\nFound {len(categories)} categories:\n")
    for cat in categories:
        cat_id = cat.get('id')
        cat_name = cat.get('name', 'Unknown')
        parent = cat.get('parent_id')
        parent_name = parent[1] if parent and isinstance(parent, list) else 'Root'
        print(f"  [{cat_id}] {cat_name} (Parent: {parent_name})")

    # Test product search
    print("\n" + "="*60)
    print("Testing Product Search:")
    print("="*60)

    # Search for a specific product (try common terms)
    search_terms = ['Service', 'Product', 'Material', 'Consulting']

    for term in search_terms:
        results = odoo.query_products(product_name=term)
        if results:
            print(f"\nSearch '{term}': Found {len(results)} results")
            for r in results[:3]:  # Show first 3
                print(f"  - {r.get('name')} (€{r.get('list_price', 0)})")
            break

    # Get product statistics
    print("\n" + "="*60)
    print("Product Statistics:")
    print("="*60)

    # Count by type
    for prod_type in ['product', 'service', 'consu']:
        count_result = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'product.product', 'search_count',
            [[['type', '=', prod_type]]]
        )
        type_name = {'product': 'Storable Products', 'service': 'Services', 'consu': 'Consumables'}
        print(f"  {type_name.get(prod_type, prod_type)}: {count_result}")

    # Total products
    total = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'product.product', 'search_count',
        [[]]
    )
    print(f"  Total Products: {total}")

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

finally:
    odoo.close()
    print("\n" + "="*60)
    print("Done!")
    print("="*60)

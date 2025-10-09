"""
Order Creator Module

Handles creation of sales orders in Odoo
Separated from EmailProcessor for better modularity
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class OrderCreator:
    """Handles sales order creation in Odoo"""

    def __init__(self, odoo_connector):
        """
        Initialize Order Creator

        Args:
            odoo_connector: OdooConnector instance
        """
        self.odoo = odoo_connector

    def create_order_in_odoo(self, odoo_matches: Dict, entities: Dict, email: Dict) -> Optional[Dict]:
        """
        Create a sales order in Odoo from matched products

        Args:
            odoo_matches: Matched Odoo records (customer + products)
            entities: Extracted entities
            email: Original email data

        Returns:
            Order creation result or None if failed
        """
        logger.info("   Creating sales order in Odoo...")

        try:
            # Verify we have a customer
            odoo_customer = odoo_matches.get('customer')
            if not odoo_customer:
                logger.error("   [ERROR] Cannot create order: No customer found in Odoo")
                return {
                    'created': False,
                    'message': 'Customer not found in Odoo database'
                }

            customer_id = odoo_customer.get('id')
            customer_name = odoo_customer.get('name')

            # Verify we have products
            product_matches = odoo_matches.get('products', [])
            if not product_matches:
                logger.error("   [ERROR] Cannot create order: No products to add")
                return {
                    'created': False,
                    'message': 'No products found to add to order'
                }

            # Filter to only products found in Odoo
            valid_products = [p for p in product_matches if p.get('found')]
            if not valid_products:
                logger.error("   [ERROR] Cannot create order: No valid products found in Odoo")
                return {
                    'created': False,
                    'message': f'None of the {len(product_matches)} products found in Odoo'
                }

            logger.info(f"   Creating order for customer: {customer_name} (ID: {customer_id})")
            logger.info(f"   Order will contain {len(valid_products)} products")

            # Prepare order lines
            order_lines = []

            # Get extracted quantities and prices
            quantities = entities.get('quantities', [])
            prices = entities.get('prices', [])
            product_names = entities.get('product_names', [])

            # Build maps for easy lookup (use product code as key)
            quantity_map = {}
            price_map = {}

            for idx, prod_name in enumerate(product_names):
                if idx < len(quantities):
                    quantity_map[prod_name] = quantities[idx]
                if idx < len(prices):
                    price_map[prod_name] = prices[idx]

            for idx, match in enumerate(valid_products):
                product_id = match.get('id')
                product_name = match.get('name', 'Unknown')
                product_code = match.get('code', 'N/A')

                # Try to find corresponding extracted product name
                extracted_name = product_names[idx] if idx < len(product_names) else ''

                # Get quantity (from extraction or default to 1)
                quantity = quantity_map.get(extracted_name, quantities[idx] if idx < len(quantities) else 1)

                # Get price (from extraction or query from Odoo product)
                unit_price = price_map.get(extracted_name, prices[idx] if idx < len(prices) else 0)

                # Create order line
                order_line = (0, 0, {
                    'product_id': product_id,
                    'product_uom_qty': quantity,
                    'price_unit': unit_price
                })

                order_lines.append(order_line)
                logger.info(f"      + [{product_code}] {product_name[:40]} (Qty: {quantity}, Price: EUR {unit_price:.2f})")

            # Prepare order data
            order_data = {
                'partner_id': customer_id,
                'order_line': order_lines,
                'note': f"Order created from email: {email.get('subject', 'N/A')}"
            }

            # Add order reference if available
            references = entities.get('references', [])
            if references:
                order_data['client_order_ref'] = references[0]

            # Create order in Odoo
            logger.info(f"   [CREATING] Sending order to Odoo...")
            order_id = self.odoo.create_sale_order(order_data)

            if order_id:
                # Fetch order details
                order_details = self.odoo.get_sale_order(order_id)

                logger.info(f"   [OK] ORDER CREATED!")
                logger.info(f"      Order ID: {order_id}")
                logger.info(f"      Order Number: {order_details.get('name')}")
                logger.info(f"      Amount Total: EUR {order_details.get('amount_total', 0):.2f}")

                return {
                    'created': True,
                    'order_id': order_id,
                    'order_name': order_details.get('name'),
                    'amount_total': order_details.get('amount_total', 0),
                    'state': order_details.get('state'),
                    'line_count': len(order_lines)
                }
            else:
                logger.error("   [ERROR] Failed to create order in Odoo (no ID returned)")
                return {
                    'created': False,
                    'message': 'Odoo API did not return order ID'
                }

        except Exception as e:
            logger.error(f"   [ERROR] Exception while creating order: {e}", exc_info=True)
            return {
                'created': False,
                'message': f'Exception: {str(e)}'
            }

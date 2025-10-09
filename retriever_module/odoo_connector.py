"""
Odoo Connector Module

Handles connection to Odoo via XML-RPC API and data retrieval
"""

import logging
import xmlrpc.client
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class OdooConnector:
    """Class to handle Odoo API connections and queries"""

    def __init__(self, config_path: str = "config/odoo_config.json"):
        """
        Initialize Odoo Connector

        Args:
            config_path: Path to Odoo configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.url = self.config.get('url')
        self.db = self.config.get('database')
        self.username = self.config.get('username')
        self.password = self.config.get('password')
        self.uid = None
        self.common = None
        self.models = None
        self._connect()

    def _load_config(self) -> Dict:
        """
        Load Odoo configuration from environment variables

        Returns:
            Configuration dictionary with API settings
        """
        logger.info(f"Loading Odoo configuration")

        # Load from config_loader which prioritizes .env
        try:
            import os
            from dotenv import load_dotenv
            load_dotenv()

            return {
                "url": os.getenv('ODOO_URL', ''),
                "database": os.getenv('ODOO_DB_NAME', ''),
                "username": os.getenv('ODOO_USERNAME', ''),
                "password": os.getenv('ODOO_PASSWORD', ''),
            }
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {
                "url": "",
                "database": "",
                "username": "",
                "password": "",
            }

    def _connect(self):
        """Establish connection to Odoo via XML-RPC"""
        logger.info("Connecting to Odoo API...")

        try:
            # Common endpoint for authentication
            self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')

            # Authenticate
            self.uid = self.common.authenticate(
                self.db,
                self.username,
                self.password,
                {}
            )

            if not self.uid:
                raise Exception("Authentication failed")

            # Models endpoint for queries
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')

            logger.info(f"Successfully connected to Odoo (UID: {self.uid})")
        except Exception as e:
            logger.error(f"Failed to connect to Odoo: {str(e)}")
            raise

    def reconnect(self):
        """Reconnect to Odoo if connection is lost"""
        logger.info("Attempting to reconnect to Odoo...")
        self._connect()

    def query_customer_info(self, customer_id: Optional[int] = None, email: Optional[str] = None,
                           customer_name: Optional[str] = None, company_name: Optional[str] = None) -> Optional[Dict]:
        """
        Query customer information from Odoo with fuzzy matching support

        Args:
            customer_id: Customer ID in Odoo
            email: Customer email address (used for reply-to only)
            customer_name: Customer name from email body/signature
            company_name: Company name from email body/signature

        Returns:
            Customer information dictionary or None
        """
        logger.info(f"Querying customer info: id={customer_id}, email={email}, name={customer_name}, company={company_name}")

        try:
            customers = None

            # Strategy 1: Search by customer ID (highest priority)
            if customer_id:
                domain = [['id', '=', customer_id]]
                customers = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'res.partner', 'search_read',
                    [domain],
                    {'fields': ['id', 'name', 'email', 'phone', 'street', 'city', 'country_id'], 'limit': 1}
                )
                if customers:
                    logger.info(f"Found customer by ID: {customers[0].get('name')}")
                    return customers[0]

            # Strategy 2: Search by company name (preferred for B2B)
            if company_name:
                # Try exact match first
                domain = [['name', 'ilike', company_name], ['is_company', '=', True]]
                customers = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'res.partner', 'search_read',
                    [domain],
                    {'fields': ['id', 'name', 'email', 'phone', 'street', 'city', 'country_id'], 'limit': 5}
                )

                if customers:
                    logger.info(f"Found {len(customers)} company match(es) for '{company_name}': {customers[0].get('name')}")
                    return customers[0]

                # Try fuzzy variations
                variations = self._normalize_search_term(company_name)
                for variation in variations[1:]:  # Skip first (already tried)
                    logger.info(f"Trying company name variation: '{variation}'")
                    domain = [['name', 'ilike', variation], ['is_company', '=', True]]
                    customers = self.models.execute_kw(
                        self.db, self.uid, self.password,
                        'res.partner', 'search_read',
                        [domain],
                        {'fields': ['id', 'name', 'email', 'phone', 'street', 'city', 'country_id'], 'limit': 5}
                    )
                    if customers:
                        logger.info(f"Found company using variation '{variation}': {customers[0].get('name')}")
                        return customers[0]

            # Strategy 3: Search by customer name
            if customer_name:
                # Try exact match
                domain = [['name', 'ilike', customer_name]]
                customers = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'res.partner', 'search_read',
                    [domain],
                    {'fields': ['id', 'name', 'email', 'phone', 'street', 'city', 'country_id'], 'limit': 5}
                )

                if customers:
                    logger.info(f"Found {len(customers)} customer match(es) for '{customer_name}': {customers[0].get('name')}")
                    return customers[0]

            # Strategy 4: Search by email (fallback, mainly for reply-to)
            if email:
                domain = [['email', '=', email]]
                customers = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'res.partner', 'search_read',
                    [domain],
                    {'fields': ['id', 'name', 'email', 'phone', 'street', 'city', 'country_id'], 'limit': 1}
                )

                if customers:
                    logger.info(f"Found customer by email: {customers[0].get('name')}")
                    return customers[0]

            logger.warning("No customer found with provided criteria")
            return None

        except Exception as e:
            logger.error(f"Error querying customer info: {str(e)}")
            return None

    def query_orders(self, customer_id: int, limit: int = 10) -> List[Dict]:
        """
        Query customer orders from Odoo

        Args:
            customer_id: Customer ID
            limit: Maximum number of orders to return

        Returns:
            List of order dictionaries
        """
        logger.info(f"Querying orders for customer {customer_id}")

        try:
            orders = self.models.execute_kw(
                self.db, self.uid, self.password,
                'sale.order', 'search_read',
                [[['partner_id', '=', customer_id]]],
                {
                    'fields': ['id', 'name', 'date_order', 'amount_total', 'state', 'partner_id'],
                    'order': 'date_order desc',
                    'limit': limit
                }
            )

            return orders

        except Exception as e:
            logger.error(f"Error querying orders: {str(e)}")
            return []

    def query_invoices(self, customer_id: int, limit: int = 10) -> List[Dict]:
        """
        Query customer invoices from Odoo

        Args:
            customer_id: Customer ID
            limit: Maximum number of invoices to return

        Returns:
            List of invoice dictionaries
        """
        logger.info(f"Querying invoices for customer {customer_id}")

        try:
            invoices = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.move', 'search_read',
                [[['partner_id', '=', customer_id], ['move_type', 'in', ['out_invoice', 'out_refund']]]],
                {
                    'fields': ['id', 'name', 'invoice_date', 'amount_total', 'state', 'payment_state'],
                    'order': 'invoice_date desc',
                    'limit': limit
                }
            )

            return invoices

        except Exception as e:
            logger.error(f"Error querying invoices: {str(e)}")
            return []

    def _normalize_search_term(self, term: str) -> List[str]:
        """
        Generate multiple normalized variations of a search term for fuzzy matching

        Args:
            term: Original search term

        Returns:
            List of normalized variations to try
        """
        import re

        variations = [term]  # Always try original first

        # Variation 1: Normalize decimals (comma → period)
        if ',' in term:
            variations.append(term.replace(',', '.'))

        # Variation 2: Remove all spaces (for compact codes like "3M9353R")
        no_spaces = term.replace(' ', '')
        if no_spaces != term and len(no_spaces) > 5:  # Only if result is meaningful
            variations.append(no_spaces)

        # Variation 3: Remove special characters except alphanumeric, spaces, and basic punctuation
        cleaned = re.sub(r'[^\w\s\-\.]', '', term)
        if cleaned != term and len(cleaned) > 5:
            variations.append(cleaned)

        # Variation 4: Extract key alphanumeric sequences (potential product codes)
        # Look for patterns like: "9353R", "L1020", "SDS011A"
        # Must be 4+ characters and contain at least one digit
        key_terms = re.findall(r'\b[A-Z]*[0-9]+[A-Z0-9\-]*\b', term.upper())
        # Filter: only add if 4+ chars and not common words
        common_words = {'TAPE', 'PEN', 'SEAL', 'BLADE', 'GOLD', 'CARBON', 'METERS', 'DYN'}
        for kt in key_terms:
            if len(kt) >= 4 and kt not in common_words:
                variations.append(kt)

        # Variation 5: Extract brand+model patterns (e.g., "3M 9353" -> "3M9353")
        brand_model = re.findall(r'\b([A-Z0-9]+)\s+([A-Z0-9]+)', term.upper())
        for brand, model in brand_model:
            combined = brand + model
            if len(combined) >= 4:
                variations.append(combined)

        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for v in variations:
            if v and v not in seen:
                seen.add(v)
                unique_variations.append(v)

        return unique_variations

    def query_products(self, product_name: Optional[str] = None, product_id: Optional[int] = None, product_code: Optional[str] = None) -> List[Dict]:
        """
        Query product information from Odoo with comprehensive fuzzy matching

        Args:
            product_name: Product name or partial name
            product_id: Product ID
            product_code: Product code (e.g., "G-25-20-125-17")

        Returns:
            List of product dictionaries
        """
        logger.info(f"Querying products: name={product_name}, id={product_id}, code={product_code}")

        try:
            products = []

            # Strategy 1: Search by product ID
            if product_id:
                domain = [['id', '=', product_id]]
                products = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'product.template', 'search_read',
                    [domain],
                    {
                        'fields': ['id', 'name', 'default_code', 'list_price', 'standard_price', 'product_variant_id'],
                        'limit': 20
                    }
                )

            # Strategy 2: Search by product code (highest priority)
            elif product_code:
                # Normalize the product code for better matching
                # Examples: "3M L1020 685 33m" -> ["L1020-685-33", "L1020 685 33", "L1020-685", "685"]
                normalized_codes = self._normalize_product_code(product_code)

                # Try exact match first
                domain = [['default_code', '=', product_code]]
                products = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'product.template', 'search_read',
                    [domain],
                    {
                        'fields': ['id', 'name', 'default_code', 'list_price', 'standard_price', 'product_variant_id'],
                        'limit': 20
                    }
                )

                if products:
                    logger.info(f"Found {len(products)} product(s) by exact code '{product_code}'")
                else:
                    # Try normalized variations
                    for norm_code in normalized_codes:
                        domain = [['default_code', 'ilike', norm_code]]
                        products = self.models.execute_kw(
                            self.db, self.uid, self.password,
                            'product.template', 'search_read',
                            [domain],
                            {
                                'fields': ['id', 'name', 'default_code', 'list_price', 'standard_price', 'product_variant_id'],
                                'limit': 20
                            }
                        )

                        if products:
                            logger.info(f"Found {len(products)} product(s) by normalized code '{norm_code}' (from '{product_code}')")
                            break

                    if not products:
                        # Try fuzzy matching with original code
                        domain = [['default_code', 'ilike', product_code]]
                        products = self.models.execute_kw(
                            self.db, self.uid, self.password,
                            'product.template', 'search_read',
                            [domain],
                            {
                                'fields': ['id', 'name', 'default_code', 'list_price', 'standard_price', 'product_variant_id'],
                                'limit': 20
                            }
                        )

                        if products:
                            logger.info(f"Found {len(products)} product(s) by fuzzy code match '{product_code}'")
                        else:
                            # Try reversed: search for codes that contain the search term
                            # Strip last char if it's a letter (SDS016E -> SDS016)
                            if product_code and product_code[-1].isalpha():
                                truncated = product_code[:-1]
                                domain = [['default_code', 'ilike', truncated]]
                                products = self.models.execute_kw(
                                    self.db, self.uid, self.password,
                                    'product.template', 'search_read',
                                    [domain],
                                    {
                                        'fields': ['id', 'name', 'default_code', 'list_price', 'standard_price', 'product_variant_id'],
                                        'limit': 20
                                    }
                                )
                                if products:
                                    logger.info(f"Found {len(products)} product(s) by truncated code '{truncated}'")

            # Strategy 3: Search by product name with comprehensive fuzzy matching
            elif product_name:
                variations = self._normalize_search_term(product_name)
                logger.info(f"Trying {len(variations)} search variations for: {product_name}")

                for i, variation in enumerate(variations):
                    if i == 0:
                        # First variation: exact match in name field
                        domain = [['name', 'ilike', variation]]
                    else:
                        # Subsequent variations: search in both name and default_code
                        logger.info(f"Trying variation {i+1}: '{variation}'")
                        domain = ['|', ['name', 'ilike', variation], ['default_code', 'ilike', variation]]

                    products = self.models.execute_kw(
                        self.db, self.uid, self.password,
                        'product.template', 'search_read',
                        [domain],
                        {
                            'fields': ['id', 'name', 'default_code', 'list_price', 'standard_price', 'product_variant_id'],
                            'limit': 20
                        }
                    )

                    if products:
                        if i > 0:
                            logger.info(f"Found {len(products)} match(es) using variation '{variation}'")
                        break
            else:
                return []

            return products

        except Exception as e:
            logger.error(f"Error querying products: {str(e)}")
            return []

    def search_by_reference(self, reference: str) -> Optional[Dict]:
        """
        Search for order/invoice by reference number

        Args:
            reference: Reference number (order number, invoice number, etc.)

        Returns:
            Document information or None
        """
        logger.info(f"Searching for reference: {reference}")

        try:
            # Check orders
            orders = self.models.execute_kw(
                self.db, self.uid, self.password,
                'sale.order', 'search_read',
                [[['name', '=', reference]]],
                {'fields': ['id', 'name', 'partner_id', 'amount_total', 'state'], 'limit': 1}
            )

            if orders:
                return {'type': 'order', 'data': orders[0]}

            # Check invoices
            invoices = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.move', 'search_read',
                [[['name', '=', reference]]],
                {'fields': ['id', 'name', 'partner_id', 'amount_total', 'state'], 'limit': 1}
            )

            if invoices:
                return {'type': 'invoice', 'data': invoices[0]}

            return None

        except Exception as e:
            logger.error(f"Error searching by reference: {str(e)}")
            return None

    def get_recent_activity(self, customer_id: int, days: int = 30) -> Dict:
        """
        Get recent customer activity (orders, invoices, etc.)

        Args:
            customer_id: Customer ID
            days: Number of days to look back

        Returns:
            Dictionary with recent activity summary
        """
        logger.info(f"Getting recent activity for customer {customer_id} (last {days} days)")

        from datetime import datetime, timedelta
        date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        try:
            # Recent orders
            orders = self.models.execute_kw(
                self.db, self.uid, self.password,
                'sale.order', 'search_read',
                [[['partner_id', '=', customer_id], ['date_order', '>=', date_from]]],
                {'fields': ['id', 'name', 'date_order', 'amount_total', 'state']}
            )

            # Recent invoices
            invoices = self.models.execute_kw(
                self.db, self.uid, self.password,
                'account.move', 'search_read',
                [[['partner_id', '=', customer_id], ['invoice_date', '>=', date_from]]],
                {'fields': ['id', 'name', 'invoice_date', 'amount_total', 'state']}
            )

            return {
                'orders': orders,
                'invoices': invoices,
                'period_days': days
            }

        except Exception as e:
            logger.error(f"Error getting recent activity: {str(e)}")
            return {
                'orders': [],
                'invoices': [],
                'period_days': days
            }

    def execute_custom_query(self, model: str, domain: List, fields: List[str], limit: int = 100) -> List[Dict]:
        """
        Execute custom query on Odoo model

        Args:
            model: Odoo model name (e.g., 'res.partner', 'sale.order')
            domain: Search domain as list of tuples
            fields: List of fields to retrieve
            limit: Maximum number of records

        Returns:
            Query results as list of dictionaries
        """
        logger.info(f"Executing custom query on model {model}")

        try:
            results = self.models.execute_kw(
                self.db, self.uid, self.password,
                model, 'search_read',
                [domain],
                {'fields': fields, 'limit': limit}
            )

            return results

        except Exception as e:
            logger.error(f"Error executing custom query: {str(e)}")
            return []

    def create_sale_order(self, order_data: Dict) -> Optional[int]:
        """
        Create a sales order in Odoo

        Args:
            order_data: Order dictionary with:
                - partner_id: Odoo customer ID (required)
                - order_line: List of order line tuples in format (0, 0, {line_data})
                - note: Order notes (optional)
                - client_order_ref: Customer reference (optional)
                - date_order: Order date (optional)

        Returns:
            Order ID if successful, None if failed
        """
        partner_id = order_data.get('partner_id')
        order_lines = order_data.get('order_line', [])

        logger.info(f"Creating sale order for customer {partner_id} with {len(order_lines)} line(s)")

        try:
            # Prepare order values
            order_vals = {
                'partner_id': partner_id,
                'state': 'draft',  # Create as draft
            }

            # Add optional fields from order_data
            if order_data.get('note'):
                order_vals['note'] = order_data['note']
            if order_data.get('client_order_ref'):
                order_vals['client_order_ref'] = order_data['client_order_ref']
            if order_data.get('date_order'):
                order_vals['date_order'] = order_data['date_order']

            # Add order lines (already formatted as tuples)
            order_vals['order_line'] = order_lines

            if not order_lines:
                logger.error("No order lines provided")
                return None

            # Create the order
            logger.info(f"Sending create request to Odoo...")
            order_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'sale.order', 'create',
                [order_vals]
            )

            if order_id:
                logger.info(f"[OK] Sale order created successfully! Order ID: {order_id}")
                return order_id

            return None

        except Exception as e:
            logger.error(f"Error creating sale order: {str(e)}", exc_info=True)
            return None

    def get_sale_order(self, order_id: int) -> Optional[Dict]:
        """
        Get sales order details by ID

        Args:
            order_id: Order ID

        Returns:
            Order dictionary or None
        """
        try:
            order = self.models.execute_kw(
                self.db, self.uid, self.password,
                'sale.order', 'read',
                [order_id],
                {'fields': ['name', 'id', 'partner_id', 'amount_total', 'state', 'date_order']}
            )

            if order:
                return order[0]
            return None

        except Exception as e:
            logger.error(f"Error getting sale order: {str(e)}")
            return None

    def close(self):
        """Close Odoo connection (XML-RPC is stateless, so just log)"""
        logger.info("Odoo connection session ended")
        self.uid = None

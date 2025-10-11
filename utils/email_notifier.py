"""
Email Notification System
Sends formatted email notifications for each processed email with detailed breakdown
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Sends detailed email notifications for processed emails"""

    def __init__(self):
        """Initialize email notifier with SMTP configuration"""
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_address = os.getenv('EMAIL_ADDRESS')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.admin_email = os.getenv('ADMIN_EMAIL', self.email_address)

        # Notification settings
        self.enabled = os.getenv('ENABLE_EMAIL_NOTIFICATIONS', 'true').lower() == 'true'
        self.notification_email = os.getenv('NOTIFICATION_EMAIL', self.admin_email)

        if not all([self.smtp_server, self.email_address, self.email_password]):
            logger.warning("Email credentials not fully configured - notifications disabled")
            self.enabled = False

    def send_processing_notification(self, email_data: Dict, processing_result: Dict) -> bool:
        """
        Send detailed processing notification for a single email

        Args:
            email_data: Original email data
            processing_result: Result from email processor

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Email notifications disabled")
            return False

        try:
            # Build email content
            subject = self._build_subject(email_data, processing_result)
            body = self._build_html_body(email_data, processing_result)

            # Send email
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_address
            msg['To'] = self.notification_email
            msg['Subject'] = subject

            # Attach HTML body
            html_part = MIMEText(body, 'html')
            msg.attach(html_part)

            # Send via SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)

            logger.info(f"Processing notification sent to {self.notification_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    def _build_subject(self, email_data: Dict, processing_result: Dict) -> str:
        """Build email subject line"""
        intent_type = processing_result.get('intent', {}).get('type', 'Unknown')
        company = processing_result.get('entities', {}).get('company_name', 'Unknown Company')
        success = "[OK]" if processing_result.get('success') else "[FAILED]"

        return f"{success} New {intent_type.replace('_', ' ').title()} - {company}"

    def _build_html_body(self, email_data: Dict, processing_result: Dict) -> str:
        """Build HTML email body with detailed breakdown"""
        intent = processing_result.get('intent', {})
        entities = processing_result.get('entities', {})
        context = processing_result.get('context', {})
        odoo_matches = processing_result.get('odoo_matches', {})
        order_created = processing_result.get('order_created', {})
        success = processing_result.get('success', False)

        # Extract key data
        customer_info = context.get('customer_info')
        products = context.get('json_data', {}).get('products', [])
        original_subject = email_data.get('subject', 'No Subject')
        original_from = email_data.get('from', 'Unknown')

        # Build HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 900px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                }}
                .status-badge {{
                    display: inline-block;
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 14px;
                }}
                .status-success {{ background-color: #4CAF50; }}
                .status-warning {{ background-color: #ff9800; }}
                .status-error {{ background-color: #f44336; }}
                .section {{
                    background-color: #f9f9f9;
                    border-left: 4px solid #667eea;
                    padding: 20px;
                    margin-bottom: 20px;
                    border-radius: 5px;
                }}
                .section-title {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #667eea;
                    margin-bottom: 15px;
                    display: flex;
                    align-items: center;
                }}
                .section-title::before {{
                    content: '>';
                    margin-right: 10px;
                }}
                .info-grid {{
                    display: grid;
                    grid-template-columns: 150px 1fr;
                    gap: 10px;
                    margin: 10px 0;
                }}
                .info-label {{
                    font-weight: bold;
                    color: #666;
                }}
                .info-value {{
                    color: #333;
                }}
                .product-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                }}
                .product-table th {{
                    background-color: #667eea;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    font-weight: bold;
                }}
                .product-table td {{
                    padding: 10px 12px;
                    border-bottom: 1px solid #ddd;
                }}
                .product-table tr:hover {{
                    background-color: #f5f5f5;
                }}
                .match-score {{
                    font-weight: bold;
                }}
                .match-high {{ color: #4CAF50; }}
                .match-medium {{ color: #ff9800; }}
                .match-low {{ color: #f44336; }}
                .footer {{
                    text-align: center;
                    color: #888;
                    font-size: 12px;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                }}
                .badge {{
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                .badge-success {{ background-color: #d4edda; color: #155724; }}
                .badge-warning {{ background-color: #fff3cd; color: #856404; }}
                .badge-danger {{ background-color: #f8d7da; color: #721c24; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Email Processing Report</h1>
                <p><span class="status-badge status-{'success' if success else 'error'}">
                    {'[OK] Successfully Processed' if success else '[FAILED] Processing Failed'}
                </span></p>
                <p style="margin: 5px 0;">Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <!-- ORIGINAL EMAIL INFO -->
            <div class="section">
                <div class="section-title">Original Email</div>
                <div class="info-grid">
                    <div class="info-label">From:</div>
                    <div class="info-value">{original_from}</div>
                    <div class="info-label">Subject:</div>
                    <div class="info-value">{original_subject}</div>
                    <div class="info-label">Date:</div>
                    <div class="info-value">{email_data.get('date', 'Unknown')}</div>
                </div>
            </div>

            <!-- INTENT CLASSIFICATION -->
            <div class="section">
                <div class="section-title">Intent Classification</div>
                <div class="info-grid">
                    <div class="info-label">Intent Type:</div>
                    <div class="info-value"><strong>{intent.get('type', 'Unknown').replace('_', ' ').title()}</strong></div>
                    <div class="info-label">Confidence:</div>
                    <div class="info-value">
                        <span class="match-score match-{'high' if intent.get('confidence', 0) >= 0.8 else 'medium' if intent.get('confidence', 0) >= 0.6 else 'low'}">
                            {intent.get('confidence', 0):.0%}
                        </span>
                    </div>
                    <div class="info-label">Sub-Type:</div>
                    <div class="info-value">{intent.get('sub_type', 'N/A')}</div>
                </div>
            </div>

            <!-- COMPANY/CUSTOMER PARSED -->
            <div class="section">
                <div class="section-title">Company Information Parsed</div>
                <div class="info-grid">
                    <div class="info-label">Company Name:</div>
                    <div class="info-value"><strong>{entities.get('company_name', 'Not extracted')}</strong></div>
                    <div class="info-label">Contact Person:</div>
                    <div class="info-value">{entities.get('customer_name', 'Not extracted')}</div>
                    <div class="info-label">Email:</div>
                    <div class="info-value">{', '.join(entities.get('customer_emails', [])) or 'Not extracted'}</div>
                    <div class="info-label">Phone:</div>
                    <div class="info-value">{', '.join(entities.get('phone_numbers', [])) or 'Not extracted'}</div>
                </div>
            </div>

            <!-- PRODUCTS PARSED -->
            <div class="section">
                <div class="section-title">Products Parsed from Email</div>
                <p><strong>{len(entities.get('product_names', []))} products</strong> extracted from email content</p>
                {self._build_products_parsed_table(entities)}
            </div>

            <!-- COMPANY MATCHING -->
            <div class="section">
                <div class="section-title">Company Matching Result</div>
                {self._build_customer_match_html(customer_info, odoo_matches.get('customer'))}
            </div>

            <!-- PRODUCT MATCHING -->
            <div class="section">
                <div class="section-title">Product Matching Results</div>
                <p><strong>{len(products)} of {len(entities.get('product_names', []))}</strong> products matched in database</p>
                {self._build_product_match_table(products, odoo_matches.get('products', []))}
            </div>

            <!-- ORDER CREATION (if applicable) -->
            {self._build_order_section_html(order_created) if order_created.get('created') else ''}

            <!-- PROCESSING SUMMARY -->
            <div class="section">
                <div class="section-title">Processing Summary</div>
                <div class="info-grid">
                    <div class="info-label">Status:</div>
                    <div class="info-value">
                        <span class="badge badge-{'success' if success else 'danger'}">
                            {'[OK] Success' if success else '[FAILED] Failed'}
                        </span>
                    </div>
                    <div class="info-label">Intent:</div>
                    <div class="info-value">{intent.get('type', 'Unknown')}</div>
                    <div class="info-label">Company Matched:</div>
                    <div class="info-value">
                        <span class="badge badge-{'success' if customer_info else 'warning'}">
                            {'[OK] Yes' if customer_info else '[WARNING] No'}
                        </span>
                    </div>
                    <div class="info-label">Products Matched:</div>
                    <div class="info-value">
                        {len(products)}/{len(entities.get('product_names', []))}
                        <span class="badge badge-{'success' if len(products) == len(entities.get('product_names', [])) else 'warning' if len(products) > 0 else 'danger'}">
                            {len(products) / len(entities.get('product_names', [])) * 100 if len(entities.get('product_names', [])) > 0 else 0:.0f}%
                        </span>
                    </div>
                    <div class="info-label">Order Created:</div>
                    <div class="info-value">
                        <span class="badge badge-{'success' if order_created.get('created') else 'warning'}">
                            {'[OK] Yes' if order_created.get('created') else '[WARNING] No'}
                        </span>
                    </div>
                </div>
            </div>

            <div class="footer">
                <p>RAG Email Processing System</p>
                <p>This is an automated notification. Do not reply to this email.</p>
            </div>
        </body>
        </html>
        """

        return html

    def _build_products_parsed_table(self, entities: Dict) -> str:
        """Build HTML table of parsed products"""
        product_names = entities.get('product_names', [])
        product_codes = entities.get('product_codes', [])
        quantities = entities.get('quantities', [])
        prices = entities.get('prices', [])

        if not product_names:
            return "<p>No products extracted from email.</p>"

        html = """
        <table class="product-table">
            <tr>
                <th>#</th>
                <th>Product Name</th>
                <th>Product Code</th>
                <th>Quantity</th>
                <th>Price (EUR)</th>
            </tr>
        """

        for idx, name in enumerate(product_names):
            code = product_codes[idx] if idx < len(product_codes) else 'N/A'
            qty = quantities[idx] if idx < len(quantities) else 'N/A'
            price = f"{prices[idx]:.2f}" if idx < len(prices) and prices[idx] else 'N/A'

            html += f"""
            <tr>
                <td>{idx + 1}</td>
                <td><strong>{name}</strong></td>
                <td>{code}</td>
                <td>{qty}</td>
                <td>{price}</td>
            </tr>
            """

        html += "</table>"
        return html

    def _build_customer_match_html(self, json_customer: Dict, odoo_customer: Dict) -> str:
        """Build HTML for customer matching results"""
        if not json_customer and not odoo_customer:
            return """
            <p><span class="badge badge-warning">[WARNING] No customer match found</span></p>
            <p>Customer will need to be identified manually.</p>
            """

        html = "<div class='info-grid'>"

        if json_customer:
            match_score = json_customer.get('match_score', 0)
            score_class = 'match-high' if match_score >= 0.8 else 'match-medium' if match_score >= 0.6 else 'match-low'

            html += f"""
            <div class="info-label">JSON Database:</div>
            <div class="info-value">
                <span class="badge badge-success">[OK] Found</span>
                <strong>{json_customer.get('name', 'Unknown')}</strong>
                <span class="match-score {score_class}">({match_score:.0%} match)</span>
            </div>
            <div class="info-label">Customer Ref:</div>
            <div class="info-value">{json_customer.get('ref', 'N/A')}</div>
            <div class="info-label">Contact:</div>
            <div class="info-value">{json_customer.get('email', 'N/A')} | {json_customer.get('phone', 'N/A')}</div>
            """

        if odoo_customer:
            html += f"""
            <div class="info-label">Odoo Database:</div>
            <div class="info-value">
                <span class="badge badge-success">[OK] Found</span>
                <strong>{odoo_customer.get('name', 'Unknown')}</strong> (ID: {odoo_customer.get('id', 'N/A')})
            </div>
            """
        else:
            html += """
            <div class="info-label">Odoo Database:</div>
            <div class="info-value"><span class="badge badge-warning">[WARNING] Not found in Odoo</span></div>
            """

        html += "</div>"
        return html

    def _build_product_match_table(self, json_products: List[Dict], odoo_products: List[Dict]) -> str:
        """Build HTML table of product matching results"""
        if not json_products:
            return "<p>No products were matched in the database.</p>"

        # Build map of Odoo products by code
        odoo_map = {}
        for match in odoo_products:
            odoo_prod = match.get('odoo_product')
            if odoo_prod:
                code = odoo_prod.get('default_code')
                if code:
                    odoo_map[code] = odoo_prod

        html = """
        <table class="product-table">
            <tr>
                <th>#</th>
                <th>Product Code</th>
                <th>Product Name</th>
                <th>Match Score</th>
                <th>Odoo Status</th>
                <th>Price (EUR)</th>
            </tr>
        """

        for idx, prod in enumerate(json_products):
            code = prod.get('default_code', 'N/A')
            name = prod.get('name', 'Unknown')
            score = prod.get('match_score', 0)
            score_class = 'match-high' if score >= 0.8 else 'match-medium' if score >= 0.6 else 'match-low'

            odoo_prod = odoo_map.get(code)
            odoo_status = '[OK] In Odoo' if odoo_prod else '[WARNING] Not in Odoo'
            odoo_badge = 'badge-success' if odoo_prod else 'badge-warning'

            price = prod.get('standard_price', 0)

            html += f"""
            <tr>
                <td>{idx + 1}</td>
                <td><strong>{code}</strong></td>
                <td>{name}</td>
                <td><span class="match-score {score_class}">{score:.0%}</span></td>
                <td><span class="badge {odoo_badge}">{odoo_status}</span></td>
                <td>{price:.2f}</td>
            </tr>
            """

        html += "</table>"
        return html

    def _build_order_section_html(self, order_created: Dict) -> str:
        """Build HTML for order creation section"""
        if not order_created.get('created'):
            return ""

        return f"""
        <div class="section">
            <div class="section-title">Order Created in Odoo</div>
            <div class="info-grid">
                <div class="info-label">Order Number:</div>
                <div class="info-value"><strong>{order_created.get('order_name', 'N/A')}</strong></div>
                <div class="info-label">Order ID:</div>
                <div class="info-value">{order_created.get('order_id', 'N/A')}</div>
                <div class="info-label">Total Amount:</div>
                <div class="info-value"><strong>EUR {order_created.get('amount_total', 0):.2f}</strong></div>
                <div class="info-label">Status:</div>
                <div class="info-value"><span class="badge badge-success">{order_created.get('state', 'N/A')}</span></div>
                <div class="info-label">Line Items:</div>
                <div class="info-value">{order_created.get('line_count', 0)}</div>
            </div>
        </div>
        """

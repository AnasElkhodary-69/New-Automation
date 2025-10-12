"""
Telegram Message Formatter
Formats order processing results into readable Telegram messages
"""

from typing import Dict, List, Optional
from datetime import datetime


class TelegramMessageFormatter:
    """Format processing results for Telegram notifications"""

    def __init__(self):
        """Initialize formatter"""
        pass


    def format_order_notification(
        self,
        email: Dict,
        result: Dict,
        order_id: str
    ) -> str:
        """
        Format complete order notification with parsed vs matched comparison

        Args:
            email: Original email data
            result: Processing result from EmailProcessor
            order_id: Order identifier

        Returns:
            Formatted Telegram message
        """
        # Extract data
        intent = result.get('intent', {})
        entities = result.get('entities', {})
        context = result.get('context', {})
        odoo_matches = result.get('odoo_matches', {})
        order_created = result.get('order_created', {})

        customer_info = context.get('customer_info')
        products = context.get('json_data', {}).get('products', [])

        # Build message parts
        header = self._format_header(order_id, email)
        company_section = self._format_company_section(entities, customer_info, odoo_matches.get('customer'))
        products_section = self._format_products_section(entities, products, odoo_matches.get('products', []))
        summary_section = self._format_summary(intent, entities, odoo_matches, order_created)
        footer = self._format_footer(order_id)

        # Combine all sections
        message = f"{header}\n\n{company_section}\n\n{products_section}\n\n{summary_section}\n\n{footer}"

        return message

    def _format_header(self, order_id: str, email: Dict) -> str:
        """Format message header"""
        subject = email.get('subject', 'No Subject')
        from_email = email.get('from', 'Unknown')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return f"""🔔 NEW ORDER #{order_id}

📧 Email Info:
  From: {from_email}
  Subject: {subject}
  Time: {timestamp}"""

    def _format_company_section(
        self,
        entities: Dict,
        json_customer: Optional[Dict],
        odoo_customer: Optional[Dict]
    ) -> str:
        """Format company parsing and matching section"""
        company_extracted = entities.get('company_name', 'Not extracted')
        contact_extracted = entities.get('customer_name', 'Not extracted')

        section = "🏢 COMPANY\n"
        section += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        section += f"  Extracted: \"{company_extracted}\"\n"

        if json_customer:
            match_score = json_customer.get('match_score', 0)
            matched_name = json_customer.get('name', 'Unknown')
            icon = "✅" if match_score >= 0.8 else "⚠️"
            section += f"  {icon} Matched: \"{matched_name}\" ({match_score:.0%})\n"

            if odoo_customer:
                odoo_id = odoo_customer.get('id')
                section += f"  📊 Odoo ID: {odoo_id}\n"
            else:
                section += f"  ⚠️ Odoo: Not found in database\n"
        else:
            section += f"  ❌ Matched: No match found\n"

        section += f"  👤 Contact: {contact_extracted}"

        return section

    def _format_products_section(
        self,
        entities: Dict,
        json_products: List[Dict],
        odoo_products: List[Dict]
    ) -> str:
        """
        Format products section: ONE entry per extracted product
        Shows: [Extracted Name] → [Matched in JSON?] → [Found in Odoo?]
        """
        product_names = entities.get('product_names', [])
        product_codes = entities.get('product_codes', [])
        quantities = entities.get('quantities', [])
        prices = entities.get('prices', [])

        total_parsed = len(product_names)

        # Count how many products were actually matched in Odoo
        total_matched_odoo = sum(1 for match in odoo_products if match.get('odoo_product') is not None)

        section = f"📦 PRODUCTS ({total_matched_odoo}/{total_parsed} matched)\n"
        section += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        # Loop through each EXTRACTED product (from DSPy)
        # Match by INDEX position (both lists are in the same order)
        for idx, extracted_name in enumerate(product_names, 1):
            # Get extracted data
            extracted_code = product_codes[idx-1] if idx-1 < len(product_codes) else None
            qty = quantities[idx-1] if idx-1 < len(quantities) else 0
            price = prices[idx-1] if idx-1 < len(prices) else 0.0

            # Get match by index position (odoo_products[idx-1])
            match = odoo_products[idx-1] if idx-1 < len(odoo_products) else None
            json_prod = match.get('json_product') if match else None
            odoo_prod = match.get('odoo_product') if match else None

            # Status icon
            if odoo_prod:
                icon = "✅"
                status = "Matched"
            elif json_prod:
                icon = "⚠️"
                status = "Partial Match"
            else:
                icon = "❌"
                status = "No Match"

            # Format product entry
            section += f"\n{idx}. {icon} {status}\n"
            section += f"   Extracted: {extracted_name}\n"
            if extracted_code:
                section += f"   Code: {extracted_code}\n"

            # Show match details if found
            if odoo_prod:
                odoo_name = odoo_prod.get('name', 'Unknown')
                odoo_code = odoo_prod.get('default_code', 'N/A')
                odoo_id = odoo_prod.get('id', 'N/A')

                section += f"   Matched: {odoo_name}\n"
                section += f"   Code: {odoo_code}\n"
                section += f"   Odoo ID: {odoo_id}\n"
            elif json_prod:
                json_name = json_prod.get('name', 'Unknown')
                json_code = json_prod.get('default_code', 'N/A')
                section += f"   Partial Match: {json_name}\n"
                section += f"   Code: {json_code}\n"
                section += f"   ⚠️ Not verified in Odoo\n"

            # Quantity and price
            section += f"   Qty: {qty} | Price: €{price:.2f}\n"

        return section

    def _format_summary(
        self,
        intent: Dict,
        entities: Dict,
        odoo_matches: Dict,
        order_created: Dict
    ) -> str:
        """Format processing summary"""
        intent_type = intent.get('type', 'Unknown')
        confidence = intent.get('confidence', 0)
        product_count = len(entities.get('product_names', []))

        # Count matched products from odoo_matches
        odoo_products = odoo_matches.get('products', [])
        matched_count = sum(1 for match in odoo_products if match.get('odoo_product') is not None)

        section = "📊 **SUMMARY**\n"
        section += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        section += f"  Intent: {intent_type.replace('_', ' ').title()} ({confidence:.0%})\n"

        # Company status
        if entities.get('company_name'):
            section += f"  Company Match: ✅\n"
        else:
            section += f"  Company Match: ❌\n"

        # Products status
        match_rate = (matched_count / product_count * 100) if product_count > 0 else 0
        if match_rate == 100:
            section += f"  Products: ✅ {matched_count}/{product_count} (100%)\n"
        elif match_rate >= 80:
            section += f"  Products: ⚠️ {matched_count}/{product_count} ({match_rate:.0f}%)\n"
        else:
            section += f"  Products: ❌ {matched_count}/{product_count} ({match_rate:.0f}%)\n"

        # Order creation status
        if order_created.get('created'):
            order_name = order_created.get('order_name', 'N/A')
            amount = order_created.get('amount_total', 0)
            section += f"  Order Created: ✅ {order_name} (€{amount:.2f})\n"
        else:
            section += f"  Order Created: ⏸️ Pending confirmation\n"

        return section

    def _format_footer(self, order_id: str) -> str:
        """Format message footer with action instructions"""
        return f"""💬 **FEEDBACK**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reply with corrections in plain text, e.g.:
• "Company should be XYZ GmbH"
• "Product 2 should be code 9000842"
• "Quantity for product 1 is 100"
• "Everything looks good, approve"

Order ID: {order_id}"""

    def format_confirmation_message(self, order_id: str, correction_summary: Dict) -> str:
        """
        Format confirmation message after parsing user feedback (supports MULTIPLE corrections)

        Args:
            order_id: Order identifier
            correction_summary: Parsed corrections from Mistral with corrections_list

        Returns:
            Confirmation message
        """
        corrections_list = correction_summary.get('corrections_list', [])
        overall_confidence = correction_summary.get('overall_confidence', 0)
        total_corrections = len(corrections_list)

        if total_corrections == 0:
            return f"❓ I didn't understand any corrections in your message. Could you please rephrase?"

        # Header
        message = f"✅ **UNDERSTOOD {total_corrections} CORRECTION(S)** (Order #{order_id})\n\n"

        # Format each correction
        for idx, correction in enumerate(corrections_list, 1):
            correction_type = correction.get('correction_type', 'unknown')
            corrections_data = correction.get('corrections', {})
            confidence = correction.get('confidence', 0)

            if correction_type == 'company_match':
                correct_name = corrections_data.get('correct_company_name', 'Unknown')
                message += f"📝 **[{idx}] Company Correction:**\n"
                message += f"  New company: {correct_name}\n"
                message += f"  Confidence: {confidence:.0%}\n\n"

            elif correction_type == 'product_match':
                product_idx = corrections_data.get('product_index', 0)
                correct_code = corrections_data.get('correct_product_code')
                correct_name = corrections_data.get('correct_product_name')

                message += f"📝 **[{idx}] Product #{product_idx} Correction:**\n"
                if correct_name:
                    message += f"  Name: {correct_name}\n"
                if correct_code:
                    message += f"  Code: {correct_code}\n"
                message += f"  Confidence: {confidence:.0%}\n\n"

            elif correction_type == 'quantity':
                product_idx = corrections_data.get('product_index', 0)
                new_qty = corrections_data.get('correct_quantity', 0)
                message += f"📝 **[{idx}] Quantity Correction:**\n"
                message += f"  Product #{product_idx}: {new_qty} units\n"
                message += f"  Confidence: {confidence:.0%}\n\n"

            elif correction_type == 'price':
                product_idx = corrections_data.get('product_index', 0)
                new_price = corrections_data.get('correct_price', 0)
                message += f"📝 **[{idx}] Price Correction:**\n"
                message += f"  Product #{product_idx}: €{new_price:.2f}\n"
                message += f"  Confidence: {confidence:.0%}\n\n"

            elif correction_type == 'confirm':
                message += f"✅ **[{idx}] Confirmation:**\n"
                message += f"  All matches confirmed!\n"
                message += f"  Order approved for creation.\n\n"

            elif correction_type == 'reject':
                reason = corrections_data.get('reason', 'User rejected')
                message += f"❌ **[{idx}] Rejection:**\n"
                message += f"  Reason: {reason}\n\n"

        message += f"📊 Overall Confidence: {overall_confidence:.0%}\n"
        message += f"💾 All {total_corrections} correction(s) will improve future processing."

        return message

    def format_clarification_message(self, order_id: str, question: str) -> str:
        """
        Format clarification request message

        Args:
            order_id: Order identifier
            question: Clarification question from Mistral

        Returns:
            Clarification message
        """
        return f"""❓ **NEED CLARIFICATION** (Order #{order_id})

{question}

Please provide more details so I can help you correctly."""

    def format_error_message(self, order_id: str, error: str) -> str:
        """
        Format error message

        Args:
            order_id: Order identifier
            error: Error description

        Returns:
            Error message
        """
        return f"""❌ **ERROR** (Order #{order_id})

{error}

Please try again or contact support."""

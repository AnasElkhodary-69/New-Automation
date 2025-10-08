"""
Bulk Attachment Processing Test

Tests the complete RAG workflow on PDF attachments:
1. Parse PDF (OCR if needed)
2. Classify intent
3. Extract entities
4. Match customer in Odoo
5. Match products in Odoo
6. Track tokens, costs, and performance

Uses actual app workflow - no shortcuts!
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from email_module.email_reader import EmailReader
from retriever_module.odoo_connector import OdooConnector
from retriever_module.vector_store import VectorStore
from orchestrator.processor import EmailProcessor
from orchestrator.mistral_agent import MistralAgent
from dotenv import load_dotenv

load_dotenv()


class BulkAttachmentTester:
    """Test harness for bulk PDF processing"""

    def __init__(self, attachments_dir: str = "attachments"):
        """
        Initialize tester

        Args:
            attachments_dir: Directory containing PDF attachments
        """
        self.attachments_dir = Path(attachments_dir)
        self.results = []

        # Initialize components (using actual app workflow)
        print("=" * 100)
        print("BULK ATTACHMENT PROCESSING TEST")
        print("=" * 100)
        print("\n[1/4] Initializing system components...\n")

        self.email_reader = EmailReader()
        self.odoo = OdooConnector()
        self.vector_store = VectorStore()
        self.ai_agent = MistralAgent()
        self.processor = EmailProcessor(self.odoo, self.vector_store, self.ai_agent)

        print("   [OK] All components initialized")
        print(f"   [OK] DSPy enabled: {self.processor.USE_DSPY}")

    def process_attachments(self, limit: int = 50):
        """
        Process PDF attachments using app workflow

        Args:
            limit: Maximum number of PDFs to process
        """
        # Get PDF files
        pdf_files = list(self.attachments_dir.glob("*.pdf"))[:limit]

        if not pdf_files:
            print(f"\n[ERROR] No PDF files found in {self.attachments_dir}")
            return

        print(f"\n[2/4] Found {len(pdf_files)} PDF files to process (limit: {limit})\n")

        # Process each PDF
        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"\n{'='*100}")
            print(f"PROCESSING PDF {i}/{len(pdf_files)}: {pdf_path.name}")
            print(f"{'='*100}")

            result = self._process_single_pdf(pdf_path, i)
            self.results.append(result)

            # Print summary after each PDF
            self._print_pdf_summary(result)

    def _process_single_pdf(self, pdf_path: Path, index: int) -> Dict:
        """
        Process a single PDF using app workflow

        Args:
            pdf_path: Path to PDF file
            index: PDF index number

        Returns:
            Processing result dictionary
        """
        result = {
            'index': index,
            'filename': pdf_path.name,
            'pdf_path': str(pdf_path),
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'error': None
        }

        try:
            # STEP 1: Parse PDF (using email_reader OCR logic)
            print(f"\n[STEP 1] Parsing PDF...")
            parsed_text = self._parse_pdf(pdf_path)
            result['parsed_text'] = parsed_text
            result['text_length'] = len(parsed_text)
            result['ocr_used'] = len(parsed_text) > 0
            print(f"   [OK] Extracted {len(parsed_text)} characters")
            print(f"   [OK] OCR used: {result['ocr_used']}")

            # Create fake email for processing
            email = {
                'subject': f'Order from {pdf_path.stem}',
                'body': parsed_text,
                'from': 'test@example.com'
            }

            # STEP 2: Process through app workflow
            print(f"\n[STEP 2] Processing through RAG workflow...")
            workflow_result = self.processor.process_email(email)

            # Extract results
            result['intent'] = workflow_result.get('intent', {})
            result['entities'] = workflow_result.get('entities', {})
            result['context'] = workflow_result.get('context', {})
            result['odoo_matches'] = workflow_result.get('odoo_matches', {})
            result['token_usage'] = workflow_result.get('token_usage', {})

            # STEP 3: Extract customer info
            print(f"\n[STEP 3] Customer Matching...")
            result['customer'] = self._extract_customer_info(result)

            # STEP 4: Extract product info
            print(f"\n[STEP 4] Product Matching...")
            result['products'] = self._extract_product_info(result)

            # STEP 5: Calculate costs
            print(f"\n[STEP 5] Calculating costs...")
            result['cost_analysis'] = self._calculate_costs(result)

            result['success'] = True

        except Exception as e:
            result['error'] = str(e)
            print(f"\n[ERROR] Processing failed: {e}")
            import traceback
            traceback.print_exc()

        return result

    def _parse_pdf(self, pdf_path: Path) -> str:
        """
        Parse PDF using email_reader OCR logic

        Args:
            pdf_path: Path to PDF

        Returns:
            Extracted text
        """
        try:
            import pdfplumber

            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            return text.strip()
        except Exception as e:
            print(f"   [WARNING] PDF parsing failed: {e}")
            return ""

    def _extract_customer_info(self, result: Dict) -> Dict:
        """Extract customer matching info"""
        customer = {
            'extracted_name': result['entities'].get('company_name', 'N/A'),
            'extracted_contact': result['entities'].get('customer_name', 'N/A'),
            'extracted_email': result['entities'].get('email', 'N/A'),
            'json_match': None,
            'json_match_score': 0,
            'odoo_match': None,
            'odoo_ref': None,
            'odoo_id': None
        }

        # JSON match
        json_customer = result['context'].get('customer_info')
        if json_customer:
            customer['json_match'] = json_customer.get('name', 'N/A')
            customer['json_match_score'] = json_customer.get('match_score', 0)
            print(f"   [JSON] Matched: {customer['json_match']} (score: {customer['json_match_score']:.0%})")

        # Odoo match
        odoo_customer = result['odoo_matches'].get('customer')
        if odoo_customer and odoo_customer.get('found'):
            customer['odoo_match'] = odoo_customer.get('name', 'N/A')
            customer['odoo_ref'] = odoo_customer.get('ref', 'N/A')
            customer['odoo_id'] = odoo_customer.get('id', 'N/A')
            print(f"   [ODOO] Matched: {customer['odoo_match']}")
            print(f"   [ODOO] Ref: {customer['odoo_ref']}, ID: {customer['odoo_id']}")
        else:
            print(f"   [WARNING] No Odoo match found")

        return customer

    def _extract_product_info(self, result: Dict) -> List[Dict]:
        """Extract product matching info"""
        products = []

        # Get extracted products
        product_names = result['entities'].get('product_names', [])
        product_codes = result['entities'].get('product_codes', [])
        quantities = result['entities'].get('quantities', [])
        prices = result['entities'].get('prices', [])

        # Get Odoo matches
        odoo_products = result['odoo_matches'].get('products', [])

        for i in range(len(product_names)):
            product = {
                'index': i + 1,
                'extracted_name': product_names[i] if i < len(product_names) else 'N/A',
                'extracted_code': product_codes[i] if i < len(product_codes) else 'N/A',
                'quantity': quantities[i] if i < len(quantities) else 0,
                'price': prices[i] if i < len(prices) else 0.0,
                'json_match': None,
                'json_match_score': 0,
                'odoo_match': None,
                'odoo_id': None,
                'odoo_code': None
            }

            # Get JSON match
            json_products = result['context'].get('json_data', {}).get('products', [])
            if i < len(json_products):
                product['json_match'] = json_products[i].get('name', 'N/A')
                product['json_match_score'] = json_products[i].get('match_score', 0)

            # Get Odoo match
            if i < len(odoo_products):
                odoo_prod = odoo_products[i]
                if odoo_prod.get('found'):
                    product['odoo_match'] = odoo_prod.get('name', 'N/A')
                    product['odoo_id'] = odoo_prod.get('id', 'N/A')
                    product['odoo_code'] = odoo_prod.get('code', 'N/A')

            products.append(product)

            # Print product summary
            status = "[MATCHED]" if product['odoo_id'] else "[NO MATCH]"
            print(f"   {status} Product {i+1}: {product['extracted_name'][:50]}")
            if product['odoo_id']:
                print(f"           Odoo: {product['odoo_match'][:50]} (ID: {product['odoo_id']})")

        return products

    def _calculate_costs(self, result: Dict) -> Dict:
        """Calculate token usage and costs"""
        token_usage = result.get('token_usage', {})

        input_tokens = token_usage.get('input_tokens', 0)
        output_tokens = token_usage.get('output_tokens', 0)
        total_tokens = token_usage.get('total_tokens', 0)

        # Determine model used
        model_used = "mistral-small-latest" if self.processor.USE_DSPY else "mistral-large-latest"

        # Pricing (per 1K tokens)
        pricing = {
            'mistral-small-latest': {'input': 0.001, 'output': 0.001},
            'mistral-large-latest': {'input': 0.004, 'output': 0.004}
        }

        rates = pricing.get(model_used, {'input': 0, 'output': 0})

        input_cost = (input_tokens / 1000) * rates['input']
        output_cost = (output_tokens / 1000) * rates['output']
        total_cost = input_cost + output_cost

        cost_analysis = {
            'model_used': model_used,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'input_cost_usd': round(input_cost, 6),
            'output_cost_usd': round(output_cost, 6),
            'total_cost_usd': round(total_cost, 6)
        }

        print(f"   Model: {model_used}")
        print(f"   Tokens: {total_tokens:,} ({input_tokens:,} in + {output_tokens:,} out)")
        print(f"   Cost: ${total_cost:.6f}")

        return cost_analysis

    def _print_pdf_summary(self, result: Dict):
        """Print summary for processed PDF"""
        print(f"\n{'-'*100}")
        print(f"SUMMARY: {result['filename']}")
        print(f"{'-'*100}")

        if not result['success']:
            print(f"[ERROR] {result['error']}")
            return

        # Intent
        intent = result['intent']
        print(f"\n[INTENT]")
        print(f"  Type: {intent.get('type', 'N/A')} ({intent.get('confidence', 0):.0%} confidence)")

        # Customer
        customer = result['customer']
        print(f"\n[CUSTOMER]")
        print(f"  Extracted: {customer['extracted_name']}")
        print(f"  Odoo Match: {customer['odoo_match'] or 'NOT FOUND'}")
        if customer['odoo_ref']:
            print(f"  Odoo Ref: {customer['odoo_ref']} (ID: {customer['odoo_id']})")

        # Products
        print(f"\n[PRODUCTS]")
        print(f"  Total: {len(result['products'])}")
        matched = sum(1 for p in result['products'] if p['odoo_id'])
        if len(result['products']) > 0:
            print(f"  Matched in Odoo: {matched}/{len(result['products'])} ({matched/len(result['products'])*100:.0f}%)")
        else:
            print(f"  Matched in Odoo: 0/0 (N/A - no products extracted)")

        # Cost
        cost = result['cost_analysis']
        print(f"\n[COST]")
        print(f"  Model: {cost['model_used']}")
        print(f"  Tokens: {cost['total_tokens']:,}")
        print(f"  Cost: ${cost['total_cost_usd']:.6f}")

    def generate_report(self, output_dir: str = "test_results"):
        """
        Generate comprehensive test report

        Args:
            output_dir: Directory to save reports
        """
        print(f"\n{'='*100}")
        print(f"[3/4] Generating Reports...")
        print(f"{'='*100}\n")

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. JSON Report (detailed)
        json_path = output_path / f"bulk_test_results_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"   [OK] JSON report saved: {json_path}")

        # 2. CSV Report (summary)
        csv_path = output_path / f"bulk_test_summary_{timestamp}.csv"
        summary_data = []

        for result in self.results:
            if result['success']:
                summary_data.append({
                    'Index': result['index'],
                    'Filename': result['filename'],
                    'Text_Length': result.get('text_length', 0),
                    'OCR_Used': result.get('ocr_used', False),
                    'Intent': result['intent'].get('type', 'N/A'),
                    'Confidence': f"{result['intent'].get('confidence', 0):.0%}",
                    'Customer_Extracted': result['customer']['extracted_name'],
                    'Customer_Odoo_Match': result['customer']['odoo_match'] or 'NOT FOUND',
                    'Customer_Odoo_Ref': result['customer']['odoo_ref'] or 'N/A',
                    'Customer_Odoo_ID': result['customer']['odoo_id'] or 'N/A',
                    'Products_Count': len(result['products']),
                    'Products_Matched': sum(1 for p in result['products'] if p['odoo_id']),
                    'Match_Rate': f"{sum(1 for p in result['products'] if p['odoo_id'])/len(result['products'])*100:.0f}%" if result['products'] else 'N/A',
                    'Model_Used': result['cost_analysis']['model_used'],
                    'Total_Tokens': result['cost_analysis']['total_tokens'],
                    'Cost_USD': f"${result['cost_analysis']['total_cost_usd']:.6f}",
                    'Success': result['success']
                })

        df = pd.DataFrame(summary_data)
        df.to_csv(csv_path, index=False, encoding='utf-8')
        print(f"   [OK] CSV summary saved: {csv_path}")

        # 3. Product Details CSV
        products_csv = output_path / f"bulk_test_products_{timestamp}.csv"
        product_data = []

        for result in self.results:
            if result['success']:
                for product in result['products']:
                    product_data.append({
                        'PDF_Index': result['index'],
                        'PDF_Filename': result['filename'],
                        'Product_Index': product['index'],
                        'Extracted_Name': product['extracted_name'],
                        'Extracted_Code': product['extracted_code'],
                        'Quantity': product['quantity'],
                        'Price': product['price'],
                        'JSON_Match': product['json_match'] or 'NOT FOUND',
                        'JSON_Score': f"{product['json_match_score']:.0%}" if product['json_match_score'] else 'N/A',
                        'Odoo_Match': product['odoo_match'] or 'NOT FOUND',
                        'Odoo_ID': product['odoo_id'] or 'N/A',
                        'Odoo_Code': product['odoo_code'] or 'N/A'
                    })

        df_products = pd.DataFrame(product_data)
        df_products.to_csv(products_csv, index=False, encoding='utf-8')
        print(f"   [OK] Product details saved: {products_csv}")

        # 4. Statistics Summary
        self._print_statistics()

        return json_path, csv_path, products_csv

    def _print_statistics(self):
        """Print overall statistics"""
        print(f"\n{'='*100}")
        print(f"[4/4] OVERALL STATISTICS")
        print(f"{'='*100}\n")

        successful = [r for r in self.results if r['success']]
        failed = [r for r in self.results if not r['success']]

        print(f"[PROCESSING]")
        print(f"  Total PDFs: {len(self.results)}")
        print(f"  Successful: {len(successful)} ({len(successful)/len(self.results)*100:.0f}%)")
        print(f"  Failed: {len(failed)} ({len(failed)/len(self.results)*100:.0f}%)")

        if successful:
            # Customer matching
            odoo_customer_found = sum(1 for r in successful if r['customer']['odoo_id'])
            print(f"\n[CUSTOMER MATCHING]")
            print(f"  Odoo Matches: {odoo_customer_found}/{len(successful)} ({odoo_customer_found/len(successful)*100:.0f}%)")

            # Product matching
            total_products = sum(len(r['products']) for r in successful)
            matched_products = sum(sum(1 for p in r['products'] if p['odoo_id']) for r in successful)
            print(f"\n[PRODUCT MATCHING]")
            print(f"  Total Products: {total_products}")
            print(f"  Matched in Odoo: {matched_products}/{total_products} ({matched_products/total_products*100:.0f}%)")

            # Cost analysis
            total_tokens = sum(r['cost_analysis']['total_tokens'] for r in successful)
            total_cost = sum(r['cost_analysis']['total_cost_usd'] for r in successful)
            avg_tokens = total_tokens / len(successful)
            avg_cost = total_cost / len(successful)

            print(f"\n[COST ANALYSIS]")
            print(f"  Total Tokens: {total_tokens:,}")
            print(f"  Total Cost: ${total_cost:.6f}")
            print(f"  Avg Tokens/PDF: {avg_tokens:,.0f}")
            print(f"  Avg Cost/PDF: ${avg_cost:.6f}")

            # Model usage
            models_used = {}
            for r in successful:
                model = r['cost_analysis']['model_used']
                models_used[model] = models_used.get(model, 0) + 1

            print(f"\n[MODEL USAGE]")
            for model, count in models_used.items():
                print(f"  {model}: {count} PDFs ({count/len(successful)*100:.0f}%)")

            # OCR usage
            ocr_used = sum(1 for r in successful if r.get('ocr_used'))
            print(f"\n[OCR USAGE]")
            print(f"  PDFs with OCR: {ocr_used}/{len(successful)} ({ocr_used/len(successful)*100:.0f}%)")


def main():
    """Main test execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Bulk PDF attachment testing')
    parser.add_argument('--dir', default='attachments', help='Attachments directory')
    parser.add_argument('--limit', type=int, default=50, help='Max PDFs to process')
    parser.add_argument('--output', default='test_results', help='Output directory')

    args = parser.parse_args()

    # Run test
    tester = BulkAttachmentTester(args.dir)
    tester.process_attachments(limit=args.limit)

    # Generate reports
    json_path, csv_path, products_csv = tester.generate_report(args.output)

    print(f"\n{'='*100}")
    print(f"TEST COMPLETE!")
    print(f"{'='*100}")
    print(f"\nReports saved to:")
    print(f"  - {json_path}")
    print(f"  - {csv_path}")
    print(f"  - {products_csv}")
    print(f"\n{'='*100}\n")


if __name__ == "__main__":
    main()

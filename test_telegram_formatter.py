"""
Test Telegram Message Formatter with new odoo_matches structure
"""

from utils.telegram_message_formatter import TelegramMessageFormatter

# Create formatter
formatter = TelegramMessageFormatter()

# Mock email data
email = {
    'from': 'test@example.com',
    'subject': 'Test Order',
    'body': 'Test body'
}

# Mock result with new structure
result = {
    'intent': {
        'type': 'order_inquiry',
        'confidence': 0.95
    },
    'entities': {
        'company_name': 'Stenqvist Austria GmbH',
        'customer_name': 'Gerhard Kleinferchner',
        'product_names': [
            '3M Cushion Mount Plus E1520 457mm x 23m',
            '3M 9353R Splicetape 50mm x 33m Sample',
            'Doctor Blade Stainless Steel Gold 35x0.20 RPE Length 1335mm',
            'Longlife2 Doctor Blade 35x0.20x125x1.7mm'
        ],
        'quantities': [24, 1, 5, 10],
        'prices': [156.9, 0.0, 0.0, 0.0]
    },
    'context': {
        'customer_info': {
            'name': 'Stenqvist Austria GmbH',
            'match_score': 1.0,
            'ref': '1337'
        },
        'json_data': {
            'products': [
                {
                    'id': 8651,
                    'name': '3M Cushion Mount Plus E1520 457mm x 23m',
                    'default_code': 'E1520-457-23',
                    'standard_price': 0.0,
                    'extracted_product_name': '3M Cushion Mount Plus E1520 457mm x 23m'
                },
                {
                    'id': 8647,
                    'name': '3M 9353R Splicetape 50mm x 33m',
                    'default_code': '9353R',
                    'standard_price': 0.0,
                    'extracted_product_name': '3M 9353R Splicetape 50mm x 33m Sample'
                },
                {
                    'id': 9630,
                    'name': 'Doctor Blade Gold 35x0,20 mm / RPE / L1335 mm',
                    'default_code': 'G-35-20-RPE-L1335',
                    'standard_price': 3.72,
                    'extracted_product_name': 'Doctor Blade Stainless Steel Gold 35x0.20 RPE Length 1335mm'
                },
                {
                    'id': 9523,
                    'name': 'Doctor Blade Carbon 35x0,20x125x1,7 mm',
                    'default_code': 'C-35-20-125-17',
                    'standard_price': 0.75,
                    'extracted_product_name': 'Longlife2 Doctor Blade 35x0.20x125x1.7mm'
                }
            ]
        }
    },
    'odoo_matches': {
        'customer': {
            'found': True,
            'id': 3153,
            'name': 'Stenqvist Austria GmbH',
            'ref': '1337'
        },
        'products': [
            {
                'json_product': {
                    'id': 8651,
                    'name': '3M Cushion Mount Plus E1520 457mm x 23m',
                    'default_code': 'E1520-457-23',
                    'standard_price': 0.0
                },
                'odoo_product': {
                    'id': 8651,
                    'name': '3M Cushion Mount Plus E1520 457mm x 23m',
                    'default_code': 'E1520-457-23',
                    'standard_price': 0.0,
                    'list_price': 1.0
                },
                'match_method': 'json_id_verified',
                'extracted_name': '3M Cushion Mount Plus E1520 457mm x 23m'
            },
            {
                'json_product': {
                    'id': 8647,
                    'name': '3M 9353R Splicetape 50mm x 33m',
                    'default_code': '9353R',
                    'standard_price': 0.0
                },
                'odoo_product': {
                    'id': 8647,
                    'name': '3M 9353R Splicetape 50mm x 33m',
                    'default_code': '9353R',
                    'standard_price': 0.0,
                    'list_price': 1.0
                },
                'match_method': 'json_id_verified',
                'extracted_name': '3M 9353R Splicetape 50mm x 33m Sample'
            },
            {
                'json_product': {
                    'id': 9630,
                    'name': 'Doctor Blade Gold 35x0,20 mm / RPE / L1335 mm',
                    'default_code': 'G-35-20-RPE-L1335',
                    'standard_price': 3.72
                },
                'odoo_product': {
                    'id': 9630,
                    'name': 'Doctor Blade Gold 35x0,20 mm / RPE / L1335 mm',
                    'default_code': 'G-35-20-RPE-L1335',
                    'standard_price': 3.72,
                    'list_price': 0.0
                },
                'match_method': 'json_id_verified',
                'extracted_name': 'Doctor Blade Stainless Steel Gold 35x0.20 RPE Length 1335mm'
            },
            {
                'json_product': {
                    'id': 9523,
                    'name': 'Doctor Blade Carbon 35x0,20x125x1,7 mm',
                    'default_code': 'C-35-20-125-17',
                    'standard_price': 0.75
                },
                'odoo_product': {
                    'id': 9523,
                    'name': 'Doctor Blade Carbon 35x0,20x125x1,7 mm',
                    'default_code': 'C-35-20-125-17',
                    'standard_price': 0.75,
                    'list_price': 0.0
                },
                'match_method': 'json_id_verified',
                'extracted_name': 'Longlife2 Doctor Blade 35x0.20x125x1.7mm'
            }
        ],
        'match_summary': {
            'customer_matched': True,
            'products_matched': 4,
            'products_total': 4
        }
    },
    'order_created': {
        'created': False,
        'message': 'Order creation disabled'
    }
}

# Format message
order_id = "TEST_ORDER_001"
message = formatter.format_order_notification(email, result, order_id)

print("=" * 60)
print("TELEGRAM MESSAGE OUTPUT:")
print("=" * 60)
print(message)
print("=" * 60)

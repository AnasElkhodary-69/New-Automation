"""
Send a test order email to the system inbox for testing Phase 1+2 integration
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

load_dotenv()

# Email config
FROM_EMAIL = "info@moaz.ca"
TO_EMAIL = os.getenv("EMAIL_ADDRESS")  # System inbox
PASSWORD = "kxrh cpki qlsf ylsw"  # App password for info@moaz.ca

# Test order email with products from Phase 1/2 tests
email_body = """
Dear SDS Print Team,

We would like to place an order for the following products:

1. 3M Klischee-Klebeband Cushion Mount L1520, 685 x 0,55 mm, Rolle à 33m
   Quantity: 2 pieces
   Price: EUR 245.00 per piece

2. 3M Klischee-Klebeband Cushion Mount L1320, 685 x 0,55 mm, Rolle à 33m
   Quantity: 3 pieces
   Price: EUR 198.50 per piece

3. SDS025 - 177H DuroSeal Bobst 16S Grey
   Article Code: 8060104 (our internal code)
   Quantity: 5 pieces
   Price: EUR 312.00 per piece

Please confirm the order and provide delivery timeline.

Best regards,
Maria Schmidt
Purchasing Manager

Dürrbeck Druck GmbH
Hauptstraße 45
82319 Starnberg, Germany
Tel: +49 8151 9999-0
Email: m.schmidt@duerrbeck-druck.de
"""

# Create email
msg = MIMEMultipart()
msg['From'] = FROM_EMAIL
msg['To'] = TO_EMAIL
msg['Subject'] = "Test Order - Phase 1+2 Integration Test"

msg.attach(MIMEText(email_body, 'plain'))

# Send email
try:
    print(f"Sending test email to {TO_EMAIL}...")
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(FROM_EMAIL, PASSWORD)
    server.send_message(msg)
    server.quit()
    print("✓ Test email sent successfully!")
    print("\nEmail contains:")
    print("- 3 products (L1520, L1320, SDS025)")
    print("- Product codes, quantities, prices")
    print("- Customer info (Dürrbeck Druck GmbH)")
    print("\nThis will test:")
    print("1. Multi-pass code extraction (L1520, L1320 from names)")
    print("2. Customer code deprioritization (8060104 -> SDS025)")
    print("3. Attribute extraction (brand, width, thickness, machine type)")
    print("4. Smart matching with duplicate prevention")
    print("\nNow run: python main.py")
except Exception as e:
    print(f"✗ Error sending email: {e}")

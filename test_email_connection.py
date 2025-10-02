"""
Test email connection (IMAP/SMTP)
"""

import imaplib
import smtplib

# Email credentials
EMAIL_ADDRESS = "moaz.radwan@ai2go.vip"
EMAIL_PASSWORD = "vsdr xsuy mdkk otbu"

# Gmail settings (assuming it's Gmail based on app password format)
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

print("Testing Email Connection...")
print(f"Email: {EMAIL_ADDRESS}")
print("=" * 60)

# Test IMAP (receiving emails)
print("\n1. Testing IMAP (reading emails)...")
try:
    imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    imap.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    imap.select('INBOX')

    # Get mailbox status
    status, messages = imap.search(None, 'ALL')
    email_count = len(messages[0].split()) if messages[0] else 0

    status, unseen = imap.search(None, 'UNSEEN')
    unread_count = len(unseen[0].split()) if unseen[0] else 0

    print(f"[OK] IMAP connection successful!")
    print(f"     Total emails in INBOX: {email_count}")
    print(f"     Unread emails: {unread_count}")

    imap.close()
    imap.logout()

except Exception as e:
    print(f"[FAIL] IMAP connection failed: {e}")

# Test SMTP (sending emails)
print("\n2. Testing SMTP (sending emails)...")
try:
    smtp = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    smtp.starttls()
    smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

    print(f"[OK] SMTP connection successful!")
    print(f"     Ready to send emails")

    smtp.quit()

except Exception as e:
    print(f"[FAIL] SMTP connection failed: {e}")

print("\n" + "=" * 60)
print("Email Configuration Summary:")
print("=" * 60)
print(f"EMAIL_ADDRESS={EMAIL_ADDRESS}")
print(f"EMAIL_PASSWORD={EMAIL_PASSWORD}")
print(f"IMAP_SERVER={IMAP_SERVER}")
print(f"IMAP_PORT={IMAP_PORT}")
print(f"SMTP_SERVER={SMTP_SERVER}")
print(f"SMTP_PORT={SMTP_PORT}")

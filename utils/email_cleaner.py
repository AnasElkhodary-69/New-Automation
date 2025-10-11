"""
Email Content Cleaner
Removes noise from emails while preserving order data
"""

import re
from typing import List, Tuple


# T&C detection keywords (case-insensitive)
TC_KEYWORDS = [
    # English
    'terms and conditions', 'terms & conditions', 'terms of service',
    'general terms', 'purchase terms', 'sales terms',
    # German
    'allgemeine geschäftsbedingungen', 'agb', 'geschäftsbedingungen',
    'verkaufsbedingungen', 'einkaufsbedingungen', 'lieferbedingungen'
]


def is_terms_and_conditions_file(filename: str) -> bool:
    """
    Detect if a file is likely a T&C document based on filename

    Args:
        filename: Name of the file (e.g., "terms_and_conditions.pdf")

    Returns:
        True if file appears to be T&C document
    """
    filename_lower = filename.lower()

    # Remove extension for checking
    name_without_ext = re.sub(r'\.(pdf|docx?|txt)$', '', filename_lower)

    # Check against keywords
    for keyword in TC_KEYWORDS:
        if keyword in name_without_ext:
            return True

    # Additional patterns (including common typos)
    patterns = [
        r'\b(agb|t[&+]c|gtc)\b',
        r'term[ns]',  # Catches "terms" or "termns" (typo)
        r'condition',
        r'bedingung',  # German
    ]

    for pattern in patterns:
        if re.search(pattern, name_without_ext):
            return True

    return False


def clean_email_content(text: str) -> str:
    """
    Remove noise from email content while preserving order data

    Removes:
    - Email threads and quoted text
    - Email signatures (after greeting) - BUT ONLY if no PDF content follows
    - Legal disclaimers
    - Excessive whitespace

    Preserves:
    - Product codes, names, quantities
    - Customer information
    - Tables and lists
    - Special instructions
    - PDF attachment content

    Args:
        text: Raw email content

    Returns:
        Cleaned email content
    """
    if not text or not text.strip():
        return text

    # Check if text contains PDF attachment content
    has_pdf_content = '=== ATTACHMENT:' in text and '.pdf ===' in text

    # 1. Remove email threads - everything after "Original Message"
    # BUT: Do NOT remove if PDF content appears after the thread marker
    thread_markers = [
        r'-----\s*Original Message\s*-----',
        r'-----\s*Ursprüngliche Nachricht\s*-----',
        r'________________________________',  # Outlook separator
        r'From:.*Sent:.*To:.*Subject:',  # Email header block
    ]

    for marker in thread_markers:
        match = re.search(marker, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            # Check if PDF marker appears AFTER this thread marker
            pdf_marker_pos = text.find('=== ATTACHMENT:')
            thread_marker_pos = match.start()

            # Only remove thread if NO PDF content comes after it
            if pdf_marker_pos == -1 or pdf_marker_pos < thread_marker_pos:
                text = text[:match.start()]
                break
            # Otherwise, keep the content (PDF is after this marker)

    # 2. Remove "On [date]... wrote:" patterns
    text = re.sub(r'On .{10,100} wrote:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Am .{10,100} schrieb:', '', text, flags=re.IGNORECASE)

    # 3. Remove quoted lines (lines starting with > or |)
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()
        # Keep line if it doesn't start with quote markers
        if not stripped.startswith(('>', '|', '»')):
            cleaned_lines.append(line)

    text = '\n'.join(cleaned_lines)

    # 4. Remove signatures - ONLY if there's no PDF content after
    # (PDF content often appears after email signatures)
    if not has_pdf_content:
        signature_markers = [
            r'Mit freundlichen Grüßen',
            r'Mit freundlichem Gruß',
            r'Best regards',
            r'Kind regards',
            r'Regards',
            r'Sincerely',
            r'Viele Grüße',
            r'Freundliche Grüße',
        ]

        # Find first signature marker and cut there
        earliest_pos = len(text)
        for marker in signature_markers:
            match = re.search(marker, text, flags=re.IGNORECASE)
            if match and match.start() < earliest_pos:
                earliest_pos = match.start()

        if earliest_pos < len(text):
            text = text[:earliest_pos]

    # 5. Remove legal disclaimers (common patterns)
    disclaimer_patterns = [
        r'This email is confidential.*?(?=\n\n|\Z)',
        r'Diese E-Mail enthält vertrauliche.*?(?=\n\n|\Z)',
        r'CONFIDENTIALITY NOTICE.*?(?=\n\n|\Z)',
        r'Der Inhalt dieser E-Mail.*?(?=\n\n|\Z)',
    ]

    for pattern in disclaimer_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)

    # 6. Clean up excessive whitespace
    # Multiple blank lines -> max 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove trailing/leading whitespace per line
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()


def filter_terms_and_conditions_content(text: str, max_length: int = 500) -> str:
    """
    Heavily truncate T&C content to avoid wasting tokens
    Extract only key business terms

    Args:
        text: T&C document text
        max_length: Maximum characters to keep

    Returns:
        Truncated summary of key terms
    """
    if not text or not text.strip():
        return ""

    # Look for key business terms
    key_patterns = [
        r'payment.*?(?:net\s*\d+|prepayment|advance)',
        r'delivery.*?(?:\d+\s*(?:days|weeks|months))',
        r'warranty.*?(?:\d+\s*(?:months|years))',
        r'return.*?(?:\d+\s*days)',
    ]

    extracted = []
    text_lower = text.lower()

    for pattern in key_patterns:
        matches = re.findall(pattern, text_lower, flags=re.IGNORECASE)
        if matches:
            extracted.extend(matches[:2])  # Max 2 matches per pattern

    if extracted:
        summary = "[T&C Summary] " + "; ".join(extracted[:5])
        return summary[:max_length]

    # If no key terms found, just return truncated first part
    return f"[T&C Document - Truncated] {text[:max_length]}..."


def clean_email_data(email_data: dict) -> dict:
    """
    Clean email data structure, handling body and attachments

    Args:
        email_data: Dictionary with 'body' and 'attachments' keys

    Returns:
        Cleaned email data (modifies in place and returns)
    """
    # Clean main email body
    if 'body' in email_data and email_data['body']:
        email_data['body'] = clean_email_content(email_data['body'])

    # Handle attachments - filter T&C documents
    if 'attachments' in email_data:
        for attachment in email_data['attachments']:
            filename = attachment.get('filename', '')

            # Check if this is a T&C document
            if is_terms_and_conditions_file(filename):
                # Mark as T&C and truncate content
                attachment['is_terms_and_conditions'] = True

                if 'content' in attachment and attachment['content']:
                    attachment['content'] = filter_terms_and_conditions_content(
                        attachment['content'],
                        max_length=500
                    )
            else:
                attachment['is_terms_and_conditions'] = False

    return email_data

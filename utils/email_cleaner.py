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

    STRATEGY:
    - For PDFs < 10k chars: Preserve everything (likely order/invoice data)
    - For PDFs >= 10k chars: Extract business terms, truncate legal boilerplate
    - Never remove PDF content after email signatures

    Removes:
    - Email threads and quoted text (only if NO PDF follows)
    - Email signatures (only if NO PDF follows)
    - Legal disclaimers
    - Excessive whitespace

    Preserves:
    - Product codes, names, quantities, prices
    - Customer information
    - Tables and lists
    - Special instructions
    - PDF attachment content (ALL of it if < 10k, business terms if >= 10k)

    Args:
        text: Raw email content

    Returns:
        Cleaned email content
    """
    if not text or not text.strip():
        return text

    # Check if text contains PDF attachment content
    has_pdf_content = '=== ATTACHMENT:' in text and '.pdf ===' in text.lower()

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


def extract_business_terms_from_tc(text: str, max_length: int = 3000) -> str:
    """
    Extract key business terms from T&C documents while truncating legal boilerplate

    Extracts:
    - Payment terms (net days, prepayment, discounts)
    - Delivery terms (timeframes, conditions, Incoterms)
    - Warranty periods
    - Return policies
    - Liability limits
    - Price adjustment clauses

    Args:
        text: T&C document text
        max_length: Maximum characters to keep (default: 3000)

    Returns:
        Extracted business terms summary
    """
    if not text or not text.strip():
        return ""

    # Section headers to look for (multi-language: German, English)
    important_sections = [
        # Payment
        r'(?:payment|zahlung|payment\s+terms|zahlungsbedingungen).*?(?=\n\d+\.|$)',
        r'(?:prices?|preise?).*?(?=\n\d+\.|$)',

        # Delivery
        r'(?:delivery|lieferung|lieferbedingungen|delivery\s+terms).*?(?=\n\d+\.|$)',
        r'(?:shipping|versand).*?(?=\n\d+\.|$)',

        # Warranty
        r'(?:warranty|gewährleistung|garantie).*?(?=\n\d+\.|$)',

        # Returns
        r'(?:return|rückgabe|widerruf).*?(?=\n\d+\.|$)',

        # Liability
        r'(?:liability|haftung).*?(?=\n\d+\.|$)',

        # Tolerances/Deviations (important for manufacturing)
        r'(?:tolerance|abweichung|deviation).*?(?=\n\d+\.|$)',
    ]

    # Key specific terms to extract
    key_term_patterns = [
        # Payment terms
        r'(?:payment|zahlung).*?(?:net\s*\d+|netto\s*\d+|\d+\s*(?:days|tage))',
        r'(?:discount|skonto|rabatt).*?\d+%',
        r'prepayment|vorkasse|advance\s+payment',

        # Delivery terms
        r'(?:delivery|lieferung).*?\d+\s*(?:days|weeks|months|tage|wochen|monate)',
        r'(?:EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|FOB|CFR|CIF)',  # Incoterms

        # Warranty
        r'(?:warranty|gewährleistung).*?\d+\s*(?:months?|years?|monate|jahre)',

        # Tolerances (critical for manufacturing orders)
        r'tolerance.*?\+/?-?\s*\d+%',
        r'deviation.*?\+/?-?\s*\d+%',
        r'\+/?-\s*\d+%',  # ±10%, etc.

        # Price adjustments
        r'price\s+adjust.*?\d+%',
        r'preisanpassung.*?\d+%',
    ]

    extracted_sections = []
    text_lower = text.lower()

    # Extract important sections
    for pattern in important_sections:
        matches = re.findall(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if matches:
            for match in matches[:2]:  # Max 2 matches per section
                # Truncate very long matches
                match_text = match[:500] if len(match) > 500 else match
                extracted_sections.append(match_text.strip())

    # Extract specific key terms
    key_terms = []
    for pattern in key_term_patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches:
            key_terms.extend(matches[:3])  # Max 3 matches per pattern

    # Build summary
    summary_parts = []

    if key_terms:
        summary_parts.append("[KEY TERMS]\n" + "\n- ".join(key_terms[:10]))

    if extracted_sections:
        summary_parts.append("\n\n[RELEVANT SECTIONS]\n" + "\n\n".join(extracted_sections[:5]))

    if summary_parts:
        summary = "\n".join(summary_parts)
        # Truncate to max_length
        if len(summary) > max_length:
            summary = summary[:max_length] + "...[truncated]"
        return f"[T&C Business Terms Extracted]\n{summary}"

    # Fallback: return truncated beginning
    return f"[T&C Document]\n{text[:max_length]}...[truncated]"


def filter_terms_and_conditions_content(text: str, max_length: int = 500) -> str:
    """
    DEPRECATED: Use extract_business_terms_from_tc() instead

    Heavily truncate T&C content to avoid wasting tokens
    Extract only key business terms

    Args:
        text: T&C document text
        max_length: Maximum characters to keep

    Returns:
        Truncated summary of key terms
    """
    # Redirect to new function with better extraction
    return extract_business_terms_from_tc(text, max_length=max_length)


def clean_email_data(email_data: dict) -> dict:
    """
    Clean email data structure with intelligent PDF handling

    STRATEGY:
    1. PDFs < 10k chars: Keep 100% (likely order/invoice data)
    2. PDFs >= 10k chars (non-T&C): Keep 100% (may contain products)
    3. PDFs >= 10k chars (T&C): Extract business terms only (~3k chars)
    4. Never remove content after email signatures if PDF follows

    Args:
        email_data: Dictionary with 'body' and 'attachments' keys

    Returns:
        Cleaned email data (modifies in place and returns)
    """
    import logging
    logger = logging.getLogger(__name__)

    # Clean main email body (but preserve PDF content that comes after signatures)
    if 'body' in email_data and email_data['body']:
        email_data['body'] = clean_email_content(email_data['body'])

    # Handle attachments with intelligent size-based strategy
    if 'attachments' in email_data:
        for attachment in email_data['attachments']:
            filename = attachment.get('filename', '')
            content = attachment.get('content', '')
            content_length = len(content)

            # Check if this is a T&C document
            is_tc = is_terms_and_conditions_file(filename)
            attachment['is_terms_and_conditions'] = is_tc

            # STRATEGY: Size-based handling
            if content_length < 10000:
                # Small PDF (< 10k chars): Keep everything (likely order/invoice)
                logger.info(f"[EMAIL CLEANER] PDF '{filename}': {content_length} chars - PRESERVING ALL (small PDF)")
                # No modification needed
                pass

            elif content_length >= 10000 and not is_tc:
                # Large PDF (>= 10k chars) but NOT T&C: Keep everything (may contain products)
                logger.info(f"[EMAIL CLEANER] PDF '{filename}': {content_length} chars - PRESERVING ALL (non-T&C content)")
                # No modification needed
                pass

            elif content_length >= 10000 and is_tc:
                # Large T&C PDF (>= 10k chars): Extract business terms only
                logger.info(f"[EMAIL CLEANER] PDF '{filename}': {content_length} chars - EXTRACTING BUSINESS TERMS (T&C document)")

                if 'content' in attachment and attachment['content']:
                    original_length = len(attachment['content'])
                    attachment['content'] = extract_business_terms_from_tc(
                        attachment['content'],
                        max_length=3000  # Keep up to 3000 chars of business terms
                    )
                    new_length = len(attachment['content'])
                    logger.info(f"[EMAIL CLEANER]   Reduced from {original_length} to {new_length} chars ({(new_length/original_length)*100:.1f}%)")

    return email_data

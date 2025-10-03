"""
Email Reader Module

Handles connecting to email server via IMAP and fetching emails
Supports PDF text extraction and image OCR
"""

import logging
import imaplib
from typing import List, Dict, Optional
import json
from pathlib import Path
import io
import base64
import tempfile

# Import standard email library with absolute import to avoid conflict
import email.message
from email import message_from_bytes
from email.header import decode_header

# PDF and image processing
try:
    import pdfplumber
    from PIL import Image
    import pytesseract
    from pdf2image import convert_from_bytes
    PDF_SUPPORT = True

    # Configure Tesseract path for Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except ImportError:
    PDF_SUPPORT = False
    logging.warning("PDF/Image extraction libraries not installed. Install: pip install pdfplumber pytesseract pdf2image Pillow")

logger = logging.getLogger(__name__)


class EmailReader:
    """Class to handle reading emails from IMAP server"""

    def __init__(self, config_path: str = "config/email_config.json"):
        """
        Initialize Email Reader

        Args:
            config_path: Path to email configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.connection = None
        self._connect()

    def _load_config(self) -> Dict:
        """
        Load email configuration from JSON file and environment variables

        Returns:
            Configuration dictionary with IMAP settings
        """
        logger.info(f"Loading email configuration from {self.config_path}")

        # Load from config_loader which prioritizes .env
        try:
            from config.config_loader import ConfigLoader
            loader = ConfigLoader()
            return loader.load_email_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {
                "imap_server": "imap.gmail.com",
                "imap_port": 993,
                "email": "",
                "password": "",
                "use_ssl": True
            }

    def _connect(self):
        """
        Establish connection to IMAP server
        """
        logger.info("Connecting to IMAP server...")

        try:
            if self.config.get('use_ssl'):
                self.connection = imaplib.IMAP4_SSL(
                    self.config['imap_server'],
                    self.config['imap_port']
                )
            else:
                self.connection = imaplib.IMAP4(
                    self.config['imap_server'],
                    self.config['imap_port']
                )

            self.connection.login(
                self.config['email'],
                self.config['password']
            )
            logger.info("Successfully connected to IMAP server")
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {str(e)}")
            raise

    def fetch_unread_emails(self, mailbox: str = "INBOX") -> List[Dict]:
        """
        Fetch all unread emails from specified mailbox

        Args:
            mailbox: Mailbox to check (default: INBOX)

        Returns:
            List of email dictionaries with parsed content
        """
        logger.info(f"Fetching unread emails from {mailbox}")

        try:
            self.connection.select(mailbox)
            status, messages = self.connection.search(None, 'UNSEEN')

            if status != 'OK':
                logger.error("Failed to search for unread emails")
                return []

            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} unread email(s)")

            emails = []
            for email_id in email_ids:
                email_data = self._fetch_email_by_id(email_id)
                if email_data:
                    emails.append(email_data)

            return emails

        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            return []

    def _fetch_email_by_id(self, email_id: bytes) -> Optional[Dict]:
        """
        Fetch and parse a single email by ID

        Args:
            email_id: Email ID from IMAP server

        Returns:
            Parsed email dictionary or None if error
        """
        try:
            status, msg_data = self.connection.fetch(email_id, '(RFC822)')

            if status != 'OK':
                logger.error(f"Failed to fetch email {email_id}")
                return None

            raw_email = msg_data[0][1]
            msg = message_from_bytes(raw_email)

            # Extract body
            body_data = self._extract_body(msg)

            # Extract attachments with content (PDFs, images)
            attachments, attachment_text = self._extract_attachments_with_content(msg)

            # Combine email body with extracted attachment text
            full_body = body_data.get('text', '')
            if attachment_text:
                full_body += attachment_text

            # Parse email data
            email_dict = {
                'id': email_id.decode(),
                'message_id': msg.get('Message-ID', ''),
                'from': self._decode_header(msg.get('From', '')),
                'to': self._decode_header(msg.get('To', '')),
                'subject': self._decode_header(msg.get('Subject', '')),
                'date': msg.get('Date', ''),
                'body': full_body,  # Now includes PDF/image text
                'body_html': body_data.get('html', ''),
                'attachments': attachments
            }

            return email_dict

        except Exception as e:
            logger.error(f"Error parsing email {email_id}: {str(e)}")
            return None

    def _decode_header(self, header_value: str) -> str:
        """
        Decode email header value

        Args:
            header_value: Raw header value

        Returns:
            Decoded header string
        """
        if not header_value:
            return ""

        try:
            decoded_parts = decode_header(header_value)
            decoded_string = ""

            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    decoded_string += part

            return decoded_string
        except Exception as e:
            logger.warning(f"Error decoding header: {e}")
            return str(header_value)

    def _extract_body(self, msg: email.message.Message) -> Dict[str, str]:
        """
        Extract email body (text and HTML)

        Args:
            msg: Email message object

        Returns:
            Dictionary with 'text' and 'html' keys
        """
        body = {'text': '', 'html': ''}

        try:
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))

                    # Skip attachments
                    if "attachment" in content_disposition:
                        continue

                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            decoded_payload = payload.decode(charset, errors='ignore')

                            if content_type == "text/plain":
                                body['text'] += decoded_payload
                            elif content_type == "text/html":
                                body['html'] += decoded_payload
                    except Exception as e:
                        logger.warning(f"Error decoding part: {e}")
                        continue
            else:
                # Not multipart
                content_type = msg.get_content_type()
                payload = msg.get_payload(decode=True)

                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    decoded_payload = payload.decode(charset, errors='ignore')

                    if content_type == "text/plain":
                        body['text'] = decoded_payload
                    elif content_type == "text/html":
                        body['html'] = decoded_payload

        except Exception as e:
            logger.error(f"Error extracting body: {e}")

        return body

    def _extract_attachments(self, msg: email.message.Message) -> List[Dict]:
        """
        Extract attachment information from email

        Args:
            msg: Email message object

        Returns:
            List of attachment dictionaries
        """
        attachments = []

        try:
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_header(filename)

                        attachments.append({
                            'filename': filename,
                            'content_type': part.get_content_type(),
                            'size': len(part.get_payload(decode=True) or b'')
                        })
        except Exception as e:
            logger.error(f"Error extracting attachments: {e}")

        return attachments

    def mark_as_read(self, email_id: bytes):
        """
        Mark an email as read

        Args:
            email_id: Email ID to mark as read
        """
        try:
            if isinstance(email_id, str):
                email_id = email_id.encode()

            self.connection.store(email_id, '+FLAGS', '\\Seen')
            logger.info(f"Marked email {email_id} as read")
        except Exception as e:
            logger.error(f"Error marking email as read: {str(e)}")

    def mark_as_unread(self, email_id: bytes):
        """
        Mark an email as unread

        Args:
            email_id: Email ID to mark as unread
        """
        try:
            if isinstance(email_id, str):
                email_id = email_id.encode()

            self.connection.store(email_id, '-FLAGS', '\\Seen')
            logger.info(f"Marked email {email_id} as unread")
        except Exception as e:
            logger.error(f"Error marking email as unread: {str(e)}")

    def move_to_folder(self, email_id: bytes, folder: str):
        """
        Move email to specified folder

        Args:
            email_id: Email ID to move
            folder: Destination folder name
        """
        try:
            if isinstance(email_id, str):
                email_id = email_id.encode()

            # Copy to destination folder
            result = self.connection.copy(email_id, folder)
            if result[0] == 'OK':
                # Mark original as deleted
                self.connection.store(email_id, '+FLAGS', '\\Deleted')
                # Expunge to actually delete
                self.connection.expunge()
                logger.info(f"Moved email {email_id} to {folder}")
        except Exception as e:
            logger.error(f"Error moving email: {str(e)}")

    def _extract_text_from_pdf(self, pdf_bytes: bytes, filename: str) -> str:
        """
        Extract text from PDF file, including text from images within PDF

        Args:
            pdf_bytes: PDF file content as bytes
            filename: Name of the PDF file for logging

        Returns:
            Extracted text content
        """
        if not PDF_SUPPORT:
            logger.warning(f"PDF extraction not available for {filename}")
            return ""

        extracted_text = ""

        try:
            # Method 1: Extract text directly from PDF
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        extracted_text += f"\n--- Page {page_num} ---\n{text}\n"

            # Method 2: If no text found, try OCR on PDF pages
            if not extracted_text.strip():
                try:
                    # Specify poppler path for Windows
                    poppler_path = r"C:\Anas's PC\Moaz\New Automation\poppler-24.08.0\Library\bin"
                    images = convert_from_bytes(pdf_bytes, poppler_path=poppler_path)
                    for page_num, image in enumerate(images, 1):
                        try:
                            ocr_text = pytesseract.image_to_string(image)
                            if ocr_text:
                                extracted_text += f"\n--- Page {page_num} (OCR) ---\n{ocr_text}\n"
                        except pytesseract.TesseractNotFoundError:
                            logger.debug(f"Tesseract not installed, skipping OCR for {filename}")
                            break
                except Exception as ocr_error:
                    logger.debug(f"OCR failed for {filename}: {ocr_error}")

            if extracted_text.strip():
                logger.info(f"Extracted {len(extracted_text)} chars from PDF: {filename}")
            else:
                logger.warning(f"No text found in PDF: {filename}")

        except Exception as e:
            logger.error(f"PDF extraction error ({filename}): {str(e)}")

        return extracted_text

    def _extract_text_from_image(self, image_bytes: bytes, filename: str) -> str:
        """
        Extract text from image using OCR

        Args:
            image_bytes: Image file content as bytes
            filename: Name of the image file for logging

        Returns:
            Extracted text content
        """
        if not PDF_SUPPORT:
            logger.warning(f"Image OCR not available for {filename}")
            return ""

        extracted_text = ""

        try:
            image = Image.open(io.BytesIO(image_bytes))

            try:
                extracted_text = pytesseract.image_to_string(image)
            except pytesseract.TesseractNotFoundError:
                logger.warning(f"Tesseract not installed, skipping OCR for {filename}")
                return ""

            if extracted_text.strip():
                logger.info(f"Extracted {len(extracted_text)} chars from image: {filename}")
            else:
                logger.debug(f"No text found in {filename}")

        except Exception as e:
            logger.error(f"Image extraction error ({filename}): {str(e)}")

        return extracted_text

    def _extract_attachments_with_content(self, msg: email.message.Message) -> tuple[List[Dict], str]:
        """
        Extract attachment information AND text content from PDFs/images

        Args:
            msg: Email message object

        Returns:
            Tuple of (attachments list, combined extracted text)
        """
        attachments = []
        combined_text = ""

        try:
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_header(filename)
                        content_type = part.get_content_type()
                        payload = part.get_payload(decode=True)

                        if payload:
                            size = len(payload)

                            attachments.append({
                                'filename': filename,
                                'content_type': content_type,
                                'size': size
                            })

                            # Extract text from PDF
                            if content_type == 'application/pdf' or filename.lower().endswith('.pdf'):
                                pdf_text = self._extract_text_from_pdf(payload, filename)
                                if pdf_text:
                                    combined_text += f"\n\n=== ATTACHMENT: {filename} ===\n{pdf_text}\n"

                            # Extract text from images
                            elif content_type.startswith('image/') or filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
                                image_text = self._extract_text_from_image(payload, filename)
                                if image_text:
                                    combined_text += f"\n\n=== ATTACHMENT: {filename} ===\n{image_text}\n"

        except Exception as e:
            logger.error(f"Error extracting attachments with content: {e}")

        return attachments, combined_text

    def close(self):
        """Close IMAP connection"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                logger.info("IMAP connection closed")
            except Exception as e:
                logger.error(f"Error closing IMAP connection: {str(e)}")

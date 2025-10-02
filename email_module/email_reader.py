"""
Email Reader Module

Handles connecting to email server via IMAP and fetching emails
"""

import logging
import imaplib
from typing import List, Dict, Optional
import json
from pathlib import Path

# Import standard email library with absolute import to avoid conflict
import email.message
from email import message_from_bytes
from email.header import decode_header

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

            # Parse email data
            email_dict = {
                'id': email_id.decode(),
                'message_id': msg.get('Message-ID', ''),
                'from': self._decode_header(msg.get('From', '')),
                'to': self._decode_header(msg.get('To', '')),
                'subject': self._decode_header(msg.get('Subject', '')),
                'date': msg.get('Date', ''),
                'body': body_data.get('text', ''),
                'body_html': body_data.get('html', ''),
                'attachments': self._extract_attachments(msg)
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

    def close(self):
        """Close IMAP connection"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                logger.info("IMAP connection closed")
            except Exception as e:
                logger.error(f"Error closing IMAP connection: {str(e)}")
